from __future__ import annotations

import hashlib
from pathlib import Path

from crypto_decision_lab.scripts.phase196_data_source_registry_lineage_contract_research_only import (
    build_phase196,
)


def test_phase196_builds_hashed_read_only_registry(
    tmp_path: Path,
) -> None:
    source_root = tmp_path / "source"
    source_root.mkdir()

    csv_path = source_root / "prices.csv"
    csv_path.write_text(
        "timestamp,close\n2026-01-01T00:00:00Z,100\n",
        encoding="utf-8",
    )

    json_path = source_root / "metadata.json"
    json_path.write_text(
        '{"symbol":"BTCUSDT"}\n',
        encoding="utf-8",
    )

    documentation_path = tmp_path / "phase196.md"
    payload = build_phase196(
        scan_roots=[source_root],
        output_dir=tmp_path / "artifact",
        documentation_path=documentation_path,
    )

    assert payload["phase"] == 196
    assert payload["phase_status"] == "PASS_RESEARCH_ONLY"
    assert payload["registry_status"] == (
        "DATA_SOURCE_REGISTRY_READY_RESEARCH_ONLY"
    )

    assert payload["summary"]["source_count"] == 2
    assert payload["summary"]["hashes_verified"] == 2
    assert payload["summary"]["empty_file_count"] == 0

    records = {
        Path(item["relative_or_absolute_path"]).name: item
        for item in payload["sources"]
    }

    assert records["prices.csv"]["content_sha256"] == hashlib.sha256(
        csv_path.read_bytes()
    ).hexdigest()
    assert records["prices.csv"]["format_class"] == "TABULAR_TEXT"
    assert records["metadata.json"]["format_class"] == (
        "STRUCTURED_TEXT"
    )

    for item in payload["sources"]:
        assert item["read_only_evidence"] is True
        assert item["canonical_write_allowed"] is False
        assert item["authenticated_connection_used"] is False

    assert documentation_path.is_file()


def test_phase196_detects_duplicate_content_without_approval(
    tmp_path: Path,
) -> None:
    source_root = tmp_path / "fixtures"
    source_root.mkdir()

    (source_root / "a.csv").write_text(
        "timestamp,close\n1,2\n",
        encoding="utf-8",
    )
    (source_root / "b.csv").write_text(
        "timestamp,close\n1,2\n",
        encoding="utf-8",
    )

    payload = build_phase196(
        scan_roots=[source_root],
        output_dir=tmp_path / "artifact",
    )

    assert payload["summary"]["source_count"] == 2
    assert (
        payload["summary"]["duplicate_content_group_count"]
        == 1
    )
    assert payload["data_trust_validated"] is False
    assert payload["valid_for_decision"] is False
    assert payload["approval_effect"] == "NONE_RESEARCH_ONLY"


def test_phase196_accepts_missing_roots_and_keeps_locks_closed(
    tmp_path: Path,
) -> None:
    missing_root = tmp_path / "does_not_exist"

    payload = build_phase196(
        scan_roots=[missing_root],
        output_dir=tmp_path / "artifact",
    )

    assert payload["summary"]["scan_root_count"] == 1
    assert payload["summary"]["existing_root_count"] == 0
    assert payload["summary"]["missing_root_count"] == 1
    assert payload["summary"]["source_count"] == 0
    assert payload["registry_ready"] is True
    assert payload["data_trust_validated"] is False

    locks = payload["locks"]
    assert locks["operational_status"] == "BLOCKED_RESEARCH_ONLY"
    assert locks["promotion_allowed"] is False
    assert locks["shadow_decision_allowed"] is False
    assert locks["decision_layer_allowed"] is False
    assert locks["canonical_data_writes"] == 0
    assert locks["real_orders_generated"] is False
    assert locks["real_capital_used"] is False
