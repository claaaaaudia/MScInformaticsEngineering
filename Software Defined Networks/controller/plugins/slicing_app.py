#!/usr/bin/env python3

import os
import yaml
import grpc
import time

from plugin_base import PluginBase

class NetworkSlicingApp(PluginBase):

    def info(self):
        return {
            "name": "slicing_app",
            "description": "Network slicing based on source IP and L3 routing (Self-Healing)."
        }

    def startup(self, ctrl, build_dir, config_dir):
        self._ctrl = ctrl
        self.logger.info("[SLICING] startup initiated")

        # ---------------------------
        # Load YAML safely
        # ---------------------------
        cfg_file = os.path.join(config_dir, "slicing.yaml")
        if not os.path.exists(cfg_file):
            self.logger.error("[SLICING] YAML not found: %s", cfg_file)
            return

        try:
            with open(cfg_file) as f:
                self._cfg = yaml.safe_load(f) # Guardado na classe para usar no Self-Healing
            if not self._cfg:
                return
        except Exception as e:
            self.logger.error("[SLICING] YAML load error: %s", e)
            return

        required = ["device", "grpc_addr", "device_id", "p4info", "json", "slices"]
        for k in required:
            if k not in self._cfg:
                self.logger.error("[SLICING] Missing YAML key: %s", k)
                return

        self.device = self._cfg["device"]

        # ---------------------------
        # Connect to switch
        # ---------------------------
        try:
            self.logger.info("[SLICING] connecting to %s", self.device)
            ctrl.connect(
                name=self.device,
                grpc_addr=self._cfg["grpc_addr"],
                device_id=self._cfg["device_id"],
                p4info_path=os.path.join(build_dir, self._cfg["p4info"]),
                json_path=os.path.join(build_dir, self._cfg["json"])
            )
            self.logger.info("[SLICING] pushing pipeline")
            ctrl.push_pipeline(self.device)
            time.sleep(3) # Esperar estabilização
        except Exception as e:
            self.logger.error("[SLICING] connect/pipeline error: %s", e)
            return

        # ---------------------------
        # Initial Installation
        # ---------------------------
        self.install_slices(self._cfg)
        self.install_l3_routes(self._cfg)

        # ---------------------------
        # Self-Healing Subscriptions
        # ---------------------------
        ctrl.subscribe(PluginBase.STATE_RESET, self.on_state_reset, self.info()['name'])
        ctrl.subscribe(PluginBase.DEVICE_RECONNECTED, self.on_device_reconnected, self.info()['name'])
        
        # Subscricao para detetar regras individuais apagadas
        ctrl.subscribe(PluginBase.ENTRY_REMOVED, self.on_entry_removed, self.info()['name'])
        self.is_recovering = False


    # ---------------------------
    # Install L3 Routing rules
    # ---------------------------
    def install_l3_routes(self, cfg):
        self.logger.info("[SLICING] installing L3 routing rules")
        for entry in cfg.get('table_entries', []):
            try:
                self._ctrl.install_table_entry(
                    device_name=self.device,
                    table_name=entry['table'],
                    match_fields=entry.get('match'),
                    action_name=entry['action'],
                    action_params=entry.get('params')
                )
            except Exception:
                pass 


    # ---------------------------
    # Install slice rules
    # ---------------------------
    def install_slices(self, cfg):
        self.logger.info("[SLICING] installing %d slices", len(cfg["slices"]))
        for sl in cfg["slices"]:
            if "src_ip" not in sl or "id" not in sl:
                continue

            try:
                self._ctrl.install_table_entry(
                    device_name=self.device,
                    table_name="MyIngress.slice_classifier",
                    match_fields={"hdr.ipv4.srcAddr": sl["src_ip"]},
                    action_name="MyIngress.set_slice",
                    action_params={"slice_id": sl["id"]}
                )

                if "rate" in sl and "burst" in sl:
                    try:
                        self._ctrl.meter_entry_modify(
                            device_name=self.device,
                            meter_name="MyIngress.sliceMeter",
                            index=sl["id"],
                            meter_config={
                                "cir": sl["rate"], "cburst": sl["burst"],
                                "pir": sl["rate"], "pburst": sl["burst"]
                            }
                        )
                    except Exception:
                        rate_bmv2 = float(sl['rate']) / 1000000.0
                        burst_bmv2 = sl['burst']
                        cmd = f"echo 'meter_set_rates MyIngress.sliceMeter {sl['id']} {rate_bmv2}:{burst_bmv2} {rate_bmv2}:{burst_bmv2}' | simple_switch_CLI --thrift-port 9091 > /dev/null 2>&1"
                        os.system(cmd)
            except Exception:
                pass


    # ---------------------------
    # Self-Healing Handlers
    # ---------------------------
    def on_state_reset(self, event):
        if event['device'] == self.device:
            self.logger.info("[SLICING] STATE_RESET detected on %s! Forcing pipeline reset...", self.device)
            
            try:
                self._ctrl.push_pipeline(self.device)
                time.sleep(3)
                
                self.logger.info("[SLICING] Pipeline reset. Reinstalling all rules...")
                self.install_slices(self._cfg)
                self.install_l3_routes(self._cfg)
                self.logger.info("[SLICING] Recovery completed successfully.")
            except Exception as e:
                self.logger.error("[SLICING] Failed to recover state: %s", e)

    def on_device_reconnected(self, event):
        """O switch foi reiniciado. Repor pipeline e tabelas."""
        if event['device'] == self.device:
            self.logger.info("[SLICING] DEVICE_RECONNECTED on %s! Re-pushing pipeline...", self.device)
            try:
                self._ctrl.push_pipeline(self.device)
                time.sleep(3)
                self.install_slices(self._cfg)
                self.install_l3_routes(self._cfg)
            except Exception as e:
                self.logger.error("[SLICING] Recovery failed: %s", e)

    def on_entry_removed(self, event):
        if event['device'] == self.device and not getattr(self, 'is_recovering', False):
            self.is_recovering = True
            self.logger.warning("[SLICING] Rule removal detected on %s! Forcing auto-recovery...", self.device)
            
            try:
                
                self._ctrl.push_pipeline(self.device)
                time.sleep(3)
                
                self.install_slices(self._cfg)
                self.install_l3_routes(self._cfg)
                self.logger.info("[SLICING] Auto-recovery completed! Traffic restored.")
            except Exception as e:
                self.logger.error("[SLICING] Recovery failed: %s", e)
            finally:
                time.sleep(2)
                self.is_recovering = False


    def shutdown(self):
        self.logger.info("[SLICING] shutdown signal received")

plugin = NetworkSlicingApp