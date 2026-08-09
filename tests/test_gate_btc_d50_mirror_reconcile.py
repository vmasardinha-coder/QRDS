import csv
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from tools.gate_btc_d50_mirror_reconcile import ReconciliationError, build_audit


CORE = (
    ("D50_CONTROL", "CONTROL"),
    ("D50_COST_AWARE", "PRIMARY_PROMOTION_ELIGIBLE"),
    ("D50_EXIT_2SIGMA", "EXPLORATORY"),
)
DATES = [
    "2026-07-31",
    "2026-08-01",
    "2026-08-02",
    "2026-08-03",
    "2026-08-06",
    "2026-08-07",
    "2026-08-08",
]
FIELDS = [
    "record_type",
    "observation_number",
    "strategy",
    "role",
    "date",
    "bar_close_at_utc",
    "gate_anchor_utc",
    "first_retrieved_at_utc",
    "gross_return",
    "trading_cost_return",
    "funding_return",
    "net_return",
    "equity_from_anchor",
    "turnover",
    "gross_long",
    "gross_short_abs",
    "net_exposure",
    "kill_switch_active",
    "vol_scale",
    "source_bar_sha256",
    "replay_row_sha256",
    "status",
    "orders",
    "capital",
]


def digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def rows_for_dates(dates):
    rows = []
    for observation_number, day in enumerate(dates, start=1):
        source_hash = digest(f"source:{day}")
        for strategy_index, (strategy, role) in enumerate(CORE):
            gross = 0.001 * (observation_number + strategy_index + 1)
            cost = 0.0001 * (strategy_index + 1)
            funding = -0.00001 * strategy_index
            net = gross - cost + funding
            rows.append(
                {
                    "record_type": "PROSPECTIVE_DAILY_RETURN",
                    "observation_number": str(observation_number),
                    "strategy": strategy,
                    "role": role,
                    "date": day,
                    "bar_close_at_utc": f"{day}T20:00:00+00:00",
                    "gate_anchor_utc": "2026-07-31T16:59:39+00:00",
                    "first_retrieved_at_utc": f"{day}T20:10:00+00:00",
                    "gross_return": str(gross),
                    "trading_cost_return": str(cost),
                    "funding_return": str(funding),
                    "net_return": str(net),
                    "equity_from_anchor": str(1.0 + net),
                    "turnover": str(0.1 + 0.01 * strategy_index),
                    "gross_long": "0.5",
                    "gross_short_abs": "0.5",
                    "net_exposure": "0.0",
                    "kill_switch_active": "False",
                    "vol_scale": "",
                    "source_bar_sha256": source_hash,
                    "replay_row_sha256": digest(f"replay:{day}:{strategy}"),
                    "status": "ADMITTED_BY_FROZEN_GATE",
                    "orders": "0",
                    "capital": "0",
                }
            )
    return rows


def write_csv(path: Path, rows):
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def local_status():
    return {
        "status": "PASS_PROSPECTIVE_ROWS_APPENDED",
        "gate_anchor_utc": "2026-07-31T16:59:39+00:00",
        "paired_prospective_observations": 7,
        "first_prospective_date": DATES[0],
        "latest_prospective_date": DATES[-1],
        "excluded_historical_backfill_dates": ["2026-08-04", "2026-08-05"],
        "historical_backfill_counted_as_prospective": False,
        "research_only": True,
        "operational_status": "NOT_APPROVED",
        "orders": 0,
        "capital": 0,
    }


def remote_status(current=4):
    return {
        "schema": "gate_btc.d50_measurement_status.v1",
        "data_as_of": "2026-08-06",
        "research_only": True,
        "shadow_only": True,
        "not_approved": True,
        "promotion_allowed": False,
        "orders_generated": 0,
        "real_capital_used": 0,
        "prospective_immutable_ledger": {
            "current": current,
            "target": 30,
            "status": "BLOCKED_LOCAL_SOURCE_REVISION_REPAIR_PENDING",
            "source_revision_only": True,
            "economic_fields_identical": True,
            "frozen_history_must_be_preserved": True,
            "mutation_performed": False,
        },
    }


class D50MirrorReconcileTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.local_status_path = self.root / "D50_PROSPECTIVE_STATUS_V2.json"
        self.local_ledger_path = self.root / "d50_prospective_observations_v2.csv"
        self.remote_status_path = self.root / "STATUS.json"
        self.prior_ledger_path = self.root / "prior_d50_prospective_observations_v2.csv"
        self.diagnostics_dir = self.root / "diagnostics"
        self.repair_result_path = self.root / "RESULTADO_FINAL.txt"

        self.local_rows = rows_for_dates(DATES)
        write_csv(self.local_ledger_path, self.local_rows)
        write_csv(self.prior_ledger_path, rows_for_dates(DATES[:4]))
        self.local_status_path.write_text(json.dumps(local_status()), encoding="utf-8")
        self.remote_status_path.write_text(json.dumps(remote_status()), encoding="utf-8")
        self.diagnostics_dir.mkdir()
        diagnostic = {
            "schema": "gate_btc.d50_source_revision_diagnostic.v1",
            "status": "PASS_PROVENANCE_ONLY_FROZEN_ROW_PRESERVED",
            "date": "2026-08-01",
            "strategy": "D50_CONTROL",
            "economic_fields_identical": True,
            "source_revision_detected": True,
            "frozen_row_preserved": True,
            "mutation_performed": False,
            "counter_incremented_for_existing_date": False,
            "research_only": True,
            "shadow_only": True,
            "not_approved": True,
            "promotion_allowed": False,
            "orders": 0,
            "capital": 0,
        }
        (self.diagnostics_dir / "revision.json").write_text(json.dumps(diagnostic), encoding="utf-8")
        self.repair_result_path.write_text(
            "\n".join(
                [
                    "STATUS=PASS_REPAIR_COMPLETE",
                    "FROZEN_ROWS_PRESERVED=True",
                    "RESEARCH_ONLY=True",
                    "OPERATIONAL_STATUS=NOT_APPROVED",
                    "ORDERS=0",
                    "CAPITAL=0",
                ]
            )
            + "\n",
            encoding="utf-8",
        )

    def tearDown(self):
        self.temp.cleanup()

    def build(self):
        return build_audit(
            local_status_path=self.local_status_path,
            local_ledger_path=self.local_ledger_path,
            remote_status_path=self.remote_status_path,
            prior_ledger_path=self.prior_ledger_path,
            diagnostics_dir=self.diagnostics_dir,
            repair_result_path=self.repair_result_path,
        )

    def test_passes_forward_only_4_to_7_candidate_without_mutating_inputs(self):
        before = {
            path: hashlib.sha256(path.read_bytes()).hexdigest()
            for path in (
                self.local_status_path,
                self.local_ledger_path,
                self.remote_status_path,
                self.prior_ledger_path,
            )
        }
        audit = self.build()
        after = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in before}

        self.assertEqual(before, after)
        self.assertEqual(audit["status"], "PASS_MIRROR_ADVANCE_CANDIDATE")
        self.assertEqual(audit["remote_mirror"]["current"], 4)
        self.assertEqual(audit["local_checkpoint"]["paired_observations"], 7)
        self.assertEqual(audit["local_checkpoint"]["latest_date"], "2026-08-08")
        self.assertTrue(audit["frozen_prefix_evidence"]["frozen_prefix_preserved"])
        self.assertEqual(audit["source_revision_evidence"]["count"], 1)
        self.assertFalse(audit["runtime_mutation_performed"])
        self.assertEqual(audit["orders_generated"], 0)
        self.assertEqual(audit["real_capital_used"], 0)

    def test_rejects_changed_frozen_prefix(self):
        changed = list(self.local_rows)
        changed[0] = dict(changed[0])
        changed[0]["net_return"] = "0.999"
        write_csv(self.local_ledger_path, changed)
        with self.assertRaisesRegex(ReconciliationError, "frozen prior row changed"):
            self.build()

    def test_rejects_historical_backfill_counted_as_prospective(self):
        status = local_status()
        status["historical_backfill_counted_as_prospective"] = True
        self.local_status_path.write_text(json.dumps(status), encoding="utf-8")
        with self.assertRaisesRegex(ReconciliationError, "Historical backfill|historical backfill"):
            self.build()

    def test_rejects_nonzero_orders(self):
        status = local_status()
        status["orders"] = 1
        self.local_status_path.write_text(json.dumps(status), encoding="utf-8")
        with self.assertRaisesRegex(ReconciliationError, "safety invariant changed"):
            self.build()

    def test_rejects_remote_mirror_ahead_of_local_checkpoint(self):
        self.remote_status_path.write_text(json.dumps(remote_status(current=8)), encoding="utf-8")
        with self.assertRaisesRegex(ReconciliationError, "remote mirror leads local checkpoint"):
            self.build()

    def test_blocked_source_revision_requires_full_proof_pack(self):
        with self.assertRaisesRegex(ReconciliationError, "prior ledger is required"):
            build_audit(
                local_status_path=self.local_status_path,
                local_ledger_path=self.local_ledger_path,
                remote_status_path=self.remote_status_path,
            )


if __name__ == "__main__":
    unittest.main()
