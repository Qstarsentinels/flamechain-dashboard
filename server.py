import http.server
import json
import os
import time
import threading
from http import HTTPStatus

PORT = 8546
STATE_FILE = "global_network_state.json"
INDEX_FILE = "index.html"
file_lock = threading.Lock()

class FlameChainServer(http.server.BaseHTTPRequestHandler):
    def _set_headers(self, status=HTTPStatus.OK, content_type="application/json"):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_OPTIONS(self):
        self._set_headers(HTTPStatus.OK)

    def do_GET(self):
        path = self.path.split('?')[0]

        if path == "/" or path == "/index.html":
            if os.path.exists(INDEX_FILE):
                try:
                    with open(INDEX_FILE, "rb") as f:
                        content = f.read()
                    self._set_headers(HTTPStatus.OK, content_type="text/html; charset=utf-8")
                    self.wfile.write(content)
                except Exception as e:
                    self._set_headers(HTTPStatus.INTERNAL_SERVER_ERROR)
                    self.wfile.write(json.dumps({"error": f"Failed to read index.html: {str(e)}"}).encode('utf-8'))
            else:
                self._set_headers(HTTPStatus.NOT_FOUND, content_type="text/html; charset=utf-8")
                default_html = "<html><body><h1>FlameChain Node Portal</h1><p>index.html not found.</p></body></html>"
                self.wfile.write(default_html.encode('utf-8'))

        elif path == "/state" or path == "/global_network_state.json":
            with file_lock:
                if not os.path.exists(STATE_FILE):
                    self._set_headers(HTTPStatus.OK)
                    self.wfile.write(json.dumps({"nodes": {}}).encode('utf-8'))
                    return
                try:
                    with open(STATE_FILE, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    self._set_headers(HTTPStatus.OK)
                    self.wfile.write(json.dumps(data).encode('utf-8'))
                except Exception as e:
                    self._set_headers(HTTPStatus.INTERNAL_SERVER_ERROR)
                    self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))

        else:
            self._set_headers(HTTPStatus.NOT_FOUND)
            self.wfile.write(json.dumps({"error": "Endpoint not found"}).encode('utf-8'))

    def do_POST(self):
        path = self.path.split('?')[0]

        if path == "/telemetry/submit" or path == "/telemetry":
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length == 0:
                self._set_headers(HTTPStatus.BAD_REQUEST)
                self.wfile.write(json.dumps({"error": "Empty payload"}).encode('utf-8'))
                return

            post_data = self.rfile.read(content_length)

            try:
                payload = json.loads(post_data.decode('utf-8'))
            except json.JSONDecodeError:
                self._set_headers(HTTPStatus.BAD_REQUEST)
                self.wfile.write(json.dumps({"error": "Invalid JSON payload"}).encode('utf-8'))
                return

            with file_lock:
                # Load current global state
                current_state = {"nodes": {}}
                if os.path.exists(STATE_FILE):
                    try:
                        with open(STATE_FILE, "r", encoding="utf-8") as f:
                            current_state = json.load(f)
                            if "nodes" not in current_state or not isinstance(current_state["nodes"], dict):
                                current_state["nodes"] = {}
                    except json.JSONDecodeError:
                        current_state = {"nodes": {}}

                # Extract telemetry fields
                node_id = payload.get("node_id") or payload.get("id") or "unknown_node"
                ram = payload.get("ram") or payload.get("total_ram_mb") or 0
                watt_hours = payload.get("watt_hours") or payload.get("wh") or 0.0
                shard_id = payload.get("shard_id") or payload.get("active_shard") or "shard_0_vision_encoder.bin"
                last_seen = payload.get("last_seen") or time.time()

                # Update state for node
                current_state["nodes"][node_id] = {
                    "node_id": node_id,
                    "ram": ram,
                    "watt_hours": watt_hours,
                    "shard_id": shard_id,
                    "last_seen": last_seen
                }

                # Atomic write back to global_network_state.json
                tmp_file = f"{STATE_FILE}.tmp"
                try:
                    with open(tmp_file, "w", encoding="utf-8") as f:
                        json.dump(current_state, f, indent=2)
                    os.replace(tmp_file, STATE_FILE)

                    self._set_headers(HTTPStatus.OK)
                    self.wfile.write(json.dumps({
                        "status": "success",
                        "node_id": node_id,
                        "updated_at": last_seen
                    }).encode('utf-8'))
                except Exception as e:
                    self._set_headers(HTTPStatus.INTERNAL_SERVER_ERROR)
                    self.wfile.write(json.dumps({"error": f"Failed to store telemetry: {str(e)}"}).encode('utf-8'))

        else:
            self._set_headers(HTTPStatus.NOT_FOUND)
            self.wfile.write(json.dumps({"error": "POST path not recognized"}).encode('utf-8'))

    def log_message(self, format, *args):
        print(f"[FlameChain Server] {self.address_string()} - {format % args}")

def main():
    server_address = ('', PORT)
    httpd = http.server.ThreadingHTTPServer(server_address, FlameChainServer)
    print(f"[+] FlameChain Telemetry and State Server hosting on port {PORT}...")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[-] Shutting down server.")
        httpd.server_close()

if __name__ == '__main__':
    main()
