import os
import json
import time
import logging
import hashlib
import urllib.request
import urllib.error

TELEMETRY_ENDPOINT = "http://127.0.0.1:8080/api/telemetry"
TELEMETRY_TIMEOUT_SEC = 2.0
STATE_FILE = "node_state.json"

WH_INCREMENT = 0.000150
FLAME_INCREMENT = 0.813475

IPFS_GATEWAY_FALLBACKS = [
    "https://ipfs.io/ipns/k51qzi5uqu5dl11flamechain_state.json",
    "https://gateway.pinata.cloud/ipfs/QmFlameChainGlobalStateFallback"
]

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

node_state = {
    "node_id": "ipad-edge-alpha-01",
    "watt_hours": 0.0,
    "flame_tokens": 0.0,
    "available_ram_mb": 3420,
    "active_shards": ["shard_llama3_8b_layer_12_16"],
    "mesh_role": "inference_worker"
}


def fetch_ipfs_state() -> dict:
    for gateway_url in IPFS_GATEWAY_FALLBACKS:
        try:
            req = urllib.request.Request(
                gateway_url,
                headers={"User-Agent": "FlameChain-EdgeNode/1.0"}
            )
            with urllib.request.urlopen(req, timeout=2.0) as resp:
                if resp.status == 200:
                    return json.loads(resp.read().decode("utf-8"))
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError, Exception):
            continue
    return {}


def audit_initial_state() -> dict:
    global node_state

    highest_wh = float(node_state.get("watt_hours", 0.0))
    highest_tokens = float(node_state.get("flame_tokens", 0.0))

    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as f:
                local_state = json.load(f)
                highest_wh = max(highest_wh, float(local_state.get("watt_hours", 0.0)))
                highest_tokens = max(highest_tokens, float(local_state.get("flame_tokens", 0.0)))
        except (json.JSONDecodeError, OSError, ValueError) as err:
            logging.warning(f"Could not read local {STATE_FILE}: {err}")

    ipfs_state = fetch_ipfs_state()
    if ipfs_state:
        try:
            highest_wh = max(highest_wh, float(ipfs_state.get("watt_hours", 0.0)))
            highest_tokens = max(highest_tokens, float(ipfs_state.get("flame_tokens", 0.0)))
        except (ValueError, TypeError):
            pass

    node_state["watt_hours"] = highest_wh
    node_state["flame_tokens"] = highest_tokens

    try:
        with open(STATE_FILE, "w") as f:
            json.dump(node_state, f, indent=2)
    except OSError as err:
        logging.error(f"Failed to write state file: {err}")

    return node_state


def submit_telemetry(payload: dict) -> bool:
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
        return False


def run_pulse_loop():
    pulse_count = 0
    while True:
        pulse_count += 1
        
        node_state["watt_hours"] += WH_INCREMENT
        node_state["flame_tokens"] += FLAME_INCREMENT

        pulse_data = f"{node_state['node_id']}:{pulse_count}:{time.time()}"
        sha_hash = hashlib.sha256(pulse_data.encode("utf-8")).hexdigest()[:16]

        ram = node_state.get("available_ram_mb", 3420)
        wh = node_state["watt_hours"]
        tokens = node_state["flame_tokens"]

        print(
            f"[PULSE #{pulse_count}] SHA256: {sha_hash} | RAM: {ram}MB | Wh: {wh:.6f} | FLAME: {tokens:.6f} | Shard: HOTSWAP",
            flush=True
        )

        submit_telemetry(node_state)

        try:
            with open(STATE_FILE, "w") as f:
                json.dump(node_state, f, indent=2)
        except OSError:
            pass

        time.sleep(5)


if __name__ == "__main__":
    audit_initial_state()
    run_pulse_loop()
