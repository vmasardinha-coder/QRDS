#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "tools/gate_btc_research_factory_status.json"
RUNTIME_STATUS = ROOT / "tools/gate_btc_factory/FACTORY_STATUS_RUNTIME.json"
OUT = ROOT / "tools/gate_btc_factory/FACTORY_TRANSITIONS_RUNTIME.json"
APPROVAL_PREFIXES = ("APPROVED_FOR_SEPARATE_PROSPECTIVE", "APPROVED_PROSPECTIVE")
FRESH_MINUTES = 180
FUTURE_SKEW_MINUTES = 5
EXPECTED_RUNTIME_SAFETY = {
    "ENGINE_FEED": False,
    "NOT_APPROVED": True,
    "ORDERS": 0,
    "REAL_CAPITAL": 0,
    "RESEARCH_ONLY": True,
    "SHADOW_ONLY": True,
}


def generation_matches(status: str) -> list[tuple[int, int, int]]:
    rows: list[tuple[int, int, int]] = []
    for match in re.finditer(r"H(\d+)[-_]H(\d+)", status or ""):
        rows.append((int(match.group(1)), int(match.group(2)), match.start()))
    return rows


def build_next_generation(track: dict) -> dict | None:
    if track.get("classification") != "OPEN_DISCOVERY":
        return None
    if track.get("open_issue") is not None or track.get("open_pr") is not None:
        return None
    status = str(track.get("status", ""))
    rows = generation_matches(status)
    if not rows:
        return None
    start0, end, pos = max(rows, key=lambda row: row[1])
    if end < 40:
        return None
    tail = status[pos:]
    if "CLOSED" not in tail:
        return None
    if any(token in tail for token in ("PREREGISTERED", "OPEN_DISCOVERY", "DATA_QA", "IN_PROGRESS")):
        return None
    return next_generation_action(start0, end)


def next_generation_action(start0: int, end: int) -> dict:
    start = end + 1
    finish = start + 9
    marker = f"B3 H{start}-H{finish}"
    return {
        "action": "CREATE_NEXT_GENERATION_ISSUE",
        "track": "B3_H40_PLUS",
        "marker": marker,
        "title": f"{marker}: automatic next discovery generation",
        "body": (
            f"Factory-generated continuation request after H{start0}-H{end} closed.\n\n"
            f"Pre-register H{start}-H{finish} before reading results. Use materially new mechanisms/data dimensions; "
            "do not recycle rejected cells or retune frozen survivors. Preserve the historical cutoff, independent replication, "
            "frozen execution/cost/side/calendar/concentration gates, and all provenance/causality checks. "
            "H1 economics and partial prospective survivor economics remain forbidden inputs. "
            "Orders=0, real capital=0, engine_feed=false. Null result is valid.\n\n"
            f"{marker}\nAUTO_FACTORY_CONTINUATION=true"
        ),
    }


def build_next_generation_from_runtime(frontier: dict | None) -> dict | None:
    if not frontier:
        return None
    status = str(frontier.get("status", ""))
    survivors = frontier.get("survivors", [])
    if survivors:
        return None
    if not status.startswith("CLOSED_NO_") or not status.endswith("_SURVIVOR"):
        return None
    generation = str(frontier.get("generation", ""))
    match = re.fullmatch(r"H(\d+)-H(\d+)", generation)
    if not match:
        return None
    start0, end = int(match.group(1)), int(match.group(2))
    expected = end + 1
    if frontier.get("next_generation_start") != expected:
        return None
    return next_generation_action(start0, end)


def approved_activations(tracks: dict, activations: dict | None = None) -> list[dict]:
    active = (activations or {}).get("activations", {})
    actions = []
    for name, track in sorted(tracks.items()):
        status = str(track.get("status", ""))
        if not status.startswith(APPROVAL_PREFIXES):
            continue
        if isinstance(active, dict) and name in active:
            state = active.get(name, {}).get("state") if isinstance(active.get(name), dict) else None
            if state == "ACTIVE_PROSPECTIVE_SHADOW":
                continue
        actions.append({
            "action": "ACTIVATE_APPROVED_PROSPECTIVE_SHADOW",
            "track": name,
            "status": status,
            "marker": f"AUTO-PROSPECTIVE:{name}",
            "activation_state": "ACTIVE_PROSPECTIVE_SHADOW",
            "orders": 0,
            "real_capital": 0,
            "engine_feed": False,
        })
    return actions


def load_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise SystemExit(f"FAIL missing required factory runtime: {path.relative_to(ROOT)}") from exc
    except Exception as exc:
        raise SystemExit(f"FAIL invalid JSON {path.relative_to(ROOT)}: {exc}") from exc
    if not isinstance(value, dict):
        raise SystemExit(f"FAIL expected JSON object: {path.relative_to(ROOT)}")
    return value


def load_runtime_json(path: str) -> dict | None:
    try:
        raw = subprocess.check_output(
            ["git", "show", f"origin/gate-btc-runtime:{path}"],
            cwd=ROOT,
            text=True,
            stderr=subprocess.DEVNULL,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None
    try:
        value = json.loads(raw)
    except Exception as exc:
        raise SystemExit(f"FAIL invalid runtime authority {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise SystemExit(f"FAIL expected runtime object: {path}")
    return value


def validate_source_safety(src: dict) -> None:
    safety = src.get("safety", {})
    required = {
        "research_only": True,
        "shadow_only": True,
        "not_approved": True,
        "orders": 0,
        "real_capital": 0,
        "engine_feed": False,
        "no_holdout_contamination": True,
    }
    for key, expected in required.items():
        if safety.get(key) != expected:
            raise SystemExit(f"FAIL safety boundary {key}={safety.get(key)!r}")


def parse_utc(value: str) -> datetime:
    if not value:
        raise SystemExit("FAIL missing canonical source timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise SystemExit(f"FAIL invalid canonical source timestamp: {value!r}") from exc
    if parsed.tzinfo is None:
        raise SystemExit("FAIL canonical source timestamp must be timezone-aware")
    return parsed.astimezone(timezone.utc)


def validate_runtime_binding(src: dict, runtime: dict, source_hash: str | None = None, *, now: datetime | None = None) -> str:
    if runtime.get("global_safety") != EXPECTED_RUNTIME_SAFETY:
        raise SystemExit("FAIL factory runtime safety mismatch")
    if runtime.get("source_generated_at") != src.get("generated_at_utc"):
        raise SystemExit("FAIL factory runtime is not bound to the current canonical source timestamp")
    if source_hash is not None and runtime.get("source_hash") != source_hash:
        raise SystemExit("FAIL factory runtime is not bound to the current canonical source hash")
    freshness_block = runtime.get("source_freshness", {})
    if freshness_block.get("freshness_limit_minutes") != FRESH_MINUTES:
        raise SystemExit("FAIL factory runtime freshness limit mismatch")
    if freshness_block.get("future_timestamp_tolerance_minutes") != FUTURE_SKEW_MINUTES:
        raise SystemExit("FAIL factory runtime future timestamp tolerance mismatch")
    freshness = freshness_block.get("status")
    if freshness not in {"FRESH", "STALE_READ_ONLY"}:
        raise SystemExit(f"FAIL invalid factory source freshness: {freshness!r}")
    current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    source_time = parse_utc(src.get("generated_at_utc"))
    age_minutes = (current - source_time).total_seconds() / 60.0
    if age_minutes < -FUTURE_SKEW_MINUTES:
        raise SystemExit("FAIL canonical source timestamp is materially in the future")
    age_minutes = max(0.0, age_minutes)
    expected = "FRESH" if age_minutes <= FRESH_MINUTES else "STALE_READ_ONLY"
    if freshness != expected:
        raise SystemExit(f"FAIL factory runtime freshness does not match canonical source age: runtime={freshness} expected={expected}")
    return freshness


def build_plan(src: dict, runtime: dict, *, source_hash: str | None = None, now: datetime | None = None, frontier: dict | None = None, activations: dict | None = None) -> dict:
    validate_source_safety(src)
    freshness = validate_runtime_binding(src, runtime, source_hash, now=now)
    transitions_allowed = freshness == "FRESH"
    tracks = src.get("tracks", {})
    actions: list[dict] = []
    if transitions_allowed:
        nxt = build_next_generation_from_runtime(frontier)
        if nxt is None:
            nxt = build_next_generation(tracks.get("B3_H40_PLUS", {}))
        if nxt:
            actions.append(nxt)
        actions.extend(approved_activations(tracks, activations))
    blocked_eligible = [name for name, track in tracks.items() if str(track.get("status", "")).startswith("ELIGIBLE_")]
    return {
        "schema": "qrds.factory.transitions.v2",
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "source_generated_at_utc": src.get("generated_at_utc"),
        "source_hash": runtime.get("source_hash"),
        "source_freshness": freshness,
        "runtime_frontier_authority": frontier is not None,
        "prospective_registry_authority": activations is not None,
        "transitions_allowed": transitions_allowed,
        "blocked_reason": None if transitions_allowed else "STALE_SOURCE_READ_ONLY_NO_TRANSITIONS",
        "actions": actions,
        "eligible_not_activated": sorted(blocked_eligible),
        "safety": {"RESEARCH_ONLY": True, "SHADOW_ONLY": True, "ORDERS": 0, "REAL_CAPITAL": 0, "ENGINE_FEED": False, "production_activation_allowed": False},
    }


def main() -> int:
    src = load_json(SOURCE)
    runtime = load_json(RUNTIME_STATUS)
    source_hash = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    frontier = load_runtime_json("runtime/autonomous_science/CURRENT.json")
    activations = load_runtime_json("runtime/factory_autonomy/PROSPECTIVE_ACTIVATIONS.json")
    report = build_plan(src, runtime, source_hash=source_hash, frontier=frontier, activations=activations)
    OUT.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"actions": len(report["actions"]), "eligible_not_activated": report["eligible_not_activated"], "source_freshness": report["source_freshness"], "transitions_allowed": report["transitions_allowed"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
