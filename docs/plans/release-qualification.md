# Release qualification: SDK + native plugin + skill

Status: research plan; no CI changes or release authorization implied.

## Existing CI gap, reproduced

Current workflow runs `pytest -q -m unit`: collection contains 32 tests.
`pytest --collect-only -q -m 'not integration and not trading'` contains 42.
The ten additional tests are all in tests/test_exchanges.py:

- TestCreateExchangeMocked: limitless/polymarket_us/polymarket credential wiring,
  unknown exchange handling.
- TestExchangeList: known exchanges and trading exchanges.
- TestIsPmxtAvailable: boolean availability result.
- TestNormalizeExchangeName: aliases, unknown names, known-name preservation.

Thus green CI currently omits offline exchange-wiring coverage. Fix either marker
assignment or the CI selection, with a collection assertion preventing recurrence.
The wrapper summary for collect-only misleadingly printed 'No tests collected';
raw subprocess capture confirmed successful collection of 32 and 42 node IDs.

## Required release lanes

1. Fast offline: complete non-network/non-trading suite plus lint. Every test
   classified; CI must not silently omit unmarked offline tests.
2. SDK contract: qualified pmxt versions at supported range boundaries. Validate
   exact signatures and response models with realistic objects, not permissive
   mocks. Report installed dependency versions.
3. Packaging: build wheel and sdist; twine check; wheel install outside checkout;
   assert import origin, entry point, bundled skill, metadata/version agreement.
4. Hermes adapter: isolated host/profile, actual PluginManager discovery and
   dispatch, missing config, disabled plugin, no duplicate registration, no network
   at registration. Record a pinned host revision. No hidden live-profile edits.
5. Compatibility: upstream scanner with positive control and nonempty manifest;
   latest target revision qualification before release. Zero findings alone is
   not a discovery or execution test.
6. Live reads: opt-in bounded test with a real configured backend; verify result
   values/IDs, not only success booleans. No real orders, funding or cancellation.
7. Release: new immutable version, owner approval, main-only OIDC publisher,
   then exact PyPI readback and fresh installed-package smoke.

## CI/release policy

Retain publishing restricted to main. PRs run validation but cannot mint release
authority. Put id-token: write only on the publish job. Do not publish on a PR or
from an unreviewed external workflow invocation.

Current skip-existing avoids duplicate-upload errors but is not a release gate:
existing PyPI files are immutable and may differ from freshly built files of the
same name. Before a new release, require the intended version to be absent and
verify the final published files. For an already released version, make the skip
explicit rather than claiming changed metadata was published.

Keep core SDK minimum Python support separate from the Python versions required
by the qualified Hermes host. Add host testing on supported interpreters rather
than assuming the current 3.10/3.11/3.12 SDK matrix proves plugin compatibility.

## Release decision

Do not bump dependency minimum or package version until upstream research defines
the supported API contract. Candidate full native-plugin release: 0.4.0. A 0.3.1
maintenance release is optional, not a prerequisite if 0.4.0 can be qualified.

Release remains blocked until the upstream API audit, implementation, complete
qualification, and explicit owner publishing approval are complete.
