from __future__ import annotations

import json
from pathlib import Path

from crypto_decision_lab.scripts.phase40_portal_visual_qa_accessibility_link_audit import READY_GATE, build_phase40


def test_phase40_builds_visual_qa_from_minimal_source(tmp_path):
    repo_root = tmp_path / "repo"
    project_dir = repo_root / "crypto_decision_lab"
    source = project_dir / "artifacts" / "phase39_interpretation_readiness_information_architecture"
    source.mkdir(parents=True)
    (project_dir / "docs" / "reports").mkdir(parents=True)
    (source / "index.html").write_text(
        "<html><head><title>Source</title></head><body><nav><a href='index.html'>Home</a></nav><main><h1>Source</h1><p>research-only BLOCKED_RESEARCH_ONLY</p></main></body></html>",
        encoding="utf-8",
    )
    out = project_dir / "artifacts" / "phase40_test"
    summary = build_phase40(out, source, repo_root)
    assert summary["gate"] == READY_GATE
    assert summary["operational_status"] == "BLOCKED_RESEARCH_ONLY"
    assert summary["edge_validated"] is False
    assert summary["canonical_data_writes"] == 0
    assert (out / "index.html").exists()
    assert (out / "phase40_visual_qa_summary.json").exists()
    loaded = json.loads((out / "phase40_visual_qa_summary.json").read_text(encoding="utf-8"))
    assert loaded["visual_qa_ready"] is True
