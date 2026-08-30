import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from tools.gate_btc_2_stage9_bitget_ledger_bridge import build_canonical_admission
from tools.gate_btc_2_prospective_counter_bridge import validate_admission


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


class BitgetLedgerBridgeTests(unittest.TestCase):
    def _fixture(self, root: Path):
        cap = root / "capture"; adm = root / "admission"
        cap.mkdir(); adm.mkdir()
        perp=b'{"code":"00000","data":[{"symbol":"BTCUSDT"}]}'
        spot=b'{"code":"00000","data":[{"symbol":"BTCUSDT"}]}'
        (cap/"bitget_perp.json").write_bytes(perp); (cap/"bitget_spot.json").write_bytes(spot)
        capture={
            "provider":"BITGET_PUBLIC_V2","venue":"BITGET","instrument":"BTCUSDT",
            "captured_at_utc":"2026-08-30T17:00:08Z","roles":{"FUNDING":{},"OPEN_INTEREST":{},"PERP_VOLUME":{},"SPOT_VOLUME":{}},
            "raw_sha256":{"perp":sha(perp),"spot":sha(spot)},"forward_only":True,"historical_rows_backfilled":0,
            "source_admitted":False,"prospective_credit":0,"methodology_changes":0,"clock_changes":0,"economics_changes":0,
            "research_only":True,"shadow_only":True,"not_approved":True,"engine_feed":False,"orders_generated":0,"real_capital_used":0,
            "no_retune":True,"no_backfill":True,"fail_closed":True,
        }
        (cap/"capture_decision.json").write_text(json.dumps(capture))
        review={"review_sha256":"a"*64}
        provider={
            "decision":"ADMITTED_FORWARD_ONLY","provider":"BITGET_PUBLIC_V2","venue":"BITGET","instrument":"BTCUSDT",
            "raw_roles":["FUNDING","OPEN_INTEREST","PERP_VOLUME","SPOT_VOLUME"],"captured_at_utc":"2026-08-30T17:00:08Z",
            "review_sha256":"a"*64,"source_admitted_for_shadow_collection":True,"prospective_observations_admitted":1,
            "forward_only":True,"backfill":False,"historical_recovery":False,"silent_source_substitution":False,
            "stage_9_complete":False,"economics_allowed":False,"engine_feed":False,"orders_generated":0,"real_capital_used":0,
            "no_retune":True,"no_backfill":True,"fail_closed":True,
        }
        (adm/"bitget_stage9_review.json").write_text(json.dumps(review)); (adm/"bitget_stage9_admission.json").write_text(json.dumps(provider))
        return cap, adm

    def test_valid_bridge_binds_supplied_scheduled_run(self):
        with tempfile.TemporaryDirectory() as td:
            cap, adm=self._fixture(Path(td)); row=build_canonical_admission(cap, adm, 33321729143)
            validate_admission(row)
            self.assertEqual(row["run_id"], 33321729143)
            self.assertFalse(row["backfill"]); self.assertFalse(row["engine_feed"])

    def test_distinct_run_ids_produce_distinct_admission_identity(self):
        with tempfile.TemporaryDirectory() as td:
            cap, adm=self._fixture(Path(td))
            a=build_canonical_admission(cap, adm, 33321729143)
            b=build_canonical_admission(cap, adm, 33399999999)
            self.assertNotEqual(a["admission_artifact_sha256"], b["admission_artifact_sha256"])

    def test_invalid_run_id_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            cap, adm=self._fixture(Path(td))
            with self.assertRaises(RuntimeError): build_canonical_admission(cap, adm, 0)

    def test_raw_tamper_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            cap, adm=self._fixture(Path(td)); (cap/"bitget_spot.json").write_bytes(b'{}')
            with self.assertRaises(RuntimeError): build_canonical_admission(cap, adm, 33321729143)

    def test_scientific_boundary_change_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            cap, adm=self._fixture(Path(td)); d=json.loads((cap/"capture_decision.json").read_text()); d["economics_changes"]=1; (cap/"capture_decision.json").write_text(json.dumps(d))
            with self.assertRaises(RuntimeError): build_canonical_admission(cap, adm, 33321729143)


if __name__ == "__main__": unittest.main()
