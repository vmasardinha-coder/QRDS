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
            "v16c": declared.get("v16c") or nd("V16C declaration/prereg absent"),
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
        "schema": "gate_btc.shadow_executive.v1",
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
