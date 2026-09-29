
import json

import os



STATE_FILE = "flamechain_live_state.json"



def Audit_Mesh():

    if not os.path.exists(STATE_FILE):

        print("[-] State file missing.")

        return

    with open(STATE_FILE, "r") as f:

        state = json.load(f)

    hw = state.get("mesh_node_hardware", {})

    total_wh = state.get("total_wh_metered", 0.0)

    print("==================================================")

    print("      FLAMECHAIN MESH HARDWARE & YIELD METRICS    ")

    print("==================================================")

    print(f"[*] Total Metered Watt-Hours : {total_wh:.6f} Wh")

    print(f"[*] Local Device System RAM  : {hw.get('total_device_ram_gb', 'N/A')} GB")

    print(f"[*] Available System RAM     : {hw.get('available_ram_gb', 'N/A')} GB")

    print(f"[*] Active Model Shards      : {len(state.get('active_model_manifest', []))}")

    print(f"[*] Total Network Accounts   : {len(state.get('account_balances', {}))}")

    print("==================================================")



if __name__ == "__main__":

    Audit_Mesh()

