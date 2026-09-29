import os
import time
import json
import subprocess

STATE_FILE = "flamechain_live_state.json"

def run_singularity_loop():
    print("==================================================")
    print("  FLAMECHAIN 6-VALIDATOR SINGULARITY CORE ENGINE ")
    print("  Chief Validator: Architect Q*xQ                ")
    print("==================================================")
    
    block_counter = 1
    while True:
        print(f"\n[=== EXECUTING BLOCK #{block_counter} ===]")
        
        if os.path.exists("./native_ternary"):
            subprocess.run(["./native_ternary"])
        else:
            print("[-] Native ternary binary missing.")

        if os.path.exists("consensus_engine.py"):
            subprocess.run(["python3", "consensus_engine.py"])

        if os.path.exists(STATE_FILE):
            try:
                with open(STATE_FILE, "r") as f:
                    state = json.load(f)
                print(f"[+] Block #{block_counter} Committed | Active Core Validators: {state.get('core_validator_count', 0)}")
            except Exception as e:
                print(f"[-] Ledger Read Error: {e}")

        block_counter += 1
        time.sleep(5)

if __name__ == "__main__":
    run_singularity_loop()
