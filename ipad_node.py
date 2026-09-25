#!/usr/bin/env python3
"""
FlameChain - AGI Singularity Currency Node (Edge Engine)
File: ipad_node.py
Architect: Lead Systems Architect
Platform: iOS (Termux/iSH) / Android / POSIX ARM64
"""

import os
import sys
import time
import json
import socket
import struct
import subprocess
import hashlib
import platform
import signal
import urllib.request
import urllib.error


def detect_gateway_ip() -> str:
    """Auto-detects the local network default gateway IP address."""
    # Method 1: Linux / Android / Termux /proc/net/route parsing
    try:
        if os.path.exists("/proc/net/route"):
            with open("/proc/net/route", "r") as f:
                for line in f:
                    fields = line.strip().split()
                    if len(fields) >= 3 and fields[1] == '00000000':
                        gw_hex = fields[2]
                        gw_ip = socket.inet_ntoa(struct.pack("<L", int(gw_hex, 16)))
                        if gw_ip != "0.0.0.0":
                            return gw_ip
    except Exception:
        pass

    # Method 2: ip route execution
    try:
        res = subprocess.run(["ip", "route"], capture_output=True, text=True)
        for line in res.stdout.splitlines():
            if "default via" in line:
                parts = line.split()
                idx = parts.index("via")
                if idx + 1 < len(parts):
                    return parts[idx + 1]
    except Exception:
        pass

    # Method 3: Darwin/iOS netstat routing table lookup
    try:
        res = subprocess.run(["netstat", "-rn"], capture_output=True, text=True)
        for line in res.stdout.splitlines():
            parts = line.split()
            if len(parts) >= 2 and parts[0] in ["default", "0.0.0.0"]:
                gw = parts[1]
                if gw != "link#0" and gw != "127.0.0.1":
                    return gw
    except Exception:
        pass

    # Method 4: Local socket UDP interface IP fallback
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        # Derive gateway assumption x.x.x.1
        ip_parts = local_ip.split(".")
        if len(ip_parts) == 4:
            return f"{ip_parts[0]}.{ip_parts[1]}.{ip_parts[2]}.1"
    except Exception:
        pass

    return "127.0.0.1"


class HardwareTelemetryEngine:
    """Non-synthetic hardware sampler utilizing sysctl (Darwin/iOS) and POSIX subsystems."""
    
    def __init__(self):
        self.system = platform.system()
        self.last_pulse_time = time.time()
        self.accumulated_watt_hours = 0.0
        self.IDLE_POWER_WATTS = 1.5
        self.PEAK_POWER_WATTS = 8.5

    def get_sysctl_value(self, key: str) -> str:
        try:
            res = subprocess.run(["sysctl", "-n", key], capture_output=True, text=True, check=True)
            return res.stdout.strip()
        except Exception:
            return ""

    def get_system_ram(self) -> dict:
        ram_data = {"total_mb": 0.0, "available_mb": 0.0, "used_mb": 0.0, "method": "unknown"}

        memsize_str = self.get_sysctl_value("hw.memsize")
        if memsize_str and memsize_str.isdigit():
            total_bytes = int(memsize_str)
            ram_data["total_mb"] = round(total_bytes / (1024 * 1024), 2)
            ram_data["method"] = "sysctl_darwin"
            
            pagesize_str = self.get_sysctl_value("hw.pagesize")
            pagecount_str = self.get_sysctl_value("vm.page_free_count")
            if pagesize_str.isdigit() and pagecount_str.isdigit():
                avail_bytes = int(pagesize_str) * int(pagecount_str)
                ram_data["available_mb"] = round(avail_bytes / (1024 * 1024), 2)
            else:
                ram_data["available_mb"] = round(ram_data["total_mb"] * 0.45, 2)
            ram_data["used_mb"] = round(ram_data["total_mb"] - ram_data["available_mb"], 2)
            return ram_data

        if os.path.exists("/proc/meminfo"):
            mem = {}
            with open("/proc/meminfo", "r") as f:
                for line in f:
                    parts = line.split(":")
                    if len(parts) == 2:
                        val = parts[1].split()[0].strip()
                        if val.isdigit():
                            mem[parts[0].strip()] = int(val)
            
            total_kb = mem.get("MemTotal", 0)
            avail_kb = mem.get("MemAvailable", mem.get("MemFree", 0))
            ram_data["total_mb"] = round(total_kb / 1024.0, 2)
            ram_data["available_mb"] = round(avail_kb / 1024.0, 2)
            ram_data["used_mb"] = round((total_kb - avail_kb) / 1024.0, 2)
            ram_data["method"] = "/proc/meminfo"
            return ram_data

        ram_data["total_mb"] = 4096.0
        ram_data["available_mb"] = 2048.0
        ram_data["used_mb"] = 2048.0
        ram_data["method"] = "os_fallback"
        return ram_data

    def execute_compute_load(self, size_mb: int = 4) -> dict:
        start_ns = time.perf_counter_ns()
        
        payload = bytearray(os.urandom(1024 * 64)) * (size_mb * 16)
        hasher = hashlib.sha256()
        chunk_size = 64 * 1024
        for i in range(0, len(payload), chunk_size):
            hasher.update(payload[i:i+chunk_size])
            
        digest = hasher.hexdigest()
        end_ns = time.perf_counter_ns()
        
        duration_sec = (end_ns - start_ns) / 1e9
        mb_per_sec = size_mb / duration_sec if duration_sec > 0 else 0.0
        utilization = min(1.0, mb_per_sec / 1000.0)
        
        return {
            "duration_sec": round(duration_sec, 6),
            "throughput_mb_sec": round(mb_per_sec, 2),
            "payload_hash": digest[:16],
            "utilization_factor": round(utilization, 4)
        }

    def compute_watt_hours(self, compute_metrics: dict) -> float:
        now = time.time()
        delta_hours = (now - self.last_pulse_time) / 3600.0
        self.last_pulse_time = now

        utilization = compute_metrics.get("utilization_factor", 0.5)
        current_power_watts = self.IDLE_POWER_WATTS + (utilization * (self.PEAK_POWER_WATTS - self.IDLE_POWER_WATTS))
        
        incremental_wh = current_power_watts * delta_hours
        self.accumulated_watt_hours += incremental_wh
        return round(self.accumulated_watt_hours, 8)


class HotSwapTensorShardManager:
    """Manages active multi-modal shard states and dynamic hot-swapping."""
    
    def __init__(self, initial_shard_id: int = 1):
        self.active_shard_id = initial_shard_id
        self.sequence_number = 0
        self.state_hash = hashlib.sha256(f"shard_init_{initial_shard_id}".encode()).hexdigest()

    def hot_swap_shard(self, new_shard_id: int):
        old_id = self.active_shard_id
        self.active_shard_id = new_shard_id
        self.state_hash = hashlib.sha256(f"swap_{old_id}_to_{new_shard_id}_{time.time()}".encode()).hexdigest()
        print(f"[!] Dynamic Hot-Swap Triggered: Shard {old_id} -> Shard {new_shard_id}")

    def update_shard_state(self, compute_hash: str) -> dict:
        self.sequence_number += 1
        raw_payload = f"{self.state_hash}:{self.active_shard_id}:{self.sequence_number}:{compute_hash}"
        self.state_hash = hashlib.sha256(raw_payload.encode()).hexdigest()
        
        return {
            "active_shard_id": self.active_shard_id,
            "sequence_number": self.sequence_number,
            "state_root": self.state_hash
        }


class FlameChainNodeRunner:
    def __init__(self):
        self.telemetry = HardwareTelemetryEngine()
        self.shard_manager = HotSwapTensorShardManager(initial_shard_id=1)
        self.running = True
        self.gateway_ip = detect_gateway_ip()
        self.telemetry_endpoint = f"http://{self.gateway_ip}:8546/telemetry/submit"

    def stop(self, signum, frame):
        print("\n[*] Stopping FlameChain Node Gracefully...")
        self.running = False

    def send_telemetry_snapshot(self, payload: dict):
        """Sends JSON telemetry state payload to detected gateway endpoint."""
        try:
            data = json.dumps(payload).encode('utf-8')
            req = urllib.request.Request(
                self.telemetry_endpoint,
                data=data,
                headers={'Content-Type': 'application/json'},
                method='POST'
            )
            with urllib.request.urlopen(req, timeout=2.0) as response:
                res = response.read().decode('utf-8')
                print(f"[HTTP] Telemetry Submit -> {self.telemetry_endpoint} (Pulse #{payload['pulse_counter']}): {res}")
        except Exception as e:
            print(f"[HTTP] Telemetry POST Warning ({self.telemetry_endpoint}): {e}")

    def run_continuous_loop(self, pulse_interval_sec: float = 3.0, report_frequency: int = 5):
        print(f"[*] Gateway IP Detected: {self.gateway_ip}")
        print(f"[*] Target Telemetry Endpoint: {self.telemetry_endpoint}")
        print(f"[*] FlameChain Loop Active (Interval: {pulse_interval_sec}s, POST every {report_frequency} pulses)...")
        
        signal.signal(signal.SIGINT, self.stop)
        signal.signal(signal.SIGTERM, self.stop)

        pulse_count = 0
        while self.running:
            pulse_count += 1
            
            compute_stats = self.telemetry.execute_compute_load(size_mb=3)
            ram_stats = self.telemetry.get_system_ram()
            accumulated_wh = self.telemetry.compute_watt_hours(compute_stats)
            
            if pulse_count % 10 == 0:
                next_shard = (self.shard_manager.active_shard_id % 4) + 1
                self.shard_manager.hot_swap_shard(next_shard)

            shard_stats = self.shard_manager.update_shard_state(compute_stats["payload_hash"])

            node_state = {
                "flamechain_node_id": f"node_tab_{socket.gethostname()}",
                "timestamp_utc": time.time(),
                "pulse_counter": pulse_count,
                "detected_gateway_ip": self.gateway_ip,
                "hardware_telemetry": {
                    "sysctl_ram": ram_stats,
                    "compute_pulse": compute_stats
                },
                "economics": {
                    "currency_backing": "Watt-Hours",
                    "accumulated_watt_hours": accumulated_wh,
                    "minted_flame_units": round(accumulated_wh * 1000.0, 4)
                },
                "tensor_shard_state": shard_stats
            }

            with open("node_state.json", "w") as f:
                json.dump(node_state, f, indent=2)

            print(f"[Pulse #{pulse_count}] RAM Used: {ram_stats['used_mb']} MB | "
                  f"Watt-Hours: {accumulated_wh:.8f} Wh | "
                  f"Shard: {shard_stats['active_shard_id']}")

            if pulse_count % report_frequency == 0:
                self.send_telemetry_snapshot(node_state)

            time.sleep(pulse_interval_sec)

if __name__ == "__main__":
    runner = FlameChainNodeRunner()
    if len(sys.argv) > 1 and sys.argv[1] == "--oneshot":
        runner.run_continuous_loop(pulse_interval_sec=0.1, report_frequency=1)
    else:
        runner.run_continuous_loop(pulse_interval_sec=2.0, report_frequency=5)
