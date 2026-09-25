#!/usr/bin/env python3
"""
FlameChain - Edge Node Distribution Server
File: server.py
Architect: Lead Systems Architect
Port: 8546
"""

import os
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler

PORT = 8546
SOURCE_FILE = "ipad_node.py"

class FlameChainDistServer(BaseHTTPRequestHandler):
    """HTTP Request Handler for FlameChain node code provisioning."""
    
    def do_GET(self):
        if self.path == "/download/ios_node.py":
            if os.path.exists(SOURCE_FILE):
                try:
                    with open(SOURCE_FILE, "rb") as f:
                        payload = f.read()
                    
                    self.send_response(200)
                    self.send_header("Content-Type", "text/x-python")
                    self.send_header("Content-Length", str(len(payload)))
                    self.send_header("Access-Control-Allow-Origin", "*")
                    self.end_headers()
                    self.wfile.write(payload)
                except Exception as err:
                    self.send_error(500, f"Internal Server Error: {str(err)}")
            else:
                self.send_error(404, f"Source payload file '{SOURCE_FILE}' not found on host.")
        else:
            self.send_error(404, "Endpoint Not Found. Valid route: /download/ios_node.py")

    def log_message(self, format, *args):
        sys.stdout.write(f"[{self.log_date_time_string()}] {self.client_address[0]} -> {format % args}\n")

def run_server(port: int = PORT):
    server_address = ('', port)
    httpd = HTTPServer(server_address, FlameChainDistServer)
    print(f"[*] FlameChain Distribution Server active on port {port}...")
    print(f"[*] Route exposed: http://0.0.0.0:{port}/download/ios_node.py -> serving local '{SOURCE_FILE}'")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[*] Terminating FlameChain Distribution Server...")
        httpd.server_close()

if __name__ == "__main__":
    run_server()
