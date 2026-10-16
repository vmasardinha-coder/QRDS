import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
import requests
from tools import gate_btc_v16b_cmc_snapshot as capture

class SnapshotRetryTests(unittest.TestCase):
    def response(self,status):
        response=Mock(status_code=status,headers={},url=capture.ENDPOINT)
        response.content=json.dumps({"data":[{"id":i} for i in range(150)]}).encode()
        response.json.return_value=json.loads(response.content)
        if status >= 400:response.raise_for_status.side_effect=requests.HTTPError(str(status))
        return response

    def run_capture(self,responses):
        with tempfile.TemporaryDirectory() as tmp, patch.object(capture.requests,"Session") as session, patch.object(capture.time,"sleep") as sleep:
            session.return_value.get.side_effect=responses
            result=capture.capture(Path(tmp))
            self.assertEqual(result[0].read_bytes(),responses[-1].content)
            return result[2],session.return_value.get.call_count,sleep.call_count

    def test_transient_limit_retries_same_source_and_preserves_response(self):
        evidence,calls,sleeps=self.run_capture([self.response(429),self.response(200)])
        self.assertEqual((calls,sleeps),(2,1))
        self.assertEqual(evidence["rows"],150)
        self.assertEqual(evidence["endpoint"],capture.ENDPOINT)
        self.assertEqual(evidence["orders"],0)

    def test_permanent_error_does_not_retry_or_create_snapshot(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(capture.requests,"Session") as session, patch.object(capture.time,"sleep") as sleep:
            session.return_value.get.return_value=self.response(403)
            with self.assertRaises(requests.HTTPError):capture.capture(Path(tmp))
            self.assertFalse(list(Path(tmp).iterdir()))
            self.assertEqual(session.return_value.get.call_count,1)
            sleep.assert_not_called()

    def test_exhausted_limit_is_failure_not_fabricated_evidence(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(capture.requests,"Session") as session, patch.object(capture.time,"sleep"):
            session.return_value.get.return_value=self.response(429)
            with self.assertRaises(requests.HTTPError):capture.capture(Path(tmp))
            self.assertEqual(session.return_value.get.call_count,3)
            self.assertFalse(list(Path(tmp).iterdir()))
