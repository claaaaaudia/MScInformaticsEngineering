#!/usr/bin/env python3

import os
import subprocess
import threading
import yaml
import time

from plugin_base import PluginBase

POLL_INTERVAL = 5
TS_DISABLE_COOLDOWN_POLLS = 3

class NetworkSlicingCounting(PluginBase):

    def info(self):
        return {
            "name": "slicing_counting",
            "description": "Network slicing telemetry with Bandwidth calculation (IN and OUT)."
        }

    def startup(self, ctrl, build_dir, config_dir):
        self._ctrl = ctrl
        self._stop_event = threading.Event()

        # Store previous state for both Input (In) and Output (Out) to calculate deltas
        self.last_bytes_in = {1: 0, 2: 0, 3: 0}
        self.last_bytes_out = {1: 0, 2: 0, 3: 0}
        self.last_tot_pkts = {1: 0, 2: 0, 3: 0}
        self.last_pass_pkts = {1: 0, 2: 0, 3: 0}
        self.last_time = time.time()
        self.ts_enabled = False
        self.no_exceed_polls = 0

        self.logger.info("[SLICING COUNTING] startup initiated")

        # ---------------------------
        # Load YAML safely
        # ---------------------------
        cfg_file = os.path.join(config_dir, "slicing.yaml")
        self.logger.info("[SLICING COUNTING] loading config: %s", cfg_file)

        if not os.path.exists(cfg_file):
            self.logger.error("[SLICING COUNTING] YAML not found: %s", cfg_file)
            return

        try:
            with open(cfg_file) as f:
                cfg = yaml.safe_load(f)

            if not cfg:
                self.logger.error("[SLICING COUNTING] YAML is empty or invalid")
                return

        except Exception as e:
            self.logger.error("[SLICING COUNTING] YAML load error: %s", e)
            return

        if "device" not in cfg:
            self.logger.error("[SLICING COUNTING] Missing YAML key: device")
            return

        self.device = cfg["device"]

        # ---------------------------
        # Start monitoring thread
        # ---------------------------
        self.logger.info("[SLICING COUNTING] starting stats thread")

        threading.Thread(
            target=self.poll_stats,
            daemon=True
        ).start()

        # Ensure traffic shaping starts disabled by policy.
        self._set_ts_state(False)

    def _set_ts_state(self, enabled):
        signal_name = "USR1" if enabled else "USR2"
        try:
            subprocess.run(
                ["docker", "kill", "-s", signal_name, "traffic-shaping"],
                check=True,
                capture_output=True,
                text=True,
            )
            self.ts_enabled = enabled
            self.logger.info("[SLICING COUNTING] traffic-shaping %s", "ENABLED" if enabled else "DISABLED")
        except Exception as e:
            self.logger.warning("[SLICING COUNTING] failed to set traffic-shaping %s: %s", signal_name, e)

    # ---------------------------
    # Poll counters & Calculate Bandwidth
    # ---------------------------
    def poll_stats(self):
        self.logger.info("[SLICING COUNTING] stats thread running")

        while not self._stop_event.is_set():

            if self.device in self._ctrl.devices:
                try:
                    current_time = time.time()
                    time_diff = current_time - self.last_time
                    resultados = {}

                    # Loop through the 3 slices (1=Bronze, 2=Silver, 3=Gold)
                    exceed_detected = False
                    for slice_id in [1, 2, 3]:
                        # Read the two P4 counters
                        total = self._ctrl.read_counters(self.device, "MyIngress.sliceCounter", index=slice_id)
                        passed = self._ctrl.read_counters(self.device, "MyIngress.passedCounter", index=slice_id)

                        # Extract packet counts
                        tot_pkts = total['packets']
                        pass_pkts = passed['packets']
                        
                        # Interval exceed signal: new drops since last poll.
                        prev_tot_pkts = self.last_tot_pkts[slice_id]
                        prev_pass_pkts = self.last_pass_pkts[slice_id]
                        
                        delta_tot_pkts = max(0, tot_pkts - prev_tot_pkts)
                        delta_pass_pkts = max(0, pass_pkts - prev_pass_pkts)
                        delta_drop_pkts = max(0, delta_tot_pkts - delta_pass_pkts)
                        
                        if delta_drop_pkts > 0:
                            exceed_detected = True

                        # Extract current byte counts
                        curr_bytes_in = total['bytes']
                        curr_bytes_out = passed['bytes']
                        
                        # Calculate byte difference since the last poll
                        bytes_diff_in = curr_bytes_in - self.last_bytes_in[slice_id]
                        bytes_diff_out = curr_bytes_out - self.last_bytes_out[slice_id]
                        
                        # Calculate Mbps: (Bytes * 8 bits) / (Seconds * 1,000,000)
                        mbps_in = (bytes_diff_in * 8) / (time_diff * 1000000) if time_diff > 0 else 0
                        mbps_out = (bytes_diff_out * 8) / (time_diff * 1000000) if time_diff > 0 else 0

                        # Update history for the next poll cycle
                        self.last_bytes_in[slice_id] = curr_bytes_in
                        self.last_bytes_out[slice_id] = curr_bytes_out
                        self.last_tot_pkts[slice_id] = tot_pkts
                        self.last_pass_pkts[slice_id] = pass_pkts

                        resultados[slice_id] = {
                            'tot': tot_pkts,                 # Mantém acumulado como pediste
                            'pass_5s': delta_pass_pkts,      # Mostra só os que passaram agora
                            'drop_5s': delta_drop_pkts,      # Mostra só os drops que caíram agora
                            'mbps_in': mbps_in,
                            'mbps_out': mbps_out
                        }

                    self.last_time = current_time

                    # Traffic shaping activation policy:
                    # - turn ON immediately when new over-limit drops are detected
                    # - turn OFF only after a cooldown window with no exceed
                    if exceed_detected:
                        self.no_exceed_polls = 0
                        if not self.ts_enabled:
                            self._set_ts_state(True)
                    else:
                        self.no_exceed_polls += 1
                        if self.ts_enabled and self.no_exceed_polls >= TS_DISABLE_COOLDOWN_POLLS:
                            self._set_ts_state(False)

                    # Formatted logs for the 3 slices with IN and OUT metrics (AGORA MAIS CLAROS!)
                    self.logger.info(
                        "[SLICING] Bronze (ID 1) | Total: %d | Passed(5s): %d | Drops(5s): %d | BW In: %.2f Mbps | BW Out: %.2f Mbps",
                        resultados[1]['tot'], resultados[1]['pass_5s'], resultados[1]['drop_5s'], resultados[1]['mbps_in'], resultados[1]['mbps_out']
                    )
                    self.logger.info(
                        "[SLICING] Silver (ID 2) | Total: %d | Passed(5s): %d | Drops(5s): %d | BW In: %.2f Mbps | BW Out: %.2f Mbps",
                        resultados[2]['tot'], resultados[2]['pass_5s'], resultados[2]['drop_5s'], resultados[2]['mbps_in'], resultados[2]['mbps_out']
                    )
                    self.logger.info(
                        "[SLICING] Gold   (ID 3) | Total: %d | Passed(5s): %d | Drops(5s): %d | BW In: %.2f Mbps | BW Out: %.2f Mbps",
                        resultados[3]['tot'], resultados[3]['pass_5s'], resultados[3]['drop_5s'], resultados[3]['mbps_in'], resultados[3]['mbps_out']
                    )

                except Exception as e:
                    self.logger.warning("[SLICING COUNTING] counter read error: %s", e)
            
            time.sleep(POLL_INTERVAL)

    # ---------------------------
    # Shutdown
    # ---------------------------
    def shutdown(self):
        self.logger.info("[SLICING COUNTING] shutdown signal received")
        self._set_ts_state(False)
        self._stop_event.set()

plugin = NetworkSlicingCounting