"""Native Hermes plugin registration tests without a live Hermes runtime."""

import json
import tomllib
from pathlib import Path

import pytest


@pytest.mark.unit
class TestPluginRegistration:
    def test_package_version_is_040(self):
        import hermes_pmxt

        assert hermes_pmxt.__version__ == "0.4.0"

    def test_distribution_declares_native_plugin_entry_point(self):
        config = tomllib.loads(Path("pyproject.toml").read_text())
        entry_points = config["project"]["entry-points"]["hermes_agent.plugins"]

        assert entry_points["hermes-pmxt"] == "hermes_pmxt"

    def test_native_plugin_surface_contains_no_write_tools(self):
        from hermes_pmxt.plugin import TOOLS

        names = {name for name, _schema, _handler in TOOLS}
        forbidden = {"pmxt_order", "pmxt_build_order", "pmxt_submit_order", "pmxt_cancel_order"}

        assert names.isdisjoint(forbidden)

    def test_registers_curated_read_only_tools_and_bundled_skill(self):
        from hermes_pmxt.plugin import register

        class FakeContext:
            def __init__(self):
                self.tools = {}
                self.skills = {}

            def register_tool(self, *, name, toolset, schema, handler, **kwargs):
                self.tools[name] = {
                    "toolset": toolset,
                    "schema": schema,
                    "handler": handler,
                }

            def register_skill(self, name, path):
                self.skills[name] = Path(path)

        ctx = FakeContext()
        register(ctx)

        assert set(ctx.tools) == {
            "pmxt_runtime_status",
            "pmxt_list_exchanges",
            "pmxt_search",
            "pmxt_events",
            "pmxt_series",
            "pmxt_order_books",
            "pmxt_matched_market_clusters",
        }
        assert all(entry["toolset"] == "pmxt" for entry in ctx.tools.values())
        assert ctx.skills["pmxt"].is_file()

    def test_handler_returns_standard_json_envelope(self):
        from hermes_pmxt.plugin import register

        class FakeContext:
            def __init__(self):
                self.tools = {}

            def register_tool(self, *, name, handler, **kwargs):
                self.tools[name] = handler

            def register_skill(self, name, path):
                pass

        ctx = FakeContext()
        register(ctx)

        payload = json.loads(ctx.tools["pmxt_runtime_status"]({}))

        assert payload["success"] is True
        assert "mode" in payload["data"]

    def test_extended_read_only_handlers_use_curated_pmxt_calls(self, monkeypatch):
        from hermes_pmxt import plugin

        calls = []

        def fake_call(method, exchange, params=None, **kwargs):
            calls.append((method, exchange, params))
            return {"success": True, "data": {}}

        monkeypatch.setattr(plugin, "pmxt_call", fake_call)

        class FakeContext:
            def __init__(self):
                self.tools = {}

            def register_tool(self, *, name, handler, **kwargs):
                self.tools[name] = handler

            def register_skill(self, name, path):
                pass

        ctx = FakeContext()
        plugin.register(ctx)

        assert json.loads(ctx.tools["pmxt_series"]({"exchange": "hunch", "query": "token"}))["success"]
        assert json.loads(ctx.tools["pmxt_order_books"]({"outcome_ids": ["yes", "no"]}))["success"]
        assert json.loads(ctx.tools["pmxt_matched_market_clusters"]({"query": "fed"}))["success"]
        assert calls == [
            ("fetchSeries", "hunch", {"query": "token"}),
            ("fetchOrderBooks", "polymarket", {"outcome_ids": ["yes", "no"]}),
            ("fetchMatchedMarketClusters", "router", {"query": "fed"}),
        ]
