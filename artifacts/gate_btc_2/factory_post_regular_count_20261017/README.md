# Prospective regular-grid QA correction

The immutable 2026-10-16 collector receipt records 115 physical M5 bars:
113 regular bars from 09:00 through 18:20, plus 18:25 and 18:30.
Its spacing diagnostics are empty, but the phase gate rejected it because code
hard-coded at most one nonregular bar. The sealed phase contract specifies the
regular interval; it does not impose that hard-coded call/post-regular count.

Starting 2026-10-19 only, validate the full regular grid independently of the
number of nonregular bars. Preserve the existing same-day, sorted/unique,
5-minute-grid, before-19:00 and nonexpired-contract checks on every observed bar.
No missing regular bar is accepted, no row is synthesized or removed, and no
signal, feature, outcome, price or strategy rule is changed.

Decisions through 2026-10-16 retain the previous predicate. Existing immutable
session receipts are not replayed, overwritten or awarded retroactive credit.
The next physical receipt depends on the normal Bridge collector on 2026-10-19.
No MT5 task, schedule, H1/H31 runtime or terminal process was changed.

Validation includes preservation of the 16/10 refusal, future full-grid acceptance
with two nonregular bars, missing regular bars, duplicate/wrong-day/off-grid and
late bars, unchanged 32 intraday feature/window outputs under extreme tail prices,
physical range reconciliation and the collector's deterministic self-test.
