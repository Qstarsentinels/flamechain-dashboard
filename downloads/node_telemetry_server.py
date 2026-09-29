import os
import sys
import time
import json
import base64
import hashlib
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler

STATIC_CID = "QmCZqCxd9btbSqv4v2dGVD1GrkauQwGGn41NofAnQwzTnD"
STATIC_IPFS_URL = f"https://ipfs.io/ipfs/{STATIC_CID}"

class ReusableHTTPServer(HTTPServer):
    allow_reuse_address = True

class FlameChainGatewayHandler(BaseHTTPRequestHandler):
    def _set_cors_headers(self):
        # Allow connections from FlameGPT.net, Tesla web views, iOS WebKit, and local test clients
        origin = self.headers.get('Origin', '*')
        self.send_header('Access-Control-Allow-Origin', origin if origin != '*' else '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS, UPGRADE')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization, X-Requested-With, Sec-WebSocket-Key, Sec-WebSocket-Version')
        self.send_header('Access-Control-Allow-Credentials', 'true')

    def do_OPTIONS(self):
        self.send_response(204)
        self._set_cors_headers()
        self.end_headers()

    def do_GET(self):
        # Handle WebSocket Upgrade Request Check
        if self.headers.get('Upgrade', '').lower() == 'websocket':
            self._handle_websocket_upgrade()
            return

        if self.path in ['/', '/telemetry', '/metrics', '/bridge']:
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self._set_cors_headers()
            self.end_headers()

            ram_info = self._get_ram_info()
            state_info = self._get_file_json(Path.home() / ".flamechain" / "state.json")
            vram_lp_info = self._get_file_json(Path.home() / ".flamechain" / "vram_liquidity.json")
            distill_info = self._get_file_json(Path.home() / ".flamechain" / "distilled_architect_dataset.json")

            watt_total = state_info.get("watt_hours_total", (time.time() % 86400) * 0.0125)
            ram_used_mb = ram_info.get("used_mb", 4096.0)
            vram_used_mb = vram_lp_info.get("total_vram_committed_mb", round(ram_used_mb * 0.25, 2))

            dynamic_total_supply = round(watt_total + ram_used_mb + vram_used_mb, 4)

            base_energy_rate = 0.05
            ram_weight = 0.002
            vram_weight = 0.008

            energy_val = base_energy_rate * watt_total
            ram_val = ram_weight * ram_used_mb
            vram_val = vram_weight * vram_used_mb
            fc_price_usd = round(energy_val + ram_val + vram_val, 6)

            client_ua = self.headers.get('User-Agent', 'Unknown Client')

            telemetry_payload = {
                "status": "ONLINE",
                "node_id": "FlameChain-Android-TabS-01",
                "gateway_bridge": {
                    "protocol": "HTTP/1.1 + WebSocket Hybrid",
                    "supported_clients": ["Tesla In-Car Browser", "iOS WebKit / Safari", "FlameGPT.net WebUI"],
                    "active_client_user_agent": client_ua
                },
                "ipfs_state": {
                    "cid": STATIC_CID,
                    "url": STATIC_IPFS_URL,
                    "pin_status": "STATIC_ANCHOR_BOUND"
                },
                "consensus_status": {
                    "lock": "LOCKED_DUAL_KEY",
                    "required_quorum": "100%",
                    "critical_validators": ["Validator-6-CoreNode", "Validator-7-Gemini"]
                },
                "singularity_epoch": 1,
                "port": 8545,
                "tokenomics": {
                    "token_symbol": "FLAME",
                    "total_supply_formula": "Total_Supply = Minted_Watts + Allocated_RAM_MB + Allocated_VRAM_MB",
                    "total_supply": dynamic_total_supply,
                    "minted_watts": round(watt_total, 4),
                    "allocated_ram_mb": ram_used_mb,
                    "allocated_vram_mb": vram_used_mb
                },
                "price_valuation_engine": {
                    "price_formula": "FC_Price = (Base_Energy_Rate * Total_Watts) + (RAM_Weight * Allocated_RAM) + (VRAM_Weight * Allocated_VRAM)",
                    "fc_price_usd": fc_price_usd
                },
                "timestamp": time.time()
            }

            self.wfile.write(json.dumps(telemetry_payload, indent=2).encode('utf-8'))
        else:
            self.send_response(404)
            self._set_cors_headers()
            self.end_headers()
            self.wfile.write(b'{"error": "Bridge endpoint not found"}')

    def _handle_websocket_upgrade(self):
        """Minimal RFC6455 Handshake for WebSocket clients."""
        key = self.headers.get('Sec-WebSocket-Key')
        if not key:
            self.send_error(400, "Missing Sec-WebSocket-Key")
            return

        GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
        accept_key = base64.b64encode(hashlib.sha1((key + GUID).encode()).digest()).decode()

        self.send_response(101, 'Switching Protocols')
        self.send_header('Upgrade', 'websocket')
        self.send_header('Connection', 'Upgrade')
        self.send_header('Sec-WebSocket-Accept', accept_key)
        self.end_headers()

    def _get_file_json(self, path):
        if path.exists():
            try:
                with open(path, 'r') as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def _get_ram_info(self):
        try:
            with open('/proc/meminfo', 'r') as f:
                lines = f.readlines()
            mem = {}
            for line in lines:
                parts = line.split(':')
                if len(parts) == 2:
                    mem[parts[0].strip()] = int(parts[1].strip().split()[0])
            
            total_mb = round(mem.get('MemTotal', 8192 * 1024) / 1024, 2)
            free_mb = round(mem.get('MemAvailable', 4096 * 1024) / 1024, 2)
            used_mb = round(total_mb - free_mb, 2)
            percent = round((used_mb / total_mb) * 100, 2) if total_mb > 0 else 0.0

            return {
                "total_mb": total_mb,
                "used_mb": used_mb,
                "available_mb": free_mb,
                "used_percent": percent
            }
        except Exception as e:
            return {"error": str(e)}

    def log_message(self, format, *args):
        sys.stdout.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] [Gateway Bridge] {self.address_string()} - {format % args}\n")
        sys.stdout.flush()

def run_server(port=8545):
    server_address = ('0.0.0.0', port)
    httpd = ReusableHTTPServer(server_address, FlameChainGatewayHandler)
    print(f"[FlameChain Gateway] Active on port {port} | CID Bound: {STATIC_CID}")
    sys.stdout.flush()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        httpd.server_close()

if __name__ == '__main__':
    run_server()
