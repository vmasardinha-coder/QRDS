from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
ARTIFACT = ROOT / "artifacts/phase186_test_inventory_research_only/phase186_test_inventory.json"
DOC = ROOT / "docs/reports/journal_replay/phase186_test_inventory_summary.md"

GATE = "PHASE186_TEST_INVENTORY_RESEARCH_ONLY_READY_RESEARCH_ONLY"

LOCKS = {
    "app_mode": "INTERACTIVE_RESEARCH_ONLY",
    "policy_lock": "ACTIVE",
    "operational_status": "BLOCKED_RESEARCH_ONLY",
    "edge_validated": False,
    "edge_operationally_validated": False,
    "shadow_decision_allowed": False,
    "decision_layer_allowed": False,
    "trading_signal_generated": False,
    "recommendation_generated": False,
    "allocation_generated": False,
    "operational_decision_allowed": False,
    "safe_apply_allowed": False,
    "promotion_allowed": False,
    "canonical_data_writes": 0,
}


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def files(base: Path, pattern: str) -> list[Path]:
    if not base.exists():
        return []
    return sorted(
        p for p in base.rglob(pattern)
        if p.is_file() and "__pycache__" not in p.parts
    )


def phase_coverage(items: list[Path]) -> dict[str, Any]:
    found: set[int] = set()

    for path in items:
        for raw in re.findall(r"phase[_-]?0*(\d{1,3})(?!\d)", rel(path), re.I):
            number = int(raw)
            if 0 <= number <= 185:
                found.add(number)

    expected = set(range(186))
    return {
        "present_count": len(found),
        "present_phases": sorted(found),
        "missing_count": len(expected - found),
        "missing_phases": sorted(expected - found),
    }


def collect_only() -> dict[str, Any]:
    command = [sys.executable, "-m", "pytest", "--collect-only", "-q"]
    timeout = int(os.environ.get("QRDS_PHASE186_COLLECT_TIMEOUT_SECONDS", "120"))
    started = time.perf_counter()

    try:
        result = subprocess.run(
            command,
            cwd=ROOT,
            env=os.environ.copy(),
            text=True,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            check=False,
        )

        status = "PASS" if result.returncode == 0 else "FAILED_DIAGNOSTIC_CAPTURED"

        return {
            "status": status,
            "return_code": result.returncode,
            "timed_out": False,
            "timeout_seconds": timeout,
            "duration_seconds": round(time.perf_counter() - started, 3),
            "stdout_tail": result.stdout.splitlines()[-120:],
            "stderr_tail": result.stderr.splitlines()[-120:],
        }

    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout.decode("utf-8", "replace") if isinstance(exc.stdout, bytes) else (exc.stdout or "")
        stderr = exc.stderr.decode("utf-8", "replace") if isinstance(exc.stderr, bytes) else (exc.stderr or "")

        return {
            "status": "TIMEOUT_DIAGNOSTIC_CAPTURED",
            "return_code": None,
            "timed_out": True,
            "timeout_seconds": timeout,
            "duration_seconds": round(time.perf_counter() - started, 3),
            "stdout_tail": stdout.splitlines()[-120:],
            "stderr_tail": stderr.splitlines()[-120:],
        }

    except Exception as exc:
        return {
            "status": "EXECUTION_ERROR_NEEDS_REVIEW",
            "return_code": None,
            "timed_out": False,
            "timeout_seconds": timeout,
            "duration_seconds": round(time.perf_counter() - started, 3),
            "stdout_tail": [],
            "stderr_tail": [f"{type(exc).__name__}: {exc}"],
        }


def main() -> int:
    test_files = files(ROOT / "tests", "test_*.py")
    script_files = files(ROOT / "src/crypto_decision_lab/scripts", "phase*.py")
    doc_files = files(ROOT / "docs", "*phase*.md")
    artifact_files = files(ROOT / "artifacts", "*.json")

    collect = collect_only()
    needs_review = (
        collect["status"] == "EXECUTION_ERROR_NEEDS_REVIEW"
        or not test_files
        or not artifact_files
    )

    if needs_review:
        phase_status = "NEEDS_REVIEW"
    elif collect["status"] == "PASS":
        phase_status = "READY_RESEARCH_ONLY"
    else:
        phase_status = "READY_RESEARCH_ONLY_WITH_FINDINGS"

    payload = {
        "schema_version": "1.0.0",
        "phase": 186,
        "phase_name": "TEST_INVENTORY_RESEARCH_ONLY",
        "gate": GATE,
        "phase_status": phase_status,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "research_only": True,
        "descriptive_only": True,
        "valid_for_decision": False,
        "approval_effect": "NONE_RESEARCH_ONLY",
        "full_suite_status": "SKIPPED_LOCAL_ECONOMICAL",
        "scope": {
            "audit_phase_start": 0,
            "audit_phase_end": 185,
            "suite_execution": "COLLECT_ONLY",
            "full_pytest_suite_executed": False,
            "new_feature_created": False,
            "canonical_dataset_modified": False,
        },
        "locks": LOCKS,
        "pytest_collect_only": collect,
        "inventory": {
            "test_files": len(test_files),
            "phase_scripts": len(script_files),
            "phase_documents": len(doc_files),
            "artifact_json_files": len(artifact_files),
        },
        "phase_coverage_0_185": {
            "tests": phase_coverage(test_files),
            "scripts": phase_coverage(script_files),
            "documents": phase_coverage(doc_files),
            "artifacts": phase_coverage(artifact_files),
        },
        "findings": [
            {
                "severity": (
                    "INFO" if collect["status"] == "PASS"
                    else "NEEDS_REVIEW" if needs_review
                    else "WARNING"
                ),
                "code": collect["status"],
                "message": (
                    "pytest collect-only concluÃ­do."
                    if collect["status"] == "PASS"
                    else "DiagnÃ³stico capturado; nenhuma correÃ§Ã£o automÃ¡tica foi aplicada."
                ),
            }
        ],
        "next_phase_candidate": "PHASE187_ARTIFACT_INTEGRITY_SCANNER_0_185",
        "next_phase_blocked_by_needs_review": needs_review,
    }

    assert payload["locks"]["promotion_allowed"] is False
    assert payload["locks"]["decision_layer_allowed"] is False
    assert payload["locks"]["shadow_decision_allowed"] is False
    assert payload["locks"]["canonical_data_writes"] == 0

    ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
    ARTIFACT.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    DOC.parent.mkdir(parents=True, exist_ok=True)
    DOC.write_text(
        f"""# Phase 186 â€” Test Inventory Research-only

## Gate

```text
{GATE}
```

## Resultado

```text
Phase status: {phase_status}
pytest collect-only: {collect["status"]}
Return code: {collect["return_code"]}
Timed out: {collect["timed_out"]}
Full suite: SKIPPED_LOCAL_ECONOMICAL
Operational: BLOCKED_RESEARCH_ONLY
Promotion allowed: False
Decision layer allowed: False
Shadow decision allowed: False
canonical_data_writes: 0
```

## InventÃ¡rio

```json
{json.dumps(payload["inventory"], indent=2, ensure_ascii=False)}
```

## Cobertura nominal 0â€“185

```json
{json.dumps(payload["phase_coverage_0_185"], indent=2, ensure_ascii=False)}
```

## SaÃ­da final da coleta

### stdout

```text
{chr(10).join(collect["stdout_tail"][-80:]) or "(vazio)"}
```

### stderr

```text
{chr(10).join(collect["stderr_tail"][-80:]) or "(vazio)"}
```

A Phase 186 nÃ£o executou a suÃ­te completa e nÃ£o gerou sinal, recomendaÃ§Ã£o,
alocaÃ§Ã£o, ordem, safe-apply ou decisÃ£o operacional.
""",
        encoding="utf-8",
    )

    print(GATE)
    print("Phase status:", phase_status)
    print("pytest collect-only:", collect["status"])
    print("Return code:", collect["return_code"])
    print("Timed out:", collect["timed_out"])
    print("Test files:", len(test_files))
    print("Artifact JSON files:", len(artifact_files))
    print("Full suite: SKIPPED_LOCAL_ECONOMICAL")
    print("Operational: BLOCKED_RESEARCH_ONLY")
    print("Promotion allowed: False")
    print("Decision layer allowed: False")
    print("Shadow decision allowed: False")
    print("canonical_data_writes: 0")

    if collect["status"] != "PASS":
        print("")
        print("=== COLLECT STDOUT TAIL ===")
        print("\n".join(collect["stdout_tail"][-80:]) or "(vazio)")
        print("")
        print("=== COLLECT STDERR TAIL ===")
        print("\n".join(collect["stderr_tail"][-80:]) or "(vazio)")

    return 2 if needs_review else 0


if __name__ == "__main__":
    raise SystemExit(main())
