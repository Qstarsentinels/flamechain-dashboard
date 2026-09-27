import os
import json
import time
import platform

NODE_STATE_FILE = "node_state.json"
GLOBAL_STATE_FILE = "global_network_state.json"

def read_json_file(filepath):
    if not os.path.exists(filepath):
        return {}
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[WARN] Failed to read {filepath}: {e}")
        return {}

def write_json_file(filepath, data):
    try:
        tmp_file = f"{filepath}.tmp"
        with open(tmp_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        os.replace(tmp_file, filepath)
        return True
    except Exception as e:
        print(f"[ERROR] Failed to write {filepath}: {e}")
        return False

def submit_telemetry():
    try:
        # Dynamically read local node_state.json
        local_state = read_json_file(NODE_STATE_FILE)

        # Extract required metrics with safe fallbacks
        node_id = str(local_state.get("node_id", "ipad-validator-node"))
        architecture = str(local_state.get("architecture", platform.machine() or "arm64"))
        node_os = str(local_state.get("os", platform.system() or "iOS/Darwin"))
        system_ram_mb = int(local_state.get("system_ram_mb", local_state.get("ram_mb", 4096)))
        pulse_count = int(local_state.get("pulse_count", local_state.get("pulses", 0)))
        wh_consumed = float(local_state.get("wh_consumed", local_state.get("watt_hours", 0.0)))
        flame_minted = float(local_state.get("flame_minted", local_state.get("balance", 0.0)))
        timestamp = float(local_state.get("timestamp", time.time()))

        node_telemetry = {
            "node_id": node_id,
            "architecture": architecture,
            "os": node_os,
            "system_ram_mb": system_ram_mb,
            "pulse_count": pulse_count,
            "wh_consumed": wh_consumed,
            "flame_minted": flame_minted,
            "timestamp": timestamp,
            "status": local_state.get("status", "ACTIVE")
        }

        # Read existing global network state or initialize
        global_state = read_json_file(GLOBAL_STATE_FILE)
        if not isinstance(global_state, dict):
            global_state = {}

        if "nodes" not in global_state or not isinstance(global_state["nodes"], dict):
            global_state["nodes"] = {}

        # Update specific node entry inside global network state
        global_state["nodes"][node_id] = node_telemetry

        # Dynamically compute global aggregates across all active nodes
        total_wh = 0.0
        total_flame = 0.0
        total_ram_mb = 0

        for n_id, n_data in global_state["nodes"].items():
            if isinstance(n_data, dict):
                total_wh += float(n_data.get("wh_consumed", 0.0))
                total_flame += float(n_data.get("flame_minted", 0.0))
                total_ram_mb += int(n_data.get("system_ram_mb", 0))

        global_state["energy_wh"] = round(total_wh, 4)
        global_state["gross_supply"] = round(total_flame, 4)
        global_state["combined_mesh_memory_gb"] = round(total_ram_mb / 1024.0, 2)
        global_state["last_updated"] = time.time()

        # Commit update to global state file
        success = write_json_file(GLOBAL_STATE_FILE, global_state)
        if success:
            print(f"[INFO] Telemetry successfully synchronized for node: {node_id}")
        return success

    except Exception as e:
        # Non-blocking log to ensure no network or runtime errors break execution
        print(f"[ERROR] Non-fatal exception in submit_telemetry: {e}")
        return False

if __name__ == "__main__":
    submit_telemetry()
