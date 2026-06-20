"""
Tests for hermes-pmxt tools.

Unit tests (no pmxt required):
    pytest -q -m unit

Integration tests (need pmxt + sidecar/API):
    pytest -q -m integration

Trading tests (disabled by default):
    pytest -q -m trading --run-trading
"""
import pytest

from hermes_pmxt import (
    get_mode,
    get_base_url,
    pmxt_list_exchanges,
    pmxt_runtime_status,
    runtime_status_str,
)
from hermes_pmxt.registry import (
    TOOLS,
    KNOWN_EXCHANGES,
    get_tool,
    list_tools,
    is_destructive as registry_is_destructive,
    requires_credentials,
)
from hermes_pmxt.shaper import (
    compact_market,
    compact_event,
    compact_order_book,
    shape_result,
)


# ============================================================================
# Unit tests -- no pmxt, no network
# ============================================================================

@pytest.mark.unit
class TestConfig:
    def test_runtime_status_returns_valid_structure(self):
        result = pmxt_runtime_status()
        assert result["success"]
        assert "mode" in result["data"]
        assert isinstance(result["data"]["pmxt_installed"], bool)
        assert isinstance(result["data"]["has_api_key"], bool)
        assert result["data"]["mode"] in ("hosted", "custom", "local-sidecar")

    def test_runtime_status_str(self):
        s = runtime_status_str()
        assert isinstance(s, str)
        assert "mode=" in s

    def test_get_mode_defaults(self):
        mode = get_mode()
        assert mode in ("hosted", "custom", "local-sidecar")

    def test_get_base_url_defaults(self):
        url = get_base_url()
        assert url.startswith("http")

    def test_pmxt_list_exchanges(self):
        result = pmxt_list_exchanges()
        assert result["success"]
        assert len(result["data"]["known"]) >= 8
        assert "polymarket" in result["data"]["known"]
        assert "kalshi" in result["data"]["known"]

    def test_list_exchanges_mode_field(self):
        result = pmxt_list_exchanges()
        assert result["data"]["mode"] in ("hosted", "custom", "local-sidecar")


@pytest.mark.unit
class TestRegistry:
    def test_tools_count(self):
        assert len(TOOLS) >= 30

    def test_destructive_tools(self):
        destructive = [t for t in TOOLS if t.destructive]
        names = {t.name for t in destructive}
        assert "createOrder" in names
        assert "submitOrder" in names
        assert "cancelOrder" in names

    def test_build_order_not_destructive(self):
        tool = get_tool("buildOrder")
        assert tool is not None
        assert not tool.destructive

    def test_read_only_tools_include_fetch(self):
        tool = get_tool("fetchMarkets")
        assert tool is not None
        assert tool.read_only
        assert not tool.destructive

    def test_credential_required_tools(self):
        assert registry_is_destructive("createOrder")
        assert not registry_is_destructive("fetchMarkets")
        assert requires_credentials("buildOrder")

    def test_list_tools_by_category(self):
        trading = list_tools(category="trading")
        assert len(trading) >= 5
        for t in trading:
            assert t.category == "trading"

    def test_list_tools_read_only(self):
        ro = list_tools(read_only=True)
        for t in ro:
            assert not t.destructive

    def test_known_exchanges(self):
        assert "polymarket" in KNOWN_EXCHANGES
        assert "kalshi" in KNOWN_EXCHANGES
        assert "router" in KNOWN_EXCHANGES
        assert len(KNOWN_EXCHANGES) >= 12

    def test_get_tool_unknown(self):
        assert get_tool("nonexistentMethod") is None


@pytest.mark.unit
class TestShaper:
    def test_compact_market(self):
        market = {
            "market_id": "m1",
            "title": "Test Market",
            "outcomes": [
                {"label": "Yes", "price": 0.6},
                {"label": "No", "price": 0.4},
            ],
            "volume_24h": 1000,
            "liquidity": 2000,
            "status": "active",
            "exchange": "polymarket",
        }
        cmp = compact_market(market)
        assert cmp["market_id"] == "m1"
        assert cmp["title"] == "Test Market"
        assert cmp["outcomes"][0]["label"] == "Yes"
        assert cmp["volume_24h"] == 1000
        assert "status" not in cmp  # active filtered
        assert cmp["exchange"] == "polymarket"

    def test_compact_event(self):
        event = {
            "event_id": "e1",
            "title": "Test Event",
            "market_count": 3,
            "top_markets": [
                {"market_id": "m1", "title": "M1", "outcomes": [{"label": "Yes", "price": 0.5}]},
            ],
            "exchange": "polymarket",
        }
        cmp = compact_event(event)
        assert cmp["event_id"] == "e1"
        assert cmp["title"] == "Test Event"
        assert cmp["market_count"] == 3
        assert cmp["exchange"] == "polymarket"
        assert len(cmp["markets"]) == 1

    def test_compact_order_book(self):
        book = {
            "best_bid": 0.42,
            "best_ask": 0.44,
            "spread": 0.02,
            "bids": [{"price": 0.42, "size": 100}],
            "asks": [{"price": 0.44, "size": 50}],
        }
        cmp = compact_order_book(book)
        assert cmp["best_bid"] == 0.42
        assert cmp["best_ask"] == 0.44
        assert cmp["spread"] == 0.02
        assert len(cmp["bids"]) == 1

    def test_shape_result_markets(self):
        raw = [
            {"market_id": "m1", "title": "T1", "outcomes": [], "volume_24h": 100, "liquidity": 200},
        ]
        shaped = shape_result("fetchMarkets", raw)
        assert "markets" in shaped
        assert len(shaped["markets"]) == 1

    def test_shape_result_verbose(self):
        raw = {"key": "value"}
        shaped = shape_result("fetchMarkets", raw, verbose=True)
        assert "raw" in shaped

    def test_truncate_long_description(self):
        from hermes_pmxt.shaper import _truncate
        assert _truncate("abc", 2) == "ab..."
        assert _truncate("ab", 5) == "ab"
        assert _truncate(None, 5) == ""
        assert _truncate(123, 5) == ""


@pytest.mark.unit
class TestToolCallSafety:
    """Test that destructive operations require confirmed=True."""

    def test_require_confirmed_blocks(self):
        from hermes_pmxt.tools import _require_confirmed

        result = _require_confirmed("createOrder", confirmed=False)
        assert result is not None
        assert result["success"] is False
        assert "confirmation" in result["error"].lower()

    def test_require_confirmed_allows(self):
        from hermes_pmxt.tools import _require_confirmed

        result = _require_confirmed("createOrder", confirmed=True)
        assert result is None

    def test_runtime_status_works(self):
        result = pmxt_runtime_status()
        assert result["success"]
        assert "mode" in result["data"]

    def test_destructive_list_consistency(self):
        from hermes_pmxt.tools import _DESTRUCTIVE_CONFIRM_MSG
        assert "confirmation" in _DESTRUCTIVE_CONFIRM_MSG.lower()


# ============================================================================
# Integration tests -- need pmxt and sidecar/API
# ============================================================================

@pytest.mark.integration
class TestServer:
    def test_server_health(self):
        from hermes_pmxt import pmxt_server_health
        result = pmxt_server_health()
        assert result["success"]
        assert "running" in result["data"]

    def test_server_status(self):
        from hermes_pmxt import pmxt_server_status
        result = pmxt_server_status()
        assert result["success"]


@pytest.mark.integration
class TestSearch:
    def test_search_polymarket(self):
        from hermes_pmxt import pmxt_search
        result = pmxt_search("bitcoin", exchange="polymarket", limit=3)
        assert result["success"]
        assert result["count"] > 0
        m = result["data"][0]
        assert "market_id" in m
        assert "outcomes" in m

    def test_search_kalshi(self):
        from hermes_pmxt import pmxt_search
        result = pmxt_search("trump", exchange="kalshi", limit=2)
        assert result["success"]

    def test_search_all_exchanges(self):
        from hermes_pmxt import pmxt_search
        result = pmxt_search("election", limit=2)
        assert result["success"]
        assert "exchanges_searched" in result


@pytest.mark.integration
class TestQuote:
    def test_quote_known_market(self):
        from hermes_pmxt import pmxt_quote
        result = pmxt_quote("bitcoin reach", "polymarket")
        assert result["success"]
        d = result["data"]
        assert "yes" in d
        assert "no" in d

    def test_quote_nonexistent(self):
        from hermes_pmxt import pmxt_quote
        result = pmxt_quote("totally-fake-id-12345", "polymarket")
        assert not result["success"]


@pytest.mark.integration
class TestOrderBook:
    def test_order_book(self):
        from hermes_pmxt import pmxt_search, pmxt_order_book
        search = pmxt_search("bitcoin", exchange="polymarket", limit=1)
        assert search["success"]
        outcome_id = search["data"][0]["outcomes"][0]["outcome_id"]
        result = pmxt_order_book(outcome_id, "polymarket")
        assert result["success"]
        assert "bids" in result["data"]


@pytest.mark.integration
class TestEvents:
    def test_events(self):
        from hermes_pmxt import pmxt_events
        result = pmxt_events("election", exchange="polymarket", limit=2)
        assert result["success"]
        assert result["count"] > 0


@pytest.mark.integration
class TestArbitrage:
    def test_arbitrage_scan(self):
        from hermes_pmxt import pmxt_arbitrage_scan
        result = pmxt_arbitrage_scan("trump", exchanges=["polymarket", "kalshi"])
        assert result["success"]


@pytest.mark.integration
class TestReturnFormat:
    def test_success_has_data(self):
        from hermes_pmxt import pmxt_search
        result = pmxt_search("test", exchange="polymarket", limit=1)
        assert "success" in result
        assert "data" in result

    def test_error_has_error(self):
        from hermes_pmxt import pmxt_quote
        result = pmxt_quote("fake-id", "nonexistent")
        assert result["success"] is False
        assert "error" in result


# ============================================================================
# Unit test classes that mock exchange behavior
# ============================================================================

@pytest.mark.unit
class TestOrderMocked:
    def test_order_resolves_yes_to_outcome_id_from_cached_market(self, monkeypatch):
        from hermes_pmxt.tools import _remember_market, pmxt_order

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
        monkeypatch.setattr(
            "hermes_pmxt.tools.get_exchange",
            lambda exchange: (fake_exchange, None),
        )

        result = pmxt_order("m1", "yes", 10, "buy", "polymarket", price=0.42)

        assert result["success"]
        assert fake_exchange.calls[0]["outcome_id"] == "yes-token"
        assert fake_exchange.calls[0]["market_id"] == "m1"

    def test_order_accepts_exact_outcome_id_without_cached_market(self, monkeypatch):
        from hermes_pmxt.tools import pmxt_order

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
        monkeypatch.setattr(
            "hermes_pmxt.tools.get_exchange",
            lambda exchange: (fake_exchange, None),
        )

        result = pmxt_order("m2", "12345678901234567890", 1, "buy", "polymarket")

        assert result["success"]
        assert fake_exchange.calls[0]["outcome_id"] == "12345678901234567890"

    def test_order_returns_error_when_outcome_cannot_be_resolved(self, monkeypatch):
        from hermes_pmxt.tools import pmxt_order

        class FakeExchange:
            def create_order(self, **kwargs):
                raise AssertionError("should not be called")

        monkeypatch.setattr("hermes_pmxt.tools._ensure", lambda: None)
        monkeypatch.setattr(
            "hermes_pmxt.tools.get_exchange",
            lambda exchange: (FakeExchange(), None),
        )

        result = pmxt_order("unknown-market", "yes", 1, "buy", "polymarket")

        assert result["success"] is False
        assert "Could not resolve outcome" in result["error"]


@pytest.mark.unit
class TestCompareMocked:
    def test_compare_market_groups_similar_titles(self, monkeypatch):
        from hermes_pmxt import pmxt_compare_market

        def fake_search(query, exchange=None, limit=5, **kwargs):
            data = {
                "polymarket": [{
                    "exchange": "polymarket",
                    "market_id": "p1",
                    "title": "Will Bitcoin hit $200k in 2026?",
                    "slug": "btc-200k",
                    "outcomes": [
                        {"label": "Yes", "price": 0.31},
                        {"label": "No", "price": 0.69},
                    ],
                    "volume_24h": 100,
                    "liquidity": 200,
                    "url": "",
                }],
                "kalshi": [{
                    "exchange": "kalshi",
                    "market_id": "k1",
                    "title": "Will Bitcoin hit $200k in 2026",
                    "slug": "BTC200K",
                    "outcomes": [
                        {"label": "Yes", "price": 0.37},
                        {"label": "No", "price": 0.63},
                    ],
                    "volume_24h": 50,
                    "liquidity": 150,
                    "url": "",
                }],
            }
            return {"success": True, "data": data.get(exchange, [])}

        monkeypatch.setattr("hermes_pmxt.tools.pmxt_search", fake_search)

        result = pmxt_compare_market("bitcoin 200k", ["polymarket", "kalshi"])

        assert result["success"]
        assert result["count"] == 1
        assert result["data"][0]["exchange_count"] == 2
        assert result["data"][0]["yes_spread"] == pytest.approx(0.06)


@pytest.mark.unit
class TestPortfolioMocked:
    def test_portfolio_aggregates_positions(self, monkeypatch):
        from hermes_pmxt import pmxt_portfolio

        def fake_balance(exchange):
            return {
                "success": True,
                "data": [{"currency": "USD", "available": 100, "total": 100, "locked": 0}],
            }

        def fake_positions(exchange):
            if exchange == "kalshi":
                return {"success": False, "error": "missing creds"}
            return {
                "success": True,
                "data": [
                    {
                        "market_id": "m1",
                        "size": 4,
                        "current_price": 0.6,
                        "unrealized_pnl": 1.2,
                    }
                ],
            }

        monkeypatch.setattr("hermes_pmxt.tools.pmxt_balance", fake_balance)
        monkeypatch.setattr("hermes_pmxt.tools.pmxt_positions", fake_positions)

        result = pmxt_portfolio(["polymarket", "kalshi"])

        assert result["success"]
        assert result["data"]["summary"]["total_positions"] == 1
        assert result["data"]["summary"]["total_notional"] == pytest.approx(2.4)
        assert result["partial_errors"] == ["missing creds"]


@pytest.mark.unit
class TestSearchMocked:
    def test_search_forwards_optional_filters(self, monkeypatch):
        from hermes_pmxt import pmxt_search

        class Outcome:
            outcome_id = "yes-1"
            label = "Yes"
            price = 0.6
            price_change_24h = None

        class Market:
            market_id = "m1"
            title = "Will BTC hit 200k?"
            description = ""
            outcomes = [Outcome()]
            volume_24h = 10
            liquidity = 20
            url = ""
            status = "active"
            slug = "btc-200k"
            category = "crypto"
            yes = Outcome()
            no = None

        class FakeExchange:
            def __init__(self):
                self.kwargs = None

            def fetch_markets(self, query, limit, sort=None, searchIn=None, slug=None):
                self.kwargs = {
                    "query": query,
                    "limit": limit,
                    "sort": sort,
                    "searchIn": searchIn,
                    "slug": slug,
                }
                return [Market()]

        fake_exchange = FakeExchange()

        monkeypatch.setattr("hermes_pmxt.tools._ensure", lambda: None)
        monkeypatch.setattr(
            "hermes_pmxt.tools.get_exchange",
            lambda exchange: (fake_exchange, None),
        )

        result = pmxt_search(
            "bitcoin", exchange="polymarket", limit=5,
            sort="volume", search_in="both", slug="btc-200k",
        )

        assert result["success"]
        assert fake_exchange.kwargs == {
            "query": "bitcoin", "limit": 5,
            "sort": "volume", "searchIn": "both", "slug": "btc-200k",
        }


@pytest.mark.unit
class TestExecutionPriceMocked:
    def test_execution_price_manual_fallback(self, monkeypatch):
        from hermes_pmxt import pmxt_execution_price

        class Level:
            def __init__(self, price, size):
                self.price = price
                self.size = size

        class Book:
            asks = [Level(0.52, 5), Level(0.54, 10)]
            bids = [Level(0.48, 5), Level(0.46, 10)]

        class FakeExchange:
            def fetch_order_book(self, outcome_id):
                return Book()

        monkeypatch.setattr("hermes_pmxt.tools._ensure", lambda: None)
        monkeypatch.setattr(
            "hermes_pmxt.tools.get_exchange",
            lambda exchange: (FakeExchange(), None),
        )

        result = pmxt_execution_price("outcome-1", "polymarket", "buy", 10)

        assert result["success"]
        assert result["data"]["best_price"] == 0.52
        assert result["data"]["estimated_price"] == pytest.approx(0.53)
        assert result["data"]["slippage"] == pytest.approx(0.01)
