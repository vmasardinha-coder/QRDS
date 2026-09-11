#!/usr/bin/env python3
"""Build the canonical reporting-only 13-block GATE BTC shadow executive.

Contract: QRDS issue #297. The generator is deliberately fail-visible: required
blocks and fields are never omitted. Missing canonical evidence is rendered as
N/D with provenance/reason rather than inferred or fabricated.

This is a reporting transform only. It does not change methodology, scientific
credit, counters, promotion state, engine feed, orders, or real capital.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import date
from pathlib import Path
from typing import Any

ND = "N/D"
BLOCK_ORDER = [
    ("01_passado", "PASSADO"),
    ("02_live_financeiro", "LIVE FINANCEIRO"),
    ("03_d50", "D50"),
    ("04_proxy_real", "PROXY REAL"),
    ("05_preservation", "PRESERVATION"),
    ("06_live_estrutural", "LIVE ESTRUTURAL"),
    ("07_clocks", "CLOCKS"),
    ("08_fundo_regime", "FUNDO/REGIME"),
    ("09_radar_externo", "RADAR EXTERNO"),
    ("10_meta_2030", "META 2030"),
    ("11_lideranca_publicacao", "LIDERANCA/PUBLICACAO"),
    ("12_gate_btc_2", "GATE BTC 2.0"),
    ("13_factory_externo", "FACTORY/EXTERNO"),
]
FINANCIAL_FIELDS = [
    "baseline", "current_index", "variation", "hwm", "drawdown", "giveback",
    "capital_1m_equivalent", "fees_custody_live", "fees_custody_cumulative",
    "sharpe", "sortino", "calmar", "var_95", "var_99", "es_95", "es_99",
    "payoff", "best_day", "worst_day", "pl_decomposition", "deltas",
    "baseline_version", "health_state", "health_source",
]


def load(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        obj = json.loads(path.read_text(encoding="utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None
    return obj if isinstance(obj, dict) else None


def sha256(path: Path) -> str | None:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None


def nd(reason: str, source: str | None = None) -> dict[str, Any]:
    out: dict[str, Any] = {"value": ND, "status": "NOT_AVAILABLE_NOT_INFERRED", "reason": reason}
    if source:
        out["source"] = source
    return out


def value(v: Any, source: str | None = None) -> dict[str, Any]:
    if v is None:
        return nd("canonical field absent", source)
    out: dict[str, Any] = {"value": v, "status": "PRESENT"}
    if source:
        out["source"] = source
    return out


def component(state: dict[str, Any], name: str) -> dict[str, Any]:
    obj = (state.get("components") or {}).get(name)
    return obj if isinstance(obj, dict) else {}


def first_present(*items: Any) -> Any:
    for item in items:
        if item is not None:
            return item
    return None


def financial_block(state: dict[str, Any]) -> dict[str, Any]:
    # Reporting state currently has no single canonical financial economics schema.
    # Harvest only explicit fields if present; otherwise preserve the required field as N/D.
    candidates = []
    for key in ("financial", "financial_snapshot", "economics", "live_financial"):
        obj = state.get(key)
        if isinstance(obj, dict):
            candidates.append(obj)
    merged: dict[str, Any] = {}
    for obj in candidates:
        merged.update(obj)

    aliases = {
        "current_index": ("current_index", "index", "nav", "net_nav"),
        "variation": ("variation", "return", "return_since_start"),
        "hwm": ("hwm", "high_water_mark"),
        "drawdown": ("drawdown", "max_drawdown", "current_drawdown"),
        "giveback": ("giveback",),
        "capital_1m_equivalent": ("capital_1m_equivalent", "capital_1m"),
        "fees_custody_live": ("fees_custody_live", "fees_live"),
        "fees_custody_cumulative": ("fees_custody_cumulative", "fees_cumulative"),
        "var_95": ("var_95", "VaR95"), "var_99": ("var_99", "VaR99"),
        "es_95": ("es_95", "ES95"), "es_99": ("es_99", "ES99"),
    }
    fields: dict[str, Any] = {}
    for field in FINANCIAL_FIELDS:
        names = aliases.get(field, (field,))
        found = first_present(*(merged.get(n) for n in names))
        fields[field] = value(found, "runtime/GATE_BTC_REPORTING_CURRENT_STATE.json") if found is not None else nd(
            "no canonical financial field in reporting state",
            "runtime/GATE_BTC_REPORTING_CURRENT_STATE.json",
        )
    return {
        "status": "PRESENT_WITH_ND_FIELDS" if any(v["value"] == ND for v in fields.values()) else "PRESENT",
        "required_fields": fields,
        "missing_field_count": sum(v["value"] == ND for v in fields.values()),
    }


def track_catalog(state: dict[str, Any]) -> dict[str, Any]:
    c = state.get("executive_track_catalog")
    return c if isinstance(c, dict) else {}


def ledger_excerpt(state: dict[str, Any], ids: list[str]) -> dict[str, Any]:
    inv = state.get("ledger_inventory") or {}
    return {i: inv[i] for i in ids if i in inv}


def semantic_projection(state: dict[str, Any]) -> dict[str, Any]:
    """Project selected runtime ledgers into stable executive meanings without reinterpreting them."""
    catalog = track_catalog(state)
    ledgers = catalog.get("ledger_tracks") or state.get("ledger_inventory") or {}
    declared = catalog.get("declared_nonledger_tracks") or {}
    specs = {
        "d100": {"display_name": "D100", "ledger_ids": ["d100"]},
        "momentum_m3": {"display_name": "M3", "ledger_ids": ["momentum_m3"]},
        "v16b1": {"display_name": "V16B.1", "ledger_ids": ["v16b1", "v16b_1"], "parent_track_id": "v16b", "parent_reporting_role": "TERMINAL_PARENT_NOT_REOPENED"},
        "v16c1": {"display_name": "V16C.1", "ledger_ids": ["v16c1", "v16c_1"], "parent_track_id": "v16c", "parent_reporting_role": "FROZEN_BLOCKED_PARENT"},
        "v12": {"display_name": "V12", "ledger_ids": ["delta_v12_engine", "delta_v12_prices"]},
        "qos": {"display_name": "QOS", "ledger_ids": ["qos_three_track"]},
    }
    out: dict[str, Any] = {}
    for semantic_id, spec in specs.items():
        matched = {ledger_id: ledgers[ledger_id] for ledger_id in spec["ledger_ids"] if ledger_id in ledgers}
        entry: dict[str, Any] = {
            "semantic_id": semantic_id,
            "display_name": spec["display_name"],
            "representation_status": "PRESENT_RUNTIME_LEDGER" if matched else "ABSENT_NOT_INFERRED",
            "ledger_ids_expected": list(spec["ledger_ids"]),
            "records": matched,
            "inventory_only": True,
            "scientific_authority": False,
            "health_authority": False,
            "promotion_authority": False,
            "economics_authority": False,
        }
        parent_id = spec.get("parent_track_id")
        if parent_id:
            parent = ledgers.get(parent_id) or declared.get(parent_id)
            entry["parent"] = {
                "track_id": parent_id,
                "reporting_role": spec["parent_reporting_role"],
                "record": parent if isinstance(parent, dict) else nd(f"{parent_id} parent absent"),
                "source_status_preserved": True,
            }
        out[semantic_id] = entry
    qos_component = component(state, "qos_monthly")
    if qos_component:
        out["qos"]["component"] = qos_component
        if out["qos"]["representation_status"] == "ABSENT_NOT_INFERRED":
            out["qos"]["representation_status"] = "PRESENT_COMPONENT_NO_RUNTIME_LEDGER"
    return out



def _required_ref(required: dict[str, Any], track_id: str, display_name: str) -> dict[str, Any]:
    obj = required.get(track_id)
    if isinstance(obj, dict):
        return obj
    return {
        "track_id": track_id,
        "display_name": display_name,
        "canonical_evidence_status": "ABSENT_NOT_INFERRED",
        "inventory_only": True,
        "scientific_authority": False,
        "engine_feed": False,
        "orders_generated": 0,
        "real_capital_used": 0,
    }


def _status_of(obj: Any, default: str = "N/D") -> str:
    if not isinstance(obj, dict):
        return default
    return str(obj.get("status") or obj.get("representation_status") or obj.get("canonical_evidence_status") or default)


def build_full_master_v2(
    state: dict[str, Any],
    payloads: dict[str, dict[str, Any]],
    semantic: dict[str, Any],
    required: dict[str, Any],
    ledgers: dict[str, Any],
    declared: dict[str, Any],
) -> dict[str, Any]:
    """Single executive model: technical/scientific + economic/decision inventory.

    Reporting-only. External tracks are surfaced as explicit references and remain
    N/D/ABSENT_NOT_INFERRED unless canonical evidence is actually present.
    """
    d50 = component(state, "d50")
    delta = component(state, "delta")
    gateway = component(state, "gateway")
    momentum = component(state, "momentum_m1_m2")
    qos = component(state, "qos_monthly")
    bull = component(state, "bull_replay_live_shadow")

    externals = {
        "portal_btc": _required_ref(required, "portal_btc", "Portal BTC"),
        "portal_watchlist": _required_ref(required, "portal_watchlist", "Portal BTC Watchlist"),
        "macro_quant": _required_ref(required, "macro_quant", "Macro Quant"),
        "agent_trader": _required_ref(required, "agent_trader", "Agent Trader"),
        "proxy_real": _required_ref(required, "proxy_real", "Proxy Real / Victor Real"),
        "empiricus_delta": _required_ref(required, "empiricus_delta", "Empiricus Delta"),
        "cloud_delta": _required_ref(required, "cloud_delta", "Cloud / Anthropic Delta"),
        "delta_external_historical": _required_ref(required, "delta_external_historical", "Delta External Historical"),
        "atlas_manual": _required_ref(required, "atlas_manual", "Atlas / Manual"),
    }

    technical_radar = [
        {"track": "D50", "status": _status_of(d50), "current": d50.get("display_current") if d50 else None, "target": d50.get("target") if d50 else None, "freshness": d50.get("freshness") if d50 else None, "authority": d50.get("authority") if d50 else None},
        {"track": "Delta walk-forward", "status": _status_of(delta), "current": delta.get("observations") if delta else None, "target": delta.get("targets") if delta else None},
        {"track": "Gateway", "status": _status_of(gateway), "current": gateway.get("valid_snapshot_count") if gateway else None, "target": gateway.get("target") if gateway else None},
        {"track": "Momentum M1/M2", "status": _status_of(momentum), "snapshots": momentum.get("observed_snapshots") if momentum else None},
        {"track": "QOS", "status": _status_of(qos), "current": qos.get("current") if qos else None, "target": qos.get("target") if qos else None},
        {"track": "D100", "status": _status_of(semantic.get("d100"))},
        {"track": "V12", "status": _status_of(semantic.get("v12"))},
        {"track": "V16B.1", "status": _status_of(semantic.get("v16b1"))},
        {"track": "B3 H1", "status": _status_of(component(state, "b3_h1") or ledgers.get("b3_h1"))},
        {"track": "B3 H31", "status": _status_of(ledgers.get("b3_h31_prospective"))},
    ]

    return {
        "schema": "gate_btc.shadow_executive.full_master_v2.v1",
        "model_name": "FULL MASTER v2 — technical + scientific + economic + decision",
        "single_model": True,
        "reporting_only": True,
        "scientific_authority": False,
        "promotion_authority": False,
        "economic_authority": False,
        "governance": {
            "research_only": True,
            "shadow_only": True,
            "not_approved": True,
            "engine_feed": False,
            "orders": 0,
            "real_capital": 0,
            "no_backfill": True,
            "no_late_seal": True,
            "no_counter_reset": True,
            "no_retune": True,
            "fail_closed": True,
        },
        "technical_radar": technical_radar,
        "cycle_allocation": {
            "qos": semantic.get("qos"),
            "bull_replay_proxy_synthetic": bull or nd("bull replay absent"),
            "proxy_real": externals["proxy_real"],
            "meta_2030": payloads["10_meta_2030"],
            "decision_question": "WHAT SHOULD BE ALLOCATED, IF AND ONLY IF SCIENTIFIC GATES EVENTUALLY ALLOW IT?",
        },
        "alpha_robots": {
            "d50": d50 or nd("d50 absent"),
            "delta_walk_forward": delta or nd("delta absent"),
            "delta_v12": semantic.get("v12"),
            "empiricus_delta": externals["empiricus_delta"],
            "cloud_delta": externals["cloud_delta"],
            "delta_external_historical": externals["delta_external_historical"],
            "macro_quant": externals["macro_quant"],
            "portal_btc": externals["portal_btc"],
            "agent_trader": externals["agent_trader"],
        },
        "regime_context": {
            "momentum_m1_m2": momentum or nd("momentum absent"),
            "momentum_m3": semantic.get("momentum_m3"),
            "gateway": gateway or nd("gateway absent"),
            "portal_btc": externals["portal_btc"],
            "macro_quant": externals["macro_quant"],
            "bull_replay": bull or nd("bull replay absent"),
            "decision_question": "WHAT TYPE OF RISK IS THE CURRENT REGIME SUPPORTING?",
        },
        "preservation": {
            "canonical_block": payloads["05_preservation"],
            "d50": d50 or nd("d50 absent"),
            "delta_v12": semantic.get("v12"),
            "macro_quant": externals["macro_quant"],
            "ledger_tracks": ledger_excerpt(state, ["lock25_50", "prl50_position", "alt_trail40_10"]),
            "decision_question": "HOW MUCH PROFIT CAN BE RETAINED WITHOUT DESTROYING THE EDGE?",
        },
        "delta_full_inventory": {
            "v11_walk_forward": delta or nd("delta absent"),
            "v12": semantic.get("v12"),
            "bull_replay": bull or nd("bull replay absent"),
            "empiricus_delta": externals["empiricus_delta"],
            "cloud_delta": externals["cloud_delta"],
            "external_historical": externals["delta_external_historical"],
            "claim_boundary": "DO_NOT_RANK_NONCOMPARABLE_WINDOWS_OR_INFER PROPRIETARY MECHANISM",
        },
        "portal_btc_full": {
            "core": externals["portal_btc"],
            "watchlist": externals["portal_watchlist"],
            "required_subviews": [
                "A/B/C/D/G/H Top100 and Top300",
                "Watchlist institutional",
                "ex-PONS attribution",
                "ex-Top3 attribution",
                "Top1/Top3/Top5 concentration",
                "Momentum",
                "Reversal",
                "Sector rotation",
                "price sanity/quarantine",
                "stopped/extreme trades",
            ],
            "systematic_alpha_claim_allowed": False,
        },
        "proxy": {
            "synthetic": {
                "series": "Victor_proxy",
                "source": bull.get("source") if bull else None,
                "claim_boundary": "SYNTHETIC_BENCHMARK_NOT_REAL_ACCOUNT",
            },
            "real": externals["proxy_real"],
            "must_never_conflate": True,
        },
        "macro_quant": {
            "external_track": externals["macro_quant"],
            "required_subviews": ["Production 90d", "Dynamic 60d", "Ref 50/50", "Score30/R30", "Score45/R45", "Score30/R90", "H1", "H2", "H3", "H4", "tripwires"],
            "real_small_capital_external_to_qrds": True,
        },
        "agent_trader": {
            "external_track": externals["agent_trader"],
            "required_books": ["US", "Crypto", "B3", "Structured B3"],
        },
        "b3_local_mt5": {
            "h1": component(state, "b3_h1") or ledgers.get("b3_h1") or nd("b3_h1 absent"),
            "h31": ledgers.get("b3_h31_prospective") or nd("b3_h31 prospective absent"),
            "mt5_role": "READ_ONLY_AUXILIARY_DISCOVERY_OR_CROSS_VALIDATION_ONLY",
            "h1_economics_read": False,
        },
        "gate_btc_2_factory": {
            "d100": semantic.get("d100"),
            "v16b1": semantic.get("v16b1"),
            "v16c1": semantic.get("v16c1"),
            "declared_tracks": declared,
            "runtime_ledger_count": len(ledgers),
            "factory_economics_feedback_allowed": False,
        },
        "external_controls": externals,
        "economic_decision_board": {
            "capital_reference_brl": 180000,
            "windows": ["HISTORICAL", "POST_PIT", "LIVE_PROSPECTIVE", "EXTERNAL_PARALLEL", "FUTURE_BASELINE"],
            "historical_values": nd("historical R$180k comparison not canonical in current runtime state"),
            "post_pit_values": nd("post-PIT economic comparison not canonical in current runtime state"),
            "live_internal": {
                "d50": d50 or nd("d50 absent"),
                "delta": delta or nd("delta absent"),
                "v12": semantic.get("v12"),
            },
            "live_external": {
                "portal_btc": externals["portal_btc"],
                "macro_quant": externals["macro_quant"],
                "agent_trader": externals["agent_trader"],
            },
            "future_baseline": nd("META 2030 / Monte Carlo baseline not canonical in current runtime state"),
            "no_cross_window_race": True,
        },
        "pending_actions": {
            "reporting_delivery": state.get("warnings", {}),
            "required_external_missing": sorted(
                k for k, v in externals.items()
                if v.get("canonical_evidence_status") != "PRESENT"
            ),
            "policy": "COLLECT_VALIDATE_DO_NOT_RETUNE",
        },
    }


def build(state: dict[str, Any], reporting_date: str) -> dict[str, Any]:
    catalog = track_catalog(state)
    ledgers = catalog.get("ledger_tracks") or state.get("ledger_inventory") or {}
    declared = catalog.get("declared_nonledger_tracks") or {}
    required = catalog.get("required_reporting_references") or {}
    empiricus = required.get("empiricus_delta")
    if not isinstance(empiricus, dict):
        empiricus = {
            "track_id": "empiricus_delta",
            "display_name": "Empiricus Delta",
            "canonical_evidence_status": "ABSENT_NOT_INFERRED",
            "scientific_authority": False,
            "inventory_only": True,
        }

    delta = component(state, "delta")
    d50 = component(state, "d50")
    bull = component(state, "bull_replay_live_shadow")
    gateway = component(state, "gateway")
    qos = component(state, "qos_monthly")
    v16b = component(state, "v16b")
    momentum = component(state, "momentum_m1_m2")
    semantic = semantic_projection(state)

    blocks: list[dict[str, Any]] = []
    payloads: dict[str, dict[str, Any]] = {
        "01_passado": {
            "delta_walk_forward": delta or nd("delta component absent"),
            "historical_policy": "BACKTEST_OR_REPLAY_ONLY; NEVER COUNTED AS PROSPECTIVE LIVE",
            "historical_backfill_counts_as_live": False,
        },
        "02_live_financeiro": financial_block(state),
        "03_d50": {
            "component": d50 or nd("d50 component absent"),
            "display_counter": value(d50.get("display_current"), d50.get("source")) if d50 else nd("d50 absent"),
            "target": value(d50.get("target"), d50.get("source")) if d50 else nd("d50 absent"),
        },
        "04_proxy_real": {
            "bull_replay_live_shadow": bull or nd("bull replay component absent"),
            "proxy_series": "Victor_proxy",
            "claim_boundary": "DESCRIPTIVE_SHADOW_ONLY_NOT_REAL_CAPITAL",
        },
        "05_preservation": {
            "status": "N/D_NO_CANONICAL_PRESERVATION_TRACK" if "preservation" not in ledgers else ledgers["preservation"].get("status", ND),
            "canonical_track_present": "preservation" in ledgers,
            "hwm": nd("no dedicated canonical preservation/HWM source found"),
            "drawdown": nd("no dedicated canonical preservation/drawdown source found"),
            "giveback": nd("no dedicated canonical preservation/giveback source found"),
            "retention_rule": nd("no canonical profit-retention rule source found"),
            "note": "Mandatory executive block retained even when evidence is unavailable; values are never inferred.",
        },
        "06_live_estrutural": {
            "v16b": v16b or ledgers.get("v16b") or nd("v16b absent"),
            "v16b1": semantic["v16b1"],
            "v16c": declared.get("v16c") or nd("V16C declaration/prereg absent"),
            "v16c1": semantic["v16c1"],
            "v16d": declared.get("v16d") or nd("V16D declaration absent"),
            "v16e": declared.get("v16e") or nd("V16E declaration absent"),
            "b3_h1": component(state, "b3_h1") or ledgers.get("b3_h1") or nd("b3_h1 absent"),
            "h31_tracks": {k: v for k, v in ledgers.items() if "h31" in k.lower()},
        },
        "07_clocks": {
            "reporting_date": reporting_date,
            "reference_data_date": value(state.get("reference_data_date"), "runtime/GATE_BTC_REPORTING_CURRENT_STATE.json"),
            "expected_data_cutoff": value(state.get("expected_data_cutoff"), "runtime/GATE_BTC_REPORTING_CURRENT_STATE.json"),
            "daily_delivery_pointer": component(state, "daily_delivery_pointer") or nd("pointer absent"),
            "delta_observations": value(delta.get("observations"), delta.get("source")) if delta else nd("delta absent"),
            "d50": d50 or nd("d50 absent"),
            "gateway": gateway or nd("gateway absent"),
            "qos_monthly": qos or nd("qos absent"),
        },
        "08_fundo_regime": {
            "canonical_regime_source": nd("no canonical fund/regime source identified in reporting state"),
            "policy": "REPORT N/D RATHER THAN INFER MARKET REGIME",
        },
        "09_radar_externo": {
            "empiricus_delta": empiricus,
            "empiricus_delta_required": True,
            "official_replica_claim": False,
            "other_required_references": {k: v for k, v in required.items() if k != "empiricus_delta"},
        },
        "10_meta_2030": {
            "canonical_meta_2030_source": nd("no canonical META 2030 runtime source identified"),
            "status": "N/D_NOT_INFERRED",
        },
        "11_lideranca_publicacao": {
            "reporting_state_status": state.get("status", ND),
            "delivery_complete": state.get("delivery_complete"),
            "freshness_warnings": state.get("warnings", {}),
            "headline": "sem fato novo relevante" if not state.get("delivery_complete") else "estado diario reconciliado",
            "publication_policy": "FULL_EXECUTIVE_ALWAYS_EMITTED_EVEN_WITH_NO_NEW_HEADLINE",
        },
        "12_gate_btc_2": {
            "source_discovery": ledger_excerpt(state, ["delta_v12_engine", "delta_v12_prices", "d100"]),
            "semantic_projection": {
                "d100": semantic["d100"],
                "momentum_m3": semantic["momentum_m3"],
                "v12": semantic["v12"],
                "qos": semantic["qos"],
            },
            "momentum": momentum or ledgers.get("momentum_m1_m2") or nd("momentum absent"),
            "declared_tracks": declared,
            "scientific_authority": False,
        },
        "13_factory_externo": {
            "runtime_ledger_count": len(ledgers),
            "runtime_ledger_ids": sorted(ledgers),
            "inventory_summary": state.get("inventory_summary", {}),
            "executive_catalog_summary": catalog.get("summary", {}),
            "required_external_references": required,
            "empiricus_delta_present_in_inventory": "empiricus_delta" in required,
            "factory_economics_feedback_allowed": False,
        },
    }

    for idx, (block_id, title) in enumerate(BLOCK_ORDER, start=1):
        blocks.append({
            "position": idx,
            "block_id": block_id,
            "title": title,
            "content": payloads[block_id],
        })

    finance_missing = payloads["02_live_financeiro"]["missing_field_count"]
    preservation_missing = not payloads["05_preservation"]["canonical_track_present"]
    empiricus_missing = empiricus.get("canonical_evidence_status") != "PRESENT"
    report_status = "COMPLETE_WITH_EXPLICIT_ND" if (finance_missing or preservation_missing or empiricus_missing) else "COMPLETE"

    return {
        "schema": "gate_btc.shadow_executive.v2",
        "contract_issue": 297,
        "reporting_date": reporting_date,
        "reference_data_date": state.get("reference_data_date"),
        "status": report_status,
        "reporting_only": True,
        "scientific_authority": False,
        "research_only": True,
        "shadow_only": True,
        "not_approved": True,
        "engine_feed": False,
        "orders_generated": 0,
        "real_capital_used": 0,
        "methodology_changes": 0,
        "counter_changes": 0,
        "promotion_allowed": False,
        "fixed_block_count": len(blocks),
        "fixed_block_order": [b[0] for b in BLOCK_ORDER],
        "blocks": blocks,
        "completeness": {
            "financial_missing_field_count": finance_missing,
            "preservation_canonical_track_missing": preservation_missing,
            "empiricus_delta_canonical_evidence_missing": empiricus_missing,
            "omission_policy": "NEVER_OMIT_REQUIRED_BLOCK_OR_FIELD; USE_ND_WITH_REASON",
        },
        "source_reporting_state_sha256": None,
        "full_master_v2": build_full_master_v2(state, payloads, semantic, required, ledgers, declared),
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        f"# GATE BTC — Shadow Executive — {report['reporting_date']}",
        "",
        f"**Status:** {report['status']}  ",
        f"**Reference data:** {report.get('reference_data_date') or ND}  ",
        "**Boundary:** RESEARCH_ONLY / SHADOW_ONLY / NOT_APPROVED / ORDERS=0 / REAL_CAPITAL=0",
        "",
    ]
    for block in report["blocks"]:
        lines += [f"## {block['position']}. {block['title']}", "", "```json", json.dumps(block["content"], indent=2, sort_keys=True, ensure_ascii=False), "```", ""]
    lines += ["---", "Generated from canonical reporting state. Missing evidence is explicitly N/D and never inferred.", ""]
    return "\n".join(lines)


def write_outputs(state_path: Path, output_dir: Path, reporting_date: str | None = None) -> tuple[Path, Path, Path]:
    state = load(state_path)
    if not state:
        raise SystemExit("reporting state missing or invalid")
    rdate = reporting_date or str(state.get("reporting_date_utc") or date.today().isoformat())
    report = build(state, rdate)
    report["source_reporting_state_sha256"] = sha256(state_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / f"SHADOW_EXECUTIVE_{rdate}.json"
    md_path = output_dir / f"SHADOW_EXECUTIVE_{rdate}.md"
    latest_path = output_dir / "SHADOW_EXECUTIVE_LATEST.json"
    latest_md = output_dir / "SHADOW_EXECUTIVE_LATEST.md"
    raw = json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    json_path.write_text(raw, encoding="utf-8")
    latest_path.write_text(raw, encoding="utf-8")
    md = render_markdown(report)
    md_path.write_text(md, encoding="utf-8")
    latest_md.write_text(md, encoding="utf-8")
    return json_path, md_path, latest_path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--reporting-date")
    args = parser.parse_args()
    paths = write_outputs(args.state, args.output_dir, args.reporting_date)
    print(json.dumps({"outputs": [str(p) for p in paths], "contract_issue": 297, "orders_generated": 0, "real_capital_used": 0}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
