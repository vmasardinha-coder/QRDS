# GATE BTC — QRDS/QOS migration status

The existing Google/Windows routine remains the reference implementation during validation.

## Completed

1. Inventory of QRDS/QOS routines and evidence packs.
2. Classification of local-only versus remotely reproducible dependencies.
3. Reproducible Python 3.12 Actions environment and fail-closed safety runner.
4. Branch-triggered remote validation without Codespace usage.
5. Automatic TXT, JSON and ZIP evidence, including error paths.

## Pending before local shutdown

6. Recover and wire the canonical Gateway/QOS calculation entrypoints.
7. Run Google/Windows and GitHub in parallel on matching close dates. The
   fail-closed package comparator is implemented; a fixture run may validate
   structure but can never claim value parity.
8. Compare hashes, observations, compositions, metrics and timestamps. The
   2026-07-31 local package is admitted as the trusted baseline; the matched
   public-data remote-close job is wired into PR validation and its matched
   value-parity result is still pending.
9. Enable the daily schedule only after equivalence passes.
10. Produce the single MacroQuant Markdown handoff and retire only proven-redundant local routines.

## Immutable boundary

`RESEARCH_ONLY=True`; orders, real capital and operational promotion remain disabled. The workflow has read-only repository permissions and receives no exchange credentials.

The production cadence remains frozen at 21:15 America/Sao_Paulo (00:15 UTC).
The cron must not be enabled on `main` until matched-close equivalence passes;
the PR job exercises the same public-data path without claiming operational
approval or replacing the Google/Windows reference.
