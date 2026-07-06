from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

READY_GATE = "PHASE70_VALIDATION_MANIFEST_INDEX_RESEARCH_ONLY_READY_RESEARCH_ONLY"

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

REQUIRED_SAFE_FLAGS = {
    "operational_status": "BLOCKED_RESEARCH_ONLY",
    "edge_validated": False,
    "shadow_decision_allowed": False,
    "decision_layer_allowed": False,
    "promotion_allowed": False,
    "safe_apply_allowed": False,
    "canonical_data_writes": 0,
}

def _project() -> Path:
    cwd = Path.cwd()
    return cwd if cwd.name == "crypto_decision_lab" else cwd / "crypto_decision_lab"

def validate_manifest_entry(manifest: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []

    for key, expected in REQUIRED_SAFE_FLAGS.items():
        if manifest.get(key) != expected:
            errors.append(f"safety_flag_mismatch:{key}")

    for status_field in ["preflight_status", "focused_tests_status", "full_suite_status"]:
        if manifest.get(status_field) != "PASS":
            errors.append(f"{status_field}_not_pass")

    return {
        "valid_for_research_index": len(errors) == 0,
        "errors": errors,
        "phase": manifest.get("phase"),
        "gate": manifest.get("gate"),
        "safe_apply_allowed": False,
        "promotion_allowed": False,
        "edge_validated": False,
        "shadow_decision_allowed": False,
        "decision_layer_allowed": False,
        "canonical_data_writes": 0,
        "operational_status": "BLOCKED_RESEARCH_ONLY",
    }

def build_manifest_index(validation_dir: str | Path) -> dict[str, Any]:
    validation_path = Path(validation_dir)
    validation_path.mkdir(parents=True, exist_ok=True)

    manifests: list[dict[str, Any]] = []
    for path in sorted(validation_path.glob("phase*_runner_manifest.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            data = {"path": str(path), "read_error": str(exc)}
        data["_path"] = str(path)
        manifests.append(data)

    entries = []
    invalid_entries = []
    for manifest in manifests:
        validation = validate_manifest_entry(manifest)
        entry = {
            "phase": manifest.get("phase"),
            "gate": manifest.get("gate"),
            "path": manifest.get("_path"),
            "preflight_status": manifest.get("preflight_status"),
            "focused_tests_status": manifest.get("focused_tests_status"),
            "full_suite_status": manifest.get("full_suite_status"),
            "validation": validation,
        }
        entries.append(entry)
        if not validation["valid_for_research_index"]:
            invalid_entries.append(entry)

    index = {
        "gate": READY_GATE,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "manifest_count": len(entries),
        "valid_manifest_count": len(entries) - len(invalid_entries),
        "invalid_manifest_count": len(invalid_entries),
        "entries": entries,
        "invalid_entries": invalid_entries,
        "index_valid_for_research_only": len(invalid_entries) == 0,
        "safe_apply_allowed": False,
        "promotion_allowed": False,
        "edge_validated": False,
        "shadow_decision_allowed": False,
        "decision_layer_allowed": False,
        "canonical_data_writes": 0,
        "operational_status": "BLOCKED_RESEARCH_ONLY",
    }
    return index

def render_index_html(index: dict[str, Any]) -> str:
    rows = []
    for entry in index["entries"]:
        validation = entry["validation"]
        status = "PASS" if validation["valid_for_research_index"] else "NEEDS_REVIEW"
        rows.append(
            "<tr>"
            f"<td>{entry.get('phase')}</td>"
            f"<td>{entry.get('gate')}</td>"
            f"<td>{entry.get('preflight_status')}</td>"
            f"<td>{entry.get('focused_tests_status')}</td>"
            f"<td>{entry.get('full_suite_status')}</td>"
            f"<td>{status}</td>"
            "</tr>"
        )
    table = "".join(rows) or "<tr><td colspan='6'>No manifests found.</td></tr>"
    return f"""
<html>
<head>
  <meta charset="utf-8">
  <title>QRDS Validation Manifest Index</title>
  <style>
    body{{font-family:system-ui;background:#07111f;color:#e7edf8;padding:32px}}
    table{{border-collapse:collapse;width:100%;background:#101f35}}
    th,td{{border:1px solid #28415f;padding:10px;text-align:left}}
    .badge{{display:inline-block;padding:6px 10px;border:1px solid #28415f;border-radius:999px;margin:4px}}
  </style>
</head>
<body>
  <h1>QRDS Validation Manifest Index</h1>
  <p>{READY_GATE}</p>
  <p class="badge">Operational: BLOCKED_RESEARCH_ONLY</p>
  <p class="badge">Edge: False</p>
  <p class="badge">safe_apply_allowed: False</p>
  <p class="badge">canonical_data_writes: 0</p>
  <h2>Summary</h2>
  <p>Manifest count: {index["manifest_count"]}</p>
  <p>Valid manifests: {index["valid_manifest_count"]}</p>
  <p>Invalid manifests: {index["invalid_manifest_count"]}</p>
  <table>
    <thead><tr><th>Phase</th><th>Gate</th><th>Preflight</th><th>Focused</th><th>Full suite</th><th>Status</th></tr></thead>
    <tbody>{table}</tbody>
  </table>
</body>
</html>
"""

def write_manifest_index(validation_dir: str | Path) -> dict[str, Any]:
    validation_path = Path(validation_dir)
    index = build_manifest_index(validation_path)

    (validation_path / "runner_manifest_index.json").write_text(
        json.dumps(index, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (validation_path / "runner_manifest_index.html").write_text(
        render_index_html(index),
        encoding="utf-8",
    )
    return index

def build_phase70(output_dir: str | Path | None = None) -> dict[str, Any]:
    project = _project()
    out = Path(output_dir) if output_dir else project / "artifacts" / "phase70_validation_manifest_index_research_only"
    out.mkdir(parents=True, exist_ok=True)

    sample_manifest = {
        "phase": 70,
        "gate": READY_GATE,
        "preflight_status": "PASS",
        "focused_tests_status": "PASS",
        "full_suite_status": "PASS",
        **REQUIRED_SAFE_FLAGS,
    }
    (out / "phase70_runner_manifest.json").write_text(
        json.dumps(sample_manifest, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    index = write_manifest_index(out)

    result = {
        "gate": READY_GATE,
        "ready": True,
        "sample_index": index,
        **LOCKS,
    }

    (out / "phase70_validation_manifest_index.json").write_text(
        json.dumps(result, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (out / "index.html").write_text(render_index_html(index), encoding="utf-8")

    return result

def main() -> int:
    project = _project()
    validation_dir = project / "docs" / "reports" / "validation_automation"
    build_phase70()
    write_manifest_index(validation_dir)
    print("QRDS Phase 70 • Validation Manifest Index Research-Only")
    print(READY_GATE)
    print("Operational: BLOCKED_RESEARCH_ONLY")
    print("Edge: False")
    print("Shadow decision allowed: False")
    print("Decision layer allowed: False")
    print("Promotion allowed: False")
    print("safe_apply_allowed: False")
    print("canonical_data_writes: 0")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
