
import time

import json

import os



GENESIS_ANCHOR = "5721582c9690d6c7407ae7976486e906bb5a07090ab83a5dfa0f1ba6f6ab504bc10360b0d097d14b9c7729eaa7bfb7d5"

PRICE_FLOOR_USD = 0.002

CHIEF_VALIDATOR_ID = "Q_STAR_X_Q_CHIEF_VALIDATOR"

TAX_RATE = 0.10

DEFLATION_RATE = 0.05



def get_sysfs_power():

    try:

        with open("/sys/class/power_supply/battery/voltage_now", "r") as f:

            v_uv = int(f.read().strip()) / 1e6

        with open("/sys/class/power_supply/battery/current_now", "r") as f:

            i_ua = abs(int(f.read().strip())) / 1e6

        return max(v_uv * i_ua, 1.0)

    except Exception:

        return 12.5



def get_system_ram_gb():

    try:

        with open("/proc/meminfo", "r") as f:

            for line in f:

                if "MemTotal" in line:

                    kb = int(line.split()[1])

                    return round(kb / (1024 * 1024), 2)

    except Exception:

        pass

    return 8.0



def compute_wru(power_watts):

    total_ram = get_system_ram_gb()

    cpu_cores = os.cpu_count() or 4

    wru_score = (power_watts * 0.40) + (total_ram * 0.30) + (cpu_cores * 0.30)

    return round(wru_score, 4), total_ram, cpu_cores



def load_previous_ledger():

    if os.path.exists("flamechain_live_state.json"):

        try:

            with open("flamechain_live_state.json", "r") as f:

                data = json.load(f)

                prev_wh = data.get("accumulated_wh", 0.0)

                prev_fc = data.get("total_minted_fc", 0.0)

                prev_burn = data.get("total_burned_fc", 0.0)

                return prev_wh, prev_fc, prev_burn

        except Exception:

            pass

    return 0.0, 0.0, 0.0



def start_mainnet_node():

    total_wh, total_fc, burn_total_fc = load_previous_ledger()

    print("[+] FLAMECHAIN MAINNET SHARD 1 ACTIVE (V2 ENGINE)")

    print("[+] Chief Validator ID: " + CHIEF_VALIDATOR_ID)

    print("[+] Genesis Anchor Restored: " + GENESIS_ANCHOR[:16] + "...")

    print(f"[+] Loaded Ledger History -> Prev Wh: {total_wh:.4f} | Prev $FC: {total_fc:.4f}")

    while True:

        watts = get_sysfs_power()

        wru_score, total_ram, cpu_cores = compute_wru(watts)

        wh_frame = watts / 3600.0

        total_wh += wh_frame

        minted_this_frame = wh_frame * wru_score * 10.0

        burn_frame = minted_this_frame * DEFLATION_RATE

        total_fc += (minted_this_frame - burn_frame)

        burn_total_fc += burn_frame

        chief_tax_fc = total_fc * TAX_RATE

        net_chief_balance = total_fc - chief_tax_fc

        entanglement_state = "ENTANGLED_STATE_A" if int(time.time()) % 2 == 0 else "ENTANGLED_STATE_B"

        state_payload = {

            "timestamp": int(time.time()),

            "shard": "SHARD_1_GALAXY_TAB",

            "shard_2_link_mode": "HOTSPOT_BLUETOOTH_READY",

            "genesis_anchor": GENESIS_ANCHOR,

            "power_watts": round(watts, 2),

            "wru_score": wru_score,

            "allocated_ram_gb": total_ram,

            "cpu_threads": cpu_cores,

            "accumulated_wh": round(total_wh, 6),

            "total_minted_fc": round(total_fc, 6),

            "total_burned_fc": round(burn_total_fc, 6),

            "chief_validator_net_fc": round(net_chief_balance, 6),

            "chief_validator_tax_fc": round(chief_tax_fc, 6),

            "price_floor_usd": PRICE_FLOOR_USD,

            "sentinel_entanglement_state": entanglement_state,

            "total_active_shards": 1,

            "total_validators": 1,

            "dual_llm_status": "SOVEREIGN_AND_FLAMEGPT_ENGAGED",

            "governance_quorum": "70_PERCENT_PASS"

        }

        with open("flamechain_live_state.json", "w") as f:

            json.dump(state_payload, f, indent=2)

        print(f"[SHARD 1 MINTING] Power: {round(watts,2)}W | WRU: {wru_score} | Net FC: {round(net_chief_balance,4)} | Burned: {round(burn_total_fc,4)}")

        time.sleep(1)



if __name__ == "__main__":

    start_mainnet_node()

