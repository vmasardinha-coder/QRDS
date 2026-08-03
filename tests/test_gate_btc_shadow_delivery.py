from __future__ import annotations

import json
import os
import tempfile
import unittest
import zipfile
from pathlib import Path

from tools import gate_btc_shadow_delivery as delivery


class ShadowDeliveryTests(unittest.TestCase):
    def _handoff(self, root: Path) -> Path:
        handoff = root / "handoff"
        handoff.mkdir()
        payload = {
            "status": "PASS_WITH_DATA_WARNINGS",
            "stage_reached": "DAILY_V2A_DELTA_GATEWAY_COLLECTION_VALIDATED",
            "data_cutoff": "2026-08-02",
            "research_only": True,
            "orders_generated": 0,
            "real_capital_used": 0,
            "operational_status": "NOT_APPROVED",
            "retrospective_gateway_performance": "PROHIBITED",
            "methodology_changes": 0,
            "components": {name: {"status": "PASS"} for name in ("v2a", "delta", "gateway_upstream", "gateway_downstream")},
            "report_delivery": {"inputs_ready": True},
        }
        (handoff / "GATE_BTC_DAILY_RESEARCH_MANIFEST.json").write_text(json.dumps(payload), encoding="utf-8")
        (handoff / "GATE_BTC_DAILY_RESEARCH_REPORT.txt").write_text("PASS\n", encoding="utf-8")
        with zipfile.ZipFile(handoff / "GATE_BTC_DAILY_RESEARCH_EVIDENCE.zip", "w") as archive:
            archive.writestr("evidence.txt", "PASS")
        return handoff

    def test_request_binds_run_and_exact_three_reports(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            handoff = self._handoff(root)
            output = root / "request.json"
            keys = ("GITHUB_RUN_ID", "GITHUB_RUN_ATTEMPT", "GITHUB_SHA", "GITHUB_REPOSITORY", "GATE_BTC_REPORT_DATE")
            old = {key: os.environ.get(key) for key in keys}
            os.environ.update({
                "GITHUB_RUN_ID": "123",
                "GITHUB_RUN_ATTEMPT": "2",
                "GITHUB_SHA": "abc123",
                "GITHUB_REPOSITORY": "owner/repo",
                "GATE_BTC_REPORT_DATE": "2026-08-03",
            })
            try:
                request = delivery.build_request(handoff, output)
            finally:
                for key, value in old.items():
                    if value is None:
                        os.environ.pop(key, None)
                    else:
                        os.environ[key] = value
            self.assertEqual(request["delivery_id"], "2026-08-03--cutoff-2026-08-02--run-123--attempt-2")
            self.assertEqual(request["source"]["report_date"], "2026-08-03")
            self.assertEqual(request["source"]["data_cutoff"], "2026-08-02")
            self.assertEqual(request["contract"]["expected_pdf_count"], 3)
            self.assertEqual(len(request["contract"]["reports"]), 3)
            self.assertTrue(all("2026-08-03" in item["filename"] for item in request["contract"]["reports"]))
            self.assertEqual(request["source"]["head_sha"], "abc123")

    def test_receipt_rejects_missing_or_extra_pdf(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            request_path = root / "request.json"
            request = {
                "schema": "gate-btc-shadow-delivery-request-v1",
                "status": "READY_FOR_RENDER",
                "delivery_id": "x",
                "duplicate_key": "y",
                "source": {},
                "contract": {
                    "expected_pdf_count": 3,
                    "reports": [
                        {"position": i, "role": role, "filename": pattern.format(date="2026-08-03")}
                        for i, (role, pattern) in enumerate(delivery.REPORT_ROLES, start=1)
                    ],
                },
            }
            request_path.write_text(json.dumps(request), encoding="utf-8")
            reports = root / "reports"
            reports.mkdir()
            for _, pattern in delivery.REPORT_ROLES[:2]:
                (reports / pattern.format(date="2026-08-03")).write_bytes(b"%PDF-1.4\n" + b"x" * 1100 + b"\n%%EOF\n")
            with self.assertRaises(RuntimeError):
                delivery.build_receipt(request_path, reports, root / "receipt.json")

    def test_receipt_passes_only_exact_pdf_set(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            request_path = root / "request.json"
            expected = [
                {"position": i, "role": role, "filename": pattern.format(date="2026-08-03")}
                for i, (role, pattern) in enumerate(delivery.REPORT_ROLES, start=1)
            ]
            request = {
                "schema": "gate-btc-shadow-delivery-request-v1",
                "status": "READY_FOR_RENDER",
                "delivery_id": "x",
                "duplicate_key": "y",
                "source": {"run_id": "1"},
                "contract": {"expected_pdf_count": 3, "reports": expected},
            }
            request_path.write_text(json.dumps(request), encoding="utf-8")
            reports = root / "reports"
            reports.mkdir()
            for item in expected:
                (reports / item["filename"]).write_bytes(b"%PDF-1.4\n" + b"x" * 1100 + b"\n%%EOF\n")
            receipt = delivery.build_receipt(request_path, reports, root / "receipt.json")
            self.assertEqual(receipt["status"], "PASS")
            self.assertEqual(receipt["exact_report_count"], 3)
            self.assertEqual(len(receipt["reports"]), 3)


if __name__ == "__main__":
    unittest.main()
