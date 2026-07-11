# Phase 187 â€” Artifact Integrity Scanner 0â€“185

## Gate

```text
PHASE187_ARTIFACT_INTEGRITY_SCANNER_RESEARCH_ONLY_READY_RESEARCH_ONLY
```

## Result

```text
Phase status: READY_RESEARCH_ONLY
Integrity status: ARTIFACT_INTEGRITY_READY_RESEARCH_ONLY
JSON discovered: 111
Target artifacts 0-185: 110
Parsed target artifacts: 110
Integrity errors: 0
Full suite: SKIPPED_LOCAL_ECONOMICAL
Operational: BLOCKED_RESEARCH_ONLY
Promotion allowed: False
Decision layer allowed: False
Shadow decision allowed: False
canonical_data_writes: 0
```

## Method

The scanner reads existing JSON artifacts directly. It does not rebuild prior
phases and does not run the full pytest suite.

Hard integrity checks:

- JSON parseability;
- JSON object root;
- explicit phase versus path phase consistency;
- research-only locks when those fields are present;
- historical `NEEDS_REVIEW` status.

Missing legacy fields are recorded through coverage counts and are not treated
as integrity failures by themselves.

## Contract coverage

```json
{
  "allocation_generated": 109,
  "app_mode": 106,
  "approval_effect": 75,
  "canonical_data_writes": 109,
  "decision_layer_allowed": 109,
  "descriptive_only": 95,
  "edge_operationally_validated": 106,
  "edge_validated": 109,
  "operational_decision_allowed": 109,
  "operational_status": 109,
  "policy_lock": 106,
  "promotion_allowed": 109,
  "recommendation_generated": 109,
  "safe_apply_allowed": 109,
  "shadow_decision_allowed": 109,
  "trading_signal_generated": 109,
  "valid_for_decision": 11
}
```

## Finding counts

```json
{}
```

## Findings preview

```json
[]
```

## Restrictions

```text
approval_effect: NONE_RESEARCH_ONLY
descriptive_only: True
valid_for_decision: False
full_suite_status: SKIPPED_LOCAL_ECONOMICAL
```

No trading signal, recommendation, allocation, order payload, safe-apply,
operational decision, or canonical data write was generated.
