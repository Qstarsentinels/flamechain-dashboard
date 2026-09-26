#!/usr/bin/env python3
"""
FlameChain Ingress Gateway
Subclasses http.server.BaseHTTPRequestHandler to ingest telemetry payloads
and serve the index.html monitoring UI.
"""

import json
import os
import sys
import time
from http.server import HTTPServer, BaseHTTPRequestHandler

HOST = "0.0.0.0"
PORT = 8546
STATE_FILE = "global_network_state.json"
INDEX_FILE = "index.html"

def load_network_state():
    if not os.path.exists(STATE_FILE):
        return {
            "total_gross_supply": 0.0,
            "total_watt_hours": 0.0,
            "total_allocated_ram_mb": 0.0,
            "last_updated": time.time(),
            "nodes": {}
        }
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {
            "total_gross_supply": 0.0,
            "total_watt_hours": 0.0,
            "total_allocated_ram_mb": 0.0,
            "last_updated": time.time(),
            "nodes": {}
        }

def save_network_state(state):
    temp_file = f"{STATE_FILE}.tmp"
    with open(temp_file, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=4)
    os.replace(temp_file, STATE_FILE)

class FlameChainGatewayHandler(BaseHTTPRequestHandler):

    def log_message(self, format, *args):
        sys.stdout.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {self.address_string()} - {format % args}\n")
        sys.stdout.flush()

    def _send_response_json(self, status_code, data):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            if not os.path.exists(INDEX_FILE):
                self.send_error(404, f"File {INDEX_FILE} not found.")
                return
            try:
                with open(INDEX_FILE, "rb") as f:
                    content = f.read()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(content)))
                self.end_headers()
                self.wfile.write(content)
            except Exception as e:
                self.send_error(500, f"Error loading index.html: {str(e)}")

        elif self.path == "/global_network_state.json" or self.path.startswith("/global_network_state.json?"):
            state = load_network_state()
            self._send_response_json(200, state)

        else:
            self.send_error(404, "Endpoint Not Found")

    def do_POST(self):
        if self.path == "/telemetry/submit":
            try:
                content_length = int(self.headers.get("Content-Length", 0))
                if content_length == 0:
                    self._send_response_json(400, {"status": "error", "message": "Empty payload"})
                    return

                raw_body = self.rfile.read(content_length)
                payload = json.loads(raw_body.decode("utf-8"))

                node_id = payload.get("node_id", f"node_{int(time.time())}")
                watt_hours = float(payload.get("watt_hours_contributed", payload.get("watt_hours", 0.0)))
                ram_allocated = float(payload.get("ram_allocated_mb", payload.get("allocated_ram", 0.0)))
                minted_balance = float(payload.get("minted_balance", payload.get("minted", 0.0)))
                device_model = payload.get("device_model", "Generic Mesh Node")
                active_shards = payload.get("active_shards", [])

                state = load_network_state()
                state["nodes"][node_id] = {
                    "device_model": device_model,
                    "watt_hours": watt_hours,
                    "ram_allocated_mb": ram_allocated,
                    "active_shards": active_shards,
                    "minted_balance": minted_balance,
                    "last_seen": time.time(),
                    "status": "active"
                }

                state["total_gross_supply"] = round(sum(n.get("minted_balance", 0.0) for n in state["nodes"].values()), 8)
                state["total_watt_hours"] = round(sum(n.get("watt_hours", 0.0) for n in state["nodes"].values()), 4)
                state["total_allocated_ram_mb"] = round(sum(n.get("ram_allocated_mb", 0.0) for n in state["nodes"].values()), 2)
                state["last_updated"] = time.time()

                save_network_state(state)

                self._send_response_json(200, {
                    "status": "ok",
                    "code": 200,
                    "node_id": node_id,
                    "global_gross_supply": state["total_gross_supply"],
                    "active_nodes": len(state["nodes"])
                })

            except Exception as e:
                self._send_response_json(500, {"status": "error", "message": str(e)})
        else:
            self.send_error(404, "Endpoint Not Found")

def run():
    server_address = (HOST, PORT)
    httpd = HTTPServer(server_address, FlameChainGatewayHandler)
    print(f"[+] FlameChain Server active on http://{HOST}:{PORT}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[-] Shutting down server...")
        httpd.server_close()

if __name__ == "__main__":
    run()
