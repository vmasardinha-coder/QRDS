from __future__ import annotations

import ast
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[3]
ARTIFACT = (
    ROOT
    / "artifacts"
    / "phase188_cross_phase_dependency_audit_research_only"
    / "phase188_cross_phase_dependency_audit.json"
)
DOC = (
    ROOT
    / "docs"
    / "reports"
    / "journal_replay"
    / "phase188_cross_phase_dependency_audit_summary.md"
)

GATE = "PHASE188_CROSS_PHASE_DEPENDENCY_AUDIT_RESEARCH_ONLY_READY_RESEARCH_ONLY"
TARGET_START = 0
TARGET_END = 185

PHASE_PATTERN = re.compile(r"phase[_-]?0*(\d{1,3})(?!\d)", re.IGNORECASE)

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


def phase_numbers(text: str) -> list[int]:
    numbers = {
        int(raw)
        for raw in PHASE_PATTERN.findall(text)
        if TARGET_START <= int(raw) <= TARGET_END
    }
    return sorted(numbers)


def phase_from_path(path: Path) -> int | None:
    numbers = phase_numbers(rel(path))
    if not numbers:
        return None
    return numbers[-1]


def find_files(base: Path, pattern: str) -> list[Path]:
    if not base.exists():
        return []
    return sorted(
        (
            path
            for path in base.rglob(pattern)
            if path.is_file() and "__pycache__" not in path.parts
        ),
        key=lambda path: rel(path).lower(),
    )


def finding(
    severity: str,
    code: str,
    path: str,
    message: str,
) -> dict[str, str]:
    return {
        "severity": severity,
        "code": code,
        "path": path,
        "message": message,
    }


def imported_phase_numbers(tree: ast.AST) -> list[int]:
    imported: set[int] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported.update(phase_numbers(alias.name))
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imported.update(phase_numbers(node.module))
            for alias in node.names:
                imported.update(phase_numbers(alias.name))

    return sorted(imported)


def string_phase_numbers(tree: ast.AST) -> list[int]:
    referenced: set[int] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            referenced.update(phase_numbers(node.value))

    return sorted(referenced)


def direct_phase_call_numbers(tree: ast.AST) -> list[int]:
    referenced: set[int] = set()

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue

        function = node.func
        if isinstance(function, ast.Name):
            referenced.update(phase_numbers(function.id))
        elif isinstance(function, ast.Attribute):
            referenced.update(phase_numbers(function.attr))

    return sorted(referenced)


def parse_python_file(path: Path) -> tuple[ast.AST | None, str | None]:
    try:
        source = path.read_text(encoding="utf-8-sig")
        return ast.parse(source, filename=rel(path)), None
    except Exception as exc:
        return None, f"{type(exc).__name__}: {exc}"


def build_phase_file_index(paths: Iterable[Path]) -> dict[int, list[str]]:
    index: dict[int, list[str]] = defaultdict(list)

    for path in paths:
        phase = phase_from_path(path)
        if phase is not None:
            index[phase].append(rel(path))

    return {
        phase: sorted(values)
        for phase, values in sorted(index.items())
    }


def detect_cycles(graph: dict[int, set[int]]) -> list[list[int]]:
    state: dict[int, int] = {}
    stack: list[int] = []
    cycles: set[tuple[int, ...]] = set()

    def canonical_cycle(nodes: list[int]) -> tuple[int, ...]:
        body = nodes[:-1]
        if not body:
            return tuple(nodes)

        rotations = [
            tuple(body[index:] + body[:index])
            for index in range(len(body))
        ]
        canonical = min(rotations)
        return canonical + (canonical[0],)

    def visit(node: int) -> None:
        state[node] = 1
        stack.append(node)

        for target in sorted(graph.get(node, set())):
            if target == node:
                continue

            target_state = state.get(target, 0)

            if target_state == 0:
                visit(target)
            elif target_state == 1 and target in stack:
                start = stack.index(target)
                cycle = stack[start:] + [target]
                cycles.add(canonical_cycle(cycle))

        stack.pop()
        state[node] = 2

    for node in sorted(graph):
        if state.get(node, 0) == 0:
            visit(node)

    return [list(cycle) for cycle in sorted(cycles)]


def artifact_phase_index() -> dict[int, list[str]]:
    artifacts_root = ROOT / "artifacts"
    index: dict[int, list[str]] = defaultdict(list)

    for path in find_files(artifacts_root, "*.json"):
        path_phase = phase_from_path(path)

        try:
            payload = json.loads(path.read_text(encoding="utf-8-sig"))
        except Exception:
            payload = None

        explicit_phase = None
        if isinstance(payload, dict):
            value = payload.get("phase")
            if isinstance(value, int) and not isinstance(value, bool):
                explicit_phase = value
            elif isinstance(value, str) and value.strip().isdigit():
                explicit_phase = int(value.strip())

        effective_phase = explicit_phase if explicit_phase is not None else path_phase

        if effective_phase is not None and TARGET_START <= effective_phase <= TARGET_END:
            index[effective_phase].append(rel(path))

    return {
        phase: sorted(paths)
        for phase, paths in sorted(index.items())
    }


def audit() -> dict[str, Any]:
    scripts = find_files(
        ROOT / "src" / "crypto_decision_lab" / "scripts",
        "phase*.py",
    )
    tests = find_files(ROOT / "tests", "test_phase*.py")
    documents = find_files(ROOT / "docs", "*phase*.md")

    script_index = build_phase_file_index(scripts)
    test_index = build_phase_file_index(tests)
    document_index = build_phase_file_index(documents)
    artifact_index = artifact_phase_index()

    graph: dict[int, set[int]] = defaultdict(set)
    script_records: list[dict[str, Any]] = []
    test_records: list[dict[str, Any]] = []
    findings: list[dict[str, str]] = []

    for path in scripts:
        source_phase = phase_from_path(path)
        if source_phase is None:
            continue

        tree, parse_error = parse_python_file(path)

        if parse_error is not None or tree is None:
            findings.append(
                finding(
                    "ERROR",
                    "SCRIPT_AST_PARSE_ERROR",
                    rel(path),
                    parse_error or "Unknown parse error.",
                )
            )
            script_records.append(
                {
                    "path": rel(path),
                    "phase": source_phase,
                    "parsed": False,
                    "parse_error": parse_error,
                }
            )
            continue

        imported = imported_phase_numbers(tree)
        string_refs = string_phase_numbers(tree)
        direct_calls = direct_phase_call_numbers(tree)

        dependency_targets = sorted(
            {
                target
                for target in imported
                if target != source_phase
            }
        )

        for target in dependency_targets:
            graph[source_phase].add(target)

            if target > source_phase:
                findings.append(
                    finding(
                        "ERROR",
                        "FORWARD_EXECUTABLE_IMPORT",
                        rel(path),
                        f"Phase {source_phase} imports phase {target}.",
                    )
                )

            if target not in script_index:
                findings.append(
                    finding(
                        "WARNING",
                        "IMPORTED_PHASE_SCRIPT_NOT_FOUND",
                        rel(path),
                        f"Imported phase {target} has no indexed phase script.",
                    )
                )

        checkpoint_direct_imports = []
        if source_phase % 5 == 0:
            checkpoint_direct_imports = [
                target
                for target in dependency_targets
                if target < source_phase
            ]

            if checkpoint_direct_imports:
                findings.append(
                    finding(
                        "WARNING",
                        "CHECKPOINT_DIRECT_PHASE_IMPORT",
                        rel(path),
                        (
                            f"Checkpoint phase {source_phase} directly imports "
                            f"prior phases {checkpoint_direct_imports}; verify "
                            "that it reads artifacts rather than rebuilding chains."
                        ),
                    )
                )

        script_records.append(
            {
                "path": rel(path),
                "phase": source_phase,
                "parsed": True,
                "imported_phase_refs": imported,
                "executable_dependencies": dependency_targets,
                "string_phase_refs": string_refs,
                "direct_call_phase_refs": direct_calls,
                "checkpoint_direct_imports": checkpoint_direct_imports,
            }
        )

    for path in tests:
        source_phase = phase_from_path(path)
        if source_phase is None:
            continue

        tree, parse_error = parse_python_file(path)

        if parse_error is not None or tree is None:
            findings.append(
                finding(
                    "ERROR",
                    "TEST_AST_PARSE_ERROR",
                    rel(path),
                    parse_error or "Unknown parse error.",
                )
            )
            test_records.append(
                {
                    "path": rel(path),
                    "phase": source_phase,
                    "parsed": False,
                    "parse_error": parse_error,
                }
            )
            continue

        imported = imported_phase_numbers(tree)

        test_records.append(
            {
                "path": rel(path),
                "phase": source_phase,
                "parsed": True,
                "imported_phase_refs": imported,
            }
        )

    cycles = detect_cycles(graph)

    for cycle in cycles:
        findings.append(
            finding(
                "ERROR",
                "EXECUTABLE_DEPENDENCY_CYCLE",
                "phase_dependency_graph",
                " -> ".join(str(item) for item in cycle),
            )
        )

    for phase, paths in sorted(script_index.items()):
        if phase not in test_index:
            findings.append(
                finding(
                    "INFO",
                    "PHASE_WITHOUT_NAMED_TEST",
                    paths[0],
                    f"Phase {phase} has no test file indexed by phase name.",
                )
            )

        if phase not in document_index:
            findings.append(
                finding(
                    "INFO",
                    "PHASE_WITHOUT_NAMED_DOCUMENT",
                    paths[0],
                    f"Phase {phase} has no document indexed by phase name.",
                )
            )

        if phase not in artifact_index:
            findings.append(
                finding(
                    "INFO",
                    "PHASE_WITHOUT_LOCAL_ARTIFACT",
                    paths[0],
                    f"Phase {phase} has no local JSON artifact indexed.",
                )
            )

    severity_counts = Counter(item["severity"] for item in findings)
    finding_code_counts = Counter(item["code"] for item in findings)
    error_count = severity_counts.get("ERROR", 0)

    if error_count:
        phase_status = "NEEDS_REVIEW"
        dependency_status = "CROSS_PHASE_DEPENDENCY_NEEDS_REVIEW"
    elif severity_counts.get("WARNING", 0):
        phase_status = "READY_RESEARCH_ONLY_WITH_FINDINGS"
        dependency_status = "CROSS_PHASE_DEPENDENCY_READY_RESEARCH_ONLY_WITH_FINDINGS"
    else:
        phase_status = "READY_RESEARCH_ONLY"
        dependency_status = "CROSS_PHASE_DEPENDENCY_READY_RESEARCH_ONLY"

    edge_count = sum(len(targets) for targets in graph.values())
    backward_edges = sum(
        1
        for source, targets in graph.items()
        for target in targets
        if target < source
    )
    forward_edges = sum(
        1
        for source, targets in graph.items()
        for target in targets
        if target > source
    )

    return {
        "phase_status": phase_status,
        "dependency_status": dependency_status,
        "inventory": {
            "phase_script_files": len(scripts),
            "phase_test_files": len(tests),
            "phase_document_files": len(documents),
            "artifact_phases_present": len(artifact_index),
            "script_phases_present": len(script_index),
            "test_phases_present": len(test_index),
            "document_phases_present": len(document_index),
        },
        "dependency_graph": {
            "node_count": len(graph),
            "edge_count": edge_count,
            "backward_edge_count": backward_edges,
            "forward_edge_count": forward_edges,
            "cycle_count": len(cycles),
            "cycles": cycles,
            "edges": {
                str(source): sorted(targets)
                for source, targets in sorted(graph.items())
            },
        },
        "phase_file_coverage": {
            "scripts": {str(k): v for k, v in script_index.items()},
            "tests": {str(k): v for k, v in test_index.items()},
            "documents": {str(k): v for k, v in document_index.items()},
            "artifacts": {str(k): v for k, v in artifact_index.items()},
        },
        "script_records": script_records,
        "test_records": test_records,
        "severity_counts": dict(sorted(severity_counts.items())),
        "finding_code_counts": dict(sorted(finding_code_counts.items())),
        "findings": findings,
    }


def write_document(payload: dict[str, Any]) -> None:
    audit_result = payload["dependency_audit"]

    warning_preview = [
        item
        for item in audit_result["findings"]
        if item["severity"] in {"ERROR", "WARNING"}
    ][:60]

    DOC.parent.mkdir(parents=True, exist_ok=True)
    DOC.write_text(
        f"""# Phase 188 â€” Cross-Phase Dependency Audit 0â€“185

## Gate

```text
{payload["gate"]}
```

## Result

```text
Phase status: {payload["phase_status"]}
Dependency status: {audit_result["dependency_status"]}
Executable dependency edges: {audit_result["dependency_graph"]["edge_count"]}
Forward executable imports: {audit_result["dependency_graph"]["forward_edge_count"]}
Dependency cycles: {audit_result["dependency_graph"]["cycle_count"]}
Errors: {audit_result["severity_counts"].get("ERROR", 0)}
Warnings: {audit_result["severity_counts"].get("WARNING", 0)}
Full suite: SKIPPED_LOCAL_ECONOMICAL
Operational: BLOCKED_RESEARCH_ONLY
Promotion allowed: False
Decision layer allowed: False
Shadow decision allowed: False
canonical_data_writes: 0
```

## Method

This phase reads existing scripts, tests, documents, and JSON artifacts.
It does not execute or rebuild prior phases.

Executable dependencies are derived from Python AST import statements.
String references are inventoried separately and do not become hard graph edges.

Hard failures:

- Python AST parse failure;
- forward executable phase import;
- executable phase dependency cycle.

Warnings:

- imported phase without an indexed script;
- checkpoint directly importing prior phase modules.

Missing legacy tests, documents, or local artifacts are informational only.

## Inventory

```json
{json.dumps(audit_result["inventory"], indent=2, ensure_ascii=False)}
```

## Graph summary

```json
{json.dumps(audit_result["dependency_graph"], indent=2, ensure_ascii=False)}
```

## Error and warning preview

```json
{json.dumps(warning_preview, indent=2, ensure_ascii=False)}
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
    audit_result = audit()

    payload = {
        "schema_version": "1.0.0",
        "phase": 188,
        "phase_name": "CROSS_PHASE_DEPENDENCY_AUDIT_RESEARCH_ONLY",
        "gate": GATE,
        "phase_status": audit_result["phase_status"],
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "research_only": True,
        "descriptive_only": True,
        "valid_for_decision": False,
        "approval_effect": "NONE_RESEARCH_ONLY",
        "full_suite_status": "SKIPPED_LOCAL_ECONOMICAL",
        "scope": {
            "audit_phase_start": TARGET_START,
            "audit_phase_end": TARGET_END,
            "reads_existing_files_only": True,
            "executes_prior_phases": False,
            "rebuilds_prior_phases": False,
            "full_pytest_suite_executed": False,
            "canonical_dataset_modified": False,
        },
        "locks": LOCKS,
        "dependency_audit": audit_result,
        "next_phase_candidate": "PHASE189_LIGHTWEIGHT_CI_RESEARCH_ONLY",
        "next_phase_blocked_by_needs_review": (
            audit_result["phase_status"] == "NEEDS_REVIEW"
        ),
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
    write_document(payload)

    graph = audit_result["dependency_graph"]

    print(GATE)
    print("Phase status:", payload["phase_status"])
    print("Dependency status:", audit_result["dependency_status"])
    print("Phase scripts:", audit_result["inventory"]["phase_script_files"])
    print("Phase tests:", audit_result["inventory"]["phase_test_files"])
    print("Executable dependency edges:", graph["edge_count"])
    print("Forward executable imports:", graph["forward_edge_count"])
    print("Dependency cycles:", graph["cycle_count"])
    print("Errors:", audit_result["severity_counts"].get("ERROR", 0))
    print("Warnings:", audit_result["severity_counts"].get("WARNING", 0))
    print("Full suite: SKIPPED_LOCAL_ECONOMICAL")
    print("Operational: BLOCKED_RESEARCH_ONLY")
    print("Promotion allowed: False")
    print("Decision layer allowed: False")
    print("Shadow decision allowed: False")
    print("canonical_data_writes: 0")

    important = [
        item
        for item in audit_result["findings"]
        if item["severity"] in {"ERROR", "WARNING"}
    ]

    if important:
        print("")
        print("=== ERROR/WARNING FINDINGS ===")
        for item in important[:120]:
            print(
                f'{item["severity"]} | {item["code"]} | '
                f'{item["path"]} | {item["message"]}'
            )

    return 2 if payload["phase_status"] == "NEEDS_REVIEW" else 0


if __name__ == "__main__":
    raise SystemExit(main())
