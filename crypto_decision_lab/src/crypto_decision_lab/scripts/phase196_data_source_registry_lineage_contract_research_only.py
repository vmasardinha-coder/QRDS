from __future__ import annotations

import argparse
import hashlib
import json
import mimetypes
import subprocess
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[3]

DEFAULT_SCAN_ROOTS = (
    Path("data"),
    Path("tests/fixtures"),
)

LOCKS = {
    "operational_status": "BLOCKED_RESEARCH_ONLY",
    "promotion_allowed": False,
    "shadow_decision_allowed": False,
    "decision_layer_allowed": False,
    "operational_decision_allowed": False,
    "safe_apply_allowed": False,
    "trading_signal_generated": False,
    "recommendation_generated": False,
    "allocation_generated": False,
    "orders_generated": False,
    "real_orders_generated": False,
    "real_capital_used": False,
    "authenticated_connection_used": False,
    "canonical_data_writes": 0,
}

FORMAT_CLASSES = {
    ".csv": "TABULAR_TEXT",
    ".tsv": "TABULAR_TEXT",
    ".json": "STRUCTURED_TEXT",
    ".jsonl": "STRUCTURED_TEXT",
    ".ndjson": "STRUCTURED_TEXT",
    ".yaml": "STRUCTURED_TEXT",
    ".yml": "STRUCTURED_TEXT",
    ".parquet": "TABULAR_BINARY",
    ".feather": "TABULAR_BINARY",
    ".arrow": "TABULAR_BINARY",
    ".pkl": "PYTHON_BINARY",
    ".pickle": "PYTHON_BINARY",
    ".txt": "TEXT",
    ".md": "TEXT",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def display_path(path: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return resolved.as_posix()


def lineage_uri(path: Path) -> str:
    displayed = display_path(path)
    if not Path(displayed).is_absolute():
        return f"repo://{displayed}"
    return f"file://{displayed}"


def source_role(path: Path) -> str:
    parts = {part.lower() for part in path.parts}
    if "fixtures" in parts:
        return "TEST_FIXTURE"
    if "data" in parts:
        return "RESEARCH_INPUT"
    return "DISCOVERED_FILE"


def format_class(path: Path) -> str:
    suffix = path.suffix.lower()
    return FORMAT_CLASSES.get(suffix, "UNKNOWN")


def git_tracked_files() -> set[str]:
    result = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=ROOT,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        return set()

    decoded = result.stdout.decode(
        "utf-8",
        errors="surrogateescape",
    )
    return {
        item.replace("\\", "/")
        for item in decoded.split("\0")
        if item
    }


def iter_scan_files(root: Path) -> Iterable[Path]:
    if root.is_file():
        yield root
        return

    for candidate in sorted(root.rglob("*")):
        if candidate.is_file() or candidate.is_symlink():
            yield candidate


def normalize_scan_roots(
    scan_roots: Iterable[Path],
) -> list[Path]:
    normalized: list[Path] = []
    seen: set[str] = set()

    for raw_root in scan_roots:
        candidate = raw_root
        if not candidate.is_absolute():
            candidate = ROOT / candidate
        candidate = candidate.resolve()

        key = candidate.as_posix().lower()
        if key in seen:
            continue

        seen.add(key)
        normalized.append(candidate)

    return normalized


def build_source_record(
    path: Path,
    tracked_files: set[str],
) -> dict[str, Any]:
    relative_or_absolute = display_path(path)
    content_hash = sha256_file(path)
    suffix = path.suffix.lower()
    mime_type, _ = mimetypes.guess_type(path.name)

    return {
        "source_id": f"src_{sha256_text(relative_or_absolute)[:16]}",
        "lineage_uri": lineage_uri(path),
        "relative_or_absolute_path": relative_or_absolute,
        "source_role": source_role(path),
        "format_class": format_class(path),
        "extension": suffix or "<none>",
        "mime_type": mime_type or "application/octet-stream",
        "size_bytes": path.stat().st_size,
        "content_sha256": content_hash,
        "content_fingerprint": content_hash[:16],
        "tracked_by_git": relative_or_absolute in tracked_files,
        "provenance_type": "FILE_SNAPSHOT",
        "read_only_evidence": True,
        "canonical_write_allowed": False,
        "authenticated_connection_used": False,
        "lineage_parent_ids": [],
        "timezone_contract": "UTC_REQUIRED_WHEN_TEMPORAL",
        "timestamp_semantics_contract": (
            "EXPLICIT_EVENT_OR_OBSERVATION_TIME_REQUIRED"
        ),
        "freshness_contract": "AUDITED_IN_PHASE_197",
        "quality_contract": "AUDITED_IN_PHASE_198",
        "reconciliation_contract": "AUDITED_IN_PHASE_199",
    }


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    rows = []

    for source in payload["sources"][:100]:
        rows.append(
            "| `{source_id}` | `{source_role}` | `{format_class}` | "
            "{size_bytes} | `{content_fingerprint}` | "
            "`{relative_or_absolute_path}` |".format(**source)
        )

    if not rows:
        rows.append(
            "| _none_ | _none_ | _none_ | 0 | _none_ | "
            "_No files discovered in configured roots_ |"
        )

    root_rows = []
    for root in payload["scan_roots"]:
        root_rows.append(
            "| `{path}` | `{status}` | {files_discovered} |".format(
                **root
            )
        )

    duplicate_lines = []
    for group in payload["duplicate_content_groups"]:
        duplicate_lines.append(
            "- `{}`: {}".format(
                group["content_sha256"],
                ", ".join(
                    f"`{path}`" for path in group["paths"]
                ),
            )
        )

    if not duplicate_lines:
        duplicate_lines.append("- No duplicate content groups detected.")

    return "\n".join(
        [
            "# Phase 196 — Data Source Registry + Lineage Contract",
            "",
            "**Status:** `PASS_RESEARCH_ONLY`",
            "",
            "## Purpose",
            "",
            "Create a deterministic, read-only registry of discovered "
            "research data and fixture files. Each source receives a "
            "stable identifier, content hash and lineage contract.",
            "",
            "This phase does not validate data trust, freshness, anomaly "
            "absence, economic edge or operational readiness.",
            "",
            "## Summary",
            "",
            f"- Scan roots: `{summary['scan_root_count']}`",
            f"- Existing roots: `{summary['existing_root_count']}`",
            f"- Missing roots: `{summary['missing_root_count']}`",
            f"- Discovered files: `{summary['source_count']}`",
            f"- Verified SHA256 hashes: `{summary['hashes_verified']}`",
            f"- Empty files: `{summary['empty_file_count']}`",
            f"- Symlinks skipped: `{summary['symlink_skipped_count']}`",
            (
                "- Duplicate-content groups: "
                f"`{summary['duplicate_content_group_count']}`"
            ),
            "",
            "## Scan roots",
            "",
            "| Root | Status | Files discovered |",
            "|---|---|---:|",
            *root_rows,
            "",
            "## Registered sources",
            "",
            "| Source ID | Role | Format | Bytes | Fingerprint | Path |",
            "|---|---|---|---:|---|---|",
            *rows,
            "",
            "## Duplicate content evidence",
            "",
            *duplicate_lines,
            "",
            "## Lineage contract",
            "",
            "- Content SHA256 is mandatory.",
            "- Inputs are treated as read-only evidence.",
            "- Temporal datasets must use explicit timestamps.",
            "- UTC is required when temporal semantics apply.",
            "- Freshness is audited in Phase 197.",
            "- Data anomalies are audited in Phase 198.",
            "- Cross-source reconciliation is audited in Phase 199.",
            "- Canonical writes remain prohibited.",
            "",
            "## Safety",
            "",
            "```text",
            "operational_status: BLOCKED_RESEARCH_ONLY",
            "data_trust_validated: False",
            "shadow_decision_allowed: False",
            "decision_layer_allowed: False",
            "promotion_allowed: False",
            "canonical_data_writes: 0",
            "```",
            "",
            "## Next",
            "",
            "`PHASE_197_TIMESTAMP_TIMEZONE_FRESHNESS_POLICY_RESEARCH_ONLY`",
            "",
        ]
    )


def build_phase196(
    *,
    scan_roots: Iterable[Path],
    output_dir: Path,
    documentation_path: Path | None = None,
) -> dict[str, Any]:
    roots = normalize_scan_roots(scan_roots)
    tracked_files = git_tracked_files()

    sources: list[dict[str, Any]] = []
    root_evidence: list[dict[str, Any]] = []
    symlink_skipped: list[str] = []

    for root in roots:
        root_record = {
            "path": display_path(root),
            "status": "MISSING",
            "files_discovered": 0,
        }

        if not root.exists():
            root_evidence.append(root_record)
            continue

        root_record["status"] = "PRESENT"

        for candidate in iter_scan_files(root):
            if candidate.is_symlink():
                symlink_skipped.append(display_path(candidate))
                continue

            record = build_source_record(candidate, tracked_files)
            sources.append(record)
            root_record["files_discovered"] += 1

        root_evidence.append(root_record)

    sources.sort(
        key=lambda item: item["relative_or_absolute_path"]
    )

    hash_groups: dict[str, list[str]] = defaultdict(list)
    for source in sources:
        hash_groups[source["content_sha256"]].append(
            source["relative_or_absolute_path"]
        )

    duplicate_content_groups = [
        {
            "content_sha256": content_hash,
            "paths": sorted(paths),
            "count": len(paths),
        }
        for content_hash, paths in sorted(hash_groups.items())
        if len(paths) > 1
    ]

    empty_files = [
        source["relative_or_absolute_path"]
        for source in sources
        if source["size_bytes"] == 0
    ]

    payload: dict[str, Any] = {
        "schema": "qrds.phase196.data_source_registry_lineage.v1",
        "phase": 196,
        "phase_status": "PASS_RESEARCH_ONLY",
        "registry_status": (
            "DATA_SOURCE_REGISTRY_READY_RESEARCH_ONLY"
        ),
        "generated_at": utc_now(),
        "repository_root": ROOT.as_posix(),
        "scan_roots": root_evidence,
        "sources": sources,
        "duplicate_content_groups": duplicate_content_groups,
        "empty_files": empty_files,
        "symlinks_skipped": sorted(symlink_skipped),
        "summary": {
            "scan_root_count": len(root_evidence),
            "existing_root_count": sum(
                root["status"] == "PRESENT"
                for root in root_evidence
            ),
            "missing_root_count": sum(
                root["status"] == "MISSING"
                for root in root_evidence
            ),
            "source_count": len(sources),
            "hashes_verified": len(sources),
            "empty_file_count": len(empty_files),
            "symlink_skipped_count": len(symlink_skipped),
            "duplicate_content_group_count": len(
                duplicate_content_groups
            ),
        },
        "lineage_contract": {
            "stable_source_id_required": True,
            "content_sha256_required": True,
            "provenance_required": True,
            "explicit_timestamp_semantics_required": True,
            "timezone_policy": "UTC_REQUIRED_WHEN_TEMPORAL",
            "input_mutation_allowed": False,
            "canonical_write_allowed": False,
            "authenticated_connection_allowed": False,
            "freshness_audit_phase": 197,
            "anomaly_audit_phase": 198,
            "reconciliation_phase": 199,
        },
        "registry_ready": True,
        "data_trust_validated": False,
        "freshness_validated": False,
        "anomaly_free_validated": False,
        "sources_reconciled": False,
        "valid_for_decision": False,
        "operational_use_allowed": False,
        "production_trading_ready": False,
        "approval_effect": "NONE_RESEARCH_ONLY",
        "next_stage": (
            "PHASE_197_TIMESTAMP_TIMEZONE_FRESHNESS_POLICY_"
            "RESEARCH_ONLY"
        ),
        "locks": LOCKS,
    }

    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = (
        output_dir
        / "phase196_data_source_registry_lineage_contract.json"
    )
    output_path.write_text(
        json.dumps(
            payload,
            indent=2,
            sort_keys=True,
            ensure_ascii=True,
        )
        + "\n",
        encoding="utf-8",
    )

    if documentation_path is not None:
        documentation_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        documentation_path.write_text(
            render_markdown(payload),
            encoding="utf-8",
        )

    return payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build the Phase 196 read-only data source registry "
            "and lineage contract."
        )
    )
    parser.add_argument(
        "--scan-root",
        action="append",
        type=Path,
        default=[],
        help=(
            "Root to scan. May be repeated. Defaults to data and "
            "tests/fixtures."
        ),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
    )
    parser.add_argument(
        "--documentation-path",
        type=Path,
        required=True,
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    roots = args.scan_root or list(DEFAULT_SCAN_ROOTS)

    payload = build_phase196(
        scan_roots=roots,
        output_dir=args.output_dir,
        documentation_path=args.documentation_path,
    )

    summary = payload["summary"]

    print("PHASE196_DATA_SOURCE_REGISTRY: PASS")
    print("Scan roots:", summary["scan_root_count"])
    print("Existing roots:", summary["existing_root_count"])
    print("Missing roots:", summary["missing_root_count"])
    print("Discovered files:", summary["source_count"])
    print("Hashes verified:", summary["hashes_verified"])
    print("Empty files:", summary["empty_file_count"])
    print(
        "Duplicate content groups:",
        summary["duplicate_content_group_count"],
    )
    print(
        "Operational:",
        payload["locks"]["operational_status"],
    )
    print(
        "Data trust validated:",
        payload["data_trust_validated"],
    )
    print(
        "Canonical data writes:",
        payload["locks"]["canonical_data_writes"],
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
