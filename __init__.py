"""PromptPay plugin — Thailand direct-settlement QR + bank reconciliation."""
from typing import Optional, Dict, Any, TYPE_CHECKING

from vbwd.plugins.base import BasePlugin, PluginMetadata

if TYPE_CHECKING:
    from flask import Blueprint


DEFAULT_CONFIG = {
    "sandbox": True,
    "merchant_promptpay_id": "",
    "enabled_banks": ["kbank", "scb"],
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


class PromptPayPlugin(BasePlugin):
    """PromptPay direct-bank integration — Thailand only."""

    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="promptpay",
            version="1.0.0",
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


def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    result = {**base}
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result
