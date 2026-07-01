from __future__ import annotations

import json
from pathlib import Path

from crypto_decision_lab.reports.operational_security import SecurityConfig, generate_operational_security_gate


def _write_report(path: Path, schema: str, report_name: str, gate_answer: str, ready: bool = True) -> Path:
    payload = {
        "schema": schema,
        "report_name": report_name,
        "gate_answer": gate_answer,
        "ready": ready,
        "report_payload_sha256": f"sha-{report_name}",
        "api_key_required": False,
        "api_key_present": False,
        "account_connection_required": False,
        "authenticated_connection_used": False,
        "orders_allowed": False,
        "orders_generated": False,
        "real_capital_used": False,
        "trading_signal_generated": False,
        "executable_signal_generated": False,
        "recommendation_generated": False,
        "allocation_generated": False,
        "portfolio_decision_generated": False,
        "operational_decision_allowed": False,
    }
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _all_reports(tmp_path: Path) -> list[Path]:
    items = [
        ("evidence_quality_gate.json", "qrds.evidence_quality_index.v1", "qrds-evidence-quality-gate"),
        ("evidence_drilldown_gate.json", "qrds.evidence_drilldown_index.v1", "qrds-evidence-drilldown-gate"),
        ("evidence_timeline_gate.json", "qrds.evidence_timeline_index.v1", "qrds-evidence-timeline-gate"),
        ("research_promotion_gate.json", "qrds.research_promotion_index.v1", "qrds-research-promotion-gate"),
        ("human_review_gate.json", "qrds.human_review_index.v1", "qrds-human-review-gate"),
        ("oos_validation_gate.json", "qrds.oos_validation_index.v1", "qrds-oos-validation-gate"),
        ("paper_trading_gate.json", "qrds.paper_trading_index.v1", "qrds-paper-trading-gate"),
        ("risk_model_gate.json", "qrds.risk_model_index.v1", "qrds-risk-model-gate"),
    ]
    return [_write_report(tmp_path / name, schema, report_name, "RECORDED_RESEARCH_ONLY") for name, schema, report_name in items]


def test_operational_security_blocks_without_inputs(tmp_path: Path) -> None:
    index = generate_operational_security_gate(output_dir=tmp_path, symbols=["BTC-USDT"])
    assert index["gate_answer"] == "NO_OPERATIONAL_SECURITY_NO_INPUT_REPORTS_RESEARCH_ONLY"
    assert index["formal_operational_security_ready"] is False
    assert index["api_key_present"] is False
    assert index["orders_generated"] is False
    assert index["trading_signal_generated"] is False
    assert index["recommendation_generated"] is False
    assert index["allocation_generated"] is False
    assert index["operational_decision_allowed"] is False
    assert (tmp_path / "index.html").exists()
    assert (tmp_path / "operational_security_gate.json").exists()


def test_operational_security_from_complete_stack_stays_locked(tmp_path: Path) -> None:
    reports = _all_reports(tmp_path)
    index = generate_operational_security_gate(
        output_dir=tmp_path / "out",
        symbols=["BTC-USDT", "ETH-USDT"],
        report_paths=[str(p) for p in reports],
        config=SecurityConfig(security_state="UNDER_REVIEW"),
    )
    assert index["gate_answer"] == "OPERATIONAL_SECURITY_INCOMPLETE_MORE_REVIEW_REQUIRED_RESEARCH_ONLY"
    assert index["input_report_count"] == 8
    assert index["criteria_ready_count"] == index["criteria_count"]
    assert index["policy_lock"] == "ACTIVE"
    assert index["formal_operational_security_ready"] is False
    assert index["operational_decision_allowed"] is False


def test_operational_security_can_record_review_but_never_unlock_ops(tmp_path: Path) -> None:
    reports = _all_reports(tmp_path)
    index = generate_operational_security_gate(
        output_dir=tmp_path / "out",
        symbols=["BTC-USDT"],
        report_paths=[str(p) for p in reports],
        config=SecurityConfig(security_state="APPROVED_RESEARCH_ONLY"),
    )
    assert index["gate_answer"] == "OPERATIONAL_SECURITY_REVIEWED_POLICY_LOCKED_RESEARCH_ONLY"
    assert index["formal_operational_security_ready"] is True
    assert index["orders_allowed"] is False
    assert index["orders_generated"] is False
    assert index["real_capital_used"] is False
    assert index["portfolio_decision_generated"] is False


def test_operational_security_blocks_unsafe_config(tmp_path: Path) -> None:
    reports = _all_reports(tmp_path)
    index = generate_operational_security_gate(
        output_dir=tmp_path / "out",
        report_paths=[str(p) for p in reports],
        config=SecurityConfig(api_key_present=True),
    )
    assert index["gate_answer"] == "OPERATIONAL_SECURITY_BLOCKED_UNSAFE_CONFIG_RESEARCH_ONLY"
    assert index["formal_operational_security_ready"] is False
    assert index["api_key_present"] is False
