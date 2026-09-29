
import json

import os

import time

from flask import Flask, jsonify, request



app = Flask(__name__)

STATE_FILE = "flamechain_live_state.json"

PEERS_FILE = "active_peers.json"



def get_peers():

    if os.path.exists(PEERS_FILE):

        with open(PEERS_FILE, "r") as f:

            return json.load(f)

    return {}



@app.route('/peer/ping', methods=['POST'])

def register_peer():

    data = request.json or {}

    node_id = data.get("node_id", "Unknown_Agent")

    ram_available_gb = data.get("ram_gb", 0.0)

    device_type = data.get("type", "Human_USBC")  # Human_USBC or AI_Agent



    peers = get_peers()

    peers[node_id] = {

        "last_seen": time.time(),

        "ram_gb": ram_available_gb,

        "type": device_type,

        "status": "ACTIVE"

    }



    with open(PEERS_FILE, "w") as f:

        json.dump(peers, f, indent=4)



    return jsonify({"status": "Registered", "active_peers_count": len(peers)}), 200



@app.route('/mesh/status', methods=['GET'])

def mesh_status():

    peers = get_peers()

    now = time.time()

    # Prune peers inactive for > 60 seconds

    active_peers = {k: v for k, v in peers.items() if now - v["last_seen"] < 60}

    total_mesh_ram = sum(p["ram_gb"] for p in active_peers.values())

    return jsonify({

        "total_active_nodes": len(active_peers),

        "total_mesh_ram_gb": round(total_mesh_ram, 2),

        "connected_peers": active_peers

    }), 200



if __name__ == "__main__":

    print("[*] Deploying Peer Discovery & Mesh Telemetry Server on Port 8082...")

    app.run(host='0.0.0.0', port=8082)

