"""
Result shaping for LLM-friendly compact outputs.

When verbose=False (default), strips fields that bloat context windows
without adding decision-relevant information. When verbose=True, returns
raw/near-raw output.

Design inspired by pmxt-mcp's src/shaper.ts, adapted for Python dicts.
"""

from __future__ import annotations

from typing import Any


def _truncate(s: Any, max_len: int) -> str:
    """Truncate a string to max_len with '...' suffix."""
    if not isinstance(s, str):
        return ""
    if len(s) <= max_len:
        return s
    return s[:max_len] + "..."


def compact_market(m: Any) -> dict:
    """Compact a market dict: id, title, outcomes price/label, volume, liquidity."""
    src = m if isinstance(m, dict) else {}
    outcomes = []
    for o in (src.get("outcomes") or []):
        outcomes.append({
            "label": o.get("label", ""),
            "price": o.get("price"),
        })

    result: dict = {
        "market_id": src.get("market_id"),
        "title": src.get("title", ""),
        "outcomes": outcomes,
    }

    if src.get("volume_24h"):
        result["volume_24h"] = src["volume_24h"]
    if src.get("liquidity"):
        result["liquidity"] = src["liquidity"]
    if src.get("status") and src.get("status") != "active":
        result["status"] = src["status"]
    if src.get("exchange"):
        result["exchange"] = src["exchange"]
    if src.get("slug"):
        result["slug"] = src["slug"]
    if src.get("yes_price") is not None:
        result["yes_price"] = src["yes_price"]
    if src.get("no_price") is not None:
        result["no_price"] = src["no_price"]

    return result


def compact_single_market(m: Any) -> dict:
    """Compact a single market with slightly more detail (outcome IDs, description)."""
    src = m if isinstance(m, dict) else {}
    outcomes = []
    for o in (src.get("outcomes") or []):
        outcomes.append({
            "outcome_id": o.get("outcome_id"),
            "label": o.get("label", ""),
            "price": o.get("price"),
        })

    result: dict = {
        "market_id": src.get("market_id"),
        "event_id": src.get("event_id"),
        "title": src.get("title", ""),
        "description": _truncate(src.get("description", ""), 200),
        "outcomes": outcomes,
    }

    if src.get("resolution_date"):
        result["resolution_date"] = src["resolution_date"]
    if src.get("volume_24h"):
        result["volume_24h"] = src["volume_24h"]
    if src.get("liquidity"):
        result["liquidity"] = src["liquidity"]
    if src.get("open_interest"):
        result["open_interest"] = src["open_interest"]
    if src.get("status"):
        result["status"] = src["status"]
    if src.get("tick_size"):
        result["tick_size"] = src["tick_size"]
    if src.get("exchange"):
        result["exchange"] = src["exchange"]

    return result


_NESTED_MARKETS_LIMIT = 5


def compact_event(e: Any) -> dict:
    """Compact an event dict: id, title, market count, top N compact markets."""
    src = e if isinstance(e, dict) else {}
    all_markets = src.get("top_markets") or src.get("markets") or []
    markets = [compact_market(m) for m in all_markets[: _NESTED_MARKETS_LIMIT]]

    result: dict = {
        "event_id": src.get("event_id"),
        "title": src.get("title", ""),
        "market_count": src.get("market_count", len(all_markets)),
        "markets": markets,
    }

    if src.get("exchange"):
        result["exchange"] = src["exchange"]
    if src.get("slug"):
        result["slug"] = src["slug"]
    if src.get("description"):
        result["description"] = _truncate(src["description"], 200)
    if src.get("url"):
        result["url"] = src["url"]

    return result


def compact_order_book(book: Any, max_levels: int = 10) -> dict:
    """Compact an order book dict to best bid/ask + limited depth."""
    src = book if isinstance(book, dict) else {}

    bids = (src.get("bids") or [])[:max_levels]
    asks = (src.get("asks") or [])[:max_levels]

    result: dict = {
        "best_bid": src.get("best_bid"),
        "best_ask": src.get("best_ask"),
        "spread": src.get("spread"),
        "spread_pct": src.get("spread_pct"),
        "mid_price": src.get("mid_price"),
        "bid_depth": src.get("bid_depth"),
        "ask_depth": src.get("ask_depth"),
        "bids": bids,
        "asks": asks,
        "bid_levels": len(bids),
        "ask_levels": len(asks),
    }

    if src.get("outcome_id"):
        result["outcome_id"] = src["outcome_id"]
    if src.get("exchange"):
        result["exchange"] = src["exchange"]

    return result


def compact_comparison(result: Any) -> dict:
    """Compact a market comparison result."""
    src = result if isinstance(result, dict) else {}

    quotes = []
    for q in (src.get("quotes") or []):
        quotes.append({
            "exchange": q.get("exchange"),
            "market_id": q.get("market_id"),
            "yes_price": q.get("yes_price"),
            "no_price": q.get("no_price"),
            "volume_24h": q.get("volume_24h"),
        })

    return {
        "title": src.get("title", ""),
        "exchange_count": src.get("exchange_count", len(quotes)),
        "yes_spread": src.get("yes_spread"),
        "no_spread": src.get("no_spread"),
        "quotes": quotes,
    }


def compact_arbitrage(opp: Any) -> dict:
    """Compact an arbitrage opportunity dict."""
    src = opp if isinstance(opp, dict) else {}
    return {
        "strategy": src.get("strategy"),
        "market_a": _truncate(src.get("market_a", ""), 100),
        "exchange_a": src.get("exchange_a"),
        "market_b": _truncate(src.get("market_b", ""), 100),
        "exchange_b": src.get("exchange_b"),
        "combined_price": src.get("combined_price"),
        "profit_margin": src.get("profit_margin"),
    }


# ---------------------------------------------------------------------------
# Main shaper dispatch
# ---------------------------------------------------------------------------

def shape_result(method: str, raw_data: Any, verbose: bool = False) -> dict:
    """
    Shape raw API output into a compact agent-friendly dict.

    Args:
        method: The underlying PMXT method name (e.g. 'fetchMarkets', 'compareMarketPrices')
        raw_data: The raw result from the PMXT SDK or API
        verbose: If True, return raw data mostly unmodified

    Returns:
        Shaped dict with compact representation
    """
    if verbose:
        return {"raw": raw_data} if isinstance(raw_data, (dict, list)) else {"raw": str(raw_data)}

    # Dispatch based on method name
    _m = method.lower().replace("_", "")

    if _m == "fetchmarket" and "matches" not in _m:
        # Singular market lookup
        return compact_single_market(raw_data) if isinstance(raw_data, dict) else {"raw": raw_data}

    if "markets" in _m:
        # List of markets
        if isinstance(raw_data, list):
            return {"markets": [compact_market(m) for m in raw_data]}
        if isinstance(raw_data, dict) and "data" in raw_data:
            inner = raw_data["data"]
            if isinstance(inner, list):
                return {"markets": [compact_market(m) for m in inner]}
        return {"markets": raw_data}

    if "events" in _m and "fetch" in _m:
        if isinstance(raw_data, list):
            return {"events": [compact_event(e) for e in raw_data]}
        return {"events": raw_data}

    if "orderbook" in _m:
        return compact_order_book(raw_data)

    if "compare" in _m or "match" in _m:
        if isinstance(raw_data, dict):
            return compact_comparison(raw_data)
        if isinstance(raw_data, list):
            return {"comparisons": [compact_comparison(c) for c in raw_data]}
        return {"data": raw_data}

    if "arbitrage" in _m or "hedge" in _m:
        if isinstance(raw_data, list):
            return {"opportunities": [compact_arbitrage(o) for o in raw_data]}
        if isinstance(raw_data, dict) and "data" in raw_data:
            inner = raw_data["data"]
            if isinstance(inner, list):
                return {"opportunities": [compact_arbitrage(o) for o in inner]}
        return {"data": raw_data}

    # Default: pass through
    if isinstance(raw_data, dict):
        return raw_data
    if isinstance(raw_data, list):
        return {"items": raw_data, "count": len(raw_data)}
    return {"value": raw_data}
