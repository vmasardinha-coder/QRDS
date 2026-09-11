"""A workflow must watch the modules its own tools import.

This exists because the same defect landed three times. PR #643 reached main with
no CI at all. The fallback wake tool woke one chained consumer and left six
unwatched, which stalled the V11 series on 2026-09-11. And the Daily Research
collection was stopped that same morning by a fail-closed guard in
`gate_btc_measurement_common.py`, a module its workflow did not watch.

Each time the fix was correct and local, and each time the family survived. So
the verdict lives here instead of in someone remembering: KNOWN_GAPS is the
reviewed backlog, and it can only shrink. A new gap fails the first test; a gap
that has been closed fails the second until its exception is deleted.
"""
import json
import subprocess
import sys
import unittest
from pathlib import Path

from tools import gate_btc_workflow_path_coverage as coverage

ROOT = Path(__file__).resolve().parents[1]

# Reviewed on 2026-09-11, over the TRANSITIVE import closure. Every entry is a
# real gap that has NOT been closed yet.
# Closing one means deleting its line here in the same pull request that fixes
# the workflow; the staleness test below makes that mandatory rather than polite.
# None of these sit on the Delta critical path — the two that did, in
# gate-btc-delta-v12-engine.yml and gate-btc-daily-research.yml, are fixed.
KNOWN_GAPS = frozenset({
    ('gate-btc-2-stage9-counter-bridge.yml',
     'tools/gate_btc_2_microstructure_shadow_manifest.py',
     'tools/gate_btc_2_microstructure_shadow_contract.py'),
    ('gate-btc-2-stage9-exit-gate.yml',
     'tools/gate_btc_2_stage9_admission_ledger.py',
     'tools/gate_btc_2_prospective_counter_bridge.py'),
    ('gate-btc-2-stage9-exit-gate.yml',
     'tools/gate_btc_2_stage9_exit_gate.py',
     'tools/gate_btc_2_stage9_admission_ledger.py'),
    ('gate-btc-2-system10-adapter-contract.yml',
     'tools/gate_btc_2_stage9_admission_ledger.py',
     'tools/gate_btc_2_prospective_counter_bridge.py'),
    ('gate-btc-2-system10-adapter-contract.yml',
     'tools/gate_btc_2_system10_event_envelope.py',
     'tools/gate_btc_2_stage9_admission_ledger.py'),
    ('gate-btc-2-system10-parity-receipt.yml',
     'tools/gate_btc_2_stage9_admission_ledger.py',
     'tools/gate_btc_2_prospective_counter_bridge.py'),
    ('gate-btc-2-system10-parity-receipt.yml',
     'tools/gate_btc_2_system10_event_envelope.py',
     'tools/gate_btc_2_stage9_admission_ledger.py'),
    ('gate-btc-2-system10-readiness-record.yml',
     'tools/gate_btc_2_stage9_admission_ledger.py',
     'tools/gate_btc_2_prospective_counter_bridge.py'),
    ('gate-btc-2-system10-readiness-record.yml',
     'tools/gate_btc_2_system10_event_envelope.py',
     'tools/gate_btc_2_stage9_admission_ledger.py'),
    ('gate-btc-2-system10-shadow-adapter-fixture.yml',
     'tools/gate_btc_2_stage9_admission_ledger.py',
     'tools/gate_btc_2_prospective_counter_bridge.py'),
    ('gate-btc-2-system10-shadow-adapter-fixture.yml',
     'tools/gate_btc_2_system10_event_envelope.py',
     'tools/gate_btc_2_stage9_admission_ledger.py'),
    ('gate-btc-source-redundancy-probes.yml',
     'tools/gate_btc_bybit_redundancy_probe.py',
     'tools/gate_btc_2_stage9_bybit_candidate_probe.py'),
    ('gate-btc-v16b-prospective-seal.yml',
     'tools/gate_btc_v16b_prospective_entry.py',
     'tools/gate_btc_binance_usdm_weekly_shortability.py'),
    ('gate-btc-v16b-prospective-seal.yml',
     'tools/gate_btc_v16b_prospective_funding.py',
     'tools/gate_btc_binance_usdm_funding_audit.py'),
    ('gate-btc-v16b-prospective-seal.yml',
     'tools/gate_btc_v16b_prospective_result.py',
     'tools/gate_btc_binance_usdm_funding_audit.py'),
    ('gate-btc-v2a-cross-archive-equivalence.yml',
     'tools/gate_btc_binance_spot_cross_archive_equivalence.py',
     'tools/gate_btc_source_redundancy_probe.py'),
})


def observed() -> set[tuple[str, str, str]]:
    return {(g["workflow"], g["listed"], g["missing"]) for g in coverage.scan(ROOT)}


class ParserTests(unittest.TestCase):
    """A scanner that quietly parses nothing would pass every test below it.

    These pin the reader against a real workflow so an empty result is a failure
    rather than a clean bill of health.
    """

    def workflow(self, name: str) -> str:
        return (ROOT / ".github" / "workflows" / name).read_text(encoding="utf-8-sig")

    def test_it_reads_the_paths_of_a_real_workflow(self):
        found = coverage.trigger_paths(self.workflow("gate-btc-delta-v12-engine.yml"))
        self.assertIn("pull_request", found)
        self.assertIn("tools/gate_btc_delta_v12_engine.py", found["pull_request"])
        self.assertIn("tools/gate_btc_delta_v12_report.py", found["pull_request"])

    def test_it_reads_both_triggers_when_both_carry_filters(self):
        found = coverage.trigger_paths(self.workflow("gate-btc-daily-research.yml"))
        self.assertEqual(set(found), {"pull_request", "push"})
        for paths in found.values():
            self.assertIn("tools/gate_btc_lock_valuation_sidecar.py", paths)

    def test_quotes_and_trailing_comments_are_stripped(self):
        text = ("on:\n  pull_request:\n    paths:\n"
                "      - 'tools/a.py'\n"
                "      - tools/b.py  # why\n"
                "      - \"tools/c.py\"\n")
        self.assertEqual(coverage.trigger_paths(text)["pull_request"],
                         ["tools/a.py", "tools/b.py", "tools/c.py"])

    def test_a_paths_key_outside_the_on_block_is_not_a_trigger_filter(self):
        text = ("on:\n  pull_request:\n    paths:\n      - tools/a.py\n"
                "jobs:\n  build:\n    steps:\n      - uses: actions/upload-artifact@v4\n"
                "        with:\n          paths:\n            - artifacts/b.py\n")
        self.assertEqual(coverage.trigger_paths(text)["pull_request"], ["tools/a.py"])

    def test_imports_are_read_in_both_spellings(self):
        found = coverage.tool_imports(ROOT / "tools" / "gate_btc_delta_v12_report.py")
        self.assertIn("tools/gate_btc_delta_paper_report.py", found)

    def test_the_scan_is_not_vacuous(self):
        # If the parser silently broke, this set would empty out and every
        # coverage test would pass while protecting nothing.
        self.assertTrue(observed())


class CoverageTests(unittest.TestCase):

    def test_no_workflow_has_a_gap_outside_the_reviewed_backlog(self):
        new = observed() - KNOWN_GAPS
        self.assertEqual(new, set(), "\n".join(
            ["A workflow does not watch a module its own tool imports.",
             "Add the missing path to that workflow's paths: filter.",
             ""] +
            [f"  {w}: lists {l}, imports {m}" for w, l, m in sorted(new)]))

    def test_a_closed_gap_must_have_its_exception_deleted(self):
        stale = KNOWN_GAPS - observed()
        self.assertEqual(stale, set(), "\n".join(
            ["These gaps are closed; delete them from KNOWN_GAPS.",
             "An exception nobody removes is how the backlog stops shrinking.",
             ""] +
            [f"  {w}: {l} -> {m}" for w, l, m in sorted(stale)]))

    def test_the_delta_critical_path_carries_no_gap_at_all(self):
        # These two stopped the V11 series on 2026-09-11. They get no exception
        # slot: a regression here must fail on its own, not join a backlog.
        protected = {"gate-btc-daily-research.yml",
                     "gate-btc-delta-v12-engine.yml",
                     "gate-btc-delta-paper-monitor.yml",
                     "gate-btc-daily-fallback.yml"}
        offending = {gap for gap in observed() if gap[0] in protected}
        self.assertEqual(offending, set())


class CommandLineTests(unittest.TestCase):
    """The scanner is meant to be runnable by hand while fixing a workflow."""

    def test_running_it_as_a_plain_script_prints_the_gaps(self):
        script = Path(coverage.__file__).resolve()
        done = subprocess.run([sys.executable, str(script)],
                              capture_output=True, text=True, cwd=script.parents[1])
        self.assertEqual(done.returncode, 0, done.stderr)
        payload = json.loads(done.stdout)
        self.assertEqual(payload["schema"], coverage.SCHEMA)
        self.assertTrue(payload["reporting_only"])
        self.assertEqual(payload["gap_count"], len(payload["gaps"]))


if __name__ == "__main__":
    unittest.main()
