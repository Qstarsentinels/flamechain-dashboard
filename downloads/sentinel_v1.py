import time
import shutil
import os

# --- ARCHITECT SCOPED PATHS ---
SOURCE = os.path.expanduser("~/storage/dcim/TeslaApp")
DESTINATION = os.path.expanduser("~/storage/downloads/Sentry_Sanctuary")

def defend_sanctuary():
    print("🛡️ SENTINEL ACTIVE: Monitoring Mobile-Synced Buffer...")

    # Failsafe: Create the local architecture on the tablet now
    for path in [SOURCE, DESTINATION]:
        if not os.path.exists(path):
            try:
                os.makedirs(path)
                print(f"📁 Initialized path: {path}")
            except Exception as e:
                print(f"❌ Initialization Error: {e}")

    while True:
        if os.path.exists(SOURCE):
            files = [f for f in os.listdir(SOURCE) if f.endswith('.mp4')]
            if files:
                print(f"📦 PROTECTING: Moving {len(files)} shards to permanent Sanctuary...")
                for f in files:
                    try:
                        shutil.move(os.path.join(SOURCE, f), os.path.join(DESTINATION, f))
                    except:
                        pass
            else:
                # This is the "Safe State" while you are in your apartment
                print("[!] Heartbeat Coherent. Sanctuary is empty/safe.")
        else:
            print("⚠️ WARNING: Sync Bridge Offline. (Expected until you are at the vehicle).")

        time.sleep(60)

if __name__ == "__main__":
    defend_sanctuary()
