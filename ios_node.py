#!/usr/bin/env python3
"""
FlameChain iOS Resilient Edge Minting Node
Mints cryptographic energy pulses, updates local ledger state (node_state.json),
and attempts transmission to gateway. Falls back to local ledger if offline.
"""

import hashlib
import json
import os
import sys
import time
import urllib.request
import urllib.error

PRIMARY_GATEWAY = "http://172.20.10.1:8546/telemetry/submit"
LOCAL_FALLBACK_GATEWAY = "http://127.0.0.1:8546/telemetry/submit"
NODE_STATE_FILE = "node_state.json"

DEFAULT_NODE_CONFIG = {
    "node_id": "node_iphone_ios",
    "device_model": "iPhone 14 Pro (iOS Bridge)",
    "watt_hours_contributed": 12.45,
    "ram_allocated_mb": 3072.0,
    "active_shards": ["shard_llama3_q4_ios"],
    "minted_balance": 150.0,
    "total_pulses_minted": 0,
    "uncommitted_pulses": [],
    "last_mint_timestamp": 0.0
}

def load_local_node_state():
    if not os.path.exists(NODE_STATE_FILE):
        return DEFAULT_NODE_CONFIG.copy()
    try:
        with open(NODE_STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[!] Warning: Could not read {NODE_STATE_FILE} ({e}). Re-initializing state.")
        return DEFAULT_NODE_CONFIG.copy()

def save_local_node_state(state):
    temp_file = f"{NODE_STATE_FILE}.tmp"
    with open(temp_file, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=4)
    os.replace(temp_file, NODE_STATE_FILE)

def mint_pulse_hash(state):
    now = time.time()
    nonce = state["total_pulses_minted"] + 1
    
    wh_delta = 0.05
    token_delta = 1.25
    
    state["watt_hours_contributed"] = round(state["watt_hours_contributed"] + wh_delta, 4)
    state["minted_balance"] = round(state["minted_balance"] + token_delta, 4)
    state["total_pulses_minted"] += 1
    state["last_mint_timestamp"] = now

    raw_header = f"{state['node_id']}:{now}:{state['watt_hours_contributed']}:{nonce}"
    pulse_hash = hashlib.sha256(raw_header.encode("utf-8")).hexdigest()

    pulse_record = {
        "nonce": nonce,
        "hash": pulse_hash,
        "wh_added": wh_delta,
        "tokens_added": token_delta,
        "timestamp": now
    }

    state["uncommitted_pulses"].append(pulse_record)
    print(f"[⚡] Minted Pulse #{nonce} | Hash: {pulse_hash[:16]}... | +{wh_delta} Wh | Total: {state['minted_balance']} FLAME")
    return pulse_record

def attempt_telemetry_post(state):
    payload = {
        "node_id": state["node_id"],
        "device_model": state["device_model"],
        "watt_hours_contributed": state["watt_hours_contributed"],
        "ram_allocated_mb": state["ram_allocated_mb"],
        "active_shards": state["active_shards"],
        "minted_balance": state["minted_balance"],
        "total_pulses": state["total_pulses_minted"],
        "uncommitted_count": len(state["uncommitted_pulses"])
    }

    encoded_data = json.dumps(payload).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "FlameChain-iOS-ResilientNode/1.0"
    }

    targets = [PRIMARY_GATEWAY, LOCAL_FALLBACK_GATEWAY]
    synced = False

    for target_url in targets:
        print(f"[->] Transmitting telemetry to gateway: {target_url}...")
        req = urllib.request.Request(target_url, data=encoded_data, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=3) as resp:
                if resp.status == 200:
                    body = json.loads(resp.read().decode("utf-8"))
                    print(f"[✔] Gateway Sync SUCCESS ({target_url}): {body.get('message', '200 OK')}")
                    state["uncommitted_pulses"] = []
                    synced = True
                    break
        except urllib.error.URLError as e:
            print(f"[!] Target unreachable ({target_url}): {e.reason}")
        except Exception as e:
            print(f"[!] Transmission error ({target_url}): {str(e)}")

    if not synced:
        print(f"[🔒] Gateway unavailable. Preserving {len(state['uncommitted_pulses'])} pulse(s) in local {NODE_STATE_FILE}.")

    save_local_node_state(state)

def main():
    print("======================================================")
    print("   FlameChain Resilient Edge Node (iOS Engine)       ")
    print("======================================================")
    
    state = load_local_node_state()
    mint_pulse_hash(state)
    attempt_telemetry_post(state)

if __name__ == "__main__":
    main()
