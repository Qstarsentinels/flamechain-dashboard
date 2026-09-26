#!/usr/bin/env python3
"""
FlameChain Ingress Gateway
Subclasses http.server.BaseHTTPRequestHandler to ingest telemetry payloads
and serve the index.html monitoring dashboard.
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
            "minted_flame_units": 0.0,
            "accumulated_watt_hours": 0.0,
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
            "minted_flame_units": 0.0,
            "accumulated_watt_hours": 0.0,
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

class FlameChainServer(BaseHTTPRequestHandler):

    def log_message(self, format, *args):
        sys.stdout.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {self.address_string()} - {format % args}\n")
        sys.stdout.flush()

    def _send_json(self, status_code, payload):
        body = json.dumps(payload).encode("utf-8")
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
                self.send_error(500, f"Error reading index.html: {str(e)}")

        elif self.path == "/global_network_state.json" or self.path.startswith("/global_network_state.json?"):
            state = load_network_state()
            self._send_json(200, state)

        else:
            self.send_error(404, "Endpoint not found")

    def do_POST(self):
        if self.path == "/telemetry/submit":
            try:
                content_length = int(self.headers.get("Content-Length", 0))
                if content_length == 0:
                    self._send_json(400, {"status": "error", "message": "Empty body"})
                    return

                raw_data = self.rfile.read(content_length)
                payload = json.loads(raw_data.decode("utf-8"))

                node_id = payload.get("node_id", f"node_{int(time.time())}")
                watt_hours = float(payload.get("watt_hours_contributed", payload.get("watt_hours", payload.get("wh", 0.0))))
                ram_allocated = float(payload.get("ram_allocated_mb", payload.get("allocated_ram", 0.0)))
                minted_balance = float(payload.get("minted_balance", payload.get("minted", 0.0)))
                pulse_count = int(payload.get("total_pulses", payload.get("pulse", 0)))
                device_model = payload.get("device_model", "Generic Mesh Edge Node")
                active_shards = payload.get("active_shards", [])

                state = load_network_state()
                if "nodes" not in state or not isinstance(state["nodes"], dict):
                    state["nodes"] = {}

                state["nodes"][node_id] = {
                    "device_model": device_model,
                    "watt_hours": watt_hours,
                    "wh": watt_hours,
                    "ram_allocated_mb": ram_allocated,
                    "active_shards": active_shards,
                    "minted_balance": minted_balance,
                    "pulse": pulse_count,
                    "last_seen": time.time(),
                    "status": "ONLINE"
                }

                total_supply = sum(n.get("minted_balance", 0.0) for n in state["nodes"].values())
                total_wh = sum(n.get("watt_hours", n.get("wh", 0.0)) for n in state["nodes"].values())
                total_ram = sum(n.get("ram_allocated_mb", 0.0) for n in state["nodes"].values())

                state["minted_flame_units"] = round(total_supply, 8)
                state["accumulated_watt_hours"] = round(total_wh, 6)
                state["total_gross_supply"] = round(total_supply, 8)
                state["total_watt_hours"] = round(total_wh, 6)
                state["total_allocated_ram_mb"] = round(total_ram, 2)
                state["last_updated"] = time.time()

                save_network_state(state)

                self._send_json(200, {
                    "status": "success",
                    "code": 200,
                    "node_id": node_id,
                    "minted_flame_units": state["minted_flame_units"],
                    "accumulated_watt_hours": state["accumulated_watt_hours"],
                    "active_nodes": len(state["nodes"])
                })

            except Exception as e:
                self._send_json(500, {"status": "error", "message": str(e)})
        else:
            self.send_error(404, "Endpoint not found")

def run():
    server_address = (HOST, PORT)
    httpd = HTTPServer(server_address, FlameChainServer)
    print(f"[+] FlameChain Ingress Server bound and listening on {HOST}:{PORT}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[-] Shutting down gateway server...")
        httpd.server_close()

if __name__ == "__main__":
    run()
