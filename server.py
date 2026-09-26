#!/usr/bin/env python3
"""
FlameChain Global Network State Sync & Telemetry Server
Listens on ('0.0.0.0', 8546)
Receives validator node telemetry via POST /telemetry/submit,
updates global aggregate metrics, and serves HTTP GET endpoints for dashboard UI.
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

class FlameChainServer(http.server.BaseHTTPRequestHandler):
    def _set_cors_headers(self, status=HTTPStatus.OK, content_type="application/json"):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()

    def do_OPTIONS(self):
        """Respond to CORS preflight requests."""
        self._set_cors_headers(HTTPStatus.OK)

    def do_GET(self):
        """Serve GET / (index.html) and GET /state or /global_network_state.json."""
        path = self.path.split('?')[0]

        if path in ["/", "/index.html"]:
            if os.path.exists(INDEX_FILE):
                try:
                    with open(INDEX_FILE, "rb") as f:
                        content = f.read()
                    self._set_cors_headers(HTTPStatus.OK, content_type="text/html; charset=utf-8")
                    self.wfile.write(content)
                except Exception as e:
                    self._set_cors_headers(HTTPStatus.INTERNAL_SERVER_ERROR)
                    self.wfile.write(json.dumps({"error": f"Failed to serve dashboard: {str(e)}"}).encode('utf-8'))
            else:
                self._set_cors_headers(HTTPStatus.NOT_FOUND, content_type="text/html; charset=utf-8")
                fallback_html = "<html><body><h1>FlameChain Node Server</h1><p>index.html missing.</p></body></html>"
                self.wfile.write(fallback_html.encode('utf-8'))

        elif path in ["/state", "/global_network_state.json", "/api/state"]:
            with file_lock:
                if not os.path.exists(STATE_FILE):
                    empty_state = {
                        "active_nodes": {},
                        "total_active_nodes": 0,
                        "total_network_wh": 0.0,
                        "total_network_flame": 0.0,
                        "last_updated": time.time()
                    }
                    self._set_cors_headers(HTTPStatus.OK)
                    self.wfile.write(json.dumps(empty_state).encode('utf-8'))
                    return

                try:
                    with open(STATE_FILE, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    self._set_cors_headers(HTTPStatus.OK)
                    self.wfile.write(json.dumps(data).encode('utf-8'))
                except Exception as e:
                    self._set_cors_headers(HTTPStatus.INTERNAL_SERVER_ERROR)
                    self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))

        else:
            self._set_cors_headers(HTTPStatus.NOT_FOUND)
            self.wfile.write(json.dumps({"error": "Endpoint not found"}).encode('utf-8'))

    def do_POST(self):
        """Process validator telemetry updates via POST /telemetry/submit."""
        path = self.path.split('?')[0]

        if path in ["/telemetry/submit", "/telemetry"]:
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length == 0:
                self._set_cors_headers(HTTPStatus.BAD_REQUEST)
                self.wfile.write(json.dumps({"error": "Empty telemetry payload"}).encode('utf-8'))
                return

            post_data = self.rfile.read(content_length)

            try:
                payload = json.loads(post_data.decode('utf-8'))
            except json.JSONDecodeError:
                self._set_cors_headers(HTTPStatus.BAD_REQUEST)
                self.wfile.write(json.dumps({"error": "Malformed JSON in request body"}).encode('utf-8'))
                return

            with file_lock:
                # Load existing network state or initialize default structure
                global_state = {
                    "active_nodes": {},
                    "total_active_nodes": 0,
                    "total_network_wh": 0.0,
                    "total_network_flame": 0.0,
                    "last_updated": time.time()
                }

                if os.path.exists(STATE_FILE):
                    try:
                        with open(STATE_FILE, "r", encoding="utf-8") as f:
                            loaded = json.load(f)
                            if isinstance(loaded, dict):
                                global_state.update(loaded)
                                if "active_nodes" not in global_state or not isinstance(global_state["active_nodes"], dict):
                                    global_state["active_nodes"] = {}
                    except json.JSONDecodeError:
                        pass

                # Extract telemetry attributes
                node_id = payload.get("node_id") or "node_unknown"
                ram = float(payload.get("ram", 0.0))
                watt_hours = float(payload.get("watt_hours", 0.0))
                shard_id = payload.get("shard_id") or payload.get("active_shard_id") or "shard_0_vision_encoder.bin"
                minted_flame = float(payload.get("minted_flame", 0.0))
                state_root = payload.get("state_root", "")
                last_seen = float(payload.get("last_seen", time.time()))

                # Upsert active node record
                global_state["active_nodes"][node_id] = {
                    "node_id": node_id,
                    "ram_mb": ram,
                    "watt_hours": watt_hours,
                    "minted_flame": minted_flame,
                    "shard_id": shard_id,
                    "state_root": state_root,
                    "last_seen": last_seen
                }

                # Compute network-wide aggregate stats
                nodes_dict = global_state["active_nodes"]
                global_state["total_active_nodes"] = len(nodes_dict)
                global_state["total_network_wh"] = round(sum(n.get("watt_hours", 0.0) for n in nodes_dict.values()), 6)
                global_state["total_network_flame"] = round(sum(n.get("minted_flame", 0.0) for n in nodes_dict.values()), 4)
                global_state["last_updated"] = time.time()

                # Atomically write state to disk
                tmp_file = f"{STATE_FILE}.tmp"
                try:
                    with open(tmp_file, "w", encoding="utf-8") as f:
                        json.dump(global_state, f, indent=2)
                    os.replace(tmp_file, STATE_FILE)

                    self._set_cors_headers(HTTPStatus.OK)
                    response_payload = {
                        "status": "acknowledged",
                        "node_id": node_id,
                        "network_active_nodes": global_state["total_active_nodes"],
                        "total_network_wh": global_state["total_network_wh"],
                        "total_network_flame": global_state["total_network_flame"],
                        "timestamp": global_state["last_updated"]
                    }
                    self.wfile.write(json.dumps(response_payload).encode('utf-8'))
                except Exception as e:
                    self._set_cors_headers(HTTPStatus.INTERNAL_SERVER_ERROR)
                    self.wfile.write(json.dumps({"error": f"Failed to persist state: {str(e)}"}).encode('utf-8'))

        else:
            self._set_cors_headers(HTTPStatus.NOT_FOUND)
            self.wfile.write(json.dumps({"error": f"Path '{path}' not found"}).encode('utf-8'))

    def log_message(self, format, *args):
        # Clean single line log format
        print(f"[FlameChain Server] {self.address_string()} - {format % args}")

def run_server():
    server_address = (HOST, PORT)
    httpd = http.server.ThreadingHTTPServer(server_address, FlameChainServer)
    print("==================================================")
    print(f"   FLAMECHAIN GLOBAL AGGREGATOR SERVER ONLINE   ")
    print("==================================================")
    print(f" Binding Address : http://{HOST}:{PORT}")
    print(f" Telemetry URL   : http://{HOST}:{PORT}/telemetry/submit")
    print(f" Dashboard URL   : http://{HOST}:{PORT}/")
    print("==================================================\n")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[-] Server shutting down gracefully.")
        httpd.server_close()

if __name__ == '__main__':
    run_server()
