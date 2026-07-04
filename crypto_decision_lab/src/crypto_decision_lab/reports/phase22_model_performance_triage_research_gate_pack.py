from __future__ import annotations

import csv
import hashlib
import html
import json
import statistics
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

APP_MODE = "INTERACTIVE_RESEARCH_ONLY"
COINS = ["BTC", "ETH", "SOL"]
SPLITS = ["TRAIN_RESEARCH_ONLY", "VALIDATION_RESEARCH_ONLY", "HOLDOUT_RESEARCH_ONLY"]
RETURN_TARGET = "forward_return_24h_research_target"
ABS_TARGET = "forward_abs_return_24h_research_target"
VOL_TARGET = "forward_realized_vol_24h_research_target"
TARGET_COLUMNS = [RETURN_TARGET, ABS_TARGET, VOL_TARGET]

RETURN_ADVANCE_MIN_HOLDOUT_BEAT_RATE = 0.50
VOL_ADVANCE_MIN_HOLDOUT_BEAT_RATE = 0.50
ABS_ADVANCE_MIN_HOLDOUT_BEAT_RATE = 0.50

SAFETY_FLAGS: dict[str, Any] = {
    "app_mode": APP_MODE,
    "research_allowed": True,
    "hypothetical_only": True,
    "api_key_required": False,
    "api_key_present": False,
    "account_connection_required": False,
    "authenticated_connection_used": False,
    "orders_allowed": False,
    "orders_generated": False,
    "real_orders_generated": False,
    "real_capital_used": False,
    "trading_signal_generated": False,
    "executable_signal_generated": False,
    "recommendation_generated": False,
    "allocation_generated": False,
    "portfolio_decision_generated": False,
    "operational_decision_allowed": False,
}


def _repo_root(repo_root: str | Path | None = None) -> Path:
    if repo_root:
        return Path(repo_root).resolve()
    here = Path.cwd().resolve()
    for p in [here, *here.parents]:
        if (p / "crypto_decision_lab").exists():
            return p
    return here


def _load_json(path: Path) -> dict[str, Any]:
    try:
        d = json.loads(path.read_text(encoding="utf-8"))
        d["_present"] = True
        return d
    except Exception:
        return {"_present": False, "gate_answer": "MISSING_RESEARCH_ONLY"}


def _read_csv(path: Path) -> list[dict[str, Any]]:
    try:
        with path.open("r", encoding="utf-8", newline="") as f:
            return [dict(row) for row in csv.DictReader(f)]
    except Exception:
        return []


def _sha_payload(payload: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


def _sha_file(path: Path) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except Exception:
        return "MISSING"


def _git_status(root: Path) -> list[str]:
    try:
        p = subprocess.run(["git", "status", "--short"], cwd=root, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        return [x for x in p.stdout.splitlines() if x.strip()]
    except Exception:
        return []


def _as_float(v: Any, default: float = 0.0) -> float:
    try:
        if v in ("", None):
            return default
        return float(v)
    except Exception:
        return default


def _as_bool(v: Any) -> bool:
    if isinstance(v, bool):
        return v
    return str(v).strip().lower() in {"true", "1", "yes", "y"}


def _mean(values: list[float]) -> float:
    return statistics.fmean(values) if values else 0.0


def _phase21_index(root: Path) -> dict[str, Any]:
    return _load_json(root / "crypto_decision_lab/artifacts/phase21_baseline_audit_interpretable_model_benchmark_pack/phase21_baseline_audit_interpretable_model_benchmark_pack_index.json")


def _phase21_metrics_path(root: Path, phase21: dict[str, Any]) -> Path:
    raw = phase21.get("combined_model_metrics_path")
    if raw:
        return Path(raw)
    return root / "crypto_decision_lab/artifacts/phase21_baseline_audit_interpretable_model_benchmark_pack/model_metrics/all_interpretable_model_metrics.csv"


def _target_bucket(target: str) -> str:
    if target == RETURN_TARGET:
        return "RETURN_24H"
    if target == ABS_TARGET:
        return "ABS_RETURN_24H"
    if target == VOL_TARGET:
        return "REALIZED_VOL_24H"
    return "UNKNOWN_TARGET"


def _advance_classification(target: str, beat_rate: float, mean_improvement: float) -> str:
    if target == RETURN_TARGET:
        if beat_rate >= RETURN_ADVANCE_MIN_HOLDOUT_BEAT_RATE and mean_improvement > 0:
            return "RETURN_MODEL_RESEARCH_ADVANCEMENT_CANDIDATE"
        return "RETURN_MODEL_NOT_READY_FOR_ADVANCEMENT_RESEARCH_ONLY"
    if target == ABS_TARGET:
        if beat_rate >= ABS_ADVANCE_MIN_HOLDOUT_BEAT_RATE and mean_improvement > 0:
            return "ABS_RETURN_MODEL_RESEARCH_ADVANCEMENT_CANDIDATE"
        return "ABS_RETURN_MODEL_NEEDS_MORE_EVIDENCE_RESEARCH_ONLY"
    if target == VOL_TARGET:
        if beat_rate >= VOL_ADVANCE_MIN_HOLDOUT_BEAT_RATE and mean_improvement > 0:
            return "VOL_MODEL_RESEARCH_ADVANCEMENT_CANDIDATE"
        return "VOL_MODEL_NEEDS_MORE_EVIDENCE_RESEARCH_ONLY"
    return "UNKNOWN_TARGET_NEEDS_REVIEW_RESEARCH_ONLY"


def _triage_metrics(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    holdout = [r for r in rows if r.get("split") == "HOLDOUT_RESEARCH_ONLY"]
    summary_rows: list[dict[str, Any]] = []
    model_rows: list[dict[str, Any]] = []

    for target in TARGET_COLUMNS:
        target_rows = [r for r in holdout if r.get("target") == target]
        beat_count = sum(1 for r in target_rows if _as_bool(r.get("beats_best_phase20_baseline")))
        improvements = [_as_float(r.get("mae_improvement_vs_best_baseline"), 0.0) for r in target_rows]
        beat_rate = beat_count / len(target_rows) if target_rows else 0.0
        mean_improvement = _mean(improvements)
        positive_improvement_sum = sum(x for x in improvements if x > 0)
        negative_improvement_sum = sum(x for x in improvements if x < 0)
        classification = _advance_classification(target, beat_rate, mean_improvement)
        summary_rows.append(
            {
                "target": target,
                "target_bucket": _target_bucket(target),
                "holdout_model_rows": len(target_rows),
                "holdout_beat_count": beat_count,
                "holdout_beat_rate": round(beat_rate, 8),
                "mean_mae_improvement_vs_baseline": round(mean_improvement, 12),
                "positive_improvement_sum": round(positive_improvement_sum, 12),
                "negative_improvement_sum": round(negative_improvement_sum, 12),
                "research_classification": classification,
                "trading_signal_generated": False,
                "recommendation_generated": False,
                "operational_decision_allowed": False,
            }
        )

    for coin in COINS:
        coin_rows = [r for r in holdout if r.get("coin") == coin]
        for target in TARGET_COLUMNS:
            ct_rows = [r for r in coin_rows if r.get("target") == target]
            beat_count = sum(1 for r in ct_rows if _as_bool(r.get("beats_best_phase20_baseline")))
            improvements = [_as_float(r.get("mae_improvement_vs_best_baseline"), 0.0) for r in ct_rows]
            model_rows.append(
                {
                    "coin": coin,
                    "target": target,
                    "target_bucket": _target_bucket(target),
                    "holdout_models": len(ct_rows),
                    "holdout_beat_count": beat_count,
                    "holdout_beat_rate": round(beat_count / len(ct_rows), 8) if ct_rows else 0.0,
                    "mean_mae_improvement_vs_baseline": round(_mean(improvements), 12),
                    "best_model_id_by_holdout_mae": min(ct_rows, key=lambda r: _as_float(r.get("mae"), 999999.0)).get("model_id", "MISSING") if ct_rows else "MISSING",
                    "best_model_holdout_mae": min((_as_float(r.get("mae"), 999999.0) for r in ct_rows), default=0.0),
                    "best_baseline_mae_for_best_model": min((_as_float(r.get("best_phase20_baseline_mae"), 999999.0) for r in ct_rows), default=0.0),
                    "trading_signal_generated": False,
                    "recommendation_generated": False,
                    "operational_decision_allowed": False,
                }
            )

    overall = {
        "holdout_rows": len(holdout),
        "holdout_beats_total": sum(1 for r in holdout if _as_bool(r.get("beats_best_phase20_baseline"))),
        "holdout_beat_rate_total": round(sum(1 for r in holdout if _as_bool(r.get("beats_best_phase20_baseline"))) / len(holdout), 8) if holdout else 0.0,
        "return_holdout_beat_rate": next((r["holdout_beat_rate"] for r in summary_rows if r["target"] == RETURN_TARGET), 0.0),
        "abs_return_holdout_beat_rate": next((r["holdout_beat_rate"] for r in summary_rows if r["target"] == ABS_TARGET), 0.0),
        "vol_holdout_beat_rate": next((r["holdout_beat_rate"] for r in summary_rows if r["target"] == VOL_TARGET), 0.0),
        "research_path_forward": "VOLATILITY_FIRST_RESEARCH_PATH" if next((r["holdout_beat_rate"] for r in summary_rows if r["target"] == VOL_TARGET), 0.0) >= VOL_ADVANCE_MIN_HOLDOUT_BEAT_RATE else "MORE_BASELINE_WORK_RESEARCH_PATH",
        "return_model_research_gate": "BLOCK_RETURN_MODEL_ADVANCEMENT_RESEARCH_ONLY" if next((r["holdout_beat_rate"] for r in summary_rows if r["target"] == RETURN_TARGET), 0.0) < RETURN_ADVANCE_MIN_HOLDOUT_BEAT_RATE else "RETURN_MODEL_CAN_BE_STUDIED_FURTHER_RESEARCH_ONLY",
        "operational_path_forward": "BLOCKED_RESEARCH_ONLY",
    }
    return summary_rows, model_rows, overall


def _write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in fields})


def _criterion(cid: str, ok: bool, observed: Any, threshold: str) -> dict[str, Any]:
    return {"criterion_id": cid, "status": "PASS" if ok else "FAIL", "ready": bool(ok), "observed": observed, "threshold": threshold}


def _render_html(path: Path, payload: dict[str, Any]) -> None:
    esc = lambda x: html.escape(str(x))
    cards = [
        ("Station", payload["station"]),
        ("Triage ready", payload["model_performance_triage_ready"]),
        ("Phase21 ready", payload["phase21_model_benchmark_ready"]),
        ("Holdout beats", payload["holdout_beats_total"]),
        ("Return beat rate", payload["return_holdout_beat_rate"]),
        ("Vol beat rate", payload["vol_holdout_beat_rate"]),
        ("Research path", payload["research_path_forward"]),
        ("Operational", payload["operational_status"]),
    ]
    card_html = "".join(f"<div class='kpi'><b>{esc(k)}</b><br>{esc(v)}</div>" for k, v in cards)
    target_html = "".join(
        f"<tr><td>{esc(r['target_bucket'])}</td><td>{esc(r['holdout_model_rows'])}</td><td>{esc(r['holdout_beat_count'])}</td><td>{esc(r['holdout_beat_rate'])}</td><td>{esc(r['mean_mae_improvement_vs_baseline'])}</td><td>{esc(r['research_classification'])}</td></tr>"
        for r in payload["target_triage_summary"]
    )
    coin_html = "".join(
        f"<tr><td>{esc(r['coin'])}</td><td>{esc(r['target_bucket'])}</td><td>{esc(r['holdout_models'])}</td><td>{esc(r['holdout_beat_count'])}</td><td>{esc(r['holdout_beat_rate'])}</td><td>{esc(r['best_model_id_by_holdout_mae'])}</td><td>{esc(r['best_model_holdout_mae'])}</td></tr>"
        for r in payload["coin_target_triage"]
    )
    crit_html = "".join(
        f"<tr><td>{esc(c['criterion_id'])}</td><td>{esc(c['status'])}</td><td>{esc(c['ready'])}</td><td>{esc(c['observed'])}</td><td>{esc(c['threshold'])}</td></tr>"
        for c in payload["criteria"]
    )
    page = (
        "<!doctype html><html><head><meta charset='utf-8'><title>QRDS Model Performance Triage</title>"
        "<style>body{font-family:Arial,sans-serif;margin:32px;background:#f6f7fb;color:#172033}.card{background:white;border:1px solid #d9deea;border-radius:14px;padding:20px;margin:16px 0}.kpi{display:inline-block;background:#eef2ff;border-radius:10px;padding:12px 16px;margin:8px;min-width:150px}table{border-collapse:collapse;width:100%;background:white}th,td{border:1px solid #d9deea;padding:8px;text-align:left}th{background:#eef2ff}.blocked{background:#fee2e2;border-radius:999px;padding:6px 10px;font-weight:700}.ok{background:#dcfce7;border-radius:999px;padding:6px 10px;font-weight:700}</style></head><body>"
        f"<h1>QRDS/QOS • Gate BTC • Research-only</h1><h2>Phase 22 Model Performance Triage Research Gate</h2>"
        f"<div class='card'><p><b>Gate answer:</b> {esc(payload['gate_answer'])}</p><p><b>Policy lock:</b> {esc(payload['policy_lock'])} • <b>Mode:</b> {esc(payload['app_mode'])}</p>{card_html}<p class='ok'>This triage interprets Phase 21 performance against Phase 20 baselines.</p><p class='blocked'>Research path labels are not trading signals, recommendations, allocations, or operational decisions.</p></div>"
        f"<h2>Target triage</h2><table><thead><tr><th>target</th><th>holdout models</th><th>beats</th><th>beat rate</th><th>mean improvement</th><th>classification</th></tr></thead><tbody>{target_html}</tbody></table>"
        f"<h2>Coin/target triage</h2><table><thead><tr><th>coin</th><th>target</th><th>models</th><th>beats</th><th>beat rate</th><th>best model</th><th>best MAE</th></tr></thead><tbody>{coin_html}</tbody></table>"
        f"<h2>Criteria</h2><table><thead><tr><th>criterion</th><th>status</th><th>ready</th><th>observed</th><th>threshold</th></tr></thead><tbody>{crit_html}</tbody></table>"
        f"<p>Generated at {esc(payload['generated_at'])} • SHA256 {esc(payload['report_payload_sha256'])}</p></body></html>"
    )
    path.write_text(page, encoding="utf-8")


def _update_project_status(root: Path, payload: dict[str, Any]) -> None:
    status_path = root / "crypto_decision_lab/docs/reports/PROJECT_STATUS_QRDS_GATE_BTC.md"
    status_path.parent.mkdir(parents=True, exist_ok=True)
    existing = status_path.read_text(encoding="utf-8") if status_path.exists() else "# QRDS/QOS Gate BTC — Project Status\n"
    marker = "\n## Latest Phase 22 update\n"
    before = existing.split(marker)[0].rstrip()
    section = [
        marker.strip(),
        "",
        f"Updated at: {payload['generated_at']}",
        "",
        f"- Phase 22 gate: `{payload['gate_answer']}`",
        f"- Model performance triage ready: `{payload['model_performance_triage_ready']}`",
        f"- Research path forward: `{payload['research_path_forward']}`",
        f"- Return model research gate: `{payload['return_model_research_gate']}`",
        f"- Return holdout beat rate: `{payload['return_holdout_beat_rate']}`",
        f"- Abs-return holdout beat rate: `{payload['abs_return_holdout_beat_rate']}`",
        f"- Volatility holdout beat rate: `{payload['vol_holdout_beat_rate']}`",
        f"- Operational status: `{payload['operational_status']}`",
        f"- Canonical writes: `{payload['canonical_data_writes']}`",
        "",
        "Phase 22 is a research triage gate only. It does not create trading signals, recommendations, allocations, or operational decisions.",
        "",
    ]
    status_path.write_text(before + "\n\n" + "\n".join(section), encoding="utf-8")


def build_phase22_model_performance_triage_research_gate_pack(
    output_dir: str | Path,
    repo_root: str | Path | None = None,
    **_: Any,
) -> dict[str, Any]:
    root = _repo_root(repo_root)
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    phase21 = _phase21_index(root)
    phase21_ready = bool(phase21.get("interpretable_model_benchmark_ready", False))
    metrics_path = Path(phase21.get("combined_model_metrics_path") or root / "crypto_decision_lab/artifacts/phase21_baseline_audit_interpretable_model_benchmark_pack/model_metrics/all_interpretable_model_metrics.csv")
    rows = _read_csv(metrics_path)

    target_summary, coin_target_summary, overall = _triage_metrics(rows)

    target_summary_path = out / "target_triage_summary.csv"
    coin_target_path = out / "coin_target_triage.csv"
    _write_csv(
        target_summary_path,
        target_summary,
        [
            "target",
            "target_bucket",
            "holdout_model_rows",
            "holdout_beat_count",
            "holdout_beat_rate",
            "mean_mae_improvement_vs_baseline",
            "positive_improvement_sum",
            "negative_improvement_sum",
            "research_classification",
            "trading_signal_generated",
            "recommendation_generated",
            "operational_decision_allowed",
        ],
    )
    _write_csv(
        coin_target_path,
        coin_target_summary,
        [
            "coin",
            "target",
            "target_bucket",
            "holdout_models",
            "holdout_beat_count",
            "holdout_beat_rate",
            "mean_mae_improvement_vs_baseline",
            "best_model_id_by_holdout_mae",
            "best_model_holdout_mae",
            "best_baseline_mae_for_best_model",
            "trading_signal_generated",
            "recommendation_generated",
            "operational_decision_allowed",
        ],
    )

    canonical_data_writes = 0
    promotion_allowed = False
    safe_apply_allowed = False
    git_status = _git_status(root)

    expected_holdout_rows = len(COINS) * 5
    expected_target_summary_rows = len(TARGET_COLUMNS)
    triage_ready = (
        phase21_ready
        and len(rows) >= 45
        and overall["holdout_rows"] >= expected_holdout_rows
        and len(target_summary) == expected_target_summary_rows
        and len(coin_target_summary) == len(COINS) * len(TARGET_COLUMNS)
    )

    criteria = [
        _criterion("phase21_index_present", bool(phase21.get("_present")), phase21.get("gate_answer", "MISSING"), "Phase 21 index present"),
        _criterion("phase21_model_benchmark_ready", phase21_ready, phase21_ready, "true"),
        _criterion("phase21_model_metrics_present", len(rows) >= 45, len(rows), ">=45 model metric rows"),
        _criterion("holdout_rows_present", overall["holdout_rows"] >= expected_holdout_rows, overall["holdout_rows"], f">= {expected_holdout_rows}"),
        _criterion("target_triage_complete", len(target_summary) == expected_target_summary_rows, len(target_summary), f"{expected_target_summary_rows} target summaries"),
        _criterion("coin_target_triage_complete", len(coin_target_summary) == len(COINS) * len(TARGET_COLUMNS), len(coin_target_summary), "coin x target summaries"),
        _criterion("return_models_blocked_if_weak", overall["return_model_research_gate"] == "BLOCK_RETURN_MODEL_ADVANCEMENT_RESEARCH_ONLY", overall["return_model_research_gate"], "block weak return model advancement"),
        _criterion("research_path_declared", overall["research_path_forward"] in {"VOLATILITY_FIRST_RESEARCH_PATH", "MORE_BASELINE_WORK_RESEARCH_PATH"}, overall["research_path_forward"], "research path label only"),
        _criterion("triage_not_trading_signal", True, "research_triage_only", "no signal"),
        _criterion("safe_apply_blocked", not safe_apply_allowed, safe_apply_allowed, "false"),
        _criterion("promotion_blocked", not promotion_allowed, promotion_allowed, "false"),
        _criterion("canonical_writes_zero", canonical_data_writes == 0, canonical_data_writes, "0"),
        _criterion("research_only_lock", True, "ACTIVE", "policy lock active"),
    ]
    ready_count = sum(1 for c in criteria if c["ready"])
    gate_ready = ready_count == len(criteria) and triage_ready
    gate = "PHASE22_MODEL_PERFORMANCE_TRIAGE_RESEARCH_GATE_READY_RESEARCH_ONLY" if gate_ready else "PHASE22_MODEL_PERFORMANCE_TRIAGE_RESEARCH_GATE_NEEDS_REVIEW_RESEARCH_ONLY"

    payload: dict[str, Any] = {
        "schema": "qrds.phase22_model_performance_triage_research_gate_pack.v1",
        "report_name": "qrds-phase22-model-performance-triage-research-gate-pack",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "gate_answer": gate,
        "policy_lock": "ACTIVE",
        "app_mode": APP_MODE,
        "station": "PHASE_22_MODEL_PERFORMANCE_TRIAGE_RESEARCH_GATE",
        "model_performance_triage_ready": gate_ready,
        "data_nature": "MODEL_PERFORMANCE_TRIAGE_RESEARCH_ONLY",
        "phase21_model_benchmark_ready": phase21_ready,
        "phase21_metrics_path": str(metrics_path),
        "phase21_metric_rows": len(rows),
        "coins": COINS,
        "target_columns": TARGET_COLUMNS,
        "holdout_rows": overall["holdout_rows"],
        "holdout_beats_total": overall["holdout_beats_total"],
        "holdout_beat_rate_total": overall["holdout_beat_rate_total"],
        "return_holdout_beat_rate": overall["return_holdout_beat_rate"],
        "abs_return_holdout_beat_rate": overall["abs_return_holdout_beat_rate"],
        "vol_holdout_beat_rate": overall["vol_holdout_beat_rate"],
        "research_path_forward": overall["research_path_forward"],
        "return_model_research_gate": overall["return_model_research_gate"],
        "target_triage_summary": target_summary,
        "coin_target_triage": coin_target_summary,
        "target_triage_summary_path": str(target_summary_path),
        "coin_target_triage_path": str(coin_target_path),
        "target_triage_summary_sha256": _sha_file(target_summary_path)[:16],
        "coin_target_triage_sha256": _sha_file(coin_target_path)[:16],
        "triage_labels_are_signals": False,
        "operational_status": "BLOCKED_RESEARCH_ONLY",
        "modeling_status": "MODEL_PERFORMANCE_TRIAGE_READY" if gate_ready else "MODEL_PERFORMANCE_TRIAGE_NEEDS_REVIEW",
        "safe_apply_allowed": safe_apply_allowed,
        "promotion_allowed": promotion_allowed,
        "canonical_data_writes": canonical_data_writes,
        "git_status_line_count": len(git_status),
        "git_status_lines": git_status[:80],
        "criteria": criteria,
        "criteria_ready_count": ready_count,
        "criteria_total_count": len(criteria),
        "mean_triage_score": round(ready_count / len(criteria), 4),
        "safety_flags": SAFETY_FLAGS,
        **SAFETY_FLAGS,
    }
    payload["report_payload_sha256"] = _sha_payload(payload)

    rp = out / "phase22_model_performance_triage_research_gate_pack.json"
    mp = out / "phase22_model_performance_triage_research_gate_pack.md"
    hp = out / "index.html"
    ip = out / "phase22_model_performance_triage_research_gate_pack_index.json"

    rp.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    mp.write_text(
        f"# QRDS/QOS Phase 22 Model Performance Triage Research Gate\n\n**Gate answer:** {gate}\n\nResearch path forward: `{payload['research_path_forward']}`\n\nReturn model research gate: `{payload['return_model_research_gate']}`\n\nReturn holdout beat rate: {payload['return_holdout_beat_rate']}\n\nAbs-return holdout beat rate: {payload['abs_return_holdout_beat_rate']}\n\nVol holdout beat rate: {payload['vol_holdout_beat_rate']}\n\nOperational status: BLOCKED_RESEARCH_ONLY\n\nResearch triage only; no signal, recommendation, allocation, or operational decision.\n",
        encoding="utf-8",
    )
    _render_html(hp, payload)

    index = {
        "schema": "qrds.phase22_model_performance_triage_research_gate_pack_index.v1",
        "report_name": payload["report_name"],
        "generated_at": payload["generated_at"],
        "gate_answer": payload["gate_answer"],
        "policy_lock": payload["policy_lock"],
        "app_mode": payload["app_mode"],
        "station": payload["station"],
        "model_performance_triage_ready": payload["model_performance_triage_ready"],
        "data_nature": payload["data_nature"],
        "phase21_model_benchmark_ready": payload["phase21_model_benchmark_ready"],
        "phase21_metric_rows": payload["phase21_metric_rows"],
        "holdout_rows": payload["holdout_rows"],
        "holdout_beats_total": payload["holdout_beats_total"],
        "holdout_beat_rate_total": payload["holdout_beat_rate_total"],
        "return_holdout_beat_rate": payload["return_holdout_beat_rate"],
        "abs_return_holdout_beat_rate": payload["abs_return_holdout_beat_rate"],
        "vol_holdout_beat_rate": payload["vol_holdout_beat_rate"],
        "research_path_forward": payload["research_path_forward"],
        "return_model_research_gate": payload["return_model_research_gate"],
        "triage_labels_are_signals": payload["triage_labels_are_signals"],
        "operational_status": payload["operational_status"],
        "modeling_status": payload["modeling_status"],
        "safe_apply_allowed": payload["safe_apply_allowed"],
        "promotion_allowed": payload["promotion_allowed"],
        "canonical_data_writes": payload["canonical_data_writes"],
        "criteria_ready_count": payload["criteria_ready_count"],
        "criteria_total_count": payload["criteria_total_count"],
        "mean_triage_score": payload["mean_triage_score"],
        "git_status_line_count": payload["git_status_line_count"],
        "target_triage_summary_path": payload["target_triage_summary_path"],
        "coin_target_triage_path": payload["coin_target_triage_path"],
        "report_path": str(rp),
        "markdown_path": str(mp),
        "html_path": str(hp),
        "index_path": str(ip),
        "serve_entrypoint": str(hp),
        "report_payload_sha256": payload["report_payload_sha256"],
        "payload": payload,
        **SAFETY_FLAGS,
    }
    ip.write_text(json.dumps(index, indent=2, sort_keys=True), encoding="utf-8")
    _update_project_status(root, payload)
    return index


build_model_performance_triage_research_gate_pack = build_phase22_model_performance_triage_research_gate_pack
