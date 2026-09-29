
import json

import os

import time

import psutil



STATE_FILE = "flamechain_live_state.json"



def read_usbc_power():

    # Attempt to read direct Android kernel power supply metrics

    try:

        with open("/sys/class/power_supply/battery/current_now", "r") as f:

            current_uamp = abs(float(f.read().strip()))

        with open("/sys/class/power_supply/battery/voltage_now", "r") as f:

            voltage_uv = abs(float(f.read().strip()))

        # Convert microamps and microvolts to Watts

        watts = (current_uamp / 1000000.0) * (voltage_uv / 1000000.0)

    except Exception:

        # Baseline fallback for mobile USB-C standard draw (10W rate)

        watts = 10.0

    return watts



def run_hardware_metering(duration_sec=2.0):

    watts = read_usbc_power()

    wh_drawn = round((watts * (duration_sec / 3600.0)), 6)

    ram = psutil.virtual_memory()

    ram_used_gb = round((ram.total - ram.available) / (1024**3), 2)

    # Calculate FC rewards: Energy + Allocated RAM

    minted_fc = round((wh_drawn * 1000.0) + (ram_used_gb * 0.5), 4)

    architect_fee = round(minted_fc * 0.10, 4)

    validator_reward = round(minted_fc - architect_fee, 4)



    if os.path.exists(STATE_FILE):

        with open(STATE_FILE, "r") as f:

            state = json.load(f)

        state["total_wh_metered"] = round(state.get("total_wh_metered", 0.0) + wh_drawn, 6)

        state["architect_accumulated_fc"] = round(state.get("architect_accumulated_fc", 0.0) + architect_fee, 4)

        with open(STATE_FILE, "w") as f:

            json.dump(state, f, indent=4)



    print(f"[+] Metered USB-C Power: {watts:.2f}W | Wh Drawn: {wh_drawn} Wh")

    print(f"[+] Active System RAM: {ram_used_gb} GB")

    print(f"[+] Block Minted: {minted_fc} FC (Validator: {validator_reward} FC | Architect: {architect_fee} FC)")



if __name__ == "__main__":

    run_hardware_metering()

