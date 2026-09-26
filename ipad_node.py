#!/usr/bin/env python3
"""
FlameChain iOS/iPad Node Telemetry Dispatcher
Probes primary network interfaces (iOS Hotspot Gateway & Loopback)
and transmits hardware allocations to the global mesh.
"""

import json
import time
import urllib.request
import urllib.error
import sys

TARGET_ENDPOINTS = [
    "http://172.20.10.1:8546/telemetry/submit",
    "http://127.0.0.1:8546/telemetry/submit"
]

def gather_node_telemetry():
    return {
        "node_id": "ios_ipad_pro_m2_mesh_01",
        "device_model": "iPad14,3 (M2)",
        "watt_hours_contributed": 32.4,
        "ram_allocated_mb": 6144.0,
        "active_shards": [
            "llama3-8b-shard-00",
            "llama3-8b-shard-01"
        ],
        "minted_balance": 4820.75,
        "timestamp": time.time()
    }

def transmit_telemetry():
    payload = gather_node_telemetry()
    encoded_data = json.dumps(payload).encode("utf-8")
    
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "FlameChain-iOS-Node/1.4.0"
    }

    print(f"[+] Prepared telemetry payload for node: {payload['node_id']}")
    success = False

    for endpoint in TARGET_ENDPOINTS:
        print(f"[->] Probing gateway target: {endpoint} ...")
        req = urllib.request.Request(endpoint, data=encoded_data, headers=headers, method="POST")
        
        try:
            with urllib.request.urlopen(req, timeout=3) as response:
                if response.status == 200:
                    res_body = json.loads(response.read().decode("utf-8"))
                    print(f"[✔] Successfully synced with gateway: {endpoint}")
                    print(f"    Response: {json.dumps(res_body)}")
                    success = True
                    break
        except urllib.error.URLError as e:
            print(f"[!] Gateway reachability failed for {endpoint}: {e.reason}")
        except Exception as e:
            print(f"[!] Error transmitting to {endpoint}: {str(e)}")

    if not success:
        print("[-] Error: All multi-gateway endpoints unreachable.", file=sys.stderr)
        return False
    return True

if __name__ == "__main__":
    print("==================================================")
    print("   FlameChain iPad Edge Telemetry Probe Engine   ")
    print("==================================================")
    transmit_telemetry()
