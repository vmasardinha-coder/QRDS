import json, subprocess, sys
from pathlib import Path
def test_phase11_offline_source_normalizer_pack_cli_generates_outputs(tmp_path: Path):
    p=subprocess.run([sys.executable,"-m","crypto_decision_lab.cli.phase11_offline_source_normalizer_pack","--output-dir",str(tmp_path/"out"),"--repo-root",str(tmp_path/"repo")],text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True)
    r=json.loads(p.stdout)
    assert r["policy_lock"]=="ACTIVE"; assert r["app_mode"]=="INTERACTIVE_RESEARCH_ONLY"
    assert Path(r["html_path"]).exists()
