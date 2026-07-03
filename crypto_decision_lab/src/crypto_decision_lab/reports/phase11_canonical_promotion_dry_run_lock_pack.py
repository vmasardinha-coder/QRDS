from __future__ import annotations

import hashlib
import html
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

APP_MODE = "INTERACTIVE_RESEARCH_ONLY"

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

TARGET_ROWS_PER_SYMBOL = 5000


def _repo_root(repo_root: str | Path | None = None) -> Path:
    if repo_root:
        return Path(repo_root).resolve()
    here = Path.cwd().resolve()
    for p in [here, *here.parents]:
        if (p / "crypto_decision_lab").exists():
            return p
    return here


def _load_json(root: Path, rel_path: str) -> dict[str, Any]:
    p = root / rel_path
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
        d["_present"] = True
        return d
    except Exception:
        return {"_present": False, "gate_answer": "MISSING_RESEARCH_ONLY"}


def _payload(d: dict[str, Any]) -> dict[str, Any]:
    return d.get("payload") if isinstance(d.get("payload"), dict) else {}


def _field(d: dict[str, Any], key: str, default: Any = None) -> Any:
    if key in d:
        return d[key]
    return _payload(d).get(key, default)


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                obj = json.loads(line)
                if isinstance(obj, dict):
                    rows.append(obj)
    except Exception:
        return []
    return rows


def _sha_file(path: Path) -> str:
    try:
        h = hashlib.sha256()
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()
    except Exception:
        return "MISSING"


def _git_status(root: Path) -> list[str]:
    try:
        p = subprocess.run(["git", "status", "--short"], cwd=root, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        return [x for x in p.stdout.splitlines() if x.strip()]
    except Exception:
        return []


def _manifest(root: Path) -> tuple[bool, str, dict[str, Any]]:
    idx = _load_json(root, "crypto_decision_lab/artifacts/phase10_offline_sample_intake_promotion_pack/phase10_offline_sample_intake_promotion_pack_index.json")
    man = _field(idx, "validated_staging_manifest", {})
    if isinstance(man, dict) and isinstance(man.get("entries"), list):
        return bool(idx.get("_present")), str(idx.get("gate_answer", "MISSING")), man
    p = root / "crypto_decision_lab/artifacts/phase10_offline_sample_intake_promotion_pack/validated_staging/validated_staging_manifest.json"
    try:
        return bool(idx.get("_present")), str(idx.get("gate_answer", "MISSING")), json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return bool(idx.get("_present")), str(idx.get("gate_answer", "MISSING")), {"entries": []}


def _quality(root: Path) -> dict[str, Any]:
    idx = _load_json(root, "crypto_decision_lab/artifacts/phase10_sample_quality_promotion_gate_pack/phase10_sample_quality_promotion_gate_pack_index.json")
    return {
        "present": bool(idx.get("_present")),
        "gate_answer": idx.get("gate_answer", "MISSING"),
        "sample_quality_ready": bool(_field(idx, "sample_quality_ready", False)),
        "full_depth_ready": bool(_field(idx, "full_depth_ready", False)),
        "promotion_allowed": bool(_field(idx, "promotion_allowed", False)),
        "canonical_data_writes": int(_field(idx, "canonical_data_writes", 0) or 0),
    }


def _canonical_path(root: Path, symbol: str, interval: str) -> Path:
    return root / "crypto_decision_lab" / "data" / "research" / symbol.lower().replace("-", "_") / interval / "canonical_ohlcv.jsonl"


def _candidates(root: Path, man: dict[str, Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    entries = man.get("entries") if isinstance(man, dict) else []
    if not isinstance(entries, list):
        entries = []
    for e in entries:
        if not isinstance(e, dict):
            continue
        symbol = str(e.get("symbol") or "UNKNOWN")
        interval = str(e.get("interval") or "1h")
        sf = Path(str(e.get("staging_file") or ""))
        if not sf.is_absolute():
            sf = root / sf
        rows = _read_jsonl(sf)
        cp = _canonical_path(root, symbol, interval)
        existing = _read_jsonl(cp) if cp.exists() else []
        out.append({
            "symbol": symbol,
            "interval": interval,
            "staging_file": str(sf),
            "staging_file_present": sf.exists(),
            "staging_rows": len(rows),
            "staging_sha256": _sha_file(sf)[:16],
            "canonical_path": str(cp),
            "canonical_exists": cp.exists(),
            "existing_canonical_rows": len(existing),
            "would_create": not cp.exists(),
            "would_append_rows": len(rows),
            "would_overwrite": False,
            "safe_apply_allowed": False,
            "canonical_write_allowed": False,
            "status": "DRY_RUN_ONLY_REVIEW_BLOCKED_RESEARCH_ONLY",
        })
    return out


def _criteria(sample_present: bool, quality: dict[str, Any], candidates: list[dict[str, Any]], blockers: list[str]) -> list[dict[str, Any]]:
    def c(cid: str, ok: bool, obs: Any, threshold: str, status: str | None = None) -> dict[str, Any]:
        return {"criterion_id": cid, "status": status or ("PASS" if ok else "FAIL"), "ready": bool(ok), "observed": obs, "threshold": threshold}
    return [
        c("sample_pack_present", sample_present, sample_present, "true"),
        c("quality_pack_present", quality["present"], quality["present"], "true"),
        c("promotion_candidates_present", bool(candidates), len(candidates), ">0"),
        c("sample_quality_ready", quality["sample_quality_ready"], quality["sample_quality_ready"], "true", "PASS" if quality["sample_quality_ready"] else "WARN"),
        c("full_depth_blocks_safe_apply", not quality["full_depth_ready"], quality["full_depth_ready"], "false"),
        c("safe_apply_blocked", True, False, "safe apply remains false"),
        c("promotion_blocked", True, False, "promotion remains false"),
        c("artifact_only_dry_run", True, 0, "0 canonical writes"),
        c("research_only_lock", True, "ACTIVE", "policy lock active"),
    ]


def _blockers(quality: dict[str, Any], candidates: list[dict[str, Any]]) -> list[str]:
    b: list[str] = []
    if not quality["present"]:
        b.append("missing_quality_pack")
    if not quality["sample_quality_ready"]:
        b.append("sample_quality_not_ready")
    if not quality["full_depth_ready"]:
        b.append("full_depth_not_ready")
    if not candidates:
        b.append("no_staging_candidates")
    if any(not x["staging_file_present"] for x in candidates):
        b.append("missing_staging_file")
    if any(x["staging_rows"] <= 0 for x in candidates):
        b.append("empty_staging_candidate")
    return b


def _write_html(path: Path, payload: dict[str, Any]) -> None:
    esc = lambda x: html.escape(str(x))
    cards = [
        ("Station", payload["station"]),
        ("Candidates", payload["promotion_candidates_count"]),
        ("Candidate rows", payload["total_candidate_rows"]),
        ("Sample quality", payload["sample_quality_ready"]),
        ("Full depth", payload["full_depth_ready"]),
        ("Safe apply", payload["safe_apply_allowed"]),
        ("Promotion allowed", payload["promotion_allowed"]),
        ("Canonical writes", payload["canonical_data_writes"]),
        ("Mean score", payload["mean_lock_score"]),
    ]
    card_html = "".join(f"<div class='kpi'><b>{esc(k)}</b><br>{esc(v)}</div>" for k, v in cards)
    rows = "".join(
        f"<tr><td>{esc(x['symbol'])}</td><td>{esc(x['interval'])}</td><td>{esc(x['staging_rows'])}</td><td>{esc(x['existing_canonical_rows'])}</td><td>{esc(x['would_create'])}</td><td>{esc(x['safe_apply_allowed'])}</td><td>{esc(x['status'])}</td></tr>"
        for x in payload["promotion_candidates"]
    ) or "<tr><td>NONE</td><td>NONE</td><td>0</td><td>0</td><td>False</td><td>False</td><td>MISSING</td></tr>"
    crit = "".join(
        f"<tr><td>{esc(c['criterion_id'])}</td><td>{esc(c['status'])}</td><td>{esc(c['ready'])}</td><td>{esc(c['observed'])}</td><td>{esc(c['threshold'])}</td></tr>"
        for c in payload["criteria"]
    )
    page = f"""<!doctype html><html><head><meta charset='utf-8'><title>QRDS Phase 11 Promotion Dry-Run Lock</title>
<style>body{{font-family:Arial,sans-serif;margin:32px;background:#f6f7fb;color:#172033}}.card{{background:white;border:1px solid #d9deea;border-radius:14px;padding:20px;margin:16px 0}}.kpi{{display:inline-block;background:#eef2ff;border-radius:10px;padding:12px 16px;margin:8px;min-width:150px}}table{{border-collapse:collapse;width:100%;background:white}}th,td{{border:1px solid #d9deea;padding:8px;text-align:left}}th{{background:#eef2ff}}.blocked{{background:#fee2e2;border-radius:999px;padding:6px 10px;font-weight:700}}</style></head><body>
<h1>QRDS/QOS • Gate BTC • Research-only</h1><h2>Phase 11 Canonical Promotion Dry-Run Lock Pack</h2>
<div class='card'><p><b>Gate answer:</b> {esc(payload['gate_answer'])}</p><p><b>Policy lock:</b> {esc(payload['policy_lock'])} • <b>Mode:</b> {esc(payload['app_mode'])}</p>{card_html}<p class='blocked'>Safe apply blocked: {esc(', '.join(payload['promotion_blockers']) or 'NONE')}</p><p>Safety lock remains active for account access, order flow, execution-style instructions, and live-fund workflow markers.</p></div>
<h2>Promotion dry-run candidates</h2><table><thead><tr><th>symbol</th><th>interval</th><th>staging_rows</th><th>existing_canonical_rows</th><th>would_create</th><th>safe_apply_allowed</th><th>status</th></tr></thead><tbody>{rows}</tbody></table>
<h2>Criteria</h2><table><thead><tr><th>criterion_id</th><th>status</th><th>ready</th><th>observed</th><th>threshold</th></tr></thead><tbody>{crit}</tbody></table>
<p>Generated at {esc(payload['generated_at'])} • SHA256 {esc(payload['report_payload_sha256'])}</p></body></html>"""
    path.write_text(page, encoding="utf-8")


def _write_md(path: Path, payload: dict[str, Any]) -> None:
    text = f"""# QRDS/QOS Phase 11 Canonical Promotion Dry-Run Lock Pack

**Gate answer:** {payload['gate_answer']}

**Policy lock:** {payload['policy_lock']} • **Mode:** {payload['app_mode']}

This pack creates a dry-run diff from validated staging rows to future canonical paths. It does not write into canonical data directories.

## Summary

- Sample pack present: {payload['sample_pack_present']}
- Quality pack present: {payload['quality_pack_present']}
- Sample quality ready: {payload['sample_quality_ready']}
- Full depth ready: {payload['full_depth_ready']}
- Promotion candidates: {payload['promotion_candidates_count']}
- Total candidate rows: {payload['total_candidate_rows']}
- Existing canonical rows: {payload['existing_canonical_rows']}
- Safe apply allowed: {payload['safe_apply_allowed']}
- Promotion allowed: {payload['promotion_allowed']}
- Canonical data writes: {payload['canonical_data_writes']}
- Blockers: {', '.join(payload['promotion_blockers']) or 'NONE'}

Safe apply remains blocked until data depth and review gates are satisfied.
"""
    path.write_text(text, encoding="utf-8")


def build_phase11_canonical_promotion_dry_run_lock_pack(output_dir: str | Path, repo_root: str | Path | None = None, **_: Any) -> dict[str, Any]:
    root = _repo_root(repo_root)
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    sample_present, sample_gate, man = _manifest(root)
    quality = _quality(root)
    candidates = _candidates(root, man)
    blockers = _blockers(quality, candidates)
    criteria = _criteria(sample_present, quality, candidates, blockers)
    ready = sum(1 for x in criteria if x["ready"])
    git_status = _git_status(root)

    payload: dict[str, Any] = {
        "schema": "qrds.phase11_canonical_promotion_dry_run_lock_pack.v1",
        "report_name": "qrds-phase11-canonical-promotion-dry-run-lock-pack",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "gate_answer": "PHASE11_CANONICAL_PROMOTION_DRY_RUN_LOCK_READY_RESEARCH_ONLY" if sample_present and quality["present"] and candidates else "PHASE11_CANONICAL_PROMOTION_DRY_RUN_LOCK_NEEDS_REVIEW_RESEARCH_ONLY",
        "policy_lock": "ACTIVE",
        "app_mode": APP_MODE,
        "station": "PHASE_11_CANONICAL_PROMOTION_DRY_RUN_LOCK",
        "sample_pack_present": sample_present,
        "sample_gate_answer": sample_gate,
        "quality_pack_present": quality["present"],
        "quality_gate_answer": quality["gate_answer"],
        "sample_quality_ready": quality["sample_quality_ready"],
        "full_depth_ready": quality["full_depth_ready"],
        "promotion_candidates_count": len(candidates),
        "total_candidate_rows": sum(x["staging_rows"] for x in candidates),
        "existing_canonical_rows": sum(x["existing_canonical_rows"] for x in candidates),
        "safe_apply_allowed": False,
        "promotion_allowed": False,
        "canonical_data_writes": 0,
        "promotion_blockers": blockers,
        "promotion_candidates": candidates,
        "criteria": criteria,
        "criteria_ready_count": ready,
        "criteria_total_count": len(criteria),
        "mean_lock_score": round(ready / len(criteria), 4),
        "git_status_line_count": len(git_status),
        "git_status_lines": git_status[:80],
        "safety_flags": SAFETY_FLAGS,
        **SAFETY_FLAGS,
    }
    payload["report_payload_sha256"] = hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()

    report_path = out / "phase11_canonical_promotion_dry_run_lock_pack.json"
    md_path = out / "phase11_canonical_promotion_dry_run_lock_pack.md"
    html_path = out / "index.html"
    index_path = out / "phase11_canonical_promotion_dry_run_lock_pack_index.json"

    report_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    _write_md(md_path, payload)
    _write_html(html_path, payload)

    index = {
        "schema": "qrds.phase11_canonical_promotion_dry_run_lock_pack_index.v1",
        "report_name": payload["report_name"],
        "generated_at": payload["generated_at"],
        "gate_answer": payload["gate_answer"],
        "policy_lock": payload["policy_lock"],
        "app_mode": payload["app_mode"],
        "station": payload["station"],
        "sample_pack_present": payload["sample_pack_present"],
        "quality_pack_present": payload["quality_pack_present"],
        "sample_quality_ready": payload["sample_quality_ready"],
        "full_depth_ready": payload["full_depth_ready"],
        "promotion_candidates_count": payload["promotion_candidates_count"],
        "total_candidate_rows": payload["total_candidate_rows"],
        "existing_canonical_rows": payload["existing_canonical_rows"],
        "safe_apply_allowed": payload["safe_apply_allowed"],
        "promotion_allowed": payload["promotion_allowed"],
        "canonical_data_writes": payload["canonical_data_writes"],
        "promotion_blockers": payload["promotion_blockers"],
        "criteria_ready_count": payload["criteria_ready_count"],
        "criteria_total_count": payload["criteria_total_count"],
        "mean_lock_score": payload["mean_lock_score"],
        "git_status_line_count": payload["git_status_line_count"],
        "report_path": str(report_path),
        "markdown_path": str(md_path),
        "html_path": str(html_path),
        "index_path": str(index_path),
        "serve_entrypoint": str(html_path),
        "report_payload_sha256": payload["report_payload_sha256"],
        "payload": payload,
        **SAFETY_FLAGS,
    }
    index_path.write_text(json.dumps(index, indent=2, sort_keys=True), encoding="utf-8")
    return index


build_phase11_pack = build_phase11_canonical_promotion_dry_run_lock_pack
