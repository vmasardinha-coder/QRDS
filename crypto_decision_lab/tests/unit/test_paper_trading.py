from __future__ import annotations

import json
from pathlib import Path

from crypto_decision_lab.reports.paper_trading import build_paper_trading_gate, parse_symbols


def _fake_report(path: Path, schema: str, report_name: str, gate_answer: str, score: float = 0.82) -> Path:
    payload = {
        "schema": schema,
        "report_name": report_name,
        "gate_answer": gate_answer,
        "generated_at": "2026-01-01T00:00:00+00:00",
        "symbols": ["BTC-USDT", "ETH-USDT"],
        "mean_research_readiness_score": score,
        "mean_symbol_evidence_score": score,
        "research_allowed": True,
        "operational_decision_allowed": False,
        "orders_generated": False,
        "recommendation_generated": False,
    }
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_parse_symbols_dedupes_and_validates() -> None:
    assert parse_symbols("btc-usdt,ETH-USDT,btc-usdt") == ["BTC-USDT", "ETH-USDT"]


def test_no_input_reports_blocks_and_keeps_safety_flags_false(tmp_path: Path) -> None:
    index = build_paper_trading_gate(tmp_path / "out", symbols="BTC-USDT,ETH-USDT")
    assert index["gate_answer"] == "NO_PAPER_TRADING_NO_INPUT_REPORTS_RESEARCH_ONLY"
    assert index["formal_paper_trading_ready"] == "NO"
    assert index["operational_decision_allowed"] is False
    assert index["orders_generated"] is False
    assert index["recommendation_generated"] is False
    assert Path(index["html_path"]).exists()


def test_full_research_only_paper_packet_can_mark_observed_but_locked(tmp_path: Path) -> None:
    reports = [
        _fake_report(tmp_path / "8l.json", "qrds.evidence_quality_gate.v1", "qrds-evidence-quality-gate", "PARTIAL", 0.84),
        _fake_report(tmp_path / "8m.json", "qrds.evidence_drilldown_gate.v1", "qrds-evidence-drilldown-gate", "PARTIAL", 0.83),
        _fake_report(tmp_path / "8n.json", "qrds.evidence_timeline_gate.v1", "qrds-evidence-timeline-gate", "PARTIAL", 0.82),
        _fake_report(tmp_path / "8o.json", "qrds.research_promotion_gate.v1", "qrds-research-promotion-gate", "BLOCKED", 0.81),
        _fake_report(tmp_path / "8p.json", "qrds.human_review_gate.v1", "qrds-human-review-gate", "UNDER_REVIEW", 0.82),
        _fake_report(tmp_path / "8q.json", "qrds.oos_validation_gate.v1", "qrds-out-of-sample-validation-gate", "OOS_PACKET", 0.86),
    ]
    index = build_paper_trading_gate(
        tmp_path / "out",
        symbols="BTC-USDT,ETH-USDT",
        reports=",".join(str(path) for path in reports),
        paper_days=35,
        paper_runs=25,
        simulated_fill_rate=0.98,
        cost_model_present=True,
        paper_artifact_present=True,
        acceptance_state="APPROVED_RESEARCH_ONLY",
    )
    assert index["gate_answer"] == "PAPER_TRADING_RESEARCH_OBSERVED_OPERATIONAL_USE_LOCKED_RESEARCH_ONLY"
    assert index["formal_paper_trading_ready"] == "YES_RESEARCH_ONLY"
    assert index["operational_decision_allowed"] is False
    assert index["real_capital_used"] is False
    assert index["trading_signal_generated"] is False


def test_missing_prior_reports_remain_blocked(tmp_path: Path) -> None:
    index = build_paper_trading_gate(
        tmp_path / "out",
        symbols="BTC-USDT",
        reports=str(tmp_path / "missing.json"),
        paper_days=30,
        paper_runs=20,
        simulated_fill_rate=0.99,
    )
    assert index["gate_answer"] == "NO_PAPER_TRADING_NO_INPUT_REPORTS_RESEARCH_ONLY"
    assert index["input_report_count"] == 0
    assert index["orders_allowed"] is False
