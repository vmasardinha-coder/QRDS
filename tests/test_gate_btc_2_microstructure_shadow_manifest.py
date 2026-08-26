import copy
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from tools.gate_btc_2_microstructure_shadow_contract import assess
from tools.gate_btc_2_microstructure_shadow_manifest import (
    DEFAULT_CONTRACT,
    SPECS,
    build_manifest,
)


CAPTURE_MS = 1787731200000
CAPTURE_UTC = "2026-08-26T08:00:00Z"


def payloads():
    return {
        "FUNDING": {"symbol": "BTCUSDT", "lastFundingRate": "0.0001", "nextFundingTime": CAPTURE_MS + 1000, "time": CAPTURE_MS},
        "OPEN_INTEREST": {"symbol": "BTCUSDT", "openInterest": "12345.67", "time": CAPTURE_MS},
        "PERP_VOLUME": {"symbol": "BTCUSDT", "volume": "100", "quoteVolume": "5000000", "openTime": CAPTURE_MS - 86400000, "closeTime": CAPTURE_MS, "count": 1000},
        "SPOT_VOLUME": {"symbol": "BTCUSDT", "volume": "80", "quoteVolume": "4000000", "openTime": CAPTURE_MS - 86400000, "closeTime": CAPTURE_MS, "count": 800},
    }


def receipt(contract):
    return {
        "schema": "gate_btc.2_0.microstructure_shadow_capture_receipt.v1",
        "capture_id": "fixture-20260826T080000Z",
        "created_at_utc": CAPTURE_UTC,
        "contract_sha256": contract["contract_sha256"],
        "forward_only": True,
        "historical_rows_backfilled": 0,
        "recovered_historical": False,
        "network_capture_job_count": 1,
        "sources": [
            {"source_role": role, "raw_file": spec["raw_file"], "request_url": spec["url"], "captured_at_utc": CAPTURE_UTC}
            for role, spec in SPECS.items()
        ],
    }


class MicrostructureShadowManifestTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = json.loads(DEFAULT_CONTRACT.read_text(encoding="utf-8"))

    def build(self, mutate=None, receipt_mutate=None):
        raw = payloads()
        rec = receipt(self.contract)
        if mutate:
            mutate(raw)
        if receipt_mutate:
            receipt_mutate(rec)
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            raw_bytes = {}
            for role, payload in raw.items():
                value = (json.dumps(payload, separators=(",", ":")) + "\n").encode()
                raw_bytes[role] = value
                (root / SPECS[role]["raw_file"]).write_bytes(value)
            return build_manifest(rec, root, self.contract), raw_bytes

    def test_valid_bytes_build_contract_admitted_manifest(self):
        manifest, raw = self.build()
        self.assertEqual(assess(self.contract, manifest)["status"], "READY_FOR_FORWARD_CAPTURE_REVIEW")
        self.assertEqual([row["source_role"] for row in manifest["sources"]], list(SPECS))
        self.assertEqual(manifest["historical_rows_backfilled"], 0)
        self.assertFalse(manifest["recovered_historical"])
        self.assertEqual(manifest["network_capture_job_count"], 1)
        self.assertEqual(len({row["content_sha256"] for row in manifest["sources"]}), 4)

    def test_wrong_symbol_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "symbol is not BTCUSDT"):
            self.build(lambda raw: raw["FUNDING"].update(symbol="ETHUSDT"))

    def test_missing_role_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "each required source role exactly once"):
            self.build(receipt_mutate=lambda rec: rec["sources"].pop())

    def test_endpoint_substitution_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "differs from the frozen public endpoint"):
            self.build(receipt_mutate=lambda rec: rec["sources"][0].update(request_url="https://example.invalid"))

    def test_historical_or_second_network_job_fails_closed(self):
        for field, value in (("historical_rows_backfilled", 1), ("network_capture_job_count", 2)):
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, "violates backfill or network-job budget"):
                self.build(receipt_mutate=lambda rec, f=field, v=value: rec.update({f: v}))

    def test_stale_payload_fails_closed(self):
        stale = CAPTURE_MS - 601000
        with self.assertRaisesRegex(ValueError, "payload is stale"):
            self.build(lambda raw: raw["OPEN_INTEREST"].update(time=stale))

    def test_future_provider_timestamp_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "temporal order is invalid"):
            self.build(lambda raw: raw["FUNDING"].update(time=CAPTURE_MS + 1))

    def test_invalid_numeric_value_fails_closed(self):
        for value in ("nan", "inf", "-1"):
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, "outside the admitted range"):
                self.build(lambda raw, v=value: raw["OPEN_INTEREST"].update(openInterest=v))

    def test_negative_funding_is_valid_market_data(self):
        manifest, _ = self.build(lambda raw: raw["FUNDING"].update(lastFundingRate="-0.0001"))
        self.assertEqual(assess(self.contract, manifest)["status"], "READY_FOR_FORWARD_CAPTURE_REVIEW")

    def test_module_is_offline_by_construction(self):
        source = (Path(__file__).resolve().parents[1] / "tools" / "gate_btc_2_microstructure_shadow_manifest.py").read_text()
        self.assertNotIn("import requests", source)
        self.assertNotIn("import urllib", source)
        self.assertNotIn("urlopen", source)


if __name__ == "__main__":
    unittest.main()
