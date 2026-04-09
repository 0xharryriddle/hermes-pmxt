"""
Core prediction market tools for Hermes Agent.

Each function returns a dict with:
  {"success": bool, "data": ..., "error": str|None}

These are designed to be called from:
  1. Direct Python imports
  2. execute_code blocks in Hermes sessions
  3. CLI scripts
"""

import re
import time
from datetime import datetime
from typing import Optional

from hermes_pmxt.exchanges import get_exchange, ensure_server


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_market_cache: dict[tuple[str, str], object] = {}


def _ok(data, **extra) -> dict:
    """Build a success response."""
    return {"success": True, "data": data, **extra}


def _err(error: str) -> dict:
    """Build an error response."""
    return {"success": False, "error": error}


def _ensure() -> Optional[dict]:
    """Ensure sidecar is running. Returns error dict or None."""
    ok, err = ensure_server()
    if not ok:
        return _err(err)
    return None


def _market_dict(m, exchange_name: str = "") -> dict:
    """Convert UnifiedMarket dataclass to serializable dict."""
    outcomes = []
    for o in (m.outcomes or []):
        outcomes.append({
            "outcome_id": o.outcome_id,
            "label": o.label,
            "price": o.price,
            "price_change_24h": o.price_change_24h,
        })

    d = {
        "market_id": m.market_id,
        "title": m.title,
        "description": m.description,
        "outcomes": outcomes,
        "volume_24h": m.volume_24h or 0,
        "liquidity": m.liquidity or 0,
        "url": m.url or "",
        "status": m.status,
        "slug": m.slug,
        "category": m.category,
    }

    # Convenience: yes/no shorthand
    if m.yes:
        d["yes_price"] = m.yes.price
        d["yes_pct"] = f"{m.yes.price * 100:.1f}%"
    if m.no:
        d["no_price"] = m.no.price
        d["no_pct"] = f"{m.no.price * 100:.1f}%"

    if exchange_name:
        d["exchange"] = exchange_name

    return d


def _candle_dict(c) -> dict:
    """Convert PriceCandle to dict."""
    return {
        "timestamp": c.timestamp,
        "datetime": datetime.fromtimestamp(c.timestamp / 1000).isoformat(),
        "open": c.open,
        "high": c.high,
        "low": c.low,
        "close": c.close,
        "volume": c.volume,
    }


def _trade_dict(t) -> dict:
    """Convert Trade to dict."""
    return {
        "id": t.id,
        "timestamp": t.timestamp,
        "datetime": datetime.fromtimestamp(t.timestamp / 1000).isoformat(),
        "price": t.price,
        "amount": t.amount,
        "side": t.side,
    }


def _remember_market(exchange_name: str, market) -> None:
    """Cache fetched markets so follow-up order calls can resolve outcome IDs."""
    if getattr(market, "market_id", None):
        _market_cache[(exchange_name, market.market_id)] = market


def _get_cached_market(exchange_name: str, market_id: str):
    """Return a previously fetched market, if available."""
    return _market_cache.get((exchange_name, market_id))


def _looks_like_outcome_id(value: str) -> bool:
    """Outcome IDs are long numeric strings on pmxt-backed exchanges."""
    return bool(re.fullmatch(r"\d{20,}", value.strip()))


def _resolve_outcome_id(market, outcome: str) -> Optional[str]:
    """Resolve a user-friendly outcome reference into an exchange outcome ID."""
    normalized = outcome.strip().lower()

    if _looks_like_outcome_id(outcome):
        return outcome.strip()

    if normalized == "yes" and getattr(market, "yes", None):
        return market.yes.outcome_id
    if normalized == "no" and getattr(market, "no", None):
        return market.no.outcome_id

    for candidate in (getattr(market, "outcomes", None) or []):
        if candidate.label.strip().lower() == normalized:
            return candidate.outcome_id

    return None


# ---------------------------------------------------------------------------
# Public Tools
# ---------------------------------------------------------------------------

def pmxt_search(
    query: str,
    exchange: Optional[str] = None,
    limit: int = 20,
) -> dict:
    """
    Search prediction markets by keyword.

    Args:
        query: Broad keyword (e.g. "election", "bitcoin", "trump")
        exchange: Specific exchange name, or None to search all available
        limit: Max results per exchange

    Returns:
        {"success": True, "data": [market_dicts], "count": N}
    """
    err = _ensure()
    if err:
        return err

    targets = [exchange] if exchange else ["polymarket", "kalshi", "limitless"]

    all_markets = []
    errors = []

    for ex_name in targets:
        ex, init_err = get_exchange(ex_name)
        if init_err:
            errors.append(init_err)
            continue
        try:
            results = ex.fetch_markets(query=query, limit=limit)
            for m in results:
                _remember_market(ex_name, m)
                all_markets.append(_market_dict(m, ex_name))
        except Exception as e:
            errors.append(f"{ex_name}: {e}")

    resp = _ok(all_markets, count=len(all_markets), exchanges_searched=targets)
    if errors:
        resp["partial_errors"] = errors
    return resp


def pmxt_quote(identifier: str, exchange: str) -> dict:
    """
    Get current YES/NO probabilities for a market.

    Accepts a keyword/title to search for (recommended) or a market slug.
    Best practice: use a distinctive phrase from the market title.

    Args:
        identifier: Search keyword or distinctive market title phrase
                    e.g. "bitcoin 200000" or "trump nominate fed"
        exchange: Exchange name

    Returns:
        {"success": True, "data": {"yes": 0.34, "no": 0.66, "yes_pct": "34.0%", ...}}
    """
    err = _ensure()
    if err:
        return err

    ex, init_err = get_exchange(exchange)
    if init_err:
        return _err(init_err)

    try:
        # Search for matching markets
        results = ex.fetch_markets(query=identifier, limit=5)
        if not results:
            return _err(f"No markets found for: {identifier}")

        # Pick the best match — first result is usually most relevant
        m = results[0]
        _remember_market(exchange, m)

        yes_price = m.yes.price if m.yes else None
        no_price = m.no.price if m.no else None

        # Derive missing
        if yes_price is not None and no_price is None:
            no_price = round(1.0 - yes_price, 4)
        elif no_price is not None and yes_price is None:
            yes_price = round(1.0 - no_price, 4)

        return _ok({
            "market_id": m.market_id,
            "title": m.title,
            "slug": m.slug,
            "exchange": exchange,
            "yes": yes_price,
            "no": no_price,
            "yes_pct": f"{yes_price * 100:.1f}%" if yes_price is not None else None,
            "no_pct": f"{no_price * 100:.1f}%" if no_price is not None else None,
            "volume_24h": m.volume_24h or 0,
            "url": m.url or "",
            "status": m.status,
            # Include outcome_ids for follow-up calls
            "outcomes": [
                {"outcome_id": o.outcome_id, "label": o.label, "price": o.price}
                for o in (m.outcomes or [])
            ],
        })
    except Exception as e:
        return _err(f"{exchange}: {e}")


def pmxt_order_book(outcome_id: str, exchange: str) -> dict:
    """
    Get the current order book for a market outcome.

    Args:
        outcome_id: Outcome ID (the Yes/No token ID, NOT market_id)
        exchange: Exchange name

    Returns:
        {"success": True, "data": {"bids": [...], "asks": [...], "spread": 0.001}}
    """
    err = _ensure()
    if err:
        return err

    ex, init_err = get_exchange(exchange)
    if init_err:
        return _err(init_err)

    try:
        book = ex.fetch_order_book(outcome_id)

        bids = [{"price": b.price, "size": b.size} for b in book.bids]
        asks = [{"price": a.price, "size": a.size} for a in book.asks]

        spread = None
        if bids and asks:
            spread = round(asks[0]["price"] - bids[0]["price"], 6)

        return _ok({
            "outcome_id": outcome_id,
            "exchange": exchange,
            "bids": bids,
            "asks": asks,
            "bid_levels": len(bids),
            "ask_levels": len(asks),
            "spread": spread,
            "spread_pct": f"{spread * 100:.2f}%" if spread is not None else None,
            "best_bid": bids[0]["price"] if bids else None,
            "best_ask": asks[0]["price"] if asks else None,
            "timestamp": book.timestamp,
        })
    except Exception as e:
        return _err(f"{exchange}: {e}")


def pmxt_ohlcv(
    outcome_id: str,
    exchange: str,
    resolution: str = "1d",
    limit: int = 30,
) -> dict:
    """
    Get price history candles.

    Args:
        outcome_id: Outcome ID
        exchange: Exchange name
        resolution: "1m", "5m", "1h", "1d"
        limit: Number of candles

    Returns:
        {"success": True, "data": [candle_dicts]}
    """
    err = _ensure()
    if err:
        return err

    ex, init_err = get_exchange(exchange)
    if init_err:
        return _err(init_err)

    try:
        candles = ex.fetch_ohlcv(outcome_id, resolution=resolution, limit=limit)
        return _ok(
            [_candle_dict(c) for c in candles],
            outcome_id=outcome_id,
            exchange=exchange,
            resolution=resolution,
            count=len(candles),
        )
    except Exception as e:
        return _err(f"{exchange}: {e}")


def pmxt_trades(
    outcome_id: str,
    exchange: str,
    limit: int = 20,
) -> dict:
    """
    Get recent trades for an outcome.

    Args:
        outcome_id: Outcome ID
        exchange: Exchange name
        limit: Max trades

    Returns:
        {"success": True, "data": [trade_dicts]}
    """
    err = _ensure()
    if err:
        return err

    ex, init_err = get_exchange(exchange)
    if init_err:
        return _err(init_err)

    try:
        trades = ex.fetch_trades(outcome_id, limit=limit)
        return _ok(
            [_trade_dict(t) for t in trades],
            outcome_id=outcome_id,
            exchange=exchange,
            count=len(trades),
        )
    except Exception as e:
        return _err(f"{exchange}: {e}")


def pmxt_events(
    query: str,
    exchange: str = "polymarket",
    limit: int = 10,
) -> dict:
    """
    Search events (groups of related markets).

    Args:
        query: Search keyword
        exchange: Exchange name (Polymarket has events)
        limit: Max events

    Returns:
        {"success": True, "data": [event_dicts]}
    """
    err = _ensure()
    if err:
        return err

    ex, init_err = get_exchange(exchange)
    if init_err:
        return _err(init_err)

    try:
        events = ex.fetch_events(query=query, limit=limit)
        result = []
        for e in events:
            markets_summary = []
            for m in (e.markets or [])[:5]:
                yes_pct = f"{m.yes.price * 100:.1f}%" if m.yes else "N/A"
                markets_summary.append({
                    "market_id": m.market_id,
                    "title": m.title,
                    "yes_pct": yes_pct,
                })

            result.append({
                "title": e.title,
                "market_count": len(e.markets or []),
                "top_markets": markets_summary,
            })

        return _ok(result, exchange=exchange, count=len(result))
    except Exception as e:
        return _err(f"{exchange}: {e}")


def pmxt_balance(exchange: str) -> dict:
    """
    Get account balance. Requires exchange credentials.

    Args:
        exchange: Exchange name

    Returns:
        {"success": True, "data": [{"currency": "USD", "available": 100.0, ...}]}
    """
    err = _ensure()
    if err:
        return err

    ex, init_err = get_exchange(exchange)
    if init_err:
        return _err(init_err)

    try:
        balances = ex.fetch_balance()
        return _ok(
            [
                {
                    "currency": b.currency,
                    "available": b.available,
                    "total": b.total,
                    "locked": b.locked,
                }
                for b in balances
            ],
            exchange=exchange,
        )
    except Exception as e:
        return _err(f"{exchange}: {e}. Ensure credentials are configured.")


def pmxt_positions(exchange: str) -> dict:
    """
    Get open positions. Requires exchange credentials.

    Args:
        exchange: Exchange name

    Returns:
        {"success": True, "data": [position_dicts]}
    """
    err = _ensure()
    if err:
        return err

    ex, init_err = get_exchange(exchange)
    if init_err:
        return _err(init_err)

    try:
        positions = ex.fetch_positions()
        return _ok(
            [
                {
                    "market_id": p.market_id,
                    "outcome_id": p.outcome_id,
                    "outcome_label": p.outcome_label,
                    "size": p.size,
                    "entry_price": p.entry_price,
                    "current_price": p.current_price,
                    "unrealized_pnl": p.unrealized_pnl,
                    "realized_pnl": p.realized_pnl,
                }
                for p in positions
            ],
            exchange=exchange,
        )
    except Exception as e:
        return _err(f"{exchange}: {e}. Ensure credentials are configured.")


def pmxt_order(
    market_id: str,
    outcome: str,
    amount: float,
    side: str,
    exchange: str,
    price: Optional[float] = None,
) -> dict:
    """
    Place an order. Requires exchange credentials.

    IMPORTANT: Never call without explicit user confirmation including
    market, outcome, amount, and exchange.

    Args:
        market_id: Market ID
        outcome: "yes" or "no" (outcome label)
        amount: Number of shares
        side: "buy" or "sell"
        exchange: Exchange name
        price: Limit price (0.0-1.0). None for market order.

    Returns:
        {"success": True, "data": {order_details}}
    """
    err = _ensure()
    if err:
        return err

    ex, init_err = get_exchange(exchange)
    if init_err:
        return _err(init_err)

    try:
        cached_market = _get_cached_market(exchange, market_id)
        outcome_id = None
        if cached_market is not None:
            outcome_id = _resolve_outcome_id(cached_market, outcome)
        elif _looks_like_outcome_id(outcome):
            outcome_id = outcome.strip()

        if outcome_id is None:
            return _err(
                "Could not resolve outcome to an outcome_id. "
                "Run pmxt_search() or pmxt_quote() for this market first, then pass "
                "'yes'/'no' or an exact outcome_id."
            )

        order_params = {
            "market_id": market_id,
            "outcome_id": outcome_id,
            "side": side,
            "type": "limit" if price is not None else "market",
            "amount": amount,
        }
        if price is not None:
            order_params["price"] = price

        order = ex.create_order(**order_params)

        return _ok({
            "order_id": order.id,
            "market_id": order.market_id,
            "outcome_id": order.outcome_id,
            "side": order.side,
            "type": order.type,
            "amount": order.amount,
            "price": order.price,
            "status": order.status,
            "filled": order.filled,
            "remaining": order.remaining,
            "timestamp": order.timestamp,
        }, exchange=exchange)
    except Exception as e:
        return _err(f"{exchange}: {e}. Ensure credentials are configured.")


def pmxt_arbitrage_scan(
    query: str,
    exchanges: Optional[list[str]] = None,
    threshold: float = 0.95,
) -> dict:
    """
    Scan for cross-exchange arbitrage opportunities.

    Finds the same topic on multiple exchanges and checks if YES on one + NO
    on another sums below 1.0 (risk-free profit).

    Args:
        query: Search keyword
        exchanges: Exchanges to compare (default: polymarket + kalshi)
        threshold: Alert if combined price < threshold

    Returns:
        {"success": True, "data": [opportunity_dicts], "count": N}
    """
    exchanges = exchanges or ["polymarket", "kalshi"]

    # Search each exchange
    results = {}
    for ex_name in exchanges:
        r = pmxt_search(query, exchange=ex_name, limit=10)
        if r["success"] and r["data"]:
            results[ex_name] = r["data"]

    if len(results) < 2:
        return _err("Need results from at least 2 exchanges for arbitrage scan")

    opportunities = []
    ex_names = list(results.keys())

    for i, ex_a in enumerate(ex_names):
        for ex_b in ex_names[i + 1:]:
            for m_a in results[ex_a]:
                for m_b in results[ex_b]:
                    # Simple title overlap matching
                    words_a = set(m_a["title"].lower().split())
                    words_b = set(m_b["title"].lower().split())
                    overlap = len(words_a & words_b) / max(len(words_a | words_b), 1)

                    if overlap < 0.4:
                        continue

                    # Check YES(a) + NO(b) < threshold
                    yes_a = m_a.get("yes_price")
                    no_b = m_b.get("no_price")

                    if yes_a is not None and no_b is not None:
                        combined = round(yes_a + no_b, 4)
                        if combined < threshold:
                            opportunities.append({
                                "strategy": "buy_yes_a_sell_no_b",
                                "market_a": m_a["title"],
                                "exchange_a": ex_a,
                                "yes_price_a": yes_a,
                                "yes_pct_a": f"{yes_a * 100:.1f}%",
                                "market_b": m_b["title"],
                                "exchange_b": ex_b,
                                "no_price_b": no_b,
                                "no_pct_b": f"{no_b * 100:.1f}%",
                                "combined_price": combined,
                                "profit_margin": f"{(1 - combined) * 100:.1f}%",
                            })

                    # Also check NO(a) + YES(b)
                    no_a = m_a.get("no_price")
                    yes_b = m_b.get("yes_price")

                    if no_a is not None and yes_b is not None:
                        combined = round(no_a + yes_b, 4)
                        if combined < threshold:
                            opportunities.append({
                                "strategy": "buy_no_a_sell_yes_b",
                                "market_a": m_a["title"],
                                "exchange_a": ex_a,
                                "no_price_a": no_a,
                                "no_pct_a": f"{no_a * 100:.1f}%",
                                "market_b": m_b["title"],
                                "exchange_b": ex_b,
                                "yes_price_b": yes_b,
                                "yes_pct_b": f"{yes_b * 100:.1f}%",
                                "combined_price": combined,
                                "profit_margin": f"{(1 - combined) * 100:.1f}%",
                            })

    return _ok(
        opportunities,
        count=len(opportunities),
        exchanges_scanned=exchanges,
        threshold=threshold,
    )


# ---------------------------------------------------------------------------
# Server Management
# ---------------------------------------------------------------------------

def pmxt_server_health() -> dict:
    """Check if pmxt sidecar server is healthy."""
    from hermes_pmxt.exchanges import server_status
    return _ok(server_status())


def pmxt_server_start() -> dict:
    """Start the pmxt sidecar server."""
    import pmxt
    try:
        pmxt.server.start()
        time.sleep(1.5)
        return _ok({"started": True, "health": pmxt.server.health()})
    except Exception as e:
        return _err(f"Failed to start server: {e}")


def pmxt_server_stop() -> dict:
    """Stop the pmxt sidecar server."""
    import pmxt
    try:
        pmxt.server.stop()
        return _ok({"stopped": True})
    except Exception as e:
        return _err(f"Failed to stop server: {e}")
