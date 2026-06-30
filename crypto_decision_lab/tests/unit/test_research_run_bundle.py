from pathlib import Path

import pytest

from crypto_decision_lab.runs.bundle import (
    RESEARCH_ARTIFACT_INDEX_SCHEMA_VERSION,
    RESEARCH_RUN_BUNDLE_SCHEMA_VERSION,
    ResearchRunBundleError,
    build_research_artifact_index,
    build_research_run_bundle,
    build_research_run_bundle_report,
    compute_sha256,
    validate_research_bundle,
)


def _manifest():
    return {
        "schema": "qrds.research_run_manifest.v1",
        "run_id": "unit-run",
        "app_mode": "INTERACTIVE_RESEARCH_ONLY",
        "symbol": "BTC-USDT",
        "interval": "1h",
        "source": "unit_test",
        "api_key_required": False,
        "api_key_present": False,
        "account_connection_required": False,
        "orders_generated": False,
        "real_capital_used": False,
        "operational_decision_allowed": False,
        "research_allowed": True,
    }


def test_compute_sha256(tmp_path):
    path = tmp_path / "artifact.jsonl"
    path.write_text('{"x": 1}\n', encoding="utf-8")

    digest = compute_sha256(path)

    assert isinstance(digest, str)
    assert len(digest) == 64


def test_build_research_artifact_index(tmp_path):
    artifact = tmp_path / "dataset.jsonl"
    artifact.write_text('{"x": 1}\n', encoding="utf-8")

    index = build_research_artifact_index(
        bundle_dir=tmp_path / "bundle",
        artifact_paths=[artifact],
    )

    assert index["schema"] == RESEARCH_ARTIFACT_INDEX_SCHEMA_VERSION
    assert index["artifact_count"] == 1
    assert index["operational_decision_allowed"] is False
    copied = tmp_path / "bundle" / index["artifacts"][0]["relative_path"]
    assert copied.exists()


def test_build_research_run_bundle(tmp_path):
    artifact = tmp_path / "dataset.jsonl"
    artifact.write_text('{"x": 1}\n', encoding="utf-8")

    bundle = build_research_run_bundle(
        manifest=_manifest(),
        artifact_paths=[artifact],
        output_dir=tmp_path / "bundles",
        bundle_name="bundle-unit",
    )

    assert bundle["schema"] == RESEARCH_RUN_BUNDLE_SCHEMA_VERSION
    assert bundle["artifact_count"] == 1
    assert bundle["operational_decision_allowed"] is False
    assert Path(bundle["manifest_path"]).exists()
    assert Path(bundle["artifact_index_path"]).exists()
    assert Path(bundle["bundle_report_path"]).exists()
    assert validate_research_bundle(bundle) == []


def test_build_research_run_bundle_blocks_operational_manifest(tmp_path):
    artifact = tmp_path / "dataset.jsonl"
    artifact.write_text('{"x": 1}\n', encoding="utf-8")

    manifest = _manifest()
    manifest["operational_decision_allowed"] = True

    with pytest.raises(ResearchRunBundleError):
        build_research_run_bundle(
            manifest=manifest,
            artifact_paths=[artifact],
            output_dir=tmp_path / "bundles",
            bundle_name="bundle-unit",
        )


def test_build_research_run_bundle_report(tmp_path):
    artifact = tmp_path / "dataset.jsonl"
    artifact.write_text('{"x": 1}\n', encoding="utf-8")

    bundle = build_research_run_bundle(
        manifest=_manifest(),
        artifact_paths=[artifact],
        output_dir=tmp_path / "bundles",
        bundle_name="bundle-unit",
    )

    report = build_research_run_bundle_report(bundle)

    assert report["bundle_quality_passed"] is True
    assert report["operational_decision_allowed"] is False
    assert report["api_key_required"] is False
    assert report["orders_generated"] is False
    assert report["real_capital_used"] is False
