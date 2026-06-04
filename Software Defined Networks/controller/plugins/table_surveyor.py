#!/usr/bin/env python3
# SPDX-License-Identifier: ANCL-1.0
# Copyright (c) 2026  jfpereira <d12267@di.uminho.pt> — di.uminho.pt
# Academic use only · no commercial use · see LICENSE
# AI-assisted development: Claude (Anthropic)
"""
table_surveyor.py — polls all device tables every SURVEY_INTERVAL seconds,
diffs the snapshot against the previous one, and emits:

  STATE_RESET        — all entries on a device were wiped at once
  ENTRY_REMOVED      — a single entry disappeared
  ENTRY_ADDED        — a single entry appeared that was not there before
  DEVICE_RECONNECTED — a device that was unreachable is reachable again
"""

import threading
import time

import grpc

from plugin_base import PluginBase

# How often (seconds) to poll all devices
SURVEY_INTERVAL = 10


class TableSurveyor(PluginBase):

    def info(self):
        return {
            'name': 'table_surveyor',
            'description': 'Polls device tables and emits diff events (STATE_RESET, ENTRY_REMOVED, ENTRY_ADDED, DEVICE_RECONNECTED).'
        }

    def startup(self, ctrl, build_dir, config_dir):
        self._ctrl = ctrl
        # device_name -> set of entry keys (frozenset of match field bytes)
        self._snapshots = {}
        # device_name -> bool (True = was reachable on last poll)
        self._reachable = {}

        # initialise snapshots for all already-connected devices
        for device_name in list(ctrl.devices.keys()):
            self._snapshots[device_name] = self._read_snapshot(device_name)
            self._reachable[device_name] = True

        # start background polling thread — must not block startup()
        t = threading.Thread(target=self._poll_loop, daemon=True)
        t.start()
        self.logger.info("started — polling every %ds", SURVEY_INTERVAL)

    # ── Snapshot helper ───────────────────────────────────────────────────────

    def _read_snapshot(self, device_name):
        """
        Read all table entries from a device and return them as a dict:
            { entry_key: entry }
        where entry_key is a frozenset of (field_id, value_bytes) tuples
        that uniquely identifies the match fields of an entry.
        Returns None if the device is unreachable.
        """
        snapshot = {}
        try:
            for response in self._ctrl.read_table_entries(device_name):
                for entity in response.entities:
                    entry = entity.table_entry
                    # Build a hashable key from the match fields
                    key = frozenset(
                        (mf.field_id, mf.exact.value or mf.lpm.value or mf.ternary.value)
                        for mf in entry.match
                    )
                    snapshot[key] = entry
        except grpc.RpcError:
            return None  # device unreachable
        return snapshot

    # ── Poll loop ─────────────────────────────────────────────────────────────

    def _poll_loop(self):
        """Background thread: polls every SURVEY_INTERVAL seconds."""
        while True:
            time.sleep(SURVEY_INTERVAL)
            for device_name in list(self._ctrl.devices.keys()):
                self._survey(device_name)

    def _survey(self, device_name):
        """Compare current snapshot with previous and emit diff events."""
        current = self._read_snapshot(device_name)

        # ── Device unreachable ────────────────────────────────────────────────
        if current is None:
            if self._reachable.get(device_name, True):
                self.logger.warning("device %s is unreachable", device_name)
                self._reachable[device_name] = False
            return

        # ── Device just came back ─────────────────────────────────────────────
        if not self._reachable.get(device_name, True):
            self.logger.info("device %s is reachable again", device_name)
            self._reachable[device_name] = True
            self._snapshots[device_name] = current
            self._ctrl.emit(PluginBase.DEVICE_RECONNECTED, {'device': device_name})
            return

        previous = self._snapshots.get(device_name, {})

        # ── All entries wiped at once ─────────────────────────────────────────
        if len(previous) > 0 and len(current) == 0:
            self.logger.info("STATE_RESET detected on %s", device_name)
            self._snapshots[device_name] = current
            self._ctrl.emit(PluginBase.STATE_RESET, {'device': device_name})
            return

        # ── Individual diffs ──────────────────────────────────────────────────
        prev_keys    = set(previous.keys())
        current_keys = set(current.keys())

        for key in prev_keys - current_keys:
            entry = previous[key]
            # Extract the raw match value bytes to pass as match_key
            match_key = next(iter(key))[1] if key else b''
            self.logger.info("ENTRY_REMOVED on %s", device_name)
            self._ctrl.emit(PluginBase.ENTRY_REMOVED, {
                'device':    device_name,
                'match_key': match_key,
                'entry':     entry
            })

        for key in current_keys - prev_keys:
            entry = current[key]
            self.logger.info("ENTRY_ADDED on %s", device_name)
            self._ctrl.emit(PluginBase.ENTRY_ADDED, {
                'device': device_name,
                'entry':  entry
            })

        self._snapshots[device_name] = current


plugin = TableSurveyor