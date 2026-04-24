"""SCB (Siam Commercial Bank) webhook reconciler."""
import hashlib
import hmac
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict

from plugins.promptpay.promptpay.bank_clients.base import (
    BankTransaction,
    IBankReconciler,
)


class ScbReconciler(IBankReconciler):
    def __init__(self, webhook_secret: str):
        self._webhook_secret = webhook_secret

    @property
    def bank_name(self) -> str:
        return "scb"

    def verify_webhook(self, body: bytes, signature: str) -> bool:
        if not self._webhook_secret or not signature:
            return False
        expected = hmac.new(
            self._webhook_secret.encode(), body, hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(expected, signature)

    def extract_transaction(self, payload: Dict[str, Any]) -> BankTransaction:
        """SCB payload (simplified):

        {
          "txn_id": "SCB...",
          "amount": 100.00,
          "ref1": "INV-1",
          "ref2": null,
          "txn_datetime": "2026-04-24T12:00:00+07:00"
        }
        """
        if "txn_id" not in payload or "amount" not in payload:
            raise ValueError("malformed SCB payload")
        ts_raw = payload.get("txn_datetime")
        try:
            ts = (
                datetime.fromisoformat(ts_raw.replace("Z", "+00:00"))
                if ts_raw
                else datetime.now(timezone.utc)
            )
        except (AttributeError, ValueError):
            ts = datetime.now(timezone.utc)
        return BankTransaction(
            bank="scb",
            bank_tx_id=payload["txn_id"],
            amount=Decimal(str(payload["amount"])),
            reference=payload.get("ref1") or payload.get("ref2"),
            timestamp=ts,
        )
