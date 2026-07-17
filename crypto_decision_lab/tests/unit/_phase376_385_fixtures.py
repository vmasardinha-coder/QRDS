from __future__ import annotations

import csv
import gzip
import hashlib
import json
from pathlib import Path
from typing import Any

LOCKS = {
    "operational_status": "BLOCKED_RESEARCH_ONLY",
    "action_status": "NO_ACTION_RESEARCH_ONLY",
    "decision_layer_allowed": False,
    "canonical_data_writes": 0,
    "account_connection_allowed": False,
    "private_api_allowed": False,
    "orders_allowed": False,
    "capital_allowed": False,
    "position_size": 0,
    "capital_used": 0,
    "real_orders_created": 0,
}

SCHEMA = (
    "open_time_ms",
    "open_time_utc",
    "provider_count",
    "providers",
    "consensus_close",
    "spread_bps",
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def base(phase: int, **extra: Any) -> dict[str, Any]:
    value = {
        "project": "QRDS/QOS/GATE BTC",
        "phase": phase,
        "status": "PASS_RESEARCH_ONLY",
        "locks": dict(LOCKS),
        "strategy_approved": False,
        "forward_shadow_eligible": False,
        "forward_shadow_started": False,
        "paper_trading_started": False,
        "historical_result_authorizes_execution": False,
        "artifact_fingerprint": f"phase-{phase}",
    }
    value.update(extra)
    return value


def write_gz(path: Path, rows: list[dict[str, Any]], fieldnames: tuple[str, ...] = SCHEMA) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    return path


def candidate_rows() -> list[dict[str, Any]]:
    return [
        {"open_time_ms": "0", "open_time_utc": "1970-01-01T00:00:00Z", "provider_count": "3", "providers": "BINANCE|BYBIT|OKX", "consensus_close": "100.0", "spread_bps": "2.0"},
        {"open_time_ms": "3600000", "open_time_utc": "1970-01-01T01:00:00Z", "provider_count": "4", "providers": "BINANCE|BYBIT|COINBASE|OKX", "consensus_close": "101.0", "spread_bps": "1.0"},
    ]


def setup_previous_chain(root: Path) -> dict[str, Path]:
    artifacts = root / "artifacts"
    raw_lineage = []
    for index, provider in enumerate(("BINANCE", "BYBIT", "COINBASE", "OKX"), start=1):
        raw = root / "data" / f"{provider.lower()}_candles.csv.gz"
        write_gz(raw, candidate_rows())
        raw_lineage.append({"provider": provider, "path": raw.relative_to(root).as_posix(), "sha256": sha256(raw)})
    candidate = artifacts / "phase367_one_real_data_remediation_evaluation_research_only" / "timestamp_consensus_remediated_dataset.csv.gz"
    write_gz(candidate, candidate_rows())
    p367 = base(
        367,
        gate="PHASE367_ONE_REAL_DATA_REMEDIATION_EVALUATION_READY_RESEARCH_ONLY",
        evaluation_executed=True,
        evaluation_id="eval-1",
        remediated_dataset_path=candidate.relative_to(root).as_posix(),
        remediated_dataset_sha256=sha256(candidate),
        input_lineage=raw_lineage,
        provider_dataset_count=4,
        real_historical_rows_used=8,
        metrics={"VALID_CONSENSUS_HOURS": 2},
    )
    p369 = base(369, gate="PHASE369_NO_CLOSED_FAMILY_PERFORMANCE_METRIC_PROOF_READY_RESEARCH_ONLY", proof_pass=True)
    p371 = base(371, gate="PHASE371_REMEDIATION_LINEAGE_AND_HASH_AUDIT_READY_RESEARCH_ONLY", lineage_audit_pass=True)
    p375 = base(
        375,
        gate="PHASE375_DATA_QUALITY_REMEDIATION_INTEGRATED_CHECKPOINT_READY_RESEARCH_ONLY",
        evaluation_executed=True,
        evaluation_id="eval-1",
        data_quality_contract_pass=True,
        governance_pass=True,
        no_closed_family_metric_proof_pass=True,
        candidate_research_dataset_adopted=False,
        active_hypotheses=0,
        active_experiment_budget=0,
        closed_families_reopened=False,
        real_historical_rows_used=8,
        provider_dataset_count=4,
    )
    paths = {
        "p367": write_json(artifacts / "p367.json", p367),
        "p369": write_json(artifacts / "p369.json", p369),
        "p371": write_json(artifacts / "p371.json", p371),
        "p375": write_json(artifacts / "p375.json", p375),
        "candidate": candidate,
    }
    return paths


def junit(path: Path, tests: int = 20) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f'<testsuite name="targeted" tests="{tests}" failures="0" errors="0" skipped="0"></testsuite>\n', encoding="utf-8")
    return path


def full_suite_override() -> dict[str, Any]:
    return {
        "passed": True,
        "test_file_count": 614,
        "manifest_stable": True,
        "totals": {"tests": 1531, "failures": 0, "errors": 0, "skipped": 0},
        "minimum_test_file_count": 614,
        "minimum_tests": 1521,
    }
