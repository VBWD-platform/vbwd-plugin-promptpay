"""PromptPay services — issuance + bank reconciliation."""
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional

from vbwd.extensions import db

from plugins.promptpay.promptpay.bank_clients.base import BankTransaction
from plugins.promptpay.promptpay.models import PromptPayPayment
from plugins.promptpay.promptpay.qr_renderer import render_promptpay_qr


def generate_reference() -> str:
    """Generate a short merchant-side reference (15 ASCII chars)."""
    return uuid.uuid4().hex[:15].upper()


class PromptPayService:
    def __init__(self, session=None):
        self._session = session or db.session

    def issue_qr(
        self,
        invoice_no: str,
        merchant_promptpay_id: str,
        amount: Decimal,
        expiry_minutes: int = 10,
    ) -> PromptPayPayment:
        existing = (
            self._session.query(PromptPayPayment)
            .filter_by(invoice_no=invoice_no)
            .one_or_none()
        )
        if existing is not None:
            return existing

        reference = generate_reference()
        qr_payload = render_promptpay_qr(
            merchant_promptpay_id=merchant_promptpay_id,
            amount=amount,
            reference=reference,
        )
        expires_at = datetime.now(timezone.utc) + timedelta(
            minutes=expiry_minutes
        )
        payment = PromptPayPayment(
            invoice_no=invoice_no,
            merchant_promptpay_id=merchant_promptpay_id,
            amount=amount,
            currency="THB",
            reference=reference,
            qr_payload=qr_payload,
            status="pending",
            expires_at=expires_at,
        )
        self._session.add(payment)
        self._session.commit()
        return payment


class PromptPayReconciler:
    """Match incoming BankTransaction to an open PromptPayPayment."""

    def __init__(self, session=None, match_window_minutes: int = 5):
        self._session = session or db.session
        self._match_window = timedelta(minutes=match_window_minutes)

    def match(self, bank_tx: BankTransaction) -> Optional[PromptPayPayment]:
        """Preferred match: by reference. Fallback: amount+timestamp window.

        Why fallback: some Thai banks strip the QR reference on the
        statement line. If we can find exactly one pending payment in
        the amount+window range, match it. Ambiguous matches (0 or >1)
        return None and surface for manual review.
        """
        if bank_tx.reference:
            payment = (
                self._session.query(PromptPayPayment)
                .filter_by(reference=bank_tx.reference, status="pending")
                .one_or_none()
            )
            if payment is not None and payment.amount == bank_tx.amount:
                return self._apply_match(payment, bank_tx)

        window_start = bank_tx.timestamp - self._match_window
        window_end = bank_tx.timestamp + self._match_window
        candidates = (
            self._session.query(PromptPayPayment)
            .filter(
                PromptPayPayment.status == "pending",
                PromptPayPayment.amount == bank_tx.amount,
                PromptPayPayment.created_at.between(window_start, window_end),
            )
            .all()
        )
        if len(candidates) == 1:
            return self._apply_match(candidates[0], bank_tx)
        return None

    def _apply_match(
        self, payment: PromptPayPayment, bank_tx: BankTransaction
    ) -> PromptPayPayment:
        payment.status = "completed"
        payment.matched_bank = bank_tx.bank
        payment.matched_bank_tx_id = bank_tx.bank_tx_id
        payment.paid_at = bank_tx.timestamp
        self._session.commit()
        return payment
