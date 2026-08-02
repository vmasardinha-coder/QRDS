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
   PowerShell 7 and Windows PowerShell 5.1.
9. Same-input parity completed on the user's Windows machine on 2026-08-02:
   bundle integrity PASS, offline dependency installation PASS, V2A 14/14,
   Delta 15/15, no network actions, no project-file modification, no local
   collection access, no orders and no real capital.
10. Gateway source candidates located by a read-only, no-network scan; names,
    sizes and SHA-256 values were frozen.
11. Current unified package
    `qos_master_pipeline_v1_3_RECONCILED_FULLSET_READY.zip` received. Historical
    v0.9 and v0.2 packages are optional lineage fallbacks, not current inputs.
12. Fresh 2026-08-02 full-output ZIP, review bundle, cumulative PDF and master
    TXT received. Reported master status: technical PASS, data-quality PASS,
    QA PASS_WITH_WARNINGS, `RESEARCH_ONLY`, `NOT_APPROVED`, orders=0, capital=0.
13. Gateway reference identified as `QOS_V2A1_GATEWAY_SCANNER_0.10`, data as of
    2026-08-02, technical PASS, data-quality PASS,
    `SNAPSHOT_USABLE_RESEARCH_ONLY`, no errors and retrospective use prohibited.
14. Binary admission completed: source, full-output and review ZIP integrity
    PASS; expected sizes and SHA-256 values frozen in repository manifests.
15. Canonical source review completed read-only. Exact subtree, dependencies,
    configuration and entrypoint `scripts/00_run_all_v2a1.py` confirmed. No
    formula, weight, threshold, stop or strategy change was made.
16. Canonical offline fixture and output-contract validation PASS locally.
17. Frozen downstream replay from the admitted 2026-08-02 feature snapshot
    PASS locally: selections 118 rows, compositions 132 rows, execution
    profiles 8 rows, Delta stop rules 80 rows and decision log 80 rows.

## Pending before local shutdown

18. Complete the same canonical fixture and frozen downstream replay on GitHub
    Actions and retain the generated TXT, JSON and ZIP evidence.
19. Resolve the explicit upstream-equivalence boundary. The received reference
    package does not include a complete raw-history input snapshot, so public
    source acquisition and feature construction have not been reconstructed or
    claimed equivalent.
20. Enable the daily schedule only after total-system equivalence passes.
21. Produce the single MacroQuant Markdown handoff and retire only
    proven-redundant local routines.

## Current classification

- Structural equivalence: PASS for V2A/Delta.
- Safety equivalence: PASS for V2A/Delta.
- Matched-close V2A/Delta equivalence: PASS.
- User-machine Windows V2A/Delta same-input parity: PASS.
- Gateway binary admission: PASS.
- Gateway source canonicality: PASS.
- Gateway canonical offline fixture: PASS locally.
- Gateway deterministic downstream replay: PASS locally within the admitted
  feature-snapshot scope (118/132/8/80/80).
- Gateway public-source acquisition equivalence: NOT TESTED — complete frozen
  raw-history input snapshot unavailable.
- Gateway feature-construction equivalence: NOT TESTED — complete frozen
  raw-history input snapshot unavailable.
- Total-system equivalence: BLOCKED by remote replay completion and the explicit
  upstream input-snapshot boundary.
- Gateway retrospective performance: PROHIBITED.
- Merge to `main`: NOT AUTHORIZED.
- Cron on `main`: NOT ENABLED.
- Local Google/Windows routine: MUST CONTINUE.

## Immutable boundary

`RESEARCH_ONLY=True`; orders, real capital and operational promotion remain disabled. The workflows have read-only repository permissions and receive no exchange credentials.

The production cadence remains frozen at 21:15 America/Sao_Paulo (00:15 UTC).
The cron must not be enabled on `main` until total-system equivalence passes;
the PR jobs exercise research-only paths without claiming operational approval
or replacing the Google/Windows reference.
