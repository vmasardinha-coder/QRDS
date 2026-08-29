# Workflow Operations

Human rule: use **00 VITOR — ACTION REQUIRED** as the only normal manual entrypoint.

Classes:
- `ACTION_REQUIRED`: human action is explicitly queued in `ops/workflow_operations_registry.json`.
- `AUTOMATIC_ONLY`: do not manually dispatch; Factory/schedule/PR automation owns it.
- `RUNTIME_EVIDENCE_DRAFT`: evidence branch only; yellow/red checks do not imply manual action.
- `FAIL_CLOSED_*`: preserve failure as evidence; never rerun merely to force green.
- `SUPERSEDED_*`: historical only; no manual action.

Current queue on 2026-08-29:
1. Stage 9 microstructure manual capture, exactly once, only after PR #301 is fully green and merged.

Known non-actions:
- PR #53 runtime evidence draft: do not merge because of yellow/red checks.
- PR #262 Momentum historical input mismatch: do not force green or rewrite ledger.
- PR #266 H180-H189 Treasury: superseded by later autonomous frontier; historical preregistration evidence only.
- PR #280 mortality audit: reporting-only, non-blocking.
- PR #258 Momentum source clock: superseded operational repair.

Historical Actions runs remain audit evidence. Their existence is not an instruction to rerun them.

Safety boundaries remain `RESEARCH_ONLY=true`, `ORDERS=0`, `REAL_CAPITAL=0`, `ENGINE_FEED=false`; protected H1/prospective partial economics are not opened by this operating layer.
