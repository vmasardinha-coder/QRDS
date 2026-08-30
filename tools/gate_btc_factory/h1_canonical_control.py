#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Iterable

STATUS_RE = re.compile(r"^([A-Z0-9_]+)=(.*)$")
COUNTER_RE = re.compile(r"(?:H1_)?(\d+)_OF_20(?:_CANONICAL)?")
ALLOWED_REASONS = {
    "SOURCE_NOT_PUBLISHED", "SOURCE_FAILURE", "STRUCTURAL_FAIL",
    "NON_TRADING_DAY", "DUPLICATE", "OTHER", "STRUCTURAL_PASS",
}

@dataclass(frozen=True)
class Evidence:
    path: str
    qualified: int
    remaining: int
    last_candidate_date: str
    last_candidate_status: str
    economics_locked: bool
    appended_now: bool
    precedence: tuple[str, str]


def parse_status(path: Path) -> Evidence:
    fields: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        m = STATUS_RE.match(raw.strip())
        if m:
            fields[m.group(1)] = m.group(2).strip()
    status = fields.get("STATUS", "")
    q = None
    if "QUALIFIED" in fields and "/" in fields["QUALIFIED"]:
        q = int(fields["QUALIFIED"].split("/", 1)[0])
    if q is None:
        m = COUNTER_RE.search(status)
        if m:
            q = int(m.group(1))
    if q is None or not 0 <= q <= 20:
        raise ValueError(f"invalid H1 counter in {path}")
    remaining = int(fields.get("REMAINING", 20 - q))
    if remaining != 20 - q:
        raise ValueError(f"counter/remaining mismatch in {path}")
    candidate_date = fields.get("LAST_CANDIDATE_DATE", "")
    if candidate_date:
        date.fromisoformat(candidate_date)
    # Filename timestamps are used only as a tie-breaker. A later valid candidate
    # session is stronger than an older artifact creation time.
    ts_match = re.search(r"(20\d{6})[-_](\d{6})", path.name)
    ts = ""
    if ts_match:
        ts = ts_match.group(1) + ts_match.group(2)
    return Evidence(
        path=str(path), qualified=q, remaining=remaining,
        last_candidate_date=candidate_date,
        last_candidate_status=fields.get("LAST_CANDIDATE_STATUS", "UNKNOWN"),
        economics_locked=fields.get("ECONOMICS_LOCKED", "true").lower() == "true",
        appended_now=fields.get("APPENDED_NOW", "false").lower() == "true",
        precedence=(candidate_date, ts),
    )


def discover(root: Path) -> list[Evidence]:
    out: list[Evidence] = []
    for p in root.rglob("GATE_BTC_B3_H1_STATUS*.txt"):
        try:
            out.append(parse_status(p))
        except Exception:
            continue
    return out


def choose_canonical(evidence: Iterable[Evidence]) -> tuple[Evidence, list[str]]:
    items = list(evidence)
    if not items:
        raise RuntimeError("H1_CANONICAL_EVIDENCE_NOT_FOUND")
    # Strongest session/timestamp first. Counter is monotonic: later reporting may
    # never silently regress below a previously proven canonical count.
    latest = max(items, key=lambda e: e.precedence)
    proven_max = max(e.qualified for e in items)
    warnings: list[str] = []
    if latest.qualified < proven_max:
        stronger = max((e for e in items if e.qualified == proven_max), key=lambda e: e.precedence)
        warnings.append(
            f"CANONICAL_COUNTER_REGRESSION_BLOCKED latest={latest.qualified}/20 proven={proven_max}/20"
        )
        latest = stronger
    if not latest.economics_locked and latest.qualified < 20:
        raise RuntimeError("H1_ECONOMICS_UNLOCKED_BEFORE_20")
    return latest, warnings


def normalize_reason(status: str, counted: bool, duplicate: bool = False) -> str:
    if duplicate:
        return "DUPLICATE"
    s = (status or "").upper()
    if counted and s == "STRUCTURAL_PASS":
        return "STRUCTURAL_PASS"
    if "NOT_PUBLISHED" in s or "404" in s:
        return "SOURCE_NOT_PUBLISHED"
    if "SOURCE" in s or "HTTP" in s or "RETRY" in s:
        return "SOURCE_FAILURE"
    if "NON_TRADING" in s:
        return "NON_TRADING_DAY"
    if "STRUCTURAL" in s or "QA" in s:
        return "STRUCTURAL_FAIL"
    return "OTHER"


def checkpoint_contract(qualified: int) -> dict:
    ready = qualified >= 20
    return {
        "schema": "qrds.h1.checkpoint_20_handoff.v1",
        "qualified": qualified,
        "trigger_reached": ready,
        "economics_locked_now": not ready,
        "handoff_sequence": [
            "FREEZE_FINAL_H1_LEDGER",
            "INTEGRITY_RECONCILIATION_CHECK",
            "UNLOCK_ECONOMICS_ONLY_IF_INTEGRITY_GREEN",
            "CALCULATE_CAPITAL_BASE_EQUIVALENT",
            "CALCULATE_PNL_RETURN_VOLATILITY_SHARPE_MAXDD_WIN_RATE_EXPECTANCY_TRADES_COSTS",
            "GENERATE_H1_CHECKPOINT_20_OF_20",
            "COMPARE_PREREGISTERED_BENCHMARK",
            "SCIENTIFIC_DECISION_PASS_FAIL_INCONCLUSIVE",
        ],
        "no_methodology_change": True,
        "no_counter_rewrite": True,
        "no_backfill_as_prospective": True,
    }


def mt5_paper_contract(qualified: int, reviewed: bool = False) -> dict:
    gate = qualified >= 20 and reviewed
    return {
        "schema": "qrds.h1.mt5_paper_handoff.v1",
        "handoff_exists": True,
        "handoff_ready": qualified >= 20,
        "review_required": True,
        "review_complete": reviewed,
        "paper_enabled": False,
        "activation_gate_satisfied": gate,
        "mode": "PAPER_SHADOW_OBSERVATION_ONLY",
        "orders": 0,
        "real_capital": 0,
        "engine_feed": False,
        "historical_backfill": False,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--artifact-root", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    evidence = discover(Path(args.artifact_root))
    canonical, warnings = choose_canonical(evidence)
    out = {
        "schema": "qrds.h1.canonical_control.v1",
        "canonical": canonical.__dict__,
        "warnings": warnings,
        "all_evidence": [e.__dict__ for e in sorted(evidence, key=lambda x: x.precedence)],
        "checkpoint": checkpoint_contract(canonical.qualified),
        "mt5_paper": mt5_paper_contract(canonical.qualified),
        "safety": {
            "READ_ONLY_HISTORICAL_LEDGER": True,
            "NO_COUNTER_REWRITE": True,
            "NO_BACKFILL_AS_PROSPECTIVE": True,
            "NO_RETUNE": True,
            "NO_THRESHOLD_CHANGE": True,
            "NO_FAMILY_CHANGE": True,
            "ORDERS": 0,
            "REAL_CAPITAL": 0,
        },
    }
    p = Path(args.out)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(out, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
