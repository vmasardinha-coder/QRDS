#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PLAN = ROOT / "tools/gate_btc_factory/FACTORY_TRANSITIONS_RUNTIME.json"
REGISTRY = ROOT / "tools/gate_btc_factory/PROSPECTIVE_ACTIVATIONS.json"


def gh(*args: str) -> str:
    env = os.environ.copy()
    if not env.get("GH_TOKEN"):
        raise SystemExit("FAIL GH_TOKEN required")
    return subprocess.check_output(["gh", *args], cwd=ROOT, env=env, text=True).strip()


def issue_exists(marker: str) -> bool:
    raw = gh("issue", "list", "--state", "all", "--limit", "200", "--search", marker, "--json", "number,title,body")
    rows = json.loads(raw or "[]")
    return any(marker in (r.get("title") or "") or marker in (r.get("body") or "") for r in rows)


def create_issue(action: dict) -> None:
    marker = action["marker"]
    if issue_exists(marker):
        print(f"SKIP existing issue {marker}")
        return
    title = action.get("title") or f"[{marker}] automatic prospective activation"
    body = action.get("body") or (
        f"Factory-approved automatic shadow prospective activation for {action['track']}.\n\n"
        f"Approval status: {action['status']}\n"
        "Activation is limited to the separate blind prospective/shadow registry. "
        "No production routing, orders, real capital, engine feed, retune, backfill, or partial-result feedback is permitted.\n\n"
        f"{marker}"
    )
    gh("issue", "create", "--title", title, "--body", body)
    print(f"CREATED issue {marker}")


def activate(registry: dict, action: dict) -> bool:
    track = action["track"]
    existing = registry.setdefault("activations", {}).get(track)
    if existing and existing.get("approval_status") == action["status"] and existing.get("state") == action["activation_state"]:
        return False
    registry["activations"][track] = {
        "state": action["activation_state"],
        "approval_status": action["status"],
        "activated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "orders": 0,
        "real_capital": 0,
        "engine_feed": False,
        "production": False,
    }
    return True


def main() -> int:
    plan = json.loads(PLAN.read_text(encoding="utf-8"))
    safety = plan.get("safety", {})
    if safety != {
        "ENGINE_FEED": False,
        "ORDERS": 0,
        "REAL_CAPITAL": 0,
        "RESEARCH_ONLY": True,
        "SHADOW_ONLY": True,
        "production_activation_allowed": False,
    }:
        raise SystemExit("FAIL transition plan safety mismatch")

    freshness = plan.get("source_freshness")
    transitions_allowed = plan.get("transitions_allowed")
    actions = plan.get("actions", [])
    if freshness == "STALE_READ_ONLY":
        if transitions_allowed is not False or actions:
            raise SystemExit("FAIL stale source produced transition actions")
        print("NOOP stale source is read-only; no issue or activation mutation")
        return 0
    if freshness != "FRESH" or transitions_allowed is not True:
        raise SystemExit("FAIL transition plan missing fresh-source authorization")

    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    changed = False
    for action in actions:
        kind = action.get("action")
        if kind == "CREATE_NEXT_GENERATION_ISSUE":
            create_issue(action)
        elif kind == "ACTIVATE_APPROVED_PROSPECTIVE_SHADOW":
            changed = activate(registry, action) or changed
            create_issue(action)
        else:
            raise SystemExit(f"FAIL unknown action {kind!r}")

    if changed:
        REGISTRY.write_text(json.dumps(registry, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print("UPDATED prospective activation registry")
    else:
        print("NO registry change")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
