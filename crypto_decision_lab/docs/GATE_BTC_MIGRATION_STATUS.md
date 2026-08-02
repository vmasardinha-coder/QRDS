# GATE BTC — QRDS/QOS migration status

The existing Google/Windows routine remains active until the migration PR is
explicitly merged and the first scheduled main-branch collection passes.

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
   V2A 14/14 and Delta 15/15 within the frozen cross-platform tolerance.
8. One-click offline Windows verifier tested under PowerShell 7 and Windows
   PowerShell 5.1.
9. User-machine same-input parity completed on 2026-08-02: V2A 14/14, Delta
   15/15, no network actions, no project-file modifications, no local collection
   access, no orders and no real capital.
10. Gateway v0.10 source discovered, admitted and preserved by exact hashes.
11. Unified source package, fresh 2026-08-02 full outputs, review bundle, Master
    PDF and Master TXT admitted with ZIP integrity PASS.
12. Exact Gateway subtree and entrypoint `scripts/00_run_all_v2a1.py` confirmed;
    no formula, weight, threshold, stop, strategy or selection rule changed.
13. Gateway canonical fixture and output contract PASS locally and on GitHub.
14. Frozen downstream replay PASS locally and remotely: 118 selections, 132
    composition rows, 8 execution profiles, 80 Delta stop-rule rows and 80
    decision-log rows.
15. Public-source acquisition was captured end to end in run `30759445898`:
    835 public HTTP responses recorded without credentials or account access.
16. The complete 835-response cassette replayed offline on Linux: 835 consumed,
    zero remaining, semantic parity PASS.
17. The identical cassette replayed offline on Windows: 835 consumed, zero
    remaining, schemas/row order/strings identical and cross-platform numeric
    parity PASS at frozen `rtol=atol=1e-12`; observed maximum differences were
    zero in that run.
18. Gateway total-equivalence decision PASS: source canonicality, public-source
    acquisition, raw/filtered/feature construction, downstream portfolio
    construction, output contract and safety locks all passed.
19. Total-system equivalence frozen as PASS for the research-only migration
    scope: V2A, Delta and Gateway functional, structural, safety and same-input
    equivalence are complete.
20. Daily research collection prepared for 00:15 UTC / 21:15
    America/Sao_Paulo. It dynamically selects the most recent completed UTC
    close, runs V2A, Delta and Gateway, fails closed, and uploads dated evidence.
21. The daily reporting contract is frozen at exactly three Shadow PDFs:
    Master Analytic, Comparativos Completos and Profit Preservation. Auxiliary
    TXT files are not a fourth Shadow report.
22. Full pre-deployment daily branch run `30759775067` completed successfully.
    Data cutoff was 2026-08-01; V2A PASS, Delta PASS, Gateway upstream PASS,
    Gateway downstream PASS, 835 HTTP responses captured and 835 replayed,
    zero orders, zero real capital and methodology changes zero. The handoff
    result was `PASS_WITH_DATA_WARNINGS` because Gateway reported documented
    partial public-source redundancy; report delivery inputs were READY.
23. Daily evidence artifact `8837195468`, named
    `gate-btc-daily-research-30759775067`, was retained for 30 days with size
    22,720,280 bytes and SHA-256
    `2fd589c41c09f6ba71f4b434941b84fcdd9b248a7fb9e9d2234a82176bd024d8`.

## Current classification

- V2A structural, matched-close and same-input equivalence: **PASS**.
- Delta structural, matched-close and same-input equivalence: **PASS**.
- Gateway binary admission and source canonicality: **PASS**.
- Gateway public-source acquisition equivalence: **PASS**.
- Gateway feature-construction equivalence on Linux and Windows: **PASS**.
- Gateway deterministic downstream equivalence: **PASS**.
- Safety equivalence: **PASS**.
- `TOTAL_SYSTEM_EQUIVALENCE`: **PASS_RESEARCH_ONLY**.
- Pre-deployment daily branch execution: **PASS_WITH_DATA_WARNINGS**.
- Runtime public-source quality may be `PASS` or a documented partial-redundancy
  warning. A warning remains reportable only with explicit disclosure;
  technical failure fails closed.
- Gateway current-composition retrospective performance: **PROHIBITED**.
- Operational approval: **NOT_APPROVED**.
- Merge to `main`: **NOT AUTHORIZED YET**.
- Cron file: **PREPARED IN DRAFT PR, NOT ACTIVE ON MAIN**.
- Automatic Chat delivery of the three PDFs: **NOT ACTIVE YET**.
- Local Google/Windows routine: **MUST CONTINUE UNTIL MERGE AND FIRST SCHEDULED
  MAIN-BRANCH PASS**.

## Remaining irreversible decision

All reversible technical migration and pre-deployment validation work is now
complete. The next step requiring explicit user authorization is to merge draft
PR #3 into `main`. That merge activates the prepared daily schedule on the
default branch. After the first scheduled collection passes, automatic delivery
of the three Shadow PDFs can be activated and only then may any Google/local
routine be classified as redundant.

MacroQuant remains a separate later consolidation. It is not mixed into this
migration and does not block the current research-only equivalence decision.

## Immutable boundary

`RESEARCH_ONLY=True`; orders, real capital and operational promotion remain
disabled. Workflows use read-only repository permissions and receive no exchange
credentials. A research-equivalence PASS is not a promise of profit and is not
an authorization to trade.
