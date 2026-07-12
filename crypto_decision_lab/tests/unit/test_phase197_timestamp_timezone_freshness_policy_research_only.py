from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from crypto_decision_lab.scripts.phase197_timestamp_timezone_freshness_policy_research_only import build_phase197


def write_registry(path: Path, sources: list[dict[str, object]]) -> None:
    path.write_text(
        json.dumps({
            "phase": 196,
            "registry_ready": True,
            "data_trust_validated": False,
            "summary": {"source_count": len(sources)},
            "sources": sources,
        }),
        encoding="utf-8",
    )


def record(path: Path, source_id: str, role: str = "RESEARCH_INPUT") -> dict[str, object]:
    return {
        "source_id": source_id,
        "relative_or_absolute_path": str(path),
        "source_role": role,
        "format_class": "TABULAR_TEXT",
        "content_sha256": "a" * 64,
    }


def test_phase197_explicit_utc_monotonic(tmp_path: Path) -> None:
    source = tmp_path / "btc_prices.csv"
    source.write_text(
        "timestamp,close\n"
        "2026-07-10T00:00:00Z,100\n"
        "2026-07-10T01:00:00Z,101\n"
        "2026-07-10T02:00:00Z,102\n",
        encoding="utf-8",
    )
    registry = tmp_path / "registry.json"
    write_registry(registry, [record(source, "src_prices")])

    payload = build_phase197(
        registry_path=registry,
        output_dir=tmp_path / "artifact",
        documentation_path=tmp_path / "phase197.md",
        audit_time=datetime(2026, 7, 10, 3, tzinfo=timezone.utc),
    )

    audit = payload["source_audits"][0]
    assert payload["policy_status"] == "TEMPORAL_DATA_POLICY_READY_RESEARCH_ONLY"
    assert audit["inspection_status"] == "INSPECTED"
    assert audit["timezone_status"] == "UTC_OR_OFFSET_EXPLICIT"
    assert audit["invalid_timestamp_count"] == 0
    assert audit["non_monotonic_timestamp_count"] == 0
    assert audit["median_interval_seconds"] == 3600.0


def test_phase197_flags_naive_invalid_non_monotonic(tmp_path: Path) -> None:
    source = tmp_path / "candles.csv"
    source.write_text(
        "timestamp,close\n"
        "2026-07-10 02:00:00,102\n"
        "not-a-time,101\n"
        "2026-07-10 01:00:00,100\n",
        encoding="utf-8",
    )
    registry = tmp_path / "registry.json"
    write_registry(registry, [record(source, "src_candles")])

    payload = build_phase197(
        registry_path=registry,
        output_dir=tmp_path / "artifact",
        audit_time=datetime(2026, 7, 10, 3, tzinfo=timezone.utc),
    )

    audit = payload["source_audits"][0]
    assert audit["timezone_status"] == "NEEDS_EXPLICIT_TIMEZONE"
    assert audit["invalid_timestamp_count"] == 1
    assert audit["non_monotonic_timestamp_count"] == 1
    assert payload["data_trust_validated"] is False
    assert payload["freshness_validated"] is False
    assert payload["valid_for_decision"] is False


def test_phase197_fixture_freshness_is_not_operational(tmp_path: Path) -> None:
    source = tmp_path / "historical_prices.csv"
    source.write_text(
        "timestamp,close\n2020-01-01T00:00:00Z,1\n",
        encoding="utf-8",
    )
    registry = tmp_path / "registry.json"
    write_registry(registry, [record(source, "src_fixture", "TEST_FIXTURE")])

    payload = build_phase197(
        registry_path=registry,
        output_dir=tmp_path / "artifact",
        audit_time=datetime(2026, 7, 10, tzinfo=timezone.utc),
    )

    assert payload["source_audits"][0]["freshness_status"] == (
        "FIXTURE_NOT_OPERATIONALLY_ENFORCED"
    )
    locks = payload["locks"]
    assert locks["operational_status"] == "BLOCKED_RESEARCH_ONLY"
    assert locks["promotion_allowed"] is False
    assert locks["decision_layer_allowed"] is False
    assert locks["canonical_data_writes"] == 0
