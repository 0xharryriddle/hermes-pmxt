"""Native, read-only Hermes plugin adapter for hermes-pmxt.

This module only uses the documented PluginContext methods supplied to register().
It deliberately does not start PMXT, probe capabilities, or expose trading writes.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

from hermes_pmxt.tools import (
    pmxt_call,
    pmxt_events,
    pmxt_list_exchanges,
    pmxt_runtime_status,
    pmxt_search,
)


_SKILL_PATH = Path(__file__).with_name("skill") / "SKILL.md"


def _json_handler(function: Callable[..., dict]) -> Callable[..., str]:
    """Adapt a public SDK function to Hermes's JSON-string handler contract."""

    def handler(params: dict | None = None, **_host_kwargs: Any) -> str:
        result = function(**(params or {}))
        return json.dumps(result, default=str)

    return handler


def _schema(name: str, description: str, properties: dict, required: list[str] | None = None) -> dict:
    return {
        "name": name,
        "description": description,
        "parameters": {
            "type": "object",
            "properties": properties,
            "required": required or [],
            "additionalProperties": False,
        },
    }


def _series(**params: Any) -> dict:
    exchange = params.pop("exchange", "polymarket")
    return pmxt_call("fetchSeries", exchange, params=params)


def _order_books(**params: Any) -> dict:
    exchange = params.pop("exchange", "polymarket")
    outcome_ids = params.pop("outcome_ids")
    return pmxt_call("fetchOrderBooks", exchange, params={"outcome_ids": outcome_ids})


def _matched_market_clusters(**params: Any) -> dict:
    return pmxt_call("fetchMatchedMarketClusters", "router", params=params)


TOOLS: tuple[tuple[str, dict, Callable[..., dict]], ...] = (
    (
        "pmxt_runtime_status",
        _schema("pmxt_runtime_status", "Show hermes-pmxt mode and non-secret diagnostics.", {}),
        pmxt_runtime_status,
    ),
    (
        "pmxt_list_exchanges",
        _schema("pmxt_list_exchanges", "List known PMXT venues and SDK availability.", {}),
        pmxt_list_exchanges,
    ),
    (
        "pmxt_search",
        _schema(
            "pmxt_search",
            "Search prediction markets on one PMXT venue. Read-only.",
            {
                "query": {"type": "string", "description": "Short market search query."},
                "exchange": {"type": "string", "description": "Venue, default polymarket."},
                "limit": {"type": "integer", "minimum": 1, "maximum": 20},
            },
            ["query"],
        ),
        pmxt_search,
    ),
    (
        "pmxt_events",
        _schema(
            "pmxt_events",
            "Search prediction-market event groups on one PMXT venue. Read-only.",
            {
                "query": {"type": "string", "description": "Short event search query."},
                "exchange": {"type": "string", "description": "Venue, default polymarket."},
                "limit": {"type": "integer", "minimum": 1, "maximum": 20},
            },
            ["query"],
        ),
        pmxt_events,
    ),
    (
        "pmxt_series",
        _schema(
            "pmxt_series",
            "Search PMXT venue series. Read-only.",
            {
                "query": {"type": "string", "description": "Optional series query."},
                "exchange": {"type": "string", "description": "Venue, default polymarket."},
            },
        ),
        _series,
    ),
    (
        "pmxt_order_books",
        _schema(
            "pmxt_order_books",
            "Fetch order books for multiple outcome IDs. Read-only.",
            {
                "outcome_ids": {"type": "array", "items": {"type": "string"}, "minItems": 1},
                "exchange": {"type": "string", "description": "Venue, default polymarket."},
            },
            ["outcome_ids"],
        ),
        _order_books,
    ),
    (
        "pmxt_matched_market_clusters",
        _schema(
            "pmxt_matched_market_clusters",
            "Find cross-venue market clusters with PMXT relation/confidence evidence. Read-only.",
            {
                "query": {"type": "string", "description": "Optional topic or market query."},
                "market_id": {"type": "string", "description": "Optional PMXT catalog market ID."},
                "min_confidence": {"type": "number", "minimum": 0, "maximum": 1},
                "min_venues": {"type": "integer", "minimum": 2},
                "limit": {"type": "integer", "minimum": 1, "maximum": 20},
            },
        ),
        _matched_market_clusters,
    ),
)


def register(ctx: Any) -> None:
    """Register curated, read-only PMXT tools and the bundled skill."""
    for name, schema, function in TOOLS:
        ctx.register_tool(
            name=name,
            toolset="pmxt",
            schema=schema,
            handler=_json_handler(function),
        )
    ctx.register_skill("pmxt", _SKILL_PATH)
