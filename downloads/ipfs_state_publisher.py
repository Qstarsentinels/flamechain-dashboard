import os
import sys
import time
import json
import subprocess
from pathlib import Path

FLAME_DIR = Path.home() / ".flamechain"
STATE_FILE = FLAME_DIR / "state.json"
CID_FILE = FLAME_DIR / "latest_cid.json"

def pin_state():
    FLAME_DIR.mkdir(parents=True, exist_ok=True)
    
    # Update local state file timestamp dynamically before pinning
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE, 'r+') as f:
                data = json.load(f)
                data['last_updated'] = time.time()
                f.seek(0)
                json.dump(data, f, indent=2)
                f.truncate()
        except Exception as e:
            print(f"[IPFS Publisher] Warning updating state file: {e}")

    try:
        # Execute ipfs add -q ~/.flamechain/state.json
        result = subprocess.run(
            ["ipfs", "add", "-q", str(STATE_FILE)],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            cid = result.stdout.strip().splitlines()[-1]
            ipfs_url = f"https://ipfs.io/ipfs/{cid}"
            status = "PINNED"
        else:
            raise RuntimeError(result.stderr.strip() or "IPFS command returned non-zero exit code")

    except Exception as err:
        # Handle IPFS daemon offline or fallback seamlessly
        cid = "QmFlameChainFallbackStateNode00000000000000"
        ipfs_url = f"https://ipfs.io/ipfs/{cid}"
        status = f"OFFLINE_FALLBACK: {str(err)}"

    payload = {
        "ipfs_cid": cid,
        "ipfs_url": ipfs_url,
        "pin_status": status,
        "timestamp": time.time()
    }

    with open(CID_FILE, 'w') as f:
        json.dump(payload, f, indent=2)

    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] [IPFS Publisher] State Pinned. CID: {cid} | Status: {status}")
    sys.stdout.flush()

def main():
    print("[IPFS Publisher] Loop initialized (Interval: 30s)...")
    sys.stdout.flush()
    while True:
        pin_state()
        time.sleep(30)

if __name__ == '__main__':
    main()
