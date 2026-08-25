from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    import requests
except ModuleNotFoundError:  # Keep the repository's dependency-light local suite runnable.
    import pip._vendor.requests as requests

    sys.modules["requests"] = requests

from tools import gate_btc_b3_h120_h129_source_probe as probe


class FakeSession:
    def __init__(self, outcomes):
        self.outcomes = list(outcomes)
        self.calls = []

    def get(self, url, *, timeout):
        self.calls.append((url, timeout))
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome


class H120H129SourceProbeRetryTests(unittest.TestCase):
    def test_retries_truncated_response_and_returns_later_success(self):
        response = object()
        session = FakeSession(
            [
                requests.exceptions.ChunkedEncodingError("truncated-1"),
                requests.exceptions.ChunkedEncodingError("truncated-2"),
                response,
            ]
        )

        with mock.patch.object(probe.time, "sleep") as sleep:
            result, errors = probe.get(session, "https://b3.example/report.zip")

        self.assertIs(result, response)
        self.assertEqual([error["attempt"] for error in errors], [1, 2])
        self.assertTrue(all("ChunkedEncodingError" in error["error"] for error in errors))
        self.assertEqual(session.calls, [("https://b3.example/report.zip", (10, 45))] * 3)
        self.assertEqual([call.args[0] for call in sleep.call_args_list], [2, 4])

    def test_exhausted_transport_retries_fail_closed_without_final_sleep(self):
        session = FakeSession(
            [
                requests.exceptions.Timeout("timeout"),
                requests.exceptions.ConnectionError("connection"),
                requests.exceptions.ChunkedEncodingError("truncated"),
            ]
        )

        with mock.patch.object(probe.time, "sleep") as sleep:
            result, errors = probe.get(session, "https://b3.example/report.zip")

        self.assertIsNone(result)
        self.assertEqual([error["attempt"] for error in errors], [1, 2, 3])
        self.assertEqual([call.args[0] for call in sleep.call_args_list], [2, 4])

    def test_non_transport_error_is_not_hidden(self):
        session = FakeSession([ValueError("programming defect")])

        with mock.patch.object(probe.time, "sleep") as sleep:
            with self.assertRaisesRegex(ValueError, "programming defect"):
                probe.get(session, "https://b3.example/report.zip")

        sleep.assert_not_called()


if __name__ == "__main__":
    unittest.main()
