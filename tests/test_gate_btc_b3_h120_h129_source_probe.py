from __future__ import annotations

import io
import sys
import unittest
import zipfile
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


class FakeResponse:
    def raise_for_status(self):
        return None


class H120H129SourceProbeRetryTests(unittest.TestCase):
    def test_retries_truncated_response_and_returns_later_success(self):
        response = FakeResponse()
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

    def test_schema_scan_distinguishes_exact_futures_from_options(self):
        def row(ticker):
            return f"""<BizGrp><Document><PricRpt>
              <SctyId><TckrSymb>{ticker}</TckrSymb></SctyId>
              <TradDtls><TradQty>1</TradQty></TradDtls>
              <FinInstrmAttrbts><RglrTraddCtrcts>1</RglrTraddCtrcts>
              <FinInstrmQty>1</FinInstrmQty><OpnIntrst>1</OpnIntrst>
              <FrstPric>1</FrstPric><MinPric>1</MinPric>
              <MaxPric>1</MaxPric><LastPric>1</LastPric></FinInstrmAttrbts>
            </PricRpt></Document></BizGrp>"""
        xml = ("<root>" + row("WINQ26") + row("WDOQ26") + row("WDOQ26C005500") + "</root>").encode()

        _, prefix_counts, future_counts, complete, samples = probe.scan(xml)

        self.assertEqual(prefix_counts, {"WIN": 1, "WDO": 2})
        self.assertEqual(future_counts, {"WIN": 1, "WDO": 1})
        self.assertEqual(complete, {"WIN": 1, "WDO": 1})
        self.assertEqual(samples, ["WINQ26", "WDOQ26"])

    def test_latest_xml_member_is_selected_deterministically(self):
        nested = io.BytesIO()
        with zipfile.ZipFile(nested, "w", zipfile.ZIP_DEFLATED) as inner:
            early = zipfile.ZipInfo("early.xml", date_time=(2026, 8, 7, 17, 0, 0))
            late = zipfile.ZipInfo("late.xml", date_time=(2026, 8, 7, 19, 0, 0))
            inner.writestr(early, b"<root><value>early</value></root>")
            inner.writestr(late, b"<root><value>late</value></root>")
        outer = io.BytesIO()
        with zipfile.ZipFile(outer, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("PR260807.zip", nested.getvalue())

        name, raw, nested_name, nested_hash, member_count, rejected, _ = probe.xml_from(outer.getvalue())

        self.assertEqual(name, "late.xml")
        self.assertIn(b"late", raw)
        self.assertEqual(nested_name, "PR260807.zip")
        self.assertEqual(len(nested_hash), 64)
        self.assertEqual(member_count, 2)
        self.assertEqual(rejected, [])

    def test_malformed_latest_xml_falls_back_and_is_recorded(self):
        nested = io.BytesIO()
        with zipfile.ZipFile(nested, "w", zipfile.ZIP_DEFLATED) as inner:
            early = zipfile.ZipInfo("valid.xml", date_time=(2021, 1, 4, 17, 0, 0))
            late = zipfile.ZipInfo("malformed.xml", date_time=(2021, 1, 4, 19, 0, 0))
            inner.writestr(early, b"<root />")
            inner.writestr(late, b"<root><broken></root>")
        outer = io.BytesIO()
        with zipfile.ZipFile(outer, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("PR210104.zip", nested.getvalue())

        name, _, _, _, _, rejected, _ = probe.xml_from(outer.getvalue())

        self.assertEqual(name, "valid.xml")
        self.assertEqual([item["xml_name"] for item in rejected], ["malformed.xml"])


if __name__ == "__main__":
    unittest.main()
