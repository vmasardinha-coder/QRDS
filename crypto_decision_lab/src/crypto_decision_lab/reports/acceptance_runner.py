from __future__ import annotations

import hashlib
import html
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


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

FORBIDDEN_RENDERED_PHRASES = (
    "use real capital",
    "execute trade",
    "trading signal:",
    "buy signal",
    "sell signal",
    "position sizing",
)

REQUIRED_GATES: list[dict[str, str]] = [
    {"gate_id": "8L", "kind": "evidence_quality", "title": "Evidence Quality"},
    {"gate_id": "8M", "kind": "evidence_drilldown", "title": "Evidence Drilldown"},
    {"gate_id": "8N", "kind": "evidence_timeline", "title": "Evidence Timeline"},
    {"gate_id": "8O", "kind": "research_promotion", "title": "Research Promotion"},
    {"gate_id": "8P", "kind": "human_review", "title": "Human Review / Policy Lock"},
    {"gate_id": "8Q", "kind": "oos_validation", "title": "Out-of-Sample Validation"},
    {"gate_id": "8R", "kind": "paper_trading", "title": "Paper Trading"},
    {"gate_id": "8U", "kind": "risk_model", "title": "Risk Model"},
    {"gate_id": "8V", "kind": "operational_security", "title": "Operational Security"},
    {"gate_id": "9B", "kind": "data_coverage", "title": "Data Coverage"},
    {"gate_id": "9C", "kind": "data_quality", "title": "Data Quality"},
    {"gate_id": "9D", "kind": "data_audit", "title": "Data Audit Evidence"},
    {"gate_id": "9E", "kind": "dataset_manifest", "title": "Dataset Manifest"},
]

CANONICAL_REPORT_PATHS = {
    "evidence_quality": [
        "artifacts/evidence_stack/evidence_quality/evidence_quality_gate.json",
        "artifacts/evidence_quality/evidence_quality_gate.json",
    ],
    "evidence_drilldown": [
        "artifacts/evidence_stack/evidence_drilldown/evidence_drilldown_gate.json",
        "artifacts/evidence_drilldown/evidence_drilldown_gate.json",
    ],
    "evidence_timeline": [
        "artifacts/evidence_stack/evidence_timeline/evidence_timeline_gate.json",
        "artifacts/evidence_timeline/evidence_timeline_gate.json",
    ],
    "research_promotion": [
        "artifacts/evidence_stack/research_promotion/research_promotion_gate.json",
        "artifacts/research_promotion/research_promotion_gate.json",
    ],
    "human_review": [
        "artifacts/evidence_stack/human_review/human_review_gate.json",
        "artifacts/human_review/human_review_gate.json",
    ],
    "oos_validation": [
        "artifacts/evidence_stack/oos_validation/oos_validation_gate.json",
        "artifacts/oos_validation/oos_validation_gate.json",
    ],
    "paper_trading": [
        "artifacts/evidence_stack/paper_trading/paper_trading_gate.json",
        "artifacts/paper_trading/paper_trading_gate.json",
    ],
    "risk_model": [
        "artifacts/evidence_stack/risk_model/risk_model_gate.json",
        "artifacts/risk_model/risk_model_gate.json",
    ],
    "operational_security": [
        "artifacts/evidence_stack/operational_security/operational_security_gate.json",
        "artifacts/operational_security/operational_security_gate.json",
    ],
    "data_coverage": [
        "artifacts/data_coverage/data_coverage_gate.json",
    ],
    "data_quality": [
        "artifacts/data_quality/data_quality_gate.json",
    ],
    "data_audit": [
        "artifacts/data_audit/data_audit_gate.json",
        "artifacts/data_audit/data_audit_evidence_pack.json",
    ],
    "dataset_manifest": [
        "artifacts/dataset_manifest/dataset_manifest_pack.json",
        "artifacts/dataset_manifest/dataset_manifest_gate.json",
    ],
}


def _symbols(symbols: str | Iterable[str]) -> list[str]:
    if isinstance(symbols, str):
        return [s.strip() for s in symbols.split(",") if s.strip()]
    return [str(s).strip() for s in symbols if str(s).strip()]


def _resolve_path(path: str | Path) -> Path:
    p = Path(path)
    if p.exists():
        return p
    candidates = [
        Path.cwd() / p,
        Path.cwd().parent / p,
    ]
    raw = str(p)
    if raw.startswith("crypto_decision_lab/"):
        stripped = Path(raw.split("/", 1)[1])
        candidates.extend([Path.cwd() / stripped, Path.cwd().parent / stripped])
    else:
        candidates.extend([
            Path.cwd() / "crypto_decision_lab" / p,
            Path.cwd().parent / "crypto_decision_lab" / p,
        ])
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return p


def _load_json(path: str | Path) -> dict[str, Any]:
    p = _resolve_path(path)
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {
            "report_name": Path(path).stem,
            "gate_answer": "UNREADABLE_INPUT_REPORT_RESEARCH_ONLY",
            "report_payload_sha256": "UNREADABLE",
        }


def _kind_from_payload(payload: dict[str, Any], fallback_path: str | Path) -> str:
    text = " ".join(
        str(payload.get(k, ""))
        for k in ("report_name", "schema", "gate_answer")
    ).lower().replace("-", "_").replace(".", "_")
    fallback = Path(fallback_path).stem.lower().replace("-", "_").replace(".", "_")
    combined = f"{text} {fallback}"

    needles = [
        "evidence_quality",
        "evidence_drilldown",
        "evidence_timeline",
        "research_promotion",
        "human_review",
        "oos_validation",
        "paper_trading",
        "risk_model",
        "operational_security",
        "data_coverage",
        "data_quality",
        "data_audit",
        "dataset_manifest",
        "evidence_stack",
        "housekeeping",
    ]
    for needle in needles:
        if needle in combined:
            return needle
    return fallback


def discover_canonical_reports() -> list[str]:
    found: list[str] = []
    seen: set[str] = set()
    for gate in REQUIRED_GATES:
        kind = gate["kind"]
        for candidate in CANONICAL_REPORT_PATHS.get(kind, []):
            resolved = _resolve_path(candidate)
            if resolved.exists():
                key = str(resolved.resolve())
                if key not in seen:
                    seen.add(key)
                    found.append(str(resolved))
                break
    return found


def _numeric_score(payload: dict[str, Any]) -> float:
    for key in (
        "mean_coverage_score",
        "mean_quality_score",
        "mean_audit_score",
        "mean_manifest_score",
        "mean_research_readiness_score",
        "mean_symbol_evidence_score",
        "mean_latest_score",
        "mean_risk_score",
        "mean_security_score",
        "mean_oos_score",
        "mean_paper_score",
        "mean_score",
    ):
        try:
            value = payload.get(key)
            if value is not None:
                return float(value)
        except Exception:
            pass
    return 0.0


def _is_blocking_answer(answer: str) -> bool:
    upper = answer.upper()
    blocking_tokens = (
        "NO_",
        "INCOMPLETE",
        "MISSING",
        "BLOCK",
        "MORE_",
        "REQUIRED",
        "GAPS",
        "NOT_READY",
    )
    return any(token in upper for token in blocking_tokens)


def _safety_issues(payload: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    for flag, expected in SAFETY_FLAGS.items():
        if flag == "research_allowed":
            if payload.get(flag, True) is not True:
                issues.append(flag)
        elif flag == "hypothetical_only":
            if payload.get(flag, True) is not True:
                issues.append(flag)
        elif flag == "app_mode":
            if payload.get(flag, APP_MODE) != APP_MODE:
                issues.append(flag)
        else:
            if payload.get(flag, False) is not False:
                issues.append(flag)
    return issues


def _normalize_report_row(path: str | Path) -> dict[str, Any]:
    resolved = _resolve_path(path)
    payload = _load_json(path)
    kind = _kind_from_payload(payload, path)
    answer = str(payload.get("gate_answer") or "UNKNOWN_RESEARCH_ONLY")
    status = "REPORT_PRESENT" if resolved.exists() else "MISSING_FILE"
    issues = _safety_issues(payload) if status == "REPORT_PRESENT" else ["missing_or_unreadable"]
    return {
        "kind": kind,
        "path": str(resolved),
        "status": status,
        "gate_answer": answer,
        "ready": bool(payload.get("ready")) and not _is_blocking_answer(answer),
        "blocking": _is_blocking_answer(answer),
        "score": round(_numeric_score(payload), 4),
        "sha256": str(payload.get("report_payload_sha256") or payload.get("sha256") or "MISSING")[:16],
        "safety_ok": not issues,
        "safety_issues": issues,
    }


def _gate_rows(report_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_kind: dict[str, dict[str, Any]] = {}
    for row in report_rows:
        by_kind.setdefault(row["kind"], row)

    rows: list[dict[str, Any]] = []
    for gate in REQUIRED_GATES:
        existing = by_kind.get(gate["kind"])
        if existing:
            rows.append(
                {
                    **gate,
                    "status": existing["status"],
                    "gate_answer": existing["gate_answer"],
                    "ready": existing["ready"],
                    "blocking": existing["blocking"],
                    "score": existing["score"],
                    "sha256": existing["sha256"],
                    "safety_ok": existing["safety_ok"],
                    "path": existing["path"],
                }
            )
        else:
            rows.append(
                {
                    **gate,
                    "status": "MISSING_REPORT",
                    "gate_answer": "MISSING_INPUT_REPORT_RESEARCH_ONLY",
                    "ready": False,
                    "blocking": True,
                    "score": 0.0,
                    "sha256": "MISSING",
                    "safety_ok": False,
                    "path": "MISSING",
                }
            )
    return rows


def _count_suspicious_untracked(git_status_text: str) -> int:
    count = 0
    for line in git_status_text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("?? "):
            continue
        path = stripped[3:]
        if path.startswith(("artifacts/", "crypto_decision_lab/artifacts/")):
            continue
        if path.startswith("qrds_sprint_") and path.endswith(".sh"):
            continue
        count += 1
    return count


def _sha(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _assert_research_only(rendered: str) -> None:
    low = rendered.lower()
    for term in FORBIDDEN_RENDERED_PHRASES:
        if term in low:
            raise ValueError(f"Operational language is not allowed in Acceptance Runner: {term}")


def _table(headers: list[str], rows: list[list[Any]]) -> str:
    out = ["|" + "|".join(headers) + "|", "|" + "|".join(["---"] * len(headers)) + "|"]
    for row in rows:
        out.append("|" + "|".join(str(x) for x in row) + "|")
    return "\n".join(out)


def render_markdown(payload: dict[str, Any]) -> str:
    md = f"""# QRDS/QOS • Gate BTC • Research-only
## Acceptance Runner

One-command local validation summary for the research stack. This packet records test status, gate blockers, workspace hygiene, and policy lock state; it cannot unlock operational use.

**Acceptance status:** {payload["acceptance_status"]}

**Policy lock:** {payload["policy_lock"]} • **Mode:** {payload["app_mode"]}

## Summary

- Reports present: {payload["report_present_count"]}/{payload["required_gate_count"]}
- Blocking gates: {payload["blocking_gate_count"]}
- Safety issues: {payload["safety_issue_count"]}
- Pytest status: {payload["pytest_status"]}
- Suspicious untracked: {payload["suspicious_untracked_count"]}
- Symbols: {", ".join(payload["symbols"])}

Research-only guardrail: no execution, no exchange account, no portfolio allocation output, no trade instruction, no live-fund workflow.

## Gates

{_table(
    ["gate", "title", "status", "ready", "blocking", "answer", "score", "sha256"],
    [[g["gate_id"], g["title"], g["status"], g["ready"], g["blocking"], g["gate_answer"], g["score"], g["sha256"]] for g in payload["gate_rows"]],
)}

## Safety flags

{_table(["flag", "value"], [[k, v] for k, v in payload["safety_flags"].items()])}

## Git status

```text
{payload["git_status_text"] or "clean-or-not-captured"}
```

Generated at {payload["generated_at"]} • SHA256 {payload["report_payload_sha256"]}
"""
    _assert_research_only(md)
    return md


def render_html(payload: dict[str, Any]) -> str:
    def esc(value: Any) -> str:
        return html.escape(str(value))

    cards = "\n".join(
        f"""
        <div class="gate">
          <div class="gate-id">{esc(g['gate_id'])}</div>
          <h3>{esc(g['title'])}</h3>
          <p><b>Status:</b> {esc(g['status'])} • <b>Ready:</b> {esc(g['ready'])} • <b>Blocking:</b> {esc(g['blocking'])}</p>
          <p class="answer">{esc(g['gate_answer'])}</p>
          <p><b>Score:</b> {esc(g['score'])} • <b>SHA:</b> {esc(g['sha256'])}</p>
        </div>
        """
        for g in payload["gate_rows"]
    )

    gate_rows = "\n".join(
        f"<tr><td>{esc(g['gate_id'])}</td><td>{esc(g['title'])}</td><td>{esc(g['status'])}</td><td>{esc(g['ready'])}</td><td>{esc(g['blocking'])}</td><td>{esc(g['gate_answer'])}</td><td>{esc(g['score'])}</td><td>{esc(g['sha256'])}</td></tr>"
        for g in payload["gate_rows"]
    )
    flag_rows = "\n".join(
        f"<tr><td>{esc(k)}</td><td>{esc(v)}</td></tr>"
        for k, v in payload["safety_flags"].items()
    )

    page = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>QRDS Acceptance Runner</title>
<style>
body{{font-family:Arial,sans-serif;margin:32px;background:#f6f7fb;color:#172033}}
.header,.card,.gate{{background:white;border:1px solid #d9deea;border-radius:14px;padding:18px;margin:14px 0;box-shadow:0 1px 3px rgba(0,0,0,.06)}}
.kpi{{display:inline-block;background:#eef2ff;border-radius:10px;padding:12px 16px;margin:8px 8px 8px 0;min-width:130px}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:12px}}
.gate-id{{font-size:13px;font-weight:700;color:#475569}}
.answer{{font-family:monospace;background:#f8fafc;padding:8px;border-radius:8px}}
table{{border-collapse:collapse;width:100%;background:white}}
th,td{{border:1px solid #d9deea;padding:8px;text-align:left;font-size:13px}}
th{{background:#eef2ff}}
pre{{background:#0f172a;color:#e2e8f0;padding:14px;border-radius:10px;overflow:auto}}
.badge{{display:inline-block;border-radius:999px;background:#fee2e2;padding:6px 10px;font-weight:700}}
</style>
</head>
<body>
<h1>QRDS/QOS • Gate BTC • Research-only</h1>
<h2>Acceptance Runner</h2>
<div class="header">
<p><b>Acceptance status:</b> {esc(payload["acceptance_status"])}</p>
<p><b>Policy lock:</b> {esc(payload["policy_lock"])} • <b>Mode:</b> {esc(payload["app_mode"])}</p>
<div class="kpi"><b>Reports present</b><br>{esc(payload["report_present_count"])}/{esc(payload["required_gate_count"])}</div>
<div class="kpi"><b>Blocking gates</b><br>{esc(payload["blocking_gate_count"])}</div>
<div class="kpi"><b>Safety issues</b><br>{esc(payload["safety_issue_count"])}</div>
<div class="kpi"><b>Pytest</b><br>{esc(payload["pytest_status"])}</div>
<div class="kpi"><b>Suspicious untracked</b><br>{esc(payload["suspicious_untracked_count"])}</div>
<div class="kpi"><b>Symbols</b><br>{esc(", ".join(payload["symbols"]))}</div>
<p class="badge">Research-only guardrail active</p>
<p>No execution, no exchange account, no portfolio allocation output, no trade instruction, no live-fund workflow.</p>
</div>

<h2>Gate cards</h2>
<div class="grid">{cards}</div>

<h2>Gate table</h2>
<table><thead><tr><th>Gate</th><th>Title</th><th>Status</th><th>Ready</th><th>Blocking</th><th>Answer</th><th>Score</th><th>SHA</th></tr></thead><tbody>{gate_rows}</tbody></table>

<h2>Safety flags</h2>
<table><thead><tr><th>Flag</th><th>Value</th></tr></thead><tbody>{flag_rows}</tbody></table>

<h2>Git status</h2>
<pre>{esc(payload["git_status_text"] or "clean-or-not-captured")}</pre>

<p>Generated at {esc(payload["generated_at"])} • SHA256 {esc(payload["report_payload_sha256"])}</p>
</body>
</html>"""
    _assert_research_only(page)
    return page


def build_acceptance_runner(
    output_dir: str | Path,
    symbols: str | Iterable[str] = "BTC-USDT,ETH-USDT,SOL-USDT",
    reports: Iterable[str | Path] | None = None,
    pytest_status: str = "NOT_RUN",
    git_status_text: str = "",
    refresh_status: str = "NOT_RUN",
) -> dict[str, Any]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    report_paths = list(reports) if reports is not None else discover_canonical_reports()
    report_rows = [_normalize_report_row(p) for p in report_paths]
    gate_rows = _gate_rows(report_rows)

    report_present_count = sum(1 for g in gate_rows if g["status"] == "REPORT_PRESENT")
    blocking_gate_count = sum(1 for g in gate_rows if g["blocking"] or not g["ready"])
    safety_issue_count = sum(1 for g in gate_rows if not g["safety_ok"])
    suspicious_untracked_count = _count_suspicious_untracked(git_status_text)

    if pytest_status != "PASS":
        acceptance_status = "ACCEPTANCE_RUNNER_COMPLETED_PYTEST_REVIEW_REQUIRED_RESEARCH_ONLY"
    elif safety_issue_count:
        acceptance_status = "ACCEPTANCE_RUNNER_COMPLETED_SAFETY_REVIEW_REQUIRED_RESEARCH_ONLY"
    elif blocking_gate_count:
        acceptance_status = "ACCEPTANCE_RUNNER_COMPLETED_CURRENT_GATES_STILL_BLOCK_PROMOTION_RESEARCH_ONLY"
    elif suspicious_untracked_count:
        acceptance_status = "ACCEPTANCE_RUNNER_COMPLETED_WORKSPACE_REVIEW_REQUIRED_RESEARCH_ONLY"
    else:
        acceptance_status = "ACCEPTANCE_RUNNER_COMPLETED_RESEARCH_STACK_RECORDED_POLICY_LOCK_ACTIVE"

    payload: dict[str, Any] = {
        "schema": "qrds.acceptance_runner.v1",
        "report_name": "qrds-acceptance-runner",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "acceptance_status": acceptance_status,
        "policy_lock": "ACTIVE",
        "app_mode": APP_MODE,
        "symbols": _symbols(symbols),
        "required_gate_count": len(REQUIRED_GATES),
        "report_present_count": report_present_count,
        "blocking_gate_count": blocking_gate_count,
        "safety_issue_count": safety_issue_count,
        "pytest_status": pytest_status,
        "refresh_status": refresh_status,
        "suspicious_untracked_count": suspicious_untracked_count,
        "git_status_text": git_status_text,
        "gate_rows": gate_rows,
        "report_rows": report_rows,
        "safety_flags": SAFETY_FLAGS,
        **SAFETY_FLAGS,
    }
    payload["report_payload_sha256"] = _sha(payload)

    report_path = out / "acceptance_runner.json"
    markdown_path = out / "acceptance_runner.md"
    html_path = out / "index.html"
    index_path = out / "acceptance_runner_index.json"

    report_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    markdown_path.write_text(render_markdown(payload), encoding="utf-8")
    html_path.write_text(render_html(payload), encoding="utf-8")

    index = {
        "schema": "qrds.acceptance_runner_index.v1",
        "report_name": payload["report_name"],
        "generated_at": payload["generated_at"],
        "acceptance_status": payload["acceptance_status"],
        "policy_lock": payload["policy_lock"],
        "app_mode": payload["app_mode"],
        "symbols": payload["symbols"],
        "required_gate_count": payload["required_gate_count"],
        "report_present_count": payload["report_present_count"],
        "blocking_gate_count": payload["blocking_gate_count"],
        "safety_issue_count": payload["safety_issue_count"],
        "pytest_status": payload["pytest_status"],
        "refresh_status": payload["refresh_status"],
        "suspicious_untracked_count": payload["suspicious_untracked_count"],
        "report_path": str(report_path),
        "markdown_path": str(markdown_path),
        "html_path": str(html_path),
        "index_path": str(index_path),
        "serve_entrypoint": str(html_path),
        "report_payload_sha256": payload["report_payload_sha256"],
        "payload": payload,
        **SAFETY_FLAGS,
    }
    index_path.write_text(json.dumps(index, indent=2, sort_keys=True), encoding="utf-8")
    return index
