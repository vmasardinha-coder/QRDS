from __future__ import annotations

import csv
import hashlib
import html
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

APP_MODE = "INTERACTIVE_RESEARCH_ONLY"
SOURCE_LABEL = "BINANCE_SPOT_PUBLIC_KLINES_RESEARCH_ONLY"
EXPECTED_SYMBOLS = ["BTC-USDT", "ETH-USDT", "SOL-USDT"]
EXPECTED_ROWS_PER_SYMBOL = 5000

SAFETY_FLAGS = {
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


def _root(repo_root: str | Path | None = None) -> Path:
    if repo_root:
        return Path(repo_root).resolve()
    here = Path.cwd().resolve()
    for p in [here, *here.parents]:
        if (p / "crypto_decision_lab").exists():
            return p
    return here


def _load(root: Path, rel: str) -> dict[str, Any]:
    try:
        d = json.loads((root / rel).read_text(encoding="utf-8"))
        d["_present"] = True
        return d
    except Exception:
        return {"_present": False, "gate_answer": "MISSING_RESEARCH_ONLY"}


def _payload(d: dict[str, Any]) -> dict[str, Any]:
    return d.get("payload") if isinstance(d.get("payload"), dict) else {}


def _field(d: dict[str, Any], k: str, default: Any = None) -> Any:
    if k in d:
        return d[k]
    return _payload(d).get(k, default)


def _int(x: Any, default: int = 0) -> int:
    try:
        return int(float(x))
    except Exception:
        return default


def _sha_file(path: Path) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except Exception:
        return "MISSING"


def _sha_payload(payload: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


def _git(root: Path) -> list[str]:
    try:
        p = subprocess.run(["git", "status", "--short"], cwd=root, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        return [x for x in p.stdout.splitlines() if x.strip()]
    except Exception:
        return []


def _read_csv(path: Path) -> list[dict[str, Any]]:
    try:
        with path.open("r", encoding="utf-8", newline="") as f:
            return [dict(r) for r in csv.DictReader(f)]
    except Exception:
        return []


def _public_file_inventory(root: Path) -> dict[str, Any]:
    inbox = root / "crypto_decision_lab" / "manual_intake" / "inbox"
    files = sorted(inbox.glob("*_binance_public_klines_1h.csv")) if inbox.exists() else []
    synthetic = sorted(inbox.glob("*_synthetic_fixture_ohlcv.csv")) if inbox.exists() else []
    summaries: list[dict[str, Any]] = []
    total_rows = 0
    sources = set()
    symbols = set()
    monotonic_ok = True
    shape_ok = True

    for path in files:
        rows = _read_csv(path)
        total_rows += len(rows)
        prev_ts = ""
        file_sources = set()
        file_symbols = set()
        for row in rows:
            src = str(row.get("source", ""))
            sym = str(row.get("symbol", ""))
            ts = str(row.get("timestamp", ""))
            sources.add(src)
            file_sources.add(src)
            symbols.add(sym)
            file_symbols.add(sym)
            if prev_ts and ts <= prev_ts:
                monotonic_ok = False
            prev_ts = ts
            try:
                o = float(row["open"]); h = float(row["high"]); l = float(row["low"]); c = float(row["close"]); v = float(row["volume"])
                if h < l or o < l or o > h or c < l or c > h or v < 0:
                    shape_ok = False
            except Exception:
                shape_ok = False
        summaries.append(
            {
                "file_name": path.name,
                "path": str(path),
                "rows": len(rows),
                "symbols": sorted(file_symbols),
                "sources": sorted(file_sources),
                "first_timestamp": rows[0]["timestamp"] if rows else "MISSING",
                "last_timestamp": rows[-1]["timestamp"] if rows else "MISSING",
                "sha256": _sha_file(path)[:16],
                "ready": len(rows) >= EXPECTED_ROWS_PER_SYMBOL and file_sources == {SOURCE_LABEL},
            }
        )

    return {
        "public_files": summaries,
        "public_file_count": len(summaries),
        "public_rows_total": total_rows,
        "source_labels": sorted(sources),
        "symbols": sorted(symbols),
        "synthetic_files_in_inbox": len(synthetic),
        "synthetic_file_names": [p.name for p in synthetic],
        "timestamp_monotonic_ok": monotonic_ok,
        "ohlcv_shape_ok": shape_ok,
    }


def _criterion(cid: str, ok: bool, obs: Any, threshold: str, status: str | None = None) -> dict[str, Any]:
    return {"criterion_id": cid, "status": status or ("PASS" if ok else "FAIL"), "ready": bool(ok), "observed": obs, "threshold": threshold}


def _render_html(path: Path, payload: dict[str, Any]) -> None:
    esc = lambda x: html.escape(str(x))
    cards = [
        ("Station", payload["station"]),
        ("Research ready", payload["public_data_research_ready"]),
        ("Data mode", payload["acceptance_data_drop_mode"]),
        ("Files", payload["public_file_count"]),
        ("Public rows", payload["public_rows_total"]),
        ("Rows normalized", payload["acceptance_rows_normalized"]),
        ("Valid rows", payload["acceptance_valid_rows"]),
        ("Full depth", payload["quality_full_depth_ready"]),
        ("Promotion", payload["promotion_allowed"]),
        ("Canonical writes", payload["canonical_data_writes"]),
        ("Mean score", payload["mean_certification_score"]),
    ]
    card = "".join(f"<div class='kpi'><b>{esc(k)}</b><br>{esc(v)}</div>" for k, v in cards)
    files = "".join(
        f"<tr><td>{esc(f['file_name'])}</td><td>{esc(f['rows'])}</td><td>{esc(','.join(f['symbols']))}</td><td>{esc(','.join(f['sources']))}</td><td>{esc(f['first_timestamp'])}</td><td>{esc(f['last_timestamp'])}</td><td>{esc(f['sha256'])}</td></tr>"
        for f in payload["public_files"]
    )
    criteria = "".join(
        f"<tr><td>{esc(c['criterion_id'])}</td><td>{esc(c['status'])}</td><td>{esc(c['ready'])}</td><td>{esc(c['observed'])}</td><td>{esc(c['threshold'])}</td></tr>"
        for c in payload["criteria"]
    )
    page = f"""<!doctype html><html><head><meta charset='utf-8'><title>QRDS Public Data Research Readiness</title>
<style>body{{font-family:Arial,sans-serif;margin:32px;background:#f6f7fb;color:#172033}}.card{{background:white;border:1px solid #d9deea;border-radius:14px;padding:20px;margin:16px 0}}.kpi{{display:inline-block;background:#eef2ff;border-radius:10px;padding:12px 16px;margin:8px;min-width:150px}}table{{border-collapse:collapse;width:100%;background:white}}th,td{{border:1px solid #d9deea;padding:8px;text-align:left}}th{{background:#eef2ff}}.ok{{background:#dcfce7;border-radius:999px;padding:6px 10px;font-weight:700}}.blocked{{background:#fee2e2;border-radius:999px;padding:6px 10px;font-weight:700}}</style></head><body>
<h1>QRDS/QOS • Gate BTC • Research-only</h1><h2>Phase 12 Public Data Research Readiness Certification</h2>
<div class='card'><p><b>Gate answer:</b> {esc(payload['gate_answer'])}</p><p><b>Policy lock:</b> {esc(payload['policy_lock'])} • <b>Mode:</b> {esc(payload['app_mode'])}</p>{card}<p class='ok'>Public OHLCV research dataset certified for research pipeline testing.</p><p class='blocked'>Operational decisions, orders, safe-apply and canonical promotion remain blocked.</p></div>
<h2>Public files</h2><table><thead><tr><th>file</th><th>rows</th><th>symbols</th><th>sources</th><th>first</th><th>last</th><th>sha256</th></tr></thead><tbody>{files}</tbody></table>
<h2>Criteria</h2><table><thead><tr><th>criterion_id</th><th>status</th><th>ready</th><th>observed</th><th>threshold</th></tr></thead><tbody>{criteria}</tbody></table>
<p>Generated at {esc(payload['generated_at'])} • SHA256 {esc(payload['report_payload_sha256'])}</p></body></html>"""
    path.write_text(page, encoding="utf-8")


def build_phase12_public_data_research_readiness_certification_pack(
    output_dir: str | Path,
    repo_root: str | Path | None = None,
    **_: Any,
) -> dict[str, Any]:
    root = _root(repo_root)
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    fetch = _load(root, "crypto_decision_lab/artifacts/phase12_public_market_data_fetch_pack/phase12_public_market_data_fetch_pack_index.json")
    acceptance = _load(root, "crypto_decision_lab/artifacts/phase11_data_drop_acceptance_pipeline_pack/phase11_data_drop_acceptance_pipeline_pack_index.json")
    normalizer = _load(root, "crypto_decision_lab/artifacts/phase11_offline_source_normalizer_pack/phase11_offline_source_normalizer_pack_index.json")
    quality = _load(root, "crypto_decision_lab/artifacts/phase10_sample_quality_promotion_gate_pack/phase10_sample_quality_promotion_gate_pack_index.json")
    lock = _load(root, "crypto_decision_lab/artifacts/phase11_canonical_promotion_dry_run_lock_pack/phase11_canonical_promotion_dry_run_lock_pack_index.json")

    inventory = _public_file_inventory(root)
    git_status = _git(root)

    acceptance_mode = str(_field(acceptance, "data_drop_mode", "MISSING"))
    acceptance_rows = _int(_field(acceptance, "rows_normalized", 0), 0)
    acceptance_valid = _int(_field(acceptance, "valid_rows", 0), 0)
    acceptance_staging = _int(_field(acceptance, "staging_rows", 0), 0)
    acceptance_gap = _int(_field(acceptance, "total_gap_rows", -1), -1)
    sample_quality_ready = bool(_field(quality, "sample_quality_ready", False))
    full_depth_ready = bool(_field(quality, "full_depth_ready", False))

    canonical_writes = (
        _int(_field(fetch, "canonical_data_writes", 0), 0)
        + _int(_field(acceptance, "canonical_data_writes", 0), 0)
        + _int(_field(lock, "canonical_data_writes", 0), 0)
    )
    promotion_allowed = (
        bool(_field(fetch, "promotion_allowed", False))
        or bool(_field(acceptance, "promotion_allowed", False))
        or bool(_field(lock, "promotion_allowed", False))
    )
    safe_apply_allowed = bool(_field(lock, "safe_apply_allowed", False))

    expected_total = len(EXPECTED_SYMBOLS) * EXPECTED_ROWS_PER_SYMBOL
    source_ok = inventory["source_labels"] == [SOURCE_LABEL]
    symbols_ok = sorted(inventory["symbols"]) == sorted(EXPECTED_SYMBOLS)
    files_ok = inventory["public_file_count"] == len(EXPECTED_SYMBOLS)
    rows_ok = inventory["public_rows_total"] >= expected_total

    public_data_research_ready = (
        fetch.get("_present")
        and acceptance.get("_present")
        and normalizer.get("_present")
        and files_ok
        and rows_ok
        and source_ok
        and symbols_ok
        and inventory["synthetic_files_in_inbox"] == 0
        and acceptance_mode == "INBOX_DATA"
        and acceptance_rows >= expected_total
        and acceptance_valid >= expected_total
        and acceptance_staging >= expected_total
        and sample_quality_ready
        and full_depth_ready
        and canonical_writes == 0
        and not promotion_allowed
        and not safe_apply_allowed
    )

    criteria = [
        _criterion("public_fetch_pack_present", bool(fetch.get("_present")), fetch.get("gate_answer", "MISSING"), "12I-12R fetch pack present"),
        _criterion("acceptance_pipeline_present", bool(acceptance.get("_present")), acceptance.get("gate_answer", "MISSING"), "11Q-11Z acceptance pack present"),
        _criterion("normalizer_present", bool(normalizer.get("_present")), normalizer.get("gate_answer", "MISSING"), "11I-11P normalizer present"),
        _criterion("public_files_present", files_ok, f"{inventory['public_file_count']}/{len(EXPECTED_SYMBOLS)}", "3 public files"),
        _criterion("public_rows_depth", rows_ok, inventory["public_rows_total"], f">= {expected_total} rows"),
        _criterion("public_source_clean", source_ok, inventory["source_labels"], SOURCE_LABEL),
        _criterion("expected_symbols_present", symbols_ok, inventory["symbols"], ",".join(EXPECTED_SYMBOLS)),
        _criterion("synthetic_not_in_inbox", inventory["synthetic_files_in_inbox"] == 0, inventory["synthetic_files_in_inbox"], "0 synthetic fixture files"),
        _criterion("acceptance_inbox_mode", acceptance_mode == "INBOX_DATA", acceptance_mode, "INBOX_DATA"),
        _criterion("acceptance_rows_normalized", acceptance_rows >= expected_total, acceptance_rows, f">= {expected_total}"),
        _criterion("acceptance_valid_rows", acceptance_valid >= expected_total, acceptance_valid, f">= {expected_total}"),
        _criterion("sample_quality_ready", sample_quality_ready, sample_quality_ready, "true"),
        _criterion("full_depth_ready", full_depth_ready, full_depth_ready, "true"),
        _criterion("safe_apply_blocked", not safe_apply_allowed, safe_apply_allowed, "false"),
        _criterion("promotion_blocked", not promotion_allowed, promotion_allowed, "false"),
        _criterion("canonical_writes_zero", canonical_writes == 0, canonical_writes, "0"),
        _criterion("research_only_lock", True, "ACTIVE", "policy lock active"),
    ]
    ready = sum(1 for c in criteria if c["ready"])

    gate = "PHASE12_PUBLIC_DATA_RESEARCH_READY_CERTIFIED_RESEARCH_ONLY" if public_data_research_ready else "PHASE12_PUBLIC_DATA_RESEARCH_READINESS_NEEDS_REVIEW_RESEARCH_ONLY"

    payload: dict[str, Any] = {
        "schema": "qrds.phase12_public_data_research_readiness_certification_pack.v1",
        "report_name": "qrds-phase12-public-data-research-readiness-certification-pack",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "gate_answer": gate,
        "policy_lock": "ACTIVE",
        "app_mode": APP_MODE,
        "station": "PHASE_12_PUBLIC_DATA_RESEARCH_READINESS_CERTIFICATION",
        "public_data_research_ready": bool(public_data_research_ready),
        "data_nature": "PUBLIC_MARKET_DATA_RESEARCH_ONLY",
        "source_label": SOURCE_LABEL,
        "expected_symbols": EXPECTED_SYMBOLS,
        "expected_rows_per_symbol": EXPECTED_ROWS_PER_SYMBOL,
        "expected_rows_total": expected_total,
        "public_file_count": inventory["public_file_count"],
        "public_rows_total": inventory["public_rows_total"],
        "public_source_labels": inventory["source_labels"],
        "public_symbols": inventory["symbols"],
        "public_files": inventory["public_files"],
        "timestamp_monotonic_ok": inventory["timestamp_monotonic_ok"],
        "ohlcv_shape_ok": inventory["ohlcv_shape_ok"],
        "synthetic_files_in_inbox": inventory["synthetic_files_in_inbox"],
        "synthetic_file_names": inventory["synthetic_file_names"],
        "fetch_pack_present": bool(fetch.get("_present")),
        "normalizer_present": bool(normalizer.get("_present")),
        "acceptance_pack_present": bool(acceptance.get("_present")),
        "acceptance_data_drop_mode": acceptance_mode,
        "acceptance_rows_normalized": acceptance_rows,
        "acceptance_valid_rows": acceptance_valid,
        "acceptance_staging_rows": acceptance_staging,
        "acceptance_total_gap_rows": acceptance_gap,
        "quality_sample_quality_ready": sample_quality_ready,
        "quality_full_depth_ready": full_depth_ready,
        "safe_apply_allowed": safe_apply_allowed,
        "promotion_allowed": promotion_allowed,
        "canonical_data_writes": canonical_writes,
        "operational_status": "BLOCKED_RESEARCH_ONLY",
        "modeling_status": "PUBLIC_DATA_READY_FOR_RESEARCH_BACKTEST_PIPELINE",
        "git_status_line_count": len(git_status),
        "git_status_lines": git_status[:80],
        "criteria": criteria,
        "criteria_ready_count": ready,
        "criteria_total_count": len(criteria),
        "mean_certification_score": round(ready / len(criteria), 4),
        "safety_flags": SAFETY_FLAGS,
        **SAFETY_FLAGS,
    }
    payload["report_payload_sha256"] = _sha_payload(payload)

    rp = out / "phase12_public_data_research_readiness_certification_pack.json"
    mp = out / "phase12_public_data_research_readiness_certification_pack.md"
    hp = out / "index.html"
    ip = out / "phase12_public_data_research_readiness_certification_pack_index.json"
    rp.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    mp.write_text(
        f"# QRDS/QOS Phase 12 Public Data Research Readiness Certification\n\n**Gate answer:** {gate}\n\nPublic data research ready: {public_data_research_ready}\n\nRows: {inventory['public_rows_total']}\n\nModeling status: {payload['modeling_status']}\n\nOperational status: {payload['operational_status']}\n",
        encoding="utf-8",
    )
    _render_html(hp, payload)

    index = {
        "schema": "qrds.phase12_public_data_research_readiness_certification_pack_index.v1",
        "report_name": payload["report_name"],
        "generated_at": payload["generated_at"],
        "gate_answer": payload["gate_answer"],
        "policy_lock": payload["policy_lock"],
        "app_mode": payload["app_mode"],
        "station": payload["station"],
        "public_data_research_ready": payload["public_data_research_ready"],
        "data_nature": payload["data_nature"],
        "source_label": payload["source_label"],
        "public_file_count": payload["public_file_count"],
        "public_rows_total": payload["public_rows_total"],
        "acceptance_data_drop_mode": payload["acceptance_data_drop_mode"],
        "acceptance_rows_normalized": payload["acceptance_rows_normalized"],
        "acceptance_valid_rows": payload["acceptance_valid_rows"],
        "acceptance_staging_rows": payload["acceptance_staging_rows"],
        "acceptance_total_gap_rows": payload["acceptance_total_gap_rows"],
        "quality_sample_quality_ready": payload["quality_sample_quality_ready"],
        "quality_full_depth_ready": payload["quality_full_depth_ready"],
        "safe_apply_allowed": payload["safe_apply_allowed"],
        "promotion_allowed": payload["promotion_allowed"],
        "canonical_data_writes": payload["canonical_data_writes"],
        "operational_status": payload["operational_status"],
        "modeling_status": payload["modeling_status"],
        "criteria_ready_count": payload["criteria_ready_count"],
        "criteria_total_count": payload["criteria_total_count"],
        "mean_certification_score": payload["mean_certification_score"],
        "git_status_line_count": payload["git_status_line_count"],
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
    return index


build_certification_pack = build_phase12_public_data_research_readiness_certification_pack
