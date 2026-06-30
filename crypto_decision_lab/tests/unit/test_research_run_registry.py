import pytest

from crypto_decision_lab.runs.registry import (
    RESEARCH_RUN_REGISTRY_ENTRY_SCHEMA_VERSION,
    RESEARCH_RUN_REGISTRY_SCHEMA_VERSION,
    ResearchRunRegistryError,
    build_research_run_registry,
    build_research_run_registry_entry,
    build_research_run_registry_report,
    load_research_run_registry,
    validate_registry_entries,
    write_research_run_registry,
)


def _bundle_metadata():
    return {
        "schema": "qrds.research_run_bundle.v1",
        "bundle_name": "bundle-unit",
        "bundle_dir": "/tmp/bundle-unit",
        "artifact_count": 1,
        "total_artifact_bytes": 123,
        "manifest_sha256": "a" * 64,
        "artifact_index_sha256": "b" * 64,
        "bundle_report_sha256": "c" * 64,
        "research_allowed": True,
        "operational_decision_allowed": False,
        "app_mode": "INTERACTIVE_RESEARCH_ONLY",
        "api_key_required": False,
        "api_key_present": False,
        "account_connection_required": False,
        "orders_generated": False,
        "real_capital_used": False,
    }


def _manifest():
    return {
        "schema": "qrds.research_run_manifest.v1",
        "run_id": "run-unit",
        "symbol": "BTC-USDT",
        "interval": "1h",
        "source": "unit_test",
        "regime": "BULL",
        "dql_score": 91.0,
        "dataset_row_count": 10,
        "research_allowed": True,
        "operational_decision_allowed": False,
        "app_mode": "INTERACTIVE_RESEARCH_ONLY",
        "api_key_required": False,
        "api_key_present": False,
        "account_connection_required": False,
        "orders_generated": False,
        "real_capital_used": False,
    }


def test_build_research_run_registry_entry():
    entry = build_research_run_registry_entry(
        bundle_metadata=_bundle_metadata(),
        manifest=_manifest(),
        tags=["unit", "offline"],
        notes="unit test",
    )

    assert entry["schema"] == RESEARCH_RUN_REGISTRY_ENTRY_SCHEMA_VERSION
    assert len(entry["entry_id"]) == 64
    assert entry["run_id"] == "run-unit"
    assert entry["symbol"] == "BTC-USDT"
    assert entry["regime"] == "BULL"
    assert entry["operational_decision_allowed"] is False


def test_build_research_run_registry_entry_blocks_operational_bundle():
    bundle = _bundle_metadata()
    bundle["operational_decision_allowed"] = True

    with pytest.raises(ResearchRunRegistryError):
        build_research_run_registry_entry(bundle_metadata=bundle, manifest=_manifest())


def test_build_research_run_registry():
    entry = build_research_run_registry_entry(
        bundle_metadata=_bundle_metadata(),
        manifest=_manifest(),
    )
    registry = build_research_run_registry([entry])

    assert registry["schema"] == RESEARCH_RUN_REGISTRY_SCHEMA_VERSION
    assert registry["entry_count"] == 1
    assert registry["registry_quality_passed"] is True
    assert registry["operational_decision_allowed"] is False
    assert len(registry["registry_hash"]) == 64


def test_validate_registry_entries_flags_duplicate_ids():
    entry = build_research_run_registry_entry(
        bundle_metadata=_bundle_metadata(),
        manifest=_manifest(),
    )
    issues = validate_registry_entries([entry, dict(entry)])

    assert any(issue["code"] == "DUPLICATE_REGISTRY_ENTRY_ID" for issue in issues)


def test_write_and_load_registry(tmp_path):
    entry = build_research_run_registry_entry(
        bundle_metadata=_bundle_metadata(),
        manifest=_manifest(),
    )
    registry = build_research_run_registry([entry])
    output_path = tmp_path / "registry.json"

    written = write_research_run_registry(registry, output_path)
    loaded = load_research_run_registry(written)

    assert loaded["schema"] == RESEARCH_RUN_REGISTRY_SCHEMA_VERSION
    assert loaded["entry_count"] == 1
    assert loaded["operational_decision_allowed"] is False


def test_build_research_run_registry_report():
    entry = build_research_run_registry_entry(
        bundle_metadata=_bundle_metadata(),
        manifest=_manifest(),
    )
    registry = build_research_run_registry([entry])
    report = build_research_run_registry_report(registry)

    assert report["registry_quality_passed"] is True
    assert report["entry_count"] == 1
    assert report["operational_decision_allowed"] is False
    assert report["api_key_required"] is False
    assert report["orders_generated"] is False
    assert report["real_capital_used"] is False
