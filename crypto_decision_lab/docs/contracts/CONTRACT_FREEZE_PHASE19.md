# QRDS Contract Freeze — Phase 19 / Sprint 7A

## Purpose

This document freezes the research-only contract after Phase 19.

The system is still:

`INTERACTIVE_RESEARCH_ONLY`

## Frozen unsafe flags

These flags must never be `True` in research artifacts:

```text
operational_decision_allowed
api_key_required
api_key_present
account_connection_required
authenticated_connection_used
orders_generated
real_orders_generated
real_capital_used
orders_allowed
trading_signal_generated
executable_signal_generated
recommendation_generated
```

Older artifacts may not expose every extended flag yet. That is acceptable.
But if any of them is present and `True`, the artifact is unsafe.

## Canonical safety stamp

New modules should use:

```python
build_research_safety_stamp()
```

New artifact checks should use:

```python
assert_research_only_artifact()
collect_research_contract_issues()
build_integration_health_report()
```

## Rule

Sprint 7A does not refactor all previous modules.
It adds the central contract layer and canonical health test first.

Future refactors can migrate repeated safety stamps into this contract module.
