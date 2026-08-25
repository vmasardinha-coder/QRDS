from __future__ import annotations

import io
import sys
import unittest
import zipfile
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
for path in (ROOT, TOOLS):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

try:
    import requests
except ModuleNotFoundError:  # Keep the repository's dependency-light local suite runnable.
    import pip._vendor.requests as requests

    sys.modules["requests"] = requests

from tools import gate_btc_b3_h120_h129_economics as economics
from tools import gate_btc_b3_h120_h129_source_probe as source_probe


class FakeResponse:
    def __init__(self, content: bytes):
        self.content = content

    def raise_for_status(self):
        return None


def price_report(rows):
    fields = []
    for ticker, volume in rows:
        fields.append(
            "<row>"
            f"<TckrSymb>{ticker}</TckrSymb>"
            "<TradQty>10</TradQty>"
            f"<FinInstrmQty>{volume}</FinInstrmQty>"
            "<OpnIntrst>100</OpnIntrst>"
            "<FrstPric>100</FrstPric>"
            "<MinPric>90</MinPric>"
            "<MaxPric>110</MaxPric>"
            "<LastPric>105</LastPric>"
            "</row>"
        )
    xml = ("<root>" + "".join(fields) + "</root>").encode()
    body = io.BytesIO()
    with zipfile.ZipFile(body, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("PriceReport.xml", xml)
    return body.getvalue()


class H120H129ContractIdentityTests(unittest.TestCase):
    def test_source_qa_and_economics_share_exact_identity_contract(self):
        self.assertEqual(economics.FUTURE_RE.pattern, source_probe.FUTURE_RE.pattern)

    def test_front_selection_excludes_higher_volume_option(self):
        response = FakeResponse(
            price_report(
                [
                    ("WINQ26", 200),
                    ("WDOQ26", 100),
                    ("WDOQ26C005500", 100000),
                ]
            )
        )

        with mock.patch.object(economics.requests, "get", return_value=response):
            result = economics.parse_day("2026-08-07")

        self.assertEqual(result["status"], "PASS")
        selected = {row["asset"]: row for row in result["rows"]}
        self.assertEqual(selected["WIN"]["ticker"], "WINQ26")
        self.assertEqual(selected["WDO"]["ticker"], "WDOQ26")
        self.assertEqual(selected["WDO"]["volume"], 100.0)

    def test_option_cannot_satisfy_missing_wdo_future(self):
        response = FakeResponse(price_report([("WINQ26", 200), ("WDOQ26P005500", 100000)]))

        with mock.patch.object(economics.requests, "get", return_value=response):
            result = economics.parse_day("2026-08-07")

        self.assertEqual(result["status"], "DATA_GAP_ASSET")
        self.assertEqual([row["ticker"] for row in result["rows"]], ["WINQ26"])


if __name__ == "__main__":
    unittest.main()
