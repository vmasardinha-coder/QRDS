#!/usr/bin/env python3
from __future__ import annotations

import argparse
import itertools
import json
import re
from pathlib import Path

FEATURES = (
    "OPEN_RETURN", "OPEN_RANGE", "REALIZED_VOL", "VOLUME_EARLY",
    "BAR_IMBALANCE", "CLOSE_LOCATION", "BODY_RANGE", "GAP_FROM_PRIOR_CLOSE",
)
DIRECTIONS = ("CONTINUATION", "REVERSION")
WINDOWS = (15, 30, 60, 90)
THRESHOLDS = (0.75, 1.00, 1.25, 1.50)
HORIZONS = (30, 60, 120)
START_FAMILY = 170
GEN_SIZE = 10
RESULT_RE = re.compile(r"gate_btc_b3_h(\d+)_h(\d+)_result\.json$")


def universe() -> list[tuple[str, str, int, float]]:
    return list(itertools.product(FEATURES, DIRECTIONS, WINDOWS, THRESHOLDS))


def latest_closed_frontier(root: Path) -> tuple[int, int] | None:
    rows: list[tuple[int, int, Path]] = []
    for p in (root / "tools").glob("gate_btc_b3_h*_h*_result.json"):
        m = RESULT_RE.search(p.name)
        if not m:
            continue
        a, b = map(int, m.groups())
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        status = str(d.get("status", ""))
        if status.startswith("CLOSED_") or status.startswith("SURVIVORS_"):
            rows.append((a, b, p))
    if not rows:
        return None
    a, b, _ = max(rows, key=lambda x: x[1])
    return a, b


def build_generation(start: int) -> dict:
    if start < START_FAMILY or start % 10:
        raise RuntimeError(f"NONCANONICAL_START:{start}")
    u = universe()
    offset = start - START_FAMILY
    if offset + GEN_SIZE > len(u):
        raise RuntimeError("AUTONOMOUS_SCIENCE_GRAMMAR_EXHAUSTED")
    fams = []
    for i in range(GEN_SIZE):
        fid = start + i
        feature, direction, window, threshold = u[offset + i]
        fams.append({
            "family_id": f"H{fid}",
            "feature": feature,
            "direction": direction,
            "decision_window_minutes": window,
            "abs_z_threshold": threshold,
            "holding_horizons_minutes": list(HORIZONS),
            "causal_standardization": "ROLLING_20_PRIOR_SESSIONS_MEDIAN_MAD",
        })
    return {
        "schema": "gate_btc.b3.autonomous_family_contract.v1",
        "generation": f"H{start}-H{start+9}",
        "protocol": "research/b3_autonomous_science_protocol_v1.md",
        "frozen_before_economics": True,
        "discovery": "2022-01-01/2024-12-31",
        "replication": "2020-01-01/2021-12-31",
        "h1_cutoff_exclusive": "2026-08-10",
        "max_survivors": 2,
        "research_only": True,
        "shadow_only": True,
        "not_approved": True,
        "orders": 0,
        "real_capital": 0,
        "engine_feed": False,
        "h1_economics_read": False,
        "families": fams,
    }


def next_generation(root: Path) -> dict:
    latest = latest_closed_frontier(root)
    if latest is None:
        raise RuntimeError("NO_CANONICAL_CLOSED_FRONTIER")
    _, end = latest
    start = ((end // 10) + 1) * 10
    if start < START_FAMILY:
        start = START_FAMILY
    return build_generation(start)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--start", type=int)
    ap.add_argument("--out")
    args = ap.parse_args()
    root = Path(args.root)
    d = build_generation(args.start) if args.start is not None else next_generation(root)
    text = json.dumps(d, indent=2, ensure_ascii=False) + "\n"
    if args.out:
        p = Path(args.out)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
