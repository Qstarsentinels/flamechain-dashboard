#!/usr/bin/env python3
"""
FlameChain // Standard Library Ternary Matrix Quantization Engine
Handles 1.58-bit ternary matrix quantization (-1, 0, +1), trit packing/unpacking,
layer mapping across mesh nodes, and in-memory tensor shard hot-swapping.

STRICT REQUIREMENT: Standard library modules only (json, time, math).
"""

import json
import time
import math
from typing import List, Dict, Any, Tuple


class TernarySharder:
    """1.58-bit ternary matrix quantization and dynamic weight sharding engine."""

    TRITS_PER_BYTE = 5  # 3^5 = 243 <= 256 (1 byte limit)

    def __init__(self, state_file: str = "global_network_state.json"):
        self.state_file = state_file
        self.active_shards: Dict[str, Dict[str, Any]] = {}

    def quantize_matrix(self, matrix: List[List[float]], threshold_ratio: float = 0.5) -> Tuple[List[List[int]], float]:
        """
        Quantizes a 2D float matrix into 1.58-bit ternary representation {-1, 0, +1}
        using absolute mean scaling across non-zero values.
        """
        flat_weights = [val for row in matrix for val in row]
        if not flat_weights:
            return [], 1.0

        abs_sum = sum(abs(w) for w in flat_weights)
        abs_mean = abs_sum / len(flat_weights)
        scale = abs_mean if abs_mean > 1e-8 else 1.0

        quantized_matrix = []
        for row in matrix:
            q_row = []
            for w in row:
                scaled = w / scale
                if scaled > threshold_ratio:
                    q_row.append(1)
                elif scaled < -threshold_ratio:
                    q_row.append(-1)
                else:
                    q_row.append(0)
            quantized_matrix.append(q_row)

        return quantized_matrix, scale

    def pack_trits(self, trits: List[int]) -> bytearray:
        """Packs a list of trits {-1, 0, +1} into dense bytes (5 trits per byte)."""
        packed = bytearray()
        padding = (self.TRITS_PER_BYTE - (len(trits) % self.TRITS_PER_BYTE)) % self.TRITS_PER_BYTE
        padded = trits + [0] * padding

        for i in range(0, len(padded), self.TRITS_PER_BYTE):
            chunk = padded[i:i + self.TRITS_PER_BYTE]
            byte_val = 0
            multiplier = 1
            for trit in chunk:
                val = trit + 1  # Map {-1, 0, +1} -> {0, 1, 2}
                byte_val += val * multiplier
                multiplier *= 3
            packed.append(byte_val)

        return packed

    def unpack_trits(self, packed: bytearray, original_length: int) -> List[int]:
        """Unpacks dense bytes back into a ternary trit list {-1, 0, +1}."""
        trits = []
        for byte_val in packed:
            val = byte_val
            for _ in range(self.TRITS_PER_BYTE):
                trit_mapped = val % 3
                trits.append(trit_mapped - 1)  # Map back {0, 1, 2} -> {-1, 0, +1}
                val //= 3

        return trits[:original_length]

    def shard_layer_weights(self, total_layers: int, nodes: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Distributes model layers proportionally across active mesh nodes based on RAM capacity."""
        if not nodes:
            return {"status": "error", "message": "No active nodes available"}

        active_nodes = [n for n in nodes if n.get("status", "active") == "active"] or nodes
        total_ram = sum(float(n.get("ram_gb", 0)) for n in active_nodes) or 1.0

        shards = {}
        assigned_layers = 0
        sorted_nodes = sorted(active_nodes, key=lambda x: float(x.get("ram_gb", 0)), reverse=True)

        for idx, node in enumerate(sorted_nodes):
            node_id = node.get("node_id", f"node_{idx}")
            node_ram = float(node.get("ram_gb", 0))

            if idx == len(sorted_nodes) - 1:
                layer_count = total_layers - assigned_layers
            else:
                ratio = node_ram / total_ram
                layer_count = int(math.floor(ratio * total_layers))

            layer_range = (assigned_layers, assigned_layers + max(0, layer_count - 1)) if layer_count > 0 else None
            shard_id = f"shard_{node_id}_l{assigned_layers}-{assigned_layers + max(0, layer_count - 1)}"

            shard_info = {
                "shard_id": shard_id,
                "ram_gb": node_ram,
                "layer_count": layer_count,
                "layer_range": layer_range,
                "allocation_pct": round((node_ram / total_ram) * 100, 2),
                "status": "mounted",
                "timestamp": time.time()
            }

            shards[node_id] = shard_info
            self.active_shards[shard_id] = shard_info
            assigned_layers += layer_count

        return {
            "total_layers": total_layers,
            "total_ram_gb": total_ram,
            "shards": shards,
            "timestamp": time.time()
        }


if __name__ == "__main__":
    sharder = TernarySharder()
    test_matrix = [
        [0.85, -0.42, 0.01, -0.91],
        [0.12, 0.55, -0.05, 0.99]
    ]
    q_matrix, scale = sharder.quantize_matrix(test_matrix)
    flat_trits = [val for row in q_matrix for val in row]
    packed = sharder.pack_trits(flat_trits)
    unpacked = sharder.unpack_trits(packed, len(flat_trits))

    print("=== Ternary Sharder Self-Test ===")
    print(f"Original Matrix : {test_matrix}")
    print(f"Quantized 1.58b : {q_matrix}")
    assert flat_trits == unpacked, "Trit packing round-trip verification failed!"
    print("STATUS          : PASSED")
