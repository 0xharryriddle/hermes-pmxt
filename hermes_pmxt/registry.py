"""
Generated tool registry for PMXT methods.

Maps PMXT API methods to Python-friendly names with:
  - arg specs for positional reconstruction
  - safety annotations (read_only, destructive, idempotent)
  - credential requirements
  - supported exchanges

This file serves as a static snapshot. For auto-generation from PMXT
OpenAPI specs, run: python scripts/sync_pmxt_registry.py
"""

from __future__ import annotations

from typing import Optional

# ---------------------------------------------------------------------------
# Arg spec
# ---------------------------------------------------------------------------


class ArgSpec:
    """Describes a single positional argument for a PMXT API method."""

    __slots__ = ("name", "kind", "optional", "flatten")

    def __init__(self, name: str, kind: str = "object", optional: bool = True, flatten: bool = False):
        self.name = name
        self.kind = kind
        self.optional = optional
        self.flatten = flatten

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "kind": self.kind,
            "optional": self.optional,
            "flatten": self.flatten,
        }


# ---------------------------------------------------------------------------
# Tool definition
# ---------------------------------------------------------------------------


class ToolDef:
    """Definition of a single PMXT tool/method."""

    __slots__ = ("name", "method", "description", "args", "read_only", "destructive",
                 "idempotent", "requires_credentials", "category")

    def __init__(
        self,
        name: str,
        method: str,
        description: str,
        args: Optional[list[ArgSpec]] = None,
        read_only: bool = True,
        destructive: bool = False,
        idempotent: bool = False,
        requires_credentials: bool = False,
        category: str = "data",
    ):
        self.name = name
        self.method = method
        self.description = description
        self.args = args or []
        self.read_only = read_only
        self.destructive = destructive
        self.idempotent = idempotent
        self.requires_credentials = requires_credentials
        self.category = category


# ---------------------------------------------------------------------------
# Supported exchanges (from pmxt-mcp generated tools.ts, v2.50.x)
# ---------------------------------------------------------------------------

KNOWN_EXCHANGES = [
    "polymarket",
    "polymarket_us",
    "kalshi",
    "kalshi-demo",
    "limitless",
    "probable",
    "baozi",
    "myriad",
    "opinion",
    "metaculus",
    "smarkets",
    "gemini-titan",
    "hyperliquid",
    "suibets",
    "rain",
    "mock",
    "router",
]

# Aliases for user-facing exchange names
EXCHANGE_ALIASES: dict[str, str] = {
    "polymarket-us": "polymarket_us",
    "polymarket us": "polymarket_us",
    "polymarketus": "polymarket_us",
    "kalshi-demo": "kalshi-demo",
    "kalshi demo": "kalshi-demo",
    "gemini-titan": "gemini-titan",
    "gemini titan": "gemini-titan",
}


# ---------------------------------------------------------------------------
# Tool registry (static snapshot)
# ---------------------------------------------------------------------------


def _a(name: str, kind: str = "object", optional: bool = True, flatten: bool = False) -> ArgSpec:
    return ArgSpec(name, kind, optional, flatten)


TOOLS: list[ToolDef] = [
    # --- Market & Event Data ---
    ToolDef("fetchMarkets", "fetchMarkets", "Search tradeable markets by query/slug/category.",
            [_a("params", flatten=True)], read_only=True, category="data"),
    ToolDef("fetchMarketsPaginated", "fetchMarketsPaginated",
            "Paginated market fetch with cursor snapshot. First call w/o cursor fetches all; subsequent cursor calls slice from cache.",
            [_a("params", flatten=True)], read_only=True, category="data"),
    ToolDef("fetchEvents", "fetchEvents", "Search event groups (broad topics) containing child markets.",
            [_a("params", flatten=True)], read_only=True, category="data"),
    ToolDef("fetchEventsPaginated", "fetchEventsPaginated",
            "Paginated event fetch with cursor snapshot.",
            [_a("params", flatten=True)], read_only=True, category="data"),
    ToolDef("fetchMarket", "fetchMarket", "Fetch a single market by ID, slug, or URL.",
            [_a("params", flatten=True)], read_only=True, category="data"),
    ToolDef("fetchEvent", "fetchEvent", "Fetch a single event by ID or slug.",
            [_a("params", flatten=True)], read_only=True, category="data"),
    ToolDef("fetchSeries", "fetchSeries", "Fetch series (4th tier below event/market/outcome).",
            [_a("params", flatten=True)], read_only=True, category="data"),
    ToolDef("loadMarkets", "loadMarkets", "Load and cache all markets locally. Recommended for stable iteration.",
            [], read_only=True, idempotent=True, category="data"),

    # --- Order Book & Pricing ---
    ToolDef("fetchOHLCV", "fetchOHLCV", "Get price history candles for an outcome.",
            [_a("outcomeId", "string", optional=False),
             _a("params", flatten=True)], read_only=True, category="data"),
    ToolDef("fetchOrderBook", "fetchOrderBook", "Get current order book depth for an outcome.",
            [_a("outcomeId", "string", optional=False),
             _a("limit", "number"),
             _a("params", flatten=True)], read_only=True, category="data"),
    ToolDef("fetchOrderBooks", "fetchOrderBooks", "Batch fetch order books for multiple outcome IDs.",
            [_a("outcomeIds", "unknown", optional=False)], read_only=True, category="data"),
    ToolDef("fetchTrades", "fetchTrades", "Get recent trades for an outcome.",
            [_a("outcomeId", "string", optional=False),
             _a("params", flatten=True)], read_only=True, category="data"),

    # --- Order Management ---
    ToolDef("createOrder", "createOrder", "Place an order directly. DESTRUCTIVE -- requires user confirmation.",
            [_a("params", flatten=True)], destructive=True, requires_credentials=True, category="trading"),
    ToolDef("buildOrder", "buildOrder", "Build (sign/preview) an order without submitting.",
            [_a("params", flatten=True)], read_only=True, idempotent=True, requires_credentials=True, category="trading"),
    ToolDef("submitOrder", "submitOrder", "Submit a pre-built order. DESTRUCTIVE -- requires user confirmation.",
            [_a("built", "object", optional=False)], destructive=True, requires_credentials=True, category="trading"),
    ToolDef("cancelOrder", "cancelOrder", "Cancel an open order. DESTRUCTIVE -- requires user confirmation.",
            [_a("orderId", "string", optional=False)], destructive=True, requires_credentials=True, category="trading"),
    ToolDef("fetchOrder", "fetchOrder", "Fetch a single order by ID.",
            [_a("orderId", "string", optional=False)], read_only=True, requires_credentials=True, category="trading"),
    ToolDef("fetchOpenOrders", "fetchOpenOrders", "Fetch open orders, optionally filtered by market.",
            [_a("marketId", "string")], read_only=True, requires_credentials=True, category="trading"),
    ToolDef("fetchClosedOrders", "fetchClosedOrders", "Fetch closed/filled orders.",
            [_a("params", flatten=True)], read_only=True, requires_credentials=True, category="trading"),
    ToolDef("fetchAllOrders", "fetchAllOrders", "Fetch all orders (open + closed).",
            [_a("params", flatten=True)], read_only=True, requires_credentials=True, category="trading"),
    ToolDef("fetchMyTrades", "fetchMyTrades", "Fetch user's filled trades.",
            [_a("params", flatten=True)], read_only=True, requires_credentials=True, category="trading"),

    # --- Account & Positions ---
    ToolDef("fetchBalance", "fetchBalance", "Get account balance.",
            [_a("address", "string")], read_only=True, requires_credentials=True, category="account"),
    ToolDef("fetchPositions", "fetchPositions", "Get open positions.",
            [_a("address", "string")], read_only=True, requires_credentials=True, category="account"),

    # --- Router / Cross-Venue ---
    ToolDef("compareMarketPrices", "compareMarketPrices", "Compare live prices across venues side-by-side.",
            [_a("params", flatten=True)], read_only=True, category="router"),
    ToolDef("fetchMarketMatches", "fetchMarketMatches", "Find the same or related market on other venues.",
            [_a("params", flatten=True)], read_only=True, category="router"),
    ToolDef("fetchEventMatches", "fetchEventMatches", "Find matching events across venues.",
            [_a("params", flatten=True)], read_only=True, category="router"),
    ToolDef("fetchRelatedMarkets", "fetchRelatedMarkets", "Fetch markets related to a given market.",
            [_a("params", "object", optional=False)], read_only=True, category="router"),
    ToolDef("fetchMatchedMarkets", "fetchMatchedMarkets", "Fetch all matched market pairs from the catalog.",
            [_a("params", flatten=True)], read_only=True, category="router"),
    ToolDef("fetchMatchedPrices", "fetchMatchedPrices", "Fetch prices for matched market pairs.",
            [_a("params", flatten=True)], read_only=True, category="router"),
    ToolDef("fetchHedges", "fetchHedges", "Find hedging opportunities across venues.",
            [_a("params", "object", optional=False)], read_only=True, category="router"),
    ToolDef("fetchArbitrage", "fetchArbitrage", "Find arbitrage opportunities across venues.",
            [_a("params", flatten=True)], read_only=True, category="router"),

    # --- Execution & Pricing ---
    ToolDef("getExecutionPrice", "getExecutionPrice",
            "Calculate VWAP execution price from order book.",
            [_a("orderBook", "object", optional=False),
             _a("side", "string", optional=False),
             _a("amount", "number", optional=False)],
            read_only=True, idempotent=True, category="data"),
    ToolDef("getExecutionPriceDetailed", "getExecutionPriceDetailed",
            "Detailed execution price including fill status.",
            [_a("orderBook", "object", optional=False),
             _a("side", "string", optional=False),
             _a("amount", "number", optional=False)],
            read_only=True, idempotent=True, category="data"),
]

# Index by Python method name
TOOLS_BY_NAME: dict[str, ToolDef] = {t.method: t for t in TOOLS}

# Category lists
READ_ONLY_TOOLS = [t for t in TOOLS if t.read_only and not t.destructive]
DESTRUCTIVE_TOOLS = [t for t in TOOLS if t.destructive]
CREDENTIAL_TOOLS = [t for t in TOOLS if t.requires_credentials]


def get_tool(method: str) -> Optional[ToolDef]:
    """Look up a tool definition by PMXT method name."""
    return TOOLS_BY_NAME.get(method)


def list_tools(category: Optional[str] = None, read_only: Optional[bool] = None) -> list[ToolDef]:
    """List tools, optionally filtered by category or read_only flag."""
    result = TOOLS
    if category:
        result = [t for t in result if t.category == category]
    if read_only is True:
        result = [t for t in result if t.read_only and not t.destructive]
    elif read_only is False:
        result = [t for t in result if not t.read_only or t.destructive]
    return result


def is_destructive(method: str) -> bool:
    """Return True if the method is destructive (requires user confirmation)."""
    tool = get_tool(method)
    return tool is not None and tool.destructive


def requires_credentials(method: str) -> bool:
    """Return True if the method requires exchange credentials."""
    tool = get_tool(method)
    return tool is not None and tool.requires_credentials
