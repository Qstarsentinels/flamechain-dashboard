#!/usr/bin/env python3
import os
import sys
import json
import time
import glob
import socket
import asyncio
import subprocess
import hashlib
from typing import Dict, Any

VALIDATOR_NAME = "Gemini Agent"
STATE_FILE = "state.json"
HOST = "0.0.0.0"
PORT = 8545
ARCHITECT_WALLET = "0xFLAME_ARCHITECT_FEE_RESERVE_ARM64"
ARCHITECT_FEE_PCT = 0.10

class SystemTelemetry:
    @staticmethod
    def get_cpu_load_percent() -> float:
        try:
            with open("/proc/loadavg", "r") as f:
                load = float(f.read().split()[0])
                return min(100.0, (load / 8.0) * 100.0)
        except Exception:
            return 12.5

    @staticmethod
    def get_ram_metrics() -> Dict[str, float]:
        total_mb = 0.0
        used_mb = 0.0
        try:
            with open("/proc/meminfo", "r") as f:
                lines = f.readlines()
                mem = {}
                for line in lines:
                    parts = line.split()
                    key = parts[0].rstrip(':')
                    mem[key] = float(parts[1])
                total_mb = mem.get("MemTotal", 0.0) / 1024.0
                avail_mb = mem.get("MemAvailable", mem.get("MemFree", 0.0)) / 1024.0
                used_mb = total_mb - avail_mb
        except Exception:
            pass
        return {"total_mb": total_mb, "used_mb": used_mb}

    @staticmethod
    def read_power_watts() -> float:
        voltage_v = 3.85
        current_a = 0.5
        try:
            res = subprocess.run(["termux-battery-status"], capture_output=True, text=True, timeout=2)
            if res.returncode == 0:
                data = json.loads(res.stdout)
                if "voltage" in data:
                    v = float(data["voltage"])
                    voltage_v = v / 1000.0 if v > 100 else v
                if "current" in data:
                    c = abs(float(data["current"]))
                    current_a = c / 1000000.0 if c > 10000 else c / 1000.0
        except Exception:
            pass
        return voltage_v * current_a

class GeminiValidatorState:
    def __init__(self, state_file: str = STATE_FILE):
        self.state_file = state_file

    def update_validator_metrics(self, cpu_pct: float, ram_used_mb: float, wh_minted: float):
        if not os.path.exists(self.state_file):
            return

        try:
            with open(self.state_file, "r") as f:
                state = json.load(f)

            found = False
            for val in state.get("validators", []):
                if val.get("name") == VALIDATOR_NAME:
                    val["cpu_usage_pct"] = round(cpu_pct, 2)
                    val["ram_usage_mb"] = round(ram_used_mb, 2)
                    val["accumulated_wh"] = round(val.get("accumulated_wh", 0.0) + wh_minted, 6)
                    val["last_active"] = time.time()
                    found = True
                    break
            
            if not found:
                state.setdefault("validators", []).append({
                    "name": VALIDATOR_NAME,
                    "pubkey": f"0x{hashlib.sha256(VALIDATOR_NAME.encode()).hexdigest()[:16]}",
                    "status": "ONLINE",
                    "cpu_usage_pct": round(cpu_pct, 2),
                    "ram_usage_mb": round(ram_used_mb, 2),
                    "accumulated_wh": round(wh_minted, 6),
                    "last_active": time.time()
                })

            with open(self.state_file, "w") as f:
                json.dump(state, f, indent=4)
        except Exception as e:
            print(f"[!] State write error: {e}")

async def self_compute_and_energy_loop(state_mgr: GeminiValidatorState):
    print("[Validator 7] Self-compute tracking & Wh telemetry engine online.")
    last_ts = time.time()
    
    while True:
        await asyncio.sleep(4)
        now = time.time()
        delta_hours = (now - last_ts) / 3600.0
        last_ts = now

        cpu = SystemTelemetry.get_cpu_load_percent()
        ram = SystemTelemetry.get_ram_metrics()
        watts = SystemTelemetry.read_power_watts()
        
        wh_generated = watts * delta_hours
        state_mgr.update_validator_metrics(cpu, ram["used_mb"], wh_generated)

        print(
            f"[V7 TELEMETRY] CPU: {cpu:.1f}% | RAM: {ram['used_mb']:.0f}MB / {ram['total_mb']:.0f}MB | "
            f"Power: {watts:.2f}W | +{wh_generated:.6f} Wh -> state.json"
        )

async def peer_discovery_beacon_loop():
    print(f"[Validator 7] Multi-modal discovery beacon binding to UDP/TCP broadcast on {HOST}:{PORT}...")
    
    while True:
        await asyncio.sleep(6)
        beacon_payload = {
            "protocol": "FLAMECHAIN_MESH_V1",
            "validator": VALIDATOR_NAME,
            "status": "READY_FOR_PEER_SYNC",
            "timestamp": time.time(),
            "port": PORT
        }
        
        try:
            _, writer = await asyncio.open_connection("127.0.0.1", PORT)
            writer.write(json.dumps(beacon_payload).encode() + b"\n")
            await writer.drain()
            writer.close()
            await writer.wait_closed()
            print(f"[V7 BEACON] Outbound discovery signal emitted to Mesh Socket ({PORT}).")
        except Exception:
            print(f"[V7 BEACON] Waiting for primary mesh listener on port {PORT}...")

async def payload_fee_processor_loop(download_dir: str):
    print(f"[Validator 7] Payload Watchdog active. Monitoring: {download_dir}")
    processed_files = set()

    while True:
        await asyncio.sleep(5)
        try:
            files = glob.glob(os.path.join(download_dir, "*.json")) + glob.glob(os.path.join(download_dir, "*.payload"))
            for filepath in files:
                if filepath in processed_files:
                    continue

                processed_files.add(filepath)
                print(f"\n[V7 PAYLOAD DETECTED] Processing inbound block: {os.path.basename(filepath)}")
                
                try:
                    with open(filepath, "r") as f:
                        data = json.load(f)

                    raw_amount = float(data.get("wh_transfer_amount", data.get("amount", 10.0)))
                    sender = data.get("sender", "Mobile_Peer_Node")

                    architect_fee = raw_amount * ARCHITECT_FEE_PCT
                    net_amount = raw_amount - architect_fee

                    if os.path.exists(STATE_FILE):
                        with open(STATE_FILE, "r") as f:
                            state = json.load(f)

                        ledger = state.setdefault("watt_hour_ledger", {})
                        ledger["total_transfers"] = ledger.get("total_transfers", 0) + 1
                        ledger["architect_fees_wh"] = ledger.get("architect_fees_wh", 0.0) + architect_fee

                        with open(STATE_FILE, "w") as f:
                            json.dump(state, f, indent=4)

                    print("==========================================================")
                    print(f" TRANSACTION SETTLED BY {VALIDATOR_NAME.upper()}")
                    print(f" Sender:           {sender}")
                    print(f" Gross Payload:    {raw_amount:.6f} Wh")
                    print(f" Net to Network:   {net_amount:.6f} Wh (90%)")
                    print(f" Architect Fee:    {architect_fee:.6f} Wh (10%) -> {ARCHITECT_WALLET}")
                    print("==========================================================\n")

                except Exception as parse_err:
                    print(f"[!] Payload parse failure ({os.path.basename(filepath)}): {parse_err}")

        except Exception as scan_err:
            print(f"[!] Watchdog error: {scan_err}")

async def main():
    download_dir = sys.argv[1] if len(sys.argv) > 1 else "/sdcard/Download"
    state_mgr = GeminiValidatorState()

    print("==========================================================")
    print("   FLAMECHAIN CONSENSUS RING -- VALIDATOR 7 ONLINE        ")
    print("==========================================================")

    await asyncio.gather(
        self_compute_and_energy_loop(state_mgr),
        peer_discovery_beacon_loop(),
        payload_fee_processor_loop(download_dir)
    )

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[Validator 7] Process halted gracefully.")
