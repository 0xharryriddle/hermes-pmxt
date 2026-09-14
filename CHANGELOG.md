# Changelog

## 0.4.0

- Add a native Hermes plugin distributed through the `hermes_agent.plugins` entry-point group.
- Bundle the namespaced `hermes-pmxt:pmxt` skill inside the wheel.
- Expose seven curated read-only native tools: diagnostics, venues, market/event
  search, series, batch order books, and Router matched-market clusters.
- Qualify against PMXT 2.54.x and add Hunch plus current PMXT class mappings.
- Use PMXT Router relation/confidence data for native cross-venue research rather
  than title-overlap guesses.
- Preserve N-way outcome IDs and serialize PMXT model objects before shaping.
- Fix hosted/custom client construction so it does not require a local sidecar.
- Harden legacy SDK write helpers: explicit confirmation, `order_type`, and
  opaque one-time submission tokens instead of caller-created BuiltOrder dicts.
- Expand CI to run all offline non-trading tests.

The native plugin deliberately excludes order submission, cancellation, funding,
and wallet operations. The legacy Python SDK write helpers have a separate,
caller-controlled authorization boundary and are not native plugin tools.

## 0.3.0

- Initial lazy import, configuration, result shaping, registry, and safety-gate release.
