#!/usr/bin/env python3
"""Fail-closed helpers for QRDS factory append-only ledger surfaces."""
from __future__ import annotations

import json
from pathlib import Path

EXPECTED_SAFETY = {
    "RESEARCH_ONLY": True,
    "SHADOW_ONLY": True,
    "NOT_APPROVED": True,
    "ORDERS": 0,
    "REAL_CAPITAL": 0,
    "ENGINE_FEED": False,
}


def load_contract(factory_dir: Path) -> dict:
    path = factory_dir / "LEDGER_CONTRACT.v1.json"
    if not path.is_file():
        raise SystemExit("FAIL missing LEDGER_CONTRACT.v1.json")
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise SystemExit(f"FAIL invalid ledger contract JSON: {exc}") from exc
    if not isinstance(doc, dict):
        raise SystemExit("FAIL ledger contract must be an object")
    if doc.get("schema") != "qrds.factory.ledger_contract.v1":
        raise SystemExit("FAIL unexpected ledger contract schema")
    if doc.get("append_only") is not True:
        raise SystemExit("FAIL ledger contract is not append-only")
    if doc.get("write_scope") != "tools/gate_btc_factory/":
        raise SystemExit("FAIL ledger contract escaped factory write scope")
    if doc.get("safety") != EXPECTED_SAFETY:
        raise SystemExit("FAIL ledger contract safety mismatch")
    rules = doc.get("entry_rules", {})
    required_true = [
        "id_required",
        "timestamp_utc_required",
        "immutable_identity_fields_required",
        "duplicate_id_forbidden",
        "rewrite_or_delete_forbidden",
        "partial_blind_holdout_economics_forbidden",
        "backfill_forbidden",
        "retune_frozen_forbidden",
    ]
    if any(rules.get(key) is not True for key in required_true):
        raise SystemExit("FAIL ledger contract entry rules are incomplete")
    return doc


def _load_jsonl(path: Path) -> list[dict]:
    rows: list[dict] = []
    for lineno, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not raw.strip():
            continue
        try:
            row = json.loads(raw)
        except Exception as exc:
            raise SystemExit(f"FAIL invalid JSONL {path.name}:{lineno}: {exc}") from exc
        if not isinstance(row, dict):
            raise SystemExit(f"FAIL non-object JSONL row {path.name}:{lineno}")
        rows.append(row)
    if not rows:
        raise SystemExit(f"FAIL empty ledger: {path.name}")
    return rows


def validate_ledgers(factory_dir: Path) -> dict:
    contract = load_contract(factory_dir)
    ledgers = contract.get("ledgers")
    if not isinstance(ledgers, dict) or not ledgers:
        raise SystemExit("FAIL ledger contract has no ledgers")

    summary: dict[str, dict] = {}
    for ledger_name, filename in sorted(ledgers.items()):
        path = factory_dir / filename
        if not path.is_file():
            raise SystemExit(f"FAIL missing ledger file: {filename}")
        rows = _load_jsonl(path)
        meta = rows[0]
        if meta.get("record_type") != "LEDGER_META":
            raise SystemExit(f"FAIL first row is not LEDGER_META: {filename}")
        if meta.get("ledger") != ledger_name:
            raise SystemExit(f"FAIL ledger identity mismatch: {filename}")
        if meta.get("append_only") is not True:
            raise SystemExit(f"FAIL ledger not append-only: {filename}")
        if meta.get("safety") != EXPECTED_SAFETY:
            raise SystemExit(f"FAIL ledger safety mismatch: {filename}")
        if not isinstance(meta.get("created_at_utc"), str) or not meta.get("created_at_utc"):
            raise SystemExit(f"FAIL ledger meta timestamp missing: {filename}")

        ids: set[str] = set()
        records = 0
        for row in rows[1:]:
            records += 1
            record_id = row.get("id")
            if not isinstance(record_id, str) or not record_id:
                raise SystemExit(f"FAIL ledger record missing id: {filename}")
            if record_id in ids:
                raise SystemExit(f"FAIL duplicate ledger id {record_id}: {filename}")
            ids.add(record_id)
            timestamp = row.get("created_at_utc") or row.get("closed_at_utc") or row.get("observed_at_utc")
            if not isinstance(timestamp, str) or not timestamp:
                raise SystemExit(f"FAIL ledger record missing UTC timestamp: {filename}")
            safety = row.get("safety")
            if safety is not None and safety != EXPECTED_SAFETY:
                raise SystemExit(f"FAIL ledger record safety mismatch: {filename}:{record_id}")

        summary[ledger_name] = {
            "file": filename,
            "meta_present": True,
            "records": records,
            "duplicate_ids": 0,
            "append_only": True,
            "safety": "PASS",
        }
    return summary
