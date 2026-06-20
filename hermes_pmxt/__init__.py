"""
hermes-pmxt -- Prediction market integration for Hermes Agent.

Usage:
    from hermes_pmxt import pmxt_search, pmxt_quote, pmxt_order, ...

The package imports without pmxt installed. Tools that require pmxt
will raise ImportError with a helpful message at call time.
"""

from hermes_pmxt.config import (
    get_mode,
    get_base_url,
    runtime_status,
    runtime_status_str,
)
from hermes_pmxt.exchanges import (
    is_pmxt_available,
)
from hermes_pmxt.registry import (
    TOOLS as PMXT_TOOLS,
    KNOWN_EXCHANGES,
    get_tool,
    list_tools,
    is_destructive,
    requires_credentials,
)
from hermes_pmxt.shaper import (
    shape_result,
)

from hermes_pmxt.tools import (
    pmxt_arbitrage_scan,
    pmxt_balance,
    pmxt_build_order,
    pmxt_call,
    pmxt_cancel_order,
    pmxt_compare_market,
    pmxt_events,
    pmxt_execution_price,
    pmxt_list_exchanges,
    pmxt_ohlcv,
    pmxt_order,
    pmxt_order_book,
    pmxt_portfolio,
    pmxt_positions,
    pmxt_quote,
    pmxt_runtime_status,
    pmxt_search,
    pmxt_server_health,
    pmxt_server_start,
    pmxt_server_status,
    pmxt_server_stop,
    pmxt_submit_order,
    pmxt_trades,
)

__version__ = "0.3.0"

__all__ = [
    # Config
    "get_mode",
    "get_base_url",
    "runtime_status",
    "runtime_status_str",
    # Exchange
    "is_pmxt_available",
    "pmxt_list_exchanges",
    "pmxt_runtime_status",
    # Registry
    "PMXT_TOOLS",
    "KNOWN_EXCHANGES",
    "get_tool",
    "list_tools",
    "is_destructive",
    "requires_credentials",
    # Shaper
    "shape_result",
    # Tools
    "pmxt_call",
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
    "pmxt_build_order",
    "pmxt_submit_order",
    "pmxt_cancel_order",
    "pmxt_arbitrage_scan",
    "pmxt_server_health",
    "pmxt_server_status",
    "pmxt_server_start",
    "pmxt_server_stop",
]
