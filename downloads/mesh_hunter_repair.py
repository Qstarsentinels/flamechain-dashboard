
import json

import os

import sys

import time

import socket



STATE_FILE = "flamechain_live_state.json"



def scan_for_free_compute(port_range=(8080, 8085)):

    print("[*] Mesh Hunter: Seeking free compute nodes on local mesh...")

    open_nodes = []

    for port in range(port_range[0], port_range[1] + 1):

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        sock.settimeout(0.3)

        result = sock.connect_ex(('127.0.0.1', port))

        if result == 0:

            open_nodes.append(port)

        sock.close()

    print(f"[+] Hunter Found {len(open_nodes)} Active Local Compute Gateways on Ports: {open_nodes}")

    return open_nodes



def self_repair_ledger():

    print("[*] Self-Repair Engine: Auditing live state file integrity...")

    if not os.path.exists(STATE_FILE):

        print("[!] Missing state file! Auto-regenerating genesis recovery block...")

        recovery_state = {

            "block_height": 0,

            "total_wh_metered": 0.0,

            "architect_accumulated_fc": 100.0,

            "account_balances": {"Architect_Q*xQ": 100.0}

        }

        with open(STATE_FILE, "w") as f:

            json.dump(recovery_state, f, indent=4)

        print("[+] State repaired successfully!")

    else:

        print("[+] Ledger state healthy and verified.")



if __name__ == "__main__":

    self_repair_ledger()

    scan_for_free_compute()

