$ErrorActionPreference = "Stop"
Set-StrictMode -Version 2.0
$projectRoot = "C:\QRDS\crypto_decision_lab"
$pythonExe = Join-Path $projectRoot ".venv\Scripts\python.exe"
$tests = @(
    "tests/unit/test_phase386_observation_only_use_case_freeze_research_only.py",
    "tests/unit/test_phase387_schema_compatibility_observation_adapter_research_only.py",
    "tests/unit/test_phase388_repeated_integrity_fingerprint_observation_research_only.py",
    "tests/unit/test_phase389_release_harness_failure_taxonomy_coverage_audit_research_only.py",
    "tests/unit/test_phase390_clean_clone_interrupted_resume_fixture_exercise_research_only.py",
    "tests/unit/test_phase391_github_manual_pr_release_workflow_validation_research_only.py",
    "tests/unit/test_phase392_scientific_novelty_approval_gate_research_only.py",
    "tests/unit/test_phase393_no_scientific_family_checkpoint_research_only.py",
    "tests/unit/test_phase394_observation_release_hardening_unified_portal_research_only.py",
    "tests/unit/test_phase395_observation_release_hardening_integrated_checkpoint_research_only.py",
    "tests/unit/test_phase383_release_harness_and_repetitive_failure_scanner_research_only.py",
    "tests/unit/test_phase385_noncanonical_research_dataset_adoption_full_integration_checkpoint_research_only.py"
)
Push-Location $projectRoot
try {
    & $pythonExe -B -m pytest -q --tb=long @tests
    exit $LASTEXITCODE
}
finally {
    Pop-Location
}
