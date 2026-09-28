#!/usr/bin/env python3
"""
FlameChain Central Mesh Server & Telemetry Aggregator
Target Runtime: Termux / Galaxy Tab Prime Node (Port 8080)
"""

import json
import threading
import time
from http.server import HTTPServer, BaseHTTPRequestHandler

# Thread-safe telemetry state store
MESH_LOCK = threading.Lock()
ACTIVE_NODES = {}


class FlameChainServer(BaseHTTPRequestHandler):

    def _send_json(self, data: dict, status=200):
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))

    def do_POST(self):
        if self.path == '/api/telemetry':
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length)

            try:
                payload = json.loads(body.decode('utf-8'))
                node_id = payload.get("node_id", "UNKNOWN-NODE")

                with MESH_LOCK:
                    ACTIVE_NODES[node_id] = {
                        "ram_mb": payload.get("ram_mb", 0.0),
                        "wh": payload.get("wh", 0.0),
                        "flame": payload.get("flame", 0.0),
                        "shard": payload.get("shard", "SHARD-UNKNOWN"),
                        "last_seen": time.time()
                    }

                self._send_json({"status": "acknowledged", "node_id": node_id})
            except Exception as e:
                self._send_json({"error": f"Invalid payload: {str(e)}"}, status=400)
        else:
            self._send_json({"error": "Endpoint not found"}, status=404)

    def do_GET(self):
        if self.path == '/api/agent-context':
            now = time.time()
            with MESH_LOCK:
                # Prune inactive nodes (> 30s timeout) and calculate totals
                total_ram = 0.0
                total_wh = 0.0
                total_flame = 0.0
                active_count = 0

                for nid, stats in list(ACTIVE_NODES.items()):
                    if now - stats["last_seen"] < 30:
                        total_ram += stats["ram_mb"]
                        total_wh += stats["wh"]
                        total_flame += stats["flame"]
                        active_count += 1

            # Unified context block for downstream singularity agents
            context = {
                "timestamp": now,
                "mesh_status": "ONLINE",
                "active_nodes_count": active_count,
                "combined_metrics": {
                    "total_ram_mb": round(total_ram, 2),
                    "total_watt_hours": round(total_wh, 6),
                    "total_flame_supply": round(total_flame, 6)
                },
                "agents": {
                    "FlameGPT": {
                        "role": "Mesh Dialogue & Primary Logic Synthesis",
                        "status": "ACTIVE",
                        "context_window_ram": f"{round(total_ram * 0.4, 2)}MB allocated"
                    },
                    "Sovereign LLM": {
                        "role": "Local Edge Inference & Off-Grid Reasoning",
                        "status": "ACTIVE",
                        "target_shard": "SHARD-0X-HOTSWAP-ACTIVE"
                    },
                    "Oracle": {
                        "role": "Watt-Hour Proof Verification & Energy Ingestion",
                        "status": "ACTIVE",
                        "verified_energy_wh": round(total_wh, 6)
                    },
                    "Alchemist": {
                        "role": "RAM-to-Token Liquidity Balancing & Minting Engine",
                        "status": "ACTIVE",
                        "minted_flame_supply": round(total_flame, 6)
                    },
                    "Sentinel": {
                        "role": "Mesh Fault Injection, Health & Consensus Guard",
                        "status": "ACTIVE",
                        "health": "OPTIMAL" if active_count > 0 else "DEGRADED_LOCAL_ONLY"
                    }
                }
            }
            self._send_json(context)
        else:
            self._send_json({"error": "Endpoint not found"}, status=404)

    def log_message(self, format, *args):
        # Silence default HTTP server logging to keep standard output clean
        return


def run_server(host='0.0.0.0', port=8080):
    server = HTTPServer((host, port), FlameChainServer)
    print(f"[FLAMECHAIN SERVER] Mesh HTTP REST Engine Listening on {host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    run_server()
