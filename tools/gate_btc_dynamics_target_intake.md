# Dynamics —source-bound target admission

This adapter connects the official Gateway composition files to the accepted spot rebalancer. It does not select a schedule or activate a profile.

The caller supplies the committed Gateway snapshot, its four exact source files, the canonical daily delivery pointer and the producer run ID used to retrieve that source ZIP. The adapter verifies every source-file SHA256 against the snapshot, the public/no-orders source mode, all8 profile identities, profile totals, duplicate fields/rows and source timing. The supplied snapshot/pointer/retrieval context must come from the trusted producer; arbitrary JSON is not independently authenticated by this offline adapter.

Availability is the delivery pointer's published_at_utc, not the earlier scanner run/capture time. The output retains both scanner_data_as_of and producer_market_cutoff; they are different fields and must not be relabeled as the same close.

QOS_Base, Dynamic_Defense and Vol_Target_3 yield explicit decimal target weights including CASH. Only a residual up to1e-12 may be assigned to CASH to account for floating-point serialization dust; the exact correction is disclosed. Market allocations are never rescaled. Material missing allocation, negative spot weights or profile-total mismatches reject admission.

Dynamic_Hedge and the four Delta variants remain DERIVATIVE_EXECUTION_REQUIRED, even when today's particular allocation would be flat or nonnegative. The adapter never interprets a ticker as an instrument identity, the profile's estimated daily drag as observed cost, or a recommended rebalance label as an executable calendar.

spot_weights verifies the admission hash and returns a copy of an admitted target. rebalance_admitted can process an explicit caller decision only with the matching GATE_BTC_DYNAMICS_SPOT_<profile>_V1 SpotProtocol. It carries the source publication time into the unchanged quote-causality checks, links admission/profile into the signal hash and appends a source-binding seal after the atomic rebalance seal.

This function is an offline integration primitive. It does not supply missing exact venue/instrument/lot/cost bindings, schedule/hold/stop/precedence rules, profile activation or a production driver. Fresh post-fill valuation remains mandatory. Profile activation and economic observation counts stay zero in admission outputs.

CLI:

python -m tools.gate_btc_dynamics_target_intake --source-zip <exact-producer-output.zip> --snapshot <committed-snapshot.json> --delivery-pointer <canonical-delivery-pointer.json> --producer-run-id <retrieved-run-id> --output <admission.json>
