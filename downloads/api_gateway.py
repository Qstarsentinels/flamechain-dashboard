
from flask import Flask, jsonify, request

import json

import os



app = Flask(__name__)

STATE_FILE = "flamechain_live_state.json"



@app.route('/telemetry', methods=['GET'])

def get_telemetry():

    if os.path.exists(STATE_FILE):

        with open(STATE_FILE, 'r') as f:

            data = json.load(f)

            return jsonify({

                "validators_online": data.get("core_validator_count", 0),

                "fc_price_usdt": data.get("telemetry_valuation", {}).get("fc_price_usdt", 0.0),

                "total_wh_metered": data.get("total_wh_metered", 0.0),

                "active_ram_gb": data.get("telemetry_valuation", {}).get("active_mesh_ram_gb", 0.0),

                "latest_proof": data.get("latest_proof", {})

            }), 200

    return jsonify({"error": "Node state uninitialized"}), 500



if __name__ == '__main__':

    print("[*] Launching Mesh Telemetry Gateway on Port 8080...")

    app.run(host='0.0.0.0', port=8080)

