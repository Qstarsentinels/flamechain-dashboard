import os
import json
import time
import logging
import urllib.request
import urllib.error

TELEMETRY_ENDPOINT = "http://127.0.0.1:8080/api/telemetry"
TELEMETRY_TIMEOUT_SEC = 2.0
STATE_FILE = "node_state.json"

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

node_state = {
    "node_id": "ipad-edge-alpha-01",
    "watt_hours": 0.0,
    "flame_tokens": 0.0,
    "available_ram_mb": 3420,
    "active_shards": ["shard_llama3_8b_layer_12_16"],
    "mesh_role": "inference_worker"
}


def audit_initial_state() -> dict:
    """
    Audits and restores state from node_state.json if present.
    Sets watt_hours and flame_tokens to the highest recorded values to persist progress across restarts.
    """
    global node_state
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as f:
                saved_state = json.load(f)

            saved_wh = float(saved_state.get("watt_hours", 0.0))
            saved_tokens = float(saved_state.get("flame_tokens", 0.0))

            node_state["watt_hours"] = max(float(node_state.get("watt_hours", 0.0)), saved_wh)
            node_state["flame_tokens"] = max(float(node_state.get("flame_tokens", 0.0)), saved_tokens)

            logging.info(
                f"State audit complete. Restored progress: "
                f"Watt-Hours={node_state['watt_hours']}, FLAME Tokens={node_state['flame_tokens']}"
            )
        except (json.JSONDecodeError, OSError, ValueError) as err:
            logging.error(f"Failed to read or parse {STATE_FILE}: {err}")
    else:
        logging.info(f"No {STATE_FILE} found. Initializing node baseline.")

    return node_state


def submit_telemetry(payload: dict) -> bool:
    """
    HTTP POSTs the node telemetry payload using urllib.request with a 2-second timeout.
    Catches all urllib and connection errors silently without raising exceptions or breaking the loop.
    """
    try:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            TELEMETRY_ENDPOINT,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=TELEMETRY_TIMEOUT_SEC) as response:
            return response.status in (200, 201, 202)
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, Exception):
        # Silently absorb all network & urllib errors to keep the telemetry loop resilient
        return False


def pulse_loop():
    """
    Continuous telemetry loop for edge node monitoring.
    """
    audit_initial_state()
    while True:
        submit_telemetry(node_state)
        time.sleep(5)


if __name__ == "__main__":
    audit_initial_state()
    submit_telemetry(node_state)
