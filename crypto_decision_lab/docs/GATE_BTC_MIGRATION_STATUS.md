# GATE BTC — QRDS/QOS migration status

The existing Google/Windows routine remains the reference implementation during validation.

Last updated: 2026-08-02.

## Completed

1. Inventory of QRDS/QOS routines and evidence packs.
2. Classification of local-only versus remotely reproducible dependencies.
3. Reproducible Python 3.12 Actions environment and fail-closed safety runner.
4. Branch-triggered remote validation without Codespace usage.
5. Automatic TXT, JSON and ZIP evidence, including error paths.
6. Matched public-data close for 2026-07-31 with deterministic Linux replay:
   V2A 14/14 and Delta 15/15.
7. Linux–Windows same-input semantic parity on GitHub-hosted runners:
   V2A 14/14 and Delta 15/15, with only platform-level floating-point and
   serialization differences below the frozen cross-platform tolerance.
8. One-click offline Windows verifier with fail-closed evidence, tested under
   both PowerShell 7 and Windows PowerShell 5.1.
9. Same-input parity completed on the user's own Windows machine on 2026-08-02:
   bundle integrity PASS, offline dependency installation PASS, V2A 14/14,
   Delta 15/15, no network actions, no project-file modification, no local
   collection access, no orders and no real capital.
10. Canonical Gateway source candidates located on the user's Windows machine
    by a read-only, no-network scan. Exact names, sizes and SHA-256 hashes are
    frozen in `migration/gateway/source_intake_manifest.json`.

## Pending before local shutdown

11. Ingest the five hash-frozen Gateway source/evidence ZIPs and verify name,
    size, SHA-256 and archive integrity before reading or wiring their content.
12. Review the v0.9 → v0.10 lineage and confirm the canonical Gateway/QOS
    calculation entrypoints. No reconstruction by assumption is permitted.
13. Run and compare the admitted Gateway implementation on the same frozen
    2026-07-31 input/date boundary.
14. Enable the daily schedule only after total-system equivalence passes.
15. Produce the single MacroQuant Markdown handoff and retire only
    proven-redundant local routines.

## Current classification

- Structural equivalence: PASS for the implemented V2A/Delta scope.
- Safety equivalence: PASS for the implemented V2A/Delta scope.
- Matched-close V2A/Delta equivalence: PASS.
- User-machine Windows V2A/Delta same-input parity: PASS.
- Gateway: `SOURCE_LOCATED_AWAITING_INGESTION`.
- Gateway source admission: hash manifest committed; file bytes not yet ingested.
- Total-system equivalence: BLOCKED by Gateway ingestion and parity review.
- Merge to `main`: NOT AUTHORIZED.
- Cron on `main`: NOT ENABLED.
- Local Google/Windows routine: MUST CONTINUE.

## Immutable boundary

`RESEARCH_ONLY=True`; orders, real capital and operational promotion remain disabled. The workflow has read-only repository permissions and receives no exchange credentials.

The production cadence remains frozen at 21:15 America/Sao_Paulo (00:15 UTC).
The cron must not be enabled on `main` until total-system equivalence passes;
the PR jobs exercise the public-data paths without claiming operational
approval or replacing the Google/Windows reference.
