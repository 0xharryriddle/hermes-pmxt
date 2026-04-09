#!/usr/bin/env python3
"""
hermes-pmxt demo — Interactive showcase of all tools.

Usage:
    source .venv/bin/activate
    python examples/demo.py
"""

import json
import sys
import os

# Add parent to path so we can import hermes_pmxt
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from hermes_pmxt import (
    pmxt_search,
    pmxt_quote,
    pmxt_order_book,
    pmxt_ohlcv,
    pmxt_trades,
    pmxt_events,
    pmxt_arbitrage_scan,
    pmxt_server_health,
)


def pp(label: str, result: dict):
    """Pretty-print a tool result."""
    print(f"\n{'='*60}")
    print(f"  {label}")
    print(f"{'='*60}")
    if not result["success"]:
        print(f"  ERROR: {result.get('error', 'unknown')}")
        return None

    data = result["data"]

    # Inline for simple types
    if isinstance(data, (str, int, float, bool)):
        print(f"  {data}")
        return data

    # Compact for dicts/lists
    if isinstance(data, dict):
        for k, v in data.items():
            if isinstance(v, (list, dict)) and len(str(v)) > 100:
                print(f"  {k}: [{len(v)} items]" if isinstance(v, list) else f"  {k}: {{...}}")
            else:
                print(f"  {k}: {v}")
    elif isinstance(data, list):
        print(f"  {len(data)} items")
        for i, item in enumerate(data[:5]):
            if isinstance(item, dict):
                title = item.get("title", item.get("label", str(item)[:60]))
                print(f"    [{i}] {title}")
            else:
                print(f"    [{i}] {item}")
        if len(data) > 5:
            print(f"    ... and {len(data) - 5} more")

    return data


def main():
    print("hermes-pmxt demo")
    print("=" * 60)

    # 1. Server health
    pp("Server Health", pmxt_server_health())

    # 2. Search Polymarket
    markets = pp(
        "Search: 'bitcoin' on Polymarket",
        pmxt_search("bitcoin", exchange="polymarket", limit=5),
    )

    if not markets:
        print("\nNo markets found. Exiting.")
        return

    # 3. Quote first market (use a keyword from the title)
    first = markets[0]
    # Extract a distinctive keyword from the title for quote lookup
    title_keyword = first["title"].split(" - ")[-1][:40] if " - " in first["title"] else first["title"][:40]
    pp(
        f"Quote: {first['title'][:50]}",
        pmxt_quote(title_keyword, "polymarket"),
    )

    # 4. Order book for first outcome
    if first["outcomes"]:
        outcome_id = first["outcomes"][0]["outcome_id"]
        pp(
            f"Order Book: {first['outcomes'][0]['label']}",
            pmxt_order_book(outcome_id, "polymarket"),
        )

        # 5. OHLCV
        pp(
            f"OHLCV (1d, 10 candles): {first['outcomes'][0]['label']}",
            pmxt_ohlcv(outcome_id, "polymarket", resolution="1d", limit=10),
        )

        # 6. Recent trades
        pp(
            f"Recent Trades: {first['outcomes'][0]['label']}",
            pmxt_trades(outcome_id, "polymarket", limit=5),
        )

    # 7. Events
    pp(
        "Events: 'election'",
        pmxt_events("election", exchange="polymarket", limit=3),
    )

    # 8. Arbitrage scan (Polymarket vs Kalshi)
    pp(
        "Arbitrage Scan: 'trump' (Poly vs Kalshi)",
        pmxt_arbitrage_scan("trump", exchanges=["polymarket", "kalshi"]),
    )

    print(f"\n{'='*60}")
    print("  Demo complete!")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
