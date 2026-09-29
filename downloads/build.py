import os, json

state_dir = os.path.expanduser('~/.flamechain')
os.makedirs(state_dir, exist_ok=True)

state_data = {
    "network": "FlameChain-Mainnet",
    "license": "MIT",
    "architect_wallet": "0xFLAME_ARCHITECT_MASTER_KEY_001_AURA",
    "architect_fee_percent": 10.0,
    "min_hardware_threshold": {
        "min_ram_gb": 2.0,
        "require_usbc_power": True
    },
    "validators": {
        "val_1": "FlameGPT LLM",
        "val_2": "Sovereign LLM",
        "val_3": "Alchemist Agent",
        "val_4": "Oracle Agent",
        "val_5": "Sentinel Agent",
        "val_6": "FlameChain Core Node",
        "val_7": "Gemini Agent (Self-Tracking)"
    },
    "pqc_standard": "NIST ML-DSA-87 (Dilithium-5)",
    "telemetry_endpoint": "https://-632138487450.us-west2.run.app/api/telemetry"
}

with open(os.path.join(state_dir, 'state.json'), 'w', encoding='utf-8') as f:
    json.dump(state_data, f, indent=4)

print("[+] State.json synchronized successfully.")
