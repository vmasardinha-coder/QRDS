#!/usr/bin/env python3
"""Capture contemporaneous raw CMC Top-150 universe evidence for V16B.

Research-only / shadow-only. The raw HTTP payload is preserved byte-for-byte and
an adjacent evidence manifest seals availability, request identity, and SHA256.
No strategy parameter, ranking rule, order path, or capital path is changed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

ENDPOINT = "https://pro-api.coinmarketcap.com/public-api/v1/cryptocurrency/map"
PARAMS = {
    "listing_status": "active",
    "limit": 150,
    "sort": "cmc_rank",
    "aux": "status",
}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _rows(payload: Any) -> list[dict[str, Any]]:
    if not isinstance(payload, dict):
        raise RuntimeError("CMC payload must be a JSON object")
    rows = payload.get("data") or payload.get("Data") or []
    if not isinstance(rows, list):
        raise RuntimeError("CMC payload data must be a list")
    rows = [r for r in rows if isinstance(r, dict)]
    if len(rows) < 100:
        raise RuntimeError(f"CMC ranked active snapshot too small: {len(rows)} rows")
    return rows


def capture(out_dir: Path, now: datetime | None = None) -> tuple[Path, Path, dict[str, Any]]:
    captured = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0 GATE-BTC-Research-Only/1.0"})
    response = session.get(ENDPOINT, params=PARAMS, timeout=45)
    response.raise_for_status()
    raw = response.content
    payload = response.json()
    rows = _rows(payload)

    digest = sha256_bytes(raw)
    stamp = captured.strftime("%Y%m%dT%H%M%SZ")
    snapshot_id = f"CMC_TOP150_ACTIVE_{stamp}_{digest[:12]}"
    out_dir.mkdir(parents=True, exist_ok=True)
    raw_path = out_dir / f"{snapshot_id}.raw.json"
    evidence_path = out_dir / f"{snapshot_id}.evidence.json"
    raw_path.write_bytes(raw)

    first = rows[0]
    evidence = {
        "schema": "gate_btc.v16b.cmc_universe_snapshot_evidence.v1",
        "snapshot_id": snapshot_id,
        "snapshot_date": captured.date().isoformat(),
        "available_at_utc": captured.isoformat().replace("+00:00", "Z"),
        "source_ref": response.url,
        "endpoint": ENDPOINT,
        "request_params": PARAMS,
        "http_status": response.status_code,
        "raw_snapshot_sha256": digest,
        "raw_snapshot_bytes": len(raw),
        "rows": len(rows),
        "first_rank_identity": {
            "id": first.get("id"),
            "symbol": first.get("symbol"),
            "slug": first.get("slug"),
            "cmc_rank": first.get("rank", first.get("cmc_rank")),
        },
        "research_only": True,
        "shadow_only": True,
        "not_approved": True,
        "engine_feed": False,
        "orders": 0,
        "real_capital": 0,
    }
    evidence_path.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return raw_path, evidence_path, evidence


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--out-dir", default="artifacts/gate_btc/v16b/cmc_snapshots")
    args = p.parse_args()
    raw_path, evidence_path, evidence = capture(Path(args.out_dir))
    print(json.dumps({
        "status": "OK",
        "snapshot_id": evidence["snapshot_id"],
        "available_at_utc": evidence["available_at_utc"],
        "rows": evidence["rows"],
        "raw_snapshot_sha256": evidence["raw_snapshot_sha256"],
        "raw_path": str(raw_path),
        "evidence_path": str(evidence_path),
        "ORDERS": 0,
        "REAL_CAPITAL": 0,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
