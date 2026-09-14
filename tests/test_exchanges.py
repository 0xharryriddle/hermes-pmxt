"""Tests for exchange initialization helpers and normalization."""
import pytest

from hermes_pmxt import exchanges
from hermes_pmxt.exchanges import is_pmxt_available


class TestNormalizeExchangeName:
    def test_aliases(self):
        assert exchanges.normalize_exchange_name("Polymarket US") == "polymarket_us"
        assert exchanges.normalize_exchange_name("polymarket-us") == "polymarket_us"
        assert exchanges.normalize_exchange_name("Kalshi") == "kalshi"
        assert exchanges.normalize_exchange_name("Limitless") == "limitless"

    def test_preserves_known_names(self):
        assert exchanges.normalize_exchange_name("polymarket") == "polymarket"
        assert exchanges.normalize_exchange_name("POLYMARKET") == "polymarket"
        assert exchanges.normalize_exchange_name("kalshi") == "kalshi"

    def test_handles_unknown(self):
        result = exchanges.normalize_exchange_name("nonexistent")
        assert result is not None


class TestIsPmxtAvailable:
    def test_returns_bool(self):
        assert isinstance(is_pmxt_available(), bool)


class TestExchangeList:
    def test_exchanges_tuple(self):
        assert "polymarket" in exchanges.EXCHANGES
        assert "kalshi" in exchanges.EXCHANGES
        assert isinstance(exchanges.EXCHANGES, (tuple, list))

    def test_trading_exchanges(self):
        assert "polymarket" in exchanges.TRADING_EXCHANGES
        for te in exchanges.TRADING_EXCHANGES:
            assert te in exchanges.EXCHANGES


class TestPmxt254Contract:
    def test_hosted_mode_does_not_start_local_sidecar(self, monkeypatch):
        """Hosted PMXT is a remote client and must not require pmxt.server."""
        monkeypatch.setenv("PMXT_API_KEY", "pmxt-test-key")

        class FakePMXT:
            class server:
                @staticmethod
                def health():
                    raise AssertionError("hosted mode must not probe the sidecar")

        monkeypatch.setattr(exchanges, "_get_pmxt", lambda: FakePMXT)

        assert exchanges.ensure_server() == (True, None)

    def test_hosted_polymarket_receives_pmxt_connection_context(self, monkeypatch):
        """Hosted clients must not silently fall back to a local sidecar."""
        monkeypatch.setenv("PMXT_API_KEY", "pmxt-test-key")
        monkeypatch.setenv("PMXT_WALLET_ADDRESS", "0xwallet")
        monkeypatch.setenv("PMXT_PRIVATE_KEY", "0xprivate")

        captured = {}

        class FakePolymarket:
            def __init__(self, **kwargs):
                captured.update(kwargs)

        class FakePMXT:
            Polymarket = FakePolymarket

        monkeypatch.setattr(exchanges, "_get_pmxt", lambda: FakePMXT)

        exchanges._create_exchange("polymarket")

        assert captured["pmxt_api_key"] == "pmxt-test-key"
        assert captured["wallet_address"] == "0xwallet"
        assert captured["private_key"] == "0xprivate"

    def test_polymarket_us_uses_upstream_export_name(self, monkeypatch):
        """PMXT 2.54 exports PolymarketUS, not only title-cased aliases."""
        class FakePolymarketUS:
            def __init__(self, **kwargs):
                pass

        class FakePMXT:
            PolymarketUS = FakePolymarketUS

        monkeypatch.setattr(exchanges, "_get_pmxt", lambda: FakePMXT)

        assert exchanges._exchange_class("polymarket_us") is FakePolymarketUS

    def test_router_uses_only_router_supported_connection_arguments(self, monkeypatch):
        """PMXT Router does not accept wallet_address/private venue arguments."""
        monkeypatch.setenv("PMXT_API_KEY", "pmxt-test-key")
        monkeypatch.setenv("PMXT_WALLET_ADDRESS", "0xwallet")
        captured = {}

        class FakeRouter:
            def __init__(self, **kwargs):
                captured.update(kwargs)

        class FakePMXT:
            Router = FakeRouter

        monkeypatch.setattr(exchanges, "_get_pmxt", lambda: FakePMXT)

        exchanges._create_exchange("router")

        assert captured == {"pmxt_api_key": "pmxt-test-key"}

    def test_hunch_is_known_but_not_a_generic_trading_exchange(self):
        """Hunch lacks generic limit/sell/cancel semantics in PMXT 2.54."""
        assert "hunch" in exchanges.EXCHANGES
        assert "hunch" not in exchanges.TRADING_EXCHANGES


class TestCreateExchangeMocked:
    def test_limitless_uses_env_vars(self, monkeypatch):
        """Test that _create_exchange reads env vars for Limitless."""
        monkeypatch.setenv("LIMITLESS_API_KEY", "limitless-api")
        monkeypatch.setenv("LIMITLESS_PRIVATE_KEY", "limitless-private")

        captured = {}

        class FakeLimitless:
            def __init__(self, **kwargs):
                captured.update(kwargs)

        class FakePMXT:
            Limitless = FakeLimitless
            Polymarket = FakeLimitless
            Kalshi = FakeLimitless

        monkeypatch.setattr(exchanges, "_get_pmxt", lambda: FakePMXT)

        exchanges._create_exchange("limitless")

        assert captured["api_key"] == "limitless-api"
        assert captured["private_key"] == "limitless-private"

    def test_polymarket_us_uses_env_vars(self, monkeypatch):
        """Test that _create_exchange reads env vars for Polymarket US."""
        monkeypatch.setenv("POLYMARKET_US_API_KEY", "pmus-api")
        monkeypatch.setenv("POLYMARKET_US_PRIVATE_KEY", "pmus-private")

        captured = {}

        class FakePolymarketUS:
            def __init__(self, **kwargs):
                captured.update(kwargs)

        class FakePMXT:
            PolymarketUS = FakePolymarketUS

        monkeypatch.setattr(exchanges, "_get_pmxt", lambda: FakePMXT)

        exchanges._create_exchange("polymarket_us")

        assert captured["api_key"] == "pmus-api"
        assert captured["private_key"] == "pmus-private"

    def test_unknown_exchange_raises(self, monkeypatch):
        """Test that unknown exchange raises ValueError."""
        class FakePMXT:
            pass

        monkeypatch.setattr(exchanges, "_get_pmxt", lambda: FakePMXT)

        with pytest.raises(ValueError, match="Unknown exchange"):
            exchanges._create_exchange("nonexistent")

    def test_polymarket_uses_env_vars(self, monkeypatch):
        """Test that _create_exchange reads env vars for Polymarket."""
        monkeypatch.setenv("POLYMARKET_PRIVATE_KEY", "0xpoly")
        monkeypatch.setenv("POLYMARKET_PROXY_ADDRESS", "0xproxy")

        captured = {}

        class FakePolymarket:
            def __init__(self, **kwargs):
                captured.update(kwargs)

        class FakePMXT:
            Polymarket = FakePolymarket

        monkeypatch.setattr(exchanges, "_get_pmxt", lambda: FakePMXT)

        exchanges._create_exchange("polymarket")

        assert captured.get("private_key") == "0xpoly"
        assert captured.get("proxy_address") == "0xproxy"
        assert captured.get("signature_type") == "gnosis-safe"
