#!/usr/bin/env python3
"""
FlameChain iPad/iOS Validator Node
Backed by System RAM and Watt-Hour Proof-of-Work / Proof-of-Energy Pulses
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
import urllib.request
import urllib.error

# Global Constants
STATE_FILE = "node_state.json"
TELEMETRY_URL = "http://localhost:8546"
SHARD_MODELS = [
    "shard_0_vision_encoder.bin",
    "shard_1_language_decoder.bin",
    "shard_2_audio_spectrogram.bin",
    "shard_3_spatial_vector.bin"
]

def get_total_ram_bytes():
    """Detect total system memory across Android/Termux, iOS, Linux, and macOS."""
    # Try reading /proc/meminfo (Termux / Android / Linux)
    if os.path.exists("/proc/meminfo"):
        try:
            with open("/proc/meminfo", "r") as f:
                for line in f:
                    if line.startswith("MemTotal:"):
                        parts = line.split()
                        return int(parts[1]) * 1024  # kB to bytes
        except Exception:
            pass

    # Try psutil if available
    try:
        import psutil
        return psutil.virtual_memory().total
    except ImportError:
        pass

    # Default fallback estimate (4 GB)
    return 4 * 1024 * 1024 * 1024

def detect_device_specs():
    """Gather physical node specifications."""
    arch = platform.machine() or platform.processor() or "arm64"
    sys_name = platform.system() or "Darwin"
    node_uuid = str(uuid.uuid5(uuid.NAMESPACE_DNS, socket.gethostname() or "flamechain.node"))
    
    ram_bytes = get_total_ram_bytes()
    ram_mb = round(ram_bytes / (1024 * 1024), 2)

    return {
        "node_id": f"node_{node_uuid[:12]}",
        "architecture": arch,
        "os_system": sys_name,
        "total_ram_mb": ram_mb,
        "timestamp_initialized": time.time()
    }

def send_telemetry_async(payload):
    """Fire-and-forget background thread POST request for network state sync."""
    def _post():
        try:
            data = json.dumps(payload).encode('utf-8')
            req = urllib.request.Request(
                TELEMETRY_URL,
                data=data,
                headers={'Content-Type': 'application/json'},
                method='POST'
            )
            # Short timeout to avoid hanging background threads
            with urllib.request.urlopen(req, timeout=2.0) as resp:
                pass
        except Exception:
            # Non-blocking telemetry: silently swallow network offline / server down errors
            pass

    thread = threading.Thread(target=_post, daemon=True)
    thread.start()

def save_local_state(state):
    """Atomically persist local node state to state file."""
    tmp_file = f"{STATE_FILE}.tmp"
    try:
        with open(tmp_file, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)
        os.replace(tmp_file, STATE_FILE)
    except Exception as e:
        print(f"[!] Warning: Failed to write local state: {e}")

def run_validator():
    specs = detect_device_specs()
    print("==================================================")
    print("       FLAMECHAIN VALIDATOR NODE INITIALIZED       ")
    print("==================================================")
    print(f" Node ID      : {specs['node_id']}")
    print(f" Architecture : {specs['architecture']}")
    print(f" OS           : {specs['os_system']}")
    print(f" System RAM   : {specs['total_ram_mb']} MB")
    print("==================================================\n")

    pulse_count = 0
    watt_hours_consumed = 0.0
    active_shard_idx = 0
    current_shard = SHARD_MODELS[active_shard_idx]
    last_hash = "0" * 64

    # Baseline estimated power draw (Watts) based on node computation profile
    baseline_power_watts = 5.5  # Typical mobile SoC load

    print(f"[+] Starting Minting Engine. Initial Active Shard: {current_shard}")

    while True:
        pulse_start = time.time()
        pulse_count += 1

        # 1. Check Shard Hot-Swap condition (every 10 pulses)
        if pulse_count % 10 == 0:
            active_shard_idx = (active_shard_idx + 1) % len(SHARD_MODELS)
            current_shard = SHARD_MODELS[active_shard_idx]
            print(f"\n[🔄 SHARD HOT-SWAP] Switching to Shard ({active_shard_idx + 1}/{len(SHARD_MODELS)}): {current_shard}")

        # 2. Compute Proof-of-Energy SHA-256 Pulse
        pulse_data = f"{pulse_count}:{last_hash}:{current_shard}:{specs['node_id']}:{pulse_start}"
        pulse_hash = hashlib.sha256(pulse_data.encode('utf-8')).hexdigest()
        last_hash = pulse_hash

        # 3. Simulate work and energy delta calculation
        time.sleep(0.5)  # Pulse duration interval
        elapsed_seconds = time.time() - pulse_start
        watt_hours_delta = (baseline_power_watts * elapsed_seconds) / 3600.0
        watt_hours_consumed += watt_hours_delta

        # 4. Construct current local state object
        node_state = {
            "node_specs": specs,
            "metrics": {
                "pulse_count": pulse_count,
                "watt_hours": round(watt_hours_consumed, 6),
                "active_shard": current_shard,
                "shard_index": active_shard_idx,
                "last_pulse_hash": pulse_hash,
                "last_updated": time.time()
            }
        }

        # 5. Persist state locally on every pulse
        save_local_state(node_state)

        # 6. Non-blocking telemetry update to telemetry server
        telemetry_payload = {
            specs["node_id"]: {
                "specs": specs,
                "metrics": node_state["metrics"]
            }
        }
        send_telemetry_async(telemetry_payload)

        # Logging output
        print(f"[⚡ PULSE #{pulse_count:05d}] Hash: {pulse_hash[:16]}... | Wh: {watt_hours_consumed:.6f} | Shard: {current_shard}")

if __name__ == "__main__":
    try:
        run_validator()
    except KeyboardInterrupt:
        print("\n[-] Validator Node shutdown requested. Exiting cleanly.")
        sys.exit(0)
