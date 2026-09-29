
import json

import os



STATE_FILE = "flamechain_live_state.json"



def deposit_liquidity(provider_id, usdt_amount):

    if os.path.exists(STATE_FILE):

        with open(STATE_FILE, "r") as f:

            state = json.load(f)

        vaults = state.get("liquidity_vaults", {"USDT_POOL": 0.0, "LP_PROVIDERS": {}})

        vaults["USDT_POOL"] += usdt_amount

        vaults["LP_PROVIDERS"][provider_id] = vaults["LP_PROVIDERS"].get(provider_id, 0.0) + usdt_amount

        state["liquidity_vaults"] = vaults

        with open(STATE_FILE, "w") as f:

            json.dump(state, f, indent=4)

        print(f"[+] Liquidity Added: {usdt_amount} USDT deposited by {provider_id}!")

        print(f"    Total USDT Vault Pool: {vaults['USDT_POOL']} USDT")



if __name__ == "__main__":

    deposit_liquidity("Human_LP_Validator_01", 500.0)

