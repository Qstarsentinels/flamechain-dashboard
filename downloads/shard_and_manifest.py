
import os

import json

import hashlib



STATE_FILE = "flamechain_live_state.json"

MODEL_PATH = "models/sovereign_0_5b.gguf"

SHARD_DIR = "models/shards"

SHARD_SIZE_MB = 100  # Split into 100MB chunks for mobile nodes



def get_file_hash(filepath):

    hasher = hashlib.sha256()

    with open(filepath, 'rb') as f:

        while chunk := f.read(8192):

            hasher.update(chunk)

    return hasher.hexdigest()



def shard_model():

    if not os.path.exists(MODEL_PATH):

        print("[-] Error: Model file not found. Run load_gguf_model.py first.")

        return



    if not os.path.exists(SHARD_DIR):

        os.makedirs(SHARD_DIR)



    print(f"[*] Sharding GGUF model: {MODEL_PATH} into {SHARD_SIZE_MB}MB blocks...")

    shard_manifest = []

    chunk_size = SHARD_SIZE_MB * 1024 * 1024



    with open(MODEL_PATH, 'rb') as f:

        part_num = 1

        while True:

            data = f.read(chunk_size)

            if not data:

                break

            shard_filename = f"sovereign_shard_{part_num:05d}.gguf"

            shard_path = os.path.join(SHARD_DIR, shard_filename)

            with open(shard_path, 'wb') as shard_file:

                shard_file.write(data)

            shard_hash = get_file_hash(shard_path)

            shard_manifest.append({

                "shard_id": part_num,

                "filename": shard_filename,

                "size_bytes": len(data),

                "sha256": shard_hash

            })

            print(f"[+] Created Shard {part_num}: {shard_filename} ({len(data)} bytes)")

            part_num += 1



    # Update state file with Shard Manifest

    if os.path.exists(STATE_FILE):

        with open(STATE_FILE, "r") as f:

            state = json.load(f)

        state["active_model_manifest"] = shard_manifest

        with open(STATE_FILE, "w") as f:

            json.dump(state, f, indent=4)

        print("[+] Model Shard Manifest registered to FlameChain State Ledger!")



if __name__ == "__main__":

    shard_model()

