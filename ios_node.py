#!/usr/bin/env python3
"""
FlameChain iPad Node Validator
Backed by System RAM and Watt-Hour Proof-of-Work / Proof-of-Energy Pulses
Non-blocking async telemetry and deterministic cryptographic state root generation.
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

# Network and local configuration
STATE_FILE = "node_state.json"
TELEMETRY_URL = "http://172.20.10.1:8546/telemetry/submit"
SHARD_MODELS = [
    "shard_0_vision_encoder.bin",
    "shard_1_language_decoder.bin",
    "shard_2_audio_spectrogram.bin",
    "shard_3_spatial_vector.bin"
]

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
    """Detect hardware specifications."""
    arch = platform.machine() or platform.processor() or "arm64"
    sys_name = platform.system() or "Darwin"
    node_uuid = str(uuid.uuid5(uuid.NAMESPACE_DNS, socket.gethostname() or "flamechain.ipad.node"))
    
    return {
        "node_id": f"node_{node_uuid[:12]}",
        "architecture": arch,
        "os_system": sys_name,
        "total_ram_mb": get_total_ram_mb(),
        "timestamp_initialized": time.time()
    }

def send_telemetry_async(payload):
    """
    Asynchronous non-blocking telemetry submit handler.
    Fires POST payload to http://172.20.10.1:8546/telemetry/submit with 2-second timeout.
    Catches and logs network errors as non-fatal warnings without interrupting minting loop.
    """
    def _post_task():
        try:
            data = json.dumps(payload).encode('utf-8')
            req = urllib.request.Request(
                TELEMETRY_URL,
                data=data,
                headers={'Content-Type': 'application/json'},
                method='POST'
            )
            with urllib.request.urlopen(req, timeout=2.0) as resp:
                _ = resp.read()
        except urllib.error.URLError as e:
            print(f" [!] [Non-Fatal] Telemetry Network Sync Warning: {e.reason}", file=sys.stderr)
        except Exception as e:
            print(f" [!] [Non-Fatal] Telemetry Sync Timeout/Error: {str(e)}", file=sys.stderr)

    thread = threading.Thread(target=_post_task, daemon=True)
    thread.start()

def compute_deterministic_state_root(pulse_count, accumulated_wh, active_shard_id):
    """
    Calculates deterministic cryptographic state root hash derived directly
    from pulse count, total accumulated watt hours, and active shard identifier.
    """
    raw_payload = f"pulse:{pulse_count}|wh:{accumulated_wh:.6f}|shard:{active_shard_id}"
    return hashlib.sha256(raw_payload.encode('utf-8')).hexdigest()

def save_local_state(state_dict):
    """Atomically write updated local state directly to node_state.json."""
    tmp_file = f"{STATE_FILE}.tmp"
    try:
        with open(tmp_file, "w", encoding="utf-8") as f:
            json.dump(state_dict, f, indent=2)
        os.replace(tmp_file, STATE_FILE)
    except Exception as e:
        print(f"[!] Critical error writing local state file: {e}", file=sys.stderr)

def run_validator():
    specs = detect_device_specs()
    print("==================================================")
    print("       FLAMECHAIN IPAD VALIDATOR INITIALIZED       ")
    print("==================================================")
    print(f" Node ID      : {specs['node_id']}")
    print(f" Architecture : {specs['architecture']}")
    print(f" OS           : {specs['os_system']}")
    print(f" System RAM   : {specs['total_ram_mb']} MB")
    print(f" Endpoint     : {TELEMETRY_URL}")
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

        # Hot-swap shard model every 10 pulses
        if pulse_count % 10 == 0:
            active_shard_idx = (active_shard_idx + 1) % len(SHARD_MODELS)
            active_shard_id = SHARD_MODELS[active_shard_idx]
            print(f"\n[\U0001f504 SHARD HOT-SWAP] Rotating to Shard ({active_shard_idx + 1}/{len(SHARD_MODELS)}): {active_shard_id}")

        # Compute pulse SHA-256 block hash
        pulse_data = f"{pulse_count}:{last_hash}:{active_shard_id}:{specs['node_id']}:{pulse_start}"
        pulse_hash = hashlib.sha256(pulse_data.encode('utf-8')).hexdigest()
        last_hash = pulse_hash

        # Simulate compute loop pulse interval
        time.sleep(0.5)
        elapsed = time.time() - pulse_start

        # Compute dynamic metrics
        ram_used_mb = get_current_ram_usage_mb()
        wh_delta = (baseline_power_watts * elapsed) / 3600.0
        accumulated_wh += wh_delta

        # Minting equation: (watt_hours * 1000.0) + (ram_used_mb * 0.01)
        minted_flame = (accumulated_wh * 1000.0) + (ram_used_mb * 0.01)

        # Generate deterministic state_root hash from pulse_count, accumulated_wh, and active_shard_id
        state_root = compute_deterministic_state_root(pulse_count, accumulated_wh, active_shard_id)

        # Assemble local state record
        local_state = {
            "node_specs": specs,
            "pulse_count": pulse_count,
            "ram_used_mb": ram_used_mb,
            "accumulated_wh": round(accumulated_wh, 6),
            "minted_flame_units": round(minted_flame, 4),
            "active_shard_id": active_shard_id,
            "last_pulse_hash": pulse_hash,
            "state_root": state_root,
            "last_updated": time.time()
        }

        # Write directly to node_state.json on every pulse
        save_local_state(local_state)

        # Prepare and trigger async telemetry submit POST
        telemetry_payload = {
            "node_id": specs["node_id"],
            "ram": ram_used_mb,
            "watt_hours": round(accumulated_wh, 6),
            "shard_id": active_shard_id,
            "minted_flame": round(minted_flame, 4),
            "state_root": state_root,
            "last_seen": time.time()
        }
        send_telemetry_async(telemetry_payload)

        # Log formatted output
        print(f"[\u26a1 PULSE #{pulse_count}] Hash: {pulse_hash[:16]}... | RAM: {ram_used_mb:.2f} MB | Wh: {accumulated_wh:.6f} | Minted: {minted_flame:.4f} FLAME | Shard: {active_shard_id}")

if __name__ == "__main__":
    try:
        run_validator()
    except KeyboardInterrupt:
        print("\n[-] iPad Node shutting down safely.")
        sys.exit(0)
