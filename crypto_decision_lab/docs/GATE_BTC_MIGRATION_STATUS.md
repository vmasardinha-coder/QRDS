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
    by a read-only, no-network scan. Exact names, sizes and SHA-256 hashes were
    frozen in `migration/gateway/source_intake_manifest.json`.
11. The current unified source package
    `qos_master_pipeline_v1_3_RECONCILED_FULLSET_READY.zip` was received in the
    migration conversation. The older v0.9 and v0.2 packages are now optional
    lineage fallbacks rather than mandatory intake inputs.
12. A fresh 2026-08-02 reference run was received with the full output ZIP,
    review bundle, cumulative PDF and master TXT report. The report declares:
    master technical PASS, data-quality PASS, QA PASS_WITH_WARNINGS,
    `RESEARCH_ONLY`, `NOT_APPROVED`, orders=0 and capital=0.
13. The received report identifies Gateway source/output version
    `QOS_V2A1_GATEWAY_SCANNER_0.10`, data as of 2026-08-02, technical PASS,
    data-quality PASS, `SNAPSHOT_USABLE_RESEARCH_ONLY`, no errors and
    `PROHIBITED_CURRENT_COMPOSITION` for retrospective performance.

## Pending before local shutdown

14. Verify the received source, full-output and review ZIP bytes: expected name,
    size and SHA-256 for the unified source, CRC integrity for every archive,
    and newly frozen SHA-256 values for the 2026-08-02 evidence packages.
15. Inspect the unified source read-only and confirm the canonical Gateway/QOS
    entrypoint, configuration, dependencies and output schemas. No
    reconstruction by assumption is permitted.
16. Import only the exact admitted Gateway v0.10 source into the migration
    branch without changing formulas, weights, thresholds, stops or strategy
    logic.
17. Replay the admitted implementation remotely against the 2026-08-02
    reference boundary and compare manifests, profiles, 118 selected rows,
    eight execution profiles and 80 Delta stop-rule rows.
18. Enable the daily schedule only after total-system equivalence passes.
19. Produce the single MacroQuant Markdown handoff and retire only
    proven-redundant local routines.

## Current classification

- Structural equivalence: PASS for the implemented V2A/Delta scope.
- Safety equivalence: PASS for the implemented V2A/Delta scope.
- Matched-close V2A/Delta equivalence: PASS.
- User-machine Windows V2A/Delta same-input parity: PASS.
- Gateway source: `RECEIVED_PENDING_BINARY_ADMISSION`.
- Gateway 2026-08-02 reference evidence: `RECEIVED_PENDING_BINARY_ADMISSION`.
- Gateway reported run status: technical PASS, data-quality PASS,
  `SNAPSHOT_USABLE_RESEARCH_ONLY`, operational `NOT_APPROVED`.
- Gateway retrospective performance: PROHIBITED.
- Total-system equivalence: BLOCKED by binary admission, canonicality review
  and remote Gateway replay; no longer blocked by source discovery.
- Merge to `main`: NOT AUTHORIZED.
- Cron on `main`: NOT ENABLED.
- Local Google/Windows routine: MUST CONTINUE.

## Immutable boundary

`RESEARCH_ONLY=True`; orders, real capital and operational promotion remain disabled. The workflow has read-only repository permissions and receives no exchange credentials.

The production cadence remains frozen at 21:15 America/Sao_Paulo (00:15 UTC).
The cron must not be enabled on `main` until total-system equivalence passes;
the PR jobs exercise the public-data paths without claiming operational
approval or replacing the Google/Windows reference.
