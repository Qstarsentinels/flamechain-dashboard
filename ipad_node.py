#!/usr/bin/env python3
import json
import time
import socket
import urllib.request
import urllib.error
import random
import sys

TARGET_ENDPOINTS = [
    "http://172.20.10.1:8546/telemetry/submit",
    "http://10.6.87.1:8546/telemetry/submit",
    "http://127.0.0.1:8546/telemetry/submit"
]

NODE_ID = f"node-ipad-edge-{socket.gethostname()}"
INTERVAL_SECONDS = 3.0

def gather_node_telemetry() -> dict:
    return {
        "node_id": NODE_ID,
        "status": "ONLINE",
        "watt_hours": round(random.uniform(12.5, 38.0), 2),
        "ram_allocated_gb": 3.5,
        "active_shards": ["shard-1", "shard-3"],
        "timestamp": time.time()
    }

def transmit_telemetry():
    payload = gather_node_telemetry()
    encoded_data = json.dumps(payload).encode("utf-8")

    for url in TARGET_ENDPOINTS:
        try:
            req = urllib.request.Request(
                url,
                data=encoded_data,
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=2.0) as response:
                if response.status == 200:
                    print(f"[🔥 Telemetry Success] Synchronized metrics to target -> {url} [HTTP 200]")
                    return True
                else:
                    print(f"[⚠️ Telemetry Warning] Node {url} returned HTTP status {response.status}. Trying next...")
        except urllib.error.HTTPError as e:
            if e.code == 200:
                print(f"[🔥 Telemetry Success] Synchronized to {url} [HTTP 200]")
                return True
            print(f"[❌ HTTP Error] {url} -> Status {e.code}")
        except (urllib.error.URLError, socket.timeout, Exception) as err:
            print(f"[🔌 Connection Refused/Timeout] {url} unreachable ({err})")

    print("[🚨 Mesh Telemetry Alert] All ingress target IPs failed to accept telemetry payload.")
    return False

def main():
    print(f"[🔥 FlameChain Node Engine] Initialized node ID: {NODE_ID}")
    print(f"[🔥 Mesh Target Stack]: {TARGET_ENDPOINTS}")
    
    while True:
        transmit_telemetry()
        time.sleep(INTERVAL_SECONDS)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[FlameChain Node] Telemetry loop terminated gracefully.")
        sys.exit(0)
