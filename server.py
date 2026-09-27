import os
import json
from http.server import HTTPServer, BaseHTTPRequestHandler

class FlameChainNodeHandler(BaseHTTPRequestHandler):
    """
    Ultra-lightweight HTTP handler for FlameChain telemetry and AGI agent state.
    Designed for low RAM overhead on Android Galaxy Tab Termux nodes.
    """
    
    def _set_cors_headers(self, status_code=200, content_type="application/json"):
        self.send_response(status_code)
        self.send_header("Content-Type", content_type)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_OPTIONS(self):
        self._set_cors_headers(200)

    def do_GET(self):
        if self.path == "/api/agent-context":
            context_file = "agent_context.json"
            
            if os.path.exists(context_file):
                try:
                    with open(context_file, "r", encoding="utf-8") as f:
                        payload = json.load(f)
                    
                    self._set_cors_headers(200)
                    self.wfile.write(json.dumps(payload).encode("utf-8"))
                except Exception as err:
                    self._set_cors_headers(500)
                    error_payload = {"status": "error", "message": f"Failed reading context: {str(err)}"}
                    self.wfile.write(json.dumps(error_payload).encode("utf-8"))
            else:
                self._set_cors_headers(404)
                error_payload = {"status": "error", "message": "agent_context.json not found"}
                self.wfile.write(json.dumps(error_payload).encode("utf-8"))
        else:
            self._set_cors_headers(404)
            self.wfile.write(json.dumps({"status": "error", "message": "Endpoint not found"}).encode("utf-8"))

    def log_message(self, format, *args):
        # Suppress routine GET logging to save log IO overhead on flash storage
        pass

def run_server(host="0.0.0.0", port=8080):
    server_address = (host, port)
    httpd = HTTPServer(server_address, FlameChainNodeHandler)
    print(f"[FlameChain Node] Serving endpoint /api/agent-context on http://{host}:{port}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[FlameChain Node] Telemetry server shutting down gracefully.")
        httpd.server_close()

if __name__ == "__main__":
    run_server()
