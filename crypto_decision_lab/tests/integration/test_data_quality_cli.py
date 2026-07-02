import json
import subprocess
import sys
from pathlib import Path


def test_data_quality_cli_generates_outputs(tmp_path):
    prior = tmp_path / "prior.json"
    prior.write_text(json.dumps({
        "report_name": "qrds-data-coverage-gate",
        "gate_answer": "DATA_COVERAGE_INCOMPLETE_MORE_COLLECTION_REQUIRED_RESEARCH_ONLY",
        "mean_coverage_score": 0.57,
        "report_payload_sha256": "abc123",
        "api_key_present": False,
        "authenticated_connection_used": False,
        "orders_generated": False,
        "real_orders_generated": False,
        "trading_signal_generated": False,
        "recommendation_generated": False,
        "allocation_generated": False,
        "operational_decision_allowed": False,
    }), encoding="utf-8")
    out = tmp_path / "data_quality"
    proc = subprocess.run(
        [sys.executable, "-m", "crypto_decision_lab.cli.data_quality", "--output-dir", str(out), "--symbols", "BTC-USDT,ETH-USDT", "--reports", str(prior)],
        check=True,
        text=True,
        capture_output=True,
    )
    data = json.loads(proc.stdout)
    assert data["app_mode"] == "INTERACTIVE_RESEARCH_ONLY"
    assert data["input_report_count"] == 1
    assert (out / "index.html").exists()
