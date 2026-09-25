from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from tools import gate_btc_v16b_cmc_persist as persist


def _capture(root: Path, date: str, stamp: str = "231500Z") -> Path:
    root.mkdir(parents=True, exist_ok=True)
    raw_bytes = b'{"data":[' + b','.join([b'{"id":1}' for _ in range(100)]) + b']}'
    digest = hashlib.sha256(raw_bytes).hexdigest()
    snapshot_id = f"CMC_TOP150_ACTIVE_{date.replace('-', '')}T{stamp}_{digest[:12]}"
    raw = root / f"{snapshot_id}.raw.json"
    evp = root / f"{snapshot_id}.evidence.json"
    raw.write_bytes(raw_bytes)
    ev = {
        "schema": "gate_btc.v16b.cmc_universe_snapshot_evidence.v1",
        "snapshot_id": snapshot_id,
        "snapshot_date": date,
        "available_at_utc": f"{date}T23:15:00Z",
        "source_ref": "https://pro-api.coinmarketcap.com/public-api/v1/cryptocurrency/map?limit=150",
        "raw_snapshot_sha256": digest,
        "rows": 100,
        "research_only": True,
        "shadow_only": True,
        "not_approved": True,
        "engine_feed": False,
        "orders": 0,
        "real_capital": 0,
    }
    evp.write_text(json.dumps(ev, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return root


def test_thursday_capture_is_persisted_append_only(tmp_path: Path):
    capture = _capture(tmp_path / "capture", "2026-10-01")
    runtime = tmp_path / "runtime-root"
    out = persist.persist(capture, runtime, "12345")
    assert out["status"] == "PERSISTED"
    base = runtime / "runtime/evidence/v16b/cmc_weekly"
    assert (base / "2026-10-01/run_12345/PERSISTENCE.json").exists()
    rows = [json.loads(x) for x in (base / "INDEX.jsonl").read_text().splitlines()]
    assert len(rows) == 1
    assert rows[0]["github_run_id"] == 12345
    assert rows[0]["prospective_credit"] == 0


def test_same_run_is_idempotent(tmp_path: Path):
    capture = _capture(tmp_path / "capture", "2026-10-01")
    runtime = tmp_path / "runtime-root"
    first = persist.persist(capture, runtime, "12345")
    second = persist.persist(capture, runtime, "12345")
    assert first["status"] == "PERSISTED"
    assert second["status"] == "ALREADY_PERSISTED"
    index = runtime / "runtime/evidence/v16b/cmc_weekly/INDEX.jsonl"
    assert len(index.read_text().splitlines()) == 1


def test_non_thursday_is_not_persisted(tmp_path: Path):
    capture = _capture(tmp_path / "capture", "2026-10-02")
    runtime = tmp_path / "runtime-root"
    out = persist.persist(capture, runtime, "12346")
    assert out["status"] == "NOT_THURSDAY_NO_PERSIST"
    assert not (runtime / "runtime/evidence/v16b/cmc_weekly").exists()


def test_hash_mismatch_fails_closed(tmp_path: Path):
    capture = _capture(tmp_path / "capture", "2026-10-01")
    raw = next(capture.glob("*.raw.json"))
    raw.write_bytes(b"tampered")
    with pytest.raises(ValueError, match="hash mismatch"):
        persist.persist(capture, tmp_path / "runtime-root", "12347")


def test_conflicting_existing_run_fails_closed(tmp_path: Path):
    capture = _capture(tmp_path / "capture", "2026-10-01")
    runtime = tmp_path / "runtime-root"
    persist.persist(capture, runtime, "12348")
    index = runtime / "runtime/evidence/v16b/cmc_weekly/INDEX.jsonl"
    row = json.loads(index.read_text().strip())
    row["raw_snapshot_sha256"] = "0" * 64
    index.write_text(json.dumps(row) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="conflicts"):
        persist.persist(capture, runtime, "12348")
