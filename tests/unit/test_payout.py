"""Payout capability specs (S79 Slice 2) — PromptPay outbound transfer.

RED-first oracle for the `PayoutProvider` contract on PromptPay:
- the bank-client seam (`IBankFundsTransferClient`) gains
  `create_funds_transfer` + `get_transfer_status`, implemented by the
  KBank and SCB clients (each following its own request conventions:
  KBank camelCase, SCB snake_case, both Bearer-key auth);
- `PromptPayPlugin.create_payout` delegates to the configured bank
  client and maps `BankTransferError` to the typed `PayoutError`.
"""
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from vbwd.plugins.payment_provider import PayoutError, PayoutProvider, PayoutResult


REFERENCE_ID = "withdraw-req-321"
RECEIVER_PROMPTPAY_ID = "0812345678"


class TestKBankFundsTransferClient:
    def _client(self):
        from plugins.promptpay.promptpay.bank_clients.kbank import (
            KBankFundsTransferClient,
        )

        return KBankFundsTransferClient(api_key="kb-api-key")

    def test_posts_camel_case_transfer_shape(self, mocker):
        fake = MagicMock()
        fake.status_code = 201
        fake.json.return_value = {"transferRef": "KB-TR-1", "status": "PROCESSING"}
        mock_post = mocker.patch(
            "plugins.promptpay.promptpay.bank_clients.kbank.requests.post",
            return_value=fake,
        )

        transfer = self._client().create_funds_transfer(
            amount=Decimal("123.45"),
            currency="THB",
            promptpay_id=RECEIVER_PROMPTPAY_ID,
            reference_id=REFERENCE_ID,
        )

        assert transfer.bank == "kbank"
        assert transfer.bank_transfer_id == "KB-TR-1"
        assert transfer.status == "processing"

        call = mock_post.call_args
        assert call.args[0].endswith("/transfers")
        assert call.kwargs["headers"]["Authorization"] == "Bearer kb-api-key"
        assert call.kwargs["json"] == {
            "amount": "123.45",
            "currency": "THB",
            "proxyId": RECEIVER_PROMPTPAY_ID,
            "requestRef": REFERENCE_ID,
        }

    def test_error_response_raises_bank_transfer_error(self, mocker):
        from plugins.promptpay.promptpay.bank_clients.base import BankTransferError

        fake = MagicMock()
        fake.status_code = 400
        fake.text = "invalid proxyId"
        mocker.patch(
            "plugins.promptpay.promptpay.bank_clients.kbank.requests.post",
            return_value=fake,
        )

        with pytest.raises(BankTransferError):
            self._client().create_funds_transfer(
                amount=Decimal("1.00"),
                currency="THB",
                promptpay_id=RECEIVER_PROMPTPAY_ID,
                reference_id=REFERENCE_ID,
            )

    def test_network_error_raises_bank_transfer_error(self, mocker):
        import requests

        from plugins.promptpay.promptpay.bank_clients.base import BankTransferError

        mocker.patch(
            "plugins.promptpay.promptpay.bank_clients.kbank.requests.post",
            side_effect=requests.ConnectionError("down"),
        )

        with pytest.raises(BankTransferError):
            self._client().create_funds_transfer(
                amount=Decimal("1.00"),
                currency="THB",
                promptpay_id=RECEIVER_PROMPTPAY_ID,
                reference_id=REFERENCE_ID,
            )

    def test_get_transfer_status_maps_to_neutral_status(self, mocker):
        fake = MagicMock()
        fake.status_code = 200
        fake.json.return_value = {"transferRef": "KB-TR-1", "status": "SUCCESS"}
        mock_get = mocker.patch(
            "plugins.promptpay.promptpay.bank_clients.kbank.requests.get",
            return_value=fake,
        )

        status = self._client().get_transfer_status("KB-TR-1")

        assert status == "completed"
        assert mock_get.call_args.args[0].endswith("/transfers/KB-TR-1")


class TestScbFundsTransferClient:
    def _client(self):
        from plugins.promptpay.promptpay.bank_clients.scb import (
            ScbFundsTransferClient,
        )

        return ScbFundsTransferClient(api_key="scb-api-key")

    def test_posts_snake_case_transfer_shape(self, mocker):
        fake = MagicMock()
        fake.status_code = 201
        fake.json.return_value = {"transfer_id": "SCB-TR-1", "status": "PENDING"}
        mock_post = mocker.patch(
            "plugins.promptpay.promptpay.bank_clients.scb.requests.post",
            return_value=fake,
        )

        transfer = self._client().create_funds_transfer(
            amount=Decimal("123.45"),
            currency="THB",
            promptpay_id=RECEIVER_PROMPTPAY_ID,
            reference_id=REFERENCE_ID,
        )

        assert transfer.bank == "scb"
        assert transfer.bank_transfer_id == "SCB-TR-1"
        assert transfer.status == "processing"

        call = mock_post.call_args
        assert call.args[0].endswith("/transfers")
        assert call.kwargs["headers"]["Authorization"] == "Bearer scb-api-key"
        assert call.kwargs["json"] == {
            "amount": "123.45",
            "currency": "THB",
            "promptpay_id": RECEIVER_PROMPTPAY_ID,
            "ref1": REFERENCE_ID,
        }

    def test_error_response_raises_bank_transfer_error(self, mocker):
        from plugins.promptpay.promptpay.bank_clients.base import BankTransferError

        fake = MagicMock()
        fake.status_code = 422
        fake.text = "invalid promptpay_id"
        mocker.patch(
            "plugins.promptpay.promptpay.bank_clients.scb.requests.post",
            return_value=fake,
        )

        with pytest.raises(BankTransferError):
            self._client().create_funds_transfer(
                amount=Decimal("1.00"),
                currency="THB",
                promptpay_id=RECEIVER_PROMPTPAY_ID,
                reference_id=REFERENCE_ID,
            )

    def test_get_transfer_status_maps_to_neutral_status(self, mocker):
        fake = MagicMock()
        fake.status_code = 200
        fake.json.return_value = {"transfer_id": "SCB-TR-1", "status": "FAILED"}
        mocker.patch(
            "plugins.promptpay.promptpay.bank_clients.scb.requests.get",
            return_value=fake,
        )

        assert self._client().get_transfer_status("SCB-TR-1") == "failed"


class TestBuildFundsTransferClient:
    def test_builds_kbank_and_scb(self):
        from plugins.promptpay.promptpay.bank_clients import (
            build_funds_transfer_client,
        )
        from plugins.promptpay.promptpay.bank_clients.kbank import (
            KBankFundsTransferClient,
        )
        from plugins.promptpay.promptpay.bank_clients.scb import (
            ScbFundsTransferClient,
        )

        kbank_client = build_funds_transfer_client("kbank", {"api_key": "kb"})
        scb_client = build_funds_transfer_client("scb", {"api_key": "scb"})
        assert isinstance(kbank_client, KBankFundsTransferClient)
        assert isinstance(scb_client, ScbFundsTransferClient)

    def test_unsupported_bank_raises_value_error(self):
        from plugins.promptpay.promptpay.bank_clients import (
            build_funds_transfer_client,
        )

        with pytest.raises(ValueError):
            build_funds_transfer_client("bbl", {"api_key": "x"})


class TestPromptPayPluginPayout:
    def _plugin_with_client(self, client_mock):
        from plugins.promptpay import PromptPayPlugin

        plugin = PromptPayPlugin()
        plugin._funds_transfer_client = lambda: client_mock
        return plugin

    def test_plugin_is_a_payout_provider(self):
        from plugins.promptpay import PromptPayPlugin

        assert issubclass(PromptPayPlugin, PayoutProvider)

    def test_destination_schema(self):
        from plugins.promptpay import PromptPayPlugin

        assert PromptPayPlugin().get_payout_destination_schema() == [
            {
                "name": "promptpay_id",
                "type": "text",
                "label_key": "withdraw.destination.promptpay_id",
            }
        ]

    def test_create_payout_delegates_to_bank_client(self):
        from plugins.promptpay.promptpay.bank_clients.base import BankFundsTransfer

        client_mock = MagicMock()
        client_mock.create_funds_transfer.return_value = BankFundsTransfer(
            bank="kbank", bank_transfer_id="KB-TR-1", status="processing"
        )
        plugin = self._plugin_with_client(client_mock)

        result = plugin.create_payout(
            amount=Decimal("123.45"),
            currency="THB",
            destination={"promptpay_id": RECEIVER_PROMPTPAY_ID},
            reference_id=REFERENCE_ID,
        )

        assert isinstance(result, PayoutResult)
        assert result.provider_payout_id == "KB-TR-1"
        assert result.status == "processing"
        client_mock.create_funds_transfer.assert_called_once_with(
            amount=Decimal("123.45"),
            currency="THB",
            promptpay_id=RECEIVER_PROMPTPAY_ID,
            reference_id=REFERENCE_ID,
        )

    def test_create_payout_non_thb_raises_payout_error(self):
        client_mock = MagicMock()
        plugin = self._plugin_with_client(client_mock)

        with pytest.raises(PayoutError):
            plugin.create_payout(
                amount=Decimal("12.34"),
                currency="EUR",
                destination={"promptpay_id": RECEIVER_PROMPTPAY_ID},
                reference_id=REFERENCE_ID,
            )
        client_mock.create_funds_transfer.assert_not_called()

    def test_create_payout_without_promptpay_id_raises_payout_error(self):
        plugin = self._plugin_with_client(MagicMock())

        with pytest.raises(PayoutError):
            plugin.create_payout(
                amount=Decimal("12.34"),
                currency="THB",
                destination={},
                reference_id=REFERENCE_ID,
            )

    def test_create_payout_bank_failure_raises_payout_error(self):
        from plugins.promptpay.promptpay.bank_clients.base import BankTransferError

        client_mock = MagicMock()
        client_mock.create_funds_transfer.side_effect = BankTransferError(
            "KBank transfer failed: invalid proxyId"
        )
        plugin = self._plugin_with_client(client_mock)

        with pytest.raises(PayoutError):
            plugin.create_payout(
                amount=Decimal("12.34"),
                currency="THB",
                destination={"promptpay_id": RECEIVER_PROMPTPAY_ID},
                reference_id=REFERENCE_ID,
            )

    def test_get_payout_status_delegates_to_bank_client(self):
        client_mock = MagicMock()
        client_mock.get_transfer_status.return_value = "completed"
        plugin = self._plugin_with_client(client_mock)

        assert plugin.get_payout_status("KB-TR-1") == "completed"
        client_mock.get_transfer_status.assert_called_once_with("KB-TR-1")

    def test_get_payout_status_bank_failure_raises_payout_error(self):
        from plugins.promptpay.promptpay.bank_clients.base import BankTransferError

        client_mock = MagicMock()
        client_mock.get_transfer_status.side_effect = BankTransferError("not found")
        plugin = self._plugin_with_client(client_mock)

        with pytest.raises(PayoutError):
            plugin.get_payout_status("KB-missing")
