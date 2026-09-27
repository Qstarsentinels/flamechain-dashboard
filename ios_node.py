import json
import os
import platform
import time
import urllib.error
import urllib.request

TELEMETRY_ENDPOINT = os.getenv("TELEMETRY_URL", "http://127.0.0.1:8546/telemetry/submit")
LOCAL_STATE_FILE = "node_state.json"
GLOBAL_STATE_FILE = "global_network_state.json"

def collect_telemetry_payload(pulse_count):
    return {
        "node_id": os.getenv("FLAMECHAIN_NODE_ID", f"node-ios-{os.getpid()}"),
        "platform": platform.platform(),
        "timestamp": time.time(),
        "pulse_count": pulse_count,
        "metrics": {
            "watt_hours_consumed": round(0.35 + (pulse_count * 0.001), 4),
            "allocated_ram_mb": 1536,
            "shard_processing_rate_tps": 48.2
        },
        "status": "HEALTHY"
    }

def persist_local_state(payload):
    try:
        with open(LOCAL_STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
    except Exception:
        pass

    try:
        global_data = {}
        if os.path.exists(GLOBAL_STATE_FILE):
            try:
                with open(GLOBAL_STATE_FILE, "r", encoding="utf-8") as f:
                    global_data = json.load(f)
            except Exception:
                global_data = {}

        nodes = global_data.get("nodes", {})
        nodes[payload["node_id"]] = {
            "last_seen": payload["timestamp"],
            "pulse_count": payload["pulse_count"],
            "watt_hours": payload["metrics"]["watt_hours_consumed"],
            "status": payload["status"]
        }

        global_data["nodes"] = nodes
        global_data["last_updated"] = time.time()
        global_data["total_active_nodes"] = len(nodes)

        with open(GLOBAL_STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(global_data, f, indent=2)
    except Exception:
        pass

def submit_telemetry(payload):
    if not TELEMETRY_ENDPOINT:
        return

    try:
        encoded_data = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            TELEMETRY_ENDPOINT,
            data=encoded_data,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "FlameChain-MobileNode/1.0"
            },
            method="POST"
        )
        with urllib.request.urlopen(request, timeout=1) as response:
            pass
    except Exception:
        pass

def run_pulse_loop(interval_seconds=5):
    pulse_count = 0
    while True:
        pulse_count += 1
        payload = collect_telemetry_payload(pulse_count)
        persist_local_state(payload)
        submit_telemetry(payload)
        time.sleep(interval_seconds)

if __name__ == "__main__":
    run_pulse_loop()
