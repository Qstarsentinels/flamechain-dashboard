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

    def get_system_ram_mb(self) -> float:
        if psutil:
            return psutil.virtual_memory().used / (1024 * 1024)
        return 512.00

    def submit_telemetry(self, payload: dict) -> bool:
        """Attempt POST to central telemetry server, falling back to local storage on failure."""
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

        # Fallback to local file update
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

            # Generate cryptographic proof of pulse state
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

            # Dispatch telemetry object
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
