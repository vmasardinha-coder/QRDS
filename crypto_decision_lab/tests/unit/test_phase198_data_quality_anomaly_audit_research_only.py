from __future__ import annotations

import json
from pathlib import Path

from crypto_decision_lab.scripts.phase198_data_quality_anomaly_audit_research_only import build_phase198


def write_inputs(registry: Path, temporal: Path, source: Path, source_id: str) -> None:
    registry.write_text(json.dumps({
        "phase": 196,
        "registry_ready": True,
        "sources": [{
            "source_id": source_id,
            "relative_or_absolute_path": str(source),
            "source_role": "RESEARCH_INPUT",
            "format_class": "TABULAR_TEXT",
            "content_sha256": "a" * 64,
        }],
    }), encoding="utf-8")
    temporal.write_text(json.dumps({
        "phase": 197,
        "temporal_policy_ready": True,
        "source_audits": [{
            "source_id": source_id,
            "timestamp_field": "timestamp",
            "invalid_timestamp_count": 0,
            "non_monotonic_timestamp_count": 0,
            "duplicate_adjacent_timestamp_count": 1,
            "timezone_status": "UTC_OR_OFFSET_EXPLICIT",
        }],
    }), encoding="utf-8")


def test_phase198_detects_anomalies(tmp_path: Path) -> None:
    source = tmp_path / "prices.csv"
    source.write_text(
        "timestamp,symbol,open,high,low,close,volume\n"
        "2026-01-01T00:00:00Z,BTC,100,105,95,102,10\n"
        "2026-01-01T01:00:00Z,,102,101,99,100,-1\n"
        "2026-01-01T05:00:00Z,BTC,100,110,90,105,12\n"
        "2026-01-01T05:00:00Z,BTC,100,110,90,105,12\n",
        encoding="utf-8",
    )
    registry = tmp_path / "registry.json"
    temporal = tmp_path / "temporal.json"
    write_inputs(registry, temporal, source, "src_prices")

    payload = build_phase198(registry, temporal, tmp_path / "out", tmp_path / "report.md")
    audit = payload["source_audits"][0]

    assert payload["audit_status"] == "DATA_ANOMALY_AUDIT_READY_RESEARCH_ONLY"
    assert audit["duplicate_record_count"] == 1
    assert audit["missing_symbol_count"] == 1
    assert audit["negative_volume_count"] == 1
    assert audit["ohlc_invariant_violation_count"] == 1
    assert audit["gap_analysis"]["large_gap_count"] == 1
    assert "DUPLICATE_RECORDS_PRESENT" in audit["anomaly_flags"]
    assert payload["anomaly_free_validated"] is False
    assert payload["data_trust_validated"] is False


def test_phase198_clean_data_does_not_promote(tmp_path: Path) -> None:
    source = tmp_path / "clean.csv"
    source.write_text(
        "timestamp,symbol,open,high,low,close,volume\n"
        "2026-01-01T00:00:00Z,BTC,100,105,95,102,10\n"
        "2026-01-01T01:00:00Z,BTC,102,106,100,104,11\n",
        encoding="utf-8",
    )
    registry = tmp_path / "registry.json"
    temporal = tmp_path / "temporal.json"
    write_inputs(registry, temporal, source, "src_clean")
    temporal_payload = json.loads(temporal.read_text(encoding="utf-8"))
    temporal_payload["source_audits"][0]["duplicate_adjacent_timestamp_count"] = 0
    temporal.write_text(json.dumps(temporal_payload), encoding="utf-8")

    payload = build_phase198(registry, temporal, tmp_path / "out")
    assert payload["source_audits"][0]["anomaly_flags"] == []
    assert payload["summary"]["flagged_source_count"] == 0
    assert payload["anomaly_free_validated"] is False
    assert payload["valid_for_decision"] is False


def test_phase198_locks_remain_closed(tmp_path: Path) -> None:
    registry = tmp_path / "registry.json"
    temporal = tmp_path / "temporal.json"
    registry.write_text(json.dumps({"phase": 196, "registry_ready": True, "sources": []}), encoding="utf-8")
    temporal.write_text(json.dumps({"phase": 197, "temporal_policy_ready": True, "source_audits": []}), encoding="utf-8")

    payload = build_phase198(registry, temporal, tmp_path / "out")
    locks = payload["locks"]
    assert locks["operational_status"] == "BLOCKED_RESEARCH_ONLY"
    assert locks["promotion_allowed"] is False
    assert locks["shadow_decision_allowed"] is False
    assert locks["decision_layer_allowed"] is False
    assert locks["canonical_data_writes"] == 0
    assert locks["real_orders_generated"] is False
