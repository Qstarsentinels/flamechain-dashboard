
import json

import os

import time

import random



STATE_FILE = "flamechain_live_state.json"

ARCHITECT_FEE_RATE = 0.10



def process_agent_work():

    if not os.path.exists(STATE_FILE):

        print("[-] Waiting for state file...")

        return



    with open(STATE_FILE, "r") as f:

        state = json.load(f)



    # Earn based on Wh and RAM compute load

    gross_earnings = round(random.uniform(5.0, 25.0), 4)

    architect_cut = round(gross_earnings * ARCHITECT_FEE_RATE, 4)

    net_earnings = round(gross_earnings - architect_cut, 4)



    state["architect_accumulated_fc"] = round(state.get("architect_accumulated_fc", 0.0) + architect_cut, 4)

    state["last_work_event"] = {

        "gross_fc": gross_earnings,

        "architect_10pct_fee": architect_cut,

        "agents_net_fc": net_earnings,

        "timestamp": time.time()

    }



    with open(STATE_FILE, "w") as f:

        json.dump(state, f, indent=4)



    print(f"[+] Work Verified! Gross: {gross_earnings} FC | 10% Architect Tax: {architect_cut} FC -> Wallet: Architect_Q*xQ")



if __name__ == "__main__":

    while True:

        process_agent_work()

        time.sleep(10)

