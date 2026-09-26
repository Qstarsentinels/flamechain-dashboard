#!/usr/bin/env python3
"""
FlameChain iPad Node Validator
Backed by System RAM and Watt-Hour Proof-of-Work / Proof-of-Energy Pulses
Configurable telemetry gateway with fallback snapshot persistence in local_mesh_telemetry.json.
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

# Network and local storage configuration
STATE_FILE = "node_state.json"
FALLBACK_TELEMETRY_FILE = "local_mesh_telemetry.json"
DEFAULT_GATEWAY = "http://172.20.10.1:8546/telemetry/submit"

SHARD_MODELS = [
    "shard_0_vision_encoder.bin",
    "shard_1_language_decoder.bin",
    "shard_2_audio_spectrogram.bin",
    "shard_3_spatial_vector.bin"
]

def get_telemetry_url():
    """Retrieve telemetry URL from environment variable or default to 172.20.10.1:8546."""
    env_url = os.environ.get("GATEWAY_URL")
    if env_url:
        if not env_url.startswith("http://") and not env_url.startswith("https://"):
            env_url = f"http://{env_url}"
        if "/telemetry/submit" not in env_url:
            env_url = env_url.rstrip("/") + "/telemetry/submit"
        return env_url
    return DEFAULT_GATEWAY

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
    """Get current resident memory usage in MB."""
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
    """Detect hardware parameters."""
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

def save_fallback_telemetry(payload):
    """
    Saves fallback telemetry snapshot directly into local_mesh_telemetry.json
    when HTTP gateway POST fails or times out.
    """
    tmp_file = f"{FALLBACK_TELEMETRY_FILE}.tmp"
    try:
        fallback_data = {
            "node_id": payload.get("node_id"),
            "total_mb_ram": payload.get("total_mb_ram"),
            "active_shard_id": payload.get("active_shard_id"),
            "minted_flame_units": payload.get("minted_flame_units"),
            "pulse_count": payload.get("pulse_count"),
            "accumulated_wh": payload.get("accumulated_wh"),
            "ram_used_mb": payload.get("ram_used_mb"),
            "state_root": payload.get("state_root"),
            "timestamp": payload.get("timestamp", time.time()),
            "offline_snapshot": True
        }
        with open(tmp_file, "w", encoding="utf-8") as f:
            json.dump(fallback_data, f, indent=2)
        os.replace(tmp_file, FALLBACK_TELEMETRY_FILE)
    except Exception as e:
        print(f" [!] Failed writing fallback telemetry snapshot: {e}", file=sys.stderr)

def send_telemetry_async(payload):
    """
    Non-blocking async telemetry thread POST.
    Reads URL from GATEWAY_URL environment or default 172.20.10.1:8546.
    On network failure/timeout, writes fallback snapshot into local_mesh_telemetry.json.
    """
    def _post_task():
        target_url = get_telemetry_url()
        try:
            data = json.dumps(payload).encode('utf-8')
            req = urllib.request.Request(
                target_url,
                data=data,
                headers={'Content-Type': 'application/json'},
                method='POST'
            )
            with urllib.request.urlopen(req, timeout=2.0) as resp:
                _ = resp.read()
        except (urllib.error.URLError, TimeoutError, socket.timeout) as e:
            print(f" [!] [Gateway Offline/Timeout] Saving local snapshot: {target_url} -> local_mesh_telemetry.json")
            save_fallback_telemetry(payload)
        except Exception as e:
            print(f" [!] [Telemetry Exception] {str(e)} -> Writing fallback snapshot")
            save_fallback_telemetry(payload)

    thread = threading.Thread(target=_post_task, daemon=True)
    thread.start()

def compute_deterministic_state_root(pulse_count, accumulated_wh, active_shard_id):
    """Calculates state_root hash derived from pulse attributes."""
    raw_payload = f"pulse:{pulse_count}|wh:{accumulated_wh:.6f}|shard:{active_shard_id}"
    return hashlib.sha256(raw_payload.encode('utf-8')).hexdigest()

def save_local_state(state_dict):
    """Atomically persist state to disk."""
    tmp_file = f"{STATE_FILE}.tmp"
    try:
        with open(tmp_file, "w", encoding="utf-8") as f:
            json.dump(state_dict, f, indent=2)
        os.replace(tmp_file, STATE_FILE)
    except Exception as e:
        print(f"[!] Local state write warning: {e}", file=sys.stderr)

def load_initial_state():
    """Restores session state from node_state.json if available."""
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                pulse_count = int(data.get("pulse_count", 0))
                accumulated_wh = float(data.get("accumulated_wh", 0.0))
                minted_flame_units = float(data.get("minted_flame_units", 0.0))
                active_shard_id = data.get("active_shard_id", SHARD_MODELS[0])
                print(f"[+] RESTORED PREVIOUS STATE from {STATE_FILE}:")
                print(f"    - Pulse #            : {pulse_count}")
                print(f"    - Accumulated Wh     : {accumulated_wh:.6f}")
                print(f"    - Minted FLAME       : {minted_flame_units:.4f}\n")
                return pulse_count, accumulated_wh, minted_flame_units, active_shard_id
        except Exception as e:
            print(f"[!] Error loading {STATE_FILE}: {e}. Starting fresh session.")

    print(f"[+] Initializing fresh session state on {STATE_FILE}\n")
    return 0, 0.0, 0.0, SHARD_MODELS[0]

def run_validator():
    specs = detect_device_specs()
    gateway_target = get_telemetry_url()
    print("==================================================")
    print("       FLAMECHAIN IPAD VALIDATOR NODE ONLINE       ")
    print("==================================================")
    print(f" Node ID      : {specs['node_id']}")
    print(f" Architecture : {specs['architecture']}")
    print(f" OS           : {specs['os_system']}")
    print(f" System RAM   : {specs['total_mb_ram']} MB")
    print(f" Gateway URL  : {gateway_target}")
    print("==================================================")

    # Restore session state
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

        # SHA-256 block hash
        pulse_data = f"{pulse_count}:{last_hash}:{active_shard_id}:{specs['node_id']}:{pulse_start}"
        pulse_hash = hashlib.sha256(pulse_data.encode('utf-8')).hexdigest()
        last_hash = pulse_hash

        # Pulse duration
        time.sleep(0.5)
        elapsed = time.time() - pulse_start

        # Compute dynamic resource & energy metrics
        ram_used_mb = get_current_ram_usage_mb()
        wh_delta = (baseline_power_watts * elapsed) / 3600.0
        accumulated_wh += wh_delta

        # Minting rewards calculation
        minted_flame_units = (accumulated_wh * 1000.0) + (ram_used_mb * 0.01)

        # State root computation
        state_root = compute_deterministic_state_root(pulse_count, accumulated_wh, active_shard_id)

        # Local state structure
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

        # Save to local node_state.json
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
        send_telemetry_async(telemetry_payload)

        # Stdout logging
        print(f"[\u26a1 PULSE #{pulse_count}] Hash: {pulse_hash[:16]}... | RAM: {ram_used_mb:.2f} MB | Wh: {accumulated_wh:.6f} | Minted: {minted_flame_units:.4f} FLAME | Shard: {active_shard_id}")

if __name__ == "__main__":
    try:
        run_validator()
    except KeyboardInterrupt:
        print("\n[-] Validator shutting down safely.")
        sys.exit(0)
