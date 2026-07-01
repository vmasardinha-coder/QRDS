from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path


def test_evidence_drilldown_root_wrapper_generates_artifacts(tmp_path) -> None:
    project_root = Path(__file__).resolve().parents[2]
    repo_root = project_root.parent
    wrapper = repo_root / "qrds_evidence_drilldown.sh"
    output_dir = tmp_path / "evidence_drilldown"
    env = os.environ.copy()
    env["PYTHONPATH"] = f"{project_root / 'src'}{os.pathsep}{env.get('PYTHONPATH', '')}"

    result = subprocess.run(
        [
            "bash",
            str(wrapper),
            "--output-dir",
            str(output_dir),
            "--symbols",
            "BTC-USDT,ETH-USDT,SOL-USDT",
        ],
        cwd=repo_root,
        env=env,
        text=True,
        capture_output=True,
        timeout=60,
    )

    assert result.returncode == 0, result.stderr + result.stdout
    assert (output_dir / "index.html").exists()
    assert (output_dir / "evidence_drilldown_gate.json").exists()
    payload = json.loads((output_dir / "evidence_drilldown_gate.json").read_text(encoding="utf-8"))
    assert payload["app_mode"] == "INTERACTIVE_RESEARCH_ONLY"
    assert payload["orders_generated"] is False
    assert payload["recommendation_generated"] is False
    assert payload["allocation_generated"] is False


def test_evidence_drilldown_cli_accepts_existing_evidence_report(tmp_path) -> None:
    project_root = Path(__file__).resolve().parents[2]
    repo_root = project_root.parent
    quality_wrapper = repo_root / "qrds_evidence_quality.sh"
    drilldown_wrapper = repo_root / "qrds_evidence_drilldown.sh"
    quality_dir = tmp_path / "quality"
    drilldown_dir = tmp_path / "drilldown"
    env = os.environ.copy()
    env["PYTHONPATH"] = f"{project_root / 'src'}{os.pathsep}{env.get('PYTHONPATH', '')}"

    first = subprocess.run(
        ["bash", str(quality_wrapper), "--output-dir", str(quality_dir), "--symbols", "BTC-USDT,ETH-USDT"],
        cwd=repo_root,
        env=env,
        text=True,
        capture_output=True,
        timeout=60,
    )
    assert first.returncode == 0, first.stderr + first.stdout

    second = subprocess.run(
        ["bash", str(drilldown_wrapper), "--output-dir", str(drilldown_dir), "--evidence-report", str(quality_dir / "evidence_quality_gate.json")],
        cwd=repo_root,
        env=env,
        text=True,
        capture_output=True,
        timeout=60,
    )

    assert second.returncode == 0, second.stderr + second.stdout
    assert (drilldown_dir / "index.html").exists()
    payload = json.loads((drilldown_dir / "evidence_drilldown_gate.json").read_text(encoding="utf-8"))
    assert payload["symbols"] == ["BTC-USDT", "ETH-USDT"]


def test_evidence_drilldown_serve_wrapper_contains_codespaces_port_instruction() -> None:
    project_root = Path(__file__).resolve().parents[2]
    repo_root = project_root.parent
    serve_wrapper = repo_root / "qrds_evidence_drilldown_serve.sh"

    text = serve_wrapper.read_text(encoding="utf-8")

    assert "Ports -> $PORT_TO_USE -> Open in Browser / Open Preview" in text
    assert "python -m http.server" in text
    assert "Ctrl+C" in text
