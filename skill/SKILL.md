---
name: pmxt
description: Prediction market integration — search, compare, and trade across pmxt-supported prediction market exchanges.
version: 0.2.0
author: hermes-pmxt
license: MIT
metadata:
  hermes:
    tags: [prediction-markets, polymarket, kalshi, trading, finance, arbitrage]
    category: research
    requires_tools: [execute_code]
---

# pmxt — Prediction Markets for Hermes

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
# pip
pip install pmxt

# uv
uv pip install pmxt

# If your pmxt install still needs the sidecar, pick one package manager
npm install -g pmxtjs
pnpm add -g pmxtjs
yarn global add pmxtjs
bun add -g pmxtjs
```

No API keys needed for **read-only** operations (search, quote, order book, OHLCV).
Trading requires exchange credentials in env vars.

## Quick Reference

All tools are in the `hermes_pmxt` package. Import and call from `execute_code`:

```python
from hermes_pmxt import pmxt_search, pmxt_quote, pmxt_order_book
```

| Function | Auth | Description |
|----------|------|-------------|
| `pmxt_search(query, exchange?, limit?, sort?, search_in?, slug?)` | No | Search markets |
| `pmxt_quote(keyword, exchange)` | No | Get YES/NO probabilities |
| `pmxt_order_book(outcome_id, exchange, limit?)` | No | Order book depth |
| `pmxt_ohlcv(outcome_id, exchange, res?, limit?)` | No | Price candles |
| `pmxt_trades(outcome_id, exchange, limit?)` | No | Recent trades |
| `pmxt_events(query, exchange?, limit?, sort?, search_in?, slug?)` | No | Search events |
| `pmxt_execution_price(outcome_id, exchange, side, amount)` | No | Slippage estimate |
| `pmxt_compare_market(query, exchanges?, limit?)` | No | Cross-exchange comparison |
| `pmxt_balance(exchange)` | Yes | Account balance |
| `pmxt_positions(exchange)` | Yes | Open positions |
| `pmxt_portfolio(exchanges?)` | Yes | Unified balances and positions |
| `pmxt_order(...)` | Yes | Place order, after resolving the market's outcome IDs |
| `pmxt_arbitrage_scan(query, exchanges?, threshold?)` | No | Cross-exchange spreads |
| `pmxt_server_status()` | No | Sidecar diagnostics |

## Procedure

### Rule 1: Don't Hallucinate, Calculate

When user asks "Is X likely?":
1. `pmxt_search("X", exchange="polymarket")` — use broad keywords
2. `pmxt_quote("distinctive phrase from title", exchange="polymarket")`
3. Reply: "The market implies a **[Price]%** chance."

**Search tips**: Use broad keywords, not full sentences.
- Bad: `pmxt_search("Who will win the next presidential election?")`
- Good: `pmxt_search("election", exchange="polymarket")`

**Quote tips**: Use a distinctive phrase from the market title.
- Good: `pmxt_quote("bitcoin reach", "polymarket")`
- Good: `pmxt_quote("trump nominate", "polymarket")`

### Rule 2: Smart Responses

Synthesize, don't dump raw numbers:
- Bad: "Gavin is 0.30."
- Good: "The market prices Gavin Newsom at **30%** (No: 70%). Skeptical outlook."

### Rule 3: Arbitrage Awareness

When comparing quotes across exchanges, silently check if YES(a) + NO(b) < 1.00.
If found: "Arbitrage Opportunity: Buy YES on [A] at [X]% + NO on [B] at [Y]% = [Z]% risk-free yield."

### Rule 4: Order Safety

NEVER place orders without explicit user confirmation including market, outcome, amount, exchange.
Before calling `pmxt_order()`, fetch the market with `pmxt_search()` or `pmxt_quote()` so
`yes` / `no` can be mapped to the correct `outcome_id`. If you already have the exact
`outcome_id`, pass that directly as the `outcome` argument.

### Rule 5: Price Format

All prices are 0.0-1.0 (probabilities). Always show as percentages to users.

### Rule 6: Use Comparison Before Claiming Disagreement

When a user asks whether exchanges disagree, run `pmxt_compare_market(...)` before
describing spread differences. Use `pmxt_execution_price(...)` before discussing
whether a displayed spread is realistically tradable at size.

### Rule 7: Portfolio Calls Need Auth Expectations

`pmxt_portfolio()` aggregates positions and balances across exchanges. Partial errors
are expected when some exchange credentials are missing; summarize successful
exchanges clearly instead of treating that as a full failure.

## Pitfalls

- **Kalshi is slower** for search than Polymarket/Limitless
- **outcome_id vs market_id**: Use `outcome_id` for order book/OHLCV/trades, `market_id` for orders
- **Sidecar behavior depends on pmxt version**: use `pmxt_server_status()` to confirm
- **Prices are 0-1** not dollars — don't confuse
- **Timestamps are Unix ms** — divide by 1000 for Python datetime
- **Exchange support depends on installed pmxt build**: this package is wired for Polymarket,
  Polymarket US, Kalshi, Limitless, Myriad, Opinion, Metaculus, and Smarkets

## Example Workflow

```python
from hermes_pmxt import pmxt_search, pmxt_quote, pmxt_order_book, pmxt_ohlcv

# 1. Search
result = pmxt_search("bitcoin", exchange="polymarket", limit=5)
markets = result["data"]
first = markets[0]

# 2. Quote using a keyword from the title
quote = pmxt_quote("bitcoin reach", "polymarket")
# => {"yes_pct": "4.3%", "no_pct": "95.7%", ...}

# 3. Order book (use outcome_id from search or quote results)
if first["outcomes"]:
    book = pmxt_order_book(first["outcomes"][0]["outcome_id"], "polymarket")
    # => {"best_bid": 0.043, "best_ask": 0.044, "spread": 0.001}

# 4. Price history
    candles = pmxt_ohlcv(first["outcomes"][0]["outcome_id"], "polymarket", resolution="1d")
```
