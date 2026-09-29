import time

import json

import os

import hashlib



GENESIS_ANCHOR = "5721582c9690d6c7407ae7976486e906bb5a07090ab83a5dfa0f1ba6f6ab504bc10360b0d097d14b9c7729eaa7bfb7d5"

PRICE_FLOOR_USD = 0.002  # Fixed floor price per Watt-Hour unit



def get_live_metrics():

    try:

        with open("/sys/class/power_supply/battery/voltage_now", "r") as f:

            v_uv = int(f.read().strip())

        with open("/sys/class/power_supply/battery/current_now", "r") as f:

            i_ua = abs(int(f.read().strip()))

        power_w = (v_uv / 1e6) * (i_ua / 1e6)

    except Exception:

        power_w = 12.0  # Fallback default estimation



    return {

        "power_w": max(power_w, 1.0),

        "allocated_ram_gb": 8.0,

        "cpu_threads": 8

    }



def mint_block():

    metrics = get_live_metrics()

    wh_interval = metrics["power_w"] / 3600.0  # Watt-Hours accrued in 1 sec

    # WRU Equation: Power + RAM weighting

    wru_score = (metrics["power_w"] * 0.5) + (metrics["allocated_ram_gb"] * 0.5)

    fc_minted = wh_interval * 100.0  # Mint rate

    state = {

        "timestamp": int(time.time()),

        "genesis_anchor": GENESIS_ANCHOR,

        "shard_id": "SHARD_1_GALAXY_TAB",

        "power_watts": round(metrics["power_w"], 2),

        "minted_fc": round(fc_minted, 6),

        "price_floor_usd": PRICE_FLOOR_USD,

        "wru_score": round(wru_score, 2),

        "chief_validator_tax_collected": round(fc_minted * 0.10, 6)

    }



    # Broadcast for FlameGPT.net bridge

    with open("flamechain_live_state.json", "w") as f:

        json.dump(state, f, indent=2)

    print(f"[LIVE MAINNET] Power: {metrics['power_w']:.2f}W | Minted: +{fc_minted:.4f} $FC | Floor: ${PRICE_FLOOR_USD}/Wh")



if __name__ == "__main__":

    while True:

        mint_block()

        time.sleep(1)


