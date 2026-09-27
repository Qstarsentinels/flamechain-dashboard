import os
import sys
import json
import time
import platform

NODE_STATE_FILE = "node_state.json"
GLOBAL_STATE_FILE = "global_network_state.json"

DELTA_WH = 0.000150
DELTA_MINTED = 0.812500

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
        timestamp = float(time.time())
        status = str(local_state.get("status", "ACTIVE"))

        standardized_node_state = {
            "node_id": node_id,
            "architecture": architecture,
            "os": node_os,
            "system_ram_mb": system_ram_mb,
            "pulse_count": pulse_count,
            "wh_consumed": round(wh_consumed, 6),
            "flame_minted": round(flame_minted, 6),
            "timestamp": timestamp,
            "status": status
        }

        # Save local node state
        write_json_file(NODE_STATE_FILE, standardized_node_state)

        # Sync global network state
        global_state = read_json_file(GLOBAL_STATE_FILE)
        if not isinstance(global_state, dict):
            global_state = {}

        if "nodes" not in global_state or not isinstance(global_state["nodes"], dict):
            global_state["nodes"] = {}

        global_state["nodes"][node_id] = standardized_node_state

        # Recalculate totals
        total_wh = 0.0
        total_flame = 0.0
        total_ram_mb = 0

        for n_id, n_data in global_state["nodes"].items():
            if isinstance(n_data, dict):
                total_wh += float(n_data.get("wh_consumed", 0.0))
                total_flame += float(n_data.get("flame_minted", 0.0))
                total_ram_mb += int(n_data.get("system_ram_mb", 0))

        global_state["energy_wh"] = round(total_wh, 6)
        global_state["gross_supply"] = round(total_flame, 6)
        global_state["combined_mesh_memory_gb"] = round(total_ram_mb / 1024.0, 2)
        global_state["last_updated"] = timestamp

        write_json_file(GLOBAL_STATE_FILE, global_state)
        print(f"[SYNC] Telemetry updated for {node_id} (Pulses: {pulse_count}, Wh: {wh_consumed:.6f}, FLAME: {flame_minted:.6f})")
        return True

    except Exception as e:
        # Non-blocking catch to ensure run_pulse_loop is never interrupted
        print(f"[WARN] submit_telemetry failed non-fatally: {e}")
        return False

def run_pulse_loop(interval_seconds=5.0):
    node_id = get_dynamic_node_id()
    print(f"[INIT] Starting FlameChain Proof-of-Watt loop for {node_id}")

    while True:
        try:
            local_state = read_json_file(NODE_STATE_FILE)

            current_pulses = int(local_state.get("pulse_count", 0)) + 1
            current_wh = float(local_state.get("wh_consumed", 0.0)) + DELTA_WH
            current_minted = float(local_state.get("flame_minted", 0.0)) + DELTA_MINTED

            updated_state = {
                "node_id": node_id,
                "architecture": platform.machine() or "arm64",
                "os": platform.system() or "iOS/Darwin",
                "system_ram_mb": int(local_state.get("system_ram_mb", 4096)),
                "pulse_count": current_pulses,
                "wh_consumed": round(current_wh, 6),
                "flame_minted": round(current_minted, 6),
                "timestamp": time.time(),
                "status": "ACTIVE_PROOF_OF_WATT"
            }

            write_json_file(NODE_STATE_FILE, updated_state)

            # Telemetry submission with resilient execution
            try:
                submit_telemetry()
            except Exception as telemetry_err:
                print(f"[WARN] Telemetry execution exception caught: {telemetry_err}")

        except Exception as loop_err:
            print(f"[ERROR] Exception inside run_pulse_loop: {loop_err}")

        time.sleep(interval_seconds)

if __name__ == "__main__":
    if "--once" in sys.argv:
        submit_telemetry()
    else:
        run_pulse_loop()
