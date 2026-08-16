import argparse
import io
import json
import tempfile
import unittest
import urllib.request
import zipfile
from datetime import date
from pathlib import Path
from unittest.mock import patch

from tools.gate_btc_lock_gap_recovery import (
    _StripAuthOnCrossHostRedirect,
    _artifact_for_run,
    _embedded_lock_valuation_sidecar,
    _embedded_v2a,
    _successful_runs,
)
from tools.gate_btc_measurement_status import build_status
from tools.gate_btc_reporting_current_state import reconcile


class ArtifactRedirectTest(unittest.TestCase):
    def test_historical_recovery_carries_valuation_only_sidecar(self):
        outer = io.BytesIO()
        sidecar = {
            "schema": "gate_btc.lock_valuation_sidecar.v1",
            "valuation_only": True,
            "engine_feed": False,
        }
        with zipfile.ZipFile(outer, "w") as archive:
            archive.writestr("qos_daily/lock_valuation_sidecar.json", json.dumps(sidecar))
        recovered = _embedded_lock_valuation_sidecar(outer.getvalue())
        self.assertEqual(json.loads(recovered), sidecar)

    def test_historical_v2a_uses_canonical_safety_fields(self):
        nested = io.BytesIO()
        with zipfile.ZipFile(nested, "w") as archive:
            archive.writestr("outputs/v2a_run_manifest.json", json.dumps({
                "data_as_of": "2026-08-09",
                "technical_status": "PASS",
                "operational_status": "NOT_APPROVED",
                "real_orders": 0,
                "capital_used": 0,
            }))
        outer = io.BytesIO()
        with zipfile.ZipFile(outer, "w") as archive:
            archive.writestr("qos_daily/qos_v2a_outputs.zip", nested.getvalue())
        data_as_of, recovered = _embedded_v2a(outer.getvalue())
        self.assertEqual(data_as_of, "2026-08-09")
        self.assertEqual(recovered, nested.getvalue())

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

    def test_successful_run_discovery_paginates_beyond_first_hundred(self):
        eligible = {
            "name": "GATE BTC Daily Research Collection",
            "head_branch": "main",
            "status": "completed",
            "conclusion": "success",
        }
        first_page = [{**eligible, "id": i} for i in range(100)]
        second_page = [{**eligible, "id": 31350117629}]
        with patch(
            "tools.gate_btc_lock_gap_recovery._request_json",
            side_effect=[
                {"workflow_runs": first_page},
                {"workflow_runs": second_page},
            ],
        ) as request_json:
            runs = _successful_runs("o/r", "token")
        self.assertEqual(len(runs), 101)
        self.assertEqual(runs[-1]["id"], 31350117629)
        self.assertIn("page=2", request_json.call_args_list[-1].args[0])

    def test_rerun_uses_latest_same_named_artifact(self):
        artifacts = {
            "artifacts": [
                {
                    "id": 9048726101,
                    "name": "gate-btc-daily-research-31350117629",
                    "expired": False,
                    "archive_download_url": "https://api.github.com/old.zip",
                },
                {
                    "id": 9059764095,
                    "name": "gate-btc-daily-research-31350117629",
                    "expired": False,
                    "archive_download_url": "https://api.github.com/latest.zip",
                },
            ]
        }
        with (
            patch("tools.gate_btc_lock_gap_recovery._request_json", return_value=artifacts),
            patch("tools.gate_btc_lock_gap_recovery._request_bytes", return_value=b"latest") as request_bytes,
        ):
            result = _artifact_for_run("o/r", "token", 31350117629)
        self.assertEqual(result, b"latest")
        self.assertEqual(request_bytes.call_args.args[0], "https://api.github.com/latest.zip")


class DeliveryHealthTest(unittest.TestCase):
    def test_authorized_reanchor_wait_is_current_until_first_close_arrives(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "ledgers" / "lock25_50").mkdir(parents=True)
            (root / "GATE_BTC_LATEST_ELIGIBLE_RUN.json").write_text(
                '{"data_cutoff":"2026-08-15","research_only":true,'
                '"orders_generated":0,"real_capital_used":0}', encoding="utf-8"
            )
            (root / "ledgers" / "lock25_50" / "STATUS.json").write_text(json.dumps({
                "status": "READY_WAITING_FIRST_ELIGIBLE_CLOSE",
                "first_eligible_close": "2026-08-16",
                "reanchor_authorized_at_utc": "2026-08-16T13:00:00Z",
                "valid_snapshot_count": 0,
                "research_only": True,
                "not_approved": True,
                "orders_generated": 0,
                "real_capital_used": 0,
            }), encoding="utf-8")
            result = reconcile(root, date(2026, 8, 16))
            self.assertEqual(
                result["components"]["lock25_50"]["freshness"],
                "CURRENT_AUTHORIZED_REANCHOR_WAITING_UNTOUCHED_CLOSE",
            )
            self.assertNotIn("lock25_50", result["warnings"]["stale_components"])
            self.assertNotIn("lock25_50", result["warnings"]["missing_or_undated_components"])

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

    def test_newer_runtime_failure_supersedes_older_reconciliation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "ledgers" / "d50").mkdir(parents=True)
            (root / "GATE_BTC_LATEST_ELIGIBLE_RUN.json").write_text(
                '{"data_cutoff":"2026-08-15","research_only":true,'
                '"orders_generated":0,"real_capital_used":0}', encoding="utf-8"
            )
            (root / "GATE_BTC_MEASUREMENT_STATUS.json").write_text(json.dumps({
                "data_as_of": "2026-08-15",
                "research_only": True,
                "orders_generated": 0,
                "real_capital_used": 0,
                "reconciliation_note": "verified through 2026-08-14",
                "d50_prospective_immutable_ledger": {
                    "current": 13, "target": 30, "status": "ACTIVE",
                    "latest_prospective_date": "2026-08-14", "user_action_required": False,
                },
                "d50_data_qualification": {
                    "current": 4, "target": 7, "snapshot_count_total": 14,
                    "hash_chain_valid": True, "user_action_required": False,
                },
            }), encoding="utf-8")
            (root / "ledgers" / "d50" / "STATUS.json").write_text(json.dumps({
                "data_as_of": "2026-08-15",
                "research_only": True,
                "orders_generated": 0,
                "real_capital_used": 0,
                "prospective_immutable_ledger": {
                    "current": 14, "target": 30, "status": "ACTIVE",
                    "latest_prospective_date": "2026-08-15",
                },
                "data_qualification": {
                    "current": 0, "target": 7, "snapshot_count_total": 15,
                    "status": "ACTIVE_SYNCHRONIZED_FAILURE_CHAIN_RESET_0_OF_7",
                    "synchronized_failure": True, "qualified": False,
                },
            }), encoding="utf-8")
            result = reconcile(root, date(2026, 8, 16))
            d50 = result["components"]["d50"]
            self.assertEqual(d50["authority"], "RUNTIME_NEWER_THAN_RECONCILIATION")
            self.assertEqual(d50["freshness"], "FRESH")
            self.assertEqual(d50["display_current"], 14)
            self.assertEqual(d50["data_qualification_current"], 0)
            self.assertTrue(d50["data_qualification_synchronized_failure"])

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

    def test_status_rebuild_accepts_newer_monotonic_runtime_tip(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            delta = root / "delta.csv"
            delta.write_text(
                "strategy,window,end,observations\n"
                "Delta_LS_50_50,EXPANDING_FROM_D0,2026-08-15,91\n",
                encoding="utf-8",
            )
            gateway = root / "gateway.json"
            gateway.write_text('{}', encoding="utf-8")
            lock = root / "lock.json"
            lock.write_text('{}', encoding="utf-8")
            remote = root / "d50.json"
            remote.write_text(json.dumps({
                "data_qualification": {
                    "current": 0, "snapshot_count_total": 15,
                    "hash_chain_valid": True,
                },
                "prospective_immutable_ledger": {
                    "current": 14, "latest_prospective_date": "2026-08-15",
                },
            }), encoding="utf-8")
            output = root / "status.json"
            output.write_text(json.dumps({
                "reconciliation_note": "verified through 2026-08-14",
                "d50_data_qualification": {
                    "current": 4, "snapshot_count_total": 14,
                    "hash_chain_valid": True, "user_action_required": False,
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
            self.assertEqual(rebuilt["d50_prospective_immutable_ledger"]["current"], 14)
            self.assertEqual(rebuilt["d50_data_qualification"]["current"], 0)
            self.assertNotIn("reconciliation_note", rebuilt)


if __name__ == "__main__":
    unittest.main()
