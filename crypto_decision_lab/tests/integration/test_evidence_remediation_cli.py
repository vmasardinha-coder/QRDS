from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_evidence_remediation_cli_generates_artifacts(tmp_path: Path) -> None:
    report = tmp_path / "evidence_quality_gate.json"
    report.write_text(
        json.dumps(
            {
                "schema": "qrds.evidence_quality_index.v1",
                "report_name": "qrds-evidence-quality-gate",
                "gate_answer": "PARTIAL_EVIDENCE_IS_MATURING_BUT_MORE_GATES_REQUIRED_RESEARCH_ONLY",
                "mean_research_readiness_score": 0.744,
            }
        ),
        encoding="utf-8",
    )
    output_dir = tmp_path / "out"

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "crypto_decision_lab.cli.evidence_remediation",
            "--output-dir",
            str(output_dir),
            "--symbols",
            "BTC-USDT,ETH-USDT",
            "--reports",
            str(report),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    index = json.loads(result.stdout)
    assert index["app_mode"] == "INTERACTIVE_RESEARCH_ONLY"
    assert index["input_report_count"] == 1
    assert index["operational_decision_allowed"] is False
    assert (output_dir / "index.html").exists()
    assert (output_dir / "evidence_remediation_plan.json").exists()


def test_root_wrapper_exists_after_sprint_generation() -> None:
    assert Path("../qrds_evidence_remediation.sh").exists() or Path("qrds_evidence_remediation.sh").exists()
