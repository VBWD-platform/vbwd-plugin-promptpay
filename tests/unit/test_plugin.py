"""Plugin tests — deep-merge config + metadata."""
from vbwd.plugins.base import PluginStatus

from plugins.promptpay import PromptPayPlugin, DEFAULT_CONFIG


class TestPromptPayPlugin:
    def test_metadata(self):
        assert PromptPayPlugin().metadata.name == "promptpay"

    def test_deep_merge_preserves_other_banks(self):
        plugin = PromptPayPlugin()
        plugin.initialize({"bank_credentials": {"kbank": {"api_key": "KB-X"}}})
        assert plugin.status == PluginStatus.INITIALIZED
        assert plugin._config["bank_credentials"]["kbank"]["api_key"] == "KB-X"
        assert "scb" in plugin._config["bank_credentials"]
        assert plugin._config["currency"] == DEFAULT_CONFIG["currency"]
