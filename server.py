import http.server
import json
import os
import threading
from http import HTTPStatus

PORT = 8546
STATE_FILE = "global_network_state.json"
file_lock = threading.Lock()

class FlameChainRequestHandler(http.server.BaseHTTPRequestHandler):
    def _set_headers(self, status=HTTPStatus.OK, content_type="application/json"):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()

    def do_GET(self):
        """Returns the current state from global_network_state.json."""
        if not os.path.exists(STATE_FILE):
            self._set_headers(HTTPStatus.NOT_FOUND)
            self.wfile.write(json.dumps({"error": "State file not initialized"}).encode('utf-8'))
            return

        with file_lock:
            try:
                with open(STATE_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self._set_headers(HTTPStatus.OK)
                self.wfile.write(json.dumps(data).encode('utf-8'))
            except Exception as e:
                self._set_headers(HTTPStatus.INTERNAL_SERVER_ERROR)
                self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))

    def do_POST(self):
        """Receives payload and updates global_network_state.json."""
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
            try:
                # Merge or overwrite network state
                current_state = {}
                if os.path.exists(STATE_FILE):
                    try:
                        with open(STATE_FILE, "r", encoding="utf-8") as f:
                            current_state = json.load(f)
                    except json.JSONDecodeError:
                        current_state = {}

                if isinstance(payload, dict) and isinstance(current_state, dict):
                    current_state.update(payload)
                else:
                    current_state = payload

                # Atomic write to prevent file corruption in Android/Termux environment
                tmp_file = f"{STATE_FILE}.tmp"
                with open(tmp_file, "w", encoding="utf-8") as f:
                    json.dump(current_state, f, indent=2)
                os.replace(tmp_file, STATE_FILE)

                self._set_headers(HTTPStatus.OK)
                response = {
                    "status": "success",
                    "bytes_written": len(post_data),
                    "file": STATE_FILE
                }
                self.wfile.write(json.dumps(response).encode('utf-8'))

            except Exception as e:
                self._set_headers(HTTPStatus.INTERNAL_SERVER_ERROR)
                self.wfile.write(json.dumps({"error": f"Failed to persist state: {str(e)}"}).encode('utf-8'))

    def log_message(self, format, *args):
        # Override to log in clean single-line format suitable for Termux stdio logging
        print(f"[FlameChain State Server] {self.address_string()} - {format % args}")


def run_server():
    server_address = ('', PORT)
    httpd = http.server.ThreadingHTTPServer(server_address, FlameChainRequestHandler)
    print(f"[+] FlameChain State Sync Node listening on port {PORT}...")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[-] Shutting down FlameChain State Server.")
        httpd.server_close()

if __name__ == '__main__':
    run_server()
