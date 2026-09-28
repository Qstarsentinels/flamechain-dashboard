import json
import os
import platform
import time
import uuid
import hashlib
import sys

STATE_FILE = "global_network_state.json"
LOCK_FILE = "node_id.lock"
TELEMETRY_INTERVAL_SEC = 5
STALE_THRESHOLD_SEC = 30

def get_or_create_node_id() -> str:
    """Read node_id from lockfile, or generate using standard MAC address hashing and persist it."""
    if os.path.exists(LOCK_FILE):
        try:
            with open(LOCK_FILE, 'r') as f:
                node_id = f.read().strip()
                if node_id:
                    return node_id
        except Exception as e:
            print(f"[FlameChain Warning] Failed to read {LOCK_FILE}: {e}", file=sys.stderr)

    # Generate standard node ID based on hardware MAC address
    mac_addr = uuid.getnode()
    mac_bytes = str(mac_addr).encode('utf-8')
    hash_digest = hashlib.sha256(mac_bytes).hexdigest()[:12]
    node_id = f"flame-node-{hash_digest}"

    # Write lock file
    try:
        with open(LOCK_FILE, 'w') as f:
            f.write(node_id)
        print(f"[FlameChain] Persisted identity lockfile -> {LOCK_FILE}")
    except Exception as e:
        print(f"[FlameChain Warning] Could not write {LOCK_FILE}: {e}", file=sys.stderr)

    return node_id

def get_system_ram_mb() -> int:
    """Read total system RAM in MB from /proc/meminfo or provide standard tab fallback."""
    try:
        with open('/proc/meminfo', 'r') as f:
            for line in f:
                if 'MemTotal' in line:
                    return int(line.split()[1]) // 1024
    except Exception:
        pass
    return 12288

def read_global_state() -> dict:
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, 'r') as f:
                return json.load(f)
        except Exception:
            pass
    return {"network": "FlameChain-Mainnet-Singularity", "nodes": {}}

def write_global_state(state: dict) -> None:
    temp_file = f"{STATE_FILE}.tmp"
    with open(temp_file, 'w') as f:
        json.dump(state, f, indent=2)
    os.replace(temp_file, STATE_FILE)

def submit_telemetry(node_id: str) -> dict:
    """Prune keys older than 30s and post standard heartbeat telemetry for current node."""
    now = time.time()
    state = read_global_state()

    if "nodes" not in state or not isinstance(state["nodes"], dict):
        state["nodes"] = {}

    # 1. Prune nodes where last_seen > 30 seconds ago
    pruned_nodes = {}
    for n_id, n_data in state["nodes"].items():
        last_seen = n_data.get("last_seen", 0)
        if (now - last_seen) <= STALE_THRESHOLD_SEC:
            pruned_nodes[n_id] = n_data

    # 2. Append/Update this node's heartbeats
    ram_mb = get_system_ram_mb()
    pruned_nodes[node_id] = {
        "node_id": node_id,
        "platform": platform.platform(),
        "arch": platform.machine(),
        "ram_mb": ram_mb,
        "watt_hours": 45.0,
        "status": "ACTIVE",
        "last_seen": now
    }

    state["nodes"] = pruned_nodes
    state["last_updated"] = int(now)
    write_global_state(state)

    return {
        "active_nodes_count": len(pruned_nodes),
        "ram_mb": ram_mb
    }

def main():
    node_id = get_or_create_node_id()
    print(f"[FlameChain Node] Identity locked: {node_id}")
    print(f"[FlameChain Node] Starting pulse telemetry loop every {TELEMETRY_INTERVAL_SEC}s...")

    while True:
        try:
            metrics = submit_telemetry(node_id)
            print(f"[Pulse] Node: {node_id} | Status: ACTIVE | RAM: {metrics['ram_mb']}MB | Total Mesh Nodes: {metrics['active_nodes_count']} | Timestamp: {int(time.time())}", flush=True)
        except Exception as e:
            print(f"[Pulse Error] {e}", file=sys.stderr, flush=True)
        time.sleep(TELEMETRY_INTERVAL_SEC)

if __name__ == '__main__':
    main()
