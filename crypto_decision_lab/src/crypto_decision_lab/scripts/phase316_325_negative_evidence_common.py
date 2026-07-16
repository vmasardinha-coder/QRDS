from __future__ import annotations

import csv
import gzip
import hashlib
import json
import math
import statistics
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Iterable, Sequence

from crypto_decision_lab.scripts.phase306_315_stability_common import (
    LOCKS,
    REQUIRED_PORTAL_HEADINGS,
    ROOT,
    artifact_identity,
    base_payload,
    fingerprint,
    money_brl,
    read_json,
    render_simple_portal,
    require_portal_headings,
    sha256_file,
    validate_phase,
    write_json,
    write_phase_summary,
    write_text,
)

BASELINE_PHASE315_HEAD = "4d45d3cf996da58ec1bba2a287bbf3b5ee3ce9bc"
CLOSED_FAMILY_ID = "EVIDENCE_V2_DIRECTIONAL_24_HYPOTHESES"
PROPOSED_NEW_FAMILY_ID = "ABSTENTION_RELIABILITY_CROSS_EXCHANGE_V1"
PROPOSED_QUESTION_ID = "Q_ABSTAIN_WHEN_MARKET_DATA_DISAGREES_V1"


def canonical_hash(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def hypothesis_signature(hypothesis: dict[str, Any]) -> dict[str, Any]:
    fields = {
        key: hypothesis.get(key)
        for key in (
            "family",
            "signal",
            "feature",
            "lookback_hours",
            "holding_hours",
            "threshold",
            "direction",
            "filters",
            "cost_bps_scenarios",
        )
    }
    return {
        "hypothesis_id": hypothesis.get("hypothesis_id"),
        "canonical_fields": fields,
        "signature_sha256": canonical_hash(fields),
        "retest_policy": "PROHIBITED_UNCHANGED_OR_ALIAS",
        "waiver_allowed": False,
    }


def read_csv_gz_rows(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        raise RuntimeError(f"Dataset does not exist: {path}")
    with gzip.open(path, "rt", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def finite_float(value: Any) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def quantile(values: Sequence[float], probability: float) -> float:
    sample = sorted(float(value) for value in values if math.isfinite(float(value)))
    if not sample:
        return 0.0
    if len(sample) == 1:
        return sample[0]
    position = (len(sample) - 1) * probability
    lower = int(math.floor(position))
    upper = int(math.ceil(position))
    if lower == upper:
        return sample[lower]
    weight = position - lower
    return sample[lower] * (1.0 - weight) + sample[upper] * weight


def median_interval_ms(timestamps: Sequence[int]) -> int | None:
    ordered = sorted(set(int(value) for value in timestamps))
    deltas = [right - left for left, right in zip(ordered, ordered[1:]) if right > left]
    if not deltas:
        return None
    return int(statistics.median(deltas))


def dataset_path(payload: dict[str, Any], dataset_name: str) -> Path:
    datasets = payload.get("datasets", {})
    record = datasets.get(dataset_name)
    if not isinstance(record, dict) or not record.get("path"):
        raise RuntimeError(f"Dataset metadata missing: {dataset_name}")
    path = ROOT / str(record["path"])
    if not path.is_file():
        raise RuntimeError(f"Dataset file missing: {path}")
    expected = record.get("sha256")
    if expected and sha256_file(path) != expected:
        raise RuntimeError(f"Dataset hash mismatch: {dataset_name}")
    return path


def parse_junit(path: Path) -> dict[str, int | bool | str]:
    if not path.is_file():
        raise RuntimeError(f"JUnit file does not exist: {path}")
    root = ET.parse(path).getroot()
    suites = [root] if root.tag == "testsuite" else list(root.findall("testsuite"))
    if not suites:
        suites = list(root.findall(".//testsuite"))
    totals = {"tests": 0, "failures": 0, "errors": 0, "skipped": 0}
    for suite in suites:
        for key in totals:
            totals[key] += int(float(suite.attrib.get(key, "0") or "0"))
    return {
        **totals,
        "passed": totals["tests"] > 0 and totals["failures"] == 0 and totals["errors"] == 0,
        "path": path.relative_to(ROOT).as_posix(),
        "sha256": sha256_file(path),
    }


def prerequisite_record(gate_id: str, label: str, passed: bool, evidence: Any, failure_code: str) -> dict[str, Any]:
    return {
        "gate_id": gate_id,
        "label": label,
        "passed": bool(passed),
        "evidence": evidence,
        "failure_code": None if passed else failure_code,
        "waiver_allowed": False,
    }


def write_summary(path: Path, *, title: str, gate: str, bullets: Iterable[str]) -> None:
    write_phase_summary(path, title=title, gate=gate, bullets=bullets)


__all__ = [
    "BASELINE_PHASE315_HEAD",
    "CLOSED_FAMILY_ID",
    "LOCKS",
    "PROPOSED_NEW_FAMILY_ID",
    "PROPOSED_QUESTION_ID",
    "REQUIRED_PORTAL_HEADINGS",
    "ROOT",
    "artifact_identity",
    "base_payload",
    "canonical_hash",
    "dataset_path",
    "finite_float",
    "fingerprint",
    "hypothesis_signature",
    "median_interval_ms",
    "money_brl",
    "parse_junit",
    "prerequisite_record",
    "quantile",
    "read_csv_gz_rows",
    "read_json",
    "render_simple_portal",
    "require_portal_headings",
    "sha256_file",
    "validate_phase",
    "write_json",
    "write_summary",
    "write_text",
]
