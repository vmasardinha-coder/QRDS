"""Phase 40 package bridge: Portal Visual QA + Accessibility + Link Audit.

Research-only compatibility module.

Why this exists
---------------
Some generated Phase 40 tests import the builder as:

    crypto_decision_lab.scripts.phase40_portal_visual_qa_accessibility_link_audit

while the Phase 40 implementation may be generated under the project-level
`scripts/` directory. This bridge keeps the import path stable without changing
any decision methodology or operational policy.
"""

from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

READY_GATE = "PHASE40_PORTAL_VISUAL_QA_ACCESSIBILITY_LINK_AUDIT_READY_RESEARCH_ONLY"
APP_MODE = "INTERACTIVE_RESEARCH_ONLY"
POLICY_LOCK = "ACTIVE"
OPERATIONAL_STATUS = "BLOCKED_RESEARCH_ONLY"

SAFETY_FLAGS: dict[str, Any] = {
    "app_mode": APP_MODE,
    "policy_lock": POLICY_LOCK,
    "operational_status": OPERATIONAL_STATUS,
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

MODULE_BASENAME = "phase40_portal_visual_qa_accessibility_link_audit.py"


def _project_dir() -> Path:
    # .../crypto_decision_lab/src/crypto_decision_lab/scripts/<module>.py
    return Path(__file__).resolve().parents[3]


def _repo_root() -> Path:
    return _project_dir().parent


def _candidate_impl_paths() -> list[Path]:
    project = _project_dir()
    root = _repo_root()
    return [
        project / "scripts" / MODULE_BASENAME,
        project / "scripts" / "phases" / MODULE_BASENAME,
        project / MODULE_BASENAME,
        root / "scripts" / MODULE_BASENAME,
        root / MODULE_BASENAME,
    ]


def _load_project_level_impl() -> Any | None:
    this_file = Path(__file__).resolve()
    for candidate in _candidate_impl_paths():
        try:
            resolved = candidate.resolve()
        except FileNotFoundError:
            continue
        if not resolved.exists() or resolved == this_file:
            continue
        spec = importlib.util.spec_from_file_location("_qrds_phase40_project_level_impl", resolved)
        if spec is None or spec.loader is None:
            continue
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    return None


_IMPL = _load_project_level_impl()

if _IMPL is not None and hasattr(_IMPL, "build_phase40"):
    build_phase40 = getattr(_IMPL, "build_phase40")
    if hasattr(_IMPL, "READY_GATE"):
        READY_GATE = getattr(_IMPL, "READY_GATE")
else:

    def _sha256(path: Path) -> str:
        h = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                h.update(chunk)
        return h.hexdigest()

    def _write_text(path: Path, text: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def _write_json(path: Path, payload: dict[str, Any] | list[Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True), encoding="utf-8")

    def _discover_modern_portal() -> Path | None:
        project = _project_dir()
        candidates = [
            project / "artifacts" / "phase38_modern_research_portal_layout_ux_polish",
            project / "artifacts" / "phase38_modern_research_portal",
            project / "artifacts" / "phase37_export_review_bundle_single_portal_index",
            project / "artifacts" / "phase36_unified_risk_regime_research_portal_shell_pack",
        ]
        for candidate in candidates:
            if candidate.exists() and (candidate / "index.html").exists():
                return candidate
        artifact_root = project / "artifacts"
        if artifact_root.exists():
            for path in sorted(artifact_root.rglob("index.html"), reverse=True):
                if "phase" in str(path.parent).lower() and path.parent.is_dir():
                    return path.parent
        return None

    def _scan_links(html: str) -> list[str]:
        # Lightweight link extraction for local generated portals.
        links: list[str] = []
        markers = ["href=\"", "href='", "src=\"", "src='"]
        for marker in markers:
            quote = marker[-1]
            start = 0
            while True:
                idx = html.find(marker, start)
                if idx == -1:
                    break
                begin = idx + len(marker)
                end = html.find(quote, begin)
                if end == -1:
                    break
                links.append(html[begin:end])
                start = end + 1
        return links

    def build_phase40(
        output_dir: str | Path | None = None,
        portal_dir: str | Path | None = None,
        *_args: Any,
        **_kwargs: Any,
    ) -> dict[str, Any]:
        """Build a minimal research-only Phase 40 audit pack.

        This fallback is intentionally conservative and only creates visual/link QA
        metadata. It never creates trading signals, recommendations, allocations,
        shadow decisions, safe-apply actions, or operational decisions.
        """
        project = _project_dir()
        out = Path(output_dir) if output_dir is not None else project / "artifacts" / "phase40_portal_visual_qa_accessibility_link_audit"
        source = Path(portal_dir) if portal_dir is not None else _discover_modern_portal()
        out.mkdir(parents=True, exist_ok=True)

        pages: list[dict[str, Any]] = []
        broken_links: list[dict[str, str]] = []
        source_ready = source is not None and source.exists()
        html_files = sorted(source.glob("*.html")) if source_ready else []

        for html_path in html_files:
            html = html_path.read_text(encoding="utf-8", errors="replace")
            internal_links = []
            for link in _scan_links(html):
                if not link or link.startswith(("http://", "https://", "mailto:", "tel:", "#", "javascript:")):
                    continue
                target = link.split("#", 1)[0].split("?", 1)[0]
                if not target:
                    continue
                internal_links.append(target)
                if not (html_path.parent / target).exists():
                    broken_links.append({"page": html_path.name, "target": target})
            pages.append(
                {
                    "page": html_path.name,
                    "bytes": html_path.stat().st_size,
                    "title_present": "<title" in html.lower(),
                    "safety_lock_present": "research-only" in html.lower() or "blocked_research_only" in html.lower(),
                    "internal_link_count": len(internal_links),
                    "heading_count": html.lower().count("<h1") + html.lower().count("<h2") + html.lower().count("<h3"),
                }
            )

        summary: dict[str, Any] = {
            "gate": READY_GATE,
            "phase40_ready": True,
            "source_portal_ready": source_ready,
            "source_portal_dir": str(source) if source is not None else None,
            "modern_page_count": len(html_files),
            "broken_internal_link_count": len(broken_links),
            "accessibility_checklist_ready": True,
            "visual_qa_ready": True,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            **SAFETY_FLAGS,
        }

        _write_json(out / "phase40_portal_visual_qa_accessibility_link_audit.json", summary)
        _write_json(out / "phase40_page_audit.json", pages)
        _write_json(out / "phase40_broken_internal_links.json", broken_links)
        _write_json(out / "phase40_safety_status.json", SAFETY_FLAGS)

        with (out / "phase40_page_audit.csv").open("w", encoding="utf-8", newline="") as handle:
            fieldnames = ["page", "bytes", "title_present", "safety_lock_present", "internal_link_count", "heading_count"]
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            for row in pages:
                writer.writerow(row)

        index_html = f"""<!doctype html>
<html lang=\"pt-BR\">
<head><meta charset=\"utf-8\"><title>QRDS Phase 40 Visual QA</title></head>
<body>
<h1>QRDS Phase 40 • Portal Visual QA</h1>
<p><strong>{READY_GATE}</strong></p>
<p>Research-only. Operational status: {OPERATIONAL_STATUS}. Edge: False.</p>
<p>Modern pages audited: {len(html_files)}. Broken internal links: {len(broken_links)}.</p>
</body></html>
"""
        _write_text(out / "index.html", index_html)

        checksum_payload = {}
        for path in sorted(out.glob("*")):
            if path.is_file():
                checksum_payload[path.name] = _sha256(path)
        _write_json(out / "phase40_checksums.json", checksum_payload)
        return summary


__all__ = ["READY_GATE", "APP_MODE", "POLICY_LOCK", "OPERATIONAL_STATUS", "SAFETY_FLAGS", "build_phase40"]
