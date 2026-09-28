import os
import json
import time
import logging
import hashlib
import urllib.request
import urllib.error

TELEMETRY_ENDPOINT = "http://127.0.0.1:8080/api/telemetry"
TELEMETRY_TIMEOUT_SEC = 2.0
STATE_FILE = "node_state.json"

IPFS_GATEWAY_FALLBACKS = [
    "https://ipfs.io/ipns/k51qzi5uqu5dl11flamechain_state.json",
    "https://gateway.pinata.cloud/ipfs/QmFlameChainGlobalStateFallback",
    "https://cloudflare-ipfs.com/ipfs/QmFlameChainGlobalStateFallback",
    "https://dweb.link/ipfs/QmFlameChainGlobalStateFallback"
]

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


class FlameChainNode:
    def __init__(self):
        self.node_id = "ipad-edge-alpha-01"
        self.watt_hours = 0.0
        self.flame_tokens = 0.0
        self.available_ram_mb = 3420
        self.active_shards = ["shard_llama3_8b_layer_12_16"]
        self.mesh_role = "inference_worker"

    def to_dict(self) -> dict:
        return {
            "node_id": self.node_id,
            "watt_hours": self.watt_hours,
            "flame_tokens": self.flame_tokens,
            "available_ram_mb": self.available_ram_mb,
            "active_shards": self.active_shards,
            "mesh_role": self.mesh_role
        }

    def fetch_ipfs_state(self) -> dict:
        for gateway_url in IPFS_GATEWAY_FALLBACKS:
            try:
                logging.info(f"Auditing IPFS/IPNS gateway: {gateway_url}")
                req = urllib.request.Request(
                    gateway_url,
                    headers={"User-Agent": "FlameChain-EdgeNode/1.0"}
                )
                with urllib.request.urlopen(req, timeout=2.0) as resp:
                    if resp.status == 200:
                        payload = json.loads(resp.read().decode("utf-8"))
                        logging.info(f"Successfully retrieved gateway balance state from {gateway_url}")
                        return payload
            except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError, Exception) as err:
                logging.debug(f"Gateway lookup bypass for {gateway_url}: {err}")
                continue
        return {}

    def audit_initial_state(self) -> dict:
        logging.info("Starting initial state audit across local storage and IPFS/IPNS mesh...")
        
        highest_wh = float(self.watt_hours)
        highest_tokens = float(self.flame_tokens)

        if os.path.exists(STATE_FILE):
            try:
                with open(STATE_FILE, "r") as f:
                    local_state = json.load(f)
                    highest_wh = max(highest_wh, float(local_state.get("watt_hours", 0.0)))
                    highest_tokens = max(highest_tokens, float(local_state.get("flame_tokens", 0.0)))
                    logging.info(f"Local state evaluated: Wh={highest_wh:.6f}, Tokens={highest_tokens:.6f}")
            except (json.JSONDecodeError, OSError, ValueError) as err:
                logging.warning(f"Could not read local {STATE_FILE}: {err}")

        ipfs_state = self.fetch_ipfs_state()
        if ipfs_state:
            try:
                remote_wh = float(ipfs_state.get("watt_hours", 0.0))
                remote_tokens = float(ipfs_state.get("flame_tokens", 0.0))
                highest_wh = max(highest_wh, remote_wh)
                highest_tokens = max(highest_tokens, remote_tokens)
                logging.info(f"IPFS state integrated: Wh={highest_wh:.6f}, Tokens={highest_tokens:.6f}")
            except (ValueError, TypeError) as err:
                logging.warning(f"Failed to parse numbers from IPFS payload: {err}")

        self.watt_hours = highest_wh
        self.flame_tokens = highest_tokens

        try:
            with open(STATE_FILE, "w") as f:
                json.dump(self.to_dict(), f, indent=2)
            logging.info("Initial audit complete. Persisted synchronized state baseline locally.")
        except OSError as err:
            logging.error(f"Failed to write state file during audit: {err}")

        return self.to_dict()

    def submit_telemetry(self) -> bool:
        try:
            data = json.dumps(self.to_dict()).encode("utf-8")
            req = urllib.request.Request(
                TELEMETRY_ENDPOINT,
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=TELEMETRY_TIMEOUT_SEC) as response:
                return response.status in (200, 201, 202)
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, Exception):
            return False

    def run_pulse_loop(self):
        pulse_count = 0
        while True:
            pulse_count += 1

            self.watt_hours += 0.000150
            self.flame_tokens += 0.813475

            pulse_data = f"{self.node_id}:{pulse_count}:{time.time()}"
            sha_hash = hashlib.sha256(pulse_data.encode("utf-8")).hexdigest()[:16]

            print(
                f"[PULSE #{pulse_count}] SHA256: {sha_hash} | RAM: {self.available_ram_mb}MB | "
                f"Wh: {self.watt_hours:.6f} | FLAME: {self.flame_tokens:.6f} | Shard: HOTSWAP",
                flush=True
            )

            self.submit_telemetry()

            try:
                with open(STATE_FILE, "w") as f:
                    json.dump(self.to_dict(), f, indent=2)
            except OSError:
                pass

            time.sleep(5)


if __name__ == "__main__":
    node = FlameChainNode()
    node.audit_initial_state()
    node.run_pulse_loop()
