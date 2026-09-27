import os
import json
from http.server import HTTPServer, BaseHTTPRequestHandler

HOST = "0.0.0.0"
PORT = 8546

class FlameChainNodeHandler(BaseHTTPRequestHandler):
    """
    FlameChain Mesh Telemetry & State Ingestion Server
    Optimized for low RAM / CPU overhead on Termux Android nodes.
    """

    def _set_headers(self, status_code=200, content_type="application/json"):
        self.send_response(status_code)
        self.send_header("Content-Type", content_type)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, User-Agent")
        self.end_headers()

    def do_OPTIONS(self):
        self._set_headers(200)

    def do_GET(self):
        if self.path == "/api/agent-context":
            self._serve_json_file("agent_context.json")
        elif self.path == "/api/state":
            if os.path.exists("global_network_state.json"):
                self._serve_json_file("global_network_state.json")
            else:
                self._serve_json_file("node_state.json")
        else:
            self._set_headers(404)
            self.wfile.write(json.dumps({"status": "error", "message": "Endpoint not found"}).encode("utf-8"))

    def do_POST(self):
        if self.path == "/telemetry/submit":
            try:
                content_length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(content_length)
                payload = json.loads(body.decode("utf-8"))

                self._ingest_telemetry(payload)

                self._set_headers(200)
                response = {"status": "success", "message": "Telemetry payload ingested"}
                self.wfile.write(json.dumps(response).encode("utf-8"))
            except Exception as err:
                self._set_headers(400)
                error_response = {"status": "error", "message": f"Invalid payload: {str(err)}"}
                self.wfile.write(json.dumps(error_response).encode("utf-8"))
        else:
            self._set_headers(404)
            self.wfile.write(json.dumps({"status": "error", "message": "Endpoint not found"}).encode("utf-8"))

    def _serve_json_file(self, filepath):
        if os.path.exists(filepath):
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self._set_headers(200)
                self.wfile.write(json.dumps(data).encode("utf-8"))
            except Exception as err:
                self._set_headers(500)
                err_payload = {"status": "error", "message": f"Failed reading state: {str(err)}"}
                self.wfile.write(json.dumps(err_payload).encode("utf-8"))
        else:
            self._set_headers(404)
            err_payload = {"status": "error", "message": f"{filepath} not found"}
            self.wfile.write(json.dumps(err_payload).encode("utf-8"))

    def _ingest_telemetry(self, payload):
        global_file = "global_network_state.json"
        data = {}
        if os.path.exists(global_file):
            try:
                with open(global_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                data = {}

        nodes = data.get("nodes", {})
        node_id = payload.get("node_id", "unknown_node")
        nodes[node_id] = payload

        data["nodes"] = nodes
        data["total_active_nodes"] = len(nodes)
        data["last_telemetry_submit"] = payload.get("timestamp")

        with open(global_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def log_message(self, format, *args):
        pass

def run_server():
    server_address = (HOST, PORT)
    httpd = HTTPServer(server_address, FlameChainNodeHandler)
    print(f"[FlameChain Telemetry Server] Active on http://{HOST}:{PORT}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[FlameChain Server] Shutting down gracefully...")
        httpd.server_close()

if __name__ == "__main__":
    run_server()
