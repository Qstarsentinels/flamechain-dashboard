
import time

import subprocess



print("[*] Starting Continuous FlameChain Validator Daemon...")

print("[*] Mining Wh + RAM proofs in background loop...")



try:

    while True:

        subprocess.run(["python3", "local_mesh_worker.py"])

        time.sleep(10)  # Pulse block minting every 10 seconds

except KeyboardInterrupt:

    print("[!] Validator Daemon Stopped.")

