"""PromptPayReconciler match() tests — reference + amount/window fallback."""
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import MagicMock

from plugins.promptpay.promptpay.bank_clients.base import BankTransaction
from plugins.promptpay.promptpay.services import PromptPayReconciler


def _make_bank_tx(
    amount: Decimal, reference: str = "", ts: datetime = None
) -> BankTransaction:
    return BankTransaction(
        bank="kbank",
        bank_tx_id="KB-1",
        amount=amount,
        reference=reference or None,
        timestamp=ts or datetime.now(timezone.utc),
    )


class TestMatchByReference:
    def test_preferred_reference_match(self):
        payment = MagicMock()
        payment.status = "pending"
        payment.amount = Decimal("100.00")
        payment.reference = "REF-1"

        session = MagicMock()
        session.query.return_value.filter_by.return_value.one_or_none.return_value = payment

        reconciler = PromptPayReconciler(session=session)
        bt = _make_bank_tx(Decimal("100.00"), reference="REF-1")
        matched = reconciler.match(bt)

        assert matched is payment
        assert payment.status == "completed"
        assert payment.matched_bank == "kbank"

    def test_reference_match_but_amount_mismatch_falls_through(self):
        payment = MagicMock()
        payment.status = "pending"
        payment.amount = Decimal("200.00")

        session = MagicMock()
        session.query.return_value.filter_by.return_value.one_or_none.return_value = payment
        session.query.return_value.filter.return_value.all.return_value = []

        reconciler = PromptPayReconciler(session=session)
        bt = _make_bank_tx(Decimal("100.00"), reference="REF-1")
        matched = reconciler.match(bt)

        assert matched is None
        assert payment.status == "pending"


class TestAmountWindowFallback:
    def test_exactly_one_candidate_matches(self):
        payment = MagicMock()
        payment.status = "pending"
        payment.amount = Decimal("100.00")

        session = MagicMock()
        session.query.return_value.filter_by.return_value.one_or_none.return_value = None
        session.query.return_value.filter.return_value.all.return_value = [payment]

        reconciler = PromptPayReconciler(session=session, match_window_minutes=5)
        bt = _make_bank_tx(Decimal("100.00"))
        matched = reconciler.match(bt)

        assert matched is payment
        assert payment.status == "completed"

    def test_ambiguous_multiple_candidates_no_match(self):
        session = MagicMock()
        session.query.return_value.filter_by.return_value.one_or_none.return_value = None
        session.query.return_value.filter.return_value.all.return_value = [
            MagicMock(),
            MagicMock(),
        ]

        reconciler = PromptPayReconciler(session=session)
        bt = _make_bank_tx(Decimal("100.00"))
        assert reconciler.match(bt) is None

    def test_zero_candidates_no_match(self):
        session = MagicMock()
        session.query.return_value.filter_by.return_value.one_or_none.return_value = None
        session.query.return_value.filter.return_value.all.return_value = []

        reconciler = PromptPayReconciler(session=session)
        bt = _make_bank_tx(Decimal("100.00"))
        assert reconciler.match(bt) is None
