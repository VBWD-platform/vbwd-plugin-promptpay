"""Unit tests for KBank + SCB reconcilers (TDD-first)."""
import hashlib
import hmac
from decimal import Decimal

import pytest

from plugins.promptpay.promptpay.bank_clients.kbank import KBankReconciler
from plugins.promptpay.promptpay.bank_clients.scb import ScbReconciler


class TestKBank:
    def test_verify_accepts_correct(self):
        rc = KBankReconciler(webhook_secret="kb-secret")
        body = b'{"transactionRef":"KB1"}'
        sig = hmac.new(b"kb-secret", body, hashlib.sha256).hexdigest()
        assert rc.verify_webhook(body, sig) is True

    def test_verify_rejects_wrong(self):
        rc = KBankReconciler(webhook_secret="kb-secret")
        assert rc.verify_webhook(b"body", "deadbeef") is False

    def test_verify_rejects_empty_secret(self):
        rc = KBankReconciler(webhook_secret="")
        assert rc.verify_webhook(b"body", "any") is False

    def test_extract_with_memo(self):
        rc = KBankReconciler(webhook_secret="kb-secret")
        bt = rc.extract_transaction(
            {
                "transactionRef": "KB123",
                "amount": "100.00",
                "memo": "INV-1",
                "timestamp": "2026-04-24T12:00:00+00:00",
            }
        )
        assert bt.bank == "kbank"
        assert bt.bank_tx_id == "KB123"
        assert bt.amount == Decimal("100.00")
        assert bt.reference == "INV-1"

    def test_extract_without_memo_null_reference(self):
        rc = KBankReconciler(webhook_secret="kb-secret")
        bt = rc.extract_transaction(
            {"transactionRef": "KB123", "amount": "100.00"}
        )
        assert bt.reference is None

    def test_extract_raises_on_malformed(self):
        rc = KBankReconciler(webhook_secret="kb-secret")
        with pytest.raises(ValueError, match="KBank"):
            rc.extract_transaction({"garbage": "yes"})


class TestScb:
    def test_extract_uses_ref1_then_ref2(self):
        rc = ScbReconciler(webhook_secret="scb-secret")
        bt = rc.extract_transaction(
            {
                "txn_id": "SCB1",
                "amount": 100.0,
                "ref1": "INV-1",
                "ref2": None,
                "txn_datetime": "2026-04-24T12:00:00+07:00",
            }
        )
        assert bt.reference == "INV-1"

    def test_falls_back_to_ref2_when_ref1_missing(self):
        rc = ScbReconciler(webhook_secret="scb-secret")
        bt = rc.extract_transaction(
            {
                "txn_id": "SCB1",
                "amount": 100.0,
                "ref2": "INV-ALT",
            }
        )
        assert bt.reference == "INV-ALT"

    def test_bank_name(self):
        assert ScbReconciler("x").bank_name == "scb"
