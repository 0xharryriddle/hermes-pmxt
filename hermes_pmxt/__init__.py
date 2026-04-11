"""
hermes-pmxt — Prediction market integration for Hermes Agent.

Usage:
    from hermes_pmxt import pmxt_search, pmxt_quote, pmxt_order, ...
"""

from hermes_pmxt.tools import (
    pmxt_arbitrage_scan,
    pmxt_balance,
    pmxt_compare_market,
    pmxt_events,
    pmxt_execution_price,
    pmxt_ohlcv,
    pmxt_order,
    pmxt_order_book,
    pmxt_portfolio,
    pmxt_positions,
    pmxt_quote,
    pmxt_search,
    pmxt_server_health,
    pmxt_server_start,
    pmxt_server_status,
    pmxt_server_stop,
    pmxt_trades,
)

__version__ = "0.2.0"

__all__ = [
    "pmxt_search",
    "pmxt_quote",
    "pmxt_order_book",
    "pmxt_ohlcv",
    "pmxt_trades",
    "pmxt_events",
    "pmxt_execution_price",
    "pmxt_compare_market",
    "pmxt_balance",
    "pmxt_positions",
    "pmxt_portfolio",
    "pmxt_order",
    "pmxt_arbitrage_scan",
    "pmxt_server_health",
    "pmxt_server_status",
    "pmxt_server_start",
    "pmxt_server_stop",
]
