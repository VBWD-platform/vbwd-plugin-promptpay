"""PromptPay EMVCo QR renderer (Thai QR spec per BoT).

Bot spec: tag 29 = National Clearing ID with PromptPay AID
A000000677010111, merchant identifier follows (phone, national ID, or
tax ID normalized). Tag 54 = transaction amount (dynamic QR).

CRC16/CCITT-FALSE (polynomial 0x1021, init 0xFFFF).
"""
from decimal import Decimal

PROMPTPAY_AID = "A000000677010111"
COUNTRY_TH = "TH"
CURRENCY_THB = "764"


def render_promptpay_qr(
    merchant_promptpay_id: str, amount: Decimal, reference: str = ""
) -> str:
    """Render a dynamic PromptPay QR payload.

    merchant_promptpay_id: national ID (13 digits), tax ID (13), or
      phone with country code (e.g., 66812345678 for TH phones).
      We do not try to auto-detect; caller passes a normalised string.
    amount: THB, two decimals (e.g., 100.00).
    reference: optional merchant reference, bounces back in bank notice.
    """
    identifier = _normalise_identifier(merchant_promptpay_id)
    id_type_tag = "02" if len(identifier) == 13 else "01"
    sub29 = _tlv("00", PROMPTPAY_AID) + _tlv(id_type_tag, identifier)

    parts = [
        _tlv("00", "01"),
        _tlv("01", "12"),
        _tlv("29", sub29),
        _tlv("53", CURRENCY_THB),
        _tlv("54", f"{amount:.2f}"),
        _tlv("58", COUNTRY_TH),
    ]
    if reference:
        parts.append(_tlv("62", _tlv("01", reference)))

    payload = "".join(parts) + "6304"
    crc = _crc16_ccitt(payload.encode("ascii"))
    return payload + f"{crc:04X}"


def _normalise_identifier(identifier: str) -> str:
    """Strip non-digits from the caller-provided identifier.

    Why: phone numbers may arrive with +, spaces, dashes; the QR spec
    wants digits only.
    """
    return "".join(c for c in identifier if c.isdigit())


def _tlv(tag: str, value: str) -> str:
    return f"{tag}{len(value):02d}{value}"


def _crc16_ccitt(data: bytes, poly: int = 0x1021, init: int = 0xFFFF) -> int:
    crc = init
    for byte in data:
        crc ^= byte << 8
        for _ in range(8):
            if crc & 0x8000:
                crc = (crc << 1) ^ poly
            else:
                crc <<= 1
            crc &= 0xFFFF
    return crc
