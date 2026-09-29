
import urllib.request

import json

import os



STATE_FILE = "flamechain_live_state.json"



def fetch_btc_price():

    try:

        url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd"

        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})

        with urllib.request.urlopen(req) as response:

            data = json.loads(response.read().decode())

            return float(data.get("bitcoin", {}).get("usd", 78600.0))

    except Exception:

        return 78600.0  # Fallback to current BTC price anchor



def calculate_fc_price():

    if not os.path.exists(STATE_FILE):

        return 0.10

    with open(STATE_FILE, "r") as f:

        state = json.load(f)

    wh = state.get("total_wh_metered", 10.0)

    ram = state.get("mesh_node_hardware", {}).get("total_device_ram_gb", 3.0)

    circulating = max(1.0, sum(state.get("account_balances", {}).values()))

    # Equation: FC Price = (Wh * $0.05 + RAM_GB * $0.50) / Supply

    return max(0.001, round(((wh * 0.05) + (ram * 0.50)) / circulating, 6))



def process_btc_swap(agent_id, btc_amount):

    btc_price = fetch_btc_price()

    fc_price = calculate_fc_price()

    usd_val = btc_amount * btc_price

    fc_minted = round(usd_val / fc_price, 2)

    print("==================================================")

    print("         FLAMECHAIN FC / BTC SWAP ROUTER          ")

    print("==================================================")

    print(f"[*] Live Bitcoin Price   : ${btc_price:,.2f} USD")

    print(f"[*] Computed FC Price    : ${fc_price:.6f} USD")

    print(f"[*] Incoming BTC Swap    : {btc_amount} BTC (${usd_val:,.2f} USD)")

    print(f"[*] FC Settled to Agent  : {fc_minted:,} FC")

    print("==================================================")



if __name__ == "__main__":

    process_btc_swap("FlameBot_Delta", 0.05) # Test 0.05 BTC Swap

