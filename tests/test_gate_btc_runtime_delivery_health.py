import argparse
import json
import tempfile
import unittest
import urllib.request
from datetime import date
from pathlib import Path

from tools.gate_btc_lock_gap_recovery import _StripAuthOnCrossHostRedirect
from tools.gate_btc_measurement_status import build_status
from tools.gate_btc_reporting_current_state import reconcile


class ArtifactRedirectTest(unittest.TestCase):
    def test_cross_host_redirect_strips_github_authorization(self):
        handler = _StripAuthOnCrossHostRedirect()
        request = urllib.request.Request(
            "https://api.github.com/repos/o/r/actions/artifacts/1/zip",
            headers={"Authorization": "Bearer secret", "User-Agent": "test"},
        )
        redirected = handler.redirect_request(
            request,
            None,
            302,
            "Found",
            {},
            "https://signed.blob.core.windows.net/artifact?sig=x",
        )
        self.assertIsNotNone(redirected)
        self.assertIsNone(redirected.get_header("Authorization"))


class DeliveryHealthTest(unittest.TestCase):
    def test_stale_expected_component_blocks_green_status(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "GATE_BTC_LATEST_ELIGIBLE_RUN.json").write_text(
                '{"data_cutoff":"2026-08-15","research_only":true,'
                '"orders_generated":0,"real_capital_used":0}', encoding="utf-8"
            )
            (root / "GATE_BTC_MEASUREMENT_STATUS.json").write_text(
                '{"data_as_of":"2026-08-14","research_only":true,'
                '"orders_generated":0,"real_capital_used":0}', encoding="utf-8"
            )
            result = reconcile(root, date(2026, 8, 16))
            self.assertEqual(result["status"], "BLOCKED_INCOMPLETE_DELIVERY")
            self.assertFalse(result["delivery_complete"])
            self.assertIn("delta", result["warnings"]["stale_components"])

    def test_verified_local_d50_reconciliation_becomes_display_authority(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "ledgers" / "d50").mkdir(parents=True)
            (root / "GATE_BTC_LATEST_ELIGIBLE_RUN.json").write_text(
                '{"data_cutoff":"2026-08-14","research_only":true,'
                '"orders_generated":0,"real_capital_used":0}', encoding="utf-8"
            )
            (root / "GATE_BTC_MEASUREMENT_STATUS.json").write_text(
                '{"data_as_of":"2026-08-14","research_only":true,'
                '"orders_generated":0,"real_capital_used":0,'
                '"reconciliation_note":"verified local evidence",'
                '"d50_prospective_immutable_ledger":{"current":13,"target":30,'
                '"status":"ACTIVE","latest_prospective_date":"2026-08-14",'
                '"user_action_required":false},'
                '"d50_data_qualification":{"current":4,"target":7,'
                '"hash_chain_valid":true,"user_action_required":false}}', encoding="utf-8"
            )
            (root / "ledgers" / "d50" / "STATUS.json").write_text(
                '{"data_as_of":"2026-08-06","research_only":true,'
                '"orders_generated":0,"real_capital_used":0,'
                '"prospective_immutable_ledger":{"current":4,"target":30,'
                '"status":"BLOCKED_LOCAL_SOURCE_REVISION_REPAIR_PENDING"},'
                '"data_qualification":{"current":6,"target":7}}', encoding="utf-8"
            )
            result = reconcile(root, date(2026, 8, 15))
            d50 = result["components"]["d50"]
            self.assertEqual(d50["authority"], "LOCAL_RECONCILED_MEASUREMENT")
            self.assertEqual(d50["display_current"], 13)
            self.assertEqual(d50["data_qualification_current"], 4)
            self.assertEqual(d50["raw_remote_current_for_audit_only"], 4)

    def test_status_rebuild_preserves_verified_d50_reconciliation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            delta = root / "delta.csv"
            delta.write_text(
                "strategy,window,end,observations\n"
                "Delta_LS_50_50,EXPANDING_FROM_D0,2026-08-15,91\n",
                encoding="utf-8",
            )
            gateway = root / "gateway.json"
            gateway.write_text('{"valid_snapshot_count":9,"required_snapshot_count":80}', encoding="utf-8")
            lock = root / "lock.json"
            lock.write_text('{"valid_snapshot_count":10}', encoding="utf-8")
            remote = root / "d50.json"
            remote.write_text(
                '{"data_qualification":{"current":6},'
                '"prospective_immutable_ledger":{"current":4}}', encoding="utf-8"
            )
            output = root / "status.json"
            output.write_text(json.dumps({
                "reconciliation_note": "verified local evidence",
                "d50_data_qualification": {
                    "current": 4, "hash_chain_valid": True,
                    "user_action_required": False,
                },
                "d50_prospective_immutable_ledger": {
                    "current": 13, "latest_prospective_date": "2026-08-14",
                    "user_action_required": False,
                },
            }), encoding="utf-8")
            args = argparse.Namespace(
                delta_gate=delta, gateway_status=gateway, lock_status=lock,
                d50_status=remote, output=output,
            )
            self.assertEqual(build_status(args), 0)
            rebuilt = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(rebuilt["d50_prospective_immutable_ledger"]["current"], 13)
            self.assertEqual(rebuilt["d50_data_qualification"]["current"], 4)
            self.assertEqual(rebuilt["delta_walk_forward"]["current"], 91)


if __name__ == "__main__":
    unittest.main()
