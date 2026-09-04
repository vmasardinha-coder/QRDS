#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SOURCE_REPO = "wesleyzilva/tradetech"
SOURCES = (
    {
        "commit": "e891c7be2257b4ff439d04661df1971e6df19684",
        "path": "CandlesHistoryDatas/2024_26/WINFUT_F_0_5min.csv",
    },
    {
        "commit": "0deb43c668dcd447ed169c9cafb52af625d5419e",
        "path": "CandlesHistoryDatas/CandlesHistoricos2026/WINFUT_F_0_5min.csv",
    },
)
HOLDOUT_START = "2025-01-01"
CUTOFF_EXCLUSIVE = "2026-08-10"
BATCH_SIZE = 64
MIN_ELIGIBLE_SESSIONS_PER_WINDOW = 161

SAFETY = {
    "research_only": True,
    "shadow_only": True,
    "not_approved": True,
    "engine_feed": False,
    "orders": 0,
    "real_capital": 0,
    "no_retune": True,
    "no_backfill": True,
    "no_counter_reset": True,
    "fail_closed": True,
    "h1_economics_read": False,
}


def raw_url(source: dict[str, str]) -> str:
    return f"https://raw.githubusercontent.com/{SOURCE_REPO}/{source['commit']}/{source['path']}"


def sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def parse_number(text: str) -> float:
    return float(str(text).strip().replace(".", "").replace(",", "."))


def normalize_source(raw: bytes) -> list[dict[str, Any]]:
    reader = csv.DictReader(io.StringIO(raw.decode("latin1")), delimiter=";")
    rows: list[dict[str, Any]] = []
    for r in reader:
        if str(r.get("Ativo") or "").strip().upper() != "WINFUT":
            continue
        date_s, time_s = str(r.get("Data") or "").strip(), str(r.get("Hora") or "").strip()
        if not date_s or not time_s:
            continue
        dt = datetime.strptime(f"{date_s} {time_s}", "%d/%m/%Y %H:%M:%S")
        day = dt.strftime("%Y-%m-%d")
        if day < HOLDOUT_START or day >= CUTOFF_EXCLUSIVE:
            continue
        rows.append({
            "timestamp": dt.strftime("%Y-%m-%d %H:%M:%S"),
            "open": parse_number(r.get("Abertura") or ""),
            "high": parse_number(r.get("Máximo") or ""),
            "low": parse_number(r.get("Mínimo") or ""),
            "close": parse_number(r.get("Fechamento") or ""),
            "volume": parse_number(r.get("Volume") or r.get("Quantidade") or "0"),
        })
    return rows


def merge_sources(raw_sources: list[bytes]) -> list[dict[str, Any]]:
    dedup: dict[str, dict[str, Any]] = {}
    for raw in raw_sources:
        for row in normalize_source(raw):
            ts = str(row["timestamp"])
            prior = dedup.get(ts)
            if prior is not None and prior != row:
                raise RuntimeError(f"CONFLICTING_SOURCE_ROW:{ts}")
            dedup[ts] = row
    return [dedup[k] for k in sorted(dedup)]


def eligible_sessions(rows: list[dict[str, Any]]) -> list[str]:
    by_day: dict[str, list[datetime]] = defaultdict(list)
    for row in rows:
        dt = datetime.strptime(str(row["timestamp"]), "%Y-%m-%d %H:%M:%S")
        by_day[dt.strftime("%Y-%m-%d")].append(dt)
    eligible: list[str] = []
    for day, stamps in sorted(by_day.items()):
        stamps = sorted(set(stamps))
        if len(stamps) < 40:
            continue
        if any(int((b - a).total_seconds()) != 300 for a, b in zip(stamps, stamps[1:])):
            continue
        eligible.append(day)
    return eligible


def split_windows(sessions: list[str]) -> dict[str, dict[str, str]]:
    if len(sessions) < 2 * MIN_ELIGIBLE_SESSIONS_PER_WINDOW:
        raise RuntimeError(f"INSUFFICIENT_FORWARD_UNSEEN_SESSIONS:{len(sessions)}")
    mid = len(sessions) // 2
    mid = max(mid, MIN_ELIGIBLE_SESSIONS_PER_WINDOW)
    mid = min(mid, len(sessions) - MIN_ELIGIBLE_SESSIONS_PER_WINDOW)
    discovery, replication = sessions[:mid], sessions[mid:]
    if len(discovery) < MIN_ELIGIBLE_SESSIONS_PER_WINDOW or len(replication) < MIN_ELIGIBLE_SESSIONS_PER_WINDOW:
        raise RuntimeError("WINDOW_SESSION_MINIMUM_NOT_MET")
    if discovery[0] < HOLDOUT_START or replication[0] < HOLDOUT_START:
        raise RuntimeError("HOLDOUT_START_BREACH")
    return {
        "discovery": {"start": discovery[0], "end": discovery[-1]},
        "replication": {"start": replication[0], "end": replication[-1]},
    }


def load_json(path: Path) -> dict[str, Any]:
    obj = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(obj, dict):
        raise RuntimeError(f"EXPECTED_OBJECT:{path}")
    return obj


def affected_ids(root: dict[str, Any]) -> list[str]:
    scope = root.get("affected_scope") or {}
    ids = [str(x) for x in scope.get("family_ids") or []]
    count = int(scope.get("family_count", len(ids)))
    if count != len(ids) or count == 0 or len(set(ids)) != len(ids):
        raise RuntimeError("INVALID_AFFECTED_SCOPE")
    return ids


def assert_forward_window_unread(results_dir: Path, ids: list[str]) -> None:
    wanted, seen = set(ids), set()
    for p in sorted(results_dir.glob("gate_btc_b3_h*_h*_result.json")):
        d = load_json(p)
        for fam in d.get("families") or []:
            fid = str(fam.get("family_id") or "")
            if fid not in wanted:
                continue
            seen.add(fid)
            payload = json.dumps({"discovery": fam.get("discovery"), "replication": fam.get("replication")}, sort_keys=True)
            if "2025H" in payload or "2026H" in payload or "2025-" in payload or "2026-" in payload:
                raise RuntimeError(f"FORWARD_WINDOW_ALREADY_READ:{fid}")
    missing = wanted - seen
    if missing:
        raise RuntimeError(f"MISSING_HISTORICAL_RESULTS:{len(missing)}:{sorted(missing)[:5]}")


def write_dataset(path: Path, rows: list[dict[str, Any]]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["timestamp", "open", "high", "low", "close", "volume"])
        w.writeheader(); w.writerows(rows)
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_gate(batch_ids: list[str], batch_no: int, dataset_rel: str, dataset_sha: str,
               source_evidence: list[dict[str, str]], windows: dict[str, dict[str, str]], session_count: int) -> dict[str, Any]:
    return {
        "schema": "qrds.factory.invalidated_family_scoped_source_gate.v1",
        "source_gate_id": f"WIN_M5_STRICT_FORWARD_UNSEEN_2025_2026_BATCH_{batch_no:02d}",
        "family_ids": batch_ids,
        "qualified": True,
        "free_or_official_auditable": True,
        "publication_semantics_proven": True,
        "revision_semantics_proven": True,
        "identity_qa_pass": True,
        "schema_qa_pass": True,
        "point_in_time_valid": True,
        "independent_unseen_evaluation_data": True,
        "no_historical_backfill_credit": True,
        "economics_pre_read": False,
        "evaluation_namespace": "RQ_STRICT_FORWARD_UNSEEN_2025_2026_V2",
        "dataset_relative_path": dataset_rel,
        "dataset_sha256": dataset_sha,
        "windows": windows,
        "source": {
            "repository": SOURCE_REPO,
            "objects": source_evidence,
            "instrument": "WINFUT",
            "bar_interval": "M5",
            "timezone": "America/Sao_Paulo",
            "provenance": "NEOLOGICA_PROFIT_EXPORT_PUBLISHED_IN_PUBLIC_GIT_REPOSITORY",
            "revision_semantics": "IMMUTABLE_PINNED_GIT_COMMITS_AND_HASH_BOUND_NORMALIZED_DATASET",
            "independence_mode": "STRICT_TEMPORAL_HOLDOUT_2025_PLUS_NOT_READ_BY_ORIGINAL_2020_2024_EVALUATOR",
            "holdout_start": HOLDOUT_START,
            "cutoff_exclusive": CUTOFF_EXCLUSIVE,
            "eligible_session_count": session_count,
        },
        "historical_observations_credited": 0,
        "same_historical_window_rerun": False,
        "scientific_change_allowed": False,
        "safety": dict(SAFETY),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root-cause", type=Path, required=True)
    ap.add_argument("--results-dir", type=Path, required=True)
    ap.add_argument("--runtime-root", type=Path, required=True)
    ns = ap.parse_args()

    root = load_json(ns.root_cause)
    if root.get("root_cause_classification") != "SOURCE_DATA_GAP":
        raise RuntimeError("ROOT_CAUSE_NOT_SOURCE_DATA_GAP")
    ids = affected_ids(root)
    assert_forward_window_unread(ns.results_dir, ids)

    raws, evidence = [], []
    for source in SOURCES:
        req = urllib.request.Request(raw_url(source), headers={"User-Agent": "QRDS-research-only-forward-holdout"})
        with urllib.request.urlopen(req, timeout=90) as r:
            raw = r.read()
        raws.append(raw)
        evidence.append({"commit": source["commit"], "path": source["path"], "raw_sha256": sha256_bytes(raw)})
    rows = merge_sources(raws)
    sessions = eligible_sessions(rows)
    windows = split_windows(sessions)

    data_dir = ns.runtime_root / "datasets"
    gates_dir = ns.runtime_root / "source_gates"
    dataset = data_dir / "WIN_M5_STRICT_FORWARD_UNSEEN_2025_2026.csv"
    dataset_sha = write_dataset(dataset, rows)
    repo_root = ns.runtime_root.parents[2]
    dataset_rel = str(dataset.relative_to(repo_root)).replace("\\", "/")
    gates_dir.mkdir(parents=True, exist_ok=True)
    for old in gates_dir.glob("WIN_M5_*FORWARD_UNSEEN_2025_2026_BATCH_*.json"):
        old.unlink()

    batches = [ids[i:i+BATCH_SIZE] for i in range(0, len(ids), BATCH_SIZE)]
    for i, batch in enumerate(batches, start=1):
        gate = build_gate(batch, i, dataset_rel, dataset_sha, evidence, windows, len(sessions))
        (gates_dir / f"WIN_M5_STRICT_FORWARD_UNSEEN_2025_2026_BATCH_{i:02d}.json").write_text(
            json.dumps(gate, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    manifest = {
        "schema": "qrds.factory.invalidated_forward_holdout_manifest.v2",
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "affected_family_count": len(ids),
        "batch_count": len(batches),
        "batch_size": BATCH_SIZE,
        "eligible_session_count": len(sessions),
        "minimum_sessions_per_window": MIN_ELIGIBLE_SESSIONS_PER_WINDOW,
        "holdout_start": HOLDOUT_START,
        "cutoff_exclusive": CUTOFF_EXCLUSIVE,
        "windows": windows,
        "dataset_relative_path": dataset_rel,
        "dataset_sha256": dataset_sha,
        "sources": evidence,
        "forward_unseen_verified_against_original_results": True,
        "economics_read_during_gate_build": False,
        "historical_observations_credited": 0,
        "safety": dict(SAFETY),
    }
    (ns.runtime_root / "FORWARD_HOLDOUT_MANIFEST.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"affected": len(ids), "batches": len(batches), "sessions": len(sessions), "windows": windows,
                      "dataset_sha256": dataset_sha, "orders": 0, "real_capital": 0}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
