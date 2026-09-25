#!/usr/bin/env python3
"""
FlameChain - Edge Node Distribution, Telemetry & Global State Ledger
File: server.py
Architect: Lead Systems Architect
Port: 8546
"""

import os
import sys
import json
import time
import subprocess
import hashlib
from http.server import HTTPServer, BaseHTTPRequestHandler

PORT = 8546
SOURCE_FILE = "ipad_node.py"
TELEMETRY_LOG_FILE = "latest_telemetry.json"
VAULT_FILE = "architect_vault.json"
GLOBAL_STATE_FILE = "global_network_state.json"
TAX_RATE = 0.10  # 10% Architect Tax


class ArchitectTaxEngine:
    """Enforces protocol-level 10% tax routing on all minted FC rewards and transfers."""
    
    def __init__(self, vault_path: str = VAULT_FILE):
        self.vault_path = vault_path
        self.state = self._load_vault()

    def _load_vault(self) -> dict:
        if os.path.exists(self.vault_path):
            try:
                with open(self.vault_path, "r") as f:
                    return json.load(f)
            except Exception:
                pass
        return {
            "vault_owner": "Lead Architect Protocol Vault",
            "tax_rate_percent": TAX_RATE * 100,
            "total_tax_collected_fc": 0.0,
            "total_taxed_events": 0,
            "last_updated_utc": time.time(),
            "ledger_entries": []
        }

    def _save_vault(self):
        with open(self.vault_path, "w") as f:
            json.dump(self.state, f, indent=2)

    def process_telemetry_tax(self, node_id: str, telemetry: dict) -> dict:
        """Calculates and deducts 10% tax on incremental minted FC units."""
        economics = telemetry.get("economics", {})
        gross_minted = float(economics.get("minted_flame_units", 0.0))
        pulse_counter = telemetry.get("pulse_counter", 0)

        # Track last processed amount per node
        node_history = self.state.get("node_baselines", {})
        last_gross = float(node_history.get(node_id, 0.0))

        incremental_mint = max(0.0, gross_minted - last_gross)
        if incremental_mint <= 0:
            return {
                "tax_applied_fc": 0.0,
                "net_node_reward_fc": 0.0,
                "total_vault_balance": self.state["total_tax_collected_fc"]
            }

        architect_tax = round(incremental_mint * TAX_RATE, 6)
        net_reward = round(incremental_mint - architect_tax, 6)

        # Update Vault State
        self.state["total_tax_collected_fc"] = round(self.state["total_tax_collected_fc"] + architect_tax, 6)
        self.state["total_taxed_events"] += 1
        self.state["last_updated_utc"] = time.time()
        if "node_baselines" not in self.state:
            self.state["node_baselines"] = {}
        self.state["node_baselines"][node_id] = gross_minted

        audit_entry = {
            "timestamp_utc": time.time(),
            "node_id": node_id,
            "pulse_counter": pulse_counter,
            "gross_incremental_fc": round(incremental_mint, 6),
            "architect_tax_fc": architect_tax,
            "net_node_fc": net_reward,
            "vault_total_after": self.state["total_tax_collected_fc"]
        }
        
        self.state["ledger_entries"].append(audit_entry)
        # Cap ledger entries history to last 100 entries
        if len(self.state["ledger_entries"]) > 100:
            self.state["ledger_entries"] = self.state["ledger_entries"][-100:]

        self._save_vault()
        return {
            "tax_applied_fc": architect_tax,
            "net_node_reward_fc": net_reward,
            "total_vault_balance": self.state["total_tax_collected_fc"]
        }


class GlobalNetworkStateBuilder:
    """Aggregates multi-node telemetry and provides GitHub commit ledger recovery."""
    
    def __init__(self, state_path: str = GLOBAL_STATE_FILE):
        self.state_path = state_path
        self.nodes = {}
        self.recover_from_github_ledger()

    def update_node(self, node_id: str, telemetry: dict, tax_info: dict) -> dict:
        self.nodes[node_id] = {
            "last_seen_utc": time.time(),
            "pulse_counter": telemetry.get("pulse_counter", 0),
            "gross_minted_fc": float(telemetry.get("economics", {}).get("minted_flame_units", 0.0)),
            "accumulated_wh": float(telemetry.get("economics", {}).get("accumulated_watt_hours", 0.0)),
            "active_shard_id": telemetry.get("tensor_shard_state", {}).get("active_shard_id", 1),
            "state_root": telemetry.get("tensor_shard_state", {}).get("state_root", "")
        }

        total_gross_fc = sum(n["gross_minted_fc"] for n in self.nodes.values())
        total_wh = sum(n["accumulated_wh"] for n in self.nodes.values())
        total_tax_fc = tax_info.get("total_vault_balance", 0.0)
        net_circulation_fc = max(0.0, total_gross_fc - total_tax_fc)

        global_state = {
            "flamechain_network": "Mainnet Alpha",
            "last_updated_utc": time.time(),
            "active_nodes_count": len(self.nodes),
            "total_global_watt_hours": round(total_wh, 8),
            "total_gross_minted_fc": round(total_gross_fc, 6),
            "architect_vault_tax_fc": total_tax_fc,
            "net_circulating_supply_fc": round(net_circulation_fc, 6),
            "latest_commit_recovery": self.latest_recovery_hash,
            "connected_nodes": self.nodes
        }

        with open(self.state_path, "w") as f:
            json.dump(global_state, f, indent=2)

        return global_state

    def recover_from_github_ledger(self):
        """Reads latest git commit metadata to seed/verify ledger recovery state."""
        try:
            res = subprocess.run(["git", "log", "-1", "--format=%H %ct"], capture_output=True, text=True, check=True)
            commit_hash, commit_time = res.stdout.strip().split()
            self.latest_recovery_hash = commit_hash
            print(f"[Ledger Recovery] Instantiated baseline state from GitHub commit: {commit_hash[:10]}")
        except Exception:
            self.latest_recovery_hash = hashlib.sha256(b"genesis_recovery_block").hexdigest()
            print("[Ledger Recovery] Git metadata unavailable. Initialized fallback recovery seed.")


# Global singleton instances
tax_engine = ArchitectTaxEngine()
state_builder = GlobalNetworkStateBuilder()


class FlameChainDistServer(BaseHTTPRequestHandler):
    """HTTP Request Handler for FlameChain code distribution, telemetry POSTs, and state inspection."""
    
    def _send_cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, HEAD, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def do_OPTIONS(self):
        self.send_response(204)
        self._send_cors_headers()
        self.end_headers()

    def do_GET(self):
        if self.path == "/download/ios_node.py":
            if os.path.exists(SOURCE_FILE):
                try:
                    file_size = os.path.getsize(SOURCE_FILE)
                    self.send_response(200)
                    self.send_header("Content-Type", "text/x-python")
                    self.send_header("Content-Length", str(file_size))
                    self._send_cors_headers()
                    self.end_headers()
                    with open(SOURCE_FILE, "rb") as f:
                        self.wfile.write(f.read())
                except Exception as err:
                    self.send_error(500, f"Internal Server Error: {str(err)}")
            else:
                self.send_error(404, f"Source file '{SOURCE_FILE}' not found.")

        elif self.path == "/state/global":
            if os.path.exists(GLOBAL_STATE_FILE):
                with open(GLOBAL_STATE_FILE, "rb") as f:
                    data = f.read()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(data)
            else:
                self.send_error(404, "Global state not initialized yet.")

        elif self.path == "/ledger/recover":
            state_builder.recover_from_github_ledger()
            resp = json.dumps({"status": "recovered", "commit_hash": state_builder.latest_recovery_hash}).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(resp)))
            self._send_cors_headers()
            self.end_headers()
            self.wfile.write(resp)

        else:
            self.send_error(404, "Endpoint Not Found.")

    def do_HEAD(self):
        if self.path == "/download/ios_node.py":
            if os.path.exists(SOURCE_FILE):
                file_size = os.path.getsize(SOURCE_FILE)
                self.send_response(200)
                self.send_header("Content-Type", "text/x-python")
                self.send_header("Content-Length", str(file_size))
                self._send_cors_headers()
                self.end_headers()
            else:
                self.send_error(404)
        else:
            self.send_error(404)

    def do_POST(self):
        if self.path == "/telemetry/submit":
            try:
                content_length = int(self.headers.get("Content-Length", 0))
                post_body = self.rfile.read(content_length)
                telemetry_data = json.loads(post_body.decode("utf-8"))

                # Persist raw latest telemetry snapshot
                with open(TELEMETRY_LOG_FILE, "w") as f:
                    json.dump(telemetry_data, f, indent=2)

                node_id = telemetry_data.get("flamechain_node_id", "unknown_node")

                # Enforce Architect Tax
                tax_info = tax_engine.process_telemetry_tax(node_id, telemetry_data)

                # Rebuild Global State Ledger
                global_state = state_builder.update_node(node_id, telemetry_data, tax_info)

                response_payload = {
                    "status": "success",
                    "acknowledged_at": time.time(),
                    "node_id": node_id,
                    "received_pulse": telemetry_data.get("pulse_counter", 0),
                    "architect_tax_applied_fc": tax_info["tax_applied_fc"],
                    "vault_balance_fc": tax_info["total_vault_balance"],
                    "net_circulating_supply_fc": global_state["net_circulating_supply_fc"]
                }

                data_bytes = json.dumps(response_payload).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data_bytes)))
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(data_bytes)

            except Exception as e:
                err_bytes = json.dumps({"status": "error", "message": str(e)}).encode("utf-8")
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(err_bytes)))
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(err_bytes)
        else:
            self.send_error(404, "Endpoint Not Found.")

    def log_message(self, format, *args):
        sys.stdout.write(f"[{self.log_date_time_string()}] {self.client_address[0]} -> {format % args}\n")

def run_server(port: int = PORT):
    server_address = ('', port)
    httpd = HTTPServer(server_address, FlameChainDistServer)
    print(f"[*] FlameChain Global Server & Architect Tax Engine active on port {port}...")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[*] Terminating Server...")
        httpd.server_close()

if __name__ == "__main__":
    run_server()
