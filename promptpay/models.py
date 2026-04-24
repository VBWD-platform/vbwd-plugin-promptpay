"""PromptPay payment + matched-bank-tx models."""
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Numeric, String

from vbwd.extensions import db


class PromptPayPayment(db.Model):
    __tablename__ = "promptpay_payments"

    id = Column(
        db.UUID,
        primary_key=True,
        server_default=db.text("gen_random_uuid()"),
    )
    invoice_no = Column(String(64), nullable=False, unique=True, index=True)
    merchant_promptpay_id = Column(String(32), nullable=False)
    amount = Column(Numeric(14, 2), nullable=False)
    currency = Column(String(3), nullable=False, default="THB")
    reference = Column(String(32), nullable=False, index=True)
    qr_payload = Column(String(512), nullable=False)
    status = Column(String(24), nullable=False, default="pending")
    matched_bank = Column(String(16), nullable=True)
    matched_bank_tx_id = Column(String(64), nullable=True, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    paid_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "invoice_no": self.invoice_no,
            "merchant_promptpay_id": self.merchant_promptpay_id,
            "amount": str(self.amount),
            "currency": self.currency,
            "reference": self.reference,
            "qr_payload": self.qr_payload,
            "status": self.status,
            "matched_bank": self.matched_bank,
            "matched_bank_tx_id": self.matched_bank_tx_id,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "paid_at": self.paid_at.isoformat() if self.paid_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
