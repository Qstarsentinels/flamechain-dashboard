
import json

import os

import hashlib



STATE_FILE = "flamechain_live_state.json"



def register_agent(agent_name, initial_faucet_fc=0.01):

    # Generate a deterministic wallet address from agent name

    wallet_address = "FC_" + hashlib.sha256(agent_name.encode()).hexdigest()[:12]

    if os.path.exists(STATE_FILE):

        with open(STATE_FILE, "r") as f:

            state = json.load(f)

        balances = state.get("account_balances", {})

        if wallet_address not in balances:

            # Grant small starter faucet so new agent can pay initial gas fees

            balances[wallet_address] = initial_faucet_fc

            state["account_balances"] = balances

            with open(STATE_FILE, "w") as f:

                json.dump(state, f, indent=4)

            print(f"[+] Wallet Created for {agent_name}!")

            print(f"    Address: {wallet_address}")

            print(f"    Starter Balance: {initial_faucet_fc} FC")

        else:

            print(f"[*] Wallet already exists for {agent_name}: {wallet_address} (Balance: {balances[wallet_address]} FC)")



if __name__ == "__main__":

    register_agent("FlameBot_Delta")

