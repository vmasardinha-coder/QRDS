import json
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path

from tools.gate_btc_lock_reanchor import reanchor
from tools.gate_btc_measurement_common import atomic_json, canonical_sha, file_sha
from tests.test_gate_btc_measurement_ledgers import CONFIG, CONTRACT, current_signal


class LockReanchorTests(unittest.TestCase):
    def test_preserves_interrupted_series_and_prohibits_gap_fill(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ledger = root / "lock25_50"
            (ledger / "snapshots").mkdir(parents=True)
            (ledger / "diagnostics").mkdir()
            contract = root / "contract.json"
            contract.write_text(json.dumps(CONTRACT), encoding="utf-8")
            config = root / "config.json"
            config.write_text(json.dumps(CONFIG), encoding="utf-8")

            anchor = {
                "cycle_id": "OLD",
                "first_eligible_close": "2026-08-06",
                "config_sha256": file_sha(contract),
            }
            anchor["anchor_sha256"] = canonical_sha(anchor, "anchor_sha256")
            atomic_json(ledger / "ANCHOR.json", anchor)
            source = {"cycle_id": "OLD", "contract_anchor_sha256": anchor["anchor_sha256"]}
            source["source_anchor_sha256"] = canonical_sha(source, "source_anchor_sha256")
            atomic_json(ledger / "SOURCE_ANCHOR.json", source)
            atomic_json(ledger / "STATUS.json", {"cycle_id": "OLD", "valid_snapshot_count": 3})
            for sequence, day in enumerate(("2026-08-06", "2026-08-07", "2026-08-08"), start=1):
                snapshot = {"snapshot_id": day, "sequence": sequence}
                snapshot["snapshot_sha256"] = canonical_sha(snapshot, "snapshot_sha256")
                atomic_json(ledger / "snapshots" / f"{day}.json", snapshot)
            for day in ("2026-08-09", "2026-08-10", "2026-08-11", "2026-08-12", "2026-08-13", "2026-08-14", "2026-08-15"):
                atomic_json(ledger / "diagnostics" / f"{day}.json", {"snapshot_id": day, "snapshot_appended": False})

            current = root / "current.csv"
            current.write_text(current_signal("2026-08-15", "2026-08-16"), encoding="utf-8")
            monthly = root / "monthly.csv"
            monthly.write_text(
                "signal_date,execution_date,strategy,asset,weight,regime\n"
                "2026-07-31,2026-08-01,QOS_Moderada,BTC,1,DEFENSIVE\n"
                "2026-07-31,2026-08-01,QOS_Ultra,BTC,1,DEFENSIVE\n",
                encoding="utf-8",
            )
            equity = root / "equity.csv"
            equity.write_text(
                "date,strategy,equity_brl,drawdown\n"
                "2026-08-15,QOS_Moderada,100,0\n"
                "2026-08-15,QOS_Ultra,200,0\n",
                encoding="utf-8",
            )
            args = Namespace(
                ledger_dir=ledger,
                contract=contract,
                old_cycle_id="OLD",
                new_cycle_id="NEW",
                base_date="2026-08-15",
                first_eligible_close="2026-08-16",
                preserved_date=["2026-08-06", "2026-08-07", "2026-08-08"],
                excluded_date=["2026-08-09", "2026-08-10", "2026-08-11", "2026-08-12", "2026-08-13", "2026-08-14", "2026-08-15"],
                authorized_at_utc="2026-08-16T13:00:00Z",
                authorization_text="authorized",
                interruption_reason="held asset left top-150 valuation download cohort",
                current_portfolios=current,
                monthly_allocations=monthly,
                equity_curves=equity,
                v2a_config=config,
                source_run_id=1,
                source_artifact_sha256="a" * 64,
            )
            result = reanchor(args)
            self.assertEqual(result["status"], "REANCHORED_WAITING_FIRST_UNTOUCHED_CLOSE")
            archive = ledger / "interrupted_series" / "OLD"
            self.assertTrue((archive / "snapshots/2026-08-06.json").is_file())
            self.assertTrue((archive / "snapshots/2026-08-08.json").is_file())
            self.assertFalse((ledger / "snapshots/2026-08-08.json").exists())
            interruption = json.loads((archive / "INTERRUPTION.json").read_text(encoding="utf-8"))
            self.assertFalse(interruption["retroactive_fill_allowed"])
            self.assertEqual(interruption["interrupted_gap_dates"][0], "2026-08-09")
            status = json.loads((ledger / "STATUS.json").read_text(encoding="utf-8"))
            self.assertEqual(status["cycle_id"], "NEW")
            self.assertEqual(status["valid_snapshot_count"], 0)
            self.assertEqual(status["retroactive_fill_prohibited_dates"][-1], "2026-08-15")
            self.assertEqual(reanchor(args), result)
            incomplete = Namespace(**vars(args))
            incomplete.excluded_date = [
                day for day in args.excluded_date if day != "2026-08-10"
            ]
            with self.assertRaisesRegex(RuntimeError, "every interrupted gap date"):
                reanchor(incomplete)


if __name__ == "__main__":
    unittest.main()
