# QRDS/QOS/GATE BTC - Handoff Tecnico - Phase 300

## Environment

- Repository project root: `C:\QRDS\crypto_decision_lab`
- Git root: `C:\QRDS`
- Branch: `main`
- Base commit before the Phase 300 batch: `8dd70e8`
- Python: `C:\QRDS\crypto_decision_lab\.venv\Scripts\python.exe`
- PYTHONPATH: `C:\QRDS\crypto_decision_lab\src`

The final Phase 300 commit is the Git HEAD printed after the batch
push. Do not hard-code a self-referential commit inside this file.

## Network workflow

Before every network action:

1. Stop and print the exact action.
2. Ask Victor to temporarily disable antivirus HTTPS/network
   protection.
3. Require ENTER.
4. Use Git with:
   `-c http.version=HTTP/1.1 -c http.sslBackend=schannel`
5. Remind Victor to re-enable antivirus.

No network action is needed for purely local generation or tests.

## Safety invariants

- `BLOCKED_RESEARCH_ONLY`
- `NO_ACTION_RESEARCH_ONLY`
- `decision_layer_allowed: False`
- `canonical_data_writes: 0`
- No private API.
- No exchange account.
- No order.
- No capital.
- No automatic promotion.
- Position size always zero.

## Current evidence

- Modal hypothesis: `MEAN_REVERSION_LB3_H4_P57`
- Calibration error: `0.10325000000000002`
- Calibration validated: `False`
- Selection stable: `False`
- Severe decay: `False`
- Mean per R$10,000: `-19.71470167962266`
- Lower 95% per R$10,000: `-27.33966593024908`
- Strategy approved: `False`
- Forward shadow eligible: `False`

## Validated test baseline

- Last global checkpoint: Phase 285
- Global test files: `524`
- Global tests: `1431`
- Failures: `0`
- Errors: `0`
- Manifest stable: `True`
- Next mandatory global full-suite: Phase 305

## Phase 300 contracts

- Phase 296: immutable candidate freeze protocol.
- Phase 297: forward-only evidence clock, no historical backfill.
- Phase 298: inactive paper execution and kill-switch contract.
- Phase 299: final visual product-state portal.
- Phase 300: full handoff package.

## Recommended Phases 301-305

- 301: verify official public endpoint specifications and collect a
  substantially longer historical sample.
- 302: add controlled price, volume, volatility, liquidity and
  derivatives-context features with explicit lineage.
- 303: create a finite hypothesis registry v2 with a hard experiment
  budget and multiple-testing controls.
- 304: nested walk-forward robustness, plain-language portal and
  candidate comparison.
- 305: mandatory global full-suite, tracking, snapshot and checkpoint.

Do not assume that additional features create edge. The valid outcome
may still be `NO_ACTION_RESEARCH_ONLY`.
