from crypto_decision_lab.runs.bundle import build_research_run_bundle
from crypto_decision_lab.runs.registry import (
    build_research_run_registry,
    build_research_run_registry_entry,
    build_research_run_registry_report,
    load_research_run_registry,
    write_research_run_registry,
)


def _safe_manifest():
    return {
        "schema": "qrds.research_run_manifest.v1",
        "run_id": "integration-run",
        "generated_at": "2026-01-01T00:00:00+00:00",
        "symbol": "BTC-USDT",
        "interval": "1h",
        "source": "unit_test",
        "pipeline_commit": "test-commit",
        "dql_score": 90.0,
        "regime": "BULL",
        "dataset_row_count": 1,
        "export_artifact_count": 1,
        "research_allowed": True,
        "operational_decision_allowed": False,
        "app_mode": "INTERACTIVE_RESEARCH_ONLY",
        "api_key_required": False,
        "api_key_present": False,
        "account_connection_required": False,
        "orders_generated": False,
        "real_capital_used": False,
    }


def test_bundle_to_registry_happy_path(tmp_path):
    artifact = tmp_path / "dataset.jsonl"
    artifact.write_text('{"row": 1}\n', encoding="utf-8")

    manifest = _safe_manifest()
    bundle = build_research_run_bundle(
        manifest=manifest,
        artifact_paths=[artifact],
        output_dir=tmp_path / "bundles",
        bundle_name="integration-bundle",
    )

    entry = build_research_run_registry_entry(
        bundle_metadata=bundle,
        manifest=manifest,
        tags=["integration"],
    )

    registry = build_research_run_registry([entry])
    report = build_research_run_registry_report(registry)

    output_path = tmp_path / "registry" / "registry.json"
    written = write_research_run_registry(registry, output_path)
    loaded = load_research_run_registry(written)

    assert registry["entry_count"] == 1
    assert loaded["entry_count"] == 1
    assert loaded["entries"][0]["run_id"] == "integration-run"
    assert loaded["entries"][0]["symbol"] == "BTC-USDT"
    assert report["registry_quality_passed"] is True
    assert report["operational_decision_allowed"] is False
