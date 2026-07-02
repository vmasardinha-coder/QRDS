# QRDS/QOS Workspace Cleanup Dry-Run

Sprint 9R creates a controlled dry-run/apply gate for workspace hygiene after the portal/docs inventory and cleanup plan.

Default mode is dry-run only. It classifies exact duplicate wrappers, low-risk cleanup candidates, and medium-risk review items. Low-risk apply requires explicit opt-in through `QRDS_APPLY_LOW_RISK_CLEANUP=1`.

Research-only policy remains active: this report does not unlock any operational market workflow, exchange connection, order generation, account connection, allocation output, or live-fund workflow.

Primary wrappers:

```bash
bash qrds_workspace_cleanup_dry_run.sh
bash qrds_workspace_cleanup_dry_run_serve.sh
```

Optional low-risk apply mode:

```bash
QRDS_APPLY_LOW_RISK_CLEANUP=1 bash qrds_workspace_cleanup_dry_run.sh
```

Approval requires test pass, documentation presence, policy lock active, and git hygiene review.
