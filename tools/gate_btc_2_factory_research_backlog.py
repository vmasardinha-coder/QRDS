#!/usr/bin/env python3
"""Read-only backlog inventory for registered GATE BTC 2.0 hypotheses.

Observability only: this script never allocates family ids, admits sources,
creates collectors, promotes science, backfills, retunes, feeds engines,
sends orders, or uses real capital.
"""
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path

DOC_GLOB = "GATE_BTC_2_HYPOTHESIS_*.md"


def strip_md(value: str) -> str:
    return value.strip().strip("*` ")


def parse_doc(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    title = re.search(r"^#\s+Gate BTC 2\.0\s+[—-]\s+(.+?)\s*$", text, re.M | re.I)
    status = re.search(r"^Status:\s*(.+?)\s*$", text, re.M | re.I)
    eligibility = re.search(r"^Prospective eligibility:\s*(.+?)\s*$", text, re.M | re.I)
    engine_weight = re.search(r"^Engine weight:\s*(.+?)\s*$", text, re.M | re.I)
    registered = re.search(r"^Registered:\s*(.+?)\s*$", text, re.M | re.I)
    readiness = re.search(r"\|\s*Family\s*\|\s*Status\s*\|\s*Data-readiness\s*\|", text, re.I)
    disposition_row = None
    if readiness:
        for line in text[readiness.start():].splitlines()[2:8]:
            if line.strip().startswith("|") and "---" not in line:
                cells = [c.strip() for c in line.strip().strip("|").split("|")]
                if len(cells) >= 5:
                    disposition_row = cells
                    break
    family_id = strip_md(title.group(1)) if title else path.stem
    row = {
        "family_id": family_id,
        "document": str(path.as_posix()),
        "status": strip_md(status.group(1)) if status else "UNSPECIFIED",
        "prospective_eligibility": strip_md(eligibility.group(1)) if eligibility else "UNSPECIFIED",
        "engine_weight": strip_md(engine_weight.group(1)) if engine_weight else "UNSPECIFIED",
        "registered": strip_md(registered.group(1)) if registered else None,
        "data_readiness": None,
    }
    if disposition_row and strip_md(disposition_row[0]).upper() == family_id.upper():
        row["status"] = strip_md(disposition_row[1])
        row["data_readiness"] = strip_md(disposition_row[2])
        row["engine_weight"] = strip_md(disposition_row[3])
        row["prospective_eligibility"] = strip_md(disposition_row[4])
    return row


def build(main_root: Path) -> dict:
    docs_root = main_root / "crypto_decision_lab/docs"
    rows = [parse_doc(p) for p in sorted(docs_root.glob(DOC_GLOB))]
    not_eligible = [r for r in rows if r["prospective_eligibility"].upper() == "NOT_ELIGIBLE"]
    eligible = [r for r in rows if r["prospective_eligibility"].upper() not in {"NOT_ELIGIBLE", "UNSPECIFIED"}]
    return {
        "schema": "gate_btc_2.factory_research_backlog.v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "mode": "READ_ONLY_RESEARCH_BACKLOG",
        "summary": {
            "registered_hypothesis_documents": len(rows),
            "not_eligible_count": len(not_eligible),
            "non_not_eligible_count": len(eligible),
        },
        "families": rows,
        "authority": {
            "source_admission_authority": False,
            "family_id_allocation_authority": False,
            "collector_creation_authority": False,
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
        "# GATE BTC 2.0 — Factory Research Backlog",
        "",
        f"Generated: `{x['generated_at_utc']}`",
        "",
        f"- Registered hypothesis documents: **{x['summary']['registered_hypothesis_documents']}**",
        f"- Prospectively NOT_ELIGIBLE: **{x['summary']['not_eligible_count']}**",
        "",
        "| Family | Status | Data readiness | Prospective eligibility | Engine weight |",
        "|---|---|---|---|---:|",
    ]
    for row in x["families"]:
        lines.append(
            f"| `{row['family_id']}` | `{row['status']}` | `{row['data_readiness'] or 'UNSPECIFIED'}` | "
            f"`{row['prospective_eligibility']}` | `{row['engine_weight']}` |"
        )
    lines += [
        "",
        "Backlog is observability only. NOT_ELIGIBLE means no collector/source admission/promotion is authorized by this artifact.",
        "",
        "`RESEARCH_ONLY=true` · `SHADOW_ONLY=true` · `NO_BACKFILL=true` · `NO_RETUNE=true` · `ENGINE_FEED=false` · `ORDERS=0` · `REAL_CAPITAL=0`",
        "",
    ]
    return "\n".join(lines)


def self_test() -> None:
    assert strip_md("**NOT_ELIGIBLE**") == "NOT_ELIGIBLE"
    assert strip_md("`0`") == "0"
    print("FACTORY_RESEARCH_BACKLOG_SELF_TEST=PASS")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--main-root", type=Path)
    ap.add_argument("--out-json", type=Path)
    ap.add_argument("--out-md", type=Path)
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        self_test()
        return 0
    if not all((a.main_root, a.out_json, a.out_md)):
        ap.error("--main-root, --out-json and --out-md are required")
    x = build(a.main_root)
    a.out_json.parent.mkdir(parents=True, exist_ok=True)
    a.out_md.parent.mkdir(parents=True, exist_ok=True)
    a.out_json.write_text(json.dumps(x, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    a.out_md.write_text(render_md(x), encoding="utf-8")
    print(json.dumps(x["summary"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
