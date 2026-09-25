#!/usr/bin/env python3
"""Read-only health view for preregistered external prospective collectors.

Measures observed cadence from append-only histories. It never reconstructs missed
captures, changes cadence, assigns economics, promotes science, feeds engines,
sends orders or uses real capital.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

FAMILIES = ("F-XVOL-SURFACE", "F-XMM-INVENTORY")


def parse_dt(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def load_history(path: Path) -> list[dict]:
    if not path.is_file():
        raise FileNotFoundError(f"REQUIRED_HISTORY_MISSING:{path}")
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not rows:
        raise RuntimeError(f"EMPTY_HISTORY:{path}")
    return rows


def cadence_hours(prereg: dict) -> float:
    cron = str(prereg["collection_cadence"]["cron_utc"])
    if cron != "17 */4 * * *":
        raise RuntimeError(f"UNSUPPORTED_OR_CHANGED_PREREG_CADENCE:{cron}")
    return 4.0


def family_health(rows: list[dict], cadence_h: float, now: datetime) -> dict:
    times = [parse_dt(str(r["observed_at_utc"])) for r in rows]
    if times != sorted(times):
        raise RuntimeError("NON_MONOTONIC_EXTERNAL_HISTORY")
    intervals = [(b - a).total_seconds() / 3600.0 for a, b in zip(times, times[1:])]
    over = [x for x in intervals if x > cadence_h]
    latest = times[-1]
    return {
        "record_count": len(rows),
        "first_observed_at_utc": times[0].isoformat(),
        "latest_observed_at_utc": latest.isoformat(),
        "latest_age_hours": round((now - latest).total_seconds() / 3600.0, 6),
        "preregistered_collection_cadence_hours": cadence_h,
        "observed_interval_count": len(intervals),
        "intervals_over_preregistered_cadence": len(over),
        "max_observed_interval_hours": round(max(intervals), 6) if intervals else None,
        "latest_interval_hours": round(intervals[-1], 6) if intervals else None,
        "note": "Intervals above the preregistered collection cadence are operational delivery gaps/delays only. This monitor never reconstructs them and assigns zero scientific/economic interpretation.",
    }


def build(main_root: Path, external_root: Path) -> dict:
    prereg = json.loads((main_root / "artifacts/gate_btc_2/family_handoffs/EXTERNAL_FORWARD_COLLECTION_PREREG_20260922.json").read_text(encoding="utf-8"))
    cadence_h = cadence_hours(prereg)
    now = datetime.now(timezone.utc)
    families = {}
    for fid in FAMILIES:
        rows = load_history(external_root / f"runtime/gate_btc_2/external_family_forward/{fid}/HISTORY.jsonl")
        families[fid] = family_health(rows, cadence_h, now)
    return {
        "schema": "gate_btc_2.external_collection_health.v1",
        "generated_at_utc": now.isoformat(),
        "mode": "READ_ONLY_OPERATIONAL_HEALTH",
        "preregistered_cron_utc": prereg["collection_cadence"]["cron_utc"],
        "cadence_meaning": prereg["collection_cadence"]["meaning"],
        "families": families,
        "authority": {
            "backfill_authority": False,
            "cadence_change_authority": False,
            "source_admission_authority": False,
            "promotion_authority": False,
            "execution_authority": False,
            "scientific_credit": 0,
        },
        "safety": {
            "RESEARCH_ONLY": True,
            "SHADOW_ONLY": True,
            "NO_BACKFILL": True,
            "NO_RETUNE": True,
            "ENGINE_FEED": False,
            "ORDERS": 0,
            "REAL_CAPITAL": 0,
        },
    }


def render_md(x: dict) -> str:
    lines = [
        "# GATE BTC 2.0 — External Collection Health", "",
        f"Generated: `{x['generated_at_utc']}`", "",
        f"Preregistered cadence: `{x['preregistered_cron_utc']}`", "",
        "| Family | Records | Latest age h | Latest interval h | Max interval h | Intervals > 4h |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for fid, h in x["families"].items():
        lines.append(f"| `{fid}` | {h['record_count']} | {h['latest_age_hours']:.2f} | {h['latest_interval_hours']:.2f} | {h['max_observed_interval_hours']:.2f} | {h['intervals_over_preregistered_cadence']} |")
    lines += ["", "This is operational observability only. Cadence gaps are not backfilled and carry zero scientific/economic interpretation.", ""]
    return "\n".join(lines)


def self_test() -> None:
    base = datetime(2026, 1, 1, tzinfo=timezone.utc)
    rows = [
        {"observed_at_utc": base.isoformat()},
        {"observed_at_utc": base.replace(hour=4).isoformat()},
        {"observed_at_utc": base.replace(hour=9).isoformat()},
    ]
    h = family_health(rows, 4.0, base.replace(hour=10))
    assert h["intervals_over_preregistered_cadence"] == 1
    assert h["max_observed_interval_hours"] == 5.0
    print("EXTERNAL_COLLECTION_HEALTH_SELF_TEST=PASS")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--main-root", type=Path)
    ap.add_argument("--external-root", type=Path)
    ap.add_argument("--out-json", type=Path)
    ap.add_argument("--out-md", type=Path)
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        self_test(); return 0
    if not all((a.main_root, a.external_root, a.out_json, a.out_md)):
        ap.error("--main-root --external-root --out-json --out-md required")
    x = build(a.main_root, a.external_root)
    a.out_json.parent.mkdir(parents=True, exist_ok=True)
    a.out_md.parent.mkdir(parents=True, exist_ok=True)
    a.out_json.write_text(json.dumps(x, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    a.out_md.write_text(render_md(x), encoding="utf-8")
    print(json.dumps({fid: x['families'][fid] for fid in FAMILIES}, sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
