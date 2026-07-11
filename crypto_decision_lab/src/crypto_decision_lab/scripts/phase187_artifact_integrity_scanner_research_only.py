from __future__ import annotations

import hashlib
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
ARTIFACT = (
    ROOT
    / "artifacts"
    / "phase187_artifact_integrity_scanner_research_only"
    / "phase187_artifact_integrity_scanner.json"
)
DOC = (
    ROOT
    / "docs"
    / "reports"
    / "journal_replay"
    / "phase187_artifact_integrity_scanner_summary.md"
)

GATE = "PHASE187_ARTIFACT_INTEGRITY_SCANNER_RESEARCH_ONLY_READY_RESEARCH_ONLY"
TARGET_START = 0
TARGET_END = 185

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

EXPECTED_IF_PRESENT = {
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
    "valid_for_decision": False,
    "descriptive_only": True,
    "approval_effect": "NONE_RESEARCH_ONLY",
}


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalize_phase(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.strip().isdigit():
        return int(value.strip())
    return None


def phase_from_path(path: Path) -> int | None:
    matches = re.findall(
        r"phase[_-]?0*(\d{1,3})(?!\d)",
        rel(path),
        flags=re.IGNORECASE,
    )
    if not matches:
        return None
    return int(matches[-1])


def observed_contract_values(payload: dict[str, Any]) -> dict[str, Any]:
    observed: dict[str, Any] = {}

    locks = payload.get("locks")
    if isinstance(locks, dict):
        for key in EXPECTED_IF_PRESENT:
            if key in locks:
                observed[key] = locks[key]

    for key in EXPECTED_IF_PRESENT:
        if key in payload:
            observed[key] = payload[key]

    return observed


def finding(
    severity: str,
    code: str,
    path: Path,
    message: str,
) -> dict[str, str]:
    return {
        "severity": severity,
        "code": code,
        "path": rel(path),
        "message": message,
    }


def scan_artifacts() -> dict[str, Any]:
    artifacts_root = ROOT / "artifacts"
    all_json = sorted(
        (
            path
            for path in artifacts_root.rglob("*.json")
            if path.is_file()
            and "phase187_artifact_integrity_scanner_research_only"
            not in path.parts
        ),
        key=lambda item: rel(item).lower(),
    )

    target_records: list[dict[str, Any]] = []
    excluded_records: list[dict[str, Any]] = []
    findings: list[dict[str, str]] = []
    contract_coverage: Counter[str] = Counter()
    phase_to_paths: dict[int, list[str]] = defaultdict(list)

    parsed_target_count = 0

    for path in all_json:
        path_phase = phase_from_path(path)

        try:
            payload = json.loads(path.read_text(encoding="utf-8-sig"))
        except Exception as exc:
            if path_phase is not None and TARGET_START <= path_phase <= TARGET_END:
                findings.append(
                    finding(
                        "ERROR",
                        "JSON_PARSE_ERROR",
                        path,
                        f"{type(exc).__name__}: {exc}",
                    )
                )
                target_records.append(
                    {
                        "path": rel(path),
                        "phase": path_phase,
                        "parsed": False,
                        "size_bytes": path.stat().st_size,
                        "sha256": sha256(path),
                    }
                )
            else:
                excluded_records.append(
                    {
                        "path": rel(path),
                        "reason": "UNPARSEABLE_OUTSIDE_TARGET_OR_PHASE_UNKNOWN",
                    }
                )
            continue

        explicit_phase = (
            normalize_phase(payload.get("phase"))
            if isinstance(payload, dict)
            else None
        )
        effective_phase = explicit_phase if explicit_phase is not None else path_phase

        if effective_phase is None or not (TARGET_START <= effective_phase <= TARGET_END):
            excluded_records.append(
                {
                    "path": rel(path),
                    "reason": "OUTSIDE_TARGET_OR_PHASE_UNKNOWN",
                    "explicit_phase": explicit_phase,
                    "path_phase": path_phase,
                }
            )
            continue

        parsed_target_count += 1
        phase_to_paths[effective_phase].append(rel(path))

        record: dict[str, Any] = {
            "path": rel(path),
            "phase": effective_phase,
            "explicit_phase": explicit_phase,
            "path_phase": path_phase,
            "parsed": True,
            "json_root_type": type(payload).__name__,
            "size_bytes": path.stat().st_size,
            "sha256": sha256(path),
        }

        if not isinstance(payload, dict):
            findings.append(
                finding(
                    "ERROR",
                    "JSON_ROOT_NOT_OBJECT",
                    path,
                    f"Expected object, found {type(payload).__name__}.",
                )
            )
            target_records.append(record)
            continue

        if (
            explicit_phase is not None
            and path_phase is not None
            and explicit_phase != path_phase
        ):
            findings.append(
                finding(
                    "ERROR",
                    "PHASE_PATH_MISMATCH",
                    path,
                    f"Payload phase {explicit_phase} differs from path phase {path_phase}.",
                )
            )

        locks_value = payload.get("locks")
        if "locks" in payload and not isinstance(locks_value, dict):
            findings.append(
                finding(
                    "ERROR",
                    "LOCKS_NOT_OBJECT",
                    path,
                    f"locks must be an object, found {type(locks_value).__name__}.",
                )
            )

        observed = observed_contract_values(payload)
        record["observed_contract_keys"] = sorted(observed)

        for key, value in observed.items():
            contract_coverage[key] += 1
            expected = EXPECTED_IF_PRESENT[key]
            if value != expected:
                findings.append(
                    finding(
                        "ERROR",
                        "RESEARCH_ONLY_CONTRACT_VIOLATION",
                        path,
                        f"{key}={value!r}; expected {expected!r}.",
                    )
                )

        phase_status = payload.get("phase_status")
        if isinstance(phase_status, str) and phase_status.upper() == "NEEDS_REVIEW":
            findings.append(
                finding(
                    "ERROR",
                    "HISTORICAL_ARTIFACT_NEEDS_REVIEW",
                    path,
                    "Artifact phase_status is NEEDS_REVIEW.",
                )
            )

        target_records.append(record)

    finding_counts = Counter(item["code"] for item in findings)
    severity_counts = Counter(item["severity"] for item in findings)
    error_count = severity_counts.get("ERROR", 0)

    if error_count:
        integrity_status = "NEEDS_REVIEW"
        phase_status = "NEEDS_REVIEW"
    else:
        integrity_status = "ARTIFACT_INTEGRITY_READY_RESEARCH_ONLY"
        phase_status = "READY_RESEARCH_ONLY"

    present_phases = sorted(phase_to_paths)
    expected_phases = set(range(TARGET_START, TARGET_END + 1))

    return {
        "all_json_files_discovered": len(all_json),
        "target_artifact_files": len(target_records),
        "parsed_target_artifact_files": parsed_target_count,
        "excluded_json_files": len(excluded_records),
        "present_phase_count": len(present_phases),
        "present_phases": present_phases,
        "phases_without_artifact": sorted(expected_phases - set(present_phases)),
        "phase_to_artifact_count": {
            str(phase): len(paths)
            for phase, paths in sorted(phase_to_paths.items())
        },
        "phases_with_multiple_artifacts": {
            str(phase): paths
            for phase, paths in sorted(phase_to_paths.items())
            if len(paths) > 1
        },
        "contract_key_coverage": dict(sorted(contract_coverage.items())),
        "severity_counts": dict(sorted(severity_counts.items())),
        "finding_code_counts": dict(sorted(finding_counts.items())),
        "findings": findings,
        "target_records": target_records,
        "excluded_records": excluded_records,
        "integrity_status": integrity_status,
        "phase_status": phase_status,
    }


def write_doc(payload: dict[str, Any]) -> None:
    scan = payload["artifact_scan"]
    findings_preview = scan["findings"][:50]

    DOC.parent.mkdir(parents=True, exist_ok=True)
    DOC.write_text(
        f"""# Phase 187 â€” Artifact Integrity Scanner 0â€“185

## Gate

```text
{payload["gate"]}
```

## Result

```text
Phase status: {payload["phase_status"]}
Integrity status: {scan["integrity_status"]}
JSON discovered: {scan["all_json_files_discovered"]}
Target artifacts 0-185: {scan["target_artifact_files"]}
Parsed target artifacts: {scan["parsed_target_artifact_files"]}
Integrity errors: {scan["severity_counts"].get("ERROR", 0)}
Full suite: SKIPPED_LOCAL_ECONOMICAL
Operational: BLOCKED_RESEARCH_ONLY
Promotion allowed: False
Decision layer allowed: False
Shadow decision allowed: False
canonical_data_writes: 0
```

## Method

The scanner reads existing JSON artifacts directly. It does not rebuild prior
phases and does not run the full pytest suite.

Hard integrity checks:

- JSON parseability;
- JSON object root;
- explicit phase versus path phase consistency;
- research-only locks when those fields are present;
- historical `NEEDS_REVIEW` status.

Missing legacy fields are recorded through coverage counts and are not treated
as integrity failures by themselves.

## Contract coverage

```json
{json.dumps(scan["contract_key_coverage"], indent=2, ensure_ascii=False)}
```

## Finding counts

```json
{json.dumps(scan["finding_code_counts"], indent=2, ensure_ascii=False)}
```

## Findings preview

```json
{json.dumps(findings_preview, indent=2, ensure_ascii=False)}
```

## Restrictions

```text
approval_effect: NONE_RESEARCH_ONLY
descriptive_only: True
valid_for_decision: False
full_suite_status: SKIPPED_LOCAL_ECONOMICAL
```

No trading signal, recommendation, allocation, order payload, safe-apply,
operational decision, or canonical data write was generated.
""",
        encoding="utf-8",
    )


def main() -> int:
    scan = scan_artifacts()

    payload = {
        "schema_version": "1.0.0",
        "phase": 187,
        "phase_name": "ARTIFACT_INTEGRITY_SCANNER_RESEARCH_ONLY",
        "gate": GATE,
        "phase_status": scan["phase_status"],
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "research_only": True,
        "descriptive_only": True,
        "valid_for_decision": False,
        "approval_effect": "NONE_RESEARCH_ONLY",
        "full_suite_status": "SKIPPED_LOCAL_ECONOMICAL",
        "scope": {
            "audit_phase_start": TARGET_START,
            "audit_phase_end": TARGET_END,
            "reads_existing_artifacts_only": True,
            "rebuilds_prior_phases": False,
            "full_pytest_suite_executed": False,
            "canonical_dataset_modified": False,
        },
        "locks": LOCKS,
        "artifact_scan": scan,
        "next_phase_candidate": "PHASE188_CROSS_PHASE_DEPENDENCY_AUDIT_0_185",
        "next_phase_blocked_by_needs_review": scan["phase_status"] == "NEEDS_REVIEW",
    }

    assert payload["locks"]["promotion_allowed"] is False
    assert payload["locks"]["decision_layer_allowed"] is False
    assert payload["locks"]["shadow_decision_allowed"] is False
    assert payload["locks"]["canonical_data_writes"] == 0

    ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
    ARTIFACT.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    write_doc(payload)

    print(GATE)
    print("Phase status:", payload["phase_status"])
    print("Integrity status:", scan["integrity_status"])
    print("JSON discovered:", scan["all_json_files_discovered"])
    print("Target artifacts 0-185:", scan["target_artifact_files"])
    print("Parsed target artifacts:", scan["parsed_target_artifact_files"])
    print("Present phases:", scan["present_phase_count"])
    print("Integrity errors:", scan["severity_counts"].get("ERROR", 0))
    print("Full suite: SKIPPED_LOCAL_ECONOMICAL")
    print("Operational: BLOCKED_RESEARCH_ONLY")
    print("Promotion allowed: False")
    print("Decision layer allowed: False")
    print("Shadow decision allowed: False")
    print("canonical_data_writes: 0")

    if scan["findings"]:
        print("")
        print("=== FINDINGS ===")
        for item in scan["findings"][:100]:
            print(
                f'{item["severity"]} | {item["code"]} | '
                f'{item["path"]} | {item["message"]}'
            )

    return 2 if payload["phase_status"] == "NEEDS_REVIEW" else 0


if __name__ == "__main__":
    raise SystemExit(main())
