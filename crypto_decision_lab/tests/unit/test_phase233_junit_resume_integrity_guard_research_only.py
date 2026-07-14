from __future__ import annotations

import json
from pathlib import Path

from crypto_decision_lab.scripts.phase233_junit_resume_integrity_guard_research_only import (
    build_junit_resume_integrity_guard,
)


VALID_XML = """<?xml version="1.0" encoding="utf-8"?>
<testsuites>
  <testsuite name="x" tests="2" failures="0" errors="0" skipped="0"/>
</testsuites>
"""


def test_phase233_junit_resume_integrity_guard_passes(tmp_path: Path):
    for index in (1, 2, 3):
        (tmp_path / f"phase225_shard_{index}.xml").write_text(
            VALID_XML,
            encoding="utf-8",
        )

    meta = tmp_path / "phase225_v10_file_001_sample.json"
    meta.write_text(
        json.dumps(
            {
                "files": ["tests/unit/test_sample.py"],
                "returncode": 0,
                "timed_out": False,
                "mode": "STANDARD_PYTEST_V10",
            }
        ),
        encoding="utf-8",
    )
    meta.with_suffix(".xml").write_text(
        VALID_XML,
        encoding="utf-8",
    )
    meta.with_suffix(".log").write_text(
        "..",
        encoding="utf-8",
    )

    payload = build_junit_resume_integrity_guard(
        full_suite_dir=tmp_path,
    )
    assert payload["passed"] is True
    assert payload["invalid_result_group_count"] == 0
