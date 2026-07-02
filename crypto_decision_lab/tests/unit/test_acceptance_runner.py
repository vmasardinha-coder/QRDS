import json
from pathlib import Path

from crypto_decision_lab.reports.acceptance_runner import build_acceptance_runner


def test_acceptance_runner_builds_expected_artifacts(tmp_path: Path) -> None:
    prior = tmp_path / "evidence_quality_gate.json"
    prior.write_text(
        json.dumps(
            {
                "report_name": "qrds-evidence-quality-gate",
                "gate_answer": "PARTIAL_EVIDENCE_IS_MATURING_BUT_MORE_GATES_REQUIRED_RESEARCH_ONLY",
                "mean_research_readiness_score": 0.7,
                "report_payload_sha256": "abc123",
                "app_mode": "INTERACTIVE_RESEARCH_ONLY",
                "research_allowed": True,
                "hypothetical_only": True,
                "orders_generated": False,
                "real_capital_used": False,
                "trading_signal_generated": False,
                "recommendation_generated": False,
                "allocation_generated": False,
                "portfolio_decision_generated": False,
                "operational_decision_allowed": False,
            }
        ),
        encoding="utf-8",
    )

    result = build_acceptance_runner(
        tmp_path / "acceptance",
        "BTC-USDT,ETH-USDT",
        reports=[prior],
        pytest_status="PASS",
        git_status_text="",
    )

    payload = result["payload"]
    assert payload["app_mode"] == "INTERACTIVE_RESEARCH_ONLY"
    assert payload["report_present_count"] == 1
    assert payload["blocking_gate_count"] >= 1
    assert payload["orders_generated"] is False
    assert (tmp_path / "acceptance" / "index.html").exists()
    assert (tmp_path / "acceptance" / "acceptance_runner.json").exists()


def test_acceptance_runner_detects_suspicious_untracked(tmp_path: Path) -> None:
    result = build_acceptance_runner(
        tmp_path / "acceptance",
        "BTC-USDT",
        reports=[],
        pytest_status="PASS",
        git_status_text="?? unexpected_file.py\n?? qrds_sprint_foo.sh\n?? artifacts/local.json\n",
    )
    assert result["payload"]["suspicious_untracked_count"] == 1
