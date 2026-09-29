
import json

import os

import time

from flask import Flask, request, jsonify



app = Flask(__name__)

STATE_FILE = "flamechain_live_state.json"



@app.route('/mesh/inference', methods=['POST'])

def process_inference():

    # Force JSON parsing regardless of header quirks

    data = request.get_json(force=True, silent=True) or {}

    prompt = data.get("prompt", "Default Mesh Task")

    agent = data.get("agent", "FlameBot_Alpha")

    gas_fee = float(data.get("gas_fee_fc", 0.001))



    if os.path.exists(STATE_FILE):

        with open(STATE_FILE, "r") as f:

            state = json.load(f)

        balances = state.get("account_balances", {})

        architect_bal = balances.get("Architect_Q*xQ", 0.0)

        if architect_bal < gas_fee:

            return jsonify({"error": "Insufficient FC balance"}), 400

        balances["Architect_Q*xQ"] = round(architect_bal - gas_fee, 6)

        state["architect_accumulated_fc"] = round(state.get("architect_accumulated_fc", 0.0) + gas_fee, 6)

        state["account_balances"] = balances

        with open(STATE_FILE, "w") as f:

            json.dump(state, f, indent=4)



    return jsonify({

        "status": "SUCCESS",

        "agent": agent,

        "gas_deducted": gas_fee,

        "response": f"[{agent} Multi-Modal Execution]: Task '{prompt}' processed using active GGUF shards."

    }), 200



if __name__ == "__main__":

    print("[+] Launching Fixed FlameChain Inference Node on Port 8083...")

    app.run(host='0.0.0.0', port=8083)




@app.route('/mesh/swap', methods=['POST'])

def handle_swap():

    data = request.get_json(force=True, silent=True) or {}

    agent = data.get("agent", "Anonymous_Agent")

    amount = float(data.get("amount", 10.0))

    source_asset = data.get("source_asset", "USDT")

    target_asset = data.get("target_asset", "USDC")

    fc_settled = round(amount * 10.0, 2) # $1.00 USDT = 10 FC

    return jsonify({

        "status": "SWAP_SETTLED",

        "agent": agent,

        "input": f"{amount} {source_asset}",

        "flamechain_settlement": f"{fc_settled} FC",

        "output_released": f"{amount * 0.995} {target_asset}"

    }), 200

