#!/usr/bin/env python3
"""
FlameChain Edge Node Telemetry Module
Target OS/Hardware: iOS / Termux / Mobile Mesh Node
"""

import hashlib
import json
import os
import sys
import time
import urllib.request
import urllib.error

try:
    import psutil
except ImportError:
    psutil = None


class FlameNode:
    def __init__(self):
        self.count = 0
        self.wh = 0.000000
        self.flame = 0.000000
        self.node_id = os.getenv("NODE_ID", "NODE-IOS-PAD-01")
        self.tab_ip = os.getenv("TAB_IP", "127.0.0.1")
        self.endpoint = f"http://{self.tab_ip}:8080/api/telemetry"
        self.fallback_file = "telemetry_fallback.json"
        self.state_file = "node_state.json"
        
        self.audit_initial_state()

    def get_system_ram_mb(self) -> float:
        if psutil:
            return psutil.virtual_memory().used / (1024 * 1024)
        return 512.00

    def audit_initial_state(self):
        """Read node_state.json and preserve maximum historical state."""
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, "r") as f:
                    state_data = json.load(f)
                    existing_wh = float(state_data.get("wh", 0.0))
                    existing_flame = float(state_data.get("flame", 0.0))
                    existing_count = int(state_data.get("count", 0))

                    self.wh = max(existing_wh, self.wh)
                    self.flame = max(existing_flame, self.flame)
                    self.count = max(existing_count, self.count)
                    
                    print(
                        f"[STATE RESTORED] Loaded from {self.state_file} | "
                        f"Pulse: {self.count} | Wh: {self.wh:.6f} | FLAME: {self.flame:.6f}"
                    )
            except Exception as e:
                print(f"[WARN] Failed to audit initial state from {self.state_file}: {e}", file=sys.stderr)

    def persist_state(self):
        """Save current pulse state locally."""
        state_payload = {
            "node_id": self.node_id,
            "count": self.count,
            "wh": self.wh,
            "flame": self.flame,
            "updated_at": time.time()
        }
        try:
            with open(self.state_file, "w") as f:
                json.dump(state_payload, f, indent=2)
        except OSError as e:
            print(f"[WARN] Failed to write {self.state_file}: {e}", file=sys.stderr)

    def submit_telemetry(self, payload: dict) -> bool:
        """POST telemetry payload to central server, falling back to disk on failure."""
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(
            self.endpoint,
            data=data,
            headers={'Content-Type': 'application/json'},
            method='POST'
        )

        try:
            with urllib.request.urlopen(req, timeout=2.0) as response:
                if response.status == 200:
                    return True
        except (urllib.error.URLError, OSError, TimeoutError):
            pass

        # Local fallback telemetry update
        try:
            with open(self.fallback_file, "w") as f:
                json.dump(payload, f, indent=2)
        except OSError as e:
            print(f"[WARN] Failed to write fallback telemetry: {e}", file=sys.stderr)
            return False

        return False

    def run_pulse_loop(self, max_pulses=None):
        while True:
            self.count += 1
            self.wh += 0.000150
            self.flame += 0.813475

            self.persist_state()

            telemetry_payload_str = f"flamechain:{self.count}:{self.wh}:{self.flame}:{time.time()}"
            sha256_hash = hashlib.sha256(telemetry_payload_str.encode('utf-8')).hexdigest()

            ram_mb = self.get_system_ram_mb()

            print(
                f"[PULSE #{self.count}] SHA256: {sha256_hash} | "
                f"RAM: {ram_mb:.2f}MB | "
                f"Wh: {self.wh:.6f} (+0.000150) | "
                f"FLAME: {self.flame:.6f} (+0.813475) | "
                f"Shard: SHARD-0X-HOTSWAP-ACTIVE"
            )
            sys.stdout.flush()

            telemetry_data = {
                "node_id": self.node_id,
                "pulse": self.count,
                "hash": sha256_hash,
                "ram_mb": round(ram_mb, 2),
                "wh": round(self.wh, 6),
                "flame": round(self.flame, 6),
                "shard": "SHARD-0X-HOTSWAP-ACTIVE",
                "timestamp": time.time()
            }
            self.submit_telemetry(telemetry_data)

            if max_pulses and self.count >= max_pulses:
                break

            time.sleep(1.0)


if __name__ == "__main__":
    node = FlameNode()
    node.run_pulse_loop()
