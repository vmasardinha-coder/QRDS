$ErrorActionPreference = "Continue"
$projectRoot = "C:\QRDS\crypto_decision_lab"
$pythonExe = Join-Path $projectRoot ".venv\Scripts\python.exe"
$tests = @(
    "tests/unit/test_phase406_phase405_global_suite_certificate_seal_research_only.py",
    "tests/unit/test_phase407_resumed_executed_test_attribution_audit_research_only.py",
    "tests/unit/test_phase408_post_suite_repository_hygiene_artifact_isolation_research_only.py",
    "tests/unit/test_phase409_sealed_certificate_deterministic_release_reconstruction_research_only.py",
    "tests/unit/test_phase410_post_global_suite_reliability_midpoint_checkpoint_research_only.py",
    "tests/unit/test_phase411_portal_tracking_consistency_audit_research_only.py",
    "tests/unit/test_phase412_rollback_documentation_recovery_evidence_validation_research_only.py",
    "tests/unit/test_phase413_scientific_family_explicit_approval_guard_research_only.py",
    "tests/unit/test_phase414_post_global_suite_unified_portal_research_only.py",
    "tests/unit/test_phase415_post_global_suite_integrated_tracking_checkpoint_research_only.py",
    "tests/unit/test_phase405_mandatory_global_full_suite_integrated_checkpoint_research_only.py",
    "tests/unit/test_phase404_repeated_release_reliability_unified_portal_research_only.py"
)
Push-Location $projectRoot
try { & $pythonExe -B -m pytest -q --tb=long @tests; exit $LASTEXITCODE } finally { Pop-Location }
