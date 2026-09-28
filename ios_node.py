import json
import os
import platform
import time
import uuid
import hashlib

STATE_FILE = "global_network_state.json"
TELEMETRY_INTERVAL_SEC = 5
STALE_THRESHOLD_SEC = 30

def generate_hardware_node_id() -> str:
    """Generate a deterministic, persistent node identity based on system hostname and MAC address."""
    hostname = platform.node() or "unknown-host"
    mac_addr = uuid.getnode()
    hardware_fingerprint = f"{hostname}:{mac_addr}"
    hash_digest = hashlib.sha256(hardware_fingerprint.encode('utf-8')).hexdigest()[:12]
    return f"flame-node-{hash_digest}"

def get_system_ram_mb() -> int:
    """Read available system RAM in MB from /proc/meminfo or provide fallback."""
    try:
        with open('/proc/meminfo', 'r') as f:
            for line in f:
                if 'MemTotal' in line:
                    return int(line.split()[1]) // 1024
    except Exception:
        pass
    return 12288  # Galaxy Tab default baseline profile

def read_global_state() -> dict:
    """Load the current multi-modal mesh network state."""
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, 'r') as f:
                return json.load(f)
        except Exception:
            pass
    return {"network": "FlameChain-Mainnet", "nodes": {}}

def write_global_state(state: dict) -> None:
    """Atomically write the network state back to disk."""
    temp_file = f"{STATE_FILE}.tmp"
    with open(temp_file, 'w') as f:
        json.dump(state, f, indent=2)
    os.replace(temp_file, STATE_FILE)

def submit_telemetry(node_id: str) -> None:
    """Update active node metrics and purge stale nodes inactive for over 30 seconds."""
    now = time.time()
    state = read_global_state()
    
    if "nodes" not in state or not isinstance(state["nodes"], dict):
        state["nodes"] = {}

    # 1. Purge stale nodes (> 30 seconds inactive)
    active_nodes = {}
    for n_id, n_data in state["nodes"].items():
        last_seen = n_data.get("last_seen", 0)
        if (now - last_seen) <= STALE_THRESHOLD_SEC:
            active_nodes[n_id] = n_data

    # 2. Add or update current node telemetry
    ram_mb = get_system_ram_mb()
    active_nodes[node_id] = {
        "node_id": node_id,
        "platform": platform.platform(),
        "arch": platform.machine(),
        "ram_mb": ram_mb,
        "watt_hours": 45.0,  # Telemetry baseline reading
        "status": "ACTIVE",
        "last_seen": now
    }

    state["nodes"] = active_nodes
    state["last_pruned_timestamp"] = int(now)
    
    write_global_state(state)

def main():
    node_id = generate_hardware_node_id()
    print(f"[FlameChain Node] Identity locked: {node_id}")
    print(f"[FlameChain Node] Monitoring mesh telemetry loop (interval: {TELEMETRY_INTERVAL_SEC}s)...")
    
    while True:
        try:
            submit_telemetry(node_id)
        except Exception as e:
            print(f"[FlameChain Error] Telemetry update failed: {e}")
        time.sleep(TELEMETRY_INTERVAL_SEC)

if __name__ == '__main__':
    main()
