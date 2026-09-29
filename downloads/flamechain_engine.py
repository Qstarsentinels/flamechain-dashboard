#!/usr/bin/env python3
import os
import sys
import json
import time
import glob
import ast
import subprocess
import hashlib
from typing import Dict, List, Any

STATE_FILE = "state.json"
MIN_RAM_MB = 2048
VALIDATOR_COUNT = 7

class HardwareEnforcer:
    @staticmethod
    def get_total_ram_mb() -> float:
        try:
            with open("/proc/meminfo", "r") as f:
                for line in f:
                    if "MemTotal" in line:
                        parts = line.split()
                        return float(parts[1]) / 1024.0
        except Exception:
            pass
        return 0.0

    @staticmethod
    def read_battery_telemetry() -> Dict[str, float]:
        voltage_v = 3.85
        current_a = 0.5
        try:
            result = subprocess.run(["termux-battery-status"], capture_output=True, text=True, timeout=2)
            if result.returncode == 0:
                data = json.loads(result.stdout)
                if "voltage" in data:
                    voltage_v = float(data["voltage"]) / 1000.0 if data["voltage"] > 100 else float(data["voltage"])
                if "current" in data:
                    raw_curr = abs(float(data["current"]))
                    current_a = raw_curr / 1000000.0 if raw_curr > 10000 else raw_curr / 1000.0
        except Exception:
            try:
                if os.path.exists("/sys/class/power_supply/battery/voltage_now"):
                    with open("/sys/class/power_supply/battery/voltage_now", "r") as f:
                        voltage_v = float(f.read().strip()) / 1e6
                if os.path.exists("/sys/class/power_supply/battery/current_now"):
                    with open("/sys/class/power_supply/battery/current_now", "r") as f:
                        current_a = abs(float(f.read().strip())) / 1e6
            except Exception:
                pass
        return {"voltage_v": voltage_v, "current_a": current_a, "watts": voltage_v * current_a}

class SelfRebuildingStateEngine:
    def __init__(self, state_path: str = STATE_FILE):
        self.state_path = state_path
        self.hardware = HardwareEnforcer()

    def verify_hardware(self):
        ram = self.hardware.get_total_ram_mb()
        print(f"[+] Detected System RAM: {ram:.2f} MB")
        if ram < MIN_RAM_MB:
            print(f"[!] WARNING: Minimum RAM requirement ({MIN_RAM_MB}MB) not met. Operational instability may occur.")
        else:
            print(f"[✓] RAM constraint passed (>= {MIN_RAM_MB}MB).")

    def generate_genesis_validators(self) -> List[Dict[str, Any]]:
        validators = []
        for i in range(1, VALIDATOR_COUNT + 1):
            seed = f"flamechain_v{i}_node_tx_key_{time.time()}"
            v_hash = hashlib.sha256(seed.encode()).hexdigest()[:16]
            validators.append({
                "id": f"val_{i}",
                "pubkey": f"0x{v_hash}",
                "status": "ACTIVE",
                "weight_wh": 1.0,
                "allocated_ram_mb": MIN_RAM_MB / VALIDATOR_COUNT
            })
        return validators

    def enforce_state(self):
        state_data = {}
        rebuild_needed = False

        if os.path.exists(self.state_path):
            try:
                with open(self.state_path, "r") as f:
                    state_data = json.load(f)
            except Exception as e:
                print(f"[!] Corrupted {self.state_path} detected: {e}. Rebuilding...")
                rebuild_needed = True
        else:
            print(f"[!] {self.state_path} missing. Initializing new state...")
            rebuild_needed = True

        validators = state_data.get("validators", [])
        if len(validators) != VALIDATOR_COUNT:
            print(f"[!] Validator count mismatch (Found: {len(validators)}, Required: {VALIDATOR_COUNT}). Rebuilding validator ring...")
            state_data["validators"] = self.generate_genesis_validators()
            rebuild_needed = True

        if state_data.get("min_ram_mb") != MIN_RAM_MB:
            state_data["min_ram_mb"] = MIN_RAM_MB
            rebuild_needed = True

        if "watt_hour_ledger" not in state_data:
            state_data["watt_hour_ledger"] = {
                "total_wh_consumed": 0.0,
                "last_checkpoint_timestamp": time.time()
            }
            rebuild_needed = True
        else:
            last_ts = state_data["watt_hour_ledger"].get("last_checkpoint_timestamp", time.time())
            delta_hours = (time.time() - last_ts) / 3600.0
            telemetry = self.hardware.read_battery_telemetry()
            wh_added = telemetry["watts"] * delta_hours
            state_data["watt_hour_ledger"]["total_wh_consumed"] += wh_added
            state_data["watt_hour_ledger"]["last_checkpoint_timestamp"] = time.time()
            print(f"[+] Added {wh_added:.6f} Wh to cumulative ledger. Total: {state_data['watt_hour_ledger']['total_wh_consumed']:.6f} Wh")

        if rebuild_needed:
            with open(self.state_path, "w") as f:
                json.dump(state_data, f, indent=4)
            print(f"[✓] State successfully reconciled and saved to {self.state_path}")
        else:
            print(f"[✓] Integrity check passed. {self.state_path} compliant.")

class ModuleASTAnalyzer:
    @staticmethod
    def analyze_directory(target_dir: str):
        print(f"\n[+] Analyzing Python modules in directory: {target_dir}")
        py_files = glob.glob(os.path.join(target_dir, "*.py"))
        
        if not py_files:
            print(f"[-] No external .py files found in {target_dir}")
            return

        for filepath in py_files:
            filename = os.path.basename(filepath)
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    source = f.read()
                parsed = ast.parse(source)
                classes = [node.name for node in ast.walk(parsed) if isinstance(node, ast.ClassDef)]
                functions = [node.name for node in ast.walk(parsed) if isinstance(node, ast.FunctionDef)]
                print(f"  • File: {filename} | Classes: {len(classes)} | Functions: {len(functions)}")
            except Exception as e:
                print(f"  ! Error analyzing {filename}: {e}")

if __name__ == "__main__":
    print("=== FlameChain Self-Rebuilding Mesh Engine ===")
    engine = SelfRebuildingStateEngine()
    engine.verify_hardware()
    engine.enforce_state()
    
    download_dir = sys.argv[1] if len(sys.argv) > 1 else "/sdcard/Download"
    if os.path.exists(download_dir):
        ModuleASTAnalyzer.analyze_directory(download_dir)
