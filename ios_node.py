import json
import os
import platform
import time
import urllib.error
import urllib.request

TELEMETRY_ENDPOINT = "http://127.0.0.1:8546/telemetry/submit"
LOCAL_STATE_FILE = "node_state.json"
GLOBAL_STATE_FILE = "global_network_state.json"

def collect_telemetry_payload():
    """
    Gather lightweight hardware metrics and AGI node telemetry.
    """
    return {
        "node_id": os.getenv("FLAMECHAIN_NODE_ID", f"node-ios-{os.getpid()}"),
        "platform": platform.platform(),
        "timestamp": time.time(),
        "metrics": {
            "watt_hours_consumed": 0.35,
            "allocated_ram_mb": 1536,
            "shard_processing_rate_tps": 48.2
        },
        "status": "HEALTHY"
    }

def persist_local_state(payload):
    """
    Persists state to node_state.json FIRST on every pulse before network attempts.
    Also syncs aggregate telemetry into global_network_state.json.
    """
    # 1. Primary local state write
    try:
        with open(LOCAL_STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
    except Exception as e:
        print(f"[State Write Error] Failed updating {LOCAL_STATE_FILE}: {e}")

    # 2. Aggregate global state sync
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
            "watt_hours": payload["metrics"]["watt_hours_consumed"],
            "status": payload["status"]
        }

        global_data["nodes"] = nodes
        global_data["last_updated"] = time.time()
        global_data["total_active_nodes"] = len(nodes)

        with open(GLOBAL_STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(global_data, f, indent=2)
    except Exception as e:
        print(f"[State Write Error] Failed updating {GLOBAL_STATE_FILE}: {e}")

def submit_telemetry(payload):
    """
    Attempts POST submit to ingest endpoint with minimal timeout.
    Catches URLError/ConnectionRefusedError non-blocking and continues instantly.
    """
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
        # 1-second connect/read timeout prevents blocking the pulse loop
        with urllib.request.urlopen(request, timeout=1) as response:
            pass
    except (urllib.error.URLError, urllib.error.HTTPError, ConnectionRefusedError, OSError):
        # Gracefully swallow network/connection errors without stalling execution
        pass
    except Exception:
        # Non-fatal fallback catch
        pass

def start_pulse_loop(interval_seconds=5):
    """
    Main pulse loop: Persists local state first, attempts non-blocking telemetry submit,
    and immediately continues execution.
    """
    print(f"[FlameChain Mobile Node] Active. Persisting to {LOCAL_STATE_FILE} and posting to {TELEMETRY_ENDPOINT}")
    while True:
        try:
            # Step 1: Collect payload
            payload = collect_telemetry_payload()

            # Step 2: Persist state locally FIRST on every pulse
            persist_local_state(payload)

            # Step 3: Attempt telemetry transport (non-blocking failure)
            submit_telemetry(payload)

        except Exception as err:
            print(f"[Pulse Warning] Loop iteration exception swallowed: {err}")

        time.sleep(interval_seconds)

if __name__ == "__main__":
    start_pulse_loop()
