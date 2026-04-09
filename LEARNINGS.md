# Learnings — Building hermes-pmxt

Things discovered during implementation that differ from the docs/research.

## pmxt SDK Realities

### server.status() returns a dict, not an object
The docs suggest `status.running`, `status.pid` etc. In practice, `pmxt.server.status()`
returns a plain `dict` with keys: `running`, `pid`, `port`, `version`, `uptimeSeconds`,
`lock_file`. Must use `.get()` not attribute access.

### fetch_market() (singular) doesn't work by ID
`exchange.fetch_market(market_id="701486")` throws `PmxtError: Unknown error`.
The singular method exists but its parameter handling is unclear.
**Workaround**: Use `fetch_markets(query=keyword, limit=N)` to search by title/keyword.

### fetch_markets(slug=...) is slow or returns empty
For Polymarket, slug-based lookup (`fetch_markets(slug="will-bitcoin-reach-...")`) either
times out or returns 0 results. The slug parameter doesn't map to Polymarket's API as
expected.
**Workaround**: Use keyword query search. Works fast and reliably.

### search vs quote — keyword is the key
The most reliable way to find a specific market is through keyword search.
Quote should accept a distinctive phrase from the market title, not a numeric ID.

### orders still need real outcome_ids under the hood
The pmxt SDK's `create_order()` call requires `market_id` plus `outcome_id`.
This wrapper now resolves `yes` / `no` or exact labels from markets already fetched by
`pmxt_search()` / `pmxt_quote()`. If you skip the lookup step, pass the exact
`outcome_id` yourself.

## Kalshi Behavior

- Kalshi returns markets with `before`/`not before` label style
- Kalshi can be read-only without API keys (data only)
- Kalshi search is slower than Polymarket

## Sidecar Server

- Auto-starts on first SDK call (~1-2 seconds)
- `pmxt.server.health()` returns bool — simplest check
- Logs at `~/.pmxt/server.log`
- Shared across Python processes (singleton)
- Version 2.0.2 at time of build

## Price Scale

All prices confirmed as 0.0-1.0 (probabilities). Kalshi internally uses 0-100
but pmxt normalizes to 0-1 in the Python SDK.

## outcome_id is Very Long

Polymarket outcome_ids are 70+ character strings (token IDs). Don't try to
display them — use labels for display and pass IDs as-is for API calls.

## Trade Timestamps

All timestamps are Unix milliseconds. Recent trades show real-time activity —
sub-second resolution. Divide by 1000 for Python datetime.

## Arbitrage Scan Design

Cross-exchange matching is done by title word overlap (Jaccard similarity on words).
40% threshold works for finding related markets. True arbitrage is rare — most
combined prices are near 1.00.
