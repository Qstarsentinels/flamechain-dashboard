
import json

import os

import time



STATE_FILE = "flamechain_live_state.json"



def process_agent_mining_block(agent_id, wh_contributed, ram_allocated_gb):

    if not os.path.exists(STATE_FILE):

        initial_state = {

            "total_wh_metered": 10.0,

            "mesh_node_hardware": {"total_device_ram_gb": 3.0},

            "account_balances": {}

        }

        with open(STATE_FILE, "w") as f:

            json.dump(initial_state, f, indent=4)

    with open(STATE_FILE, "r") as f:

        state = json.load(f)

    # Reward Equation: 10 FC per Wh + 5 FC per GB RAM reserved

    block_reward = round((wh_contributed * 10.0) + (ram_allocated_gb * 5.0), 2)

    balances = state.setdefault("account_balances", {})

    balances[agent_id] = round(balances.get(agent_id, 0.0) + block_reward, 2)

    with open(STATE_FILE, "w") as f:

        json.dump(state, f, indent=4)

    print("==================================================")

    print("        AGENT PROOF-OF-WORK MINING ENGINE         ")

    print("==================================================")

    print(f"[+] MINING SUCCESS: {agent_id} mined {block_reward} FC!")

    print(f"    Contribution: {wh_contributed} Wh | {ram_allocated_gb} GB RAM")

    print(f"    New Balance : {balances[agent_id]} FC")

    print("==================================================")



if __name__ == "__main__":

    process_agent_mining_block("FlameBot_Delta", 1.5, 4.0)

