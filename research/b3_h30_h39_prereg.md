# B3 H30-H39 Cross-Asset Pre-registration

Date: 2026-08-23
Status: RESEARCH ONLY — PRE-RESULT
Parent issue: #100

## Isolation
H1 economics are forbidden. Exclusive cutoff: 2026-08-10 America/Sao_Paulo. Orders=0, capital=0, engine_feed=false.

## Data and synchronization
WIN and WDO community Profit continuous exports from the same source already used by H14-H29. Discovery uses 2024_26 5-minute bars. Independent replication uses 2020_22 + 2022_24 15-minute bars. Only exact common timestamps are admitted; no forward fill. Sessions must begin 09:00 and have no internal bar gaps.

## Families
H30 WIN impulse -> WDO response. At 30m and 60m, standardized WIN return >= {1.0,1.5} rolling-session scale; trade WDO next bar in same sign and opposite sign as separately preregistered alternatives; horizons {60,120}m.
H31 WDO impulse -> WIN response. Symmetric to H30.
H32 relative-return divergence convergence. zWIN-zWDO absolute spread >= {1.0,1.5}; trade the relatively lagging leg toward the leader; horizons {60,120}m.
H33 relative-return divergence continuation. Same trigger; trade lagging leg away from leader / continuation alternative; horizons {60,120}m.
H34 relative realized-volatility shock. 60m realized-vol ratio WIN/WDO outside rolling 20-session median ratio by {1.5,2.0}x; trade higher-vol leg in its 60m direction; horizons {60,120}m.
H35 cross-asset confirmation. 30m returns same sign and each standardized magnitude >= {0.5,1.0}; trade each leg separately in confirmed direction; horizon {60,120}m.
H36 cross-asset disagreement fade. 30m signs disagree and both standardized magnitude >= {0.5,1.0}; fade each leg separately; horizons {60,120}m.
H37 opening-sign matrix. Four exact states sign(WIN first30m) x sign(WDO first30m); trade each leg separately according to its own opening sign and inverse alternative; horizon 120m. No matrix cell may be selected after results: all eight leg/direction rules are fixed candidates.
H38 relative VWAP displacement. At 60m compute each asset close-minus-causal-VWAP divided by same-session range; absolute displacement difference >= {0.25,0.50}; trade lagging leg convergence and continuation as separate alternatives; horizon 60m.
H39 equal-weight cross-asset vote. Votes are own 30m sign, other-asset 30m sign, own 60m VWAP side. No fitted weights. Absolute vote >=2; trade each leg separately; horizons {60,120}m.

## Gates
Same gates as H14-H29, applied to the traded leg: minimum 60 trades; reference net edge >0.25 bp/trade; positive under stress cost; positive after one-extra-bar delayed entry; both long and short >=15 and positive; >=2 eligible half-year buckets with >=15 and positive; top-5 positive trades <=40% of positive gross. Family discovery survival requires >=2 qualified cells with parameter/horizon breadth. Replication must independently satisfy the same family survival rule. Maximum 2 final survivors, no forced promotion.

## Costs
WIN reference/stress 2.0/3.0 bp round-trip; WDO 1.5/2.5 bp. Continuous-series cross-level comparisons are forbidden; only scale-invariant returns/ratios/states are used.

## Diagnostics
In addition to economics, report exact synchronized-session counts, common-bar coverage, signal counts by family/leg, rejection reasons, and discovery-vs-replication state. If synchronized coverage is materially deficient, close as DATA_INADEQUATE rather than interpreting economics.
