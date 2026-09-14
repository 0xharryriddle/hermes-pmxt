---
name: pmxt
description: Read-only prediction-market research via hermes-pmxt native tools.
version: 0.4.0-dev
metadata:
  hermes:
    tags: [prediction-markets, polymarket, kalshi, research]
---

# PMXT prediction-market research

Use the `pmxt_*` tools for read-only market discovery and diagnostics.

Start with `pmxt_runtime_status` when a backend may be unavailable. Use
`pmxt_events` for broad topics and `pmxt_search` for specific markets. Present
prices as probabilities, preserve venue and outcome labels, and do not claim that
similar titles represent equivalent contracts.

Use `pmxt_series` for venue-native series and `pmxt_order_books` when comparing
multiple known outcome IDs. `pmxt_matched_market_clusters` is the preferred
cross-venue comparison entry point: it returns PMXT relation/confidence evidence,
not title-overlap guesses. Treat any spread as a research lead; contract rules,
fees, liquidity and settlement must still be checked before making a decision.

This bundled native-plugin skill intentionally does not provide trade submission,
cancellation, funding, or wallet operations.
