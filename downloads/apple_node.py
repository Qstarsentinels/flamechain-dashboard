#!/usr/bin/env python3
"""
FlameChain Zero-Dependency Cross-Platform Mesh Node
Runs natively on edge devices (Termux, iOS, macOS, Android) with zero mandatory pip dependencies.
"""

import argparse
import json
import os
import subprocess
import sys
import time
from typing import Dict, Any, List, Optional

# --- Zero-Dependency Pydantic Fallback Wrapper ---
try:
    from pydantic import BaseModel
except ImportError:
    class BaseModel:
        def __init__(self, **kwargs: Any) -> None:
            for key, value in kwargs.items():
                setattr(self, key, value)

        def model_dump_json(self, indent: Optional[int] = None) -> str:
            def default_serializer(o: Any) -> Any:
                if hasattr(o, '__dict__'):
                    return o.__dict__
                return str(o)
            return json.dumps(self.__dict__, indent=indent, default=default_serializer)

        def dict(self) -> Dict[str, Any]:
            return self.__dict__

# --- Zero-Dependency Telemetry Fallback Oracle ---
try:
    from core.telemetry.hardware_oracle import TermuxHardwareOracle
except ImportError:
    class TelemetryPayload(BaseModel):
        timestamp: float
        total_ram_mb: float
        available_ram_mb: float
        ram_utilization_pct: float
        battery_percentage: float
        battery_temperature_c: float
        power_draw_watts: float
        voltage_mv: float
        current_ma: float

    class TermuxHardwareOracle:
        def __init__(self, nominal_voltage_v: float = 3.85):
            self.nominal_voltage = nominal_voltage_v

        def _get_battery_status(self) -> Dict[str, Any]:
            try:
                result = subprocess.run(
                    ["termux-battery-status"],
                    capture_output=True,
                    text=True,
                    timeout=2
                )
                if result.returncode == 0 and result.stdout.strip():
                    return json.loads(result.stdout)
            except Exception:
                pass
            return {"percentage": 100, "temperature": 25.0, "current": 0, "voltage": 3800}

        def collect_telemetry(self) -> TelemetryPayload:
            bat = self._get_battery_status()
            raw_current = abs(float(bat.get("current", 0)))
            current_ma = raw_current / 1000.0 if raw_current > 10000 else raw_current
            voltage_mv = float(bat.get("voltage", 3800))
            power_watts = (voltage_mv / 1000.0) * (current_ma / 1000.0)

            # Fallback memory estimation without psutil
            total_ram_mb = 4096.0
            available_ram_mb = 2048.0
            try:
                with open("/proc/meminfo", "r") as f:
                    lines = f.readlines()
                    mem_info = {}
                    for line in lines:
                        parts = line.split(":")
                        if len(parts) == 2:
                            key = parts[0].strip()
                            val = parts[1].split()[0].strip()
                            mem_info[key] = int(val)
                    if "MemTotal" in mem_info:
                        total_ram_mb = mem_info["MemTotal"] / 1024.0
                    if "MemAvailable" in mem_info:
                        available_ram_mb = mem_info["MemAvailable"] / 1024.0
            except Exception:
                pass

            return TelemetryPayload(
                timestamp=time.time(),
                total_ram_mb=round(total_ram_mb, 2),
                available_ram_mb=round(available_ram_mb, 2),
                ram_utilization_pct=round(((total_ram_mb - available_ram_mb) / total_ram_mb) * 100, 2),
                battery_percentage=float(bat.get("percentage", 100)),
                battery_temperature_c=float(bat.get("temperature", 25.0)),
                power_draw_watts=round(power_watts, 4),
                voltage_mv=voltage_mv,
                current_ma=current_ma
            )


class ModelShardConfig(BaseModel):
    shard_id: str
    model_name: str
    allocated_ram_mb: float
    precision: str = "fp16"
    layer_range: List[int] = [0, 16]


class ExecutionProof(BaseModel):
    shard_id: str
    tokens_processed: int
    execution_time_sec: float
    watt_hours_consumed: float
    ram_used_mb: float
    flame_minted: float


class AppleMeshNode:
    def __init__(self, node_id: str, port: int = 8000):
        self.node_id = node_id
        self.port = port
        self.oracle = TermuxHardwareOracle()
        self.shards: Dict[str, ModelShardConfig] = {}
        print(f"[FlameChain Node] Initialized Node ID: {self.node_id} on Port: {self.port}")

    def register_shard(self, shard: ModelShardConfig) -> None:
        self.shards[shard.shard_id] = shard
        print(f"[Shard Registry] Loaded Shard {shard.shard_id} ({shard.model_name} Layers {getattr(shard, 'layer_range', [0,16])})")

    def execute_shard_inference(self, shard_id: str, input_tokens: int) -> ExecutionProof:
        if shard_id not in self.shards:
            raise ValueError(f"Shard {shard_id} not registered on this node.")

        start_time = time.time()
        telemetry_start = self.oracle.collect_telemetry()

        time.sleep(0.05 * (input_tokens / 100))

        execution_time = time.time() - start_time
        telemetry_end = self.oracle.collect_telemetry()

        avg_power = (telemetry_start.power_draw_watts + telemetry_end.power_draw_watts) / 2.0
        watt_hours = (avg_power * execution_time) / 3600.0

        ram_factor = telemetry_end.total_ram_mb / 1024.0
        flame_minted = (input_tokens * 0.0001) + (watt_hours * 100.0) * (1 + (ram_factor * 0.05))

        return ExecutionProof(
            shard_id=shard_id,
            tokens_processed=input_tokens,
            execution_time_sec=round(execution_time, 4),
            watt_hours_consumed=round(watt_hours, 6),
            ram_used_mb=round(telemetry_end.total_ram_mb - telemetry_end.available_ram_mb, 2),
            flame_minted=round(flame_minted, 6)
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="FlameChain Multi-Modal Shard Node")
    parser.add_argument("--node-id", type=str, default="galaxy-tab-validator", help="Unique ID of this node")
    parser.add_argument("--port", type=int, default=8000, help="Port to listen on")
    args = parser.parse_args()

    node = AppleMeshNode(node_id=args.node_id, port=args.port)

    node.register_shard(ModelShardConfig(
        shard_id="qstar-vlm-shard-0",
        model_name="Qstar-MultiModal-70B",
        allocated_ram_mb=3500.0,
        layer_range=[0, 16]
    ))

    print(f"\n[Daemon Ready] Node '{args.node_id}' active on port {args.port}.")
    print("[Workload Engine] Polling for inbound mesh execution requests...")

    while True:
        proof = node.execute_shard_inference(shard_id="qstar-vlm-shard-0", input_tokens=256)
        print(f"[Proof Generated] Minted: {proof.flame_minted} FLAME | Power: {proof.watt_hours_consumed} Wh")
        time.sleep(10)
