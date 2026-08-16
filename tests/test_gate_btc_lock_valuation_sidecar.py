import json
import tempfile
import unittest
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from tools.gate_btc_lock_valuation_sidecar import build_sidecar, validate_sidecar
from tools.gate_btc_measurement_common import canonical_sha


def signal(weights):
    return {"weights": weights}


class LockValuationSidecarTests(unittest.TestCase):
    def test_collects_missing_held_asset_without_changing_selection_master(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ledger = root / "ledger"
            ledger.mkdir()
            (ledger / "ANCHOR.json").write_text(json.dumps({
                "cycle_id": "CYCLE_2026_08_16",
                "first_eligible_close": "2026-08-16",
            }), encoding="utf-8")
            (ledger / "SOURCE_ANCHOR.json").write_text(json.dumps({
                "base_date": "2026-08-15",
                "portfolios": {
                    "QOS_Moderada": {"initial_eligible_signal": signal({"BTC": 0.5, "KAITO": 0.5})},
                    "QOS_Ultra": {"initial_eligible_signal": signal({"BTC": 0.5, "KAITO": 0.5})},
                },
            }), encoding="utf-8")
            archive = root / "v2a.zip"
            with zipfile.ZipFile(archive, "w") as zf:
                zf.writestr(
                    "data/processed/qos_v2a_master_daily.csv",
                    "date,symbol,close_usd,volume_usd,source\n"
                    "2026-08-15,BTC,100,1,cdd\n"
                    "2026-08-16,BTC,101,1,cdd\n"
                    "2026-08-15,KAITO,2,1,okx\n",
                )

            calls = []

            def cdd(symbol):
                calls.append(("cdd", symbol))
                return ({"2026-08-15": {"close_usd": 2, "confirmed": True}}, "a" * 64, "https://cdd")

            def binance(symbol):
                calls.append(("binance", symbol))
                return ({
                    "2026-08-15": {"close_usd": 2, "confirmed": True},
                    "2026-08-16": {"close_usd": 2.2, "confirmed": True},
                }, "b" * 64, "https://binance")

            payload = build_sidecar(
                v2a_zip=archive,
                ledger_dir=ledger,
                snapshot_id="2026-08-16",
                fetchers={"cdd": cdd, "binance": binance, "okx": lambda symbol: ({}, "c" * 64, "https://okx")},
                generated_at=datetime(2026, 8, 17, 0, 20, tzinfo=timezone.utc),
            )
            self.assertEqual(payload["status"], "PASS_EXACT_ACTIVE_HOLDING_CLOSES")
            self.assertFalse(payload["engine_feed"])
            self.assertFalse(payload["selection_membership_changed"])
            self.assertIn(("cdd", "KAITO"), calls)
            self.assertIn(("binance", "KAITO"), calls)
            selected = [row for row in payload["observations"] if row["symbol"] == "KAITO"]
            self.assertEqual({row["source"] for row in selected}, {"binance"})
            values = validate_sidecar(
                payload,
                snapshot_id="2026-08-16",
                prior_date="2026-08-15",
                required_assets={"BTC", "KAITO"},
            )
            self.assertEqual(values["KAITO:current"], 2.2)

            payload["observations"][-1]["source"] = "okx"
            payload["sidecar_sha256"] = canonical_sha(payload, "sidecar_sha256")
            with self.assertRaisesRegex(RuntimeError, "one source"):
                validate_sidecar(
                    payload,
                    snapshot_id="2026-08-16",
                    prior_date="2026-08-15",
                    required_assets={"BTC", "KAITO"},
                )

    def test_fails_closed_when_no_source_has_both_exact_closes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ledger = root / "ledger"
            ledger.mkdir()
            (ledger / "ANCHOR.json").write_text(json.dumps({
                "cycle_id": "CYCLE", "first_eligible_close": "2026-08-16",
            }), encoding="utf-8")
            (ledger / "SOURCE_ANCHOR.json").write_text(json.dumps({
                "base_date": "2026-08-15",
                "portfolios": {
                    "QOS_Moderada": {"initial_eligible_signal": signal({"KAITO": 1.0})},
                    "QOS_Ultra": {"initial_eligible_signal": signal({"KAITO": 1.0})},
                },
            }), encoding="utf-8")
            archive = root / "v2a.zip"
            with zipfile.ZipFile(archive, "w") as zf:
                zf.writestr("data/processed/qos_v2a_master_daily.csv", "date,symbol,close_usd\n")
            empty = lambda symbol: ({}, "0" * 64, "https://source")
            with self.assertRaisesRegex(RuntimeError, "exact valuation pair unavailable"):
                build_sidecar(
                    v2a_zip=archive,
                    ledger_dir=ledger,
                    snapshot_id="2026-08-16",
                    fetchers={"cdd": empty, "binance": empty, "okx": empty},
                )


if __name__ == "__main__":
    unittest.main()
