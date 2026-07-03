import json, subprocess, sys
from pathlib import Path

def test_archive_manifest_repo_hygiene_cli_generates_outputs(tmp_path: Path) -> None:
    root=tmp_path/'repo'; (root/'scripts'/'archive'/'installers').mkdir(parents=True)
    (root/'scripts'/'archive'/'installers'/'qrds_sprint_9A_example.sh').write_text('#!/usr/bin/env bash\n',encoding='utf-8')
    (root/'crypto_decision_lab'/'docs').mkdir(parents=True); (root/'crypto_decision_lab'/'docs'/'x.md').write_text('doc',encoding='utf-8')
    (root/'crypto_decision_lab'/'artifacts'/'p').mkdir(parents=True); (root/'crypto_decision_lab'/'artifacts'/'p'/'index.html').write_text('<html></html>',encoding='utf-8')
    out=tmp_path/'out'
    proc=subprocess.run([sys.executable,'-m','crypto_decision_lab.cli.archive_manifest_repo_hygiene','--output-dir',str(out),'--repo-root',str(root)],text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True)
    result=json.loads(proc.stdout); assert result['policy_lock']=='ACTIVE'; assert result['app_mode']=='INTERACTIVE_RESEARCH_ONLY'; assert Path(result['html_path']).exists()
