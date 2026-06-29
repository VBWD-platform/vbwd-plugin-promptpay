"""PromptPay plugin — Thailand direct-settlement QR + bank reconciliation."""
from decimal import Decimal
from typing import Optional, Dict, Any, List, TYPE_CHECKING

from vbwd.plugins.base import BasePlugin, PluginMetadata
from vbwd.plugins.payment_provider import PayoutError, PayoutProvider, PayoutResult

if TYPE_CHECKING:
    from flask import Blueprint

    from plugins.promptpay.promptpay.bank_clients.base import (
        IBankFundsTransferClient,
    )


DEFAULT_CONFIG = {
    "sandbox": True,
    "merchant_promptpay_id": "",
    "enabled_banks": ["kbank", "scb"],
    "payout_bank": "kbank",
    "bank_credentials": {
        "kbank": {"api_key": "", "webhook_secret": ""},
        "scb": {"api_key": "", "webhook_secret": ""},
        "bbl": {"api_key": "", "webhook_secret": ""},
        "krungsri": {"api_key": "", "webhook_secret": ""},
    },
    "qr_expiry_minutes": 10,
    "reconcile_match_window_minutes": 5,
    "currency": "THB",
}

PAYOUT_DESTINATION_SCHEMA: List[Dict[str, Any]] = [
    {
        "name": "promptpay_id",
        "type": "text",
        "label_key": "withdraw.destination.promptpay_id",
    }
]

PAYOUT_CURRENCY = "THB"


class PromptPayPlugin(BasePlugin, PayoutProvider):
    """PromptPay direct-bank integration — Thailand only.

    Inbound stays QR + bank-webhook reconciliation; outbound payout
    (S79 `PayoutProvider` capability) rides the bank-client seam — the
    plugin delegates to the configured `payout_bank` transfer client.
    """

    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="promptpay",
            version="26.6.1",
            author="VBWD Team",
            description=(
                "Direct PromptPay (Thailand) — EMVCo QR issuance + Thai "
                "bank-webhook reconciliation (KBank, SCB, BBL, Krungsri)."
            ),
            dependencies=[],
        )

    def initialize(self, config: Optional[Dict[str, Any]] = None) -> None:
        merged = _deep_merge(DEFAULT_CONFIG, config or {})
        super().initialize(merged)

    def get_blueprint(self) -> Optional["Blueprint"]:
        from plugins.promptpay.promptpay.routes import promptpay_plugin_bp

        return promptpay_plugin_bp

    def get_url_prefix(self) -> Optional[str]:
        return "/api/v1/plugins/promptpay"

    @property
    def admin_permissions(self):
        return [
            {
                "key": "payments.configure",
                "label": "Payment provider settings",
                "group": "Payments",
            },
        ]

    def on_enable(self) -> None:
        pass

    def on_disable(self) -> None:
        pass

    def get_payout_destination_schema(self) -> List[Dict[str, Any]]:
        return PAYOUT_DESTINATION_SCHEMA

    def create_payout(
        self,
        amount: Decimal,
        currency: str,
        destination: Dict[str, Any],
        reference_id: str,
    ) -> PayoutResult:
        from plugins.promptpay.promptpay.bank_clients.base import BankTransferError

        if currency.upper() != PAYOUT_CURRENCY:
            raise PayoutError(
                f"PromptPay payouts support {PAYOUT_CURRENCY} only, got {currency}"
            )
        receiver_promptpay_id = str(destination.get("promptpay_id", "")).strip()
        if not receiver_promptpay_id:
            raise PayoutError("PromptPay payout requires a destination promptpay_id")
        try:
            transfer = self._funds_transfer_client().create_funds_transfer(
                amount=amount,
                currency=currency,
                promptpay_id=receiver_promptpay_id,
                reference_id=reference_id,
            )
        except BankTransferError as error:
            raise PayoutError(f"PromptPay payout failed: {error}")
        return PayoutResult(
            provider_payout_id=transfer.bank_transfer_id,
            status=transfer.status,
        )

    def get_payout_status(self, provider_payout_id: str) -> str:
        from plugins.promptpay.promptpay.bank_clients.base import BankTransferError

        try:
            return self._funds_transfer_client().get_transfer_status(provider_payout_id)
        except BankTransferError as error:
            raise PayoutError(f"PromptPay payout status lookup failed: {error}")

    def _funds_transfer_client(self) -> "IBankFundsTransferClient":
        """Build the configured payout bank's transfer client from the
        live config (fresh per call, like the payment plugins'
        `_get_adapter`)."""
        from flask import current_app

        from plugins.promptpay.promptpay.bank_clients import (
            build_funds_transfer_client,
        )

        config = current_app.config_store.get_config("promptpay")
        payout_bank = str(
            config.get("payout_bank", DEFAULT_CONFIG["payout_bank"])
        ).lower()
        credentials = config.get("bank_credentials", {}).get(payout_bank, {})
        try:
            return build_funds_transfer_client(payout_bank, credentials)
        except ValueError as error:
            raise PayoutError(str(error))


def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    result = {**base}
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result
