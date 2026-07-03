from pathlib import Path
from crypto_decision_lab.reports.archive_manifest_repo_hygiene import build_archive_manifest_repo_hygiene

def test_archive_manifest_repo_hygiene_builds_artifacts(tmp_path: Path) -> None:
    root=tmp_path/'repo'; (root/'scripts'/'archive'/'installers').mkdir(parents=True)
    (root/'scripts'/'archive'/'installers'/'qrds_sprint_9A_example.sh').write_text('#!/usr/bin/env bash\n',encoding='utf-8')
    (root/'crypto_decision_lab'/'docs').mkdir(parents=True); (root/'crypto_decision_lab'/'docs'/'x.md').write_text('doc',encoding='utf-8')
    (root/'crypto_decision_lab'/'artifacts'/'p').mkdir(parents=True); (root/'crypto_decision_lab'/'artifacts'/'p'/'index.html').write_text('<html></html>',encoding='utf-8')
    result=build_archive_manifest_repo_hygiene(output_dir=tmp_path/'out', repo_root=root); payload=result['payload']
    assert payload['policy_lock']=='ACTIVE'; assert payload['app_mode']=='INTERACTIVE_RESEARCH_ONLY'
    assert payload['archived_installer_count']==1; assert payload['criteria_ready_count']>=5
    assert Path(result['html_path']).exists(); assert Path(result['markdown_path']).exists(); assert Path(result['report_path']).exists()

def test_archive_manifest_repo_hygiene_has_no_operational_flags(tmp_path: Path) -> None:
    root=tmp_path/'repo'; (root/'scripts'/'archive'/'installers').mkdir(parents=True); (root/'crypto_decision_lab'/'docs').mkdir(parents=True); (root/'crypto_decision_lab'/'artifacts'/'p').mkdir(parents=True)
    (root/'crypto_decision_lab'/'artifacts'/'p'/'index.html').write_text('<html></html>',encoding='utf-8')
    result=build_archive_manifest_repo_hygiene(output_dir=tmp_path/'out', repo_root=root); payload=result['payload']
    for key in ['api_key_present','authenticated_connection_used','orders_generated','real_orders_generated','real_capital_used','trading_signal_generated','executable_signal_generated','recommendation_generated','allocation_generated','portfolio_decision_generated','operational_decision_allowed']:
        assert payload[key] is False
