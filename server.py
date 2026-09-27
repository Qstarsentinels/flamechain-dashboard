import os
import json
from http.server import HTTPServer, BaseHTTPRequestHandler

AGENT_CONTEXT_FILE = "agent_context.json"

class FlameChainRequestHandler(BaseHTTPRequestHandler):

    def _set_headers(self, status_code=200, content_type="application/json"):
        self.send_response(status_code)
        self.send_header("Content-Type", content_type)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_OPTIONS(self):
        self._set_headers(200)

    def do_GET(self):
        if self.path == "/api/agent-context":
            if not os.path.exists(AGENT_CONTEXT_FILE):
                self._set_headers(404)
                response = {"error": f"File '{AGENT_CONTEXT_FILE}' not found."}
                self.wfile.write(json.dumps(response).encode("utf-8"))
                return

            try:
                with open(AGENT_CONTEXT_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                
                self._set_headers(200)
                self.wfile.write(json.dumps(data).encode("utf-8"))
            except json.JSONDecodeError:
                self._set_headers(500)
                response = {"error": "Invalid JSON format in agent_context.json."}
                self.wfile.write(json.dumps(response).encode("utf-8"))
            except Exception as e:
                self._set_headers(500)
                response = {"error": str(e)}
                self.wfile.write(json.dumps(response).encode("utf-8"))
        else:
            self._set_headers(404)
            response = {"error": "Route not found"}
            self.wfile.write(json.dumps(response).encode("utf-8"))

def run_server(host="0.0.0.0", port=8080):
    server_address = (host, port)
    httpd = HTTPServer(server_address, FlameChainRequestHandler)
    print(f"FlameChain Node Server listening on http://{host}:{port}")
    httpd.serve_forever()

if __name__ == "__main__":
    run_server()
