"""
Tests for hermes-pmxt tools.

Run: source .venv/bin/activate && python -m pytest tests/ -v
"""

import pytest
from hermes_pmxt import (
    pmxt_search,
    pmxt_quote,
    pmxt_order_book,
    pmxt_ohlcv,
    pmxt_trades,
    pmxt_events,
    pmxt_arbitrage_scan,
    pmxt_server_health,
    pmxt_server_start,
)
from hermes_pmxt.tools import _remember_market, pmxt_order


class TestServer:
    def test_server_health(self):
        result = pmxt_server_health()
        assert result["success"]
        assert "running" in result["data"]

    def test_server_start(self):
        result = pmxt_server_start()
        assert result["success"]


class TestSearch:
    def test_search_polymarket(self):
        result = pmxt_search("bitcoin", exchange="polymarket", limit=3)
        assert result["success"]
        assert result["count"] > 0
        assert len(result["data"]) <= 3

        m = result["data"][0]
        assert "market_id" in m
        assert "title" in m
        assert "outcomes" in m
        assert isinstance(m["outcomes"], list)

    def test_search_kalshi(self):
        result = pmxt_search("trump", exchange="kalshi", limit=2)
        assert result["success"]
        # Kalshi might have results or not, but shouldn't error

    def test_search_all_exchanges(self):
        result = pmxt_search("election", limit=2)
        assert result["success"]
        assert "exchanges_searched" in result

    def test_search_invalid_exchange(self):
        result = pmxt_search("test", exchange="nonexistent")
        # Should fail gracefully
        assert not result["success"] or result["count"] == 0


class TestQuote:
    def test_quote_known_market(self):
        # Quote uses keyword search, not market_id
        result = pmxt_quote("bitcoin reach", "polymarket")
        assert result["success"]
        d = result["data"]
        assert "yes" in d
        assert "no" in d
        assert d["yes"] is None or (0 <= d["yes"] <= 1)
        assert d["no"] is None or (0 <= d["no"] <= 1)
        assert "yes_pct" in d
        assert "no_pct" in d
        assert "outcomes" in d

    def test_quote_nonexistent(self):
        result = pmxt_quote("totally-fake-id-12345", "polymarket")
        assert not result["success"]


class TestOrderBook:
    def test_order_book(self):
        search = pmxt_search("bitcoin", exchange="polymarket", limit=1)
        assert search["success"]
        outcome_id = search["data"][0]["outcomes"][0]["outcome_id"]

        result = pmxt_order_book(outcome_id, "polymarket")
        assert result["success"]
        d = result["data"]
        assert "bids" in d
        assert "asks" in d
        assert "bid_levels" in d
        assert "ask_levels" in d


class TestOHLCV:
    def test_ohlcv(self):
        search = pmxt_search("bitcoin", exchange="polymarket", limit=1)
        assert search["success"]
        outcome_id = search["data"][0]["outcomes"][0]["outcome_id"]

        result = pmxt_ohlcv(outcome_id, "polymarket", resolution="1d", limit=5)
        assert result["success"]
        assert isinstance(result["data"], list)

        if result["data"]:
            c = result["data"][0]
            assert "timestamp" in c
            assert "open" in c
            assert "close" in c


class TestTrades:
    def test_trades(self):
        search = pmxt_search("bitcoin", exchange="polymarket", limit=1)
        assert search["success"]
        outcome_id = search["data"][0]["outcomes"][0]["outcome_id"]

        result = pmxt_trades(outcome_id, "polymarket", limit=3)
        assert result["success"]
        assert isinstance(result["data"], list)


class TestEvents:
    def test_events(self):
        result = pmxt_events("election", exchange="polymarket", limit=2)
        assert result["success"]
        assert result["count"] > 0

        e = result["data"][0]
        assert "title" in e
        assert "market_count" in e
        assert "top_markets" in e


class TestArbitrage:
    def test_arbitrage_scan(self):
        result = pmxt_arbitrage_scan("trump", exchanges=["polymarket", "kalshi"])
        assert result["success"]
        assert "count" in result
        # May or may not find opportunities, but shouldn't error


class TestOrder:
    def test_order_resolves_yes_to_outcome_id_from_cached_market(self, monkeypatch):
        class Outcome:
            def __init__(self, outcome_id, label):
                self.outcome_id = outcome_id
                self.label = label
                self.price = 0.42

        class Market:
            market_id = "m1"
            outcomes = [Outcome("yes-token", "Yes"), Outcome("no-token", "No")]
            yes = outcomes[0]
            no = outcomes[1]

        class Order:
            id = "o1"
            market_id = "m1"
            outcome_id = "yes-token"
            side = "buy"
            type = "limit"
            amount = 10
            price = 0.42
            status = "open"
            filled = 0
            remaining = 10
            timestamp = 1234567890

        class FakeExchange:
            def __init__(self):
                self.calls = []

            def create_order(self, **kwargs):
                self.calls.append(kwargs)
                return Order()

        fake_exchange = FakeExchange()
        _remember_market("polymarket", Market())

        monkeypatch.setattr("hermes_pmxt.tools._ensure", lambda: None)
        monkeypatch.setattr("hermes_pmxt.tools.get_exchange", lambda exchange: (fake_exchange, None))

        result = pmxt_order("m1", "yes", 10, "buy", "polymarket", price=0.42)

        assert result["success"]
        assert fake_exchange.calls[0]["outcome_id"] == "yes-token"
        assert fake_exchange.calls[0]["market_id"] == "m1"

    def test_order_accepts_exact_outcome_id_without_cached_market(self, monkeypatch):
        class Order:
            id = "o2"
            market_id = "m2"
            outcome_id = "12345678901234567890"
            side = "buy"
            type = "market"
            amount = 1
            price = None
            status = "open"
            filled = 0
            remaining = 1
            timestamp = 1234567891

        class FakeExchange:
            def __init__(self):
                self.calls = []

            def create_order(self, **kwargs):
                self.calls.append(kwargs)
                return Order()

        fake_exchange = FakeExchange()

        monkeypatch.setattr("hermes_pmxt.tools._ensure", lambda: None)
        monkeypatch.setattr("hermes_pmxt.tools.get_exchange", lambda exchange: (fake_exchange, None))

        result = pmxt_order(
            "m2",
            "12345678901234567890",
            1,
            "buy",
            "polymarket",
        )

        assert result["success"]
        assert fake_exchange.calls[0]["outcome_id"] == "12345678901234567890"

    def test_order_accepts_alphanumeric_outcome_id_without_cached_market(self, monkeypatch):
        class Order:
            id = "o3"
            market_id = "m3"
            outcome_id = "KXUKPARTY-29-C"
            side = "buy"
            type = "market"
            amount = 1
            price = None
            status = "open"
            filled = 0
            remaining = 1
            timestamp = 1234567892

        class FakeExchange:
            def __init__(self):
                self.calls = []

            def create_order(self, **kwargs):
                self.calls.append(kwargs)
                return Order()

        fake_exchange = FakeExchange()

        monkeypatch.setattr("hermes_pmxt.tools._ensure", lambda: None)
        monkeypatch.setattr("hermes_pmxt.tools.get_exchange", lambda exchange: (fake_exchange, None))

        result = pmxt_order(
            "m3",
            "KXUKPARTY-29-C",
            1,
            "buy",
            "kalshi",
        )

        assert result["success"]
        assert fake_exchange.calls[0]["outcome_id"] == "KXUKPARTY-29-C"

    def test_order_returns_clear_error_when_outcome_cannot_be_resolved(self, monkeypatch):
        class FakeExchange:
            def create_order(self, **kwargs):
                raise AssertionError("create_order should not be called")

        monkeypatch.setattr("hermes_pmxt.tools._ensure", lambda: None)
        monkeypatch.setattr("hermes_pmxt.tools.get_exchange", lambda exchange: (FakeExchange(), None))

        result = pmxt_order("unknown-market", "yes", 1, "buy", "polymarket")

        assert result["success"] is False
        assert "Could not resolve outcome" in result["error"]


class TestReturnFormat:
    """All tools should return {"success": bool, "data": ...} format."""

    def test_success_has_data(self):
        result = pmxt_search("test", exchange="polymarket", limit=1)
        assert "success" in result
        assert "data" in result

    def test_error_has_error(self):
        result = pmxt_quote("fake-id", "nonexistent")
        assert result["success"] is False
        assert "error" in result
