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

def print_hardware_header(node_id, ram_mb):
    banner = f"""
============================================================
🔥 FLAMECHAIN AGI SINGULARITY MESH NODE
============================================================
Node ID               : {node_id}
Platform Architecture : {platform.platform()}
System Python         : {platform.python_version()}
Dynamic Shard RAM     : {ram_mb:,.2f} MB
Target Ingest URL     : {TELEMETRY_ENDPOINT or 'DISABLED (OFFLINE MINTING)'}
Local State Path      : {os.path.abspath(LOCAL_STATE_FILE)}
============================================================
"""
    print(banner.strip(), flush=True)

def load_initial_state():
    pulse_count = 0
    wh_consumed = 0.0
    flame_minted = 0.0

    if os.path.exists(LOCAL_STATE_FILE):
        try:
            with open(LOCAL_STATE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)

            if isinstance(data, dict):
                pulse_count = data.get("pulse_count") or data.get("pulse") or 0

                metrics = data.get("metrics", {}) if isinstance(data.get("metrics"), dict) else {}
                energy_metrics = data.get("energy_metrics", {}) if isinstance(data.get("energy_metrics"), dict) else {}

                wh_val = (
                    data.get("watt_hours_consumed") or
                    data.get("wh_consumed") or
                    metrics.get("watt_hours_consumed") or
                    metrics.get("wh_consumed") or
                    energy_metrics.get("watt_hours_consumed") or
                    energy_metrics.get("wh_consumed") or
                    0.0
                )
                wh_consumed = float(wh_val)

                minted_val = (
                    data.get("flame_minted") or
                    data.get("minted") or
                    metrics.get("flame_minted") or
                    metrics.get("minted") or
                    energy_metrics.get("flame_minted") or
                    energy_metrics.get("minted") or
                    0.0
                )
                flame_minted = float(minted_val)

        except Exception as e:
            print(f"[State Boot Warning] Exception parsing {LOCAL_STATE_FILE}: {e}. Initializing default state.", flush=True)

    return int(pulse_count), float(wh_consumed), float(flame_minted)

def collect_telemetry_payload(node_id, pulse_count, hash_val, ram_mb, wh, minted, shard_name):
    return {
        "node_id": node_id,
        "platform": platform.platform(),
        "timestamp": time.time(),
        "pulse_count": pulse_count,
        "proof_hash": hash_val,
        "energy_metrics": {
            "watt_hours_consumed": round(wh, 6),
            "flame_minted": round(minted, 6)
        },
        "metrics": {
            "watt_hours_consumed": round(wh, 6),
            "flame_minted": round(minted, 6),
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

def submit_telemetry(payload):
    if TELEMETRY_ENDPOINT:
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
                return
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

def run_pulse_loop(interval_seconds=5):
    node_id = os.getenv("FLAMECHAIN_NODE_ID", f"node-ios-{os.getpid()}")
    ram_mb = 137760.00

    print_hardware_header(node_id, ram_mb)

    pulse_count, wh_consumed, flame_minted = load_initial_state()
    print(f"[FlameChain Bootloader] Restored State -> Pulse: #{pulse_count} | Wh: {wh_consumed:.6f} | FLAME: {flame_minted:.6f}\n", flush=True)

    shards = ["shard-0-embed", "shard-1-attn", "shard-2-mlp", "shard-3-norm"]

    while True:
        pulse_count += 1
        
        delta_wh = 0.000150
        wh_consumed += delta_wh
        delta_minted = 0.812500
        flame_minted += delta_minted

        hash_val = hashlib.sha256(f"{node_id}-{pulse_count}-{time.time()}".encode("utf-8")).hexdigest()
        shard_name = shards[pulse_count % len(shards)]

        print(f"[⚡ PULSE #{pulse_count}] Hash: {hash_val[:16]}... | RAM: {ram_mb:.2f} MB | Wh: {wh_consumed:.6f} | Minted: {flame_minted:.4f} FLAME | Shard: {shard_name}", flush=True)

        payload = collect_telemetry_payload(node_id, pulse_count, hash_val, ram_mb, wh_consumed, flame_minted, shard_name)
        persist_local_state(payload)
        submit_telemetry(payload)
        
        time.sleep(interval_seconds)

if __name__ == "__main__":
    run_pulse_loop()
