# Source-readiness audit and reporting continuity — 23 October 2026

The observed System13 panel advanced to 76 snapshots. Its latest verified
observation has 250 members, of which 215 pass the existing observed flags/quote
checks. The existing V2A registry provides exact coin-ID source candidates for
91: Binance 48, OKX 41, Gate 1 and Kraken 1. This is 42.3256% candidate coverage.
The unchanged 80% requirement needs 172 covered assets: at least 81 additional
exact bindings, followed by source-specific OHLCV/tradability/adjustment review.
The absolute 50-asset minimum does not replace the 80% requirement.

These are identity candidates, not System13-admitted sources or ready bars.
Ninety instruments carry a literal USDT quote suffix, one USD; no parity
conversion is assumed. The existing USD import boundary remains unchanged.
Registry authority for another study is not transferred. Training and holdout
remain blocked and scientific credit is zero. Missing and excluded members
remain visible in the output.

The audit is now part of the existing isolated panel workflow and publication
scope. SOURCE_READINESS.json is exported as its own track. Factory export
refreshes after successful M3 or panel/F-X delivery, so the repaired underlying
states need not wait for a delayed hourly schedule. Runtime checkout requires
only the current commit and status files rather than full branch history and
raw archives. The isolated panel checkout also requests only its input/output
namespaces. Superseded read-only PR checks can be cancelled; canonical writers
remain serialized without cancellation. Publication still
recomputes after competing writers and touches only the derived status file.

The separately received local 23 October pressure-valve report adds legacy
results through 12:35 BRT. Cumulative reference net bps at 30/60/120 minutes:

| Family | Trades per horizon | 30 min | 60 min | 120 min |
|---|---:|---:|---:|---:|
| H474 | 7 | +24.6657 | +44.9014 | -73.4966 |
| H478 | 8 | +43.3590 | +141.6360 | -124.8495 |
| H626 | 6 | +20.5520 | -45.9211 | -147.9935 |

H478 60-minute cumulative stress result is +133.6360 bps and delayed-entry
result +101.6159 bps. These describe a small observed sample, not a chosen or
approved strategy. Horizon outcomes are alternatives, not independent trades;
summed trade bps are not compounded portfolio returns.

The new autopsy contains intraday supervisor statuses only. Its final records
show H31 eight closed local trades and three canonical eligible observations,
and both Inspired V2 challengers closed. It contains no new expanded-580 daily
result or basket close. Therefore expanded-family and five/ten-family basket
results retain their separate 22 October cut; no 23 October result is invented.

REVIEW_FACTS.json records hashes, exact metrics and the reviewed source cut.
Local validation: six source-readiness tests and eight exporter tests passed,
including a real sparse clone preserving all exported tracks while omitting raw archives.
