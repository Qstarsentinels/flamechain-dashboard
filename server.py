#!/usr/bin/env python3
"""
FlameChain - Edge Node Distribution & Telemetry Server
File: server.py
Architect: Lead Systems Architect
Port: 8546
"""

import os
import sys
import json
import time
from http.server import HTTPServer, BaseHTTPRequestHandler

PORT = 8546
SOURCE_FILE = "ipad_node.py"
TELEMETRY_LOG_FILE = "latest_telemetry.json"

class FlameChainDistServer(BaseHTTPRequestHandler):
    """HTTP Request Handler for FlameChain node code distribution and telemetry ingest."""
    
    def _send_cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, HEAD, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def do_OPTIONS(self):
        self.send_response(204)
        self._send_cors_headers()
        self.end_headers()

    def _handle_download_request(self, send_body: bool = True):
        if self.path == "/download/ios_node.py":
            if os.path.exists(SOURCE_FILE):
                try:
                    file_size = os.path.getsize(SOURCE_FILE)
                    self.send_response(200)
                    self.send_header("Content-Type", "text/x-python")
                    self.send_header("Content-Length", str(file_size))
                    self._send_cors_headers()
                    self.end_headers()
                    
                    if send_body:
                        with open(SOURCE_FILE, "rb") as f:
                            self.wfile.write(f.read())
                except Exception as err:
                    self.send_error(500, f"Internal Server Error: {str(err)}")
            else:
                self.send_error(404, f"Source file '{SOURCE_FILE}' not found.")
        else:
            self.send_error(404, "Endpoint Not Found. Valid routes: /download/ios_node.py, /telemetry/submit")

    def do_GET(self):
        self._handle_download_request(send_body=True)

    def do_HEAD(self):
        self._handle_download_request(send_body=False)

    def do_POST(self):
        if self.path == "/telemetry/submit":
            try:
                content_length = int(self.headers.get("Content-Length", 0))
                post_body = self.rfile.read(content_length)
                telemetry_data = json.loads(post_body.decode("utf-8"))

                # Persist telemetry state locally
                with open(TELEMETRY_LOG_FILE, "w") as f:
                    json.dump(telemetry_data, f, indent=2)

                pulse = telemetry_data.get("pulse_counter", 0)
                node_id = telemetry_data.get("flamechain_node_id", "unknown")

                response_payload = {
                    "status": "success",
                    "acknowledged_at": time.time(),
                    "node_id": node_id,
                    "received_pulse": pulse
                }

                data_bytes = json.dumps(response_payload).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data_bytes)))
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(data_bytes)

            except Exception as e:
                err_bytes = json.dumps({"status": "error", "message": str(e)}).encode("utf-8")
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(err_bytes)))
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(err_bytes)
        else:
            self.send_error(404, "Endpoint Not Found.")

    def log_message(self, format, *args):
        sys.stdout.write(f"[{self.log_date_time_string()}] {self.client_address[0]} -> {format % args}\n")

def run_server(port: int = PORT):
    server_address = ('', port)
    httpd = HTTPServer(server_address, FlameChainDistServer)
    print(f"[*] FlameChain Telemetry & Code Server active on port {port}...")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[*] Terminating Server...")
        httpd.server_close()

if __name__ == "__main__":
    run_server()
