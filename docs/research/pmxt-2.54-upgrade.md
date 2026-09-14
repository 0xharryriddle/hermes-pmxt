# PMXT 2.54 upgrade research

Status: upstream research; no source changes. Current PyPI `pmxt` is 2.54.0
(`requires-python >=3.8`). The upstream repository's Python package metadata and
`__version__` still report 2.18.x, so version strings from a checkout are not a
reliable compatibility authority. Qualify published wheels and observable
capabilities instead.

## Confirmed upstream changes relevant to hermes-pmxt

### 1. Router is a Python client

Upstream now exports `pmxt.Router` and documents it as cross-venue intelligence.
The current hermes-pmxt docs/learning notes that imply Router is only an
`exchange="router"` target are stale. Preserve the generic router fallback only
as a compatibility path, then add direct Router capability detection and curated
methods after signature tests.

Useful read-only primitives:
- fetch markets across hosted catalog
- fetch matched market clusters with relation/confidence evidence
- compare prices across venues
- matched/related markets, hedges and arbitrage

Source: https://www.pmxt.dev/docs/introduction

### 2. API surface expanded beyond current curated registry

Current core method verbs expose 47 methods. Existing registry has 33, missing:
- fetchEventsPaginated (registry has it; verify current behavior)
- fetchSeries
- fetchMarket and fetchEvent (registry has these)
- fetchEventMetadata
- fetchOrderBooks batch reads
- filterMarkets/filterEvents
- websocket watch/unwatch methods
- auth/session/close lifecycle methods

Not every upstream method belongs in an LLM-facing tool surface. First add only
high-value safe reads: `fetchSeries`, `fetchOrderBooks`, and perhaps curated
router clusters. Keep filters local unless their SDK contract is stable. Do not
expose session/auth lifecycle or websocket subscriptions in the first native
plugin release without lifetime/backpressure design.

Canonical source:
https://raw.githubusercontent.com/pmxt-dev/pmxt/main/core/src/server/method-verbs.json

### 3. New Hunch venue

PMXT 2.51 added Hunch, a Base/x402 parimutuel venue. It differs materially from
CLOB assumptions:
- market orders only; limit, sell and cancel unsupported
- order book is emulated
- binary and N-way outcomes
- volume24h may be 0 because upstream reports a pool total, not a 24h split
- hosted mode is read-only; self-hosted write path needs Base credentials

Add Hunch to discovery/capability reporting. Do not present generic order-book,
limit, sell or cancel affordances without per-venue capability confirmation.

Source: https://www.pmxt.dev/changelog (2.51.0)

### 4. New observable data and pagination

Upstream exports UnifiedSeries, sourceMetadata, paginated events/markets,
matched-cluster types, price comparisons, arbitrage, execution results and
websocket subscription models. The shaper must preserve source/quality/capability
information deliberately rather than flatten unknown models or assume binary
YES/NO. Current docs must become N-way safe.

### 5. Fixed bugs invalidate permissive integration assumptions

PMXT changelog records bugs in OHLCV/trades parameter transport, Hyperliquid ID
handling/limits, user-trade fields/balances, hosted closed/all order behavior,
and error construction. hermes-pmxt must assert returned values and IDs, not only
that calls did not throw. Do not hide typed PMXT errors behind generic failures.

## Direct wheel signature qualification

Installed a fresh temporary environment with `pmxt==2.54.0` and inspected the
actual Python signatures. Confirmed:

- `pmxt.Router(pmxt_api_key=None, base_url=None, auto_start_server=False)`
- `Router.fetch_matched_market_clusters(...)` supports market/event identity,
  query, relation(s), confidence, venue inclusion/exclusion, `min_venues`,
  order-book enrichment, sort, limit and offset.
- `Router.fetch_matched_event_clusters(...)` has equivalent event filters.
- `fetch_series(params=None, **kwargs)`, `fetch_order_books(outcome_ids)`,
  `fetch_events_paginated(params=None, **kwargs)`, and
  `fetch_markets_paginated(params=None, **kwargs)` are present on Router,
  Polymarket, Hunch and Hyperliquid.

Capability discovery is operational, not static: reading an instance's `.has`
property attempted a sidecar HTTP call and failed without a server. The upgrade
must therefore never touch `.has` during import/registration or static list
rendering. Add an explicit diagnostic/capability probe with timeout/error state,
and cache it only under caller control.

## Upgrade recommendation

Target a 0.4.0 release after implementation and qualification:

1. Pin a tested PMXT compatibility window beginning at 2.54.0, with an upper
   bound only after incompatibilities are known. Do not simply raise a minimum
   based on source metadata that contradicts PyPI.
2. Generate or validate registry against the method manifest; classify methods
   into curated/read-only/trading/internal-lifecycle categories.
3. Add dynamic per-instance capability discovery and return unsupported as an
   explicit typed result, not an optimistic UI/tool description.
4. Replace binary-only quote/compare shape with outcome-vector-safe representation.
5. Add Router client path and matched-cluster result shaping with provenance.
6. Add Hunch as a discoverable venue, read-only in default/native plugin mode.
7. Build native adapter and bundled skill only after SDK contract tests pass.

## Evidence

- PyPI: https://pypi.org/pypi/pmxt/json
- PMXT intro/router: https://www.pmxt.dev/docs/introduction
- PMXT changelog: https://www.pmxt.dev/changelog
- Python exports: https://raw.githubusercontent.com/pmxt-dev/pmxt/main/sdks/python/pmxt/__init__.py
- Core method manifest: https://raw.githubusercontent.com/pmxt-dev/pmxt/main/core/src/server/method-verbs.json
