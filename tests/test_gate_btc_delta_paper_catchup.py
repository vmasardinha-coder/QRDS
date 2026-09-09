import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tools import gate_btc_delta_paper_catchup as catchup


def pointer(**over):
    """A pointer shaped like the one the collection actually publishes."""
    base = {
        "artifact_name": "gate-btc-daily-research-34349545018",
        "branch": "main",
        "data_cutoff": "2026-09-09",
        "delivery_request_sha256": "28897a5749b7fdc84581f8d8e937504b5d0a1dd6c7730c80bc404390d70148d9",
        "event_name": "schedule",
        "head_sha": "1b4114c8dbaba38960eca3f38d385e07c72cee9a",
        "operational_status": "NOT_APPROVED",
        "orders_generated": 0,
        "published_at_utc": "2026-09-09T12:17:26.737387+00:00",
        "real_capital_used": 0,
        "research_only": True,
        "run_attempt": 1,
        "run_id": 34349545018,
        "schema_version": "1.0.0",
        "workflow_file": ".github/workflows/gate-btc-daily-research.yml",
        "workflow_name": "GATE BTC Daily Research Collection",
    }
    base.update(over)
    return base


def status(**over):
    base = {"data_as_of": "2026-09-08", "source_run_id": "34323454513", "observed_days": 26}
    base.update(over)
    return base


class DecisionTests(unittest.TestCase):

    def test_a_newer_close_is_processed(self):
        d = catchup.decide(pointer(), status())
        self.assertEqual(d["decision"], catchup.PROCESS)
        self.assertEqual(d["source_run_id"], 34349545018)
        self.assertEqual(d["days_ahead"], 1)

    def test_the_same_close_from_a_newer_run_is_not_reprocessed(self):
        # The live trap: on 2026-09-09 the pointer carried run 34349545018 while
        # the ledger held 34323454513 — a newer run id for a close already
        # booked. Comparing run ids would reprocess 09-08 every hour.
        d = catchup.decide(pointer(data_cutoff="2026-09-08"), status())
        self.assertEqual(d["decision"], catchup.UP_TO_DATE)
        self.assertNotEqual(d["source_run_id"], int(status()["source_run_id"]))

    def test_a_pointer_older_than_the_ledger_never_moves_the_series_back(self):
        d = catchup.decide(pointer(data_cutoff="2026-09-07"), status())
        self.assertEqual(d["decision"], catchup.POINTER_BEHIND_LEDGER)
        self.assertIn("backwards", d["reason"])

    def test_a_multi_day_jump_is_still_process_and_left_to_the_monitor(self):
        # The catchup decides only that there is something to look at. Refusing a
        # gap is the monitor's rule and is not duplicated here.
        d = catchup.decide(pointer(data_cutoff="2026-09-12"), status())
        self.assertEqual(d["decision"], catchup.PROCESS)
        self.assertEqual(d["days_ahead"], 4)

    def test_no_ledger_yet_is_processed_not_refused(self):
        d = catchup.decide(pointer(), None)
        self.assertEqual(d["decision"], catchup.PROCESS)
        self.assertIsNone(d["ledger_data_as_of"])

    def test_a_missing_pointer_is_an_error(self):
        with self.assertRaises(catchup.CatchupError):
            catchup.decide(None, status())


class PointerSafetyTests(unittest.TestCase):

    def test_a_pointer_from_another_workflow_is_refused(self):
        with self.assertRaises(catchup.CatchupError):
            catchup.decide(pointer(workflow_name="Something Else"), status())

    def test_a_pointer_from_another_branch_is_refused(self):
        with self.assertRaises(catchup.CatchupError):
            catchup.decide(pointer(branch="feature"), status())

    def test_every_safety_flag_is_enforced(self):
        for key, bad in (("research_only", False), ("operational_status", "APPROVED"),
                         ("orders_generated", 1), ("real_capital_used", 100)):
            with self.subTest(key=key):
                with self.assertRaises(catchup.CatchupError):
                    catchup.decide(pointer(**{key: bad}), status())

    def test_a_nonsense_run_id_is_refused(self):
        for bad in (0, -1, "34349545018", None):
            with self.subTest(run_id=bad):
                with self.assertRaises(catchup.CatchupError):
                    catchup.decide(pointer(run_id=bad), status())

    def test_an_unparseable_date_is_named_not_swallowed(self):
        with self.assertRaises(catchup.CatchupError) as raised:
            catchup.decide(pointer(data_cutoff="not-a-date"), status())
        self.assertIn("data_cutoff", str(raised.exception))
        with self.assertRaises(catchup.CatchupError) as raised:
            catchup.decide(pointer(), status(data_as_of=""))
        self.assertIn("data_as_of", str(raised.exception))


class CommandLineTests(unittest.TestCase):
    """The workflow reaches this file only through argv, so argv is what is tested."""

    def write(self, root: Path, ptr=None, st=None):
        p = root / "GATE_BTC_LATEST_ELIGIBLE_RUN.json"
        p.write_text(json.dumps(ptr if ptr is not None else pointer()))
        s = root / "STATUS.json"
        if st is not None:
            s.write_text(json.dumps(st))
        return p, s

    def test_main_prints_the_decision_and_exits_zero(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            p, s = self.write(root, st=status())
            self.assertEqual(catchup.main(["--pointer", str(p), "--status", str(s)]), 0)

    def test_main_tolerates_a_status_file_that_does_not_exist(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            p, s = self.write(root)
            self.assertFalse(s.exists())
            self.assertEqual(catchup.main(["--pointer", str(p), "--status", str(s)]), 0)

    def test_main_writes_the_decision_into_the_step_environment(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            p, s = self.write(root, st=status())
            env_file = root / "env"
            env_file.touch()
            with mock.patch.dict("os.environ", {"GITHUB_ENV": str(env_file)}):
                catchup.main(["--pointer", str(p), "--status", str(s)])
            written = env_file.read_text()
        self.assertIn("CATCHUP_DECISION=PROCESS", written)
        self.assertIn("CATCHUP_SOURCE_RUN_ID=34349545018", written)

    def test_running_it_as_a_plain_script_works_like_the_workflow_does(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            p, s = self.write(root, st=status())
            script = Path(catchup.__file__).resolve()
            done = subprocess.run(
                [sys.executable, str(script), "--pointer", str(p), "--status", str(s)],
                capture_output=True, text=True, cwd=script.parents[1])
            self.assertEqual(done.returncode, 0, done.stderr)
            self.assertEqual(json.loads(done.stdout)["decision"], catchup.PROCESS)

    def test_a_malformed_pointer_file_fails_loudly(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            p = root / "ptr.json"
            p.write_text("{not json")
            with self.assertRaises(catchup.CatchupError):
                catchup.main(["--pointer", str(p), "--status", str(root / "none.json")])


if __name__ == "__main__":
    unittest.main()
