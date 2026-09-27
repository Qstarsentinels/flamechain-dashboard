import json
import time
import os
import platform
import urllib.request
import urllib.error

TELEMETRY_ENDPOINT = "http://127.0.0.1:8546/telemetry/submit"

def collect_telemetry_payload():
    """
    Gather lightweight hardware metrics and AGI node telemetry.
    """
    return {
        "node_id": os.getenv("FLAMECHAIN_NODE_ID", f"node-ios-{os.getpid()}"),
        "platform": platform.platform(),
        "timestamp": time.time(),
        "metrics": {
            "watt_hours_estimated": 0.28,
            "allocated_ram_mb": 1536,
            "shard_processing_rate_tps": 42.5
        },
        "status": "HEALTHY"
    }

def submit_telemetry(payload=None):
    """
    Submits telemetry payload directly via HTTP POST to endpoint http://127.0.0.1:8546/telemetry/submit.
    """
    if payload is None:
        payload = collect_telemetry_payload()

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

    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            status_code = response.getcode()
            response_body = response.read().decode("utf-8")
            print(f"[Telemetry] POST {TELEMETRY_ENDPOINT} -> {status_code}: {response_body}")
            return True
    except urllib.error.HTTPError as e:
        print(f"[Telemetry Error] HTTP {e.code}: {e.reason}")
        return False
    except urllib.error.URLError as e:
        print(f"[Telemetry Error] Connection failed to {TELEMETRY_ENDPOINT}: {e.reason}")
        return False

def start_telemetry_loop(interval_seconds=10):
    """
    Worker process loop submitting telemetry at set intervals.
    """
    print(f"[FlameChain Telemetry Worker] Dispatching directly to {TELEMETRY_ENDPOINT}")
    while True:
        submit_telemetry()
        time.sleep(interval_seconds)

if __name__ == "__main__":
    submit_telemetry()
