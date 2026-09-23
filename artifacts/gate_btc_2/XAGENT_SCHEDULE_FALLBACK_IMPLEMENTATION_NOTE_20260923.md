# Implementation note

This repair intentionally reuses the existing `crypto_forward_schedule_guard.py` because that guard is target-workflow agnostic: it inspects active/successful workflow runs and dispatches only when stale. No scientific code is duplicated or changed.

The XAGENT fallback workflow supplies only two operational parameters:
- target workflow: `gate-btc-xagent-disagree-transform.yml`
- freshness threshold: 5400 seconds

The existing XAGENT transform remains the sole source of feature computation and persistence.
