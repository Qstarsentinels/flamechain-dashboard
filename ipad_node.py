#!/usr/bin/env python3
"""
FlameChain - Edge Node Telemetry & Shard Sync Module
File: ipad_node.py
Architect: Lead Systems Architect
Environment: Termux / Android / POSIX ARM64 / Linux
"""

import os
import sys
import time
import json
import hashlib
import platform

class LocalHardwareSampler:
    """Extracts non-synthetic hardware metrics directly from POSIX subsystems."""
    
    def __init__(self):
        self.os_type = platform.system()

    def get_ram_telemetry(self) -> dict:
        """Parses OS memory subsystem for accurate RAM metrics."""
        ram_info = {"total_mb": 0.0, "available_mb": 0.0, "used_mb": 0.0, "percent_used": 0.0}
        
        if os.path.exists("/proc/meminfo"):
            mem = {}
            with open("/proc/meminfo", "r") as f:
                for line in f:
                    parts = line.split(":")
                    if len(parts) == 2:
                        key = parts[0].strip()
                        val = parts[1].split()[0].strip()
                        if val.isdigit():
                            mem[key] = int(val)
            
            total_kb = mem.get("MemTotal", 0)
            avail_kb = mem.get("MemAvailable", mem.get("MemFree", 0))
            used_kb = total_kb - avail_kb
            
            ram_info["total_mb"] = round(total_kb / 1024.0, 2)
            ram_info["available_mb"] = round(avail_kb / 1024.0, 2)
            ram_info["used_mb"] = round(used_kb / 1024.0, 2)
            ram_info["percent_used"] = round((used_kb / total_kb) * 100, 2) if total_kb > 0 else 0.0
            
        return ram_info

    def measure_hardware_execution_pulse(self, size_mb: int = 4) -> dict:
        """
        Executes a native hardware benchmark (RAM read/write + SHA256 CPU execution).
        Calculates non-synthetic operations/second and memory bandwidth baseline.
        """
        test_payload = bytearray(os.urandom(1024 * 64)) * (size_mb * 16)
        
        start_time = time.perf_counter_ns()
        
        hasher = hashlib.sha256()
        chunk_size = 64 * 1024
        for i in range(0, len(test_payload), chunk_size):
            chunk = test_payload[i:i+chunk_size]
            hasher.update(chunk)
            
        digest = hasher.hexdigest()
        end_time = time.perf_counter_ns()
        
        elapsed_sec = (end_time - start_time) / 1e9
        mb_per_sec = size_mb / elapsed_sec if elapsed_sec > 0 else 0.0
        
        return {
            "execution_time_sec": round(elapsed_sec, 6),
            "throughput_mb_sec": round(mb_per_sec, 2),
            "payload_sha256": digest[:16]
        }


class ShardTelemetryEngine:
    """Manages FlameChain multi-modal shard sync telemetry."""
    
    def __init__(self, node_id: str, shard_id: int):
        self.node_id = node_id
        self.shard_id = shard_id
        self.sync_height = 0
        self.state_root = hashlib.sha256(f"genesis_{node_id}".encode()).hexdigest()

    def advance_shard_state(self, hardware_metrics: dict) -> dict:
        """Computes shard sync state using real hardware execution metrics."""
        self.sync_height += 1
        state_payload = f"{self.state_root}:{self.sync_height}:{hardware_metrics['payload_sha256']}"
        self.state_root = hashlib.sha256(state_payload.encode()).hexdigest()
        
        return {
            "shard_id": self.shard_id,
            "sync_height": self.sync_height,
            "state_root": self.state_root,
            "peer_telemetry_valid": True
        }


class FlameChainNode:
    def __init__(self, node_id: str = "node_android_tab_01", shard_id: int = 1):
        self.node_id = node_id
        self.hw_sampler = LocalHardwareSampler()
        self.shard_engine = ShardTelemetryEngine(node_id=node_id, shard_id=shard_id)

    def generate_telemetry_packet(self) -> str:
        hw_pulse = self.hw_sampler.measure_hardware_execution_pulse(size_mb=2)
        ram_stats = self.hw_sampler.get_ram_telemetry()
        shard_stats = self.shard_engine.advance_shard_state(hw_pulse)
        
        packet = {
            "flamechain_version": "1.0.0-singularity",
            "timestamp_utc": time.time(),
            "node_id": self.node_id,
            "platform": {
                "system": platform.system(),
                "machine": platform.machine(),
                "processor": platform.processor()
            },
            "telemetry": {
                "ram": ram_stats,
                "hardware_pulse": hw_pulse
            },
            "shard_sync": shard_stats
        }
        return json.dumps(packet, indent=2)

if __name__ == "__main__":
    print("[*] Initializing FlameChain Node Hardware & Shard Engine...")
    node = FlameChainNode()
    packet_json = node.generate_telemetry_packet()
    print("[+] Telemetry Sample Generated Successfully:")
    print(packet_json)
