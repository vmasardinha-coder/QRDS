$ErrorActionPreference = "Stop"
Set-StrictMode -Version 2.0
$projectRoot = "C:\QRDS\crypto_decision_lab"
$pythonExe = Join-Path $projectRoot ".venv\Scripts\python.exe"
$tests = @(
    "tests/unit/test_phase396_repeated_observation_run_manifest_semantics_freeze_research_only.py",
    "tests/unit/test_phase397_fingerprint_drift_threshold_registry_research_only.py",
    "tests/unit/test_phase398_repeated_clean_clone_interrupted_resume_reliability_research_only.py",
    "tests/unit/test_phase399_release_workflow_least_privilege_trigger_isolation_audit_research_only.py",
    "tests/unit/test_phase400_release_reliability_midpoint_checkpoint_research_only.py",
    "tests/unit/test_phase401_artifact_provenance_portal_registry_reconciliation_research_only.py",
    "tests/unit/test_phase402_deterministic_release_package_reconstruction_research_only.py",
    "tests/unit/test_phase403_scientific_family_opening_block_research_only.py",
    "tests/unit/test_phase404_repeated_release_reliability_unified_portal_research_only.py",
    "tests/unit/test_phase405_mandatory_global_full_suite_integrated_checkpoint_research_only.py",
    "tests/unit/test_phase395_observation_release_hardening_integrated_checkpoint_research_only.py",
    "tests/unit/test_phase391_github_manual_pr_release_workflow_validation_research_only.py",
    "tests/integration/test_dashboard_guide_cli.py"
)
Push-Location $projectRoot
try {
    & $pythonExe -B -m pytest -q --tb=long @tests
    exit $LASTEXITCODE
}
finally {
    Pop-Location
}
