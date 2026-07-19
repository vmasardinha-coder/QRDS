$ErrorActionPreference = "Continue"
$projectRoot = "C:\QRDS\crypto_decision_lab"
$pythonExe = Join-Path $projectRoot ".venv\Scripts\python.exe"
$tests = @(
    "tests/unit/test_phase416_certificate_retention_evidence_aging_policy_research_only.py"
    "tests/unit/test_phase417_artifact_freshness_audit_research_only.py"
    "tests/unit/test_phase418_deterministic_reproducibility_spotcheck_research_only.py"
    "tests/unit/test_phase419_documentation_tracking_drift_audit_research_only.py"
    "tests/unit/test_phase420_reliability_retention_midpoint_checkpoint_research_only.py"
    "tests/unit/test_phase421_readonly_governance_evidence_index_research_only.py"
    "tests/unit/test_phase422_future_manual_scientific_approval_prerequisites_audit_research_only.py"
    "tests/unit/test_phase423_approval_absence_scientific_family_closed_guard_research_only.py"
    "tests/unit/test_phase424_reliability_governance_unified_portal_research_only.py"
    "tests/unit/test_phase425_reliability_governance_integrated_checkpoint_research_only.py"
    "tests/unit/test_phase415_post_global_suite_integrated_tracking_checkpoint_research_only.py"
    "tests/unit/test_phase414_post_global_suite_unified_portal_research_only.py"
)
Push-Location $projectRoot
try {
    & $pythonExe -B -m pytest -q --tb=long @tests
    exit $LASTEXITCODE
}
finally {
    Pop-Location
}
