#!/usr/bin/env python3
"""Publish source proof only; the accessible economic journal is never an input/output."""
from __future__ import annotations
import argparse, hashlib, json
from datetime import datetime, timezone
from pathlib import Path
try:
    from .crypto_forward_source_admission import evaluate
except ImportError:
    from crypto_forward_source_admission import evaluate

MAX_DELIVERY_AGE_SECONDS = 600
CONTRACT = Path(__file__).with_name("CRYPTO_FORWARD_PUBLIC_SOURCE_CONTRACT.v1.json")

def contract_hash():
    value = json.loads(CONTRACT.read_text(encoding="utf-8"))
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2)+"\n", encoding="utf-8")

def append_packet(root, packet, now=None):
    now = now or datetime.now(timezone.utc)
    if packet.get("capture_profile") != "full-source-contract" or packet.get("frozen_capture_delay_seconds") != 120:
        raise ValueError("full source capture profile required")
    actual = hashlib.sha256(json.dumps({k:v for k,v in packet.items() if k != "packet_sha256"}, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    if actual != packet.get("packet_sha256"):
        raise ValueError("packet hash mismatch")
    captured = datetime.fromisoformat(packet["captured_at_utc"].replace("Z", "+00:00"))
    if captured.tzinfo is None or not 0 <= (now-captured).total_seconds() <= MAX_DELIVERY_AGE_SECONDS:
        raise ValueError("only fresh live captures may be appended; no qualification backfill")
    journal = root/"full_local"/"audits"
    journal.mkdir(parents=True, exist_ok=True)
    path = journal/(captured.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")+"-"+actual+".json")
    if path.exists():
        if json.loads(path.read_text(encoding="utf-8")) != packet:
            raise ValueError("immutable audit collision")
    else:
        # Exclusive creation prevents an existing audit ever being overwritten.
        with path.open("x", encoding="utf-8") as handle:
            handle.write(json.dumps(packet, indent=2)+"\n")
    # This directory is the explicit authority switch. Hosted partial captures
    # continue to their original audit journal and cannot override this route.
    return path

def refresh(root, now=None):
    now = now or datetime.now(timezone.utc)
    local = root/"full_local"/"audits"
    selected = local if local.exists() else root/"audits"
    try:
        result = evaluate(selected)
    except (ValueError, TypeError, AttributeError, KeyError):
        result = evaluate(root/"__no_packets__")
        result["latest_packet_qualification"] = "UNREADABLE_PACKET"
    if local.exists():
        latest = None
        try:
            packets = [json.loads(p.read_text(encoding="utf-8")) for p in local.glob("*.json")]
            latest = max(packets, key=lambda p: datetime.fromisoformat(p["captured_at_utc"].replace("Z", "+00:00")))
            captured = datetime.fromisoformat(latest["captured_at_utc"].replace("Z", "+00:00"))
            age = (now-captured).total_seconds()
            fresh = 0 <= age <= MAX_DELIVERY_AGE_SECONDS
        except (ValueError, KeyError, TypeError, AttributeError):
            age = None
            fresh = False
        qualified = result["source_admitted_forward_only"]
        result.update({"source_route":"WINDOWS_LOCAL_FULL_CONTRACT", "audit_directory":"full_local/audits",
                       "contract_semantic_sha256":contract_hash(), "source_qualification_admitted":qualified,
                       "delivery_fresh":fresh, "delivery_max_age_seconds":MAX_DELIVERY_AGE_SECONDS,
                       "delivery_age_seconds":age, "evaluated_at_utc":now.isoformat(),
                       "latest_packet_sha256":latest.get("packet_sha256") if latest else None,
                       "latest_capture_at_utc":latest.get("captured_at_utc") if latest else None,
                       "source_admitted_forward_only":qualified and fresh,
                       "family_state":"READY_FORWARD" if qualified and fresh else "WAITING_SOURCE",
                       "economic_rows_appended":0, "scientific_credit":0, "engine_feed":False})
        if latest is not None:
            write_json(root/"FULL_LOCAL_LATEST.json", latest)
    else:
        result["source_route"] = "GITHUB_HOSTED_PUBLIC"
    write_json(root/"SOURCE_ADMISSION.json", result)
    return result

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--root", required=True)
    parser.add_argument("--packet")
    args=parser.parse_args()
    root=Path(args.root)
    if args.packet:
        append_packet(root, json.loads(Path(args.packet).read_text(encoding="utf-8")))
    print(json.dumps(refresh(root), sort_keys=True))

if __name__ == "__main__":
    main()
