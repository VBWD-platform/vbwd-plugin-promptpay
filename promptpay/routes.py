"""PromptPay plugin API routes."""
import logging
from decimal import Decimal

from flask import Blueprint, current_app, jsonify, request

from vbwd.middleware.auth import require_auth

from plugins.promptpay.promptpay.bank_clients.kbank import KBankReconciler
from plugins.promptpay.promptpay.bank_clients.scb import ScbReconciler
from plugins.promptpay.promptpay.services import (
    PromptPayReconciler,
    PromptPayService,
)

logger = logging.getLogger(__name__)

promptpay_plugin_bp = Blueprint("promptpay_plugin", __name__)


def _get_config():
    return current_app.config_store.get_config("promptpay")


def _bank_reconciler(bank: str):
    config = _get_config()
    creds = config.get("bank_credentials", {}).get(bank, {})
    secret = creds.get("webhook_secret", "")
    if bank == "kbank":
        return KBankReconciler(webhook_secret=secret)
    if bank == "scb":
        return ScbReconciler(webhook_secret=secret)
    raise ValueError(f"unsupported bank: {bank}")


@promptpay_plugin_bp.route("/payments", methods=["POST"])
@require_auth
def issue_qr():
    body = request.get_json(silent=True) or {}
    required = ("invoice_no", "amount")
    missing = [f for f in required if not body.get(f)]
    if missing:
        return jsonify({"error": "missing fields", "fields": missing}), 400

    try:
        amount = Decimal(str(body["amount"]))
    except (ValueError, ArithmeticError):
        return jsonify({"error": "invalid amount"}), 400

    config = _get_config()
    merchant_id = config.get("merchant_promptpay_id", "")
    if not merchant_id:
        return jsonify({"error": "merchant_promptpay_id not configured"}), 409

    service = PromptPayService()
    payment = service.issue_qr(
        invoice_no=body["invoice_no"],
        merchant_promptpay_id=merchant_id,
        amount=amount,
        expiry_minutes=int(config.get("qr_expiry_minutes", 10)),
    )
    return jsonify(payment.to_dict()), 201


@promptpay_plugin_bp.route("/payments/<invoice_no>/status", methods=["GET"])
@require_auth
def get_status(invoice_no: str):
    from vbwd.extensions import db

    from plugins.promptpay.promptpay.models import PromptPayPayment

    payment = (
        db.session.query(PromptPayPayment)
        .filter_by(invoice_no=invoice_no)
        .one_or_none()
    )
    if payment is None:
        return jsonify({"error": "not found"}), 404
    return jsonify(payment.to_dict()), 200


@promptpay_plugin_bp.route("/webhooks/<bank>", methods=["POST"])
def bank_webhook(bank: str):
    bank = bank.lower()
    config = _get_config()
    if bank not in config.get("enabled_banks", []):
        return jsonify({"error": f"bank {bank} not enabled"}), 400

    try:
        reconciler = _bank_reconciler(bank)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    signature = request.headers.get("X-Signature", "")
    body = request.get_data()
    if not reconciler.verify_webhook(body, signature):
        return jsonify({"error": "invalid signature"}), 401

    payload = request.get_json(silent=True) or {}
    try:
        bank_tx = reconciler.extract_transaction(payload)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    match_minutes = int(config.get("reconcile_match_window_minutes", 5))
    matcher = PromptPayReconciler(match_window_minutes=match_minutes)
    matched = matcher.match(bank_tx)
    if matched is None:
        logger.warning(
            "PromptPay: unmatched bank tx %s from %s for %s",
            bank_tx.bank_tx_id,
            bank,
            bank_tx.amount,
        )
        return jsonify({"matched": False}), 202

    return jsonify({"matched": True, "invoice_no": matched.invoice_no}), 200
