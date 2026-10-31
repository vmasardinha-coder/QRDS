# GATE BTC 2.0 — Factory Item 3 reclassification

Autonomous families scanned: **2560**
Latest requalification evidence used: **768** families
Experimental-shadow eligible under frozen Item-2 semantics: **580**

## Classification counts
- `INCONCLUSIVE_BUT_FORWARD_SAFE`: 580
- `VALID_SCIENTIFIC_REJECTION`: 1980

## 512-family question
The canonical requalification queue reports `green_source_family_count=512` and `v3_scope_authorized=512`. Item 3 does not trust the queue's terminal label alone; each latest result is re-read from its actual cell evidence.

## Admission rule
A frozen family is eligible for the experimental lane only when at least two of its three frozen horizon cells are already qualified or fail solely because the evidence is insufficient (`NO_TRADES`, `MIN_TRADES`, or calendar-half insufficiency caused by fewer than two adequately populated half-year buckets). Any hard cost/robustness rejection prevents rescue of that cell. No parameter, sign, threshold, horizon, lookback or cost is changed.

## Grammar 007/008
- Grammar 007 cases: 3; historical rejects remain terminal under the same hypothesis.
- Grammar 008 cases: 24; clean discovery rejects remain terminal; underspecified preregistrations remain invalid until a materially distinct complete preregistration exists.

## Next mechanical step
Bind a prospectively valid B3 M5 source and activate **all** eligible frozen IDs as `EXPERIMENTAL_PROSPECTIVE_SHADOW` together, avoiding post-result cherry-picking. D0 must be the first observation after merged activation; historical credit remains zero.
