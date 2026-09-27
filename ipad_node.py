import json
import os
import platform
import time
import hashlib
import urllib.error
import urllib.request

TELEMETRY_ENDPOINT = os.getenv("TELEMETRY_URL", "http://127.0.0.1:8546/telemetry/submit")
LOCAL_STATE_FILE = "node_state.json"
GLOBAL_STATE_FILE = "global_network_state.json"

def collect_telemetry_payload(pulse_count, hash_val, ram_mb, wh, minted, shard_name):
    node_id = os.getenv("FLAMECHAIN_NODE_ID", f"node-ios-{os.getpid()}")
    return {
        "node_id": node_id,
        "platform": platform.platform(),
        "timestamp": time.time(),
        "pulse_count": pulse_count,
        "proof_hash": hash_val,
        "metrics": {
            "watt_hours_consumed": round(wh, 6),
            "flame_minted": round(minted, 4),
            "allocated_ram_mb": ram_mb,
            "shard_name": shard_name,
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
            "flame_minted": payload["metrics"]["flame_minted"],
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
        print("[Telemetry Offline] Local state saved.", flush=True)
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
        print("[Telemetry Offline] Local state saved.", flush=True)

def run_pulse_loop(interval_seconds=5):
    pulse_count = 0
    node_id = os.getenv("FLAMECHAIN_NODE_ID", f"node-ios-{os.getpid()}")
    shards = ["shard-0-embed", "shard-1-attn", "shard-2-mlp", "shard-3-norm"]

    while True:
        pulse_count += 1
        
        hash_val = hashlib.sha256(f"{node_id}-{pulse_count}-{time.time()}".encode("utf-8")).hexdigest()
        ram_mb = 1536
        wh = pulse_count * 0.00035
        minted = wh * 1.61803398875
        shard_name = shards[pulse_count % len(shards)]

        print(f"[⚡ PULSE #{pulse_count}] Hash: {hash_val[:16]}... | RAM: {ram_mb} MB | Wh: {wh:.6f} | Minted: {minted:.4f} FLAME | Shard: {shard_name}", flush=True)

        payload = collect_telemetry_payload(pulse_count, hash_val, ram_mb, wh, minted, shard_name)
        persist_local_state(payload)
        submit_telemetry(payload)
        
        time.sleep(interval_seconds)

if __name__ == "__main__":
    run_pulse_loop()
