
import json

import os



STATE_FILE = "flamechain_live_state.json"



# Constants

K_ENERGY = 0.05  # $0.05 per Wh

K_RAM    = 0.50  # $0.50 per GB RAM



def calculate_dynamic_fc_price():

    if not os.path.exists(STATE_FILE):

        return 0.10, 1000.0

    with open(STATE_FILE, "r") as f:

        state = json.load(f)

    wh = state.get("total_wh_metered", 10.0)

    ram = state.get("mesh_node_hardware", {}).get("total_device_ram_gb", 3.0)

    balances = state.get("account_balances", {})

    circulating_supply = max(1.0, sum(balances.values()))

    # Backing Equation

    hardware_backing_usd = (wh * K_ENERGY) + (ram * K_RAM)

    fc_price_usd = max(0.001, hardware_backing_usd / circulating_supply)

    return round(fc_price_usd, 6), round(circulating_supply, 4)



def execute_dynamic_swap(agent_id, deposit_usdt):

    fc_price, total_supply = calculate_dynamic_fc_price()

    usd_val = deposit_usdt * 1.0  # USDT = $1.00

    fc_required = round(usd_val / fc_price, 4)

    # Fee Split: 0.5% total (0.4% to LPs/Validators, 0.1% Burned)

    protocol_fee_usd = usd_val * 0.005

    validator_cut_fc = round((usd_val * 0.004) / fc_price, 4)

    burned_fc = round((usd_val * 0.001) / fc_price, 4)

    print("==================================================")

    print("    FLAMECHAIN DYNAMIC PRICE & LIQUIDITY ENGINE   ")

    print("==================================================")

    print(f"[*] Total Circulating FC   : {total_supply} FC")

    print(f"[*] Computed FC Price      : ${fc_price:.6f} USD / FC")

    print(f"[*] Swap Deposit           : ${usd_val:.2f} USDT")

    print(f"[*] FC Settled             : {fc_required} FC")

    print(f"[*] Validator/LP Yield     : +{validator_cut_fc} FC (0.4%)")

    print(f"[*] Supply Burned          : -{burned_fc} FC (0.1%)")

    print("==================================================")



if __name__ == "__main__":

    execute_dynamic_swap("FlameBot_Delta", 100.0)

