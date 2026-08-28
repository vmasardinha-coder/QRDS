#!/usr/bin/env python3
"""QRDS Factory collector supervisor (#221).

Operational metadata only. It never opens strategy economics, changes model parameters,
backfills data, promotes survivors, or mutates scientific clocks.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

ANOMALIES = {
    "WAIT_SOURCE_PUBLICATION","WAIT_CALENDAR","STALE_NO_EXPECTED_RUN","WORKFLOW_NOT_STARTED",
    "WORKFLOW_FAILED","SOURCE_DOWNLOAD_FAILURE","SOURCE_SCHEMA_FAILURE","PARSER_FAILURE",
    "STRUCTURAL_QA_FAILURE","ARTIFACT_MISSING","LEDGER_NOT_APPENDED","RUNTIME_PUBLISH_FAILURE",
    "SCHEDULE_DISABLED","COLLECTOR_MISSING","SURVIVOR_APPROVED_NOT_ACTIVATED","FACTORY_TRANSITION_STALL",
    "SCIENTIFIC_BLOCK","UNKNOWN_REQUIRES_HUMAN",
}
SAFETY = {"RESEARCH_ONLY": True, "SHADOW_ONLY": True, "NOT_APPROVED": True, "ORDERS": 0, "REAL_CAPITAL": 0, "ENGINE_FEED": False}


def utcnow():
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def api(path: str, token: str | None, method: str = "GET"):
    req = urllib.request.Request("https://api.github.com" + path, method=method)
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            raw = r.read()
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")
        raise RuntimeError(f"GitHub API {method} {path}: HTTP {e.code}: {body[:400]}") from e


def workflow_score(collector: dict, wf: dict):
    expected = (collector.get("expected_workflow_job") or "").lower()
    hay = f"{wf.get('name','')} {wf.get('path','')}".lower()
    if not expected:
        return -1
    if expected in hay:
        return 100
    tokens = [t for t in re.split(r"[^a-z0-9]+", collector["collector_id"].lower()) if len(t) > 2]
    return sum(5 for t in tokens if t in hay)


def find_workflow(collector, workflows):
    ranked = sorted(((workflow_score(collector, w), w) for w in workflows), key=lambda x: x[0], reverse=True)
    if not ranked or ranked[0][0] <= 0:
        return None
    return ranked[0][1]


def latest_run(repo, wf_id, token):
    data = api(f"/repos/{repo}/actions/workflows/{wf_id}/runs?per_page=5", token)
    runs = data.get("workflow_runs", [])
    return runs[0] if runs else None


def artifacts_for_run(repo, run_id, token):
    return api(f"/repos/{repo}/actions/runs/{run_id}/artifacts?per_page=100", token).get("artifacts", [])


def anomaly_for(collector, wf, run, artifacts):
    if collector.get("status_expected") == "FUTURE_DEPENDENT":
        return "WAIT_CALENDAR", "future prerequisite intentionally unresolved"
    if wf is None:
        if collector.get("status_expected") == "ACTIVE_PROSPECTIVE_SURVIVOR":
            return "SURVIVOR_APPROVED_NOT_ACTIVATED", "approved survivor has no discoverable workflow"
        return "COLLECTOR_MISSING", "no discoverable expected workflow"
    if wf.get("state") not in ("active", None):
        return "SCHEDULE_DISABLED", f"workflow state={wf.get('state')}"
    if run is None:
        if collector.get("schedule_expected") == "MANUAL_AUTHORIZATION_ONLY":
            return "WAIT_CALENDAR", "manual forward-only capture awaits explicit authorization; no run is expected automatically"
        return "WORKFLOW_NOT_STARTED", "no workflow run found"
    status, conclusion = run.get("status"), run.get("conclusion")
    if status != "completed":
        return None, f"workflow {status}"
    if conclusion == "failure":
        return "WORKFLOW_FAILED", "latest workflow run failed"
    if conclusion in ("cancelled", "timed_out", "action_required", "startup_failure"):
        return "WORKFLOW_FAILED", f"latest conclusion={conclusion}"
    if conclusion == "skipped":
        return "STALE_NO_EXPECTED_RUN", "latest workflow run skipped"
    if conclusion == "success" and collector.get("expected_artifact") and not artifacts:
        return "ARTIFACT_MISSING", "successful run has no Actions artifact; runtime-only publication may require registry refinement"
    return None, "latest operational run healthy"


def repair(repo, collector, wf, run, anomaly, token):
    result = {"repair_attempted": False, "repair_result": "NOT_APPLICABLE", "repair_evidence": None, "regression_fix": False, "idempotence": "NOT_APPLICABLE"}
    allow = set(collector.get("approved_auto_repair_actions", []))
    if not token or not anomaly:
        return result
    if anomaly == "WORKFLOW_FAILED" and "rerun_failed_job" in allow and run and int(run.get("run_attempt", 1)) < 2:
        api(f"/repos/{repo}/actions/runs/{run['id']}/rerun-failed-jobs", token, "POST")
        result.update(repair_attempted=True, repair_result="RERUN_FAILED_JOBS_REQUESTED", repair_evidence={"run_id": run["id"], "prior_attempt": run.get("run_attempt")}, regression_fix=True, idempotence="BOUNDED_TO_ONE_AUTOMATIC_RETRY")
    elif anomaly == "SCHEDULE_DISABLED" and "restore_authorized_schedule" in allow and wf:
        api(f"/repos/{repo}/actions/workflows/{wf['id']}/enable", token, "PUT")
        result.update(repair_attempted=True, repair_result="AUTHORIZED_SCHEDULE_ENABLE_REQUESTED", repair_evidence={"workflow_id": wf["id"], "prior_state": wf.get("state")}, regression_fix=True, idempotence="ENABLE_ENDPOINT_IDEMPOTENT")
    return result


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--registry", default="tools/gate_btc_factory/FACTORY_COLLECTOR_REGISTRY.v1.json")
    p.add_argument("--production-map", default="tools/gate_btc_factory/PRODUCTION_LINE_MAP.v1.json")
    p.add_argument("--repo", default=os.getenv("GITHUB_REPOSITORY", "vmasardinha-coder/QRDS"))
    p.add_argument("--out-dir", default="artifacts/factory_collector_health")
    p.add_argument("--apply-safe-repairs", action="store_true")
    args = p.parse_args()
    token = os.getenv("GITHUB_TOKEN")
    registry = json.loads(Path(args.registry).read_text(encoding="utf-8"))
    production = json.loads(Path(args.production_map).read_text(encoding="utf-8"))
    assert registry["global_boundary"] == SAFETY
    assert set(registry["anomaly_classes"]) == ANOMALIES
    track_state = {x["track"]: x["state"] for x in production["tracks"]}
    workflows = api(f"/repos/{args.repo}/actions/workflows?per_page=100", token).get("workflows", [])
    rows, repaired = [], 0
    for c in registry["collectors"]:
        wf = find_workflow(c, workflows)
        run = latest_run(args.repo, wf["id"], token) if wf else None
        arts = artifacts_for_run(args.repo, run["id"], token) if run and run.get("status") == "completed" else []
        anomaly, root = anomaly_for(c, wf, run, arts)
        assert anomaly is None or anomaly in ANOMALIES
        rep = repair(args.repo, c, wf, run, anomaly, token) if args.apply_safe_repairs else {"repair_attempted":False,"repair_result":"AUDIT_ONLY","repair_evidence":None,"regression_fix":False,"idempotence":"NOT_APPLIED"}
        repaired += int(rep["repair_attempted"])
        row = dict(c)
        row.update(SAFETY)
        row.update({
            "workflow_discovered": None if not wf else {"id": wf["id"], "name": wf.get("name"), "path": wf.get("path"), "state": wf.get("state")},
            "latest_run": None if not run else {k:run.get(k) for k in ("id","status","conclusion","run_attempt","created_at","updated_at","html_url")},
            "latest_success_at": run.get("updated_at") if run and run.get("conclusion") == "success" else c.get("latest_success_at"),
            "actions_artifacts_count": len(arts),
            "anomaly_class": anomaly,
            "root_cause": root,
            "scientific_risk": "NONE_OPERATIONAL_ONLY" if anomaly not in {"SCIENTIFIC_BLOCK","UNKNOWN_REQUIRES_HUMAN"} else "BOUNDARY_REACHED",
            "human_action_required": anomaly in {"SCIENTIFIC_BLOCK","UNKNOWN_REQUIRES_HUMAN"},
            **rep,
        })
        rows.append(row)
    def n(pred): return sum(1 for r in rows if pred(r))
    current = next((r for r in rows if r["collector_id"] == "FACTORY_CURRENT_GENERATION"), None)
    summary = {
        "COLLECTORS_TOTAL": len(rows),
        "HEALTHY": n(lambda r: r["anomaly_class"] is None),
        "WAIT_SOURCE_OR_CALENDAR": n(lambda r: r["anomaly_class"] in {"WAIT_SOURCE_PUBLICATION","WAIT_CALENDAR","STALE_NO_EXPECTED_RUN"}),
        "TECHNICAL_FAILURE": n(lambda r: r["anomaly_class"] in ANOMALIES - {"WAIT_SOURCE_PUBLICATION","WAIT_CALENDAR","STALE_NO_EXPECTED_RUN","SCIENTIFIC_BLOCK"}),
        "SCIENTIFIC_BLOCK": n(lambda r: r["anomaly_class"] == "SCIENTIFIC_BLOCK"),
        "STALE": n(lambda r: r["anomaly_class"] in {"STALE_NO_EXPECTED_RUN","LEDGER_NOT_APPENDED"}),
        "AUTO_REPAIRED": repaired,
        "REQUIRES_HUMAN": n(lambda r: r["human_action_required"]),
        "FACTORY_CURRENT_GENERATION": current["family_model"] if current else None,
        "FACTORY_CURRENT_STAGE": current["status_expected"] if current else None,
        "SURVIVORS_APPROVED": n(lambda r: "SURVIVOR" in r["status_expected"]),
        "SURVIVORS_ACTIVE": n(lambda r: "SURVIVOR" in r["status_expected"] and r["workflow_discovered"] is not None),
        "SURVIVORS_MISSING_COLLECTOR": n(lambda r: r["anomaly_class"] == "SURVIVOR_APPROVED_NOT_ACTIVATED"),
    }
    payload = {"schema":"qrds.factory.collector_health.v1","generated_at_utc":utcnow(),"issue":221,"safety":SAFETY,"production_line_map_schema":production.get("schema"),"summary":summary,"collectors":rows}
    out = Path(args.out_dir); out.mkdir(parents=True, exist_ok=True)
    (out/"FACTORY_COLLECTOR_HEALTH_LATEST.json").write_text(json.dumps(payload, indent=2, sort_keys=True)+"\n", encoding="utf-8")
    problems = [r for r in rows if r["anomaly_class"]]
    md = ["# FACTORY COLLECTOR HEALTH — LATEST", "", f"Generated: `{payload['generated_at_utc']}`", "", "## Summary", ""]
    md += [f"- **{k}**: {v}" for k,v in summary.items()]
    md += ["", "## Exceptions / changes", ""]
    if not problems: md.append("No operational exceptions.")
    for r in problems:
        md += [f"### {r['collector_id']} — {r['anomaly_class']}", f"- last_success: `{r.get('latest_success_at')}`", f"- expected_run: `{r.get('next_expected_run')}`", f"- root_cause: {r['root_cause']}", f"- repair_attempted: `{r['repair_attempted']}`", f"- repair_result: `{r['repair_result']}`", f"- scientific_risk: `{r['scientific_risk']}`", f"- human_action_required: `{r['human_action_required']}`", ""]
    md += ["## Immutable boundary", "", "`RESEARCH_ONLY=true`, `SHADOW_ONLY=true`, `NOT_APPROVED=true`, `ORDERS=0`, `REAL_CAPITAL=0`, `ENGINE_FEED=false`.", "No partial economics are read for operational health."]
    (out/"FACTORY_COLLECTOR_HEALTH_LATEST.md").write_text("\n".join(md)+"\n", encoding="utf-8")
    print(json.dumps(summary, sort_keys=True))

if __name__ == "__main__":
    main()
