# B3 H30-H39 V1 Scientific Conclusion

Status: SURVIVORS_READY_FOR_PROSPECTIVE

H1 economics were not read. H1 contamination=false. orders=0. capital=0. engine_feed=false.

Data adequacy passed: discovery synchronized sessions=374 with median common-bar coverage=0.9912280701754386; independent replication synchronized sessions=780 with median common-bar coverage=1.0.

Final family states:
- H30 REJECTED_DISCOVERY
- H31 SURVIVOR_REPLICATED on traded leg WIN
- H32-H39 REJECTED_DISCOVERY

H31 economic thesis: WDO impulse -> WIN response. The replicated direction is the opposite-sign response in WIN after a positive/negative standardized WDO impulse.

Discovery qualified cells:
- WIN | 30_opp_1.0 | 120m: n=175, net@2bp=8.181949 bp/trade, stress@3bp=7.181949, delayed=7.293158, top5=0.153968
- WIN | 30_opp_1.5 | 120m: n=117, net@2bp=6.162855 bp/trade, stress@3bp=5.162855, delayed=4.918815, top5=0.235483

Independent replication qualified cells include:
- WIN | 30_opp_1.5 | 120m: n=252, net@2bp=13.058067, stress@3bp=12.058067, delayed=15.833229, top5=0.123712
- WIN | 60_opp_1.0 | 120m: n=373, net@2bp=7.197523, stress@3bp=6.197523, delayed=6.939928, top5=0.099951
- WIN | 60_opp_1.5 | 60m: n=237, net@2bp=8.403338, stress@3bp=7.403338, delayed=8.837266, top5=0.142086
- WIN | 60_opp_1.5 | 120m: n=237, net@2bp=11.148471, stress@3bp=10.148471, delayed=9.106434, top5=0.131474

Prospective-eligibility rule is frozen to the exact discovery/replication intersection cell, not a post-hoc best cell:
- signal asset: WDO
- observation window: first 30 minutes
- standardized absolute WDO impulse threshold: >=1.5x trailing 20-session median absolute 30m move
- traded asset: WIN
- direction: opposite sign to the WDO impulse
- decision: after the 30m observation; execute next bar open
- holding horizon: 120 minutes
- reference/stress costs: WIN 2.0/3.0 bp round-trip

This rule is ELIGIBLE_FOR_SEPARATE_PROSPECTIVE only. It is not approved for production, sizing, capital, orders, engine feed, or H1 substitution. No H40+ generation should be used to overwrite or retune this frozen candidate.