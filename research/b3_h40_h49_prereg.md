# B3 H40-H49 Pre-registration

Status: RESEARCH ONLY — PRE-RESULT
Parent: #108

H1 economics and H31 prospective partial economics are forbidden. Historical cutoff is exclusive 2026-08-10 America/Sao_Paulo. Discovery: exact-sync WIN/WDO 2024_26 M5. Independent replication: 2020_22 + 2022_24 M15. Community source commit remains pinned by the H30-H39 loader. Scale-invariant features only; no forward fill.

Frozen families:
- H40 time-of-day cross response: at 120m and 240m, if one asset's return since open exceeds 1.0x or 1.5x trailing-20 median absolute same-horizon move, trade the other asset both same-sign and opposite-sign as separately preregistered alternatives; hold 60/120m.
- H41 overnight gap x first-30m state: gap normalized by prior-session range >=0.25/0.50 on a traded leg, then require first-30m sign same/opposite gap and trade continuation/fade as fixed alternatives; hold 120m.
- H42 range-location transition: 30m close location in session-so-far range <=0.2 or >=0.8 followed by 60m location crossing middle 0.4-0.6; trade transition direction and inverse; hold 60m.
- H43 vol-of-vol shock: current 60m realized volatility / trailing-20 median 60m RV >=1.5/2.0; trade own 60m direction and inverse; hold 60/120m.
- H44 signed-volume surprise proxy: sum(sign(close-open)*volume) over first 60m divided by trailing-20 median absolute proxy >=1.5/2.0; trade sign and inverse; hold 60/120m.
- H45 multi-horizon disagreement: sign(30m return) != sign(60m return), each absolute standardized move >=0.5/1.0; trade 60m sign and 30m sign as distinct alternatives; hold 60/120m.
- H46 opening-bar auction proxy: first-bar body/range >=0.5/0.75 and first-bar range / trailing-20 median first-bar range >=1.5; trade body sign and inverse; hold 60/120m.
- H47 prior-day range interaction: opening gap normalized by prior-day range >=0.25/0.50 and cross-asset prior-day return signs same/opposite; trade gap sign and fade on each leg separately; hold 120m.
- H48 rolling-beta residual: trailing 20-session beta of WIN 30m returns on WDO 30m returns, residual z-score >=1.5/2.0; trade WIN residual convergence and continuation; hold 60/120m.
- H49 fixed equal-weight regime mixture: votes are own 30m sign, own 60m sign, other-asset 30m sign, and inverse high-vol flag when current RV >=1.5x trailing median; absolute vote >=2/3; trade own leg in vote sign; hold 60/120m. No fitted weights.

Gates identical to H30-H39 per traded leg: min 60; net reference edge >0.25 bp/trade; positive stress; positive one-extra-bar delay; both sides >=15 and positive; >=2 half-year buckets with >=15 and positive; top-5 positive contribution <=40%. Family survival requires >=2 qualified cells with parameter/horizon breadth on at least one leg, then independent replication with same rule. Max 2 survivors. Orders=0; capital=0; engine_feed=false.
