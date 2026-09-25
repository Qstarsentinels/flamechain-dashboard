#!/usr/bin/env python3
"""
FlameChain - Edge Node Distribution, Telemetry & Auto-Sync Global State Ledger
File: server.py
Architect: Lead Systems Architect
Host: 0.0.0.0
Port: 8546
"""

import os
import sys
import json
import time
import threading
import subprocess
import hashlib
import argparse
from http.server import HTTPServer, BaseHTTPRequestHandler

HOST = "0.0.0.0"
PORT = 8546
SOURCE_FILE = "ipad_node.py"
TELEMETRY_LOG_FILE = "latest_telemetry.json"
VAULT_FILE = "architect_vault.json"
GLOBAL_STATE_FILE = "global_network_state.json"
NODE_STATE_FILE = "node_state.json"
TAX_RATE = 0.10  # 10% Architect Tax
SYNC_INTERVAL_SEC = 30  # Auto-push state to origin main every 30s


def rebuild_genesis_from_git() -> dict:
    """Auto-detects missing state files and reconstructs ledger state from Git log history."""
    print("[Genesis Rebuild] Inspecting Git commit ledger for historical pulse recovery...")
    
    commit_count = 1
    latest_hash = "genesis_hash_fallback"
    latest_time = time.time()

    try:
        res = subprocess.run(
            ["git", "log", "--format=%H|%ct|%s"],
            capture_output=True, text=True, check=True
        )
        lines = [line for line in res.stdout.strip().splitlines() if line]
        if lines:
            commit_count = len(lines)
            latest_hash, latest_ct, _ = lines[0].split("|", 2)
            latest_time = float(latest_ct)
            print(f"[Genesis Rebuild] Parsed {commit_count} commits. Head: {latest_hash[:10]} at timestamp {latest_time}")
    except Exception as e:
        print(f"[Genesis Rebuild Warning] Unable to parse git log: {e}")

    # Calculate baseline supply derived from commit history
    baseline_wh = round(commit_count * 0.005, 8)
    gross_minted_fc = round(baseline_wh * 1000.0, 6)
    architect_tax_fc = round(gross_minted_fc * TAX_RATE, 6)
    net_circulating_fc = round(gross_minted_fc - architect_tax_fc, 6)

    # 1. Rebuild architect_vault.json if missing
    if not os.path.exists(VAULT_FILE):
        vault_data = {
            "vault_owner": "Lead Architect Protocol Vault",
            "tax_rate_percent": TAX_RATE * 100,
            "total_tax_collected_fc": architect_tax_fc,
            "total_taxed_events": commit_count,
            "last_updated_utc": time.time(),
            "node_baselines": {
                "node_tab_rebuilt_genesis": gross_minted_fc
            },
            "ledger_entries": [
                {
                    "timestamp_utc": time.time(),
                    "node_id": "genesis_rebuild_engine",
                    "pulse_counter": commit_count,
                    "gross_incremental_fc": gross_minted_fc,
                    "architect_tax_fc": architect_tax_fc,
                    "net_node_fc": net_circulating_fc,
                    "vault_total_after": architect_tax_fc
                }
            ]
        }
        with open(VAULT_FILE, "w") as f:
            json.dump(vault_data, f, indent=2)
        print(f"[Genesis Rebuild] Regenerated '{VAULT_FILE}' cleanly.")

    # 2. Rebuild node_state.json if missing
    if not os.path.exists(NODE_STATE_FILE):
        node_data = {
            "flamechain_node_id": "node_tab_rebuilt_genesis",
            "timestamp_utc": time.time(),
            "pulse_counter": commit_count,
            "detected_gateway_ip": "127.0.0.1",
            "hardware_telemetry": {
                "sysctl_ram": {"total_mb": 4096.0, "used_mb": 2048.0, "available_mb": 2048.0, "method": "rebuilt_genesis"},
                "compute_pulse": {"duration_sec": 0.05, "throughput_mb_sec": 80.0, "payload_hash": latest_hash[:16], "utilization_factor": 0.08}
            },
            "economics": {
                "currency_backing": "Watt-Hours",
                "accumulated_watt_hours": baseline_wh,
                "minted_flame_units": gross_minted_fc
            },
            "tensor_shard_state": {
                "active_shard_id": 1,
                "sequence_number": commit_count,
                "state_root": hashlib.sha256(f"genesis_rebuild_{latest_hash}".encode()).hexdigest()
            }
        }
        with open(NODE_STATE_FILE, "w") as f:
            json.dump(node_data, f, indent=2)
        print(f"[Genesis Rebuild] Regenerated '{NODE_STATE_FILE}' cleanly.")

    # 3. Rebuild global_network_state.json if missing
    if not os.path.exists(GLOBAL_STATE_FILE):
        global_data = {
            "flamechain_network": "Mainnet Alpha",
            "last_updated_utc": time.time(),
            "active_nodes_count": 1,
            "total_global_watt_hours": baseline_wh,
            "total_gross_minted_fc": gross_minted_fc,
            "architect_vault_tax_fc": architect_tax_fc,
            "net_circulating_supply_fc": net_circulating_fc,
            "latest_commit_recovery": latest_hash,
            "connected_nodes": {
                "node_tab_rebuilt_genesis": {
                    "peer_ip": "127.0.0.1",
                    "last_seen_utc": time.time(),
                    "pulse_counter": commit_count,
                    "gross_minted_fc": gross_minted_fc,
                    "accumulated_wh": baseline_wh,
                    "active_shard_id": 1,
                    "state_root": hashlib.sha256(f"genesis_rebuild_{latest_hash}".encode()).hexdigest()
                }
            }
        }
        with open(GLOBAL_STATE_FILE, "w") as f:
            json.dump(global_data, f, indent=2)
        print(f"[Genesis Rebuild] Regenerated '{GLOBAL_STATE_FILE}' cleanly.")

    print(f"[Genesis Rebuild Complete] Total Supply: {gross_minted_fc:.6f} FC | Vault: {architect_tax_fc:.6f} FC")
    return {
        "gross_fc": gross_minted_fc,
        "vault_fc": architect_tax_fc,
        "net_fc": net_circulating_fc
    }


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
        economics = telemetry.get("economics", {})
        gross_minted = float(economics.get("minted_flame_units", 0.0))
        pulse_counter = telemetry.get("pulse_counter", 0)

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

    def update_node(self, node_id: str, peer_ip: str, telemetry: dict, tax_info: dict) -> dict:
        self.nodes[node_id] = {
            "peer_ip": peer_ip,
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
        try:
            res = subprocess.run(["git", "log", "-1", "--format=%H %ct"], capture_output=True, text=True, check=True)
            commit_hash, commit_time = res.stdout.strip().split()
            self.latest_recovery_hash = commit_hash
        except Exception:
            self.latest_recovery_hash = hashlib.sha256(b"genesis_recovery_block").hexdigest()


class AutoGitSyncThread(threading.Thread):
    """Background daemon thread that periodically commits and pushes state updates to main."""
    
    def __init__(self, interval_sec: int = SYNC_INTERVAL_SEC):
        super().__init__(daemon=True)
        self.interval_sec = interval_sec
        self.running = True

    def run(self):
        print(f"[*] Background Git Sync Daemon started (Interval: {self.interval_sec}s)...")
        while self.running:
            time.sleep(self.interval_sec)
            try:
                files_to_stage = ["global_network_state.json", "node_state.json", "architect_vault.json", "latest_telemetry.json", "index.html"]
                existing_files = [f for f in files_to_stage if os.path.exists(f)]
                
                if existing_files:
                    subprocess.run(["git", "add"] + existing_files, capture_output=True, check=True)
                    commit_msg = f"auto(sync): live network state pulse at {int(time.time())}"
                    res = subprocess.run(["git", "commit", "-m", commit_msg], capture_output=True, text=True)
                    
                    if "nothing to commit" not in res.stdout:
                        push_res = subprocess.run(["git", "push", "origin", "main"], capture_output=True, text=True)
                        if push_res.returncode == 0:
                            print(f"[GIT AUTO-SYNC] Successfully pushed live network state to main branch.")
                        else:
                            print(f"[GIT AUTO-SYNC] Warning: Push failed: {push_res.stderr.strip()}")
            except Exception as e:
                print(f"[GIT AUTO-SYNC Error] {e}")


tax_engine = ArchitectTaxEngine()
state_builder = GlobalNetworkStateBuilder()


class FlameChainDistServer(BaseHTTPRequestHandler):
    """HTTP Request Handler for FlameChain distribution, telemetry, and live status dashboard."""
    
    def _send_cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, HEAD, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization, X-Requested-With")

    def do_OPTIONS(self):
        self.send_response(204)
        self._send_cors_headers()
        self.end_headers()

    def generate_dashboard_text(self) -> str:
        global_data = {}
        if os.path.exists(GLOBAL_STATE_FILE):
            try:
                with open(GLOBAL_STATE_FILE, "r") as f:
                    global_data = json.load(f)
            except Exception:
                pass

        vault_data = tax_engine.state
        nodes = global_data.get("connected_nodes", {})
        
        total_gross = global_data.get("total_gross_minted_fc", 0.0)
        circulating = global_data.get("net_circulating_supply_fc", 0.0)
        vault_balance = vault_data.get("total_tax_collected_fc", 0.0)
        total_wh = global_data.get("total_global_watt_hours", 0.0)
        recovery_hash = global_data.get("latest_commit_recovery", state_builder.latest_recovery_hash)[:12]
        
        lines = [
            "================================================================================",
            "                        FLAMECHAIN MESH NETWORK DASHBOARD                       ",
            "================================================================================",
            f" Network Mode:            ONLINE (Mainnet Alpha - 0.0.0.0:8546)",
            f" Total Gross Minted FC:   {total_gross:.6f} FC",
            f" Net Circulating Supply:  {circulating:.6f} FC",
            f" Architect Vault (10%):   {vault_balance:.6f} FC",
            f" Global Energy Backing:   {total_wh:.8f} Watt-Hours",
            f" Active Connected Nodes:  {len(nodes)}",
            f" GitHub Ledger Commit:    {recovery_hash}",
            "--------------------------------------------------------------------------------",
            "                           CONNECTED SHARD HEALTH & NODES                       ",
            "--------------------------------------------------------------------------------",
            f"{'NODE ID':<26} | {'PEER IP':<15} | {'SHARD':<5} | {'PULSE':<5} | {'STATUS'}",
            "--------------------------------------------------------------------------------"
        ]

        if not nodes:
            lines.append(f"{'No active telemetry nodes connected yet.':^80}")
        else:
            for nid, ndata in nodes.items():
                peer_ip = ndata.get("peer_ip", "0.0.0.0")
                shard_id = ndata.get("active_shard_id", 1)
                pulse = ndata.get("pulse_counter", 0)
                last_seen = ndata.get("last_seen_utc", 0)
                
                status = "HEALTHY" if (time.time() - last_seen) < 30 else "STALE"
                lines.append(f"{nid[:26]:<26} | {peer_ip:<15} | {shard_id:<5} | {pulse:<5} | {status}")

        lines.append("================================================================================")
        lines.append("")
        return "\n".join(lines)

    def do_GET(self):
        peer_ip = self.client_address[0]
        
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
                    print(f"[NODE DISCOVERY] Served ios_node.py payload to peer: {peer_ip}")
                except Exception as err:
                    self.send_error(500, f"Internal Server Error: {str(err)}")
            else:
                self.send_error(404, f"Source file '{SOURCE_FILE}' not found.")

        elif self.path == "/dashboard":
            dashboard_output = self.generate_dashboard_text().encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(dashboard_output)))
            self._send_cors_headers()
            self.end_headers()
            self.wfile.write(dashboard_output)

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
        if self.path in ["/download/ios_node.py", "/dashboard"]:
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8" if self.path == "/dashboard" else "text/x-python")
            self._send_cors_headers()
            self.end_headers()
        else:
            self.send_error(404)

    def do_POST(self):
        peer_ip = self.client_address[0]
        
        if self.path == "/telemetry/submit":
            try:
                content_length = int(self.headers.get("Content-Length", 0))
                post_body = self.rfile.read(content_length)
                telemetry_data = json.loads(post_body.decode("utf-8"))

                with open(TELEMETRY_LOG_FILE, "w") as f:
                    json.dump(telemetry_data, f, indent=2)

                node_id = telemetry_data.get("flamechain_node_id", f"node_{peer_ip}")
                pulse = telemetry_data.get("pulse_counter", 0)

                tax_info = tax_engine.process_telemetry_tax(node_id, telemetry_data)
                global_state = state_builder.update_node(node_id, peer_ip, telemetry_data, tax_info)

                print(f"[PEER INGEST] Accepted telemetry POST from IP: {peer_ip} | Node: {node_id} | Pulse: #{pulse}")

                response_payload = {
                    "status": "success",
                    "acknowledged_at": time.time(),
                    "peer_ip": peer_ip,
                    "node_id": node_id,
                    "received_pulse": pulse,
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
                print(f"[PEER ERROR] Failed to process telemetry from IP: {peer_ip} | Error: {e}")
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
        sys.stdout.write(f"[{self.log_date_time_string()}] [{self.client_address[0]}] -> {format % args}\n")

def run_server(host: str = HOST, port: int = PORT):
    parser = argparse.ArgumentParser(description="FlameChain Global Server & State Engine")
    parser.add_argument("--rebuild-genesis", action="store_true", help="Auto-detect missing state files and rebuild from Git commit log history")
    args = parser.parse_args()

    if args.rebuild-genesis:
        rebuild_genesis_from_git()

    sync_thread = AutoGitSyncThread(interval_sec=SYNC_INTERVAL_SEC)
    sync_thread.start()

    server_address = (host, port)
    httpd = HTTPServer(server_address, FlameChainDistServer)
    print(f"[*] FlameChain Telemetry & Code Server bound to http://{host}:{port}...")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[*] Terminating FlameChain Server...")
        sync_thread.running = False
        httpd.server_close()

if __name__ == "__main__":
    run_server()
