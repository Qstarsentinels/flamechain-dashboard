#!/usr/bin/env python3
"""
FlameChain Local Telemetry Relay Daemon
Continuously monitors local node_state.json for modifications every 10 seconds.
Relays and merges active validator metrics into global_network_state.json
and agent_context.json across local/mesh storage.
Handles disk or network write failures gracefully without stopping execution.
"""

import os
import sys
import time
import json
import threading

NODE_STATE_FILE = "node_state.json"
GLOBAL_STATE_FILE = "global_network_state.json"
AGENT_CONTEXT_FILE = "agent_context.json"
POLL_INTERVAL_SECONDS = 10

def update_agent_context(global_state):
    """Refreshes agent_context.json metrics for AI agents."""
    try:
        nodes_dict = global_state.get("active_nodes", {})
        num_validators = len(nodes_dict)
        total_ram_mb = global_state.get("total_mesh_ram_mb", 0.0)
        gross_supply = global_state.get("total_gross_supply", 0.0)
        total_wh = global_state.get("global_watt_hours", 0.0)

        aggregate_ram_gb = round(total_ram_mb / 1024.0, 4)
        avg_wh = round(total_wh / num_validators, 6) if num_validators > 0 else 0.0

        agent_data = {
            "network_singularity": {
                "total_active_validators": num_validators,
                "aggregate_ram_gb": aggregate_ram_gb,
                "total_minted_flame": round(gross_supply, 4),
                "average_watt_hours": avg_wh,
                "total_network_wh": round(total_wh, 6),
                "last_agent_sync_timestamp": time.time()
            },
            "agents": {
                "FlameGPT": {"status": "ONLINE", "role": "Mesh Query & Natural Language Interface"},
                "Sovereign_LLM": {"status": "ACTIVE", "role": "Shard Consensus & Model Weight Synthesis"},
                "Oracle": {"status": "ONLINE", "role": "Energy Proof Verification & Wh Indexing"},
                "Alchemist": {"status": "ACTIVE", "role": "FLAME Minting & Vault Liquidity Engine"},
                "Sentinel": {"status": "GUARDING", "role": "Network Threat Protection & State Integrity"}
            }
        }

        tmp_agent_file = f"{AGENT_CONTEXT_FILE}.tmp"
        with open(tmp_agent_file, "w", encoding="utf-8") as f:
            json.dump(agent_data, f, indent=2)
        os.replace(tmp_agent_file, AGENT_CONTEXT_FILE)
    except Exception as e:
        print(f"[!] [Relay Error] Failed to update agent context: {e}", file=sys.stderr)

def merge_node_state_into_global(local_data):
    """Merges local node metrics into global_network_state.json."""
    try:
        specs = local_data.get("node_specs", {})
        node_id = specs.get("node_id", "node_local_relay")
        total_mb_ram = float(specs.get("total_mb_ram", 4096.0))

        ram_used_mb = float(local_data.get("ram_used_mb", 128.5))
        accumulated_wh = float(local_data.get("accumulated_wh", 0.0))
        minted_flame_units = float(local_data.get("minted_flame_units", 0.0))
        active_shard_id = local_data.get("active_shard_id", "shard_0_vision_encoder.bin")
        pulse_count = int(local_data.get("pulse_count", 0))
        timestamp = float(local_data.get("timestamp", time.time()))

        global_state = {
            "active_nodes": {},
            "total_active_nodes": 0,
            "total_gross_supply": 0.0,
            "global_watt_hours": 0.0,
            "total_mesh_ram_mb": 0.0,
            "last_updated": time.time()
        }

        if os.path.exists(GLOBAL_STATE_FILE):
            try:
                with open(GLOBAL_STATE_FILE, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                    if isinstance(loaded, dict):
                        global_state.update(loaded)
                        if "active_nodes" not in global_state or not isinstance(global_state["active_nodes"], dict):
                            global_state["active_nodes"] = {}
            except Exception:
                pass

        # Update node record
        global_state["active_nodes"][node_id] = {
            "node_id": node_id,
            "node_specs": specs,
            "ram_used_mb": ram_used_mb,
            "total_mb_ram": total_mb_ram,
            "accumulated_wh": accumulated_wh,
            "minted_flame_units": minted_flame_units,
            "active_shard_id": active_shard_id,
            "pulse_count": pulse_count,
            "timestamp": timestamp
        }

        # Calculate network aggregates
        nodes_list = list(global_state["active_nodes"].values())
        global_state["total_active_nodes"] = len(global_state["active_nodes"])
        global_state["total_gross_supply"] = round(sum(float(n.get("minted_flame_units", 0.0)) for n in nodes_list), 4)
        global_state["global_watt_hours"] = round(sum(float(n.get("accumulated_wh", 0.0)) for n in nodes_list), 6)
        global_state["total_mesh_ram_mb"] = round(sum(float(n.get("total_mb_ram", 0.0)) for n in nodes_list), 2)
        global_state["last_updated"] = time.time()

        # Atomic write back to global_network_state.json
        tmp_file = f"{GLOBAL_STATE_FILE}.tmp"
        with open(tmp_file, "w", encoding="utf-8") as f:
            json.dump(global_state, f, indent=2)
        os.replace(tmp_file, GLOBAL_STATE_FILE)

        # Refresh agent context
        update_agent_context(global_state)

        print(f"[🔄 RELAY SYNC] Merged Node '{node_id}' | Pulse #{pulse_count} | Wh: {accumulated_wh:.6f} | Flame: {minted_flame_units:.4f}")

    except Exception as e:
        print(f"[!] [Relay Error] Failed merging node state into global state: {e}", file=sys.stderr)

def run_relay_daemon():
    print("==================================================")
    print("      FLAMECHAIN TELEMETRY RELAY DAEMON          ")
    print("==================================================")
    print(f" Watching File : {NODE_STATE_FILE}")
    print(f" Target File   : {GLOBAL_STATE_FILE}")
    print(f" Interval      : {POLL_INTERVAL_SECONDS}s")
    print("==================================================\n")

    last_mtime = 0.0

    while True:
        try:
            if os.path.exists(NODE_STATE_FILE):
                current_mtime = os.path.getmtime(NODE_STATE_FILE)
                if current_mtime > last_mtime:
                    last_mtime = current_mtime
                    try:
                        with open(NODE_STATE_FILE, "r", encoding="utf-8") as f:
                            local_data = json.load(f)
                        merge_node_state_into_global(local_data)
                    except json.JSONDecodeError:
                        print(f"[!] [Relay Warning] {NODE_STATE_FILE} currently locked or half-written. Retrying next cycle.")
                    except Exception as e:
                        print(f"[!] [Relay Warning] Read error on {NODE_STATE_FILE}: {e}")
            else:
                print(f"[!] [Relay Waiting] {NODE_STATE_FILE} not found yet. Retrying in {POLL_INTERVAL_SECONDS}s...")

        except Exception as e:
            # Top-level exception catch ensures daemon never crashes on system drops
            print(f"[!] [Relay Top-Level Warning] Cycle exception caught: {e}", file=sys.stderr)

        time.sleep(POLL_INTERVAL_SECONDS)

if __name__ == "__main__":
    try:
        run_relay_daemon()
    except KeyboardInterrupt:
        print("\n[-] Telemetry Relay Daemon stopping gracefully.")
        sys.exit(0)
