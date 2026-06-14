"""Per-bank abstractions: webhook reconciliation + outbound transfers.

Liskov: concrete banks must honour these postconditions:
- `verify_webhook(body, signature)` returns bool without side-effects.
- `extract_transaction(payload)` returns a `BankTransaction` with the
  amount, reference (may be None), bank_tx_id, and timestamp —
  raising `ValueError` only on structural parse failure.
- `create_funds_transfer(...)` returns a `BankFundsTransfer` or raises
  the typed `BankTransferError` — never a bank-specific exception.
- `get_transfer_status(...)` returns a provider-neutral status string
  ("processing" / "completed" / "failed").
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, Optional


@dataclass
class BankTransaction:
    """Normalised incoming bank transaction."""

    bank: str
    bank_tx_id: str
    amount: Decimal
    reference: Optional[str]
    timestamp: datetime


class IBankReconciler(ABC):
    """Per-bank signature check + payload → BankTransaction parser."""

    @property
    @abstractmethod
    def bank_name(self) -> str:
        ...

    @abstractmethod
    def verify_webhook(self, body: bytes, signature: str) -> bool:
        ...

    @abstractmethod
    def extract_transaction(self, payload: Dict[str, Any]) -> BankTransaction:
        ...


class BankTransferError(Exception):
    """Typed outbound-transfer failure (S79 payout seam).

    Liskov: every bank client raises exactly this — no bank-specific
    exception leaks to the PromptPay plugin.
    """


@dataclass
class BankFundsTransfer:
    """Normalised outbound bank transfer (S79 payout seam)."""

    bank: str
    bank_transfer_id: str
    status: str


# Bank transfer statuses → provider-neutral payout status. Unknown /
# in-flight statuses stay "processing" (non-terminal is the safe
# default — the withdraw plugin refreshes via get_payout_status).
_TRANSFER_STATUS_COMPLETED = {"SUCCESS", "COMPLETED"}
_TRANSFER_STATUS_FAILED = {"FAILED", "REJECTED", "CANCELLED", "RETURNED"}


def map_bank_transfer_status(raw_status: str) -> str:
    """Map a raw bank transfer status to processing/completed/failed."""
    normalized = raw_status.upper()
    if normalized in _TRANSFER_STATUS_COMPLETED:
        return "completed"
    if normalized in _TRANSFER_STATUS_FAILED:
        return "failed"
    return "processing"


class IBankFundsTransferClient(ABC):
    """Outbound PromptPay funds transfer to a proxy id (S79 payout)."""

    @property
    @abstractmethod
    def bank_name(self) -> str:
        ...

    @abstractmethod
    def create_funds_transfer(
        self,
        amount: Decimal,
        currency: str,
        promptpay_id: str,
        reference_id: str,
    ) -> BankFundsTransfer:
        """Send money to `promptpay_id`; `reference_id` is the caller's
        idempotency/audit reference (the withdraw request id).

        Raises:
            BankTransferError: If the bank rejects or the call fails.
        """
        ...

    @abstractmethod
    def get_transfer_status(self, bank_transfer_id: str) -> str:
        """Provider-neutral status of a previously created transfer.

        Raises:
            BankTransferError: If the lookup fails.
        """
        ...
