"""
hermes-pmxt — Prediction market integration for Hermes Agent.

Usage:
    from hermes_pmxt import pmxt_search, pmxt_quote, pmxt_order, ...
"""

from hermes_pmxt.tools import (
    pmxt_search,
    pmxt_quote,
    pmxt_order_book,
    pmxt_ohlcv,
    pmxt_trades,
    pmxt_events,
    pmxt_balance,
    pmxt_positions,
    pmxt_order,
    pmxt_arbitrage_scan,
    pmxt_server_health,
    pmxt_server_start,
    pmxt_server_stop,
)

__version__ = "0.1.0"

__all__ = [
    "pmxt_search",
    "pmxt_quote",
    "pmxt_order_book",
    "pmxt_ohlcv",
    "pmxt_trades",
    "pmxt_events",
    "pmxt_balance",
    "pmxt_positions",
    "pmxt_order",
    "pmxt_arbitrage_scan",
    "pmxt_server_health",
    "pmxt_server_start",
    "pmxt_server_stop",
]
