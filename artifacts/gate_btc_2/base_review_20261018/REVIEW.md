# Base review 18 October 2026
H31 recent collector called the imported trailing() while assigning a local variable named trailing later in the same function. Current-session execution failed with UnboundLocalError before the source could be evaluated. Rename only the local selected rows; frozen rules and dates are unchanged.

Regression checks exercise both trigger/no-trigger current sessions and refuse 19 warmup inputs before fetching target data. Baseline source fails the added current-session tests; patched seven-file H31 suite:43 tests and7 subtests pass.

Status exporter separately treated all simulated trigger decisions as closed trades. It now reports the explicit closed count (7 triggers/6 closes fixture) or unknown if absent.

No historical session is replayed for canonical credit. No counter, MT5 process, schedule, order or capital changed. Future date last_frozen_source_session is max(bound calendar),not observed data; it is not a lookahead finding.
