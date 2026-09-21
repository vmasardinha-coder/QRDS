# Jesse standalone conclusion — 2026-09-21

Status: **CONCLUDED / HYPOTHESIS_SOURCE**

Authoritative evidence: workflow run `35602658322`, head `370e443dd0c5a4cdcd44adf28dea267c40833224`, artifact `10638989976`, digest `sha256:2647e7eed185a2d991c9ee8d2c589091510853df59a72e0417d8d7333f3b97ed`.

## What was tested
A clean causal abstraction of the Jesse example-strategy family **Dual Thrust**, without importing the example implementation verbatim because the upstream example appears to use the low column where `down_max_high` should use the high column.

Frozen before the long confirmation and not retuned:
- 1h OKX bars
- up/down windows 21
- coefficients 0.71 / 0.67
- fixed 24h hold
- 20 bps round-trip cost
- BTC, ETH, SOL, XRP
- 8,000 bars, split chronologically in halves

## Long confirmation
| asset | full total | PF | max DD | first half | second half | interpretation |
|---|---:|---:|---:|---:|---:|---|
| BTC | -9.10% | 0.975 | -30.34% | -11.13% | +3.13% | no robust edge |
| ETH | +81.34% | 1.404 | -19.23% | +88.36% | -2.24% | strong but regime-localized |
| SOL | -6.00% | 1.025 | -39.48% | +21.58% | -14.00% | unstable / unacceptable fragility |
| XRP | +22.65% | 1.158 | -29.51% | +6.21% | +18.21% | only asset positive in both halves; modest PF/high DD |

## Scientific decision
- **Dual Thrust is structurally novel enough to retain, but does not yet qualify for Factory migration.**
- Classification: `HOLD_RESEARCH_NOT_MIGRATED`.
- The cross-asset evidence is not broad enough: BTC and SOL fail; ETH is concentrated in the first half; only XRP is directionally persistent, with modest PF and high drawdown.
- No parameter search is authorized merely to rescue the result.
- A future revisit may test the same abstract family on an independent venue/history or use Jesse's strategy corpus to surface a different orthogonal family.

## Permanent role
Jesse remains a **periodic strategy-corpus hypothesis mine**. QRDS remains the final scientific auditor; no Jesse execution engine or strategy code is integrated into Factory.

`RESEARCH_ONLY=true`
`SHADOW_ONLY=true`
