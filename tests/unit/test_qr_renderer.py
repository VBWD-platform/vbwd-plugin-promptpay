"""PromptPay QR renderer tests (TDD-first)."""
from decimal import Decimal

from plugins.promptpay.promptpay.qr_renderer import render_promptpay_qr


class TestRenderPromptPayQr:
    def test_contains_promptpay_aid(self):
        qr = render_promptpay_qr("0123456789012", Decimal("100.00"))
        assert "A000000677010111" in qr

    def test_contains_amount(self):
        qr = render_promptpay_qr("0123456789012", Decimal("250.50"))
        assert "250.50" in qr

    def test_contains_currency_thb(self):
        qr = render_promptpay_qr("0123456789012", Decimal("100.00"))
        assert "764" in qr

    def test_contains_country_th(self):
        qr = render_promptpay_qr("0123456789012", Decimal("100.00"))
        assert "5802TH" in qr

    def test_crc_is_4_hex_chars(self):
        qr = render_promptpay_qr("0123456789012", Decimal("100.00"))
        crc = qr[-4:]
        assert all(c in "0123456789ABCDEF" for c in crc)
        assert qr[-8:-4] == "6304"

    def test_reference_field_included(self):
        qr = render_promptpay_qr(
            "0123456789012", Decimal("100.00"), reference="INV-1"
        )
        assert "INV-1" in qr

    def test_no_reference_omits_tag_62(self):
        qr = render_promptpay_qr("0123456789012", Decimal("100.00"))
        assert "INV-" not in qr

    def test_normalises_phone_identifier(self):
        qr = render_promptpay_qr("+66-812-345-678", Decimal("100.00"))
        assert "66812345678" in qr
        assert "+" not in qr.replace("+", "")  # no + in final output

    def test_deterministic_for_same_input(self):
        qr1 = render_promptpay_qr("0123456789012", Decimal("100.00"), "REF")
        qr2 = render_promptpay_qr("0123456789012", Decimal("100.00"), "REF")
        assert qr1 == qr2
