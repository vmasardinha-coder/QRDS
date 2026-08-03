#!/usr/bin/env python3
"""Build and validate immutable Shadow report delivery metadata.

This module never calculates strategy results and never places orders. It only
binds an admitted daily research handoff to exactly three PDF deliverables and
creates a cryptographic receipt after the PDFs exist.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPORT_ROLES = (
    ("MASTER_ANALYTIC", "Shadow_Watch_Executive_{date}_Reconciled_FullSet_v13_Master.pdf"),
    ("COMPARATIVOS_COMPLETOS", "Shadow_Watch_Executive_{date}_Comparativos_Completos_Janela_Alinhada.pdf"),
    ("PROFIT_PRESERVATION", "Shadow_Watch_Profit_Preservation_{date}_Shadow_Update.pdf"),
)
PASS_STATUSES = {"PASS", "PASS_WITH_DATA_WARNINGS"}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".partial")
    temporary.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False, default=str) + "\n",
        encoding="utf-8",
        newline="",
    )
    os.replace(temporary, path)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def safe_token(value: str, fallback: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_.-]+", "-", str(value or "").strip()).strip("-")
    return cleaned or fallback


def load_json(path: Path) -> dict[str, Any]:
    require(path.is_file(), f"missing JSON: {path}")
    return json.loads(path.read_text(encoding="utf-8-sig"))


def validate_handoff(payload: dict[str, Any]) -> None:
    require(payload.get("status") in PASS_STATUSES, f"handoff status={payload.get('status')}")
    require(payload.get("stage_reached") == "DAILY_V2A_DELTA_GATEWAY_COLLECTION_VALIDATED", "daily validation stage missing")
    require(payload.get("research_only") is True, "research_only lock missing")
    require(payload.get("orders_generated") == 0, "orders were generated")
    require(payload.get("real_capital_used") == 0, "real capital was used")
    require(payload.get("operational_status") == "NOT_APPROVED", "operational status changed")
    require(payload.get("retrospective_gateway_performance") == "PROHIBITED", "Gateway retrospective prohibition missing")
    require(payload.get("methodology_changes") == 0, "methodology changes detected")
    require(payload.get("report_delivery", {}).get("inputs_ready") is True, "report inputs are not ready")
    components = payload.get("components", {})
    for name in ("v2a", "delta", "gateway_upstream", "gateway_downstream"):
        require(components.get(name, {}).get("status") == "PASS", f"component {name} is not PASS")


def build_request(handoff_dir: Path, output_path: Path) -> dict[str, Any]:
    handoff_dir = handoff_dir.resolve()
    manifest_path = handoff_dir / "GATE_BTC_DAILY_RESEARCH_MANIFEST.json"
    report_path = handoff_dir / "GATE_BTC_DAILY_RESEARCH_REPORT.txt"
    evidence_path = handoff_dir / "GATE_BTC_DAILY_RESEARCH_EVIDENCE.zip"
    manifest = load_json(manifest_path)
    validate_handoff(manifest)
    require(report_path.is_file(), f"missing handoff report: {report_path}")
    require(evidence_path.is_file(), f"missing handoff evidence ZIP: {evidence_path}")

    now = datetime.now(timezone.utc)
    cutoff = safe_token(manifest.get("data_cutoff", ""), "unknown-cutoff")
    report_date = safe_token(os.environ.get("GATE_BTC_REPORT_DATE", now.date().isoformat()), "unknown-report-date")
    run_id = safe_token(os.environ.get("GITHUB_RUN_ID", "local"), "local")
    run_attempt = safe_token(os.environ.get("GITHUB_RUN_ATTEMPT", "1"), "1")
    head_sha = safe_token(os.environ.get("GITHUB_SHA", "local-unbound"), "local-unbound")
    repository = os.environ.get("GITHUB_REPOSITORY", "local/unbound")
    event_name = os.environ.get("GITHUB_EVENT_NAME", "local")
    workflow = os.environ.get("GITHUB_WORKFLOW", "GATE BTC Daily Research Collection")
    delivery_id = f"{report_date}--cutoff-{cutoff}--run-{run_id}--attempt-{run_attempt}"
    expected = [
        {"position": index, "role": role, "filename": pattern.format(date=report_date)}
        for index, (role, pattern) in enumerate(REPORT_ROLES, start=1)
    ]
    payload = {
        "schema": "gate-btc-shadow-delivery-request-v1",
        "created_utc": now.isoformat(),
        "status": "READY_FOR_RENDER",
        "delivery_id": delivery_id,
        "duplicate_key": f"{cutoff}:{head_sha}",
        "source": {
            "repository": repository,
            "workflow": workflow,
            "event_name": event_name,
            "run_id": run_id,
            "run_attempt": run_attempt,
            "head_sha": head_sha,
            "ref": os.environ.get("GITHUB_REF", "local"),
            "report_date": report_date,
            "data_cutoff": manifest.get("data_cutoff"),
            "handoff_status": manifest.get("status"),
        },
        "contract": {
            "expected_pdf_count": 3,
            "reports": expected,
            "exact_roles": [role for role, _ in REPORT_ROLES],
            "research_only": True,
            "orders_generated": 0,
            "real_capital_used": 0,
            "operational_status": "NOT_APPROVED",
            "stale_delivery_allowed": False,
            "duplicate_delivery_allowed": False,
        },
        "inputs": {
            "handoff_manifest": {"file": manifest_path.name, "bytes": manifest_path.stat().st_size, "sha256": sha256_file(manifest_path)},
            "handoff_report": {"file": report_path.name, "bytes": report_path.stat().st_size, "sha256": sha256_file(report_path)},
            "handoff_evidence": {"file": evidence_path.name, "bytes": evidence_path.stat().st_size, "sha256": sha256_file(evidence_path)},
        },
    }
    atomic_json(output_path, payload)
    return payload


def validate_pdf(path: Path) -> None:
    require(path.is_file(), f"missing PDF: {path.name}")
    require(path.stat().st_size >= 1024, f"PDF too small: {path.name}")
    with path.open("rb") as handle:
        start = handle.read(8)
        handle.seek(max(0, path.stat().st_size - 2048))
        tail = handle.read()
    require(start.startswith(b"%PDF-"), f"invalid PDF header: {path.name}")
    require(b"%%EOF" in tail, f"missing PDF EOF marker: {path.name}")


def build_receipt(request_path: Path, reports_dir: Path, output_path: Path) -> dict[str, Any]:
    request = load_json(request_path.resolve())
    require(request.get("schema") == "gate-btc-shadow-delivery-request-v1", "unsupported delivery request schema")
    require(request.get("status") == "READY_FOR_RENDER", "delivery request is not ready")
    contract = request.get("contract", {})
    require(contract.get("expected_pdf_count") == 3, "expected PDF count changed")
    expected = contract.get("reports", [])
    require(len(expected) == 3, "delivery request must contain exactly three reports")
    require([item.get("role") for item in expected] == [role for role, _ in REPORT_ROLES], "report roles/order changed")

    reports_dir = reports_dir.resolve()
    expected_names = [item["filename"] for item in expected]
    actual_names = sorted(path.name for path in reports_dir.glob("*.pdf"))
    require(sorted(expected_names) == actual_names, f"PDF set mismatch expected={sorted(expected_names)} actual={actual_names}")
    records = []
    for item in expected:
        path = reports_dir / item["filename"]
        validate_pdf(path)
        records.append({
            "position": item["position"],
            "role": item["role"],
            "filename": path.name,
            "bytes": path.stat().st_size,
            "sha256": sha256_file(path),
        })
    receipt = {
        "schema": "gate-btc-shadow-delivery-receipt-v1",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": "PASS",
        "delivery_id": request["delivery_id"],
        "duplicate_key": request["duplicate_key"],
        "request_sha256": sha256_file(request_path.resolve()),
        "source": request["source"],
        "reports": records,
        "exact_report_count": 3,
        "research_only": True,
        "orders_generated": 0,
        "real_capital_used": 0,
        "operational_status": "NOT_APPROVED",
    }
    atomic_json(output_path, receipt)
    return receipt


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    request_parser = sub.add_parser("request")
    request_parser.add_argument("--handoff-dir", type=Path, required=True)
    request_parser.add_argument("--output", type=Path, required=True)
    receipt_parser = sub.add_parser("receipt")
    receipt_parser.add_argument("--request", type=Path, required=True)
    receipt_parser.add_argument("--reports-dir", type=Path, required=True)
    receipt_parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "request":
            payload = build_request(args.handoff_dir, args.output)
        else:
            payload = build_receipt(args.request, args.reports_dir, args.output)
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0
    except Exception as exc:
        print(f"SHADOW_DELIVERY_STATUS=FAIL\nERROR={type(exc).__name__}: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
