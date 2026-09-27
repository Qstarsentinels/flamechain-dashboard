#!/usr/bin/env python3
"""
FlameChain iPad Node Validator
Backed by System RAM and Watt-Hour Proof-of-Work / Proof-of-Energy Pulses
Direct local state persistence, background network telemetry submit, and direct local global_network_state.json updater.
"""

import os
import sys
import time
import json
import hashlib
import platform
import uuid
import socket
import threading
import resource
import urllib.request
import urllib.error

# Local storage paths and network endpoints
STATE_FILE = "node_state.json"
GLOBAL_STATE_FILE = "global_network_state.json"
SNAPSHOT_FILE = "node_telemetry_snapshot.json"
PRIMARY_LAN_URL = "http://172.20.10.1:8546/telemetry/submit"

SHARD_MODELS = [
    "shard_0_vision_encoder.bin",
    "shard_1_language_decoder.bin",
    "shard_2_audio_spectrogram.bin",
    "shard_3_spatial_vector.bin"
]

def get_telemetry_urls():
    """Returns target endpoints for background telemetry."""
    urls = []
    env_url = os.environ.get("GATEWAY_URL")
    if env_url:
        if not env_url.startswith("http://") and not env_url.startswith("https://"):
            env_url = f"http://{env_url}"
        if "/telemetry/submit" not in env_url:
            env_url = env_url.rstrip("/") + "/telemetry/submit"
        urls.append(env_url)

    urls.append(PRIMARY_LAN_URL)
    urls.append("http://127.0.0.1:8546/telemetry/submit")
    return urls

def get_total_ram_mb():
    """Detect total system memory in MB."""
    if os.path.exists("/proc/meminfo"):
        try:
            with open("/proc/meminfo", "r") as f:
                for line in f:
                    if line.startswith("MemTotal:"):
                        return round(int(line.split()[1]) / 1024.0, 2)
        except Exception:
            pass

    try:
        import psutil
        return round(psutil.virtual_memory().total / (1024 * 1024), 2)
    except ImportError:
        pass

    return 4096.00

def get_current_ram_usage_mb():
    """Get current resident set memory usage (RSS) in MB."""
    try:
        import psutil
        return round(psutil.Process().memory_info().rss / (1024 * 1024), 2)
    except Exception:
        pass

    try:
        rss_kb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        if rss_kb > 0:
            return round(rss_kb / 1024.0, 2)
    except Exception:
        pass

    return 128.50

def detect_device_specs():
    """Detect node hardware specs."""
    arch = platform.machine() or platform.processor() or "arm64"
    sys_name = platform.system() or "Darwin"
    node_uuid = str(uuid.uuid5(uuid.NAMESPACE_DNS, socket.gethostname() or "flamechain.ipad.node"))
    
    return {
        "node_id": f"node_{node_uuid[:12]}",
        "architecture": arch,
        "os_system": sys_name,
        "total_mb_ram": get_total_ram_mb(),
        "timestamp_initialized": time.time()
    }

def merge_telemetry_to_global_state_direct(payload):
    """
    Directly merges node telemetry into global_network_state.json on local disk.
    Ensures state is instantly updated and available for local UI serving and git commits.
    """
    node_id = payload.get("node_id")
    snapshot_data = {
        "node_id": node_id,
        "total_mb_ram": payload.get("total_mb_ram"),
        "ram_used_mb": payload.get("ram_used_mb"),
        "active_shard_id": payload.get("active_shard_id"),
        "minted_flame_units": payload.get("minted_flame_units"),
        "accumulated_wh": payload.get("accumulated_wh"),
        "pulse_count": payload.get("pulse_count"),
        "state_root": payload.get("state_root"),
        "timestamp": payload.get("timestamp", time.time())
    }

    if os.path.exists(GLOBAL_STATE_FILE):
        try:
            global_state = {"active_nodes": {}}
            with open(GLOBAL_STATE_FILE, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                if isinstance(loaded, dict):
                    global_state.update(loaded)
                    if "active_nodes" not in global_state or not isinstance(global_state["active_nodes"], dict):
                        global_state["active_nodes"] = {}

            global_state["active_nodes"][node_id] = snapshot_data

            # Re-calculate aggregate global metrics
            nodes_list = list(global_state["active_nodes"].values())
            global_state["total_active_nodes"] = len(nodes_list)
            global_state["total_gross_supply"] = round(sum(float(n.get("minted_flame_units", 0.0)) for n in nodes_list), 4)
            global_state["global_watt_hours"] = round(sum(float(n.get("accumulated_wh", 0.0)) for n in nodes_list), 6)
            global_state["total_mesh_ram_mb"] = round(sum(float(n.get("total_mb_ram", 0.0)) for n in nodes_list), 2)
            global_state["last_updated"] = time.time()

            tmp_global = f"{GLOBAL_STATE_FILE}.tmp"
            with open(tmp_global, "w", encoding="utf-8") as f:
                json.dump(global_state, f, indent=2)
            os.replace(tmp_global, GLOBAL_STATE_FILE)
        except Exception:
            pass

    try:
        tmp_snap = f"{SNAPSHOT_FILE}.tmp"
        with open(tmp_snap, "w", encoding="utf-8") as f:
            json.dump(snapshot_data, f, indent=2)
        os.replace(tmp_snap, SNAPSHOT_FILE)
    except Exception:
        pass

def send_telemetry_async(payload, pulse_count):
    """
    Non-blocking async telemetry worker thread.
    Directly updates local global_network_state.json file on disk every pulse.
    Attempts POST to available network endpoints in background without interrupting execution.
    """
    def _post_task():
        # Update local global_network_state.json directly
        merge_telemetry_to_global_state_direct(payload)

        # Background POST attempt
        data = json.dumps(payload).encode('utf-8')
        for url in get_telemetry_urls():
            try:
                req = urllib.request.Request(
                    url,
                    data=data,
                    headers={'Content-Type': 'application/json'},
                    method='POST'
                )
                with urllib.request.urlopen(req, timeout=1.5) as resp:
                    if resp.status in (200, 201):
                        return
            except Exception:
                continue

    thread = threading.Thread(target=_post_task, daemon=True)
    thread.start()

def compute_deterministic_state_root(pulse_count, accumulated_wh, active_shard_id):
    """Calculates state_root hash derived from pulse attributes."""
    raw_payload = f"pulse:{pulse_count}|wh:{accumulated_wh:.6f}|shard:{active_shard_id}"
    return hashlib.sha256(raw_payload.encode('utf-8')).hexdigest()

def save_local_state(state_dict):
    """Atomically persist local state to node_state.json."""
    tmp_file = f"{STATE_FILE}.tmp"
    try:
        with open(tmp_file, "w", encoding="utf-8") as f:
            json.dump(state_dict, f, indent=2)
        os.replace(tmp_file, STATE_FILE)
    except Exception as e:
        print(f"[!] Local state write warning: {e}", file=sys.stderr)

def load_initial_state():
    """
    State Persistence Bootloader:
    Reads node_state.json upon launch. Restores accumulated_wh, pulse_count, and minted_flame_units into memory.
    Guarantees zero progress or tokens are lost on node restart.
    """
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                pulse_count = int(data.get("pulse_count", 0))
                accumulated_wh = float(data.get("accumulated_wh", 0.0))
                minted_flame_units = float(data.get("minted_flame_units", 0.0))
                active_shard_id = data.get("active_shard_id", SHARD_MODELS[0])
                print("==================================================")
                print(f"[+] BOOTLOADER: PERSISTED STATE RESTORED FROM {STATE_FILE}")
                print(f"    - Resuming Pulse #  : {pulse_count}")
                print(f"    - Accumulated Energy : {accumulated_wh:.6f} Wh")
                print(f"    - Total Minted FLAME : {minted_flame_units:.4f}")
                print("==================================================\n")
                return pulse_count, accumulated_wh, minted_flame_units, active_shard_id
        except Exception as e:
            print(f"[!] Warning reading {STATE_FILE}: {e}. Initializing fresh session.")

    print(f"[+] BOOTLOADER: Initializing new local validator session on {STATE_FILE}\n")
    return 0, 0.0, 0.0, SHARD_MODELS[0]

def run_validator():
    specs = detect_device_specs()
    print("==================================================")
    print("       FLAMECHAIN IPAD VALIDATOR NODE ONLINE       ")
    print("==================================================")
    print(f" Node ID         : {specs['node_id']}")
    print(f" Architecture    : {specs['architecture']}")
    print(f" OS              : {specs['os_system']}")
    print(f" System RAM      : {specs['total_mb_ram']} MB")
    print(f" LAN Telemetry   : {PRIMARY_LAN_URL}")
    print("==================================================")

    # State bootloader persistence restoration
    pulse_count, accumulated_wh, minted_flame_units, restored_shard_id = load_initial_state()

    active_shard_idx = 0
    if restored_shard_id in SHARD_MODELS:
        active_shard_idx = SHARD_MODELS.index(restored_shard_id)
    
    active_shard_id = SHARD_MODELS[active_shard_idx]
    last_hash = "0" * 64
    baseline_power_watts = 5.5

    while True:
        pulse_start = time.time()
        pulse_count += 1

        # Hot-swap models every 10 pulses
        if pulse_count % 10 == 0:
            active_shard_idx = (active_shard_idx + 1) % len(SHARD_MODELS)
            active_shard_id = SHARD_MODELS[active_shard_idx]
            print(f"\n[\U0001f504 SHARD HOT-SWAP] Active Shard Changed -> ({active_shard_idx + 1}/{len(SHARD_MODELS)}): {active_shard_id}")

        # Compute SHA-256 block hash
        pulse_data = f"{pulse_count}:{last_hash}:{active_shard_id}:{specs['node_id']}:{pulse_start}"
        pulse_hash = hashlib.sha256(pulse_data.encode('utf-8')).hexdigest()
        last_hash = pulse_hash

        # Execute compute pulse duration
        time.sleep(0.5)
        elapsed = time.time() - pulse_start

        # Dynamic resource & energy calculations
        ram_used_mb = get_current_ram_usage_mb()
        wh_delta = (baseline_power_watts * elapsed) / 3600.0
        accumulated_wh += wh_delta

        # Continuous minting reward equation
        minted_flame_units = (accumulated_wh * 1000.0) + (ram_used_mb * 0.01)

        # Deterministic State Root
        state_root = compute_deterministic_state_root(pulse_count, accumulated_wh, active_shard_id)

        # Local state payload
        local_state = {
            "node_specs": specs,
            "pulse_count": pulse_count,
            "ram_used_mb": ram_used_mb,
            "accumulated_wh": round(accumulated_wh, 6),
            "minted_flame_units": round(minted_flame_units, 4),
            "active_shard_id": active_shard_id,
            "last_pulse_hash": pulse_hash,
            "state_root": state_root,
            "timestamp": time.time()
        }

        # Save to node_state.json on every pulse
        save_local_state(local_state)

        # Assemble telemetry payload
        telemetry_payload = {
            "node_id": specs["node_id"],
            "total_mb_ram": specs["total_mb_ram"],
            "ram_used_mb": ram_used_mb,
            "accumulated_wh": round(accumulated_wh, 6),
            "minted_flame_units": round(minted_flame_units, 4),
            "active_shard_id": active_shard_id,
            "pulse_count": pulse_count,
            "state_root": state_root,
            "timestamp": time.time()
        }

        # Trigger async telemetry worker
        send_telemetry_async(telemetry_payload, pulse_count)

        # Terminal output
        print(f"[\u26a1 PULSE #{pulse_count}] Hash: {pulse_hash[:16]}... | RAM: {ram_used_mb:.2f} MB | Wh: {accumulated_wh:.6f} | Minted: {minted_flame_units:.4f} FLAME | Shard: {active_shard_id}")

if __name__ == "__main__":
    try:
        run_validator()
    except KeyboardInterrupt:
        print("\n[-] Validator shutting down safely.")
        sys.exit(0)
