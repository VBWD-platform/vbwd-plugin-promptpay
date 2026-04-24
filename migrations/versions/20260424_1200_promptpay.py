"""Create promptpay_payments.

Revision ID: 20260424_1200_promptpay
Revises: 20260424_1100_conekta
Create Date: 2026-04-24

Sprint 41 — PromptPay direct.
"""
from alembic import op
import sqlalchemy as sa


revision = "20260424_1200_promptpay"
down_revision = "20260424_1100_conekta"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "promptpay_payments",
        sa.Column(
            "id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("invoice_no", sa.String(length=64), nullable=False, unique=True),
        sa.Column("merchant_promptpay_id", sa.String(length=32), nullable=False),
        sa.Column("amount", sa.Numeric(14, 2), nullable=False),
        sa.Column(
            "currency", sa.String(length=3), nullable=False, server_default="THB"
        ),
        sa.Column("reference", sa.String(length=32), nullable=False),
        sa.Column("qr_payload", sa.String(length=512), nullable=False),
        sa.Column(
            "status", sa.String(length=24), nullable=False, server_default="pending"
        ),
        sa.Column("matched_bank", sa.String(length=16), nullable=True),
        sa.Column("matched_bank_tx_id", sa.String(length=64), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index(
        "ix_promptpay_payments_reference",
        "promptpay_payments",
        ["reference"],
        unique=False,
    )
    op.create_index(
        "ix_promptpay_payments_bank_tx",
        "promptpay_payments",
        ["matched_bank_tx_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_promptpay_payments_bank_tx", table_name="promptpay_payments")
    op.drop_index("ix_promptpay_payments_reference", table_name="promptpay_payments")
    op.drop_table("promptpay_payments")
