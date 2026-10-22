"""Index exact archived prospective observations; never invent Qlib daily bars."""
import argparse
import csv
import gzip
import hashlib
import io
import json
import math
from datetime import datetime, timezone
from pathlib import Path

from gate_btc_v2a_data_ledger import validated_records

CONTRACT = Path(__file__).resolve().parent / "gate_btc_factory/SYSTEM13_PANEL_PROTOCOL_V1.json"
CONTRACT_SHA256 = "a8f90a269efd64cd939c8707b23c2db31962cdabf6742b0e97bb016be92e4670"


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def utc(s):
    d = datetime.fromisoformat(s.replace("Z", "+00:00"))
    if d.tzinfo is None:
        raise ValueError("OBSERVED_TIMEZONE_REQUIRED")
    return d.astimezone(timezone.utc)


def panel_rows(snapshot, universe_raw, c):
    observed = utc(snapshot["source_run_utc"])
    source = csv.DictReader(io.StringIO(universe_raw.decode("utf-8-sig")))
    rows, ids = [], set()
    for r in source:
        coin = r.get("id", "")
        if not coin or coin in ids:
            raise ValueError("MISSING_OR_DUPLICATE_EXACT_COIN_ID")
        ids.add(coin); reasons = []
        flags = {k: r.get(k, "").lower() for k in ("is_stable", "is_blocked", "standard_ticker")}
        if any(v not in ("true", "false") for v in flags.values()):
            reasons.append("FLAG_UNAVAILABLE")
        if flags["is_stable"] != "false" or flags["is_blocked"] != "false" or flags["standard_ticker"] != "true":
            reasons.append("OBSERVED_UNIVERSE_FILTER_EXCLUDED")
        try:
            price = float(r["current_price"])
            if not math.isfinite(price) or price <= 0:
                raise ValueError()
        except (KeyError, TypeError, ValueError):
            price = None; reasons.append("QUOTE_UNAVAILABLE")
        try:
            quoted = utc(r["last_updated"])
            age = (observed - quoted).total_seconds()
            if age < 0 or age > c["max_quote_age_seconds"]:
                reasons.append("QUOTE_FUTURE_OR_STALE")
        except (KeyError, TypeError, ValueError):
            quoted = None; reasons.append("QUOTE_TIMESTAMP_UNAVAILABLE")
        rows.append({"coin_id": coin, "symbol": r.get("symbol"), "observed_at_utc": observed.isoformat(),
                     "quote_at_utc": quoted.isoformat() if quoted else None, "quote_usd": price,
                     "eligible_by_observed_flags_and_quote": not reasons, "unavailable_or_exclusion_reasons": reasons,
                     "membership_source_record_sha256": snapshot["record_sha256"],
                     "source_data_as_of_diagnostic_only": snapshot["source_data_as_of"],
                     "is_daily_close": False, "training_eligible": False})
    return sorted(rows, key=lambda r: r["coin_id"])


def build(runtime, out):
    raw = CONTRACT.read_bytes()
    if sha(raw) != CONTRACT_SHA256:
        raise ValueError("SYSTEM13_PROTOCOL_HASH_MISMATCH")
    c = json.loads(raw)
    release_path = runtime / "gate_btc_2/system12/READINESS.json"
    release = json.loads(release_path.read_text())
    released = release.get("system12_complete") is True and release.get("system13_dependency_released") is True
    if not released:
        raise ValueError("SYSTEM12_RESEARCH_DEPENDENCY_NOT_RELEASED")
    root = runtime / "data_quality/v2a"
    records = validated_records(root)
    out.mkdir(parents=True, exist_ok=True)
    manifests = []; blocked = []
    for _, path, record in records:
        archive = root / record["universe_archive"]["archive_path"]
        try:
            rows = panel_rows(record, gzip.decompress(archive.read_bytes()), c)
        except (KeyError, TypeError, ValueError) as exc:
            blocked.append({"snapshot_id": record["snapshot_id"], "reason": str(exc)}); continue
        payload = {"schema": "qrds.system13.observed_membership_quote_panel.v1",
                   "snapshot_id": record["snapshot_id"], "protocol_sha256": CONTRACT_SHA256,
                   "source_snapshot_sha256": sha(path.read_bytes()), "source_archive_sha256": sha(archive.read_bytes()),
                   "time_axis": "OBSERVED_AT_NOT_DAILY_CLOSE", "rows": rows,
                   "historical_price_backfill": False, "new_scientific_credit": 0}
        b = json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
        compressed = gzip.compress(b, mtime=0)
        dest = out / "observations" / (record["snapshot_id"] + ".json.gz")
        dest.parent.mkdir(exist_ok=True)
        if dest.exists() and dest.read_bytes() != compressed:
            raise ValueError("IMMUTABLE_PANEL_OBSERVATION_CHANGED")
        if not dest.exists():
            dest.write_bytes(compressed)
        manifests.append({"snapshot_id": record["snapshot_id"], "source_run_utc": record["source_run_utc"],
                          "panel_sha256": sha(compressed), "observed_member_count": len(rows),
                          "valid_quote_member_count": sum(r["eligible_by_observed_flags_and_quote"] for r in rows)})
    status = {"schema": "qrds.system13.observed_panel_status.v1", "protocol_sha256": CONTRACT_SHA256,
              "system12_dependency_released": released, "system12_readiness_sha256": sha(release_path.read_bytes()),
              "status": "OBSERVED_MEMBERSHIP_PANEL_INDEXED_QLIB_TRAINING_BLOCKED",
              "verified_source_snapshots": len(records), "indexed_panel_observations": len(manifests),
              "observed_membership_rows": sum(m["observed_member_count"] for m in manifests),
              "raw_membership_retained": True, "unavailable_snapshots": blocked,
              "required_fields_not_provided_by_quote_archives": c["required_qlib_fields"],
              "blockers": ["GOVERNED_OHLCV_AND_FACTOR_NOT_PRESENT", "SOURCE_ADMISSION_AND_TRADABILITY_NOT_GRANTED",
                           "CHRONOLOGICAL_WARMUP_TRAIN_VALIDATION_HOLDOUT_NOT_QUALIFIED"],
              "system13_complete": False, "training_ready": False, "holdout_read_allowed": False,
              "new_scientific_credit": 0, "external_qlib_economics_imported": False,
              "sources": manifests, "safety": c["safety"]}
    (out / "STATUS.json").write_text(json.dumps(status, indent=2, sort_keys=True) + "\n")
    return status


if __name__ == "__main__":
    p = argparse.ArgumentParser(); p.add_argument("--runtime", type=Path, required=True); p.add_argument("--out", type=Path, required=True)
    a = p.parse_args(); d = build(a.runtime, a.out)
    print(json.dumps({k: v for k, v in d.items() if k != "sources"}, sort_keys=True))
