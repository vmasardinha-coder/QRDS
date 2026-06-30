import pytest

from crypto_decision_lab.runs.manifest import (
    RESEARCH_RUN_MANIFEST_SCHEMA_VERSION,
    ResearchRunManifestError,
    build_research_run_manifest,
    build_research_run_manifest_report,
    validate_research_run_manifest,
)


def _base_flags():
    return {
        "app_mode": "INTERACTIVE_RESEARCH_ONLY",
        "api_key_required": False,
        "api_key_present": False,
        "account_connection_required": False,
        "orders_generated": False,
        "real_capital_used": False,
        "operational_decision_allowed": False,
    }


def _dql_report():
    report = _base_flags()
    report.update({
        "schema": "qrds.dql_report.v1",
        "symbol": "BTC-USDT",
        "interval": "1h",
        "source": "unit_test",
        "dql_score": 95.0,
        "issue_summary": {"error_count": 0},
    })
    return report


def _regime_report():
    report = _base_flags()
    report.update({
        "schema": "qrds.regime_report.v1",
        "symbol": "BTC-USDT",
        "interval": "1h",
        "source": "unit_test",
        "regime": "BULL",
        "feature_row_count": 10,
    })
    return report


def _dataset_report():
    report = _base_flags()
    report.update({
        "schema": "qrds.integrated_research_dataset.v1",
        "symbol": "BTC-USDT",
        "interval": "1h",
        "source": "unit_test",
        "row_count": 10,
        "dataset_quality_passed": True,
        "issue_summary": {"error_count": 0},
    })
    return report


def _export_report():
    report = _base_flags()
    report.update({
        "schema": "qrds.research_dataset_export.v1",
        "symbol": "BTC-USDT",
        "interval": "1h",
        "source": "unit_test",
        "row_count": 10,
        "export_format": "jsonl",
        "output_path": "exports/research.jsonl",
        "export_quality_passed": True,
    })
    return report


def test_build_research_run_manifest_happy_path():
    manifest = build_research_run_manifest(
        symbol="BTC-USDT",
        interval="1h",
        source="unit_test",
        dql_report=_dql_report(),
        regime_report=_regime_report(),
        dataset_report=_dataset_report(),
        export_report=_export_report(),
        pipeline_commit="abc123",
        artifacts=[{"kind": "jsonl", "path": "exports/research.jsonl"}],
    )

    assert manifest["schema"] == RESEARCH_RUN_MANIFEST_SCHEMA_VERSION
    assert manifest["pipeline_commit"] == "abc123"
    assert manifest["upstream_reports"]["dql"]["error_count"] == 0
    assert manifest["upstream_reports"]["integrated_dataset"]["dataset_quality_passed"] is True
    assert manifest["operational_decision_allowed"] is False
    assert manifest["api_key_required"] is False
    assert manifest["orders_generated"] is False
    assert manifest["real_capital_used"] is False


def test_manifest_blocks_bad_dql_report():
    dql = _dql_report()
    dql["issue_summary"]["error_count"] = 1

    with pytest.raises(ResearchRunManifestError):
        build_research_run_manifest(
            symbol="BTC-USDT",
            interval="1h",
            source="unit_test",
            dql_report=dql,
            regime_report=_regime_report(),
            dataset_report=_dataset_report(),
            pipeline_commit="abc123",
        )


def test_manifest_blocks_failed_dataset_report():
    dataset = _dataset_report()
    dataset["dataset_quality_passed"] = False

    with pytest.raises(ResearchRunManifestError):
        build_research_run_manifest(
            symbol="BTC-USDT",
            interval="1h",
            source="unit_test",
            dql_report=_dql_report(),
            regime_report=_regime_report(),
            dataset_report=dataset,
            pipeline_commit="abc123",
        )


def test_manifest_blocks_operational_export_report():
    export = _export_report()
    export["operational_decision_allowed"] = True

    with pytest.raises(ResearchRunManifestError):
        build_research_run_manifest(
            symbol="BTC-USDT",
            interval="1h",
            source="unit_test",
            dql_report=_dql_report(),
            regime_report=_regime_report(),
            dataset_report=_dataset_report(),
            export_report=export,
            pipeline_commit="abc123",
        )


def test_validate_manifest_flags_operational_true():
    manifest = build_research_run_manifest(
        symbol="BTC-USDT",
        interval="1h",
        source="unit_test",
        dql_report=_dql_report(),
        regime_report=_regime_report(),
        dataset_report=_dataset_report(),
        pipeline_commit="abc123",
    )
    manifest["operational_decision_allowed"] = True

    issues = validate_research_run_manifest(manifest)
    assert any(issue["code"] == "UNSAFE_MANIFEST_FLAG" for issue in issues)


def test_manifest_report_schema_and_flags():
    manifest = build_research_run_manifest(
        symbol="BTC-USDT",
        interval="1h",
        source="unit_test",
        dql_report=_dql_report(),
        regime_report=_regime_report(),
        dataset_report=_dataset_report(),
        pipeline_commit="abc123",
    )

    report = build_research_run_manifest_report(manifest)
    assert report["schema"] == "qrds.research_run_manifest_report.v1"
    assert report["manifest_quality_passed"] is True
    assert report["operational_decision_allowed"] is False
    assert report["api_key_required"] is False
    assert report["orders_generated"] is False
    assert report["real_capital_used"] is False
