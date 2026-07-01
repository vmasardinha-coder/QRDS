from __future__ import annotations

import json
from pathlib import Path

from crypto_decision_lab.reports.risk_model import RiskConfig, generate_risk_model_gate


def _write_report(path: Path, schema: str, report_name: str, gate_answer: str, score: float = 0.75) -> Path:
    payload = {
        "schema": schema,
        "report_name": report_name,
        "gate_answer": gate_answer,
        "mean_research_readiness_score": score,
        "report_payload_sha256": f"sha-{report_name}",
        "orders_generated": False,
        "recommendation_generated": False,
        "allocation_generated": False,
        "operational_decision_allowed": False,
    }
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_risk_model_blocks_without_inputs(tmp_path: Path) -> None:
    index = generate_risk_model_gate(output_dir=tmp_path, symbols=["BTC-USDT"])
    assert index["gate_answer"] == "NO_RISK_MODEL_NO_INPUT_REPORTS_RESEARCH_ONLY"
    assert index["formal_risk_ready"] is False
    assert index["operational_decision_allowed"] is False
    assert index["orders_generated"] is False
    assert index["trading_signal_generated"] is False
    assert index["recommendation_generated"] is False
    assert index["allocation_generated"] is False
    assert (tmp_path / "index.html").exists()
    assert (tmp_path / "risk_model_gate.json").exists()


def test_risk_model_records_review_but_policy_stays_locked(tmp_path: Path) -> None:
    reports = [
        _write_report(tmp_path / "evidence_quality_gate.json", "qrds.evidence_quality_index.v1", "qrds-evidence-quality-gate", "PARTIAL_EVIDENCE_IS_MATURING_BUT_MORE_GATES_REQUIRED_RESEARCH_ONLY"),
        _write_report(tmp_path / "evidence_drilldown_gate.json", "qrds.evidence_drilldown_index.v1", "qrds-evidence-drilldown-gate", "PARTIAL_COVERAGE_DRILLDOWN_MORE_EVIDENCE_REQUIRED_RESEARCH_ONLY"),
        _write_report(tmp_path / "evidence_timeline_gate.json", "qrds.evidence_timeline_index.v1", "qrds-evidence-timeline-gate", "NO_EVIDENCE_HISTORY_NOT_READY_FOR_NEXT_RESEARCH_GATE_RESEARCH_ONLY"),
        _write_report(tmp_path / "research_promotion_gate.json", "qrds.research_promotion_index.v1", "qrds-research-promotion-gate", "NO_RESEARCH_PROMOTION_CURRENT_EVIDENCE_GATES_INCOMPLETE_RESEARCH_ONLY"),
        _write_report(tmp_path / "human_review_gate.json", "qrds.human_review_index.v1", "qrds-human-review-gate", "HUMAN_REVIEW_IN_PROGRESS_POLICY_LOCKED_RESEARCH_ONLY"),
        _write_report(tmp_path / "oos_validation_gate.json", "qrds.oos_validation_index.v1", "qrds-oos-validation-gate", "OOS_VALIDATION_INCOMPLETE_MORE_RESEARCH_REQUIRED_RESEARCH_ONLY"),
        _write_report(tmp_path / "paper_trading_gate.json", "qrds.paper_trading_index.v1", "qrds-paper-trading-gate", "NO_PAPER_TRADING_ACCEPTANCE_INCOMPLETE_RESEARCH_ONLY"),
    ]
    index = generate_risk_model_gate(
        output_dir=tmp_path / "out",
        symbols=["BTC-USDT", "ETH-USDT"],
        report_paths=[str(p) for p in reports],
        config=RiskConfig(
            max_portfolio_drawdown_pct=20,
            max_symbol_exposure_pct=35,
            daily_loss_limit_pct=5,
            stress_loss_limit_pct=30,
            kill_switch_present=True,
            liquidity_check_present=True,
            cost_model_present=True,
            risk_artifact_present=True,
            risk_state="UNDER_REVIEW",
        ),
    )
    assert index["gate_answer"] == "RISK_MODEL_INCOMPLETE_MORE_RESEARCH_REQUIRED_RESEARCH_ONLY"
    assert index["input_report_count"] == 7
    assert index["criteria_ready_count"] >= 10
    assert index["policy_lock"] == "ACTIVE"
    assert index["operational_decision_allowed"] is False


def test_risk_model_can_be_reviewed_but_never_operational(tmp_path: Path) -> None:
    reports = []
    names = [
        ("evidence_quality", "qrds-evidence-quality-gate"),
        ("evidence_drilldown", "qrds-evidence-drilldown-gate"),
        ("evidence_timeline", "qrds-evidence-timeline-gate"),
        ("research_promotion", "qrds-research-promotion-gate"),
        ("human_review", "qrds-human-review-gate"),
        ("oos_validation", "qrds-oos-validation-gate"),
        ("paper_trading", "qrds-paper-trading-gate"),
    ]
    for kind, report_name in names:
        reports.append(_write_report(tmp_path / f"{kind}.json", f"qrds.{kind}_index.v1", report_name, "RECORDED_RESEARCH_ONLY", 0.8))
    index = generate_risk_model_gate(
        output_dir=tmp_path / "out",
        symbols=["BTC-USDT"],
        report_paths=[str(p) for p in reports],
        config=RiskConfig(
            max_portfolio_drawdown_pct=20,
            max_symbol_exposure_pct=35,
            daily_loss_limit_pct=5,
            stress_loss_limit_pct=30,
            kill_switch_present=True,
            liquidity_check_present=True,
            cost_model_present=True,
            risk_artifact_present=True,
            risk_state="APPROVED_RESEARCH_ONLY",
        ),
    )
    assert index["gate_answer"] == "RISK_MODEL_REVIEWED_POLICY_LOCKED_RESEARCH_ONLY"
    assert index["formal_risk_ready"] is True
    assert index["orders_allowed"] is False
    assert index["orders_generated"] is False
    assert index["real_capital_used"] is False
    assert index["portfolio_decision_generated"] is False
