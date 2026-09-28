import os
import sys
import json
import time
import hashlib
import platform

NODE_STATE_FILE = "node_state.json"
GLOBAL_STATE_FILE = "global_network_state.json"

WH_RATE_PER_SEC = 0.00003
FLAME_RATE_PER_SEC = 0.1625

LEGACY_STALE_NODES = {
    "test-node-01",
    "node_tab_localhost",
    "ios_ipad_pro_m2_mesh_01",
    "ipad-validator-node"
}

def read_json_file(filepath):
    if not os.path.exists(filepath):
        return {}
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[WARN] Read error for {filepath}: {e}")
        return {}

def write_json_file(filepath, data):
    try:
        tmp_file = f"{filepath}.tmp"
        with open(tmp_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        os.replace(tmp_file, filepath)
        return True
    except Exception as e:
        print(f"[ERROR] Write error for {filepath}: {e}")
        return False

def get_dynamic_node_id():
    arch = platform.machine() or "arm64"
    pid = os.getpid()
    return f"node-{arch}-{pid}"

def audit_initial_state():
    """Verify node_state.json on boot and restore historical token earnings if needed."""
    local_state = read_json_file(NODE_STATE_FILE)
    if not local_state:
        return

    wh_consumed = float(local_state.get("wh_consumed", 0.0))
    flame_minted = float(local_state.get("flame_minted", 0.0))

    if wh_consumed > 0 and flame_minted < (wh_consumed * 1000.0):
        audited_flame = wh_consumed * 1016.216
        local_state["flame_minted"] = round(audited_flame, 6)
        write_json_file(NODE_STATE_FILE, local_state)
        print(
            f"[INFO] AUDITED INITIAL STATE: Restored historical earnings to "
            f"{audited_flame:.6f} FLAME based on {wh_consumed:.6f} Wh"
        )

def submit_telemetry():
    try:
        node_id = get_dynamic_node_id()
        local_state = read_json_file(NODE_STATE_FILE)

        architecture = str(local_state.get("architecture", platform.machine() or "arm64"))
        node_os = str(local_state.get("os", platform.system() or "iOS/Darwin"))
        system_ram_mb = int(local_state.get("system_ram_mb", 4096))
        pulse_count = int(local_state.get("pulse_count", 0))
        wh_consumed = float(local_state.get("wh_consumed", 0.0))
        flame_minted = float(local_state.get("flame_minted", 0.0))
        current_time = float(time.time())
        status = str(local_state.get("status", "ACTIVE"))

        standardized_node_state = {
            "node_id": node_id,
            "architecture": architecture,
            "os": node_os,
            "system_ram_mb": system_ram_mb,
            "pulse_count": pulse_count,
            "wh_consumed": round(wh_consumed, 6),
            "flame_minted": round(flame_minted, 6),
            "last_seen": current_time,
            "timestamp": current_time,
            "status": status
        }

        # Update node_state.json locally
        write_json_file(NODE_STATE_FILE, standardized_node_state)

        # Update global_network_state.json
        global_state = read_json_file(GLOBAL_STATE_FILE)
        if not isinstance(global_state, dict):
            global_state = {}

        if "nodes" not in global_state or not isinstance(global_state["nodes"], dict):
            global_state["nodes"] = {}

        # Purge explicitly requested legacy and stale node keys
        for legacy_key in LEGACY_STALE_NODES:
            global_state["nodes"].pop(legacy_key, None)

        # Store current active dynamic node state
        global_state["nodes"][node_id] = standardized_node_state

        # Recalculate aggregate network totals
        total_wh = 0.0
        total_flame = 0.0
        total_ram_mb = 0

        for n_id, n_data in list(global_state["nodes"].items()):
            if n_id in LEGACY_STALE_NODES:
                global_state["nodes"].pop(n_id, None)
                continue

            if isinstance(n_data, dict):
                total_wh += float(n_data.get("wh_consumed", 0.0))
                total_flame += float(n_data.get("flame_minted", 0.0))
                total_ram_mb += int(n_data.get("system_ram_mb", 0))

        global_state["energy_wh"] = round(total_wh, 6)
        global_state["gross_supply"] = round(total_flame, 6)
        global_state["combined_mesh_memory_gb"] = round(total_ram_mb / 1024.0, 2)
        global_state["last_updated"] = current_time

        write_json_file(GLOBAL_STATE_FILE, global_state)
        return True

    except Exception as e:
        print(f"[WARN] submit_telemetry non-fatal exception: {e}")
        return False

def run_pulse_loop(interval_seconds=5.0):
    node_id = get_dynamic_node_id()
    print(f"[INIT] FlameChain Node Initialized: {node_id}")

    # Boot verification and state audit
    audit_initial_state()

    while True:
        try:
            current_time = time.time()
            local_state = read_json_file(NODE_STATE_FILE)

            last_time = float(local_state.get("timestamp", current_time - interval_seconds))
            delta_time = max(0.001, current_time - last_time)

            delta_wh = delta_time * WH_RATE_PER_SEC
            delta_flame = delta_time * FLAME_RATE_PER_SEC

            current_pulses = int(local_state.get("pulse_count", 0)) + 1
            current_wh = float(local_state.get("wh_consumed", 0.0)) + delta_wh
            current_minted = float(local_state.get("flame_minted", 0.0)) + delta_flame
            system_ram_mb = int(local_state.get("system_ram_mb", 4096))

            # Compute SHA256 Pulse Hash
            raw_hash_payload = f"{node_id}:{current_pulses}:{current_time}:{current_wh:.6f}:{current_minted:.6f}"
            pulse_sha256 = hashlib.sha256(raw_hash_payload.encode("utf-8")).hexdigest()

            # Dynamic Shard Hot-Swap ID
            shard_id = f"SHARD-0{(current_pulses % 4) + 1}-HOTSWAP-ACTIVE"

            # Print full pulse telemetry diagnostic
            print(
                f"[PULSE #{current_pulses}] SHA256: {pulse_sha256[:16]}... | "
                f"RAM: {system_ram_mb} MB | Wh: {current_wh:.6f} (+{delta_wh:.6f}) | "
                f"FLAME: {current_minted:.6f} (+{delta_flame:.6f}) | Shard: {shard_id}"
            )

            updated_state = {
                "node_id": node_id,
                "architecture": platform.machine() or "arm64",
                "os": platform.system() or "iOS/Darwin",
                "system_ram_mb": system_ram_mb,
                "pulse_count": current_pulses,
                "wh_consumed": round(current_wh, 6),
                "flame_minted": round(current_minted, 6),
                "last_seen": current_time,
                "timestamp": current_time,
                "status": "ACTIVE_PROOF_OF_WATT"
            }

            write_json_file(NODE_STATE_FILE, updated_state)

            try:
                submit_telemetry()
            except Exception as telemetry_err:
                print(f"[WARN] Telemetry submit failed: {telemetry_err}")

        except Exception as loop_err:
            print(f"[ERROR] Pulse execution loop exception: {loop_err}")

        time.sleep(interval_seconds)

if __name__ == "__main__":
    audit_initial_state()
    if "--once" in sys.argv:
        submit_telemetry()
    else:
        run_pulse_loop()
