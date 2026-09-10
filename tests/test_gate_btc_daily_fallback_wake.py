import json
import subprocess
import sys
import unittest
from pathlib import Path

from tools import gate_btc_daily_fallback_wake as wake

REPO = "vmasardinha-coder/QRDS"
AFTER = "2026-09-10T07:17:00Z"


def collection(created="2026-09-10T07:21:48Z", status="completed",
               conclusion="success", run_id=34449199835):
    return {"id": run_id, "created_at": created, "status": status, "conclusion": conclusion}


class FakeApi:
    """Records calls and replays a scripted sequence of run listings."""

    def __init__(self, *listings):
        self.listings = list(listings)
        self.calls = []

    def __call__(self, method, url, payload=None):
        self.calls.append((method, url, payload))
        if method == "POST":
            return None
        runs = self.listings.pop(0) if self.listings else []
        return {"workflow_runs": runs}

    @property
    def dispatches(self):
        return [c for c in self.calls if c[0] == "POST"]


class DecisionTests(unittest.TestCase):

    def test_a_successful_collection_wakes_the_monitor(self):
        ok, status = wake.should_wake(collection())
        self.assertTrue(ok)
        self.assertEqual(status, wake.WOKE)

    def test_a_failed_collection_does_not_wake_the_monitor(self):
        ok, status = wake.should_wake(collection(conclusion="failure"))
        self.assertFalse(ok)
        self.assertEqual(status, wake.NOT_SUCCESSFUL)

    def test_a_run_still_going_at_the_deadline_does_not_wake(self):
        ok, status = wake.should_wake(collection(status="in_progress", conclusion=None))
        self.assertFalse(ok)
        self.assertEqual(status, wake.STILL_RUNNING)

    def test_no_run_at_all_does_not_wake(self):
        ok, status = wake.should_wake(None)
        self.assertFalse(ok)
        self.assertEqual(status, wake.NO_RUN_FOUND)


class SelectionTests(unittest.TestCase):

    def test_only_runs_at_or_after_the_mark_are_considered(self):
        api = FakeApi([collection(created="2026-09-09T07:21:48Z", run_id=1)])
        self.assertIsNone(wake.newest_dispatched_run(api, REPO, AFTER))

    def test_the_newest_fresh_run_wins(self):
        api = FakeApi([collection(created="2026-09-10T07:21:48Z", run_id=1),
                       collection(created="2026-09-10T07:25:00Z", run_id=2)])
        chosen = wake.newest_dispatched_run(api, REPO, AFTER)
        self.assertEqual(chosen["id"], 2)

    def test_it_asks_for_dispatch_runs_of_the_collection_on_main(self):
        api = FakeApi([])
        wake.newest_dispatched_run(api, REPO, AFTER)
        url = api.calls[0][1]
        self.assertIn(wake.COLLECTION_WORKFLOW, url)
        self.assertIn("event=workflow_dispatch", url)
        self.assertIn("branch=main", url)


class PollingTests(unittest.TestCase):

    def test_it_waits_until_the_run_reaches_a_terminal_state(self):
        slept = []
        api = FakeApi(
            [collection(status="queued", conclusion=None)],
            [collection(status="in_progress", conclusion=None)],
            [collection()],
        )
        found = wake.wait_for_run(api, REPO, AFTER, attempts=5, delay=1,
                                  sleep=slept.append)
        self.assertEqual(found["conclusion"], "success")
        self.assertEqual(len(slept), 2)

    def test_it_gives_up_at_the_deadline_and_returns_what_it_saw(self):
        api = FakeApi(*([[collection(status="in_progress", conclusion=None)]] * 3))
        found = wake.wait_for_run(api, REPO, AFTER, attempts=3, delay=1,
                                  sleep=lambda _: None)
        self.assertEqual(found["status"], "in_progress")

    def test_it_does_not_sleep_after_the_last_attempt(self):
        slept = []
        api = FakeApi(*([[]] * 2))
        wake.wait_for_run(api, REPO, AFTER, attempts=2, delay=1, sleep=slept.append)
        self.assertEqual(len(slept), 1)


class EndToEndTests(unittest.TestCase):

    def test_a_recovered_collection_wakes_the_monitor_with_its_run_id(self):
        api = FakeApi([collection()])
        result = wake.run(api, REPO, AFTER, attempts=1, delay=0, sleep=lambda _: None)
        self.assertEqual(result["status"], wake.WOKE)
        self.assertEqual(len(api.dispatches), 1)
        method, url, payload = api.dispatches[0]
        self.assertIn(wake.MONITOR_WORKFLOW, url)
        self.assertEqual(payload["inputs"]["run_id"], "34449199835")
        self.assertEqual(payload["ref"], "main")

    def test_a_failed_collection_dispatches_nothing(self):
        api = FakeApi([collection(conclusion="failure")])
        result = wake.run(api, REPO, AFTER, attempts=1, delay=0, sleep=lambda _: None)
        self.assertEqual(result["status"], wake.NOT_SUCCESSFUL)
        self.assertEqual(api.dispatches, [])

    def test_nothing_found_dispatches_nothing(self):
        api = FakeApi([])
        result = wake.run(api, REPO, AFTER, attempts=1, delay=0, sleep=lambda _: None)
        self.assertEqual(result["status"], wake.NO_RUN_FOUND)
        self.assertEqual(api.dispatches, [])
        self.assertIsNone(result["collection_run_id"])


class CommandLineTests(unittest.TestCase):
    """The workflow reaches this file only through argv, so argv is what is tested."""

    def test_it_refuses_to_run_without_a_token(self):
        import os
        from unittest import mock
        with mock.patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(wake.WakeError):
                wake.main(["--after", AFTER, "--repository", REPO])

    def test_it_refuses_to_run_without_a_repository(self):
        import os
        from unittest import mock
        with mock.patch.dict(os.environ, {"GH_TOKEN": "x"}, clear=True):
            with self.assertRaises(wake.WakeError):
                wake.main(["--after", AFTER, "--repository", ""])

    def test_running_it_as_a_plain_script_reports_its_usage(self):
        # The workflow invokes `python tools/<name>.py`; a missing required
        # argument must fail loudly there rather than silently doing nothing.
        script = Path(wake.__file__).resolve()
        done = subprocess.run([sys.executable, str(script)],
                              capture_output=True, text=True, cwd=script.parents[1])
        self.assertEqual(done.returncode, 2)
        self.assertIn("--after", done.stderr)


if __name__ == "__main__":
    unittest.main()
