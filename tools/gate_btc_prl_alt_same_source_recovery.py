#!/usr/bin/env python3
"""Reuse QOS sealed same-source exact closes for current PRL/ALT delivery."""
from __future__ import annotations
import argparse
import csv
import gzip
import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def packed(value):
    return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n").encode()


def recover(master, qos_root, day, output, receipt):
    require(day == (datetime.now(timezone.utc).date() - timedelta(days=1)).isoformat(),
            "CURRENT_UTC_CUTOFF_ONLY")
    state_path = qos_root / "cycles" / "2026-09-30" / "SIGNAL_STATE.json"
    evidence = qos_root / "source_evidence" / "2026-09-30" / day
    prices_path = evidence / "PRICES.json"
    raw_path = evidence / "RAW_SOURCES.json.gz"
    state = json.loads(state_path.read_text())
    manifest = json.loads(prices_path.read_text())
    raw = raw_path.read_bytes()
    digest = manifest.pop("manifest_sha256")
    require(sha(packed(manifest)) == digest, "QOS_MANIFEST_HASH_MISMATCH")
    require(sha(raw) == manifest["raw_sha256"], "QOS_RAW_HASH_MISMATCH")
    gzip.decompress(raw)
    require(manifest["signal_state_sha256"] == state["state_sha256"],
            "QOS_SIGNAL_HASH_MISMATCH")
    require(manifest["cutoff"] == day and manifest["missing_candidates"] == [],
            "QOS_CUTOFF_OR_COVERAGE_MISMATCH")
    require(manifest["source_substitution"] is False
            and manifest["research_only"] is True
            and manifest["orders_generated"] == 0, "QOS_SAFETY_MISMATCH")
    quotes = {}
    for quote in manifest["quotes"]:
        symbol = quote["symbol"]
        require(quote["date"] == day and symbol in state["candidate_symbols"],
                "QOS_QUOTE_SCOPE_MISMATCH")
        require(quote["source"] == state["candidate_source_lock"][symbol],
                "QOS_LOCKED_SOURCE_MISMATCH")
        require(symbol not in quotes and float(quote["close_usd"]) > 0,
                "QOS_DUPLICATE_OR_INVALID_QUOTE")
        quotes[symbol] = quote
    selected = set(sum(state["qos_picks"].values(), []))
    require(selected <= quotes.keys(), "QOS_SELECTED_COVERAGE_MISSING")
    with master.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        fields = reader.fieldnames
        require(fields and {"date", "symbol", "close_usd"} <= set(fields),
                "MASTER_SCHEMA_INVALID")
        rows = list(reader)
    existing = {}
    for row in rows:
        if row["date"] == day and row["symbol"] in selected:
            symbol = row["symbol"]
            require(symbol not in existing, "MASTER_DUPLICATE_SELECTED_QUOTE")
            require(float(row["close_usd"]) == float(quotes[symbol]["close_usd"]),
                    "MASTER_QOS_PRICE_CONFLICT")
            if "source" in fields:
                require(row["source"] == quotes[symbol]["source"],
                        "MASTER_QOS_SOURCE_CONFLICT")
            existing[symbol] = row
    added = sorted(selected - existing.keys())
    for symbol in added:
        quote = quotes[symbol]
        row = dict.fromkeys(fields, "")
        row.update(date=day, symbol=symbol, close_usd=str(quote["close_usd"]))
        if "source" in fields:
            row["source"] = quote["source"]
        rows.append(row)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    result = {"schema": "gate_btc.same_source_recovery.v1", "cutoff": day,
              "added_symbols": added, "source_substitution": False,
              "qos_manifest_sha256": digest, "qos_raw_sha256": manifest["raw_sha256"],
              "qos_signal_state_sha256": state["state_sha256"],
              "original_master_sha256": sha(master.read_bytes()),
              "recovered_master_sha256": sha(output.read_bytes()),
              "scientific_credit_added": 0}
    receipt.parent.mkdir(parents=True, exist_ok=True)
    receipt.write_bytes(packed(result))
    return result


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--master", type=Path, required=True)
    p.add_argument("--qos-root", type=Path, required=True)
    p.add_argument("--day", required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--receipt", type=Path, required=True)
    a = p.parse_args()
    print(json.dumps(recover(a.master, a.qos_root, a.day, a.output, a.receipt),
                     sort_keys=True))
if __name__ == "__main__":
    main()
