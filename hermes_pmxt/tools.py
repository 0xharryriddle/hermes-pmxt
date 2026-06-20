"""
Core prediction market tools for Hermes Agent.

Each function returns a dict with:
  {"success": bool, "data": ..., "error": str|None}

These are designed to be called from:
  1. Direct Python imports
  2. execute_code blocks in Hermes sessions
  3. CLI scripts
"""

from __future__ import annotations

import inspect
import statistics
import time
from datetime import datetime
from typing import Optional

from hermes_pmxt.config import get_base_url, get_mode, runtime_status as _runtime_status_dict
from hermes_pmxt.exchanges import (
    EXCHANGES,
    TRADING_EXCHANGES,
    available_exchange_names,
    ensure_server,
    get_exchange,
    is_pmxt_available,
    normalize_exchange_name,
    server_status,
)
from hermes_pmxt.registry import (
    EXCHANGE_ALIASES,
    KNOWN_EXCHANGES,
    get_tool,
    is_destructive as _is_destructive,
)
from hermes_pmxt.shaper import shape_result


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


def _safe_signature_params(func) -> set[str]:
    """Return inspectable parameter names for a callable, or an empty set."""
    try:
        return set(inspect.signature(func).parameters)
    except (TypeError, ValueError):
        return set()


def _call_method(func, /, *args, **kwargs):
    """Call a method while dropping unsupported keyword arguments when possible."""
    if not kwargs:
        return func(*args)

    params = _safe_signature_params(func)
    if not params:
        return func(*args, **kwargs)

    filtered_kwargs = {key: value for key, value in kwargs.items() if key in params}
    return func(*args, **filtered_kwargs)


def _search_call_kwargs(
    fetch_markets,
    *,
    query: str,
    limit: int,
    sort: Optional[str],
    search_in: Optional[str],
    slug: Optional[str],
) -> dict:
    """Build the most compatible fetch_markets kwargs for the installed SDK."""
    kwargs = {"query": query, "limit": limit}
    params = _safe_signature_params(fetch_markets)

    if sort is not None and (not params or "sort" in params):
        kwargs["sort"] = sort

    if search_in is not None:
        if not params or "searchIn" in params:
            kwargs["searchIn"] = search_in
        elif "search_in" in params:
            kwargs["search_in"] = search_in

    if slug is not None and (not params or "slug" in params):
        kwargs["slug"] = slug

    return kwargs


def _event_call_kwargs(
    fetch_events,
    *,
    query: str,
    limit: int,
    sort: Optional[str],
    search_in: Optional[str],
    slug: Optional[str],
) -> dict:
    """Build the most compatible fetch_events kwargs for the installed SDK."""
    kwargs = {"query": query, "limit": limit}
    params = _safe_signature_params(fetch_events)

    if sort is not None and (not params or "sort" in params):
        kwargs["sort"] = sort

    if search_in is not None:
        if not params or "searchIn" in params:
            kwargs["searchIn"] = search_in
        elif "search_in" in params:
            kwargs["search_in"] = search_in

    if slug is not None and (not params or "slug" in params):
        kwargs["slug"] = slug

    return kwargs


def _market_dict(m, exchange_name: str = "") -> dict:
    """Convert UnifiedMarket dataclass to serializable dict."""
    outcomes = []
    for outcome in (getattr(m, "outcomes", None) or []):
        outcomes.append({
            "outcome_id": getattr(outcome, "outcome_id", None),
            "label": getattr(outcome, "label", ""),
            "price": getattr(outcome, "price", None),
            "price_change_24h": getattr(outcome, "price_change_24h", None),
        })

    data = {
        "market_id": getattr(m, "market_id", None),
        "title": getattr(m, "title", ""),
        "description": getattr(m, "description", ""),
        "outcomes": outcomes,
        "volume_24h": getattr(m, "volume_24h", 0) or 0,
        "liquidity": getattr(m, "liquidity", 0) or 0,
        "url": getattr(m, "url", "") or "",
        "status": getattr(m, "status", None),
        "slug": getattr(m, "slug", None),
        "category": getattr(m, "category", None),
        "event_id": getattr(m, "event_id", None),
        "tags": getattr(m, "tags", None),
        "resolved": getattr(m, "resolved", None),
    }

    yes = getattr(m, "yes", None)
    no = getattr(m, "no", None)
    if yes:
        data["yes_price"] = yes.price
        data["yes_pct"] = f"{yes.price * 100:.1f}%"
    if no:
        data["no_price"] = no.price
        data["no_pct"] = f"{no.price * 100:.1f}%"

    if exchange_name:
        data["exchange"] = exchange_name

    return data


def _candle_dict(c) -> dict:
    """Convert PriceCandle to dict."""
    timestamp = getattr(c, "timestamp", None)
    return {
        "timestamp": timestamp,
        "datetime": datetime.fromtimestamp(timestamp / 1000).isoformat() if timestamp else None,
        "open": getattr(c, "open", None),
        "high": getattr(c, "high", None),
        "low": getattr(c, "low", None),
        "close": getattr(c, "close", None),
        "volume": getattr(c, "volume", None),
    }


def _trade_dict(t) -> dict:
    """Convert Trade to dict."""
    timestamp = getattr(t, "timestamp", None)
    return {
        "id": getattr(t, "id", None),
        "timestamp": timestamp,
        "datetime": datetime.fromtimestamp(timestamp / 1000).isoformat() if timestamp else None,
        "price": getattr(t, "price", None),
        "amount": getattr(t, "amount", None),
        "side": getattr(t, "side", None),
    }


def _remember_market(exchange_name: str, market) -> None:
    """Cache fetched markets so follow-up order calls can resolve outcome IDs."""
    market_id = getattr(market, "market_id", None)
    if market_id:
        _market_cache[(exchange_name, market_id)] = market


def _get_cached_market(exchange_name: str, market_id: str):
    """Return a previously fetched market, if available."""
    return _market_cache.get((exchange_name, market_id))


def _is_alias_outcome(value: str) -> bool:
    """Return True for friendly aliases that still need market-based resolution."""
    return value.strip().lower() in {"yes", "no"}


def _resolve_outcome_id(market, outcome: str) -> Optional[str]:
    """Resolve a user-friendly outcome reference into an exchange outcome ID."""
    normalized = outcome.strip().lower()

    if not _is_alias_outcome(outcome):
        for candidate in (getattr(market, "outcomes", None) or []):
            if (candidate.label or "").strip().lower() == normalized:
                return candidate.outcome_id
        return outcome.strip()

    if normalized == "yes" and getattr(market, "yes", None):
        return market.yes.outcome_id
    if normalized == "no" and getattr(market, "no", None):
        return market.no.outcome_id

    for candidate in (getattr(market, "outcomes", None) or []):
        if (candidate.label or "").strip().lower() == normalized:
            return candidate.outcome_id

    return None


def _extract_yes_no(market_dict: dict) -> tuple[Optional[float], Optional[float]]:
    """Return YES/NO prices from a serialized market dict."""
    yes_price = market_dict.get("yes_price")
    no_price = market_dict.get("no_price")

    if yes_price is not None or no_price is not None:
        return yes_price, no_price

    for outcome in market_dict.get("outcomes", []):
        label = (outcome.get("label") or "").strip().lower()
        if label == "yes":
            yes_price = outcome.get("price")
        elif label == "no":
            no_price = outcome.get("price")

    return yes_price, no_price


def _title_overlap(title_a: str, title_b: str) -> float:
    """Compute a simple token overlap score between titles."""
    words_a = set(title_a.lower().split())
    words_b = set(title_b.lower().split())
    return len(words_a & words_b) / max(len(words_a | words_b), 1)


def _default_exchange_targets() -> list[str]:
    """Return the supported exchange list without assuming the local pmxt build."""
    discovered = available_exchange_names()
    return discovered or list(EXCHANGES)


# ---------------------------------------------------------------------------
# Public Tools
# ---------------------------------------------------------------------------

def pmxt_search(
    query: str,
    exchange: Optional[str] = None,
    limit: int = 20,
    sort: Optional[str] = None,
    search_in: Optional[str] = None,
    slug: Optional[str] = None,
) -> dict:
    """
    Search prediction markets by keyword.

    Args:
        query: Broad keyword (e.g. "election", "bitcoin", "trump")
        exchange: Specific exchange name, or None to search all available
        limit: Max results per exchange
        sort: Optional result sort, if the installed pmxt build supports it
        search_in: Optional search scope ("title", "description", "both")
        slug: Optional direct market slug lookup

    Returns:
        {"success": True, "data": [market_dicts], "count": N}
    """
    err = _ensure()
    if err:
        return err

    targets = [normalize_exchange_name(exchange)] if exchange else _default_exchange_targets()

    all_markets = []
    errors = []

    for ex_name in targets:
        ex, init_err = get_exchange(ex_name)
        if init_err:
            errors.append(init_err)
            continue
        try:
            results = _call_method(
                ex.fetch_markets,
                **_search_call_kwargs(
                    ex.fetch_markets,
                    query=query,
                    limit=limit,
                    sort=sort,
                    search_in=search_in,
                    slug=slug,
                ),
            )
            for market in results:
                _remember_market(ex_name, market)
                all_markets.append(_market_dict(market, ex_name))
        except Exception as e:
            errors.append(f"{ex_name}: {e}")

    if not all_markets and errors:
        return _err("; ".join(errors))

    resp = _ok(all_markets, count=len(all_markets), exchanges_searched=targets)
    if errors:
        resp["partial_errors"] = errors
    return resp


def pmxt_quote(identifier: str, exchange: str) -> dict:
    """
    Get current YES/NO probabilities for a market.

    Accepts a keyword/title to search for (recommended) or a market slug.
    Best practice: use a distinctive phrase from the market title.
    """
    err = _ensure()
    if err:
        return err

    exchange_name = normalize_exchange_name(exchange)
    ex, init_err = get_exchange(exchange_name)
    if init_err:
        return _err(init_err)

    try:
        results = ex.fetch_markets(query=identifier, limit=5)
        if not results:
            return _err(f"No markets found for: {identifier}")

        market = results[0]
        _remember_market(exchange_name, market)

        yes_price = market.yes.price if getattr(market, "yes", None) else None
        no_price = market.no.price if getattr(market, "no", None) else None

        if yes_price is not None and no_price is None:
            no_price = round(1.0 - yes_price, 4)
        elif no_price is not None and yes_price is None:
            yes_price = round(1.0 - no_price, 4)

        return _ok({
            "market_id": market.market_id,
            "title": market.title,
            "slug": market.slug,
            "exchange": exchange_name,
            "yes": yes_price,
            "no": no_price,
            "yes_pct": f"{yes_price * 100:.1f}%" if yes_price is not None else None,
            "no_pct": f"{no_price * 100:.1f}%" if no_price is not None else None,
            "volume_24h": getattr(market, "volume_24h", 0) or 0,
            "liquidity": getattr(market, "liquidity", 0) or 0,
            "url": getattr(market, "url", "") or "",
            "status": getattr(market, "status", None),
            "outcomes": [
                {
                    "outcome_id": getattr(outcome, "outcome_id", None),
                    "label": getattr(outcome, "label", ""),
                    "price": getattr(outcome, "price", None),
                }
                for outcome in (getattr(market, "outcomes", None) or [])
            ],
        })
    except Exception as e:
        return _err(f"{exchange_name}: {e}")


def pmxt_order_book(outcome_id: str, exchange: str, limit: int = 20) -> dict:
    """
    Get the current order book for a market outcome.

    Args:
        outcome_id: Outcome ID (the Yes/No token ID, NOT market_id)
        exchange: Exchange name
        limit: Max depth levels per side
    """
    err = _ensure()
    if err:
        return err

    exchange_name = normalize_exchange_name(exchange)
    ex, init_err = get_exchange(exchange_name)
    if init_err:
        return _err(init_err)

    try:
        book = ex.fetch_order_book(outcome_id)

        bids = [{"price": level.price, "size": level.size} for level in book.bids[:limit]]
        asks = [{"price": level.price, "size": level.size} for level in book.asks[:limit]]

        spread = None
        mid_price = None
        if bids and asks:
            spread = round(asks[0]["price"] - bids[0]["price"], 6)
            mid_price = round((asks[0]["price"] + bids[0]["price"]) / 2, 6)

        return _ok({
            "outcome_id": outcome_id,
            "exchange": exchange_name,
            "bids": bids,
            "asks": asks,
            "bid_levels": len(bids),
            "ask_levels": len(asks),
            "spread": spread,
            "spread_pct": f"{spread * 100:.2f}%" if spread is not None else None,
            "best_bid": bids[0]["price"] if bids else None,
            "best_ask": asks[0]["price"] if asks else None,
            "mid_price": mid_price,
            "bid_depth": round(sum(level["size"] for level in bids), 4),
            "ask_depth": round(sum(level["size"] for level in asks), 4),
            "timestamp": getattr(book, "timestamp", None),
        })
    except Exception as e:
        return _err(f"{exchange_name}: {e}")


def pmxt_ohlcv(
    outcome_id: str,
    exchange: str,
    resolution: str = "1d",
    limit: int = 30,
) -> dict:
    """
    Get price history candles.

    Adds basic analytics (change, SMA, RSI) when enough candles are available.
    """
    err = _ensure()
    if err:
        return err

    exchange_name = normalize_exchange_name(exchange)
    ex, init_err = get_exchange(exchange_name)
    if init_err:
        return _err(init_err)

    try:
        candles = ex.fetch_ohlcv(outcome_id, resolution=resolution, limit=limit)
        serialized = [_candle_dict(candle) for candle in candles]
        analysis = {}

        closes = [candle["close"] for candle in serialized if candle["close"] is not None]
        if len(closes) >= 2:
            analysis = {
                "current_price": closes[-1],
                "high": max(closes),
                "low": min(closes),
                "price_change": round(closes[-1] - closes[0], 4),
                "price_change_pct": (
                    f"{((closes[-1] / closes[0]) - 1) * 100:.1f}%"
                    if closes[0]
                    else None
                ),
            }
            if len(closes) >= 7:
                analysis["sma_7"] = round(statistics.mean(closes[-7:]), 4)
            if len(closes) >= 14:
                analysis["sma_14"] = round(statistics.mean(closes[-14:]), 4)
                gains = []
                losses = []
                for index in range(1, 15):
                    change = closes[-index] - closes[-index - 1]
                    if change > 0:
                        gains.append(change)
                    else:
                        losses.append(abs(change))
                avg_gain = statistics.mean(gains) if gains else 0
                avg_loss = statistics.mean(losses) if losses else 0.0001
                rs = avg_gain / avg_loss
                analysis["rsi_14"] = round(100 - (100 / (1 + rs)), 1)

        return _ok(
            serialized,
            outcome_id=outcome_id,
            exchange=exchange_name,
            resolution=resolution,
            count=len(serialized),
            analysis=analysis,
        )
    except Exception as e:
        return _err(f"{exchange_name}: {e}")


def pmxt_trades(
    outcome_id: str,
    exchange: str,
    limit: int = 20,
) -> dict:
    """
    Get recent trades for an outcome.

    Includes aggregate trade stats when data is available.
    """
    err = _ensure()
    if err:
        return err

    exchange_name = normalize_exchange_name(exchange)
    ex, init_err = get_exchange(exchange_name)
    if init_err:
        return _err(init_err)

    try:
        trades = ex.fetch_trades(outcome_id, limit=limit)
        serialized = [_trade_dict(trade) for trade in trades]
        stats = {}

        prices = [trade["price"] for trade in serialized if trade["price"] is not None]
        amounts = [trade["amount"] for trade in serialized if trade["amount"] is not None]
        if prices:
            stats["avg_price"] = round(statistics.mean(prices), 4)
            stats["min_price"] = min(prices)
            stats["max_price"] = max(prices)
            stats["last_price"] = prices[-1]
        if amounts:
            stats["total_volume"] = round(sum(amounts), 4)
            stats["avg_trade_size"] = round(statistics.mean(amounts), 4)

        return _ok(
            serialized,
            outcome_id=outcome_id,
            exchange=exchange_name,
            count=len(serialized),
            stats=stats,
        )
    except Exception as e:
        return _err(f"{exchange_name}: {e}")


def pmxt_events(
    query: str,
    exchange: Optional[str] = None,
    limit: int = 10,
    sort: Optional[str] = None,
    search_in: Optional[str] = None,
    slug: Optional[str] = None,
) -> dict:
    """
    Search events (groups of related markets).

    Returns partial errors when some exchanges do not implement event discovery.
    """
    err = _ensure()
    if err:
        return err

    targets = [normalize_exchange_name(exchange)] if exchange else _default_exchange_targets()

    all_events = []
    errors = []

    for ex_name in targets:
        ex, init_err = get_exchange(ex_name)
        if init_err:
            errors.append(init_err)
            continue
        if not hasattr(ex, "fetch_events"):
            errors.append(f"{ex_name}: fetch_events not available")
            continue

        try:
            events = _call_method(
                ex.fetch_events,
                **_event_call_kwargs(
                    ex.fetch_events,
                    query=query,
                    limit=limit,
                    sort=sort,
                    search_in=search_in,
                    slug=slug,
                ),
            )
            for event in events:
                markets_summary = []
                for market in (getattr(event, "markets", None) or [])[:5]:
                    _remember_market(ex_name, market)
                    yes = getattr(market, "yes", None)
                    markets_summary.append({
                        "market_id": getattr(market, "market_id", None),
                        "title": getattr(market, "title", ""),
                        "yes_pct": f"{yes.price * 100:.1f}%" if yes else None,
                    })

                all_events.append({
                    "event_id": getattr(event, "event_id", None),
                    "title": getattr(event, "title", ""),
                    "description": getattr(event, "description", ""),
                    "slug": getattr(event, "slug", None),
                    "exchange": ex_name,
                    "market_count": len(getattr(event, "markets", None) or []),
                    "top_markets": markets_summary,
                    "url": getattr(event, "url", ""),
                })
        except Exception as e:
            errors.append(f"{ex_name}: {e}")

    if not all_events and errors:
        return _err("; ".join(errors))

    resp = _ok(all_events, count=len(all_events), exchanges_searched=targets)
    if errors:
        resp["partial_errors"] = errors
    return resp


def pmxt_balance(exchange: str) -> dict:
    """Get account balance. Requires exchange credentials."""
    err = _ensure()
    if err:
        return err

    exchange_name = normalize_exchange_name(exchange)
    ex, init_err = get_exchange(exchange_name)
    if init_err:
        return _err(init_err)

    try:
        balances = ex.fetch_balance()
        return _ok(
            [
                {
                    "currency": getattr(balance, "currency", None),
                    "available": getattr(balance, "available", None),
                    "total": getattr(balance, "total", None),
                    "locked": getattr(balance, "locked", None),
                }
                for balance in balances
            ],
            exchange=exchange_name,
        )
    except Exception as e:
        return _err(f"{exchange_name}: {e}. Ensure credentials are configured.")


def pmxt_positions(exchange: str) -> dict:
    """Get open positions. Requires exchange credentials."""
    err = _ensure()
    if err:
        return err

    exchange_name = normalize_exchange_name(exchange)
    ex, init_err = get_exchange(exchange_name)
    if init_err:
        return _err(init_err)

    try:
        positions = ex.fetch_positions()
        return _ok(
            [
                {
                    "market_id": getattr(position, "market_id", None),
                    "title": getattr(position, "title", ""),
                    "outcome_id": getattr(position, "outcome_id", None),
                    "outcome_label": getattr(
                        position,
                        "outcome_label",
                        getattr(position, "outcome", ""),
                    ),
                    "size": getattr(position, "size", 0),
                    "entry_price": getattr(
                        position,
                        "entry_price",
                        getattr(position, "avg_price", None),
                    ),
                    "current_price": getattr(position, "current_price", None),
                    "unrealized_pnl": getattr(
                        position,
                        "unrealized_pnl",
                        getattr(position, "pnl", None),
                    ),
                    "realized_pnl": getattr(position, "realized_pnl", None),
                }
                for position in positions
            ],
            exchange=exchange_name,
        )
    except Exception as e:
        return _err(f"{exchange_name}: {e}. Ensure credentials are configured.")


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
    """
    err = _ensure()
    if err:
        return err

    exchange_name = normalize_exchange_name(exchange)
    ex, init_err = get_exchange(exchange_name)
    if init_err:
        return _err(init_err)

    try:
        cached_market = _get_cached_market(exchange_name, market_id)
        outcome_id = None
        if cached_market is not None:
            outcome_id = _resolve_outcome_id(cached_market, outcome)
        elif not _is_alias_outcome(outcome):
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
            "order_id": getattr(order, "id", None),
            "market_id": getattr(order, "market_id", market_id),
            "outcome_id": getattr(order, "outcome_id", outcome_id),
            "side": getattr(order, "side", side),
            "type": getattr(order, "type", order_params["type"]),
            "amount": getattr(order, "amount", amount),
            "price": getattr(order, "price", price),
            "status": getattr(order, "status", None),
            "filled": getattr(order, "filled", None),
            "remaining": getattr(order, "remaining", None),
            "timestamp": getattr(order, "timestamp", None),
        }, exchange=exchange_name)
    except Exception as e:
        return _err(f"{exchange_name}: {e}. Ensure credentials are configured.")


def pmxt_execution_price(
    outcome_id: str,
    exchange: str,
    side: str,
    amount: float,
) -> dict:
    """
    Estimate execution price and slippage for a target order size.

    Uses the exchange helper if available, otherwise calculates manually from
    the visible order book.
    """
    err = _ensure()
    if err:
        return err

    exchange_name = normalize_exchange_name(exchange)
    ex, init_err = get_exchange(exchange_name)
    if init_err:
        return _err(init_err)

    try:
        book = ex.fetch_order_book(outcome_id)
        levels = book.asks if side == "buy" else book.bids
        best_price = levels[0].price if levels else None

        detailed_method = getattr(ex, "get_execution_price_detailed", None)
        if callable(detailed_method):
            try:
                detailed = detailed_method(book, side, amount)
                estimated = getattr(detailed, "price", None)
                slippage = (
                    round(abs(estimated - best_price), 6)
                    if estimated is not None and best_price is not None
                    else None
                )
                return _ok(
                    {
                        "estimated_price": estimated,
                        "best_price": best_price,
                        "slippage": slippage,
                        "slippage_pct": (
                            f"{(slippage / best_price) * 100:.2f}%"
                            if slippage is not None and best_price
                            else None
                        ),
                        "filled_amount": getattr(detailed, "filled_amount", amount),
                        "requested_amount": amount,
                        "side": side,
                    },
                    outcome_id=outcome_id,
                    exchange=exchange_name,
                )
            except TypeError:
                pass

        price_method = getattr(ex, "get_execution_price", None)
        if callable(price_method):
            for call_args in ((book, side, amount), (outcome_id, side, amount)):
                try:
                    estimated = price_method(*call_args)
                    slippage = (
                        round(abs(estimated - best_price), 6)
                        if estimated is not None and best_price is not None
                        else None
                    )
                    return _ok(
                        {
                            "estimated_price": estimated,
                            "best_price": best_price,
                            "slippage": slippage,
                            "slippage_pct": (
                                f"{(slippage / best_price) * 100:.2f}%"
                                if slippage is not None and best_price
                                else None
                            ),
                            "requested_amount": amount,
                            "side": side,
                        },
                        outcome_id=outcome_id,
                        exchange=exchange_name,
                    )
                except TypeError:
                    continue

        remaining = amount
        total_value = 0.0
        for level in levels:
            fill = min(remaining, level.size)
            total_value += fill * level.price
            remaining -= fill
            if remaining <= 0:
                break

        if remaining > 0:
            return _err(
                f"Insufficient liquidity for {amount} contracts. "
                f"Only {round(amount - remaining, 4)} available in the visible book."
            )

        estimated_price = total_value / amount if amount else 0
        slippage = (
            round(abs(estimated_price - best_price), 6)
            if best_price is not None
            else None
        )
        return _ok(
            {
                "estimated_price": round(estimated_price, 6),
                "best_price": best_price,
                "slippage": slippage,
                "slippage_pct": (
                    f"{(slippage / best_price) * 100:.2f}%"
                    if slippage is not None and best_price
                    else None
                ),
                "total_value": round(total_value, 6),
                "requested_amount": amount,
                "side": side,
            },
            outcome_id=outcome_id,
            exchange=exchange_name,
        )
    except Exception as e:
        return _err(f"{exchange_name}: {e}")


def pmxt_compare_market(
    query: str,
    exchanges: Optional[list[str]] = None,
    limit: int = 5,
) -> dict:
    """
    Compare similar market matches across exchanges for a single query.

    Returns grouped comparisons with per-exchange prices and simple spread stats.
    """
    targets = [normalize_exchange_name(name) for name in (exchanges or ["polymarket", "kalshi"])]

    search_results = {}
    for ex_name in targets:
        result = pmxt_search(query, exchange=ex_name, limit=limit)
        if result["success"] and result["data"]:
            search_results[ex_name] = result["data"]

    if not search_results:
        return _err("No comparable markets found on any exchange")

    comparisons = []
    for markets in search_results.values():
        for market in markets:
            matched_group = None
            for group in comparisons:
                if _title_overlap(group["title"], market["title"]) >= 0.45:
                    matched_group = group
                    break
            if matched_group is None:
                matched_group = {"title": market["title"], "markets": []}
                comparisons.append(matched_group)
            matched_group["markets"].append(market)

    result_groups = []
    for group in comparisons:
        quotes = []
        yes_prices = []
        no_prices = []

        for market in group["markets"]:
            yes_price, no_price = _extract_yes_no(market)
            if yes_price is not None:
                yes_prices.append(yes_price)
            if no_price is not None:
                no_prices.append(no_price)
            quotes.append({
                "exchange": market.get("exchange"),
                "market_id": market.get("market_id"),
                "slug": market.get("slug"),
                "yes_price": yes_price,
                "no_price": no_price,
                "volume_24h": market.get("volume_24h", 0),
                "liquidity": market.get("liquidity", 0),
                "url": market.get("url", ""),
            })

        result_groups.append({
            "title": group["title"],
            "quotes": quotes,
            "exchange_count": len(quotes),
            "yes_spread": round(max(yes_prices) - min(yes_prices), 6) if len(yes_prices) >= 2 else None,
            "no_spread": round(max(no_prices) - min(no_prices), 6) if len(no_prices) >= 2 else None,
        })

    return _ok(result_groups, count=len(result_groups), exchanges_compared=targets)


def pmxt_portfolio(exchanges: Optional[list[str]] = None) -> dict:
    """
    Build a unified portfolio view across multiple exchanges.

    Aggregates balances and open positions while tolerating per-exchange auth gaps.
    """
    targets = [normalize_exchange_name(name) for name in (exchanges or list(TRADING_EXCHANGES))]
    positions = []
    balances = []
    errors = []

    total_notional = 0.0
    total_unrealized_pnl = 0.0

    for ex_name in targets:
        balance_result = pmxt_balance(ex_name)
        if balance_result["success"]:
            balances.append({
                "exchange": ex_name,
                "balances": balance_result["data"],
            })
        else:
            errors.append(balance_result["error"])

        positions_result = pmxt_positions(ex_name)
        if positions_result["success"]:
            for position in positions_result["data"]:
                normalized_position = dict(position)
                normalized_position["exchange"] = ex_name
                positions.append(normalized_position)

                size = normalized_position.get("size") or 0
                current_price = normalized_position.get("current_price") or 0
                unrealized = normalized_position.get("unrealized_pnl")

                total_notional += size * current_price
                if unrealized is not None:
                    total_unrealized_pnl += unrealized
        else:
            errors.append(positions_result["error"])

    return _ok(
        {
            "balances": balances,
            "positions": positions,
            "summary": {
                "exchange_count": len(targets),
                "exchanges_with_positions": sorted({position["exchange"] for position in positions}),
                "total_positions": len(positions),
                "total_notional": round(total_notional, 4),
                "total_unrealized_pnl": round(total_unrealized_pnl, 4),
            },
        },
        exchanges=targets,
        partial_errors=errors or None,
    )


def pmxt_arbitrage_scan(
    query: str,
    exchanges: Optional[list[str]] = None,
    threshold: float = 0.95,
) -> dict:
    """
    Scan for cross-exchange arbitrage opportunities.

    Finds the same topic on multiple exchanges and checks if YES on one + NO
    on another sums below 1.0 (risk-free profit).
    """
    exchange_names = [normalize_exchange_name(name) for name in (exchanges or ["polymarket", "kalshi"])]

    results = {}
    for ex_name in exchange_names:
        result = pmxt_search(query, exchange=ex_name, limit=10)
        if result["success"] and result["data"]:
            results[ex_name] = result["data"]

    if len(results) < 2:
        return _err("Need results from at least 2 exchanges for arbitrage scan")

    opportunities = []
    names = list(results.keys())

    for index, ex_a in enumerate(names):
        for ex_b in names[index + 1:]:
            for market_a in results[ex_a]:
                for market_b in results[ex_b]:
                    if _title_overlap(market_a["title"], market_b["title"]) < 0.4:
                        continue

                    yes_a, no_a = _extract_yes_no(market_a)
                    yes_b, no_b = _extract_yes_no(market_b)

                    if yes_a is not None and no_b is not None:
                        combined = round(yes_a + no_b, 4)
                        if combined < threshold:
                            opportunities.append({
                                "strategy": "buy_yes_a_sell_no_b",
                                "market_a": market_a["title"],
                                "exchange_a": ex_a,
                                "yes_price_a": yes_a,
                                "yes_pct_a": f"{yes_a * 100:.1f}%",
                                "market_b": market_b["title"],
                                "exchange_b": ex_b,
                                "no_price_b": no_b,
                                "no_pct_b": f"{no_b * 100:.1f}%",
                                "combined_price": combined,
                                "profit_margin": f"{(1 - combined) * 100:.1f}%",
                            })

                    if no_a is not None and yes_b is not None:
                        combined = round(no_a + yes_b, 4)
                        if combined < threshold:
                            opportunities.append({
                                "strategy": "buy_no_a_sell_yes_b",
                                "market_a": market_a["title"],
                                "exchange_a": ex_a,
                                "no_price_a": no_a,
                                "no_pct_a": f"{no_a * 100:.1f}%",
                                "market_b": market_b["title"],
                                "exchange_b": ex_b,
                                "yes_price_b": yes_b,
                                "yes_pct_b": f"{yes_b * 100:.1f}%",
                                "combined_price": combined,
                                "profit_margin": f"{(1 - combined) * 100:.1f}%",
                            })

    return _ok(
        opportunities,
        count=len(opportunities),
        exchanges_scanned=exchange_names,
        threshold=threshold,
    )


# ---------------------------------------------------------------------------
# Runtime / Discovery Helpers
# ---------------------------------------------------------------------------

def pmxt_runtime_status() -> dict:
    """
    Return comprehensive runtime status including mode, config, and pmxt version.

    Works without pmxt installed; returns pmxt_installed=False if absent.
    """
    return _ok(_runtime_status_dict(), version=__import__("hermes_pmxt").__version__)


def pmxt_list_exchanges() -> dict:
    """
    Return all known exchanges with aliases and availability info.

    Reports which exchanges are available in the installed pmxt build.
    """
    available = available_exchange_names() if is_pmxt_available() else []
    return _ok({
        "known": list(KNOWN_EXCHANGES),
        "aliases": dict(EXCHANGE_ALIASES),
        "available": available,
        "mode": get_mode(),
        "base_url": get_base_url(),
    })


_DESTRUCTIVE_CONFIRM_MSG = (
    "Operation '{}' is destructive and requires explicit user confirmation. "
    "Set confirmed=True after the user has approved the full order details "
    "(exchange, market, outcome, side, amount, price/type)."
)


def _require_confirmed(method: str, confirmed: bool = False) -> Optional[dict]:
    """Return an error dict if a destructive operation is not confirmed."""
    if not confirmed:
        return _err(_DESTRUCTIVE_CONFIRM_MSG.format(method))
    return None


def _resolve_method_on_exchange(ex: object, method_name: str, *args):
    """
    Try to call a named method on an exchange, falling back to call_api.

    Returns the raw result from the PMXT SDK.
    """
    method = getattr(ex, method_name, None)
    if callable(method):
        return method(*args)

    # Fallback: try call_api or generic HTTP
    call_api = getattr(ex, "call_api", None)
    if callable(call_api):
        return call_api(method_name, *args)

    raise AttributeError(
        f"Exchange does not support {method_name} and has no call_api fallback"
    )


# ---------------------------------------------------------------------------
# Generic pmxt_call
# ---------------------------------------------------------------------------

def pmxt_call(
    method: str,
    exchange: str,
    params: Optional[dict] = None,
    args: Optional[list] = None,
    credentials: Optional[dict] = None,
    *,
    confirmed: bool = False,
    verbose: bool = False,
) -> dict:
    """
    Generic PMXT API call using the tool registry and PMXT SDK.

    Args:
        method: PMXT method name (e.g. 'fetchMarkets', 'compareMarketPrices')
        exchange: Exchange name (canonical or alias)
        params: Flat params dict (mapped to positional args per registry)
        args: Raw positional args list (overrides params if provided)
        credentials: Optional venue credentials dict
        confirmed: Required True for destructive operations (createOrder, etc.)
        verbose: Return raw output instead of compact shaped result

    Returns:
        Standard {success, data, error?, meta?} dict with shaped results
    """
    err = _ensure()
    if err:
        return err

    tool = get_tool(method)
    if tool is None:
        return _err(f"Unknown PMXT method: {method}")

    if _is_destructive(method):
        block = _require_confirmed(method, confirmed)
        if block:
            return block

    exchange_name = normalize_exchange_name(exchange)
    ex, init_err = get_exchange(exchange_name)
    if init_err:
        return _err(init_err)

    try:
        if args is not None:
            raw = _resolve_method_on_exchange(ex, method, *args)
        else:
            raw = _resolve_method_on_exchange(ex, method, params or {})

        shaped = shape_result(method, raw, verbose=verbose)
        shaped["meta"] = {
            "method": method,
            "exchange": exchange_name,
            "mode": get_mode(),
        }
        return _ok(shaped)
    except Exception as e:
        return _err(f"{exchange_name}/{method}: {e}")


# ---------------------------------------------------------------------------
# Safer Order Management
# ---------------------------------------------------------------------------

def pmxt_build_order(
    market_id: Optional[str] = None,
    outcome_id: Optional[str] = None,
    side: str = "buy",
    order_type: str = "limit",
    amount: float = 0.0,
    price: Optional[float] = None,
    exchange: str = "polymarket",
    *,
    outcome: Optional[str] = None,
    denom: str = "usdc",
    slippage_pct: Optional[float] = 30.0,
) -> dict:
    """
    Build (sign/preview) an order without submitting it.

    Safe to call -- does NOT place a real order. Returns a built payload
    that can be inspected before calling pmxt_submit_order().

    Args:
        market_id: Market UUID or slug
        outcome_id: Outcome token ID
        side: 'buy' or 'sell'
        order_type: 'market' or 'limit'
        amount: Contract amount
        price: Limit price (required for limit orders)
        exchange: Exchange name
        outcome: Friendly 'yes'/'no' or label -- resolved to outcome_id
        denom: 'usdc' or 'shares'
        slippage_pct: Slippage percentage for market orders
    """
    err = _ensure()
    if err:
        return err

    exchange_name = normalize_exchange_name(exchange)
    ex, init_err = get_exchange(exchange_name)
    if init_err:
        return _err(init_err)

    # Resolve friendly outcome to outcome_id if needed
    resolved_outcome_id = outcome_id
    if outcome is not None and outcome_id is None:
        cached = _get_cached_market(exchange_name, market_id or "")
        if cached is not None:
            resolved_outcome_id = _resolve_outcome_id(cached, outcome)
        elif not _is_alias_outcome(outcome):
            resolved_outcome_id = outcome.strip()
        if resolved_outcome_id is None:
            return _err(
                "Could not resolve outcome. Run pmxt_search() first, then pass "
                "'yes'/'no' or an exact outcome_id."
            )

    if side not in ("buy", "sell"):
        return _err("side must be 'buy' or 'sell'")
    if order_type not in ("market", "limit"):
        return _err("order_type must be 'market' or 'limit'")
    if order_type == "limit" and price is None:
        return _err("price is required for limit orders")
    if amount <= 0:
        return _err("amount must be positive")

    try:
        build_method = getattr(ex, "build_order", None)
        if not callable(build_method):
            return _err(f"{exchange_name}: build_order is not available in this pmxt version")

        built = build_method(
            market_id=market_id,
            outcome_id=resolved_outcome_id,
            side=side,
            order_type=order_type,
            amount=amount,
            price=price,
            denom=denom,
            slippage_pct=slippage_pct,
        )

        # Serialize built order details for agent inspection
        return _ok({
            "market_id": getattr(built, "market_id", market_id),
            "outcome_id": getattr(built, "outcome_id", resolved_outcome_id),
            "side": side,
            "order_type": order_type,
            "amount": amount,
            "price": price,
            "denom": denom,
            "built": {
                "expiry": getattr(built, "expiry", None),
            },
            "preview": True,
            "note": "Order built but NOT submitted. Call pmxt_submit_order() with confirmed=True to place it.",
        }, exchange=exchange_name)
    except Exception as e:
        return _err(f"{exchange_name}/build_order: {e}")


def pmxt_submit_order(
    built: dict,
    exchange: str,
    *,
    confirmed: bool = False,
) -> dict:
    """
    Submit a pre-built order. DESTRUCTIVE -- requires confirmed=True.

    The built payload must come from pmxt_build_order().
    """
    block = _require_confirmed("submit_order", confirmed)
    if block:
        return block

    err = _ensure()
    if err:
        return err

    exchange_name = normalize_exchange_name(exchange)
    ex, init_err = get_exchange(exchange_name)
    if init_err:
        return _err(init_err)

    try:
        submit_method = getattr(ex, "submit_order", None)
        if not callable(submit_method):
            return _err(f"{exchange_name}: submit_order is not available")

        order = submit_method(built)
        return _ok({
            "order_id": getattr(order, "id", None),
            "market_id": getattr(order, "market_id", None),
            "outcome_id": getattr(order, "outcome_id", None),
            "side": getattr(order, "side", None),
            "type": getattr(order, "type", None),
            "amount": getattr(order, "amount", None),
            "price": getattr(order, "price", None),
            "status": getattr(order, "status", None),
            "filled": getattr(order, "filled", None),
            "remaining": getattr(order, "remaining", None),
        }, exchange=exchange_name)
    except Exception as e:
        return _err(f"{exchange_name}/submit_order: {e}")


def pmxt_cancel_order(
    order_id: str,
    exchange: str,
    *,
    confirmed: bool = False,
) -> dict:
    """
    Cancel an open order. DESTRUCTIVE -- requires confirmed=True.
    """
    block = _require_confirmed("cancel_order", confirmed)
    if block:
        return block

    err = _ensure()
    if err:
        return err

    exchange_name = normalize_exchange_name(exchange)
    ex, init_err = get_exchange(exchange_name)
    if init_err:
        return _err(init_err)

    try:
        cancel_method = getattr(ex, "cancel_order", None)
        if not callable(cancel_method):
            return _err(f"{exchange_name}: cancel_order is not available")

        result = cancel_method(order_id)
        return _ok({
            "order_id": order_id,
            "status": getattr(result, "status", "cancelled"),
        }, exchange=exchange_name)
    except Exception as e:
        return _err(f"{exchange_name}/cancel_order: {e}")


# ---------------------------------------------------------------------------
# Server Management
# ---------------------------------------------------------------------------

def pmxt_server_health() -> dict:
    """Check if pmxt sidecar server is healthy."""
    return _ok(server_status())


def pmxt_server_status() -> dict:
    """Return pmxt sidecar status details."""
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
