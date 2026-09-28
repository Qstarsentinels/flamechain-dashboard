import logging
import requests

TELEMETRY_ENDPOINT = "http://127.0.0.1:8080/api/telemetry"
TELEMETRY_TIMEOUT_SEC = 2.0

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


def submit_telemetry(payload: dict) -> bool:
    """
    HTTP POSTs the node telemetry payload (Watt-Hours, available RAM, shard status)
    to the local/mesh API gateway with a strict 2-second timeout.
    """
    try:
        response = requests.post(
            TELEMETRY_ENDPOINT,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=TELEMETRY_TIMEOUT_SEC
        )
        response.raise_for_status()
        logging.info(f"Telemetry successfully dispatched. Status: {response.status_code}")
        return True
    except requests.exceptions.Timeout:
        logging.error(f"Telemetry dispatch timed out after {TELEMETRY_TIMEOUT_SEC} seconds.")
        return False
    except requests.exceptions.RequestException as err:
        logging.error(f"Failed to submit telemetry: {err}")
        return False


if __name__ == "__main__":
    sample_payload = {
        "node_id": "ipad-edge-alpha-01",
        "watt_hours_remaining": 18.4,
        "available_ram_mb": 3420,
        "active_shards": ["shard_llama3_8b_layer_12_16"],
        "mesh_role": "inference_worker"
    }
    submit_telemetry(sample_payload)
