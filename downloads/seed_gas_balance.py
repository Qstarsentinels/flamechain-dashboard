
import json

import os



STATE_FILE = "flamechain_live_state.json"



def seed_architect():

    if os.path.exists(STATE_FILE):

        with open(STATE_FILE, "r") as f:

            state = json.load(f)

        balances = state.get("account_balances", {})

        balances["Architect_Q*xQ"] = 100.0  # Seed initial 100 FC

        state["account_balances"] = balances

        with open(STATE_FILE, "w") as f:

            json.dump(state, f, indent=4)

        print("[+] Architect_Q*xQ successfully seeded with 100.0 FC balance!")



if __name__ == "__main__":

    seed_architect()

