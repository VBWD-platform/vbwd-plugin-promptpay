"""KBank (Kasikornbank) webhook reconciler + funds-transfer client."""
import hashlib
import hmac
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, Optional

import requests

from plugins.promptpay.promptpay.bank_clients.base import (
    BankFundsTransfer,
    BankTransaction,
    BankTransferError,
    IBankFundsTransferClient,
    IBankReconciler,
    map_bank_transfer_status,
)


KBANK_DEFAULT_API_URL = "https://openapi.kasikornbank.com/promptpay/v1"
REQUEST_TIMEOUT_SECONDS = 30


class KBankReconciler(IBankReconciler):
    def __init__(self, webhook_secret: str):
        self._webhook_secret = webhook_secret

    @property
    def bank_name(self) -> str:
        return "kbank"

    def verify_webhook(self, body: bytes, signature: str) -> bool:
        if not self._webhook_secret or not signature:
            return False
        expected = hmac.new(
            self._webhook_secret.encode(), body, hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(expected, signature)

    def extract_transaction(self, payload: Dict[str, Any]) -> BankTransaction:
        """KBank payload shape (simplified):

        {
          "transactionRef": "KB123...",
          "amount": "100.00",
          "memo": "INV-1",           # may be stripped
          "timestamp": "2026-04-24T12:00:00+07:00"
        }
        """
        if "transactionRef" not in payload or "amount" not in payload:
            raise ValueError("malformed KBank payload")
        ts_raw = payload.get("timestamp")
        try:
            ts = (
                datetime.fromisoformat(ts_raw.replace("Z", "+00:00"))
                if ts_raw
                else datetime.now(timezone.utc)
            )
        except (AttributeError, ValueError):
            ts = datetime.now(timezone.utc)
        return BankTransaction(
            bank="kbank",
            bank_tx_id=payload["transactionRef"],
            amount=Decimal(str(payload["amount"])),
            reference=payload.get("memo"),
            timestamp=ts,
        )


class KBankFundsTransferClient(IBankFundsTransferClient):
    """Outbound PromptPay transfer via the KBank partner API (S79).

    KBank convention: camelCase fields, Bearer-key auth. Network and
    error responses map to the typed `BankTransferError` with a safe
    message (never the api key).
    """

    def __init__(self, api_key: str, api_url: Optional[str] = None):
        self._api_key = api_key
        self._api_url = (api_url or KBANK_DEFAULT_API_URL).rstrip("/")

    @property
    def bank_name(self) -> str:
        return "kbank"

    def create_funds_transfer(
        self,
        amount: Decimal,
        currency: str,
        promptpay_id: str,
        reference_id: str,
    ) -> BankFundsTransfer:
        body = {
            "amount": str(amount),
            "currency": currency.upper(),
            "proxyId": promptpay_id,
            "requestRef": reference_id,
        }
        try:
            resp = requests.post(
                f"{self._api_url}/transfers",
                json=body,
                headers=self._headers(),
                timeout=REQUEST_TIMEOUT_SECONDS,
            )
        except requests.RequestException as exc:
            raise BankTransferError(f"KBank transfer failed: network: {exc}")
        if resp.status_code not in (200, 201):
            raise BankTransferError(
                f"KBank transfer failed: {resp.status_code}: {resp.text[:200]}"
            )
        data = resp.json()
        return BankFundsTransfer(
            bank=self.bank_name,
            bank_transfer_id=data.get("transferRef", ""),
            status=map_bank_transfer_status(data.get("status", "")),
        )

    def get_transfer_status(self, bank_transfer_id: str) -> str:
        try:
            resp = requests.get(
                f"{self._api_url}/transfers/{bank_transfer_id}",
                headers=self._headers(),
                timeout=REQUEST_TIMEOUT_SECONDS,
            )
        except requests.RequestException as exc:
            raise BankTransferError(f"KBank status lookup failed: network: {exc}")
        if resp.status_code != 200:
            raise BankTransferError(
                f"KBank status lookup failed: {resp.status_code}: {resp.text[:200]}"
            )
        return map_bank_transfer_status(resp.json().get("status", ""))

    def _headers(self) -> Dict[str, str]:
        return {"Authorization": f"Bearer {self._api_key}"}
