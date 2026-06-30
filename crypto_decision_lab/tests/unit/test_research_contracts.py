import pytest

from crypto_decision_lab.contracts.research import (
    CONTRACT_FREEZE_REGISTRY_SCHEMA_VERSION,
    INTEGRATION_HEALTH_REPORT_SCHEMA_VERSION,
    RESEARCH_APP_MODE,
    ResearchContractError,
    assert_research_only_artifact,
    build_contract_freeze_registry,
    build_integration_health_report,
    build_research_safety_stamp,
    collect_research_contract_issues,
    validate_contract_freeze_registry,
    validate_integration_health_report,
)


def test_build_research_safety_stamp():
    stamp = build_research_safety_stamp()

    assert stamp["research_allowed"] is True
    assert stamp["app_mode"] == RESEARCH_APP_MODE
    assert stamp["operational_decision_allowed"] is False
    assert stamp["api_key_required"] is False
    assert stamp["orders_generated"] is False
    assert stamp["real_capital_used"] is False
    assert stamp["recommendation_generated"] is False


def test_collect_research_contract_issues_passes_safe_artifact():
    artifact = {
        "schema": "unit.schema.v1",
        "research_allowed": True,
        "operational_decision_allowed": False,
        "api_key_required": False,
        "orders_generated": False,
        "real_capital_used": False,
    }

    assert collect_research_contract_issues(artifact, name="unit") == []


def test_collect_research_contract_issues_flags_unsafe_artifact():
    artifact = {
        "schema": "unit.schema.v1",
        "orders_generated": True,
    }

    issues = collect_research_contract_issues(artifact, name="unit")

    assert any(issue["code"] == "UNSAFE_RESEARCH_FLAG" for issue in issues)


def test_assert_research_only_artifact_raises():
    with pytest.raises(ResearchContractError):
        assert_research_only_artifact(
            {"schema": "unit.schema.v1", "real_capital_used": True},
            name="unsafe",
        )


def test_build_contract_freeze_registry():
    registry = build_contract_freeze_registry()

    assert registry["schema"] == CONTRACT_FREEZE_REGISTRY_SCHEMA_VERSION
    assert registry["app_mode"] == RESEARCH_APP_MODE
    assert registry["approved_phase_count"] >= 20
    assert "qrds.edge_report.v1" in registry["known_artifact_schemas"]
    assert validate_contract_freeze_registry(registry) == []


def test_build_integration_health_report():
    artifacts = {
        "a": {
            "schema": "unit.a.v1",
            "research_allowed": True,
            "operational_decision_allowed": False,
            "api_key_required": False,
            "orders_generated": False,
            "real_capital_used": False,
        },
        "b": {
            "schema": "unit.b.v1",
            "research_allowed": True,
            "operational_decision_allowed": False,
            "api_key_required": False,
            "orders_generated": False,
            "real_capital_used": False,
        },
    }

    report = build_integration_health_report(artifacts)

    assert report["schema"] == INTEGRATION_HEALTH_REPORT_SCHEMA_VERSION
    assert report["integration_health_passed"] is True
    assert report["issue_summary"]["error_count"] == 0
    assert validate_integration_health_report(report) == []
