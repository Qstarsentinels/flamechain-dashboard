#!/usr/bin/env bash

set -e

PORT=8545
LOG_FILE="cloudflared.log"

echo "================================================="
echo "  FlameChain Cloudflare / IPNS Network Dispatcher  "
echo "================================================="

# 1. Ensure Telemetry Daemon is running locally
if ! lsof -i :$PORT > /dev/null 2>&1; then
    echo "[*] Launching flame_daemon_v3.py on port $PORT..."
    python3 flame_daemon_v3.py > daemon.log 2>&1 &
    sleep 2
else
    echo "[+] Local daemon already running on port $PORT."
fi

# 2. Check or Install cloudflared binary in Termux
if ! command -v cloudflared &> /dev/null; then
    echo "[*] cloudflared not detected. Installing binary..."
    
    ARCH=$(uname -m)
    case "$ARCH" in
        aarch64|arm64) BIN_ARCH="arm64" ;;
        armv7l|arm)    BIN_ARCH="arm" ;;
        x86_64)        BIN_ARCH="amd64" ;;
        *) echo "[-] Unsupported architecture: $ARCH"; exit 1 ;;
    esac

    CF_URL="https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-${BIN_ARCH}"
    echo "[*] Fetching cloudflared from ${CF_URL}..."
    curl -L "$CF_URL" -o "$PREFIX/bin/cloudflared" || curl -L "$CF_URL" -o "./cloudflared"
    
    if [ -f "$PREFIX/bin/cloudflared" ]; then
        chmod +x "$PREFIX/bin/cloudflared"
    elif [ -f "./cloudflared" ]; then
        chmod +x ./cloudflared
        export PATH="$PATH:."
    fi
    echo "[+] cloudflared binary installed successfully."
fi

# 3. Clean up existing tunnel logs
rm -f "$LOG_FILE"

# 4. Start Cloudflare Quick Tunnel
echo "[*] Establishing Cloudflare Secure Tunnel to http://127.0.0.1:$PORT..."
cloudflared tunnel --url http://127.0.0.1:$PORT > "$LOG_FILE" 2>&1 &
CF_PID=$!

echo "[*] Waiting for Cloudflare edge route propagation..."

# Wait for URL to appear in log (timeout after 20 seconds)
COUNTER=0
TUNNEL_URL=""
while [ $COUNTER -lt 20 ]; do
    if grep -q "trycloudflare.com" "$LOG_FILE"; then
        TUNNEL_URL=$(grep -oE "https://[a-zA-Z0-9-]+\.trycloudflare\.com" "$LOG_FILE" | head -n 1)
        break
    fi
    sleep 1
    COUNTER=$((COUNTER+1))
done

if [ -n "$TUNNEL_URL" ]; then
    echo ""
    echo "=========================================================================="
    echo "[✓] FLAMECHAIN AGENT ONLINE - PUBLIC TELEMETRY ENDPOINT:"
    echo "    $TUNNEL_URL"
    echo "=========================================================================="
    echo ""
    echo "[*] Validating live public response:"
    curl -s "$TUNNEL_URL" | head -n 20
    echo ""
    echo "[+] Copy and paste the HTTPS URL above into your Web App telemetry config."
else
    echo "[-] Tunnel connection timed out. Check $LOG_FILE for details."
    cat "$LOG_FILE"
    exit 1
fi
