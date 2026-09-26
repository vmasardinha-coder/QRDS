#!/usr/bin/env python3
"""Append-only prospective CMC identity corpus. Never substitutes training history."""
from __future__ import annotations
import argparse
import csv
import hashlib
import io
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit
from tools import gate_btc_v16b_cmc_persist as legacy

CONTRACT = Path("artifacts/gate_btc/v16b/GATE_BTC_V16B1_UNIVERSE_CUTOVER_20260926.json")
BASE = Path("runtime/evidence/v16b1/prospective_universe")

def digest(data):
    return hashlib.sha256(data).hexdigest()

def encoded(obj):
    return (json.dumps(obj, indent=2, sort_keys=True) + "\n").encode()

def immutable(path, data):
    if path.exists():
        if path.read_bytes() != data:
            raise ValueError("immutable evidence conflict: " + str(path))
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("xb") as f:
            f.write(data)

def persist(capture_dir, runtime_root, run_id, code_sha, now=None, contract_path=CONTRACT):
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError("timezone required")
    if not str(run_id).isdigit() or len(code_sha) != 40 or any(c not in "0123456789abcdef" for c in code_sha):
        raise ValueError("run id and exact source SHA required")
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    raw, evidence, ev = legacy._load_and_validate(capture_dir)
    available = datetime.fromisoformat(ev["available_at_utc"].replace("Z", "+00:00"))
    cutoff = datetime.fromisoformat(contract["not_before_utc"].replace("Z", "+00:00"))
    if available.tzinfo is None or not cutoff <= available <= now:
        raise ValueError("capture outside prospective cutover")
    if available.date().isoformat() != ev["snapshot_date"] or available.date() != now.astimezone(timezone.utc).date():
        raise ValueError("only same-day live captures; no historical intake")
    url = urlsplit(ev["source_ref"])
    if url.scheme != "https" or url.netloc != "pro-api.coinmarketcap.com" or url.path != "/public-api/v1/cryptocurrency/map":
        raise ValueError("unqualified source")
    rows = json.loads(raw.read_bytes()).get("data", [])
    if len(rows) != 150 or ev["rows"] != 150:
        raise ValueError("exact Top-150 required")
    normalized = []
    for r in rows:
        rank = r.get("cmc_rank", r.get("rank"))
        if "rank" in r and "cmc_rank" in r and r["rank"] != r["cmc_rank"]:
            raise ValueError("conflicting rank fields")
        if type(rank) is not int or type(r.get("id")) is not int or r["id"] <= 0:
            raise ValueError("invalid CMC identity or rank")
        if not isinstance(r.get("symbol"), str) or not r["symbol"].strip() or not isinstance(r.get("slug"), str) or not r["slug"].strip():
            raise ValueError("missing CMC identity")
        normalized.append({"cmc_id": r["id"], "cmc_symbol": r["symbol"], "cmc_slug": r["slug"], "cmc_rank": rank})
    if {r["cmc_rank"] for r in normalized} != set(range(1, 151)) or len({r["cmc_id"] for r in normalized}) != 150:
        raise ValueError("non-unique or incomplete Top-150")
    base = runtime_root / BASE
    captures = base / "captures" / ("run_" + str(run_id))
    weekly = available.weekday() == 3 and ev["snapshot_date"] >= contract["first_eligible_thursday"]
    record = {
        "schema": "gate_btc.v16b1.prospective_universe_capture.v1",
        "snapshot_id": ev["snapshot_id"], "snapshot_date": ev["snapshot_date"],
        "available_at_utc": ev["available_at_utc"], "source_ref": ev["source_ref"],
        "raw_sha256": digest(raw.read_bytes()), "evidence_sha256": digest(evidence.read_bytes()),
        "contract_sha256": digest(contract_path.read_bytes()), "source_code_sha": code_sha,
        "github_run_id": int(run_id), "rows": 150,
        "weekly_eligible": weekly, "scientific_credit": 0, "prospective_credit": 0,
        "historical_training_authority": False, "engine_feed": False,
        "research_only": True, "shadow_only": True, "orders": 0, "real_capital": 0,
    }
    # Reruns must prove that all previously persisted bytes remain identical.
    immutable(captures / raw.name, raw.read_bytes())
    immutable(captures / evidence.name, evidence.read_bytes())
    immutable(captures / "CAPTURE.json", encoded(record))
    immutable(base / "CUTOVER.json", contract_path.read_bytes())
    if weekly:
        selected = base / "weeks" / ev["snapshot_date"] / "UNIVERSE.json"
        if not selected.exists():  # Frozen first successful pre-close capture wins.
            buffer = io.StringIO(newline="")
            writer = csv.DictWriter(buffer, fieldnames=["cmc_id", "cmc_symbol", "cmc_slug", "cmc_rank"], lineterminator="\n")
            writer.writeheader()
            writer.writerows(sorted(normalized, key=lambda r: r["cmc_rank"]))
            csv_bytes = buffer.getvalue().encode()
            immutable(selected.parent / "CMC_IDENTITIES.csv", csv_bytes)
            immutable(selected, encoded({**record, "identities_sha256": digest(csv_bytes)}))
        else:
            prior = json.loads(selected.read_text())
            if digest((selected.parent / "CMC_IDENTITIES.csv").read_bytes()) != prior["identities_sha256"]:
                raise ValueError("weekly identities hash mismatch")
    weeks = sorted(p.parent.name for p in (base / "weeks").glob("*/UNIVERSE.json"))
    status = {
        "schema": "gate_btc.v16b1.prospective_universe_status.v1",
        "status": "ACCUMULATING_WEEKLY_UNIVERSE" if weeks else "WAITING_FIRST_ELIGIBLE_THURSDAY",
        "cutover_contract_sha256": digest(contract_path.read_bytes()),
        "latest_capture": record, "observed_week_count": len(weeks), "observed_weeks": weeks,
        "first_eligible_thursday": contract["first_eligible_thursday"],
        "historical_training_input_replaced": False, "training_ready": False,
        "frozen_model_min_prior_weeks": 52,
        "remaining_blocker": "MISSING_AUTHORITATIVE_MODEL_TRAINING_HISTORY",
        "scientific_credit": 0, "prospective_credit": 0, "engine_feed": False,
        "research_only": True, "shadow_only": True, "no_backfill": True,
        "no_retune": True, "orders": 0, "real_capital": 0,
    }
    (base / "STATUS.json").write_bytes(encoded(status))
    return status

def main():
    p = argparse.ArgumentParser()
    for field in ("capture-dir", "runtime-root", "run-id", "code-sha"):
        p.add_argument("--" + field, required=True)
    a = p.parse_args()
    out = persist(Path(a.capture_dir), Path(a.runtime_root), a.run_id, a.code_sha)
    print(json.dumps(out, sort_keys=True))

if __name__ == "__main__":
    main()
