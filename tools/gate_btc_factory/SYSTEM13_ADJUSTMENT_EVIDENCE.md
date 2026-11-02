# System13: documented factor at the governed import boundary

The frozen panel protocol requires reviewed corporate-action/tradability evidence,
a numeric factor, native units, and qualification before the future session opens.
The importer does not grant source admission or derive a factor.

The hash-bound `adjustment_evidence` JSON must identify the admission's `source_id`
and `adjustment_policy`. Its `factor_intervals` contain reviewed rows with:

- `coin_id`, exact `venue_instrument`, literal `quote_currency`, `volume_unit`;
- a finite positive JSON number `factor` (no implicit 1 and no Boolean);
- `valid_from_utc`, `valid_to_utc`, covering the entire bar interval;
- `evidence_available_at_utc`, no later than source qualification;
- `official_source_url`, `source_locator` identifying the reviewed statement;
- `official_source_path`, `official_source_sha256`, binding the preserved original
  document bytes inside the supplied bundle (HTML/PDF/text accepted as bytes).

Exactly one reviewed interval must cover an imported instrument/session. The bar's
factor must equal that interval's numeric factor. Document hashes, source/policy,
native units, membership, admission time and bar clock are checked independently.
External documentary review remains responsible for interpreting and authenticating
the official statement; field presence is not proof of its substantive correctness.

On 2026-11-02, a regression fixture demonstrated that the previous importer accepted
factor=7 with a hash-bound document containing no numeric factor. This is a missing
implementation of the existing evidence requirement, not a new scientific gate.
The fix awards no admission, session, model, outcome, or scientific credit. Existing
native captures, binding population, historical panels and partitions are unchanged.
