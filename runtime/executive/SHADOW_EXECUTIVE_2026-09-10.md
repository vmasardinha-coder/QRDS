# GATE BTC — Shadow Executive — 2026-09-10

**Status:** COMPLETE_WITH_EXPLICIT_ND  
**Reference data:** 2026-09-09  
**Boundary:** RESEARCH_ONLY / SHADOW_ONLY / NOT_APPROVED / ORDERS=0 / REAL_CAPITAL=0

## 1. PASSADO

```json
{
  "delta_walk_forward": {
    "freshness": "STALE",
    "observations": 117,
    "source": "runtime/GATE_BTC_MEASUREMENT_STATUS.json",
    "status": "ACTIVE",
    "targets": [
      90,
      120
    ]
  },
  "historical_backfill_counts_as_live": false,
  "historical_policy": "BACKTEST_OR_REPLAY_ONLY; NEVER COUNTED AS PROSPECTIVE LIVE"
}
```

## 2. LIVE FINANCEIRO

```json
{
  "missing_field_count": 24,
  "required_fields": {
    "baseline": {
      "reason": "no canonical financial field in reporting state",
      "source": "runtime/GATE_BTC_REPORTING_CURRENT_STATE.json",
      "status": "NOT_AVAILABLE_NOT_INFERRED",
      "value": "N/D"
    },
    "baseline_version": {
      "reason": "no canonical financial field in reporting state",
      "source": "runtime/GATE_BTC_REPORTING_CURRENT_STATE.json",
      "status": "NOT_AVAILABLE_NOT_INFERRED",
      "value": "N/D"
    },
    "best_day": {
      "reason": "no canonical financial field in reporting state",
      "source": "runtime/GATE_BTC_REPORTING_CURRENT_STATE.json",
      "status": "NOT_AVAILABLE_NOT_INFERRED",
      "value": "N/D"
    },
    "calmar": {
      "reason": "no canonical financial field in reporting state",
      "source": "runtime/GATE_BTC_REPORTING_CURRENT_STATE.json",
      "status": "NOT_AVAILABLE_NOT_INFERRED",
      "value": "N/D"
    },
    "capital_1m_equivalent": {
      "reason": "no canonical financial field in reporting state",
      "source": "runtime/GATE_BTC_REPORTING_CURRENT_STATE.json",
      "status": "NOT_AVAILABLE_NOT_INFERRED",
      "value": "N/D"
    },
    "current_index": {
      "reason": "no canonical financial field in reporting state",
      "source": "runtime/GATE_BTC_REPORTING_CURRENT_STATE.json",
      "status": "NOT_AVAILABLE_NOT_INFERRED",
      "value": "N/D"
    },
    "deltas": {
      "reason": "no canonical financial field in reporting state",
      "source": "runtime/GATE_BTC_REPORTING_CURRENT_STATE.json",
      "status": "NOT_AVAILABLE_NOT_INFERRED",
      "value": "N/D"
    },
    "drawdown": {
      "reason": "no canonical financial field in reporting state",
      "source": "runtime/GATE_BTC_REPORTING_CURRENT_STATE.json",
      "status": "NOT_AVAILABLE_NOT_INFERRED",
      "value": "N/D"
    },
    "es_95": {
      "reason": "no canonical financial field in reporting state",
      "source": "runtime/GATE_BTC_REPORTING_CURRENT_STATE.json",
      "status": "NOT_AVAILABLE_NOT_INFERRED",
      "value": "N/D"
    },
    "es_99": {
      "reason": "no canonical financial field in reporting state",
      "source": "runtime/GATE_BTC_REPORTING_CURRENT_STATE.json",
      "status": "NOT_AVAILABLE_NOT_INFERRED",
      "value": "N/D"
    },
    "fees_custody_cumulative": {
      "reason": "no canonical financial field in reporting state",
      "source": "runtime/GATE_BTC_REPORTING_CURRENT_STATE.json",
      "status": "NOT_AVAILABLE_NOT_INFERRED",
      "value": "N/D"
    },
    "fees_custody_live": {
      "reason": "no canonical financial field in reporting state",
      "source": "runtime/GATE_BTC_REPORTING_CURRENT_STATE.json",
      "status": "NOT_AVAILABLE_NOT_INFERRED",
      "value": "N/D"
    },
    "giveback": {
      "reason": "no canonical financial field in reporting state",
      "source": "runtime/GATE_BTC_REPORTING_CURRENT_STATE.json",
      "status": "NOT_AVAILABLE_NOT_INFERRED",
      "value": "N/D"
    },
    "health_source": {
      "reason": "no canonical financial field in reporting state",
      "source": "runtime/GATE_BTC_REPORTING_CURRENT_STATE.json",
      "status": "NOT_AVAILABLE_NOT_INFERRED",
      "value": "N/D"
    },
    "health_state": {
      "reason": "no canonical financial field in reporting state",
      "source": "runtime/GATE_BTC_REPORTING_CURRENT_STATE.json",
      "status": "NOT_AVAILABLE_NOT_INFERRED",
      "value": "N/D"
    },
    "hwm": {
      "reason": "no canonical financial field in reporting state",
      "source": "runtime/GATE_BTC_REPORTING_CURRENT_STATE.json",
      "status": "NOT_AVAILABLE_NOT_INFERRED",
      "value": "N/D"
    },
    "payoff": {
      "reason": "no canonical financial field in reporting state",
      "source": "runtime/GATE_BTC_REPORTING_CURRENT_STATE.json",
      "status": "NOT_AVAILABLE_NOT_INFERRED",
      "value": "N/D"
    },
    "pl_decomposition": {
      "reason": "no canonical financial field in reporting state",
      "source": "runtime/GATE_BTC_REPORTING_CURRENT_STATE.json",
      "status": "NOT_AVAILABLE_NOT_INFERRED",
      "value": "N/D"
    },
    "sharpe": {
      "reason": "no canonical financial field in reporting state",
      "source": "runtime/GATE_BTC_REPORTING_CURRENT_STATE.json",
      "status": "NOT_AVAILABLE_NOT_INFERRED",
      "value": "N/D"
    },
    "sortino": {
      "reason": "no canonical financial field in reporting state",
      "source": "runtime/GATE_BTC_REPORTING_CURRENT_STATE.json",
      "status": "NOT_AVAILABLE_NOT_INFERRED",
      "value": "N/D"
    },
    "var_95": {
      "reason": "no canonical financial field in reporting state",
      "source": "runtime/GATE_BTC_REPORTING_CURRENT_STATE.json",
      "status": "NOT_AVAILABLE_NOT_INFERRED",
      "value": "N/D"
    },
    "var_99": {
      "reason": "no canonical financial field in reporting state",
      "source": "runtime/GATE_BTC_REPORTING_CURRENT_STATE.json",
      "status": "NOT_AVAILABLE_NOT_INFERRED",
      "value": "N/D"
    },
    "variation": {
      "reason": "no canonical financial field in reporting state",
      "source": "runtime/GATE_BTC_REPORTING_CURRENT_STATE.json",
      "status": "NOT_AVAILABLE_NOT_INFERRED",
      "value": "N/D"
    },
    "worst_day": {
      "reason": "no canonical financial field in reporting state",
      "source": "runtime/GATE_BTC_REPORTING_CURRENT_STATE.json",
      "status": "NOT_AVAILABLE_NOT_INFERRED",
      "value": "N/D"
    }
  },
  "status": "PRESENT_WITH_ND_FIELDS"
}
```

## 3. D50

```json
{
  "component": {
    "authority": "LOCAL_RECONCILED_MEASUREMENT",
    "data_qualification_current": 7,
    "data_qualification_qualified": true,
    "data_qualification_raw_remote": 7,
    "data_qualification_snapshot_count_total": 22,
    "data_qualification_status": "ACTIVE_CONSECUTIVE_PASS_CHAIN_7_OF_7",
    "data_qualification_synchronized_failure": false,
    "display_current": 21,
    "freshness": "STALE",
    "raw_remote_current_for_audit_only": 21,
    "source": "runtime/ledgers/d50/STATUS.json",
    "status": "ACTIVE",
    "target": 30
  },
  "display_counter": {
    "source": "runtime/ledgers/d50/STATUS.json",
    "status": "PRESENT",
    "value": 21
  },
  "target": {
    "source": "runtime/ledgers/d50/STATUS.json",
    "status": "PRESENT",
    "value": 30
  }
}
```

## 4. PROXY REAL

```json
{
  "bull_replay_live_shadow": {
    "data_as_of": "2026-09-08",
    "freshness": "STALE",
    "leaderboard_descriptive_only": [
      {
        "max_drawdown": -0.03678048997585026,
        "net_nav": 1.07241768664,
        "observations": 26,
        "return_since_start": 0.07241768663999992,
        "series": "Delta_LS_70_30"
      },
      {
        "max_drawdown": -0.02732609050741286,
        "net_nav": 1.066545172,
        "observations": 26,
        "return_since_start": 0.0665451720000001,
        "series": "Delta_LS_70_30_StopVol"
      },
      {
        "max_drawdown": -0.03383335938960197,
        "net_nav": 1.03513686433,
        "observations": 26,
        "return_since_start": 0.03513686433000007,
        "series": "Delta_LS_50_50"
      },
      {
        "max_drawdown": -0.02397971140062971,
        "net_nav": 1.03508525507,
        "observations": 26,
        "return_since_start": 0.03508525507000004,
        "series": "Delta_LS_50_50_StopVol"
      },
      {
        "max_drawdown": -0.015473602321982582,
        "net_nav": 1.02610337769,
        "observations": 26,
        "return_since_start": 0.02610337768999993,
        "series": "QOS_Ultra"
      },
      {
        "max_drawdown": -0.007446972520059325,
        "net_nav": 1.02581612495,
        "observations": 26,
        "return_since_start": 0.025816124949999963,
        "series": "Victor_proxy"
      },
      {
        "max_drawdown": -0.007804334180932293,
        "net_nav": 1.02337362475,
        "observations": 26,
        "return_since_start": 0.023373624750000044,
        "series": "QOS_Moderada"
      },
      {
        "max_drawdown": -0.0064207049061093535,
        "net_nav": 1.0139433166,
        "observations": 26,
        "return_since_start": 0.013943316600000033,
        "series": "BTC_ETH_70_30"
      },
      {
        "max_drawdown": -0.008294695074147818,
        "net_nav": 1.01031510963,
        "observations": 26,
        "return_since_start": 0.010315109630000041,
        "series": "BTC_puro"
      }
    ],
    "observed_days": 26,
    "source": "ledgers/bull_replay_live_shadow/STATUS.json",
    "status": "LIVE_DIAGNOSTIC_ACTIVE"
  },
  "claim_boundary": "DESCRIPTIVE_SHADOW_ONLY_NOT_REAL_CAPITAL",
  "proxy_series": "Victor_proxy"
}
```

## 5. PRESERVATION

```json
{
  "canonical_track_present": false,
  "drawdown": {
    "reason": "no dedicated canonical preservation/drawdown source found",
    "status": "NOT_AVAILABLE_NOT_INFERRED",
    "value": "N/D"
  },
  "giveback": {
    "reason": "no dedicated canonical preservation/giveback source found",
    "status": "NOT_AVAILABLE_NOT_INFERRED",
    "value": "N/D"
  },
  "hwm": {
    "reason": "no dedicated canonical preservation/HWM source found",
    "status": "NOT_AVAILABLE_NOT_INFERRED",
    "value": "N/D"
  },
  "note": "Mandatory executive block retained even when evidence is unavailable; values are never inferred.",
  "retention_rule": {
    "reason": "no canonical profit-retention rule source found",
    "status": "NOT_AVAILABLE_NOT_INFERRED",
    "value": "N/D"
  },
  "status": "N/D_NO_CANONICAL_PRESERVATION_TRACK"
}
```

## 6. LIVE ESTRUTURAL

```json
{
  "b3_h1": {
    "backfill_automatically_created": false,
    "economics_locked": true,
    "expected_session_weekday_proxy": "2026-09-09",
    "freshness": "STALE",
    "latest_valid_date": "2026-09-04",
    "source": "ledgers/b3_h1/STATUS.json",
    "status": "ACTIVE_STRUCTURAL_COLLECTION",
    "valid_observation_count": 7
  },
  "h31_tracks": {
    "b3_h31_prospective": {
      "engine_feed": false,
      "health_authority": false,
      "inventory_only": true,
      "ledger_id": "b3_h31_prospective",
      "schema": "gate_btc.b3.h31.prospective_status.v2",
      "sha256": "2aa8dc88dfaa3c1070e2e819f960d292a8c82d16a0dee1d296b44a35582f3479",
      "source": "ledgers/b3_h31_prospective/STATUS.json",
      "status": "ACTIVE_PROSPECTIVE"
    },
    "b3_h31_shadow_paper": {
      "health_authority": false,
      "inventory_only": true,
      "ledger_id": "b3_h31_shadow_paper",
      "schema": "gate_btc.b3.h31.shadow_paper_status.v1",
      "sha256": "0ec9e1db2dd66e01daf0e9c9475335a175ac3a73b6b0d4d7baef46b46024e7ee",
      "source": "ledgers/b3_h31_shadow_paper/STATUS.json",
      "status": "UNKNOWN"
    }
  },
  "v16b": {
    "canonical_cycle_count": 0,
    "entry_seal": "NONE_CANONICAL",
    "freshness": "FRESH",
    "next_canonical_event": null,
    "signal_producer": "IMPLEMENTED_AND_SOURCE_BOUND_BUT_NO_CANONICAL_SIGNAL_CREATED",
    "signal_seal": "NONE_CANONICAL",
    "source": "ledgers/v16b/STATUS.json",
    "status": "TERMINAL_BLOCKED_NOT_PROMOTABLE",
    "v16b_preflight": null,
    "v16b_rehearsal": null
  },
  "v16c": {
    "reason": "V16C declaration/prereg absent",
    "status": "NOT_AVAILABLE_NOT_INFERRED",
    "value": "N/D"
  },
  "v16d": {
    "reason": "V16D declaration absent",
    "status": "NOT_AVAILABLE_NOT_INFERRED",
    "value": "N/D"
  },
  "v16e": {
    "reason": "V16E declaration absent",
    "status": "NOT_AVAILABLE_NOT_INFERRED",
    "value": "N/D"
  }
}
```

## 7. CLOCKS

```json
{
  "d50": {
    "authority": "LOCAL_RECONCILED_MEASUREMENT",
    "data_qualification_current": 7,
    "data_qualification_qualified": true,
    "data_qualification_raw_remote": 7,
    "data_qualification_snapshot_count_total": 22,
    "data_qualification_status": "ACTIVE_CONSECUTIVE_PASS_CHAIN_7_OF_7",
    "data_qualification_synchronized_failure": false,
    "display_current": 21,
    "freshness": "STALE",
    "raw_remote_current_for_audit_only": 21,
    "source": "runtime/ledgers/d50/STATUS.json",
    "status": "ACTIVE",
    "target": 30
  },
  "daily_delivery_pointer": {
    "data_cutoff": "2026-09-09",
    "expected_data_cutoff": "2026-09-09",
    "freshness": "FRESH",
    "lag_days": 0,
    "source": "runtime/GATE_BTC_LATEST_ELIGIBLE_RUN.json",
    "status": "CURRENT"
  },
  "delta_observations": {
    "source": "runtime/GATE_BTC_MEASUREMENT_STATUS.json",
    "status": "PRESENT",
    "value": 117
  },
  "expected_data_cutoff": {
    "source": "runtime/GATE_BTC_REPORTING_CURRENT_STATE.json",
    "status": "PRESENT",
    "value": "2026-09-09"
  },
  "gateway": {
    "freshness": "FRESH",
    "latest_source_data_as_of": "2026-09-09",
    "source": "runtime/ledgers/gateway_dynamics/STATUS.json",
    "status": "ACTIVE",
    "target": 80,
    "valid_snapshot_count": 35
  },
  "qos_monthly": {
    "current": 1,
    "expected_closes": [
      "2026-08-31",
      "2026-09-30",
      "2026-10-31"
    ],
    "freshness": "CURRENT_CALENDAR_GATED",
    "source": "runtime/GATE_BTC_MEASUREMENT_STATUS.json",
    "status": "ACTIVE_CALENDAR_GATED",
    "target": 3
  },
  "reference_data_date": {
    "source": "runtime/GATE_BTC_REPORTING_CURRENT_STATE.json",
    "status": "PRESENT",
    "value": "2026-09-09"
  },
  "reporting_date": "2026-09-10"
}
```

## 8. FUNDO/REGIME

```json
{
  "canonical_regime_source": {
    "reason": "no canonical fund/regime source identified in reporting state",
    "status": "NOT_AVAILABLE_NOT_INFERRED",
    "value": "N/D"
  },
  "policy": "REPORT N/D RATHER THAN INFER MARKET REGIME"
}
```

## 9. RADAR EXTERNO

```json
{
  "empiricus_delta": {
    "canonical_evidence_matches": [],
    "canonical_evidence_status": "ABSENT_NOT_INFERRED",
    "classification": "EXTERNAL_BENCHMARK_REQUIRED_IN_EXECUTIVE_INVENTORY",
    "display_name": "Empiricus Delta",
    "engine_feed": false,
    "inventory_only": true,
    "orders_generated": 0,
    "real_capital_used": 0,
    "requirements_sha256": "682d31727fa2cb9c3f0fd87b4c4f63aea6b27ebfc7e3a450f34894e279324151",
    "requirements_source": "main_repo/tools/gate_btc_executive_reporting_requirements.json",
    "scientific_authority": false,
    "scientific_status": "NOT_INFERRED",
    "source_authority": "OPERATOR_REPORTING_REQUIREMENT",
    "track_id": "empiricus_delta"
  },
  "empiricus_delta_required": true,
  "official_replica_claim": false,
  "other_required_references": {}
}
```

## 10. META 2030

```json
{
  "canonical_meta_2030_source": {
    "reason": "no canonical META 2030 runtime source identified",
    "status": "NOT_AVAILABLE_NOT_INFERRED",
    "value": "N/D"
  },
  "status": "N/D_NOT_INFERRED"
}
```

## 11. LIDERANCA/PUBLICACAO

```json
{
  "delivery_complete": false,
  "freshness_warnings": {
    "blocked_dependency_components": [],
    "failed_delivery_components": [],
    "missing_or_undated_components": [],
    "stale_components": [
      "delta",
      "lock25_50",
      "d50",
      "prl50",
      "alt_trail",
      "bull_replay_live_shadow",
      "b3_h1",
      "momentum_m1_m2"
    ],
    "unrepresented_runtime_ledgers": [
      "b3_h1_inspired_challengers",
      "b3_h31_prospective",
      "b3_h31_shadow_paper",
      "b3_win_wdo_univariate",
      "d100",
      "delta_v12_engine",
      "delta_v12_prices",
      "momentum_m1_m2_economics",
      "qos_three_track",
      "v16_family",
      "v16b1",
      "v16c",
      "v16d",
      "v16e"
    ]
  },
  "headline": "sem fato novo relevante",
  "publication_policy": "FULL_EXECUTIVE_ALWAYS_EMITTED_EVEN_WITH_NO_NEW_HEADLINE",
  "reporting_state_status": "BLOCKED_INCOMPLETE_DELIVERY"
}
```

## 12. GATE BTC 2.0

```json
{
  "declared_tracks": {},
  "momentum": {
    "freshness": "STALE",
    "last_run_state": "NO_NEW_SNAPSHOT_CUTOFF_NOT_PUBLISHED",
    "m1_summary": null,
    "m2_summary": null,
    "methodology_failure": false,
    "observed_snapshots": 15,
    "source": "ledgers/momentum_m1_m2/STATUS.json",
    "status": "WAIT_SOURCE_PUBLICATION"
  },
  "scientific_authority": false,
  "source_discovery": {
    "d100": {
      "health_authority": false,
      "inventory_only": true,
      "ledger_id": "d100",
      "schema": "qrds.d100.forward_collection.v1",
      "sha256": "23d3895e805bb993abe38844bfabd50e842f732bede3d149a37a967d8a4393d3",
      "source": "ledgers/d100/STATUS.json",
      "status": "ACTIVE_FORWARD_COLLECTION"
    },
    "delta_v12_engine": {
      "data_as_of": "2026-09-09",
      "engine_feed": false,
      "health_authority": false,
      "inventory_only": true,
      "ledger_id": "delta_v12_engine",
      "observed_days": 2,
      "orders_generated": 0,
      "promotion_allowed": false,
      "real_capital_used": 0,
      "schema": "gate_btc.delta_v12_engine.v1",
      "sha256": "affb0106766c61f4a1ff995abb6360812e6043ecf3a74af0f0b9c95da2be7af2",
      "source": "ledgers/delta_v12_engine/STATUS.json",
      "status": "ACTIVE_PROSPECTIVE_SHADOW"
    },
    "delta_v12_prices": {
      "engine_feed": false,
      "health_authority": false,
      "inventory_only": true,
      "ledger_id": "delta_v12_prices",
      "schema": "gate_btc.delta_v12_multi_venue_daily_prices.v1",
      "sha256": "7c4d4904d8542f0be32b22e9c09dc2d391a139a6d71de873135cbcb5f665f224",
      "source": "ledgers/delta_v12_prices/COVERAGE.json",
      "status": "NO_CANONICAL_STATUS_FIELD",
      "status_authority_file": "COVERAGE.json",
      "top_level_files": [
        "COVERAGE.json",
        "PINS.json",
        "PRICE_PROVENANCE.json"
      ]
    }
  }
}
```

## 13. FACTORY/EXTERNO

```json
{
  "empiricus_delta_present_in_inventory": true,
  "executive_catalog_summary": {
    "all_track_ids": [
      "alt_trail40_10",
      "b3_h1",
      "b3_h1_inspired_challengers",
      "b3_h31_prospective",
      "b3_h31_shadow_paper",
      "b3_win_wdo_univariate",
      "bull_replay_live_shadow",
      "d100",
      "d50",
      "delta_paper_monitor",
      "delta_v12_engine",
      "delta_v12_prices",
      "empiricus_delta",
      "gateway_dynamics",
      "lock25_50",
      "momentum_m1_m2",
      "momentum_m1_m2_economics",
      "prl50_position",
      "qos_three_track",
      "v16_family",
      "v16b",
      "v16b1",
      "v16c",
      "v16d",
      "v16e"
    ],
    "declared_nonledger_track_count": 0,
    "does_not_authorize_science_or_trading": true,
    "does_not_change_delivery_health": true,
    "ledger_track_count": 24,
    "missing_canonical_reference_ids": [
      "empiricus_delta"
    ],
    "required_reporting_reference_count": 1
  },
  "factory_economics_feedback_allowed": false,
  "inventory_summary": {
    "complete_directory_enumeration": true,
    "component_count": 13,
    "does_not_change_delivery_health": true,
    "inventory_only": true,
    "ledger_count": 24,
    "ledger_ids": [
      "alt_trail40_10",
      "b3_h1",
      "b3_h1_inspired_challengers",
      "b3_h31_prospective",
      "b3_h31_shadow_paper",
      "b3_win_wdo_univariate",
      "bull_replay_live_shadow",
      "d100",
      "d50",
      "delta_paper_monitor",
      "delta_v12_engine",
      "delta_v12_prices",
      "gateway_dynamics",
      "lock25_50",
      "momentum_m1_m2",
      "momentum_m1_m2_economics",
      "prl50_position",
      "qos_three_track",
      "v16_family",
      "v16b",
      "v16b1",
      "v16c",
      "v16d",
      "v16e"
    ],
    "represented_ledger_ids": [
      "alt_trail40_10",
      "b3_h1",
      "bull_replay_live_shadow",
      "d50",
      "delta_paper_monitor",
      "gateway_dynamics",
      "lock25_50",
      "momentum_m1_m2",
      "prl50_position",
      "v16b"
    ],
    "status_authority_candidates": [
      "STATUS.json",
      "CANONICAL_STATUS.json",
      "ECONOMICS_STATUS.json",
      "STATE.json",
      "EVIDENCE_GATE.json",
      "COVERAGE.json"
    ],
    "unrepresented_ledger_ids": [
      "b3_h1_inspired_challengers",
      "b3_h31_prospective",
      "b3_h31_shadow_paper",
      "b3_win_wdo_univariate",
      "d100",
      "delta_v12_engine",
      "delta_v12_prices",
      "momentum_m1_m2_economics",
      "qos_three_track",
      "v16_family",
      "v16b1",
      "v16c",
      "v16d",
      "v16e"
    ]
  },
  "required_external_references": {
    "empiricus_delta": {
      "canonical_evidence_matches": [],
      "canonical_evidence_status": "ABSENT_NOT_INFERRED",
      "classification": "EXTERNAL_BENCHMARK_REQUIRED_IN_EXECUTIVE_INVENTORY",
      "display_name": "Empiricus Delta",
      "engine_feed": false,
      "inventory_only": true,
      "orders_generated": 0,
      "real_capital_used": 0,
      "requirements_sha256": "682d31727fa2cb9c3f0fd87b4c4f63aea6b27ebfc7e3a450f34894e279324151",
      "requirements_source": "main_repo/tools/gate_btc_executive_reporting_requirements.json",
      "scientific_authority": false,
      "scientific_status": "NOT_INFERRED",
      "source_authority": "OPERATOR_REPORTING_REQUIREMENT",
      "track_id": "empiricus_delta"
    }
  },
  "runtime_ledger_count": 24,
  "runtime_ledger_ids": [
    "alt_trail40_10",
    "b3_h1",
    "b3_h1_inspired_challengers",
    "b3_h31_prospective",
    "b3_h31_shadow_paper",
    "b3_win_wdo_univariate",
    "bull_replay_live_shadow",
    "d100",
    "d50",
    "delta_paper_monitor",
    "delta_v12_engine",
    "delta_v12_prices",
    "gateway_dynamics",
    "lock25_50",
    "momentum_m1_m2",
    "momentum_m1_m2_economics",
    "prl50_position",
    "qos_three_track",
    "v16_family",
    "v16b",
    "v16b1",
    "v16c",
    "v16d",
    "v16e"
  ]
}
```

---
Generated from canonical reporting state. Missing evidence is explicitly N/D and never inferred.
