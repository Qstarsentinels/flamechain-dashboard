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
        # Dynamically read local node state
        local_state = read_json_file(NODE_STATE_FILE)

        # Standardize node values
        node_id = str(local_state.get("node_id", "ipad-validator-node"))
        architecture = str(local_state.get("architecture", platform.machine() or "arm64"))
        node_os = str(local_state.get("os", platform.system() or "iOS/Darwin"))
        system_ram_mb = int(local_state.get("system_ram_mb", local_state.get("ram_mb", 4096)))
        pulse_count = int(local_state.get("pulse_count", local_state.get("pulses", 0)))
        wh_consumed = float(local_state.get("wh_consumed", local_state.get("watt_hours", local_state.get("wh", 0.0))))
        flame_minted = float(local_state.get("flame_minted", local_state.get("minted_tokens", local_state.get("balance", 0.0))))
        timestamp = float(time.time())
        status = str(local_state.get("status", "ACTIVE"))

        # Construct standardized node state object
        standardized_node_state = {
            "node_id": node_id,
            "architecture": architecture,
            "os": node_os,
            "system_ram_mb": system_ram_mb,
            "pulse_count": pulse_count,
            "wh_consumed": wh_consumed,
            "flame_minted": flame_minted,
            "timestamp": timestamp,
            "status": status
        }

        # 1. Update node_state.json locally BEFORE committing global state
        write_json_file(NODE_STATE_FILE, standardized_node_state)

        # 2. Read global state structure
        global_state = read_json_file(GLOBAL_STATE_FILE)
        if not isinstance(global_state, dict):
            global_state = {}

        if "nodes" not in global_state or not isinstance(global_state["nodes"], dict):
            global_state["nodes"] = {}

        # 3. Write standardized keys into global_network_state.json for this node
        global_state["nodes"][node_id] = standardized_node_state

        # 4. Compute network-wide totals dynamically across all registered nodes
        total_wh = 0.0
        total_flame = 0.0
        total_ram_mb = 0

        for n_id, n_data in global_state["nodes"].items():
            if isinstance(n_data, dict):
                total_wh += float(n_data.get("wh_consumed", n_data.get("wh", 0.0)))
                total_flame += float(n_data.get("flame_minted", n_data.get("minted_tokens", 0.0)))
                total_ram_mb += int(n_data.get("system_ram_mb", n_data.get("ram_mb", 0)))

        global_state["energy_wh"] = round(total_wh, 4)
        global_state["gross_supply"] = round(total_flame, 4)
        global_state["combined_mesh_memory_gb"] = round(total_ram_mb / 1024.0, 2)
        global_state["last_updated"] = timestamp

        # Commit update to global_network_state.json
        success = write_json_file(GLOBAL_STATE_FILE, global_state)
        if success:
            print(f"[INFO] Local and global telemetry state successfully committed for {node_id}")
        return success

    except Exception as e:
        print(f"[ERROR] Telemetry submission error: {e}")
        return False

if __name__ == "__main__":
    submit_telemetry()
