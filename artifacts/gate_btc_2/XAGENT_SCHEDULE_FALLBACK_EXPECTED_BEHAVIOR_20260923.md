# Expected behavior

The fallback guard is allowed to dispatch the existing XAGENT workflow only when:
1. no target run is active; and
2. the latest successful target run is at least 5400 seconds old.

A fallback dispatch is a current-time prospective observation only. It does not recreate or label a missed timestamp, does not backfill, and earns zero scientific/survivor credit by itself.

The original XAGENT workflow remains the sole producer/persister. The fallback workflow has no runtime write path.
