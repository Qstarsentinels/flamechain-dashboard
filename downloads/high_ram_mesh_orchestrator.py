
import psutil

import json

import time

import os



STATE_FILE = "flamechain_live_state.json"



def calculate_ram_allocation():

    mem = psutil.virtual_memory()

    total_gb = mem.total / (1024**3)

    available_gb = mem.available / (1024**3)

    # Reserve 2GB for Android OS

    usable_ram = max(1.0, available_gb - 2.0)

    # Allocate dynamic RAM limits

    sovereign_llm_ram = round(usable_ram * 0.30, 2)  # 30% for Sovereign router

    flamegpt_ram      = round(usable_ram * 0.50, 2)  # 50% for FlameGPT heavy model

    flamebots_ram     = round(usable_ram * 0.20, 2)  # 20% split across 3 Agents

    return {

        "total_device_ram_gb": round(total_gb, 2),

        "available_ram_gb": round(available_gb, 2),

        "allocations": {

            "Sovereign_LLM": f"{sovereign_llm_ram} GB",

            "FlameGPT": f"{flamegpt_ram} GB",

            "FlameBot_Alpha": f"{round(flamebots_ram/3, 2)} GB",

            "FlameBot_Beta": f"{round(flamebots_ram/3, 2)} GB",

            "FlameBot_Gamma": f"{round(flamebots_ram/3, 2)} GB"

        }

    }



def update_mesh_state():

    alloc = calculate_ram_allocation()

    print("==================================================")

    print("   FLAMECHAIN GALAXY TAB HIGH-RAM ALLOCATOR       ")

    print("==================================================")

    print(json.dumps(alloc, indent=4))

    if os.path.exists(STATE_FILE):

        with open(STATE_FILE, "r") as f:

            state = json.load(f)

        state["mesh_node_hardware"] = alloc

        state["active_agents"] = ["FlameBot_Alpha", "FlameBot_Beta", "FlameBot_Gamma"]

        with open(STATE_FILE, "w") as f:

            json.dump(state, f, indent=4)

        print("[+] Dynamic RAM pools updated in FlameChain Ledger!")



if __name__ == "__main__":

    update_mesh_state()

