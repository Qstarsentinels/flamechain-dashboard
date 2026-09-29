
import json

import os

from flask import Flask, jsonify



app = Flask(__name__)

STATE_FILE = "flamechain_live_state.json"



@app.route('/', methods=['GET'])

def ledger_explorer():

    if os.path.exists(STATE_FILE):

        with open(STATE_FILE, "r") as f:

            state = json.load(f)

        return jsonify({

            "network_name": "FlameChain AGI Mainnet",

            "backing_asset": "Watt-Hours (Wh) + RAM (GB)",

            "network_status": "ONLINE",

            "ledger_state": state

        }), 200

    return jsonify({"error": "Ledger state not found"}), 404



if __name__ == "__main__":

    print("[+] Deploying Public Mesh Explorer on Port 8084...")

    app.run(host='0.0.0.0', port=8084)

