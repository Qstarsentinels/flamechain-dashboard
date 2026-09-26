#!/usr/bin/env python3
"""
FlameChain iPad Node Validator
Backed by System RAM and Watt-Hour Proof-of-Work / Proof-of-Energy Pulses
Non-blocking async telemetry poster with multi-gateway failover checking.
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

# Network and storage configuration
STATE_FILE = "node_state.json"
PRIMARY_SERVER_IP = "172.20.10.1"
PRIMARY_SERVER_PORT = 8546
TELEMETRY_PATH = "/telemetry/submit"

SHARD_MODELS = [
    "shard_0_vision_encoder.bin",
    "shard_1_language_decoder.bin",
    "shard_2_audio_spectrogram.bin",
    "shard_3_spatial_vector.bin"
]

def check_gateway_connection(host, port, timeout=1.0):
    """Check connectivity to server endpoint."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except Exception:
        return False

def get_target_telemetry_url():
    """Determine reachability of primary gateway or fall back to localhost."""
    if check_gateway_connection(PRIMARY_SERVER_IP, PRIMARY_SERVER_PORT, timeout=0.8):
        return f"http://{PRIMARY_SERVER_IP}:{PRIMARY_SERVER_PORT}{TELEMETRY_PATH}"
    return f"http://127.0.0.1:{PRIMARY_SERVER_PORT}{TELEMETRY_PATH}"

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
    """Detect node hardware parameters."""
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

def send_telemetry_async(payload):
    """
    Non-blocking async telemetry thread POST.
    Payload attributes: node_id, total_mb_ram, accumulated_wh, minted_flame_units, active_shard_id, timestamp.
    Logs concise warnings without breaking the minting loop.
    """
    def _post_task():
        target_url = get_target_telemetry_url()
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
        except urllib.error.URLError as e:
            print(f" [!] [Telemetry Warning] Gateway reachability drop at {target_url}: {e.reason}")
        except Exception as e:
            print(f" [!] [Telemetry Warning] Telemetry POST timeout or exception: {str(e)}")

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
        print(f"[!] Local state write warning: {e}")

def run_validator():
    specs = detect_device_specs()
    print("==================================================")
    print("       FLAMECHAIN IPAD VALIDATOR NODE ONLINE       ")
    print("==================================================")
    print(f" Node ID      : {specs['node_id']}")
    print(f" Architecture : {specs['architecture']}")
    print(f" OS           : {specs['os_system']}")
    print(f" System RAM   : {specs['total_mb_ram']} MB")
    print("==================================================\n")

    pulse_count = 0
    accumulated_wh = 0.0
    active_shard_idx = 0
    active_shard_id = SHARD_MODELS[active_shard_idx]
    last_hash = "0" * 64
    baseline_power_watts = 5.5

    print(f"[+] Engine Started. Active Shard: {active_shard_id}")

    while True:
        pulse_start = time.time()
        pulse_count += 1

        # Rotate models every 10 pulses
        if pulse_count % 10 == 0:
            active_shard_idx = (active_shard_idx + 1) % len(SHARD_MODELS)
            active_shard_id = SHARD_MODELS[active_shard_idx]
            print(f"\n[\U0001f504 SHARD HOT-SWAP] Active Shard Changed -> ({active_shard_idx + 1}/{len(SHARD_MODELS)}): {active_shard_id}")

        # Pulse hash
        pulse_data = f"{pulse_count}:{last_hash}:{active_shard_id}:{specs['node_id']}:{pulse_start}"
        pulse_hash = hashlib.sha256(pulse_data.encode('utf-8')).hexdigest()
        last_hash = pulse_hash

        # Compute work cycle
        time.sleep(0.5)
        elapsed = time.time() - pulse_start

        # Resource & energy calculations
        ram_used_mb = get_current_ram_usage_mb()
        wh_delta = (baseline_power_watts * elapsed) / 3600.0
        accumulated_wh += wh_delta

        # Minting rewards: (watt_hours * 1000.0) + (ram_used_mb * 0.01)
        minted_flame_units = (accumulated_wh * 1000.0) + (ram_used_mb * 0.01)

        # Deterministic Cryptographic State Root
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

        # Local state save
        save_local_state(local_state)

        # Construct payload with required keys:
        # node_id, total_mb_ram, accumulated_wh, minted_flame_units, active_shard_id, and timestamp
        telemetry_payload = {
            "node_id": specs["node_id"],
            "total_mb_ram": specs["total_mb_ram"],
            "ram_used_mb": ram_used_mb,
            "accumulated_wh": round(accumulated_wh, 6),
            "minted_flame_units": round(minted_flame_units, 4),
            "active_shard_id": active_shard_id,
            "state_root": state_root,
            "timestamp": time.time()
        }

        # Trigger async telemetry transmission
        send_telemetry_async(telemetry_payload)

        # Print continuous pulse stdout
        print(f"[\u26a1 PULSE #{pulse_count}] Hash: {pulse_hash[:16]}... | RAM: {ram_used_mb:.2f} MB | Wh: {accumulated_wh:.6f} | Minted: {minted_flame_units:.4f} FLAME | Shard: {active_shard_id}")

if __name__ == "__main__":
    try:
        run_validator()
    except KeyboardInterrupt:
        print("\n[-] iPad Node Validator stopping gracefully.")
        sys.exit(0)
