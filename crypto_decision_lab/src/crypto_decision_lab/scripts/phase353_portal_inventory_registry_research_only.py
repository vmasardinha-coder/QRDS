from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from crypto_decision_lab.scripts.phase346_355_closure_navigation_common import (
    ROOT,
    base_payload,
    discover_portals,
    fingerprint,
    phase_summary,
    read_json,
    validate_phase,
    write_json,
    write_summary,
    write_text,
)


def build(phase352_path: Path, output_dir: Path, *, project_root: Path | None = None) -> dict[str, Any]:
    p352 = read_json(phase352_path)
    validate_phase(p352, 352)
    root = (project_root or ROOT).resolve()
    # Phase 353 inventories portals that existed before this navigation batch.
    # Excluding 353+ keeps reruns idempotent and prevents the unified portal from
    # being treated as its own historical predecessor after an interrupted run.
    portals = [item for item in discover_portals(root) if int(item.get("phase", -1)) < 353]
    latest = portals[-1] if portals else None

    payload = base_payload(353, "PORTAL_INVENTORY_REGISTRY_READY_RESEARCH_ONLY")
    payload.update(
        {
            "gate": "PHASE353_PORTAL_INVENTORY_REGISTRY_READY_RESEARCH_ONLY",
            "portal_count": len(portals),
            "portals": portals,
            "latest_existing_portal": latest,
            "latest_existing_portal_found": latest is not None,
            "registry_is_navigation_only": True,
            "scientific_result_changed": False,
            "network_required": False,
        }
    )
    payload["artifact_fingerprint"] = fingerprint(payload)
    output_dir.mkdir(parents=True, exist_ok=True)
    write_json(output_dir / "phase353_portal_inventory_registry.json", payload)

    lines = [
        "# QRDS Portal Catalog",
        "",
        "This catalog is a navigation layer. It does not change any scientific result or safety gate.",
        "",
        f"Detected local portals: **{len(portals)}**",
        "",
        "| Phase | Local path | SHA-256 |",
        "|---:|---|---|",
    ]
    if portals:
        for item in reversed(portals):
            lines.append(f"| {item['phase']} | `{item['relative_path']}` | `{item['sha256']}` |")
    else:
        lines.append("| — | No portal found during this run | — |")
    lines.extend(
        [
            "",
            "Use the root launcher `ABRIR_QRDS.ps1` after Phase 354 to open the current portal automatically.",
        ]
    )
    write_text(root / "docs" / "PORTAL_CATALOG.md", "\n".join(lines))
    write_summary(
        root / "docs/reports/closure_navigation_v1/phase353_portal_inventory_registry_summary.md",
        title="Phase 353 — Portal Inventory Registry",
        gate=payload["gate"],
        bullets=[
            f"Detected portals: `{len(portals)}`",
            f"Latest existing portal: `{latest['relative_path'] if latest else 'NONE'}`",
            "Navigation only: `True`",
            "Scientific result changed: `False`",
        ],
    )
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase352-artifact", type=Path, default=ROOT / "artifacts/phase352_new_question_governance_research_only/phase352_new_question_governance.json")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "artifacts/phase353_portal_inventory_registry_research_only")
    parser.add_argument("--project-root", type=Path, default=ROOT)
    args = parser.parse_args()
    payload = build(args.phase352_artifact, args.output_dir, project_root=args.project_root)
    print(payload["gate"])
    print("Portals detected:", payload["portal_count"])
    print("Latest portal:", (payload["latest_existing_portal"] or {}).get("relative_path"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
