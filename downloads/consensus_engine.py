
import json

import os

import time



STATE_FILE = "flamechain_live_state.json"



# Post-Quantum Dilithium-5 Addresses for the 6 Core Validators

CORE_VALIDATORS = {

    "Architect_Q*xQ": "dilithium5_1arch_qxq_7f8a9b2c3d4e5f6a",

    "Validator_1_North": "dilithium5_1val_north_9a8b7c6d5e4f3a2b",

    "Validator_2_South": "dilithium5_1val_south_1f2e3d4c5b6a7b8c",

    "Validator_3_East": "dilithium5_1val_east_3c4d5e6f7a8b9c0d",

    "Validator_4_West": "dilithium5_1val_west_5e6f7a8b9c0d1e2f",

    "Validator_5_Core": "dilithium5_1val_core_7a8b9c0d1e2f3a4b"

}



def sync_state():

    if not os.path.exists(STATE_FILE):

        state = {

            "core_validator_count": len(CORE_VALIDATORS),

            "chief_validator": "Architect_Q*xQ",

            "architect_address": CORE_VALIDATORS["Architect_Q*xQ"],

            "validator_registry": CORE_VALIDATORS,

            "architect_fee_rate": 0.10,

            "architect_accumulated_fc": 0.0,

            "total_wh_metered": 0.0,

            "active_agents": ["FlameBot_Alpha", "FlameBot_Beta", "FlameBot_Gamma"],

            "dual_llms": ["Ternary_1.58b_Primary", "Ternary_1.58b_Verifier"],

            "last_updated": time.time()

        }

    else:

        try:

            with open(STATE_FILE, "r") as f:

                state = json.load(f)

            state["core_validator_count"] = len(CORE_VALIDATORS)

            state["validator_registry"] = CORE_VALIDATORS

            state["last_updated"] = time.time()

        except Exception:

            return



    with open(STATE_FILE, "w") as f:

        json.dump(state, f, indent=4)



if __name__ == "__main__":

    sync_state()

