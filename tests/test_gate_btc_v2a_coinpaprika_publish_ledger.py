from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from tools.gate_btc_v2a_coinpaprika_publish_ledger import seal


class DurableLedgerTests(unittest.TestCase):
    def test_waiting_produces_no_runtime_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            evidence = root / "evidence"
            sub = evidence / "coinpaprika_epoch_v1"
            (sub / "market_identity").mkdir(parents=True)
            (sub / "closed_candles").mkdir()
            raw = b"[]"
            (evidence / "COINPAPRIKA_RAW.json").write_bytes(raw)
            (evidence / "COINPAPRIKA_TOP250.json").write_text(json.dumps([
                {"id": f"coin-{n}"} for n in range(250)]))
            (sub / "SERIES.json").write_text(json.dumps({"family_id": "V2A_COINPAPRIKA_V1",
                "engine_feed": False, "scientific_credit": 0, "raw_sha256": hashlib.sha256(raw).hexdigest()}))
            (sub / "market_identity/MARKET_IDENTITY.json").write_text(json.dumps({
                "family_id": "V2A_COINPAPRIKA_V1", "engine_feed": False, "scientific_credit": 0,
                "ticker_raw_sha256": hashlib.sha256(raw).hexdigest()}))
            (sub / "closed_candles/CLOSED_CANDLES.json").write_text(json.dumps({
                "family_id": "V2A_COINPAPRIKA_V1", "engine_feed": False, "scientific_credit": 0,
                "state": "WAIT_FIRST_FULL_PROSPECTIVE_CLOSE", "target_utc_close_date": None,
                "observed_closed_candle_count": 0}))
            runtime = root / "runtime"
            result = seal(evidence, runtime, {"family_id": "V2A_COINPAPRIKA_V1"},
                          datetime(2026, 9, 29, 20, tzinfo=timezone.utc))
            self.assertEqual(result, "WAIT_FIRST_FULL_PROSPECTIVE_CLOSE")
            self.assertFalse(runtime.exists())

    def test_rejects_ticker_hash_mismatch_before_seal(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sub = root / "evidence/coinpaprika_epoch_v1"
            (sub / "market_identity").mkdir(parents=True)
            (sub / "closed_candles").mkdir()
            (root / "evidence/COINPAPRIKA_RAW.json").write_bytes(b"tampered")
            (sub / "SERIES.json").write_text(json.dumps({"family_id": "V2A_COINPAPRIKA_V1",
                "engine_feed": False, "scientific_credit": 0, "raw_sha256": "wrong"}))
            (sub / "market_identity/MARKET_IDENTITY.json").write_text(json.dumps({
                "family_id": "V2A_COINPAPRIKA_V1", "engine_feed": False, "scientific_credit": 0}))
            (sub / "closed_candles/CLOSED_CANDLES.json").write_text(json.dumps({
                "family_id": "V2A_COINPAPRIKA_V1", "engine_feed": False, "scientific_credit": 0}))
            with self.assertRaisesRegex(ValueError, "ticker source hash mismatch"):
                seal(root / "evidence", root / "runtime", {"family_id": "V2A_COINPAPRIKA_V1"},
                     datetime(2026, 10, 1, 20, tzinfo=timezone.utc))

    def test_seals_valid_close_once_and_preserves_immutable_archive(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            evidence = root / "evidence"
            sub = evidence / "coinpaprika_epoch_v1"
            (sub / "market_identity").mkdir(parents=True)
            (sub / "closed_candles").mkdir()
            raw = b"[]"
            raw_hash = hashlib.sha256(raw).hexdigest()
            (evidence / "COINPAPRIKA_RAW.json").write_bytes(raw)
            (evidence / "COINPAPRIKA_TOP250.json").write_text(json.dumps([
                {"id": "btc-bitcoin" if n == 0 else f"coin-{n}"} for n in range(250)]))
            base = {"family_id": "V2A_COINPAPRIKA_V1", "engine_feed": False, "scientific_credit": 0}
            (sub / "SERIES.json").write_text(json.dumps({**base, "raw_sha256": raw_hash}))
            row = {"coinpaprika_id": "btc-bitcoin", "symbol": "BTC",
                   "status": "EXACT_MARKET_IDENTITY_CONFIRMED", "source_identity": "BINANCE_SPOT",
                   "source_symbol": "BTCUSDT"}
            (sub / "market_identity/MARKET_IDENTITY.json").write_text(json.dumps({
                **base, "ticker_raw_sha256": raw_hash, "confirmed_market_identity_count": 1,
                "rows": [row]}))
            start = 1790726400000
            candle_raw = json.dumps([[start, "1", "2", "0.5", "1.5", "10",
                                      start + 86_400_000 - 1, "15"]]).encode()
            (sub / "closed_candles/btc-bitcoin.candle.json").write_bytes(candle_raw)
            (sub / "closed_candles/CLOSED_CANDLES.json").write_text(json.dumps({
                **base, "state": "PARTIAL_CLOSED_CANDLE_OBSERVATION",
                "target_utc_close_date": "2026-09-30", "observed_closed_candle_count": 1,
                "gaps": [], "candles": [{**row, "utc_close_date": "2026-09-30",
                    "close_usd": 1.5, "raw_sha256": hashlib.sha256(candle_raw).hexdigest()}]}))
            runtime = root / "runtime"
            genesis = {"family_id": "V2A_COINPAPRIKA_V1", "first_full_prospective_utc_date": "2026-09-30"}
            now = datetime(2026, 10, 1, 12, tzinfo=timezone.utc)
            self.assertEqual(seal(evidence, runtime, genesis, now), "SEALED_NEW_FULL_CLOSE")
            self.assertEqual(seal(evidence, runtime, genesis, now), "ALREADY_SEALED_NO_OVERWRITE")


if __name__ == "__main__":
    unittest.main()
