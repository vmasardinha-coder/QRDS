#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import math
from datetime import date, timedelta
from pathlib import Path

FREEZE_DATE = date.fromisoformat("2026-09-09")
CANDIDATE_ID = "GATE_BTC_MOMENTUM_M3_PERSISTENCE_20260909"
MIN_COMMON_ASSETS = 30


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def canonical_sha(payload: dict) -> str:
    body = {k: v for k, v in payload.items() if k != "snapshot_sha256"}
    raw = (json.dumps(body, sort_keys=True, separators=(",", ":")) + "\n").encode()
    return _sha256(raw)


def _load_source_snapshot(path: Path, expected_cutoff: str) -> dict:
    if not path.exists():
        raise SystemExit(f"required canonical source snapshot missing: {path.name}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("cutoff") != expected_cutoff:
        raise SystemExit(f"source cutoff mismatch: expected {expected_cutoff}")
    if payload.get("snapshot_sha256") != canonical_sha(payload):
        raise SystemExit(f"source snapshot hash mismatch: {expected_cutoff}")
    safety = payload.get("safety", {})
    if not (
        safety.get("research_only") is True
        and safety.get("shadow_only") is True
        and safety.get("not_approved") is True
        and safety.get("engine_feed") is False
        and int(safety.get("orders", 0) or 0) == 0
        and int(safety.get("real_capital", 0) or 0) == 0
    ):
        raise SystemExit(f"source safety invariant mismatch: {expected_cutoff}")
    rows = payload.get("m1", {}).get("rows")
    if not isinstance(rows, list):
        raise SystemExit(f"m1.rows missing: {expected_cutoff}")
    seen = set()
    parsed = {}
    for row in rows:
        asset = str(row.get("asset", "")).strip().upper()
        if not asset:
            raise SystemExit(f"blank asset: {expected_cutoff}")
        if asset in seen:
            raise SystemExit(f"duplicate asset {asset}: {expected_cutoff}")
        seen.add(asset)
        value = row.get("r30")
        if value is None:
            continue
        try:
            value = float(value)
        except Exception:
            continue
        if math.isfinite(value):
            parsed[asset] = value
    return {"payload": payload, "r30": parsed, "sha256": payload["snapshot_sha256"]}


def _rank_percentiles(values: dict[str, float]) -> dict[str, dict]:
    ordered = sorted(values.items(), key=lambda item: (-item[1], item[0]))
    n = len(ordered)
    if n < 2:
        raise SystemExit("rank percentile requires at least two assets")
    out = {}
    for rank, (asset, value) in enumerate(ordered, 1):
        out[asset] = {
            "r30": value,
            "rank": rank,
            "pct": 1.0 - (rank - 1) / (n - 1),
        }
    return out


def _population_std(values: list[float]) -> float:
    mean = sum(values) / len(values)
    return math.sqrt(sum((x - mean) ** 2 for x in values) / len(values))


def compute(source_ledger_dir: Path, cutoff: str) -> dict:
    target_date = date.fromisoformat(cutoff)
    if target_date <= FREEZE_DATE:
        raise SystemExit("M3 prospective cutoff must be strictly after 2026-09-09 freeze")
    cutoffs = [
        cutoff,
        (target_date - timedelta(days=7)).isoformat(),
        (target_date - timedelta(days=14)).isoformat(),
    ]
    snapshots = {
        c: _load_source_snapshot(source_ledger_dir / f"{c}.json", c)
        for c in cutoffs
    }
    common = set.intersection(*(set(snapshots[c]["r30"]) for c in cutoffs))
    if len(common) < MIN_COMMON_ASSETS:
        raise SystemExit(
            f"common universe below frozen minimum: {len(common)} < {MIN_COMMON_ASSETS}"
        )
    ranked = {}
    for c in cutoffs:
        ranked[c] = _rank_percentiles({a: snapshots[c]["r30"][a] for a in common})

    rows = []
    for asset in sorted(common):
        pcts = [ranked[c][asset]["pct"] for c in cutoffs]
        mean_pct = sum(pcts) / 3.0
        instability = _population_std(pcts)
        score = mean_pct - 0.50 * instability
        rows.append({
            "asset": asset,
            "m3": score,
            "mean_pct": mean_pct,
            "instability": instability,
            "cutoff_percentiles": {c: ranked[c][asset]["pct"] for c in cutoffs},
            "cutoff_r30": {c: ranked[c][asset]["r30"] for c in cutoffs},
        })
    rows.sort(key=lambda row: (-row["m3"], row["asset"]))
    for idx, row in enumerate(rows, 1):
        row["rank_m3"] = idx

    payload = {
        "schema": "gate_btc.momentum_m3_persistence_snapshot.v1",
        "candidate_id": CANDIDATE_ID,
        "cutoff": cutoff,
        "classification": "PROSPECTIVE_SHADOW",
        "source_cutoffs": cutoffs,
        "source_snapshot_sha256": {c: snapshots[c]["sha256"] for c in cutoffs},
        "common_universe_n": len(common),
        "rows": rows,
        "selection_preview": [row["asset"] for row in rows[:10]],
        "economics_activated": False,
        "retrospective_credit": 0,
        "safety": {
            "research_only": True,
            "shadow_only": True,
            "not_approved": True,
            "engine_feed": False,
            "promotion_eligible": False,
            "orders": 0,
            "real_capital": 0,
            "backfill": False,
            "late_seal": False,
            "counter_reset": False,
            "retune": False,
        },
    }
    payload["snapshot_sha256"] = canonical_sha(payload)
    return payload


def persist(payload: dict, ledger_dir: Path, output: Path) -> None:
    ledger_dir.mkdir(parents=True, exist_ok=True)
    output.parent.mkdir(parents=True, exist_ok=True)
    target = ledger_dir / f"{payload['cutoff']}.json"
    rendered = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if target.exists():
        existing = json.loads(target.read_text(encoding="utf-8"))
        if existing.get("snapshot_sha256") != canonical_sha(existing):
            raise SystemExit("existing M3 snapshot hash mismatch")
        if existing != payload:
            raise SystemExit("duplicate M3 cutoff with different canonical payload")
    else:
        target.write_text(rendered, encoding="utf-8")
    output.write_text(rendered, encoding="utf-8")


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--source-ledger-dir", type=Path, required=True)
    p.add_argument("--ledger-dir", type=Path, required=True)
    p.add_argument("--cutoff", required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    payload = compute(args.source_ledger_dir, args.cutoff)
    persist(payload, args.ledger_dir, args.output)
    print(json.dumps({
        "candidate_id": CANDIDATE_ID,
        "cutoff": payload["cutoff"],
        "common_universe_n": payload["common_universe_n"],
        "snapshot_sha256": payload["snapshot_sha256"],
        "status": "PASS_PROSPECTIVE_SHADOW_SIGNAL_ONLY",
        "orders": 0,
        "real_capital": 0,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
