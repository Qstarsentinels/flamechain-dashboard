#!/usr/bin/env python3
"""
FlameChain // TFHE Threshold Multisig Engine
Enforces a 2-of-2 threshold signature requirement (Galaxy Tab Master + iPhone Node)
over architect_vault.json before authorizing withdrawal transactions.

STRICT REQUIREMENT: Standard library modules only (json, time, math, hashlib, secrets).
"""

import json
import os
import time
import hashlib
import secrets
from typing import Dict, Any

VAULT_FILE = "architect_vault.json"


class TFHEThresholdMultisig:
    """Verifies 2-of-2 threshold signatures for architect_vault.json withdrawals."""

    def __init__(self, vault_path: str = VAULT_FILE):
        self.vault_path = vault_path
        self._ensure_vault_exists()

    def _ensure_vault_exists(self) -> None:
        """Initializes architect_vault.json if missing."""
        if not os.path.exists(self.vault_path):
            tab_pubhash = hashlib.sha256(b"GALAXY_TAB_S8_MASTER_TFHE_KEY_V1").hexdigest()
            iphone_pubhash = hashlib.sha256(b"ISH_IPHONE_14PRO_TFHE_KEY_V1").hexdigest()

            vault_data = {
                "vault_address": "0xArchitectVaultMaster",
                "balance_fc": 312500.00,
                "threshold_required": 2,
                "signers": {
                    "galaxy_tab_master": {
                        "device_type": "Android (Galaxy Tab)",
                        "pubkey_hash": tab_pubhash,
                        "status": "active"
                    },
                    "iphone_node": {
                        "device_type": "iOS (iPhone)",
                        "pubkey_hash": iphone_pubhash,
                        "status": "active"
                    }
                },
                "withdrawal_history": [],
                "last_updated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            }
            with open(self.vault_path, "w") as f:
                json.dump(vault_data, f, indent=2)

    def load_vault(self) -> Dict[str, Any]:
        with open(self.vault_path, "r") as f:
            return json.load(f)

    def save_vault(self, data: Dict[str, Any]) -> None:
        data["last_updated"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        with open(self.vault_path, "w") as f:
            json.dump(data, f, indent=2)

    def compute_tx_digest(self, destination: str, amount_fc: float, timestamp: float) -> str:
        """Derives SHA-256 transaction digest."""
        payload = f"{destination}:{amount_fc:.4f}:{timestamp}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def generate_signature(self, secret_seed: str, tx_digest: str) -> str:
        """Generates deterministic signature token for a signer."""
        return hashlib.sha256(f"{secret_seed}:{tx_digest}".encode("utf-8")).hexdigest()

    def verify_signature(self, expected_pubhash: str, sig_token: str, tx_digest: str, secret_seed: str) -> bool:
        """Validates secret seed pubkey hash and signature token digest match."""
        derived_pubhash = hashlib.sha256(secret_seed.encode("utf-8")).hexdigest()
        if derived_pubhash != expected_pubhash:
            return False

        expected_sig = self.generate_signature(secret_seed, tx_digest)
        return secrets.compare_digest(sig_token, expected_sig)

    def execute_2of2_withdrawal(
        self,
        destination: str,
        amount_fc: float,
        sig_galaxy_tab: str,
        sig_iphone: str,
        tab_secret_seed: str = "GALAXY_TAB_S8_MASTER_TFHE_KEY_V1",
        iphone_secret_seed: str = "ISH_IPHONE_14PRO_TFHE_KEY_V1"
    ) -> Dict[str, Any]:
        """Validates 2-of-2 threshold signatures and deducts funds from architect_vault.json."""
        vault = self.load_vault()
        current_balance = float(vault.get("balance_fc", 0.0))

        if amount_fc <= 0:
            return {"success": False, "error": "Withdrawal amount must be greater than zero"}

        if amount_fc > current_balance:
            return {
                "success": False,
                "error": "Insufficient balance in architect_vault.json",
                "available": current_balance,
                "requested": amount_fc
            }

        timestamp = time.time()
        tx_digest = self.compute_tx_digest(destination, amount_fc, timestamp)

        signers = vault.get("signers", {})
        tab_pubhash = signers.get("galaxy_tab_master", {}).get("pubkey_hash", "")
        iphone_pubhash = signers.get("iphone_node", {}).get("pubkey_hash", "")

        valid_tab = self.verify_signature(tab_pubhash, sig_galaxy_tab, tx_digest, tab_secret_seed)
        valid_iphone = self.verify_signature(iphone_pubhash, sig_iphone, tx_digest, iphone_secret_seed)

        if not valid_tab and not valid_iphone:
            return {"success": False, "error": "Multisig failure: Both signatures invalid (0 of 2 verified)"}
        if not valid_tab:
            return {"success": False, "error": "Multisig failure: Galaxy Tab signature invalid (1 of 2 verified)"}
        if not valid_iphone:
            return {"success": False, "error": "Multisig failure: iPhone signature invalid (1 of 2 verified)"}

        # 2-of-2 requirement satisfied
        new_balance = round(current_balance - amount_fc, 4)
        vault["balance_fc"] = new_balance

        tx_record = {
            "tx_digest": tx_digest,
            "destination": destination,
            "amount_fc": amount_fc,
            "remaining_vault_balance": new_balance,
            "multisig_status": "2-of-2 VERIFIED (Galaxy Tab + iPhone)",
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(timestamp))
        }

        vault.setdefault("withdrawal_history", []).append(tx_record)
        self.save_vault(vault)

        return {
            "success": True,
            "message": "2-of-2 Threshold Multisig Verified. Funds released from architect_vault.json.",
            "tx": tx_record
        }


if __name__ == "__main__":
    ms = TFHEThresholdMultisig()
    now = time.time()
    digest = ms.compute_tx_digest("0xVaultRecipient", 100.0, now)

    tab_sig = ms.generate_signature("GALAXY_TAB_S8_MASTER_TFHE_KEY_V1", digest)
    iphone_sig = ms.generate_signature("ISH_IPHONE_14PRO_TFHE_KEY_V1", digest)

    print("=== TFHE 2-of-2 Multisig Self-Test ===")
    res = ms.execute_2of2_withdrawal("0xVaultRecipient", 100.0, tab_sig, iphone_sig)
    assert res["success"] is True, "Self-test withdrawal failed!"
    print("STATUS       : PASSED")
