# GATE BTC — Shadow Executive — 2026-10-26

**Status:** COMPLETE_WITH_EXPLICIT_ND  
**Reference data:** 2026-10-25  
**Boundary:** RESEARCH_ONLY / SHADOW_ONLY / NOT_APPROVED / ORDERS=0 / REAL_CAPITAL=0

## 1. PASSADO

```json
{
  "delta_walk_forward": {
    "freshness": "FRESH",
    "observations": 164,
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
    "data_qualification_current": 14,
    "data_qualification_qualified": true,
    "data_qualification_raw_remote": 14,
    "data_qualification_snapshot_count_total": 86,
    "data_qualification_status": "ACTIVE_CONSECUTIVE_PASS_CHAIN_14_OF_7",
    "data_qualification_synchronized_failure": false,
    "display_current": 85,
    "freshness": "FRESH",
    "raw_remote_current_for_audit_only": 85,
    "source": "runtime/ledgers/d50/STATUS.json",
    "status": "ACTIVE",
    "target": 120
  },
  "display_counter": {
    "source": "runtime/ledgers/d50/STATUS.json",
    "status": "PRESENT",
    "value": 85
  },
  "target": {
    "source": "runtime/ledgers/d50/STATUS.json",
    "status": "PRESENT",
    "value": 120
  }
}
```

## 4. PROXY REAL

```json
{
  "bull_replay_live_shadow": {
    "active_epoch": "epochs/independent_20261009",
    "anchor_date": "2026-10-09",
    "can_append": false,
    "collection_health_hint": "GREEN_ACTIVE",
    "data_as_of": "2026-10-25",
    "engine_feed": false,
    "expected_source_data_as_of": "2026-10-26",
    "first_return_date": "2026-10-10",
    "formal_prospective_evidence": false,
    "freshness": "CURRENT_CALENDAR_GATED",
    "inherited_scientific_credit": 0,
    "not_approved": true,
    "observed_days": 16,
    "orders_generated": 0,
    "original_last_observation_date": "2026-09-08",
    "original_observed_days_preserved": 26,
    "original_status": "INTERRUPTED_DESCRIPTIVE_ONLY",
    "real_capital_used": 0,
    "research_only": true,
    "retrospective_backfill": false,
    "schema": "gate_btc.bull_replay_live_shadow.delivery.v1",
    "scientific_credit": 0,
    "shadow_only": true,
    "source": "ledgers/bull_replay_live_shadow/DELIVERY_STATUS.json",
    "status": "WAITING_NEXT_DAILY_CLOSE",
    "updated_at_utc": "2026-10-26T05:18:39.971254+00:00"
  },
  "c4_reference": {
    "approximate": true,
    "collection_paused_by_reference_freeze": false,
    "comparison_updates_enabled": true,
    "dates_of_trajectory_marks": null,
    "historical_trajectory_brl": [
      180000,
      220000,
      200000
    ],
    "new_real_mark_policy": "APPEND_OBSERVED_MARK_WITH_DATE; NEVER_REPLACE_WITH_PROXY",
    "proxy_evidence_status": "PRESENT",
    "real_vs_proxy_delta": {
      "reason": "requires observed real marks on matching dates",
      "status": "NOT_AVAILABLE_NOT_INFERRED",
      "value": "N/D"
    },
    "reference_balance_brl": 200000,
    "reference_is_current_daily_valuation": false,
    "reference_status": "USER_REPORTED_APPROXIMATE_BASELINE_RETAINED"
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
    "backfill_automatically_created": null,
    "canonical_checkpoint_count": 18,
    "counter_scope": "CANONICAL_CHECKPOINT",
    "economics_locked": true,
    "expected_session_weekday_proxy": "2026-10-23",
    "freshness": "FRESH",
    "latest_valid_date": "2026-10-23",
    "remaining": 2,
    "source": "ledgers/b3_h1/CANONICAL_STATUS.json",
    "status": "H1_18_OF_20_CANONICAL",
    "structural_observation_count": 13,
    "valid_observation_count": 18
  },
  "h31_tracks": {
    "b3_h31_prospective": {
      "engine_feed": false,
      "health_authority": false,
      "inventory_only": true,
      "ledger_id": "b3_h31_prospective",
      "schema": "gate_btc.b3.h31.prospective_status.v2",
      "sha256": "7ac444a10af60950b0b9174877c7e74b143b17e6a6f7875fb687b09014d49953",
      "source": "ledgers/b3_h31_prospective/STATUS.json",
      "status": "ACTIVE_PROSPECTIVE"
    },
    "b3_h31_shadow_paper": {
      "health_authority": false,
      "inventory_only": true,
      "ledger_id": "b3_h31_shadow_paper",
      "schema": "gate_btc.b3.h31.shadow_paper_status.v1",
      "sha256": "13d35084897d4c1e0384ad8f5a0831ef9b04cc8dd4828375a58101340c277bc7",
      "source": "ledgers/b3_h31_shadow_paper/STATUS.json",
      "status": "UNKNOWN"
    }
  },
  "v16b": {
    "canonical_cycle_count": 0,
    "entry_seal": "NONE_CANONICAL",
    "freshness": "CLOSED_NOT_APPLICABLE",
    "next_canonical_event": null,
    "signal_producer": "IMPLEMENTED_AND_SOURCE_BOUND_BUT_NO_CANONICAL_SIGNAL_CREATED",
    "signal_seal": "NONE_CANONICAL",
    "source": "ledgers/v16b/STATUS.json",
    "status": "TERMINAL_BLOCKED_NOT_PROMOTABLE",
    "terminal_disposition": "CLOSED_FAIL_CLOSED_EXTERNAL_ENTRY_INFRASTRUCTURE_BLOCK",
    "v16b_preflight": null,
    "v16b_rehearsal": null
  },
  "v16b1": {
    "display_name": "V16B.1",
    "economics_authority": false,
    "health_authority": false,
    "inventory_only": true,
    "ledger_ids_expected": [
      "v16b1",
      "v16b_1"
    ],
    "parent": {
      "record": {
        "canonical_cycle_count": 0,
        "data_as_of": "2026-09-09",
        "engine_feed": false,
        "health_authority": false,
        "inventory_only": true,
        "ledger_id": "v16b",
        "orders_generated": 0,
        "promotion_allowed": false,
        "real_capital_used": 0,
        "schema": "gate_btc.v16b.status.v1",
        "sha256": "96cbcc0287cd8ba64bc7df42d42f63c5d04fbf1f6c27cdd74702d94e7e57de9e",
        "source": "ledgers/v16b/STATUS.json",
        "status": "TERMINAL_BLOCKED_NOT_PROMOTABLE"
      },
      "reporting_role": "TERMINAL_PARENT_NOT_REOPENED",
      "source_status_preserved": true,
      "track_id": "v16b"
    },
    "promotion_authority": false,
    "records": {
      "v16b1": {
        "canonical_cycle_count": 0,
        "data_as_of": "2026-09-09",
        "engine_feed": false,
        "health_authority": false,
        "inventory_only": true,
        "ledger_id": "v16b1",
        "orders_generated": 0,
        "promotion_allowed": false,
        "real_capital_used": 0,
        "schema": "gate_btc.v16b1.status.v1",
        "sha256": "a91c84afccc170e82f201acf98b87413efd67af650953db09abce95438c8aa23",
        "source": "ledgers/v16b1/STATUS.json",
        "status": "PROSPECTIVE_ORCHESTRATOR_ACTIVE"
      }
    },
    "representation_status": "PRESENT_RUNTIME_LEDGER",
    "scientific_authority": false,
    "semantic_id": "v16b1"
  },
  "v16c": {
    "reason": "V16C declaration/prereg absent",
    "status": "NOT_AVAILABLE_NOT_INFERRED",
    "value": "N/D"
  },
  "v16c1": {
    "display_name": "V16C.1",
    "economics_authority": false,
    "health_authority": false,
    "inventory_only": true,
    "ledger_ids_expected": [
      "v16c1",
      "v16c_1"
    ],
    "parent": {
      "record": {
        "canonical_cycle_count": 0,
        "health_authority": false,
        "inventory_only": true,
        "ledger_id": "v16c",
        "schema": "gate_btc.v16c.status.v1",
        "sha256": "181f83b8815b9822d242ddb395e45eb8b103729f578614a6a9cc11ddfb418d91",
        "source": "ledgers/v16c/STATUS.json",
        "status": "PREREGISTERED_WAIT_CAUSAL_PROSPECTIVE_LEDGER"
      },
      "reporting_role": "FROZEN_BLOCKED_PARENT",
      "source_status_preserved": true,
      "track_id": "v16c"
    },
    "promotion_authority": false,
    "records": {},
    "representation_status": "ABSENT_NOT_INFERRED",
    "scientific_authority": false,
    "semantic_id": "v16c1"
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
    "data_qualification_current": 14,
    "data_qualification_qualified": true,
    "data_qualification_raw_remote": 14,
    "data_qualification_snapshot_count_total": 86,
    "data_qualification_status": "ACTIVE_CONSECUTIVE_PASS_CHAIN_14_OF_7",
    "data_qualification_synchronized_failure": false,
    "display_current": 85,
    "freshness": "FRESH",
    "raw_remote_current_for_audit_only": 85,
    "source": "runtime/ledgers/d50/STATUS.json",
    "status": "ACTIVE",
    "target": 120
  },
  "daily_delivery_pointer": {
    "data_cutoff": "2026-10-25",
    "expected_data_cutoff": "2026-10-25",
    "freshness": "FRESH",
    "lag_days": 0,
    "source": "runtime/GATE_BTC_LATEST_ELIGIBLE_RUN.json",
    "status": "CURRENT"
  },
  "delta_observations": {
    "source": "runtime/GATE_BTC_MEASUREMENT_STATUS.json",
    "status": "PRESENT",
    "value": 164
  },
  "expected_data_cutoff": {
    "source": "runtime/GATE_BTC_REPORTING_CURRENT_STATE.json",
    "status": "PRESENT",
    "value": "2026-10-25"
  },
  "gateway": {
    "freshness": "FRESH",
    "latest_source_data_as_of": "2026-10-26",
    "source": "runtime/ledgers/gateway_dynamics/STATUS.json",
    "status": "ACTIVE",
    "target": 80,
    "valid_snapshot_count": 79
  },
  "qos_monthly": {
    "current": 2,
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
    "value": "2026-10-25"
  },
  "reporting_date": "2026-10-26"
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
    "blocked_dependency_components": [
      "v16b1"
    ],
    "failed_delivery_components": [],
    "missing_or_undated_components": [],
    "semantic_projection_ledger_ids": [
      "d100",
      "delta_v12_engine",
      "delta_v12_prices",
      "qos_three_track",
      "v16b1"
    ],
    "stale_components": [
      "v16b1"
    ],
    "unrepresented_runtime_ledgers": [
      "b3_h1_inspired_challengers",
      "b3_h31_prospective",
      "b3_h31_shadow_paper",
      "b3_win_wdo_univariate",
      "delta_v13_engine",
      "momentum_canonical_net",
      "momentum_cost_sensitivity",
      "momentum_m1_m2_economics",
      "momentum_m3",
      "momentum_m3_economics",
      "v16_family",
      "v16c",
      "v16d",
      "v16e"
    ],
    "unrepresented_runtime_ledgers_component_only": [
      "b3_h1_inspired_challengers",
      "b3_h31_prospective",
      "b3_h31_shadow_paper",
      "b3_win_wdo_univariate",
      "delta_v12_engine",
      "delta_v12_prices",
      "delta_v13_engine",
      "momentum_canonical_net",
      "momentum_cost_sensitivity",
      "momentum_m1_m2_economics",
      "momentum_m3",
      "momentum_m3_economics",
      "v16_family",
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
    "collection_health_hint": "GREEN_CLOSED",
    "cost_status": "N_D",
    "economic_epoch_id": "hold_20260928",
    "economic_freshness": "CLOSED_NOT_APPLICABLE",
    "economic_gaps": [],
    "economic_nav": {
      "M1_TOP10": 1.0100180724250019,
      "M2_TOP10": 1.0033364399022817
    },
    "economic_status": "CLOSED_RULE_VERSION_SUPERSEDED",
    "economics_source": "ledgers/momentum_m1_m2_economics/epochs/hold_20260928/DELIVERY_STATUS.json",
    "first_eligible_economic_cutoff": "2026-09-28",
    "freshness": "FRESH",
    "last_economic_cutoff": "2026-10-19",
    "last_run_state": null,
    "latest_economics": {
      "btc_daily_return_gross": -0.002162794096156717,
      "btc_nav": 0.9793786214946847,
      "cost_status": "N_D",
      "cutoff": "2026-10-19",
      "daily_return_gross": {
        "M1_TOP10": 0.011286670272169008,
        "M2_TOP10": 0.014354719234347835
      },
      "event": "HOLD",
      "evidence": {
        "price_manifest_sha256": "b43986be9f6cb02c98a775112699a2f76e728a0d2d43c8623cf510279dcfb680",
        "snapshot_sha256": "f34a54463eea176a8644a1e18ac64082200a170fffe05969b5b69722d2a42f28",
        "source_available_at_utc": "2026-10-20T08:52:35.310532+00:00"
      },
      "excess_vs_btc_percentage_points": {
        "M1_TOP10": 3.063945093031717,
        "M2_TOP10": 2.395781840759703
      },
      "holdings_after_close": {
        "M1_TOP10": [
          "STRK",
          "BTW",
          "DRV",
          "NIGHT",
          "CARDS",
          "ZRO",
          "GRASS",
          "KAIA",
          "TIA",
          "MET"
        ],
        "M2_TOP10": [
          "ZRO",
          "NIGHT",
          "STRK",
          "BTW",
          "GRASS",
          "DRV",
          "KCS",
          "CARDS",
          "RENDER",
          "AERO"
        ]
      },
      "illustrative_brl_pnl": {
        "M1_TOP10": 1803.253036500334,
        "M2_TOP10": 600.5591824107092
      },
      "illustrative_brl_value": {
        "M1_TOP10": 181803.25303650033,
        "M2_TOP10": 180600.5591824107
      },
      "nav": {
        "M1_TOP10": 1.0100180724250019,
        "M2_TOP10": 1.0033364399022817
      },
      "net_return": null,
      "observed_at_utc": "2026-10-20T08:52:35.526366+00:00",
      "quantities_after_close": {
        "M1_TOP10": {
          "BTW": 0.052338407518072914,
          "CARDS": 0.3979796028543003,
          "DRV": 0.24172107751051025,
          "GRASS": 0.1513646331521116,
          "KAIA": 2.328562533459457,
          "MET": 0.2827066601585517,
          "NIGHT": 2.4602293944412827,
          "STRK": 1.2815017932322053,
          "TIA": 0.1903600885815732,
          "ZRO": 0.05430610781663278
        },
        "M2_TOP10": {
          "AERO": 0.12121764539621448,
          "BTW": 0.052527907757940355,
          "CARDS": 0.39942055671169835,
          "DRV": 0.2425962704011889,
          "GRASS": 0.15191267493729332,
          "KCS": 0.013966333872837881,
          "NIGHT": 2.469137079685901,
          "RENDER": 0.05463858173841333,
          "STRK": 1.2861416917068427,
          "ZRO": 0.05450273245512537
        }
      },
      "reporting_currency_note": "FIXED_NOTIONAL_ILLUSTRATION_NOT_REALIZED_BRL_OR_FX_ADJUSTED",
      "return_observations": 20,
      "total_return_gross": {
        "M1_TOP10": 0.010018072425001856,
        "M2_TOP10": 0.003336439902281718
      }
    },
    "legacy_economic_status": "CLOSED_INTERRUPTED_DIAGNOSTIC_ONLY",
    "m1_summary": {
      "breadth_pct_m1_gt_zero": 41.46341463414634,
      "cross_sectional_dispersion_m1": 0.7029351896953352,
      "cutoff": "2026-10-25",
      "delta_breadth_pct_points": -0.7052600646488401,
      "engine_feed": false,
      "lookback_14_date": "2026-10-11",
      "lookback_30_date": "2026-09-25",
      "median_m1": -0.17660419208226374,
      "negative_median_distance_to_zero": 0.5094678039372256,
      "orders": 0,
      "real_capital": 0,
      "status": "SHADOW_ONLY_NOT_APPROVED",
      "universe_n": 82
    },
    "m2_summary": {
      "breadth_pct_m2_gt_zero": 43.90243902439025,
      "cross_sectional_dispersion_m2": 3.5442461705922628,
      "cutoff": "2026-10-25",
      "delta_breadth_pct_points": -5.495151337055539,
      "engine_feed": false,
      "excluded_incomplete_history": 47,
      "median_m2": -0.25680358298668526,
      "orders": 0,
      "real_capital": 0,
      "reference_calendar": "BTC_COMPLETED_UTC_DAILY_BARS",
      "reference_window_bars": 31,
      "reference_window_end": "2026-10-25",
      "reference_window_start": "2026-09-25",
      "status": "PROSPECTIVE_SHADOW_ONLY_NOT_APPROVED",
      "universe_n": 82
    },
    "methodology_failure": null,
    "next_economic_action": "FOLLOW_SEPARATE_TRADABLE_VERSION_NO_HISTORY_TRANSFER",
    "observed_snapshots": 61,
    "price_coverage_cutoff": "2026-10-19",
    "price_coverage_is_historical": true,
    "price_coverage_status": "PASS_REQUIRED_PRICE_COVERAGE",
    "return_observations": 20,
    "signal_status": "ACTIVE_PROSPECTIVE_SHADOW",
    "source": "ledgers/momentum_m1_m2/STATUS.json",
    "status": "CLOSED_RULE_VERSION_SUPERSEDED",
    "successor_source": "ledgers/momentum_tradable_v1/STATUS.json",
    "terminal_observation_target": null,
    "weighting_audit": {
      "engine_changed": true,
      "historical_rewrite_performed": false,
      "status": "APPROVED_HOLD_ACCOUNTING"
    }
  },
  "scientific_authority": false,
  "semantic_projection": {
    "d100": {
      "component": {
        "anchor_bar_date": "2026-09-29",
        "collection_health_hint": "GREEN_ACTIVE",
        "distinct_capture_days": 30,
        "economic_freshness": "FRESH",
        "economic_source": "ledgers/d100/economic/STATUS.json",
        "economic_status": "ACTIVE_SHADOW_N80",
        "first_possible_bar_date": "2026-09-29",
        "freshness": "FRESH",
        "latest_eligible_asset_count": 39,
        "latest_market_data_observed_count": 70,
        "latest_physical_capture_at_utc": "2026-10-26T01:09:34.316927Z",
        "latest_raw_universe_count": 100,
        "latest_signal_available_at_utc": "2026-10-26T01:09:51.300935Z",
        "next_action": "AUTOMATIC_DAILY_CAPTURE_AND_PAIRED_ADVANCEMENT_UNTIL_N80",
        "physical_snapshot_count": 30,
        "physical_status": "ACTIVE_PHYSICAL_DATA_FEED",
        "protocol_approved": true,
        "remaining_scientific_observations": 53,
        "scientific_blockers": [],
        "scientific_observations_credited": 27,
        "scientific_target": 80,
        "source": "ledgers/d100/STATUS.json",
        "status": "ACTIVE_SHADOW_N80"
      },
      "display_name": "D100",
      "economics_authority": false,
      "health_authority": false,
      "inventory_only": true,
      "ledger_ids_expected": [
        "d100"
      ],
      "promotion_authority": false,
      "records": {
        "d100": {
          "distinct_capture_days": 30,
          "economic_status": "SEE_SEPARATE_APPROVED_ECONOMIC_AUTHORITY",
          "health_authority": false,
          "inventory_only": true,
          "latest_physical_capture_at_utc": "2026-10-26T01:09:34.316927Z",
          "latest_snapshot_id": "20261026T010934316927Z_635340845dfb",
          "ledger_id": "d100",
          "physical_snapshot_count": 30,
          "schema": "qrds.d100.forward_collection.v2",
          "scientific_blockers": [],
          "scientific_observations_credited": 0,
          "scientific_target": null,
          "sha256": "d7a8dda606d972674e5b6175ada5572d925f637b98e8b84da4239f5ba46c1b9f",
          "source": "ledgers/d100/STATUS.json",
          "status": "ACTIVE_PHYSICAL_DATA_FEED"
        }
      },
      "representation_status": "PRESENT_RUNTIME_LEDGER",
      "scientific_authority": false,
      "semantic_id": "d100"
    },
    "momentum_m3": {
      "display_name": "M3",
      "economics_authority": false,
      "health_authority": false,
      "inventory_only": true,
      "ledger_ids_expected": [
        "momentum_m3"
      ],
      "promotion_authority": false,
      "records": {
        "momentum_m3": {
          "data_as_of": "2026-10-25",
          "engine_feed": false,
          "health_authority": false,
          "inventory_only": true,
          "ledger_id": "momentum_m3",
          "observed_snapshots": 41,
          "schema": "gate_btc.momentum_m3.status.v1",
          "sha256": "d28e1359a2d4e39f50d33ddd9561a83d78970f62546a33804dea47787c8feb79",
          "source": "ledgers/momentum_m3/STATUS.json",
          "status": "ACTIVE_PROSPECTIVE_SIGNAL_SHADOW"
        }
      },
      "representation_status": "PRESENT_RUNTIME_LEDGER",
      "scientific_authority": false,
      "semantic_id": "momentum_m3"
    },
    "qos": {
      "component": {
        "current": 2,
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
      "display_name": "QOS",
      "economics_authority": false,
      "health_authority": false,
      "inventory_only": true,
      "ledger_ids_expected": [
        "qos_three_track"
      ],
      "promotion_authority": false,
      "records": {
        "qos_three_track": {
          "engine_feed": false,
          "health_authority": false,
          "inventory_only": true,
          "latest_snapshot_date": "2026-10-04",
          "ledger_id": "qos_three_track",
          "orders_generated": 0,
          "real_capital_used": 0,
          "schema": "gate_btc.qos_covered_delivery.v1",
          "sha256": "e48b4e9fc5baa6767eb652c351ac3e6d39b017fc78c7b4d96169c5af378890bf",
          "source": "ledgers/qos_three_track/STATUS.json",
          "status": "WAITING_NEXT_APPROVED_MONTH_END"
        }
      },
      "representation_status": "PRESENT_RUNTIME_LEDGER",
      "scientific_authority": false,
      "semantic_id": "qos"
    },
    "v12": {
      "display_name": "V12",
      "economics_authority": false,
      "health_authority": false,
      "inventory_only": true,
      "ledger_ids_expected": [
        "delta_v12_engine",
        "delta_v12_prices"
      ],
      "promotion_authority": false,
      "records": {
        "delta_v12_engine": {
          "closure_date": "2026-09-22",
          "closure_sha256": "faae9af396c2ae5e752a81069c48cbe1324a40541b09cf697d7f2a8a75cc9631",
          "closure_source": "migration/reporting/delta_v12_engine_closure.json",
          "data_as_of": "2026-09-19",
          "engine_feed": false,
          "health_authority": false,
          "inventory_only": true,
          "ledger_id": "delta_v12_engine",
          "observed_days": 12,
          "orders_generated": 0,
          "promotion_allowed": false,
          "raw_status_preserved": "ACTIVE_PROSPECTIVE_SHADOW",
          "real_capital_used": 0,
          "reporting_disposition": "DESCRIPTIVE_ONLY_AND_NOW_FROZEN",
          "schema": "gate_btc.delta_v12_engine.v1",
          "scientific_credit": 0,
          "sha256": "bf2e2958ff546f1f5b0ba2adbdf004b17c9acf2922f4d8381561b63db0619af6",
          "source": "ledgers/delta_v12_engine/STATUS.json",
          "status": "CLOSED_NO_FURTHER_OBSERVATIONS_POSSIBLE",
          "status_authority_file": "STATUS.json",
          "top_level_files": [
            "ANCHOR.json",
            "DAILY_NAV.csv",
            "DISCARDED_ANCHORS.json",
            "EVIDENCE_GATE.json",
            "POSITIONS_HISTORY.csv",
            "REPORT.html",
            "SELECTIONS_HISTORY.csv",
            "STATUS.json",
            "TRADE_EVENTS.csv",
            "UNIVERSE_MEMBERSHIP.csv"
          ]
        },
        "delta_v12_prices": {
          "engine_feed": false,
          "health_authority": false,
          "inventory_only": true,
          "ledger_id": "delta_v12_prices",
          "schema": "gate_btc.delta_v12_multi_venue_daily_prices.v1",
          "sha256": "4e4526a37e1406c5b2d20b4334ff21435d36735ddc7c0db5630b97606af10ec9",
          "source": "ledgers/delta_v12_prices/COVERAGE.json",
          "status": "NO_CANONICAL_STATUS_FIELD",
          "status_authority_file": "COVERAGE.json",
          "top_level_files": [
            "ARK_STALE_FEED_UNPIN_20261005.json",
            "COVERAGE.json",
            "PINS.json",
            "PRICE_PROVENANCE.json"
          ]
        }
      },
      "representation_status": "PRESENT_RUNTIME_LEDGER",
      "scientific_authority": false,
      "semantic_id": "v12"
    }
  },
  "source_discovery": {
    "d100": {
      "distinct_capture_days": 30,
      "economic_status": "SEE_SEPARATE_APPROVED_ECONOMIC_AUTHORITY",
      "health_authority": false,
      "inventory_only": true,
      "latest_physical_capture_at_utc": "2026-10-26T01:09:34.316927Z",
      "latest_snapshot_id": "20261026T010934316927Z_635340845dfb",
      "ledger_id": "d100",
      "physical_snapshot_count": 30,
      "schema": "qrds.d100.forward_collection.v2",
      "scientific_blockers": [],
      "scientific_observations_credited": 0,
      "scientific_target": null,
      "sha256": "d7a8dda606d972674e5b6175ada5572d925f637b98e8b84da4239f5ba46c1b9f",
      "source": "ledgers/d100/STATUS.json",
      "status": "ACTIVE_PHYSICAL_DATA_FEED"
    },
    "delta_v12_engine": {
      "closure_date": "2026-09-22",
      "closure_sha256": "faae9af396c2ae5e752a81069c48cbe1324a40541b09cf697d7f2a8a75cc9631",
      "closure_source": "migration/reporting/delta_v12_engine_closure.json",
      "data_as_of": "2026-09-19",
      "engine_feed": false,
      "health_authority": false,
      "inventory_only": true,
      "ledger_id": "delta_v12_engine",
      "observed_days": 12,
      "orders_generated": 0,
      "promotion_allowed": false,
      "raw_status_preserved": "ACTIVE_PROSPECTIVE_SHADOW",
      "real_capital_used": 0,
      "reporting_disposition": "DESCRIPTIVE_ONLY_AND_NOW_FROZEN",
      "schema": "gate_btc.delta_v12_engine.v1",
      "scientific_credit": 0,
      "sha256": "bf2e2958ff546f1f5b0ba2adbdf004b17c9acf2922f4d8381561b63db0619af6",
      "source": "ledgers/delta_v12_engine/STATUS.json",
      "status": "CLOSED_NO_FURTHER_OBSERVATIONS_POSSIBLE",
      "status_authority_file": "STATUS.json",
      "top_level_files": [
        "ANCHOR.json",
        "DAILY_NAV.csv",
        "DISCARDED_ANCHORS.json",
        "EVIDENCE_GATE.json",
        "POSITIONS_HISTORY.csv",
        "REPORT.html",
        "SELECTIONS_HISTORY.csv",
        "STATUS.json",
        "TRADE_EVENTS.csv",
        "UNIVERSE_MEMBERSHIP.csv"
      ]
    },
    "delta_v12_prices": {
      "engine_feed": false,
      "health_authority": false,
      "inventory_only": true,
      "ledger_id": "delta_v12_prices",
      "schema": "gate_btc.delta_v12_multi_venue_daily_prices.v1",
      "sha256": "4e4526a37e1406c5b2d20b4334ff21435d36735ddc7c0db5630b97606af10ec9",
      "source": "ledgers/delta_v12_prices/COVERAGE.json",
      "status": "NO_CANONICAL_STATUS_FIELD",
      "status_authority_file": "COVERAGE.json",
      "top_level_files": [
        "ARK_STALE_FEED_UNPIN_20261005.json",
        "COVERAGE.json",
        "PINS.json",
        "PRICE_PROVENANCE.json"
      ]
    }
  },
  "system12": {
    "adjudication_decision": "PASS",
    "adjudication_receipt_semantic_sha256": "00ae74518d9e391c90d7cf0cff7ac59a2004c5f3d79f7ccc360ff8032df56a12",
    "adjudication_receipt_status": "VERIFIED_SEPARATE_AGENT_ADJUDICATION",
    "adjudication_reporting_status": "VERIFIED_PINNED_READINESS_PROJECTION",
    "adjudication_scope": "HASH_BOUND_SYSTEM11_EXECUTION_IMPLEMENTATION_PARITY_ONLY",
    "compared_events": 3307200,
    "contract_sha256": "d06c294dfb74f699ab46333160fb69cca6ec53d605ce0909e41c036ff46866d3",
    "economic_claim_authorized": false,
    "implementation_replication_pass": true,
    "independent_adjudication_executed": true,
    "next_action": "BIND_QRDS_GOVERNED_SYSTEM13_PANEL_BEFORE_INTEGRATED_QLIB_RESEARCH",
    "post_review_release_scope": "HASH_BOUND_SYSTEM11_EXECUTION_IMPLEMENTATION_PARITY_ONLY",
    "post_review_release_semantic_sha256": "cde3be3f5be425c374eba062faa2a9e30eccff6f88cb74e8417b6aa74780fc25",
    "post_review_release_status": "VERIFIED_FROZEN_SCOPE_RESEARCH_RELEASE",
    "raw_implementation_status_preserved": "PASS_IMPLEMENTATION_PARITY_PENDING_INDEPENDENT_ADJUDICATION",
    "readiness_status": "SYSTEM12_FROZEN_PARITY_COMPLETE_SYSTEM13_RESEARCH_DEPENDENCY_RELEASED",
    "reporting_only": true,
    "scenario_count": 300,
    "scientific_authority": false,
    "scientific_credit": 0,
    "source": "gate_btc_2/system12/READINESS.json",
    "source_sha256": {
      "contract": "7a550b4b07f8244bc2b524d21b6db85e2ccfbf4c13ca236c83263dbdb6dc5c9a",
      "frozen_contract_authority": "7a550b4b07f8244bc2b524d21b6db85e2ccfbf4c13ca236c83263dbdb6dc5c9a",
      "implementation": "bc0c36fcc70936c2460ef408b69dc2de4557590463ca3e8bb8b7d157124ae6fa",
      "pinned_adjudication": "80ac1a7bb0e2ccf416f2e586fd7fb748ba2712bf368566759d3e6bf098357490",
      "post_review_release": "222108980ba9aa792dfa4ac44b08053b10c32c9e9aefde5c9e6ea8af5aca5d82",
      "readiness": "c2190bc70365ad072b0f0afe043039b5b6b2a71442ae196cda6ce1ceff5c8e0b"
    },
    "status": "SYSTEM12_FROZEN_PARITY_COMPLETE_SYSTEM13_RESEARCH_DEPENDENCY_RELEASED",
    "system12_complete": true,
    "system12_completion_authorized": true,
    "system13_complete": false,
    "system13_dependency_released": true,
    "system13_release_authorized": true,
    "workflow_run_url": "https://github.com/vmasardinha-coder/QRDS/actions/runs/38088972067"
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
      "delta_v13_engine",
      "empiricus_delta",
      "gateway_dynamics",
      "lock25_50",
      "momentum_canonical_net",
      "momentum_cost_sensitivity",
      "momentum_m1_m2",
      "momentum_m1_m2_economics",
      "momentum_m3",
      "momentum_m3_economics",
      "momentum_tradable_v1",
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
    "ledger_track_count": 30,
    "missing_canonical_reference_ids": [
      "empiricus_delta"
    ],
    "required_reporting_reference_count": 1
  },
  "factory_economics_feedback_allowed": false,
  "inventory_summary": {
    "complete_directory_enumeration": true,
    "component_count": 19,
    "does_not_change_delivery_health": true,
    "inventory_only": true,
    "ledger_count": 30,
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
      "delta_v13_engine",
      "gateway_dynamics",
      "lock25_50",
      "momentum_canonical_net",
      "momentum_cost_sensitivity",
      "momentum_m1_m2",
      "momentum_m1_m2_economics",
      "momentum_m3",
      "momentum_m3_economics",
      "momentum_tradable_v1",
      "prl50_position",
      "qos_three_track",
      "v16_family",
      "v16b",
      "v16b1",
      "v16c",
      "v16d",
      "v16e"
    ],
    "reported_ledger_count": 30,
    "represented_ledger_ids": [
      "alt_trail40_10",
      "b3_h1",
      "bull_replay_live_shadow",
      "d100",
      "d50",
      "delta_paper_monitor",
      "gateway_dynamics",
      "lock25_50",
      "momentum_m1_m2",
      "momentum_tradable_v1",
      "prl50_position",
      "qos_three_track",
      "v16b",
      "v16b1"
    ],
    "status_authority_candidates": [
      "STATUS.json",
      "CANONICAL_STATUS.json",
      "ECONOMICS_STATUS.json",
      "STATE.json",
      "EVIDENCE_GATE.json",
      "COVERAGE.json"
    ],
    "unreported_ledger_ids": [],
    "unrepresented_ledger_ids": [
      "b3_h1_inspired_challengers",
      "b3_h31_prospective",
      "b3_h31_shadow_paper",
      "b3_win_wdo_univariate",
      "delta_v12_engine",
      "delta_v12_prices",
      "delta_v13_engine",
      "momentum_canonical_net",
      "momentum_cost_sensitivity",
      "momentum_m1_m2_economics",
      "momentum_m3",
      "momentum_m3_economics",
      "v16_family",
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
  "runtime_ledger_count": 30,
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
    "delta_v13_engine",
    "gateway_dynamics",
    "lock25_50",
    "momentum_canonical_net",
    "momentum_cost_sensitivity",
    "momentum_m1_m2",
    "momentum_m1_m2_economics",
    "momentum_m3",
    "momentum_m3_economics",
    "momentum_tradable_v1",
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
