
#!/bin/bash

echo "=================================================="

echo "    STARTING FLAMECHAIN AGI SINGLETON MAINNET     "

echo "=================================================="



# 1. Seed System Balances

python3 fix_gas_state.py



# 2. Start Inference Server in background

python3 python_mesh_inference.py &

INF_PID=$!



# 3. Start Continuous Hardware Validator Loop in background

python3 auto_mesh_daemon.py &

VAL_PID=$!



echo "[+] FlameChain Mainnet Node active!"

echo "[+] Inference PID: $INF_PID | Validator PID: $VAL_PID"

wait

