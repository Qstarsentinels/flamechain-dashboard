
from http.server import HTTPServer, BaseHTTPRequestHandler

import json

import os



STATE_FILE = "flamechain_live_state.json"



class FlameChainGateway(BaseHTTPRequestHandler):

    def _set_headers(self):

        self.send_response(200)

        self.send_header('Content-type', 'application/json')

        self.end_headers()



    def do_GET(self):

        self._set_headers()

        if os.path.exists(STATE_FILE):

            with open(STATE_FILE, 'r') as f:

                state = json.load(f)

        else:

            state = {"status": "offline"}

        self.wfile.write(json.dumps(state).encode('utf-8'))



def run_gateway(port=8080):

    server_address = ('', port)

    httpd = HTTPServer(server_address, FlameChainGateway)

    print(f"[+] FlameChain Live Gateway running on port {port}...")

    httpd.serve_forever()



if __name__ == "__main__":

    run_gateway()

