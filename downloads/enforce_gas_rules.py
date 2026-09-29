
import json

import os



STATE_FILE = "flamechain_live_state.json"

GAS_FEE_FC = 0.001



def execute_transaction(sender_address="Architect_Q*xQ"):

    if not os.path.exists(STATE_FILE):

        print("[-] State file missing.")

        return False

    with open(STATE_FILE, "r") as f:

        state = json.load(f)

    balances = state.get("account_balances", {})

    sender_bal = balances.get(sender_address, 0.0)

    if sender_bal < GAS_FEE_FC:

        print(f"[-] Transaction Failed: Insufficient FC for gas fee ({GAS_FEE_FC} FC required).")

        return False

    # Deduct Gas Fee and move to accumulated pool

    balances[sender_address] = round(sender_bal - GAS_FEE_FC, 6)

    state["architect_accumulated_fc"] = round(state.get("architect_accumulated_fc", 0.0) + GAS_FEE_FC, 6)

    state["account_balances"] = balances

    with open(STATE_FILE, "w") as f:

        json.dump(state, f, indent=4)

    print(f"[+] Transaction Passed! Gas Fee of {GAS_FEE_FC} FC deducted from {sender_address}.")

    return True



if __name__ == "__main__":

    execute_transaction("Architect_Q*xQ")

