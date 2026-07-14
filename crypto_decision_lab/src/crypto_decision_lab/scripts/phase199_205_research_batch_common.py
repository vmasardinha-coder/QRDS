from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]

LOCKS = {
    "operational_status": "BLOCKED_RESEARCH_ONLY",
    "promotion_allowed": False,
    "shadow_decision_allowed": False,
    "decision_layer_allowed": False,
    "operational_decision_allowed": False,
    "safe_apply_allowed": False,
    "trading_signal_generated": False,
    "recommendation_generated": False,
    "allocation_generated": False,
    "orders_generated": False,
    "real_orders_generated": False,
    "real_capital_used": False,
    "authenticated_connection_used": False,
    "canonical_data_writes": 0,
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"Required artifact missing: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return payload


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [line.rstrip(" \t") for line in content.splitlines()]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def sha256_json(value: Any) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        default=str,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def require_phase(payload: dict[str, Any], phase: int) -> None:
    if payload.get("phase") != phase:
        raise ValueError(f"Expected Phase {phase}, found {payload.get('phase')}")
