"""IBankReconciler — per-bank webhook + statement polling abstraction.

Liskov: concrete banks must honour these postconditions:
- `verify_webhook(body, signature)` returns bool without side-effects.
- `extract_transaction(payload)` returns a `BankTransaction` with the
  amount, reference (may be None), bank_tx_id, and timestamp —
  raising `ValueError` only on structural parse failure.
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
    def bank_name(self) -> str: ...

    @abstractmethod
    def verify_webhook(self, body: bytes, signature: str) -> bool: ...

    @abstractmethod
    def extract_transaction(
        self, payload: Dict[str, Any]
    ) -> BankTransaction: ...
