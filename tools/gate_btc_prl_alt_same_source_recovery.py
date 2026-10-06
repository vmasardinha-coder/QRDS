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
    cycles=sorted(p for p in (qos_root/"cycles").glob("*/SIGNAL_STATE.json")
                  if p.parent.name<=day and not (p.parent/"BLOCKED.json").exists())
    require(cycles,"NO_ACTIVE_QOS_SIGNAL_FOR_CUTOFF")
    state_path=cycles[-1]
    signal_date=state_path.parent.name
    evidence = qos_root / "source_evidence" / signal_date / day
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
    require(manifest["cutoff"] == day, "QOS_CUTOFF_MISMATCH")
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
    epoch_converted=[]
    for row in rows:
        if row["date"] == day and row["symbol"] in selected:
            symbol = row["symbol"]
            require(symbol not in existing, "MASTER_DUPLICATE_SELECTED_QUOTE")
            quote=quotes[symbol]
            old=float(row["close_usd"])
            new=float(quote["close_usd"])
            same=old==new
            prospective=(state.get("source_epoch",{}).get("source_lock")
                         == "binance_spot_daily_archive"
                         and symbol in state["source_epoch"].get("remapped_symbols",[])
                         and row.get("source")=="cdd"
                         and quote["source"]=="binance_spot_daily_archive")
            relative=abs(old-new)/max(abs(old),abs(new),1e-15)
            require(same or (prospective and relative<=1e-8),
                    "MASTER_QOS_PRICE_CONFLICT")
            if "source" in fields and row["source"]!=quote["source"]:
                require(prospective,"MASTER_QOS_SOURCE_CONFLICT")
                row["source"]=quote["source"]
                row["close_usd"]=str(new)
                epoch_converted.append(symbol)
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
              "added_symbols": added, "qualified_new_epoch_transport": epoch_converted,
              "qos_signal_date": signal_date, "source_substitution": False,
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
