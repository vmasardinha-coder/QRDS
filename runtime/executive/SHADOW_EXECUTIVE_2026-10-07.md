# GATE BTC — Shadow Executive — 2026-10-07

**Status:** COMPLETE_WITH_EXPLICIT_ND  
**Reference data:** 2026-10-06  
**Boundary:** RESEARCH_ONLY / SHADOW_ONLY / NOT_APPROVED / ORDERS=0 / REAL_CAPITAL=0

## 1. PASSADO

```json
{
  "delta_walk_forward": {
    "freshness": "FRESH",
    "observations": 145,
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
    "authority": "VERIFIED_RECONCILIATION_STALE_EXTERNAL_EVIDENCE_REQUIRED",
    "data_qualification_current": 7,
    "data_qualification_qualified": true,
    "data_qualification_raw_remote": 7,
    "data_qualification_snapshot_count_total": 22,
    "data_qualification_status": "ACTIVE_CONSECUTIVE_PASS_CHAIN_7_OF_7",
    "data_qualification_synchronized_failure": false,
    "display_current": null,
    "freshness": "STALE",
    "raw_remote_current_for_audit_only": 21,
    "source": "runtime/ledgers/d50/STATUS.json",
    "status": "ACTIVE",
    "target": 30
  },
  "display_counter": {
    "reason": "canonical field absent",
    "source": "runtime/ledgers/d50/STATUS.json",
    "status": "NOT_AVAILABLE_NOT_INFERRED",
    "value": "N/D"
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
    "active_epoch": "epochs/independent_20260929",
    "anchor_date": "2026-09-29",
    "can_append": false,
    "collection_health_hint": "AMBER_BLOCKED_DEPENDENCY",
    "data_as_of": null,
    "engine_feed": false,
    "expected_source_data_as_of": "2026-09-29",
    "first_return_date": "2026-09-30",
    "formal_prospective_evidence": false,
    "freshness": "INTERRUPTED_PRESERVED",
    "inherited_scientific_credit": 0,
    "not_approved": true,
    "observed_days": 0,
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
    "status": "BLOCKED_EPOCH_DAILY_GAP_NO_BACKFILL",
    "updated_at_utc": "2026-10-07T06:07:51.959462+00:00"
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
    "expected_session_weekday_proxy": "2026-10-06",
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
    "freshness": "STALE",
    "next_canonical_event": null,
    "signal_producer": "IMPLEMENTED_AND_SOURCE_BOUND_BUT_NO_CANONICAL_SIGNAL_CREATED",
    "signal_seal": "NONE_CANONICAL",
    "source": "ledgers/v16b/STATUS.json",
    "status": "TERMINAL_BLOCKED_NOT_PROMOTABLE",
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
        "sha256": "0781e9a548e709e78cb4777dce2d3e25bc986984818af63cc32cbd1ae9d9cf6c",
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
    "authority": "VERIFIED_RECONCILIATION_STALE_EXTERNAL_EVIDENCE_REQUIRED",
    "data_qualification_current": 7,
    "data_qualification_qualified": true,
    "data_qualification_raw_remote": 7,
    "data_qualification_snapshot_count_total": 22,
    "data_qualification_status": "ACTIVE_CONSECUTIVE_PASS_CHAIN_7_OF_7",
    "data_qualification_synchronized_failure": false,
    "display_current": null,
    "freshness": "STALE",
    "raw_remote_current_for_audit_only": 21,
    "source": "runtime/ledgers/d50/STATUS.json",
    "status": "ACTIVE",
    "target": 30
  },
  "daily_delivery_pointer": {
    "data_cutoff": "2026-10-06",
    "expected_data_cutoff": "2026-10-06",
    "freshness": "FRESH",
    "lag_days": 0,
    "source": "runtime/GATE_BTC_LATEST_ELIGIBLE_RUN.json",
    "status": "CURRENT"
  },
  "delta_observations": {
    "source": "runtime/GATE_BTC_MEASUREMENT_STATUS.json",
    "status": "PRESENT",
    "value": 145
  },
  "expected_data_cutoff": {
    "source": "runtime/GATE_BTC_REPORTING_CURRENT_STATE.json",
    "status": "PRESENT",
    "value": "2026-10-06"
  },
  "gateway": {
    "freshness": "FRESH",
    "latest_source_data_as_of": "2026-10-07",
    "source": "runtime/ledgers/gateway_dynamics/STATUS.json",
    "status": "ACTIVE",
    "target": 80,
    "valid_snapshot_count": 60
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
    "value": "2026-10-06"
  },
  "reporting_date": "2026-10-07"
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
      "bull_replay_live_shadow",
      "v16b1"
    ],
    "failed_delivery_components": [
      "momentum_m1_m2"
    ],
    "missing_or_undated_components": [
      "prl50",
      "alt_trail"
    ],
    "semantic_projection_ledger_ids": [
      "d100",
      "delta_v12_engine",
      "delta_v12_prices",
      "qos_three_track",
      "v16b1"
    ],
    "stale_components": [
      "d50",
      "b3_h1",
      "v16b",
      "v16b1"
    ],
    "unrepresented_runtime_ledgers": [
      "b3_h1_inspired_challengers",
      "b3_h31_prospective",
      "b3_h31_shadow_paper",
      "b3_win_wdo_univariate",
      "delta_v13_engine",
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
    "collection_health_hint": "RED_FAILED_DELIVERY",
    "cost_status": "N_D",
    "economic_epoch_id": "hold_20260928",
    "economic_freshness": "STALE",
    "economic_gaps": [],
    "economic_nav": {
      "M1_TOP10": 1.1181314484766287,
      "M2_TOP10": 1.1243434523347366
    },
    "economic_status": "FAILED_ECONOMIC_DELIVERY",
    "economics_source": "ledgers/momentum_m1_m2_economics/epochs/hold_20260928/DELIVERY_STATUS.json",
    "first_eligible_economic_cutoff": "2026-09-28",
    "freshness": "FRESH",
    "last_economic_cutoff": "2026-10-05",
    "last_run_state": null,
    "latest_economics": {
      "btc_daily_return_gross": -0.00881925343811385,
      "btc_nav": 1.025138871524387,
      "cost_status": "N_D",
      "cutoff": "2026-10-05",
      "daily_return_gross": {
        "M1_TOP10": 0.05769214784999632,
        "M2_TOP10": 0.059598688679411316
      },
      "event": "HOLD",
      "evidence": {
        "price_manifest_sha256": "be6d869ff3319973d53e7990593864946c44c61f7b0ba8fe63ac044c24ec562e",
        "snapshot_sha256": "8f7707e0e97c81fcdacd3bf4fba5201773204e24a83aa0c1dc1cc6ee1e8b7ee3",
        "source_available_at_utc": "2026-10-06T10:11:32.296926+00:00"
      },
      "excess_vs_btc_percentage_points": {
        "M1_TOP10": 9.299257695224172,
        "M2_TOP10": 9.920458081034965
      },
      "holdings_after_close": {
        "M1_TOP10": [
          "QNT",
          "NEAR",
          "RAY",
          "AR",
          "ENA",
          "ARB",
          "NIGHT",
          "ZRO",
          "SEI",
          "KMNO"
        ],
        "M2_TOP10": [
          "NEAR",
          "QNT",
          "NIGHT",
          "ZRO",
          "RAY",
          "ENA",
          "SEI",
          "RUNE",
          "ICP",
          "PYTH"
        ]
      },
      "illustrative_brl_pnl": {
        "M1_TOP10": 21263.66072579317,
        "M2_TOP10": 22381.821420252596
      },
      "illustrative_brl_value": {
        "M1_TOP10": 201263.66072579316,
        "M2_TOP10": 202381.82142025259
      },
      "nav": {
        "M1_TOP10": 1.1181314484766287,
        "M2_TOP10": 1.1243434523347366
      },
      "net_return": null,
      "observed_at_utc": "2026-10-06T10:11:32.457831+00:00",
      "quantities_after_close": {
        "M1_TOP10": {
          "AR": 0.02369106846718787,
          "ARB": 0.49140049140049147,
          "ENA": 0.4025764895330113,
          "KMNO": 2.271178741766977,
          "NEAR": 0.020466639377814164,
          "NIGHT": 3.0883261272390365,
          "QNT": 0.0003748125937031484,
          "RAY": 0.05225479437738413,
          "SEI": 1.364815067558346,
          "ZRO": 0.059952038369304565
        },
        "M2_TOP10": {
          "ENA": 0.4025764895330113,
          "ICP": 0.029069767441860468,
          "NEAR": 0.020466639377814164,
          "NIGHT": 3.0883261272390365,
          "PYTH": 1.26984126984127,
          "QNT": 0.0003748125937031484,
          "RAY": 0.05225479437738413,
          "RUNE": 0.13297872340425532,
          "SEI": 1.364815067558346,
          "ZRO": 0.059952038369304565
        }
      },
      "reporting_currency_note": "FIXED_NOTIONAL_ILLUSTRATION_NOT_REALIZED_BRL_OR_FX_ADJUSTED",
      "return_observations": 6,
      "total_return_gross": {
        "M1_TOP10": 0.11813144847662871,
        "M2_TOP10": 0.12434345233473665
      }
    },
    "legacy_economic_status": "CLOSED_INTERRUPTED_DIAGNOSTIC_ONLY",
    "m1_summary": {
      "breadth_pct_m1_gt_zero": 37.64705882352941,
      "cross_sectional_dispersion_m1": 0.7891114202219,
      "cutoff": "2026-10-06",
      "delta_breadth_pct_points": -4.21340629274966,
      "engine_feed": false,
      "lookback_14_date": "2026-09-22",
      "lookback_30_date": "2026-09-06",
      "median_m1": -0.2075555478694463,
      "negative_median_distance_to_zero": 0.44838376844925965,
      "orders": 0,
      "real_capital": 0,
      "status": "SHADOW_ONLY_NOT_APPROVED",
      "universe_n": 85
    },
    "m2_summary": {
      "breadth_pct_m2_gt_zero": 50.588235294117645,
      "cross_sectional_dispersion_m2": 3.248753511921504,
      "cutoff": "2026-10-06",
      "delta_breadth_pct_points": -6.388508891928865,
      "engine_feed": false,
      "excluded_incomplete_history": 0,
      "median_m2": 0.1373031267131802,
      "orders": 0,
      "real_capital": 0,
      "reference_calendar": "BTC_COMPLETED_UTC_DAILY_BARS",
      "reference_window_bars": 31,
      "reference_window_end": "2026-10-06",
      "reference_window_start": "2026-09-06",
      "status": "PROSPECTIVE_SHADOW_ONLY_NOT_APPROVED",
      "universe_n": 85
    },
    "methodology_failure": null,
    "next_economic_action": "REPAIR_FAILURE_NO_RESET_NO_BACKFILL",
    "observed_snapshots": 42,
    "price_coverage_cutoff": "2026-10-05",
    "price_coverage_status": "PASS_REQUIRED_PRICE_COVERAGE",
    "return_observations": 6,
    "signal_status": "ACTIVE_PROSPECTIVE_SHADOW",
    "source": "ledgers/momentum_m1_m2/STATUS.json",
    "status": "FAILED_ECONOMIC_DELIVERY",
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
          "distinct_capture_days": 11,
          "economic_status": "SEE_SEPARATE_APPROVED_ECONOMIC_AUTHORITY",
          "health_authority": false,
          "inventory_only": true,
          "latest_physical_capture_at_utc": "2026-10-07T01:32:12.687858Z",
          "latest_snapshot_id": "20261007T013212687858Z_2b101d73ad14",
          "ledger_id": "d100",
          "physical_snapshot_count": 11,
          "schema": "qrds.d100.forward_collection.v2",
          "scientific_blockers": [],
          "scientific_observations_credited": 0,
          "scientific_target": null,
          "sha256": "82748aff8d49781a4b73a4c3a0bcff1ba46ffcb56de240717feb43461352867a",
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
          "data_as_of": "2026-10-06",
          "engine_feed": false,
          "health_authority": false,
          "inventory_only": true,
          "ledger_id": "momentum_m3",
          "observed_snapshots": 23,
          "schema": "gate_btc.momentum_m3.status.v1",
          "sha256": "50a3fc83c12b27786e5f002595b02a7858af932f7039648e4729bc252265326f",
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
          "sha256": "cd8279245a3ff8eb3dc630f42056a5335e7dd1348c10fc01407895db6e979e35",
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
          "data_as_of": "2026-09-19",
          "engine_feed": false,
          "health_authority": false,
          "inventory_only": true,
          "ledger_id": "delta_v12_engine",
          "observed_days": 12,
          "orders_generated": 0,
          "promotion_allowed": false,
          "real_capital_used": 0,
          "schema": "gate_btc.delta_v12_engine.v1",
          "sha256": "bf2e2958ff546f1f5b0ba2adbdf004b17c9acf2922f4d8381561b63db0619af6",
          "source": "ledgers/delta_v12_engine/STATUS.json",
          "status": "ACTIVE_PROSPECTIVE_SHADOW"
        },
        "delta_v12_prices": {
          "engine_feed": false,
          "health_authority": false,
          "inventory_only": true,
          "ledger_id": "delta_v12_prices",
          "schema": "gate_btc.delta_v12_multi_venue_daily_prices.v1",
          "sha256": "e7aa94b8f6c40c1f08234ebd6784c35493d8d3a8c58c005155cb2b670cbd2d36",
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
      "distinct_capture_days": 11,
      "economic_status": "SEE_SEPARATE_APPROVED_ECONOMIC_AUTHORITY",
      "health_authority": false,
      "inventory_only": true,
      "latest_physical_capture_at_utc": "2026-10-07T01:32:12.687858Z",
      "latest_snapshot_id": "20261007T013212687858Z_2b101d73ad14",
      "ledger_id": "d100",
      "physical_snapshot_count": 11,
      "schema": "qrds.d100.forward_collection.v2",
      "scientific_blockers": [],
      "scientific_observations_credited": 0,
      "scientific_target": null,
      "sha256": "82748aff8d49781a4b73a4c3a0bcff1ba46ffcb56de240717feb43461352867a",
      "source": "ledgers/d100/STATUS.json",
      "status": "ACTIVE_PHYSICAL_DATA_FEED"
    },
    "delta_v12_engine": {
      "data_as_of": "2026-09-19",
      "engine_feed": false,
      "health_authority": false,
      "inventory_only": true,
      "ledger_id": "delta_v12_engine",
      "observed_days": 12,
      "orders_generated": 0,
      "promotion_allowed": false,
      "real_capital_used": 0,
      "schema": "gate_btc.delta_v12_engine.v1",
      "sha256": "bf2e2958ff546f1f5b0ba2adbdf004b17c9acf2922f4d8381561b63db0619af6",
      "source": "ledgers/delta_v12_engine/STATUS.json",
      "status": "ACTIVE_PROSPECTIVE_SHADOW"
    },
    "delta_v12_prices": {
      "engine_feed": false,
      "health_authority": false,
      "inventory_only": true,
      "ledger_id": "delta_v12_prices",
      "schema": "gate_btc.delta_v12_multi_venue_daily_prices.v1",
      "sha256": "e7aa94b8f6c40c1f08234ebd6784c35493d8d3a8c58c005155cb2b670cbd2d36",
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
      "momentum_m1_m2",
      "momentum_m1_m2_economics",
      "momentum_m3",
      "momentum_m3_economics",
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
    "ledger_track_count": 27,
    "missing_canonical_reference_ids": [
      "empiricus_delta"
    ],
    "required_reporting_reference_count": 1
  },
  "factory_economics_feedback_allowed": false,
  "inventory_summary": {
    "complete_directory_enumeration": true,
    "component_count": 17,
    "does_not_change_delivery_health": true,
    "inventory_only": true,
    "ledger_count": 27,
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
      "momentum_m1_m2",
      "momentum_m1_m2_economics",
      "momentum_m3",
      "momentum_m3_economics",
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
      "d100",
      "d50",
      "delta_paper_monitor",
      "gateway_dynamics",
      "lock25_50",
      "momentum_m1_m2",
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
    "unrepresented_ledger_ids": [
      "b3_h1_inspired_challengers",
      "b3_h31_prospective",
      "b3_h31_shadow_paper",
      "b3_win_wdo_univariate",
      "delta_v12_engine",
      "delta_v12_prices",
      "delta_v13_engine",
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
  "runtime_ledger_count": 27,
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
    "momentum_m1_m2",
    "momentum_m1_m2_economics",
    "momentum_m3",
    "momentum_m3_economics",
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
