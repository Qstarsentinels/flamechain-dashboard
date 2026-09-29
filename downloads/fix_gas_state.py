
import json

import os



STATE_FILE = "flamechain_live_state.json"



def seed_all_balances():

    if os.path.exists(STATE_FILE):

        with open(STATE_FILE, "r") as f:

            state = json.load(f)

        balances = state.get("account_balances", {})

        # Fund key system accounts

        balances["Architect_Q*xQ"] = 1000.0

        balances["Local_Validator_01"] = 500.0

        balances["FlameBot_Alpha"] = 100.0

        balances["FlameBot_Beta"] = 100.0

        balances["FlameBot_Gamma"] = 100.0

        state["account_balances"] = balances

        with open(STATE_FILE, "w") as f:

            json.dump(state, f, indent=4)

        print("[+] All FlameChain system accounts successfully seeded with FC gas tokens!")



if __name__ == "__main__":

    seed_all_balances()

