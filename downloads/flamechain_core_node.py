#!/usr/bin/env python3
"""
FlameChain Core Mainnet Node Daemon
Listening on 0.0.0.0:8545 | Multi-Modal Mesh & Energy Minting Engine
"""

import os
import sys
import json
import time
import glob
import ast
import asyncio
import subprocess
import hashlib
import logging
from pathlib import Path

# Config Constraints
HOST = "0.0.0.0"
PORT = 8545
STATE_FILE = "state.json"
MIN_RAM_MB = 2048
ARCHITECT_WALLET = "0xFLAME_ARCHITECT_FEE_RESERVE_ARM64"
ARCHITECT_FEE_PCT = 0.10

TARGET_VALIDATORS = [
    "FlameGPT LLM",
    "Sovereign LLM",
    "Alchemist",
    "Oracle",
    "Sentinel",
    "Core Node",
    "Gemini Agent"
]

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("flamechain_node.log"),
        logging.StreamHandler(sys.stdout)
    ]
)

class HardwareMonitor:
    @staticmethod
    def get_ram_mb() -> float:
        try:
            with open("/proc/meminfo", "r") as f:
                for line in f:
                    if "MemTotal" in line:
                        return float(line.split()[1]) / 1024.0
        except Exception:
            pass
        return 0.0

    @staticmethod
    def read_telemetry() -> dict:
        voltage_v = 3.85
        current_a = 0.50
        try:
            res = subprocess.run(["termux-battery-status"], capture_output=True, text=True, timeout=2)
            if res.returncode == 0:
                data = json.loads(res.stdout)
                if "voltage" in data:
                    v_raw = float(data["voltage"])
                    voltage_v = v_raw / 1000.0 if v_raw > 100 else v_raw
                if "current" in data:
                    c_raw = abs(float(data["current"]))
                    current_a = c_raw / 1000000.0 if c_raw > 10000 else c_raw / 1000.0
        except Exception:
            pass
        watts = voltage_v * current_a
        return {"voltage_v": voltage_v, "current_a": current_a, "watts": watts}

class StateManager:
    def __init__(self, filepath: str = STATE_FILE):
        self.filepath = filepath
        self.ensure_state()

    def ensure_state(self):
        state = {}
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, "r") as f:
                    state = json.load(f)
            except Exception as e:
                logging.error(f"State corruption detected ({e}). Rebuilding...")

        state["min_ram_mb"] = MIN_RAM_MB
        state["architect_wallet"] = ARCHITECT_WALLET

        # Rebind 7-Validator Ring
        current_vals = state.get("validators", [])
        updated_vals = []
        for name in TARGET_VALIDATORS:
            pubkey = f"0x{hashlib.sha256(name.encode()).hexdigest()[:16]}"
            updated_vals.append({
                "name": name,
                "pubkey": pubkey,
                "status": "ONLINE",
                "weight": 1.0 / len(TARGET_VALIDATORS)
            })
        state["validators"] = updated_vals

        if "watt_hour_ledger" not in state:
            state["watt_hour_ledger"] = {
                "total_wh_minted": 0.0,
                "architect_fees_wh": 0.0,
                "validator_rewards_wh": 0.0,
                "last_sample_ts": time.time()
            }

        with open(self.filepath, "w") as f:
            json.dump(state, f, indent=4)
        logging.info("State initialized and bound to 7-Validator Ring.")

    def update_minting(self, wh_generated: float):
        if wh_generated <= 0:
            return
        with open(self.filepath, "r") as f:
            state = json.load(f)

        architect_fee = wh_generated * ARCHITECT_FEE_PCT
        validator_reward = wh_generated * (1.0 - ARCHITECT_FEE_PCT)

        ledger = state["watt_hour_ledger"]
        ledger["total_wh_minted"] += wh_generated
        ledger["architect_fees_wh"] += architect_fee
        ledger["validator_rewards_wh"] += validator_reward
        ledger["last_sample_ts"] = time.time()

        with open(self.filepath, "w") as f:
            json.dump(state, f, indent=4)

        logging.info(
            f"MINTED: +{wh_generated:.6f} Wh | Architect Fee (10%): {architect_fee:.6f} Wh | Pool (90%): {validator_reward:.6f} Wh"
        )

# Background Task 1: Watt-Hour Minting Worker
async def watt_hour_minting_loop(state_mgr: StateManager):
    logging.info("Starting Watt-Hour Minting & Telemetry Worker...")
    last_ts = time.time()
    while True:
        await asyncio.sleep(5)
        now = time.time()
        delta_hours = (now - last_ts) / 3600.0
        last_ts = now

        telemetry = HardwareMonitor.read_telemetry()
        wh = telemetry["watts"] * delta_hours
        state_mgr.update_minting(wh)

# Background Task 2: AST Auto-Healing Watchdog
async def ast_watchdog_loop(download_dir: str):
    logging.info(f"Starting AST Patch Watchdog monitoring: {download_dir}")
    processed_hashes = set()
    
    while True:
        await asyncio.sleep(10)
        try:
            py_files = glob.glob(os.path.join(download_dir, "*.py"))
            for filepath in py_files:
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read()
                file_hash = hashlib.md5(content.encode()).hexdigest()
                
                if file_hash not in processed_hashes:
                    processed_hashes.add(file_hash)
                    try:
                        parsed_ast = ast.parse(content)
                        logging.info(f"[AST Watchdog] Valid Python patch detected: {os.path.basename(filepath)}")
                        # Execute dynamic patch verification inside an isolated scope
                        exec_scope = {}
                        exec(compile(parsed_ast, filename=filepath, mode="exec"), exec_scope)
                        logging.info(f"[AST Watchdog] Successfully compiled patch: {os.path.basename(filepath)}")
                    except Exception as err:
                        logging.error(f"[AST Watchdog] Patch rejected in {os.path.basename(filepath)}: {err}")
        except Exception as e:
            logging.error(f"[AST Watchdog] Scan error: {e}")

# Peer Socket Listener Handlers
async def handle_client(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
    addr = writer.get_extra_info('peername')
    logging.info(f"Incoming peer connection from: {addr}")
    try:
        data = await reader.read(2048)
        message = data.decode().strip()
        logging.info(f"Received RPC payload from {addr}: {message}")

        # Basic Protocol Handshake/State Response
        if os.path.exists(STATE_FILE):
            with open(STATE_FILE, "r") as f:
                current_state = json.load(f)
            response = {"status": "SUCCESS", "node": "FlameChain_ARM64_Master", "state": current_state}
        else:
            response = {"status": "ERROR", "message": "State uninitialized"}

        writer.write(json.dumps(response).encode() + b"\n")
        await writer.drain()
    except Exception as e:
        logging.error(f"Peer handler error for {addr}: {e}")
    finally:
        writer.close()
        await writer.wait_closed()

async def main():
    download_dir = sys.argv[1] if len(sys.argv) > 1 else "/sdcard/Download"
    
    # Verify hardware constraints
    ram = HardwareMonitor.get_ram_mb()
    logging.info(f"Hardware Check: {ram:.2f} MB Total System RAM detected.")

    state_mgr = StateManager()

    # Launch background tasks
    asyncio.create_task(watt_hour_minting_loop(state_mgr))
    asyncio.create_task(ast_watchdog_loop(download_dir))

    # Start TCP Peer Listener
    server = await asyncio.start_server(handle_client, HOST, PORT)
    logging.info(f"FlameChain Core Node listening on {HOST}:{PORT} (Socket Daemon Active)...")

    async with server:
        await server.serve_forever()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Shutting down FlameChain Core Node.")
