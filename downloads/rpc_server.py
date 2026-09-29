
from http.server import HTTPServer, BaseHTTPRequestHandler

import json

import os



STATE_FILE = "flamechain_live_state.json"

PORT = 8545



class FlameChainRPC(BaseHTTPRequestHandler):

    def do_GET(self):

        self.send_response(200)

        self.send_header("Content-Type", "application/json")

        self.end_headers()

        if os.path.exists(STATE_FILE):

            with open(STATE_FILE, "r") as f:

                data = json.load(f)

        else:

            data = {"status": "FlameChain devnet initialized"}

        self.wfile.write(json.dumps(data).encode())



def run_rpc_server():

    server = HTTPServer(("0.0.0.0", PORT), FlameChainRPC)

    print(f"[*] FlameChain JSON-RPC Server active on port {PORT}...")

    server.serve_forever()



if __name__ == "__main__":

    run_rpc_server()

