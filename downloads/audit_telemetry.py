import json
import subprocess
import urllib.request
import sys

def get_raw_android_stats():
    """Extract raw hardware metrics directly from Android/Termux environment."""
    raw_stats = {}
    
    # 1. Read RAM directly from Linux Kernel
    try:
        with open("/proc/meminfo", "r") as f:
            lines = f.readlines()
            for line in lines:
                parts = line.split(":")
                if len(parts) == 2:
                    key = parts[0].strip()
                    val = parts[1].strip().split()[0]  # kB
                    if key in ["MemTotal", "MemAvailable"]:
                        raw_stats[key] = int(val)
    except Exception as e:
        raw_stats["mem_error"] = str(e)

    # 2. Read Power/Battery directly from Termux API
    try:
        res = subprocess.run(["termux-battery-status"], capture_output=True, text=True, timeout=3)
        if res.returncode == 0:
            bat_json = json.loads(res.stdout)
            raw_stats["percentage"] = bat_json.get("percentage")
            raw_stats["current"] = bat_json.get("current")  # Microamps
            raw_stats["status"] = bat_json.get("status")
        else:
            raw_stats["battery_error"] = "termux-battery-status returned non-zero exit code"
    except FileNotFoundError:
        raw_stats["battery_error"] = "termux-api package or Termux:API app not installed/configured"
    except Exception as e:
        raw_stats["battery_error"] = str(e)

    return raw_stats

def audit_port(port=8545):
    """Query local endpoint and compare against raw kernel/HAL values."""
    url = f"http://127.0.0.1:{port}"
    print(f"[*] Probing endpoint: {url} ...")
    
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "FlameChain-Auditor/1.0"})
        with urllib.request.urlopen(req, timeout=4) as response:
            payload = json.loads(response.read().decode('utf-8'))
            print("[+] Endpoint Responded Successfully.")
            print("--- Payload Received ---")
            print(json.dumps(payload, indent=2))
            
            # Cross-reference
            raw = get_raw_android_stats()
            print("\n--- Kernel & HAL Ground Truth ---")
            print(json.dumps(raw, indent=2))
            
            # Simple heuristic detection for mock data
            is_mock = False
            if "battery_error" in raw and "percentage" in payload:
                print("\n[!] WARNING: Endpoint provides battery stats, but termux-battery-status is failing locally. Endpoint is likely returning MOCK data.")
                is_mock = True
            elif "MemTotal" in raw and "mem_total" in payload:
                diff = abs(raw["MemTotal"] - payload["mem_total"])
                if diff > 102400: # 100MB divergence threshold
                    print(f"\n[!] WARNING: Significant RAM delta detected ({diff} kB). Endpoint may be mocked.")
                    is_mock = True

            if not is_mock:
                print("\n[✓] VERDICT: Telemetry appears to align with real hardware metrics.")
                
    except Exception as e:
        print(f"[-] Audit Failed: Could not fetch from {url}. Error: {e}")

if __name__ == "__main__":
    audit_port()
