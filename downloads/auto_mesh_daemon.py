
import time

import subprocess



print("==================================================")

print("   FLAMECHAIN AGI MAINNET CONTINUOUS VALIDATOR    ")

print("==================================================")



while True:

    try:

        # Run local hardware metering & mint block rewards

        subprocess.run(["python3", "local_mesh_worker.py"])

        # Perform mesh peer ping

        subprocess.run(["python3", "enforce_gas_rules.py"])

        time.sleep(10)

    except KeyboardInterrupt:

        print("[!] Stopping Miner Daemon...")

        break

