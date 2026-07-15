from __future__ import annotations

import json
import math
import statistics
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path
from typing import Any, Iterable, Sequence

from crypto_decision_lab.scripts.phase301_305_evidence_v2_common import (
    LOCKS,
    REQUIRED_PORTAL_HEADINGS,
    ROOT,
    base_payload,
    fingerprint,
    read_csv_gz,
    read_json,
    render_simple_portal,
    sha256_file,
    to_float,
    validate_locks,
    write_json,
    write_text,
)

BASELINE_PHASE305_HEAD = "a869823eadca82f5548bf59faa7f47b9c7bbe16c"


def validate_phase(payload: dict[str, Any], phase: int) -> None:
    if payload.get("phase") != phase:
        raise RuntimeError(f"Expected Phase {phase} artifact, got {payload.get('phase')}.")
    locks = payload.get("locks")
    if not isinstance(locks, dict):
        raise RuntimeError(f"Phase {phase} artifact has no permanent lock contract.")
    validate_locks(locks)
    if payload.get("historical_result_authorizes_execution") is not False:
        raise RuntimeError(f"Phase {phase} artifact weakens historical execution lock.")


def artifact_identity(path: Path, payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "phase": payload.get("phase"),
        "path": path.relative_to(ROOT).as_posix(),
        "sha256": sha256_file(path),
        "artifact_fingerprint": payload.get("artifact_fingerprint"),
        "gate": payload.get("gate"),
    }


def normalized_entropy(values: Sequence[str]) -> float:
    if not values:
        return 0.0
    counts = Counter(values)
    if len(counts) <= 1:
        return 0.0
    total = len(values)
    entropy = -sum(
        (count / total) * math.log(count / total)
        for count in counts.values()
        if count
    )
    return entropy / math.log(len(counts))


def longest_run(values: Sequence[str], target: str) -> int:
    best = 0
    current = 0
    for value in values:
        if value == target:
            current += 1
            best = max(best, current)
        else:
            current = 0
    return best


def pearson(left: Sequence[float], right: Sequence[float]) -> float:
    if len(left) != len(right):
        raise ValueError("Pearson vectors must have equal length.")
    if len(left) < 2:
        return 0.0
    mean_left = statistics.mean(left)
    mean_right = statistics.mean(right)
    centered_left = [value - mean_left for value in left]
    centered_right = [value - mean_right for value in right]
    denom_left = math.sqrt(sum(value * value for value in centered_left))
    denom_right = math.sqrt(sum(value * value for value in centered_right))
    if denom_left == 0 or denom_right == 0:
        return 1.0 if list(left) == list(right) else 0.0
    return sum(a * b for a, b in zip(centered_left, centered_right)) / (
        denom_left * denom_right
    )


def quantile(values: Sequence[float], probability: float) -> float:
    sample = sorted(float(value) for value in values if math.isfinite(float(value)))
    if not sample:
        raise ValueError("Cannot compute a quantile from an empty sample.")
    if not 0 <= probability <= 1:
        raise ValueError("Probability must be between zero and one.")
    if len(sample) == 1:
        return sample[0]
    position = (len(sample) - 1) * probability
    lower = int(math.floor(position))
    upper = int(math.ceil(position))
    if lower == upper:
        return sample[lower]
    weight = position - lower
    return sample[lower] * (1.0 - weight) + sample[upper] * weight


def money_brl(value: float) -> str:
    sign = "-" if value < 0 else ""
    absolute = abs(value)
    return f"R$ {sign}{absolute:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def parse_junit(path: Path) -> dict[str, int | bool | str]:
    if not path.exists():
        raise RuntimeError(f"JUnit file does not exist: {path}")
    root = ET.parse(path).getroot()
    suites: list[ET.Element]
    if root.tag == "testsuite":
        suites = [root]
    elif root.tag == "testsuites":
        suites = list(root.findall("testsuite"))
    else:
        suites = list(root.findall(".//testsuite"))
    if not suites:
        raise RuntimeError(f"No testsuite element found in {path}.")
    totals = {"tests": 0, "failures": 0, "errors": 0, "skipped": 0}
    for suite in suites:
        for key in totals:
            totals[key] += int(float(suite.attrib.get(key, "0")))
    return {
        **totals,
        "passed": totals["tests"] > 0
        and totals["failures"] == 0
        and totals["errors"] == 0,
        "path": path.relative_to(ROOT).as_posix(),
        "sha256": sha256_file(path),
    }


def gate_record(
    gate_id: str,
    label: str,
    passed: bool,
    evidence: Any,
    failure_code: str,
) -> dict[str, Any]:
    return {
        "gate_id": gate_id,
        "label": label,
        "passed": bool(passed),
        "evidence": evidence,
        "failure_code": None if passed else failure_code,
        "waiver_allowed": False,
    }


def require_portal_headings(path: Path) -> None:
    text = path.read_text(encoding="utf-8-sig")
    missing = [heading for heading in REQUIRED_PORTAL_HEADINGS if heading not in text]
    if missing:
        raise RuntimeError(f"Portal is missing required headings: {missing}")
    if "VOCE ESTA AQUI" not in text:
        raise RuntimeError("Portal is missing VOCE ESTA AQUI visual marker.")


def write_phase_summary(
    path: Path,
    *,
    title: str,
    gate: str,
    bullets: Iterable[str],
) -> None:
    body = "\n".join(f"- {item}" for item in bullets)
    write_text(
        path,
        f"""# {title}

Gate: `{gate}`

{body}

Permanent state: `BLOCKED_RESEARCH_ONLY` / `NO_ACTION_RESEARCH_ONLY`.
No recommendation, allocation, signal, order, private account connection or
capital use is authorized.
""",
    )


__all__ = [
    "BASELINE_PHASE305_HEAD",
    "LOCKS",
    "REQUIRED_PORTAL_HEADINGS",
    "ROOT",
    "artifact_identity",
    "base_payload",
    "fingerprint",
    "gate_record",
    "longest_run",
    "money_brl",
    "normalized_entropy",
    "parse_junit",
    "pearson",
    "quantile",
    "read_csv_gz",
    "read_json",
    "render_simple_portal",
    "require_portal_headings",
    "sha256_file",
    "to_float",
    "validate_phase",
    "write_json",
    "write_phase_summary",
    "write_text",
]
