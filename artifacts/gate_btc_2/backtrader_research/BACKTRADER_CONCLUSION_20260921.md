# Backtrader standalone conclusion — 2026-09-21

## Classification

`CONCLUDED / AUDITOR`

Backtrader is retained as an execution-timing / order-lifecycle auditor. It did not produce an economically new alpha family in this test and nothing from its external performance is imported into the Factory.

## Evidence source

Existing successful standalone workflow run: `35606823401`

Artifact: `gate-btc-backtrader-standalone`

Artifact head SHA: `cd7f61bd1372c2395b4bc1c6cba3b1ea9801fc64`

Upstream Backtrader research SHA recorded by the experiment: `b853d7c90b6721476eb5a5ea3135224e33db1f14`

Experiment: `execution_timing_semantics_audit`

Data: BTC/USDT, 1h, 4000 bars, 2026-04-07T22:00:00Z through 2026-09-21T13:00:00Z.

Frozen mechanics: EMA 20/50, start cash 10,000, 0.1% commission per side, 95% sizing.

## Results

| Execution semantic | Final value | Return | Max DD | Order fills |
|---|---:|---:|---:|---:|
| Hypothetical same-close | 11,453.8763 | 14.5388% | -15.6164% | 73 |
| Causal custom next-open | 11,452.5307 | 14.5253% | -15.6208% | 73 |
| Backtrader default market order | 11,786.2226 | 17.8622% | -15.6210% | 67 |

Deltas:

- next-open minus same-close: `-0.013456 pp`
- Backtrader default minus same-close: `+3.323463 pp`
- Backtrader default minus custom next-open: `+3.336919 pp`

## Interpretation

The experiment does **not** support a general claim that same-close execution materially inflated this particular strategy: same-close and custom next-open were nearly identical over this sample.

The material difference came from Backtrader's default order lifecycle / framework semantics. It produced 67 fills instead of 73 and a ~3.34 percentage-point return difference versus the explicit custom next-open implementation, with essentially unchanged max drawdown.

Therefore the useful contribution is methodological: identical-looking strategy logic can yield different economics when the engine's order submission, pending-order handling, fill timing, position state and lifecycle semantics differ.

This is a framework-semantic audit result, not evidence that Backtrader itself improves alpha.

## Factory disposition

No new alpha family is migrated.

No Backtrader numeric result, winner parameter, return, or framework default becomes canonical Factory truth.

The useful finding is already substantially covered by the existing Factory audit gate:

`AUDIT-XEXEC-01 / execution_realism_stress`

Accordingly, Backtrader remains an external independent auditor that can be used for engine-parity checks when a Factory survivor needs a second implementation. No additional Factory migration is required from this run.

## Scientific boundary

- `RESEARCH_ONLY=true`
- `SHADOW_ONLY=true`
- no real capital
- no external performance import
- no parameter retune from this result
- no automatic promotion

## Final status

`Backtrader = CONCLUDED / AUDITOR`

Primary reusable capability: `execution_timing_semantics_audit / engine parity`.
