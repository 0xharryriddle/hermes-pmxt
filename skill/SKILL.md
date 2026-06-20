---
name: pmxt
description: Prediction market integration -- search, compare, and trade across pmxt-supported prediction market exchanges.
version: 0.3.0
author: hermes-pmxt
license: MIT
metadata:
  hermes:
    tags: [prediction-markets, polymarket, kalshi, trading, finance, arbitrage]
    category: research
    requires_tools: [execute_code]
---

# pmxt -- Prediction Markets for Hermes

Real-time access to prediction markets for fact-checking, probability analysis,
arbitrage detection, execution planning, and portfolio inspection.

## When to Use

- User asks "What's the probability of X?" or "Is X likely to happen?"
- User wants trending prediction markets
- User wants arbitrage opportunities across exchanges
- User wants to place or manage trades
- User wants to check positions or balance

## Setup

```bash
pip install pmxt>=2.50.0

# Check runtime status
python3 -c "from hermes_pmxt import pmxt_runtime_status; print(pmxt_runtime_status())"
```

Hosted mode (recommended): set `PMXT_API_KEY` env var. Local sidecar mode works
without an API key but requires pmxt-core running on localhost:3847.

## Quick Reference

All tools are in the `hermes_pmxt` package. Import and call from `execute_code`:

```python
from hermes_pmxt import pmxt_search, pmxt_quote, pmxt_order_book, pmxt_call
```

| Function | Auth | Description |
|----------|------|-------------|
| `pmxt_search(query, exchange?, limit?, sort?, search_in?, slug?)` | Mode-dep | Search markets |
| `pmxt_events(query, exchange?, limit?, sort?, search_in?, slug?)` | Mode-dep | Search event groups |
| `pmxt_quote(keyword, exchange)` | Mode-dep | Get YES/NO probabilities |
| `pmxt_order_book(outcome_id, exchange, limit?)` | Mode-dep | Order book depth |
| `pmxt_ohlcv(outcome_id, exchange, res?, limit?)` | Mode-dep | Price candles |
| `pmxt_trades(outcome_id, exchange, limit?)` | Mode-dep | Recent trades |
| `pmxt_execution_price(outcome_id, exchange, side, amount)` | Mode-dep | Slippage estimate |
| `pmxt_compare_market(query, exchanges?, limit?)` | Mode-dep | Cross-exchange comparison |
| `pmxt_arbitrage_scan(query, exchanges?, threshold?)` | Mode-dep | Cross-exchange spreads |
| `pmxt_balance(exchange)` | Yes | Account balance |
| `pmxt_positions(exchange)` | Yes | Open positions |
| `pmxt_portfolio(exchanges?)` | Yes | Unified balances and positions |
| `pmxt_build_order(...)` | Yes | Build/sign order (SAFE, does NOT submit) |
| `pmxt_submit_order(built, exchange, confirmed=True)` | Yes | Submit a pre-built order |
| `pmxt_cancel_order(order_id, exchange, confirmed=True)` | Yes | Cancel an open order |
| `pmxt_call(method, exchange, ...)` | Varies | Generic PMXT API call |
| `pmxt_runtime_status()` | No | Runtime diagnostics |
| `pmxt_list_exchanges()` | No | Known/available exchanges |

## Procedure

### Rule 1: Discovery First

When user asks about a broad topic or probability:
1. `pmxt_events("topic_keyword", exchange="polymarket")` -- discover event groups
2. Drill into specific markets within the event
3. `pmxt_quote("distinctive phrase", exchange="polymarket")` for exact prices

**Search tips**: Use broad keywords, not full sentences.
- Bad: `pmxt_search("Who will win the next presidential election?")`
- Good: `pmxt_events("election", exchange="polymarket")`

**Quote tips**: Use a distinctive phrase from the market title.
- Good: `pmxt_quote("bitcoin reach", "polymarket")`

### Rule 2: Smart Responses

Synthesize, don't dump raw numbers:
- Bad: "Gavin is 0.30."
- Good: "The market prices Gavin Newsom at **30%** (No: 70%). Skeptical outlook."

### Rule 3: Arbitrage Awareness

When comparing quotes across exchanges, check if YES(a) + NO(b) < 1.00.
Use native router methods when available:
```python
pmxt_call("compareMarketPrices", "router", params={"marketId": "...", "slug": "..."})
pmxt_call("fetchArbitrage", "router", params={"query": "..."})
```

### Rule 4: Order Safety (CRITICAL)

**NEVER place orders without explicit user confirmation.**

Safer workflow:
1. `pmxt_build_order(...)` -- preview without submitting
2. Show user: exchange, market, side, amount, price, max spend
3. Wait for explicit approval
4. `pmxt_submit_order(built, exchange, confirmed=True)` -- only after approval

Direct `pmxt_order()` requires outcome IDs. Prefer `pmxt_build_order()` which
resolves friendly `yes`/`no` labels from previously searched markets.

### Rule 5: Price Format

All prices are 0.0-1.0 (probabilities). Always show as percentages to users.

### Rule 6: Use Comparison Before Claiming Disagreement

When user asks whether exchanges disagree, run `pmxt_compare_market(...)` or
`pmxt_call("compareMarketPrices", "router", ...)` before describing spreads.

### Rule 7: Portfolio Calls Need Auth Expectations

`pmxt_portfolio()` aggregates across exchanges. Partial errors are expected
when credentials are missing; summarize successful exchanges clearly.

### Rule 8: Check Runtime Status

When troubleshooting, run `pmxt_runtime_status()` to see mode, base URL,
pmxt version, and sidecar health.

## Pitfalls

- **Hosted mode requires PMXT_API_KEY** for all operations.
- **Local sidecar mode** works without key but needs pmxt-core on localhost:3847.
- **outcome_id vs market_id**: outcome_id for order book/OHLCV/trades, market_id for orders.
- **Prices are 0-1** not dollars -- don't confuse.
- **Timestamps are Unix ms** -- divide by 1000 for Python datetime.
- **Kalshi is slower** for search than Polymarket.
- **Exchange support depends on installed pmxt build**: run `pmxt_list_exchanges()`.

## Example Workflow

```python
from hermes_pmxt import pmxt_events, pmxt_search, pmxt_quote, pmxt_order_book

# 1. Discover events (broad topics)
events = pmxt_events("election", exchange="polymarket", limit=3)
# => each event has title, market_count, top_markets

# 2. Search specific markets
result = pmxt_search("bitcoin", exchange="polymarket", limit=5)
markets = result["data"]

# 3. Quote using a keyword from the title
quote = pmxt_quote("bitcoin reach", "polymarket")
# => {"yes_pct": "4.3%", "no_pct": "95.7%", ...}

# 4. Order book for an outcome
if markets and markets[0].get("outcomes"):
    book = pmxt_order_book(markets[0]["outcomes"][0]["outcome_id"], "polymarket")
    # => {"best_bid": 0.043, "best_ask": 0.044, "spread": 0.001}
```
