#!/usr/bin/env python3
"""
FlameChain Global Network State Aggregator & Telemetry Server
Listens on port 8546.
Receives telemetry via POST /telemetry/submit.
Computes:
  - total_gross_supply = sum(minted_flame_units)
  - global_watt_hours = sum(accumulated_wh)
  - total_mesh_ram_mb = sum(total_mb_ram)
Serves API state via GET /api/state and /global_network_state.json.
Serves dashboard UI via GET /.
Full CORS support (*).
"""

import os
import sys
import json
import time
import threading
import http.server
from http import HTTPStatus

PORT = 8546
HOST = '0.0.0.0'
STATE_FILE = "global_network_state.json"
INDEX_FILE = "index.html"
file_lock = threading.Lock()

class FlameChainNetworkServer(http.server.BaseHTTPRequestHandler):
    def _set_headers(self, status=HTTPStatus.OK, content_type="application/json"):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()

    def do_OPTIONS(self):
        """CORS preflight handler."""
        self._set_headers(HTTPStatus.OK)

    def do_GET(self):
        path = self.path.split('?')[0]

        if path in ["/", "/index.html"]:
            if os.path.exists(INDEX_FILE):
                try:
                    with open(INDEX_FILE, "rb") as f:
                        content = f.read()
                    self._set_headers(HTTPStatus.OK, content_type="text/html; charset=utf-8")
                    self.wfile.write(content)
                except Exception as e:
                    self._set_headers(HTTPStatus.INTERNAL_SERVER_ERROR)
                    self.wfile.write(json.dumps({"error": f"Failed reading dashboard UI: {str(e)}"}).encode('utf-8'))
            else:
                self._set_headers(HTTPStatus.NOT_FOUND, content_type="text/html; charset=utf-8")
                self.wfile.write("<html><body><h1>FlameChain Telemetry Server</h1><p>index.html not found</p></body></html>".encode('utf-8'))

        elif path in ["/api/state", "/state", "/global_network_state.json"]:
            with file_lock:
                if not os.path.exists(STATE_FILE):
                    default_state = {
                        "active_nodes": {},
                        "total_active_nodes": 0,
                        "total_gross_supply": 0.0,
                        "global_watt_hours": 0.0,
                        "total_mesh_ram_mb": 0.0,
                        "last_updated": time.time()
                    }
                    self._set_headers(HTTPStatus.OK)
                    self.wfile.write(json.dumps(default_state, indent=2).encode('utf-8'))
                    return

                try:
                    with open(STATE_FILE, "r", encoding="utf-8") as f:
                        state_data = json.load(f)
                    self._set_headers(HTTPStatus.OK)
                    self.wfile.write(json.dumps(state_data, indent=2).encode('utf-8'))
                except Exception as e:
                    self._set_headers(HTTPStatus.INTERNAL_SERVER_ERROR)
                    self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))

        else:
            self._set_headers(HTTPStatus.NOT_FOUND)
            self.wfile.write(json.dumps({"error": "Path not found"}).encode('utf-8'))

    def do_POST(self):
        path = self.path.split('?')[0]

        if path in ["/telemetry/submit", "/telemetry"]:
            content_len = int(self.headers.get('Content-Length', 0))
            if content_len == 0:
                self._set_headers(HTTPStatus.BAD_REQUEST)
                self.wfile.write(json.dumps({"error": "Empty body"}).encode('utf-8'))
                return

            body = self.rfile.read(content_len)

            try:
                payload = json.loads(body.decode('utf-8'))
            except json.JSONDecodeError:
                self._set_headers(HTTPStatus.BAD_REQUEST)
                self.wfile.write(json.dumps({"error": "Invalid JSON format"}).encode('utf-8'))
                return

            # Extract fields from payload
            node_id = payload.get("node_id") or "node_unknown"
            ram_used_mb = float(payload.get("ram_used_mb", payload.get("ram", 0.0)))
            total_mb_ram = float(payload.get("total_mb_ram", payload.get("total_ram_mb", 4096.0)))
            accumulated_wh = float(payload.get("accumulated_wh", payload.get("watt_hours", 0.0)))
            minted_flame_units = float(payload.get("minted_flame_units", payload.get("minted_flame", 0.0)))
            active_shard_id = payload.get("active_shard_id", payload.get("shard_id", "shard_0_vision_encoder.bin"))
            pulse_count = int(payload.get("pulse_count", 0))
            timestamp = float(payload.get("timestamp", payload.get("last_seen", time.time())))

            with file_lock:
                current_state = {
                    "active_nodes": {},
                    "total_active_nodes": 0,
                    "total_gross_supply": 0.0,
                    "global_watt_hours": 0.0,
                    "total_mesh_ram_mb": 0.0,
                    "last_updated": time.time()
                }

                if os.path.exists(STATE_FILE):
                    try:
                        with open(STATE_FILE, "r", encoding="utf-8") as f:
                            data = json.load(f)
                            if isinstance(data, dict):
                                current_state.update(data)
                                if "active_nodes" not in current_state or not isinstance(current_state["active_nodes"], dict):
                                    current_state["active_nodes"] = {}
                    except json.JSONDecodeError:
                        pass

                # Upsert node record
                current_state["active_nodes"][node_id] = {
                    "node_id": node_id,
                    "ram_used_mb": ram_used_mb,
                    "total_mb_ram": total_mb_ram,
                    "accumulated_wh": accumulated_wh,
                    "minted_flame_units": minted_flame_units,
                    "active_shard_id": active_shard_id,
                    "pulse_count": pulse_count,
                    "timestamp": timestamp
                }

                # Compute aggregate sums
                nodes = current_state["active_nodes"].values()
                current_state["total_active_nodes"] = len(current_state["active_nodes"])
                current_state["total_gross_supply"] = round(sum(float(n.get("minted_flame_units", 0.0)) for n in nodes), 4)
                current_state["global_watt_hours"] = round(sum(float(n.get("accumulated_wh", 0.0)) for n in nodes), 6)
                current_state["total_mesh_ram_mb"] = round(sum(float(n.get("total_mb_ram", 0.0)) for n in nodes), 2)
                current_state["last_updated"] = time.time()

                # Atomically write updated state to disk
                tmp_path = f"{STATE_FILE}.tmp"
                try:
                    with open(tmp_path, "w", encoding="utf-8") as f:
                        json.dump(current_state, f, indent=2)
                    os.replace(tmp_path, STATE_FILE)

                    self._set_headers(HTTPStatus.OK)
                    response = {
                        "status": "success",
                        "node_id": node_id,
                        "network_aggregates": {
                            "total_active_nodes": current_state["total_active_nodes"],
                            "total_gross_supply": current_state["total_gross_supply"],
                            "global_watt_hours": current_state["global_watt_hours"],
                            "total_mesh_ram_mb": current_state["total_mesh_ram_mb"]
                        }
                    }
                    self.wfile.write(json.dumps(response).encode('utf-8'))
                except Exception as e:
                    self._set_headers(HTTPStatus.INTERNAL_SERVER_ERROR)
                    self.wfile.write(json.dumps({"error": f"Failed writing state: {str(e)}"}).encode('utf-8'))

        else:
            self._set_headers(HTTPStatus.NOT_FOUND)
            self.wfile.write(json.dumps({"error": "Unknown POST route"}).encode('utf-8'))

    def log_message(self, format, *args):
        print(f"[FlameChain Aggregator] {self.address_string()} - {format % args}")

def run():
    server_address = (HOST, PORT)
    httpd = http.server.ThreadingHTTPServer(server_address, FlameChainNetworkServer)
    print("==================================================")
    print(f"  FLAMECHAIN STATE AGGREGATOR RUNNING ON PORT {PORT}")
    print("==================================================")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[-] Aggregator shutting down.")
        httpd.server_close()

if __name__ == '__main__':
    run()
