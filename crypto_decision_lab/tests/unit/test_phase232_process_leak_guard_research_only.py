from __future__ import annotations

from crypto_decision_lab.scripts.phase232_process_leak_guard_research_only import (
    build_process_leak_guard,
)


def test_phase232_process_leak_guard_accepts_clean_snapshots():
    snapshots = iter(
        [
            {10: {"CommandLine": "python clean.py"}},
            {
                10: {"CommandLine": "python clean.py"},
                99: {
                    "Name": "powershell.exe",
                    "CommandLine": (
                        "Get-CimInstance Win32_Process "
                        "pytest|http.server|qrds_"
                    ),
                },
            },
        ]
    )
    payload = build_process_leak_guard(
        snapshot=lambda: next(snapshots),
        workload=lambda: {
            "preflight_pass": True,
        },
    )
    assert payload["passed"] is True
    assert payload["introduced_process_ids"] == [99]
    assert payload["relevant_introduced_processes"] == []


def test_phase232_process_leak_guard_blocks_python_http_server():
    snapshots = iter(
        [
            {},
            {
                77: {
                    "Name": "python.exe",
                    "CommandLine": (
                        "python -m http.server 8000"
                    ),
                }
            },
        ]
    )
    payload = build_process_leak_guard(
        snapshot=lambda: next(snapshots),
        workload=lambda: {
            "preflight_pass": True,
        },
    )
    assert payload["passed"] is False
    assert payload["introduced_process_ids"] == [77]
    assert len(payload["relevant_introduced_processes"]) == 1
