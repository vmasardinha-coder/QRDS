from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path


def _env(project_root: Path) -> dict[str, str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = f"{project_root / 'src'}{os.pathsep}{env.get('PYTHONPATH', '')}"
    return env


def test_evidence_timeline_wrapper_generates_artifacts(tmp_path: Path) -> None:
    project_root = Path(__file__).resolve().parents[2]
    repo_root = project_root.parent
    wrapper = repo_root / "qrds_evidence_timeline.sh"
    output_dir = tmp_path / "timeline"

    result = subprocess.run(
        ["bash", str(wrapper), "--output-dir", str(output_dir), "--symbols", "BTC-USDT,ETH-USDT"],
        cwd=repo_root,
        env=_env(project_root),
        text=True,
        capture_output=True,
        timeout=60,
    )

    assert result.returncode == 0, result.stderr + result.stdout
    assert (output_dir / "evidence_timeline_gate.json").exists()
    assert (output_dir / "evidence_timeline_gate.md").exists()
    assert (output_dir / "index.html").exists()

    payload = json.loads((output_dir / "evidence_timeline_gate.json").read_text(encoding="utf-8"))
    assert payload["schema"] == "qrds.evidence_timeline.v1"
    assert payload["operational_decision_allowed"] is False
    assert payload["trading_signal_generated"] is False
    assert payload["recommendation_generated"] is False
    assert payload["allocation_generated"] is False
    assert payload["portfolio_decision_generated"] is False


def test_evidence_timeline_accepts_existing_8l_8m_artifacts(tmp_path: Path) -> None:
    project_root = Path(__file__).resolve().parents[2]
    repo_root = project_root.parent
    quality_wrapper = repo_root / "qrds_evidence_quality.sh"
    drilldown_wrapper = repo_root / "qrds_evidence_drilldown.sh"
    timeline_wrapper = repo_root / "qrds_evidence_timeline.sh"
    quality_dir = tmp_path / "quality"
    drilldown_dir = tmp_path / "drilldown"
    timeline_dir = tmp_path / "timeline"
    env = _env(project_root)

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

    third = subprocess.run(
        [
            "bash",
            str(timeline_wrapper),
            "--output-dir",
            str(timeline_dir),
            "--reports",
            f"{quality_dir / 'evidence_quality_gate.json'},{drilldown_dir / 'evidence_drilldown_gate.json'}",
        ],
        cwd=repo_root,
        env=env,
        text=True,
        capture_output=True,
        timeout=60,
    )

    assert third.returncode == 0, third.stderr + third.stdout
    payload = json.loads((timeline_dir / "evidence_timeline_gate.json").read_text(encoding="utf-8"))
    assert payload["symbols"] == ["BTC-USDT", "ETH-USDT"]
    assert payload["input_report_count"] == 2
    assert payload["observation_count"] == 4


def test_evidence_timeline_serve_wrapper_contains_codespaces_port_instruction() -> None:
    project_root = Path(__file__).resolve().parents[2]
    repo_root = project_root.parent
    serve_wrapper = repo_root / "qrds_evidence_timeline_serve.sh"

    text = serve_wrapper.read_text(encoding="utf-8")

    assert "Ports -> $PORT_TO_USE -> Open in Browser / Open Preview" in text
    assert "python -m http.server" in text
    assert "Ctrl+C" in text
