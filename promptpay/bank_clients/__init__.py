"""Bank-client factory for outbound PromptPay transfers (S79).

Single home for the bank-name → funds-transfer-client mapping so the
plugin stays a thin delegator.
"""
from typing import Any, Dict

from plugins.promptpay.promptpay.bank_clients.base import IBankFundsTransferClient
from plugins.promptpay.promptpay.bank_clients.kbank import KBankFundsTransferClient
from plugins.promptpay.promptpay.bank_clients.scb import ScbFundsTransferClient


def build_funds_transfer_client(
    bank_name: str, credentials: Dict[str, Any]
) -> IBankFundsTransferClient:
    """Build the funds-transfer client for `bank_name`.

    `credentials` is the bank's entry from the plugin config
    (`bank_credentials.<bank>`): `api_key` required, `api_url` optional
    override of the bank's default endpoint.

    Raises:
        ValueError: If no transfer client exists for `bank_name`.
    """
    api_key = str(credentials.get("api_key", ""))
    api_url = credentials.get("api_url")
    if bank_name == "kbank":
        return KBankFundsTransferClient(api_key=api_key, api_url=api_url)
    if bank_name == "scb":
        return ScbFundsTransferClient(api_key=api_key, api_url=api_url)
    raise ValueError(f"unsupported payout bank: {bank_name}")
