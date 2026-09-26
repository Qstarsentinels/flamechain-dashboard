import http.server
import socketserver

PORT = 8546

class FlameChainHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/' or self.path == '':
            self.path = '/index.html'
        return super().do_GET()

    def log_message(self, format, *args):
        print(f"[FlameChain WebServer] {self.address_string()} - {format % args}")

if __name__ == '__main__':
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("", PORT), FlameChainHandler) as httpd:
        print(f"[FlameChain Node] Mesh Telemetry Dashboard live on port {PORT}")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            pass
