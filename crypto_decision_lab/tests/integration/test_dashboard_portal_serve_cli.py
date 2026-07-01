import subprocess
import time
from pathlib import Path


def test_dashboard_portal_cli_plan_only_with_serve_flag(tmp_path):
    root = Path(__file__).resolve().parents[3]
    output_dir = tmp_path / "portal-plan-only"

    result = subprocess.run(
        [
            "bash",
            "qrds_dashboard_portal.sh",
            "--output-dir",
            str(output_dir),
            "--symbols",
            "ETH-USDT,SOL-USDT",
            "--portal-name",
            "plan-only-portal",
            "--preferred-port",
            "8041",
            "--serve",
            "--plan-only",
        ],
        cwd=root,
        text=True,
        capture_output=True,
        check=True,
    )

    assert "=== UNIFIED PORTAL READY ===" in result.stdout
    assert "=== SERVE COMMAND ===" in result.stdout
    assert "=== CODESPACES PORT HINT ===" in result.stdout
    assert (output_dir / "index.html").exists()
    assert (output_dir / "dashboard_serve_plan.json").exists()


def test_qrds_portal_serve_wrapper_starts_server(tmp_path):
    root = Path(__file__).resolve().parents[3]
    output_dir = tmp_path / "portal-serve-wrapper"

    proc = subprocess.Popen(
        [
            "bash",
            "qrds_portal_serve.sh",
            "--output-dir",
            str(output_dir),
            "--symbols",
            "ETH-USDT,SOL-USDT",
            "--portal-name",
            "serve-wrapper-portal",
            "--preferred-port",
            "8042",
        ],
        cwd=root,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    try:
        time.sleep(4)
        assert proc.poll() is None
        assert (output_dir / "index.html").exists()
        assert (output_dir / "dashboard_serve_plan.json").exists()
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=8)
        except subprocess.TimeoutExpired:
            proc.kill()
