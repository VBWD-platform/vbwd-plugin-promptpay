"""Idempotent demo data."""
from decimal import Decimal

from vbwd.extensions import db

from plugins.promptpay.promptpay.models import PromptPayPayment


def populate_db() -> None:
    existing = (
        db.session.query(PromptPayPayment)
        .filter_by(invoice_no="DEMO-PP-0001")
        .one_or_none()
    )
    if existing is not None:
        return
    db.session.add(
        PromptPayPayment(
            invoice_no="DEMO-PP-0001",
            merchant_promptpay_id="0123456789012",
            amount=Decimal("99.00"),
            currency="THB",
            reference="DEMO1234567890",
            qr_payload="000201010212293700...6304ABCD",
            status="completed",
            matched_bank="kbank",
            matched_bank_tx_id="KB-DEMO-1",
        )
    )
    db.session.commit()


if __name__ == "__main__":
    populate_db()
