from pathlib import Path

from crypto_decision_lab.runs.bundle import build_research_run_bundle, build_research_run_bundle_report


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


def test_manifest_to_bundle_happy_path(tmp_path):
    artifact = tmp_path / "dataset.jsonl"
    artifact.write_text('{"row": 1}\n', encoding="utf-8")

    manifest = _safe_manifest()

    bundle = build_research_run_bundle(
        manifest=manifest,
        artifact_paths=[artifact],
        output_dir=tmp_path / "bundles",
        bundle_name="integration-bundle",
    )

    report = build_research_run_bundle_report(bundle)

    assert Path(bundle["manifest_path"]).exists()
    assert Path(bundle["artifact_index_path"]).exists()
    assert Path(bundle["bundle_report_path"]).exists()
    assert bundle["artifact_count"] == 1
    assert bundle["operational_decision_allowed"] is False
    assert report["bundle_quality_passed"] is True
    assert report["operational_decision_allowed"] is False
