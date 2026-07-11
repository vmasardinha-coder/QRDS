# Phase 189 â€” Lightweight CI Research-only

## Gate

```text
PHASE189_LIGHTWEIGHT_CI_RESEARCH_ONLY_READY_RESEARCH_ONLY
```

## Result

```text
Phase status: READY_RESEARCH_ONLY
CI status: LIGHTWEIGHT_CI_READY_RESEARCH_ONLY
Workflow: .github/workflows/qrds-lightweight-research-only.yml
Permissions read-only: True
Python: 3.12
Compile source/tests: True
pytest collect-only: True
Full pytest suite: False
Deployment: False
Repository write permission: False
Secrets: False
Scheduled trigger: False
Full suite: SKIPPED_LOCAL_ECONOMICAL
Operational: BLOCKED_RESEARCH_ONLY
Promotion allowed: False
Decision layer allowed: False
Shadow decision allowed: False
canonical_data_writes: 0
```

## Prerequisite regression state

```json
{
  "phase186_collect_status": "PASS",
  "phase187_integrity_errors": 0,
  "phase188_dependency_errors": 0,
  "phase188_dependency_warnings": 18,
  "phase188_forward_imports": 0,
  "phase188_cycles": 0
}
```

## Workflow validation

```json
{
  "path": ".github/workflows/qrds-lightweight-research-only.yml",
  "exists": true,
  "required_token_count": 15,
  "missing_required_tokens": [],
  "forbidden_token_count": 11,
  "forbidden_hits": [],
  "permissions_read_only": true,
  "uses_python_3_12": true,
  "runs_compileall": true,
  "runs_pytest_collect_only": true,
  "runs_full_test_suite": false,
  "uses_deployment": false,
  "uses_repository_write_permission": false,
  "uses_secrets": false,
  "uses_scheduled_trigger": false
}
```

## CI scope

The workflow runs only lightweight structural checks:

1. install the available test environment;
2. compile source and test files;
3. run `pytest --collect-only -q`;
4. verify research-only environment locks.

It does not run the full test suite, deploy, publish, trade, write repository
content, or use secrets.

## Restrictions

```text
approval_effect: NONE_RESEARCH_ONLY
descriptive_only: True
valid_for_decision: False
full_suite_status: SKIPPED_LOCAL_ECONOMICAL
```

No trading signal, recommendation, allocation, order payload, safe-apply,
operational decision, or canonical data write was generated.
