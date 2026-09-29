
import json

import os

import psutil



STATE_FILE = "flamechain_live_state.json"



def calculate_dynamic_fc_price():

    if not os.path.exists(STATE_FILE):

        return {"error": "State file missing"}

    with open(STATE_FILE, "r") as f:

        state = json.load(f)

    total_wh = state.get("total_wh_metered", 1.0)

    architect_fc = state.get("architect_accumulated_fc", 1.0)

    total_supply = max(architect_fc / 0.10, 1.0)  # Extrapolated total supply from 10% tax

    # System Telemetry Inputs

    ram_gb = psutil.virtual_memory().total / (1024 ** 3)

    active_nodes = state.get("core_validator_count", 6)

    # Economic Equation: Base Energy Cost + RAM Capacity Value divided by Token Supply

    wh_value_usd = total_wh * 0.12  # Standard $0.12/kWh baseline

    ram_value_usd = ram_gb * 0.05   # Memory scarcity factor

    mesh_scaling_factor = 1.0 + (active_nodes * 0.05)

    fc_price_usdt = round(((wh_value_usd + ram_value_usd) / total_supply) * mesh_scaling_factor, 6)

    telemetry_data = {

        "fc_price_usdt": max(fc_price_usdt, 0.001),  # Floor price $0.001

        "total_supply_fc": round(total_supply, 4),

        "total_wh_metered": total_wh,

        "active_mesh_ram_gb": round(ram_gb, 2),

        "mesh_scaling_factor": mesh_scaling_factor

    }

    state["telemetry_valuation"] = telemetry_data

    with open(STATE_FILE, "w") as f:

        json.dump(state, f, indent=4)

    print(f"[+] FC Telemetry Valuation Complete:")

    print(f"    - Dynamic FC Price: ${telemetry_data['fc_price_usdt']} USDT")

    print(f"    - Total FC Supply: {telemetry_data['total_supply_fc']} FC")

    print(f"    - Active Mesh RAM: {telemetry_data['active_mesh_ram_gb']} GB")

    return telemetry_data



if __name__ == "__main__":

    calculate_dynamic_fc_price()

