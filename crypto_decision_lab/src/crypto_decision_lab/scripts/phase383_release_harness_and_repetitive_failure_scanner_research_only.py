from __future__ import annotations
import argparse
from pathlib import Path
from typing import Any
from crypto_decision_lab.scripts.phase376_385_remediated_dataset_adoption_common import OBSERVED_FAILURE_CLASSES, ROOT, base_payload, fingerprint, phase_summary, python_syntax_check, read_json, scan_for_observed_patterns, validate_phase, write_json, write_summary

def build(phase382_path:Path,powershell_parser_report_path:Path,output_dir:Path,*,installer_path:Path|None=None,project_root:Path|None=None)->dict[str,Any]:
    p382=read_json(phase382_path); validate_phase(p382,382); root=(project_root or ROOT).resolve()
    source_paths=sorted((root/"src/crypto_decision_lab/scripts").glob("phase37[6-9]*.py"))+sorted((root/"src/crypto_decision_lab/scripts").glob("phase38[0-5]*.py"))
    text_paths=list(source_paths)
    for relative in ("scripts/qrds_release_gate_376_385.ps1", "scripts/serve_phase384_remediated_dataset_adoption_portal.ps1"):
        path = root / relative
        if path.is_file():
            text_paths.append(path)
    workflow_candidates = (
        root.parent / ".github/workflows/qrds-release-gate-windows-linux.yml",
        root / ".github/workflows/qrds-release-gate-windows-linux.yml",
    )
    for path in workflow_candidates:
        if path.is_file():
            text_paths.append(path)
            break
    if installer_path is not None and installer_path.is_file(): text_paths.append(installer_path)
    syntax_findings=python_syntax_check([p for p in source_paths if p.suffix==".py"])
    pattern_findings=scan_for_observed_patterns(text_paths)
    ps_report=read_json(powershell_parser_report_path)
    checks={"rollback_coexistence_pass":p382.get("coexistence_pass") is True,"python_syntax_findings_zero":len(syntax_findings)==0,"observed_pattern_findings_zero":len(pattern_findings)==0,"powershell_parser_pass":ps_report.get("passed") is True,"powershell_parse_error_count_zero":int(ps_report.get("error_count",-1))==0,"release_files_scanned":len(text_paths)>=10}
    failed=sorted(k for k,v in checks.items() if not v)
    if failed: raise RuntimeError(f"Phase 383 release harness failed; failed_checks={failed!r}; syntax_findings={syntax_findings!r}; pattern_findings={pattern_findings!r}; powershell_report={ps_report!r}.")
    payload=base_payload(383,"RELEASE_HARNESS_AND_REPETITIVE_FAILURE_SCANNER_PASS_RESEARCH_ONLY"); payload.update({"gate":"PHASE383_RELEASE_HARNESS_AND_REPETITIVE_FAILURE_SCANNER_READY_RESEARCH_ONLY","release_checks":checks,"failed_checks":[],"release_harness_pass":True,"observed_failure_classes":list(OBSERVED_FAILURE_CLASSES),"scanned_file_count":len(text_paths),"python_syntax_findings":syntax_findings,"observed_pattern_findings":pattern_findings,"powershell_parser_report":ps_report,"workflow_installed":".github/workflows/qrds-release-gate-windows-linux.yml","workflow_trigger_mode":"MANUAL_OR_PULL_REQUEST_ONLY","canonical_data_writes":0})
    payload["artifact_fingerprint"]=fingerprint(payload); output_dir.mkdir(parents=True,exist_ok=True); write_json(output_dir/"phase383_release_harness_and_repetitive_failure_scanner.json",payload)
    write_summary(phase_summary(383,"release_harness_and_repetitive_failure_scanner"),title="Phase 383 — Release Harness and Repetitive-failure Scanner",gate=payload["gate"],bullets=["Release harness pass: `True`",f"Observed failure classes frozen: `{len(OBSERVED_FAILURE_CLASSES)}`",f"Files scanned: `{len(text_paths)}`","PowerShell parser errors: `0`","Workflow trigger: `manual or pull request only`"]) ; return payload

def main()->int:
    a=argparse.ArgumentParser(); art=ROOT/"artifacts"; a.add_argument("--phase382-artifact",type=Path,default=art/"phase382_rollback_and_raw_coexistence_audit_research_only/phase382_rollback_and_raw_coexistence_audit.json"); a.add_argument("--powershell-parser-report",type=Path,required=True); a.add_argument("--installer-path",type=Path); a.add_argument("--output-dir",type=Path,default=art/"phase383_release_harness_and_repetitive_failure_scanner_research_only"); x=a.parse_args(); p=build(x.phase382_artifact,x.powershell_parser_report,x.output_dir,installer_path=x.installer_path); print(p["gate"]); print("Release harness pass:",p["release_harness_pass"]); return 0
if __name__=="__main__": raise SystemExit(main())
