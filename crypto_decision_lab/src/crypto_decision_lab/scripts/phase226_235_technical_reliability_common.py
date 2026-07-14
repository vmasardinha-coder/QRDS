from __future__ import annotations

import argparse
import copy
import hashlib
import importlib
import json
import os
import subprocess
import xml.etree.ElementTree as ET
from functools import lru_cache, wraps
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, MutableMapping, TypeVar

T = TypeVar("T")

OPERATIONAL_STATUS = "BLOCKED_RESEARCH_ONLY"
LOCKS: dict[str, Any] = {
    "operational_status": OPERATIONAL_STATUS,
    "data_trust_validated": False,
    "predictive_validity_established": False,
    "edge_validated": False,
    "decision_layer_allowed": False,
    "trading_signal_generated": False,
    "recommendation_generated": False,
    "allocation_generated": False,
    "promotion_allowed": False,
    "canonical_data_writes": 0,
}

REGISTRY_SPECS: tuple[tuple[str, str], ...] = (
    (
        "crypto_decision_lab.scripts."
        "phase141_replay_validity_requirement_registry_research_only",
        "build_replay_validity_requirement_registry",
    ),
    (
        "crypto_decision_lab.scripts."
        "phase146_risk_requirement_registry_research_only",
        "build_risk_requirement_registry",
    ),
    (
        "crypto_decision_lab.scripts."
        "phase151_shadow_decision_requirement_registry_research_only",
        "build_shadow_decision_requirement_registry",
    ),
    (
        "crypto_decision_lab.scripts."
        "phase156_shadow_simulation_requirement_registry_research_only",
        "build_shadow_simulation_requirement_registry",
    ),
    (
        "crypto_decision_lab.scripts."
        "phase161_shadow_evidence_replay_requirement_registry_research_only",
        "build_shadow_evidence_replay_requirement_registry",
    ),
    (
        "crypto_decision_lab.scripts."
        "phase166_shadow_score_requirement_registry_research_only",
        "build_shadow_score_requirement_registry",
    ),
    (
        "crypto_decision_lab.scripts."
        "phase171_shadow_readiness_requirement_registry_research_only",
        "build_shadow_readiness_requirement_registry",
    ),
)


def copy_on_read_lru_cache(
    maxsize: int = 16,
    typed: bool = False,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Cache an internal value and return a deep copy to each caller."""

    def decorate(function: Callable[..., T]) -> Callable[..., T]:
        cached = lru_cache(maxsize=maxsize, typed=typed)(function)

        @wraps(function)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            return copy.deepcopy(cached(*args, **kwargs))

        wrapper.cache_clear = cached.cache_clear  # type: ignore[attr-defined]
        wrapper.cache_info = cached.cache_info  # type: ignore[attr-defined]
        wrapper.cache_parameters = cached.cache_parameters  # type: ignore[attr-defined]
        wrapper.copy_on_read = True  # type: ignore[attr-defined]
        return wrapper

    return decorate


def project_root(value: str | Path | None = None) -> Path:
    if value is not None:
        return Path(value).resolve()
    return Path.cwd().resolve()


def registry_builders() -> list[Callable[..., dict[str, Any]]]:
    builders: list[Callable[..., dict[str, Any]]] = []
    for module_name, function_name in REGISTRY_SPECS:
        module = importlib.import_module(module_name)
        builders.append(getattr(module, function_name))
    return builders


def clear_registry_caches() -> None:
    for builder in registry_builders():
        builder.cache_clear()


def cache_contracts() -> list[dict[str, Any]]:
    contracts: list[dict[str, Any]] = []
    for (module_name, function_name), builder in zip(
        REGISTRY_SPECS,
        registry_builders(),
        strict=True,
    ):
        parameters = builder.cache_parameters()
        contracts.append(
            {
                "module": module_name,
                "function": function_name,
                "scope": "PROCESS_LOCAL",
                "maxsize": parameters["maxsize"],
                "typed": parameters["typed"],
                "copy_on_read": bool(
                    getattr(builder, "copy_on_read", False)
                ),
                "cache_clear_available": callable(builder.cache_clear),
                "cache_info_available": callable(builder.cache_info),
                "cache_parameters_available": callable(
                    builder.cache_parameters
                ),
            }
        )
    return contracts


def base_payload(phase: int, status: str) -> dict[str, Any]:
    return {
        "phase": phase,
        "status": status,
        "passed": False,
        "accepted_residual_risks": [
            "RARE_NATIVE_PYTHON_WINDOWS_RUNTIME_CRASH",
            "FUTURE_REGRESSION_OUTSIDE_CURRENT_BATCH_SCOPE",
        ],
        "locks": copy.deepcopy(LOCKS),
    }


def write_json(path: str | Path, payload: Mapping[str, Any]) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, output)
    return output


def write_markdown(
    path: str | Path,
    title: str,
    payload: Mapping[str, Any],
    lines: Iterable[str],
) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    body = [
        f"# {title}",
        "",
        f"- Phase: {payload['phase']}",
        f"- Status: `{payload['status']}`",
        f"- Passed: `{payload['passed']}`",
        f"- Operational: `{LOCKS['operational_status']}`",
        f"- Canonical writes: `{LOCKS['canonical_data_writes']}`",
        "",
        *list(lines),
        "",
        "## Residual risks accepted",
        "",
        "- Rare native Python/Windows runtime crashes.",
        "- Future regressions outside the current batch scope.",
        "",
        "These risks are monitored but are not batch blockers.",
        "",
    ]
    temporary = output.with_suffix(output.suffix + ".tmp")
    temporary.write_text("\n".join(body), encoding="utf-8")
    os.replace(temporary, output)
    return output


def add_standard_output_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--artifact", required=True)
    parser.add_argument("--documentation", required=True)
    parser.add_argument("--project-root")


def hash_paths(paths: Iterable[Path], root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted({item.resolve() for item in paths}):
        relative = path.relative_to(root).as_posix()
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def test_manifest(root: Path) -> list[Path]:
    return sorted(
        path
        for path in (root / "tests").rglob("test_*.py")
        if path.is_file()
    )


def parse_junit(path: str | Path) -> dict[str, Any]:
    source = Path(path)
    result: dict[str, Any] = {
        "path": source.as_posix(),
        "exists": source.is_file(),
        "parse_ok": False,
        "tests": 0,
        "failures": 0,
        "errors": 0,
        "skipped": 0,
    }
    if not source.is_file():
        return result

    try:
        xml_root = ET.parse(source).getroot()
    except (ET.ParseError, OSError) as exc:
        result["parse_error"] = str(exc)
        return result

    suites = (
        [xml_root]
        if xml_root.tag == "testsuite"
        else list(xml_root.findall("testsuite"))
    )
    result["parse_ok"] = True
    for key in ("tests", "failures", "errors", "skipped"):
        result[key] = sum(
            int(float(suite.attrib.get(key, "0")))
            for suite in suites
        )
    return result


def relevant_process_snapshot() -> dict[int, dict[str, Any]]:
    if os.name != "nt":
        return {}

    command = (
        "Get-CimInstance Win32_Process | "
        "Where-Object { "
        "($_.Name -match 'python|bash|cmd') -and "
        "($_.CommandLine -match 'pytest|http.server|qrds_') "
        "} | "
        "Select-Object ProcessId,ParentProcessId,Name,CommandLine | "
        "ConvertTo-Json -Compress"
    )
    result = subprocess.run(
        ["powershell", "-NoProfile", "-Command", command],
        capture_output=True,
        text=True,
        errors="replace",
        check=False,
    )
    if result.returncode != 0 or not result.stdout.strip():
        return {}

    payload = json.loads(result.stdout)
    rows = payload if isinstance(payload, list) else [payload]
    snapshot: dict[int, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        pid = int(row.get("ProcessId", 0) or 0)
        if pid <= 0 or pid == os.getpid():
            continue
        snapshot[pid] = row
    return snapshot


def load_json(path: str | Path) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TypeError(f"Expected JSON object: {path}")
    return payload
