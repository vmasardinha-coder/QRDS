#!/usr/bin/env python3
"""Live scanner for GitHub states that genuinely require Victor's intervention.

Ordinary workflow failures are Factory-owned and are intentionally excluded.
The scanner only surfaces explicit human gates such as waiting/action_required,
owner review requests, explicit human-action labels, and registry-declared tasks.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


def api(path: str):
    repo = os.environ.get("GITHUB_REPOSITORY", "vmasardinha-coder/QRDS")
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if not token:
        raise RuntimeError("GH_TOKEN/GITHUB_TOKEN is required")
    url = f"https://api.github.com/repos/{repo}/{path.lstrip('/')}"
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "qrds-victor-action-supervisor",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"GitHub API {e.code} for {url}: {body[:500]}") from e


def dedupe(actions):
    seen = set()
    out = []
    for a in actions:
        key = (a.get("type"), a.get("url"), a.get("instruction"))
        if key in seen:
            continue
        seen.add(key)
        out.append(a)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--registry", default="ops/workflow_operations_registry.json")
    ap.add_argument("--json-out", default="runtime/victor_action_queue.json")
    ap.add_argument("--markdown-out", default="runtime/victor_action_queue.md")
    args = ap.parse_args()

    registry = json.loads(Path(args.registry).read_text(encoding="utf-8"))
    ignore_prs = set(registry.get("ignore_pr_numbers_for_action_required", []))
    ignore_workflows = set(registry.get("ignore_workflow_names_for_human_queue", []))
    actions = []

    # 1) Explicit/manual queue entries maintained by policy.
    for item in registry.get("current_manual_actions", []):
        actions.append({
            "type": "EXPLICIT_MANUAL_ACTION",
            "source": "registry",
            "instruction": item.get("instruction", item.get("id", "Manual action required")),
            "url": None,
            "details": item,
        })

    # 2) GitHub Actions states that are themselves human gates.
    runs = api("actions/runs?per_page=100").get("workflow_runs", [])
    for run in runs:
        status = run.get("status")
        conclusion = run.get("conclusion")
        if status != "waiting" and conclusion != "action_required":
            continue
        pr_numbers = {p.get("number") for p in run.get("pull_requests", []) if p.get("number")}
        if pr_numbers and pr_numbers.issubset(ignore_prs):
            continue
        if run.get("name") in ignore_workflows and (not pr_numbers or pr_numbers & ignore_prs):
            continue
        signal = "WAITING_FOR_HUMAN_APPROVAL" if status == "waiting" else "ACTION_REQUIRED"
        actions.append({
            "type": signal,
            "source": "workflow_run",
            "instruction": f"Open and resolve the human gate in workflow '{run.get('name')}' run #{run.get('run_number')}.",
            "url": run.get("html_url"),
            "details": {
                "run_id": run.get("id"),
                "workflow": run.get("name"),
                "status": status,
                "conclusion": conclusion,
                "branch": run.get("head_branch"),
                "event": run.get("event"),
                "pr_numbers": sorted(pr_numbers),
            },
        })

    # 3) Open PRs that explicitly request the repository owner as reviewer.
    owner = os.environ.get("GITHUB_REPOSITORY", "vmasardinha-coder/QRDS").split("/", 1)[0]
    pulls = api("pulls?state=open&per_page=100")
    for pr in pulls:
        if pr.get("number") in ignore_prs:
            continue
        requested = {r.get("login") for r in pr.get("requested_reviewers", [])}
        if owner in requested:
            actions.append({
                "type": "OWNER_REVIEW_REQUESTED",
                "source": "pull_request",
                "instruction": f"Review PR #{pr.get('number')}: {pr.get('title')}",
                "url": pr.get("html_url"),
                "details": {"pr_number": pr.get("number")},
            })

    # 4) Explicitly labeled human decisions. This also catches PRs because GitHub's
    # issues endpoint represents PRs as issues with a pull_request field.
    labeled = api("issues?state=open&labels=human-action-required&per_page=100")
    for item in labeled:
        if item.get("number") in ignore_prs:
            continue
        actions.append({
            "type": "HUMAN_ACTION_LABEL",
            "source": "issue_or_pr",
            "instruction": f"Resolve #{item.get('number')}: {item.get('title')}",
            "url": item.get("html_url"),
            "details": {"number": item.get("number")},
        })

    actions = dedupe(actions)
    payload = {
        "schema": "victor-action-queue/v1",
        "human_action_count": len(actions),
        "actions": actions,
        "policy_note": "Ordinary failures are Factory-owned and are not surfaced here unless they become an explicit human gate.",
    }

    json_path = Path(args.json_out)
    md_path = Path(args.markdown_out)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    lines = ["# 00 VICTOR — ACTION REQUIRED", ""]
    if actions:
        lines.append(f"**{len(actions)} ação(ões) humana(s) detectada(s).**")
        lines.append("")
        for idx, a in enumerate(actions, 1):
            link = f" — {a['url']}" if a.get("url") else ""
            lines.append(f"{idx}. **{a['type']}** — {a['instruction']}{link}")
    else:
        lines.append("**Nenhuma ação manual necessária para Victor.**")
    lines += ["", "Falhas operacionais comuns continuam sob responsabilidade automática da Factory."]
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(json.dumps(payload, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
