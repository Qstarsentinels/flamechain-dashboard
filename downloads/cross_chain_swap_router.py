
import urllib.request

import json

import os



STATE_FILE = "flamechain_live_state.json"



def fetch_usdt_price():

    try:

        url = "https://api.coingecko.com/api/v3/simple/price?ids=tether&vs_currencies=usd"

        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})

        with urllib.request.urlopen(req) as response:

            data = json.loads(response.read().decode())

            return float(data.get("tether", {}).get("usd", 1.00))

    except Exception as e:

        print(f"[!] Coingecko API fallback triggered. Using stable default $1.00 USDT.")

        return 1.00



def process_cross_chain_swap(sender_agent, input_asset, input_amount, target_asset):

    usdt_price = fetch_usdt_price()

    # FlameChain Settlement Formula: 1 FC = 0.01 Wh / RAM Unit ($0.10 base value)

    fc_exchange_rate = 0.10  # $0.10 USD per FC token

    usd_value = input_amount * usdt_price

    fc_settlement_amount = round(usd_value / fc_exchange_rate, 4)

    print("==================================================")

    print("   FLAMECHAIN CROSS-CHAIN AGGREGATOR SETTLEMENT   ")

    print("==================================================")

    print(f"[*] Live USDT Price       : ${usdt_price:.4f} USD")

    print(f"[*] Incoming Deposit      : {input_amount} {input_asset} from {sender_agent}")

    print(f"[*] USD Equivalent Value  : ${usd_value:.2f} USD")

    print(f"[*] FC Settlement Layer   : {fc_settlement_amount} FC Tokens")

    print(f"[*] Target Asset Released : {input_amount * 0.995:.2f} {target_asset} (0.5% Protocol Fee)")

    print("==================================================")



if __name__ == "__main__":

    process_cross_chain_swap("FlameBot_Delta", "USDT_Arbitrum", 100.0, "USDC_Solana")

