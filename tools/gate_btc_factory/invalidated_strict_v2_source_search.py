#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

from tools.gate_btc_factory import invalidated_source_qualification_search as legacy_search

STRICT_NAMESPACE = "RQ_STRICT_FORWARD_UNSEEN_2025_2026_V2"
STRICT_MINIMUM_SESSIONS = 322
STRICT_WINDOW_START = "2025-01-01"
STRICT_WINDOW_END = "2026-08-09"


def _strict_gate_adjudication(gate_path: Path, runtime_root: Path) -> dict[str, Any]:
    base = legacy_search.validate_existing_gate(gate_path, runtime_root)
    if not gate_path.exists():
        return base
    try:
        gate = json.loads(gate_path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"present": True, "valid": False, "reason": f"GATE_PARSE_ERROR:{type(exc).__name__}:{exc}"}
    if gate.get("evaluation_namespace") != STRICT_NAMESPACE:
        return {"present": True, "valid": False, "reason": "NON_STRICT_V2_NAMESPACE_FORBIDDEN"}
    windows = gate.get("windows") or {}
    discovery = windows.get("discovery") or {}
    if str(discovery.get("start") or "") < STRICT_WINDOW_START:
        return {"present": True, "valid": False, "reason": "DISCOVERY_START_BEFORE_2025_FORBIDDEN"}
    source = gate.get("source") or {}
    sessions = source.get("eligible_session_count")
    if not isinstance(sessions, int) or sessions < STRICT_MINIMUM_SESSIONS:
        return {"present": True, "valid": False, "reason": "STRICT_V2_MINIMUM_322_SESSIONS_NOT_MET", "eligible_session_count": sessions}
    if base.get("valid") is not True:
        return base
    return {**base, "strict_namespace": STRICT_NAMESPACE, "minimum_sessions_required": STRICT_MINIMUM_SESSIONS}


def search(root_cause: dict[str, Any], gate_path: Path, runtime_root: Path, token: str | None = None,
           session=None, mt5_packet_path: Path | None = None) -> dict[str, Any]:
    out = legacy_search.search(
        root_cause,
        gate_path,
        runtime_root,
        token=token,
        session=session,
        mt5_packet_path=mt5_packet_path,
    )
    out["source_gate"] = _strict_gate_adjudication(gate_path, runtime_root)
    out["status"] = "SOURCE_GATE_GREEN" if out["source_gate"].get("valid") else "ACTIVE_SEARCHING_QUALIFICATION"
    out["frozen_source_contract"].update({
        "evaluation_namespace": STRICT_NAMESPACE,
        "minimum_sessions_required": STRICT_MINIMUM_SESSIONS,
        "strict_window_start": STRICT_WINDOW_START,
        "strict_window_end": STRICT_WINDOW_END,
        "legacy_v1_minimum_161_authoritative": False,
        "legacy_v1_gates_may_authorize_v2": False,
    })
    if out["status"] != "SOURCE_GATE_GREEN":
        if "MINIMUM_HISTORY_COVERAGE" not in out["blocking_requirements"]:
            out["blocking_requirements"].append("MINIMUM_HISTORY_COVERAGE")
        out["next_action"] = "RESOLVE_STRICT_V2_322_SESSION_SOURCE_GATE_FAIL_CLOSED"
    else:
        out["blocking_requirements"] = []
        out["next_action"] = "HAND_OFF_TO_REQUALIFICATION"
    out["strict_v2_guard"] = {
        "namespace": STRICT_NAMESPACE,
        "minimum_sessions_required": STRICT_MINIMUM_SESSIONS,
        "v1_161_floor_forbidden": True,
        "contaminated_v1_credit": 0,
        "historical_backfill_credit": 0,
    }
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root-cause", required=True)
    ap.add_argument("--gate", required=True)
    ap.add_argument("--runtime-root", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--mt5-packet")
    args = ap.parse_args()
    root = json.loads(Path(args.root_cause).read_text(encoding="utf-8"))
    if root.get("root_cause_classification") != "SOURCE_DATA_GAP":
        raise SystemExit("ROOT_CAUSE_NOT_SOURCE_DATA_GAP")
    out = search(
        root,
        Path(args.gate),
        Path(args.runtime_root),
        token=os.environ.get("GITHUB_TOKEN"),
        mt5_packet_path=Path(args.mt5_packet) if args.mt5_packet else None,
    )
    p = Path(args.output)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": out["status"],
        "namespace": STRICT_NAMESPACE,
        "minimum_sessions_required": STRICT_MINIMUM_SESSIONS,
        "source_gate": out["source_gate"]["reason"],
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
