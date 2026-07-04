import json
import subprocess
import sys
from pathlib import Path


def test_phase26_cli_generates_outputs(tmp_path: Path) -> None:
    proc = subprocess.run([sys.executable, "-m", "crypto_decision_lab.cli.phase26_regime_segmented_volatility_edge_audit_pack", "--output-dir", str(tmp_path / "out"), "--repo-root", str(tmp_path / "repo"), "--min-rows-per-coin", "100"], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
    result = json.loads(proc.stdout)
    assert result["policy_lock"] == "ACTIVE"
    assert result["app_mode"] == "INTERACTIVE_RESEARCH_ONLY"
    assert Path(result["html_path"]).exists()
