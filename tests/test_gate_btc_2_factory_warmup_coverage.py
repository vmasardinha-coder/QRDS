import copy
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from gate_btc_2_factory_control_room import warmup_coverage

class WarmupCoverageTests(unittest.TestCase):
    def seal(self, root, day, rows):
        record={"session":day,"feature_observations":rows}
        record["record_sha256"]=hashlib.sha256(json.dumps(record,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()
        path=root/(day+".json");path.write_text(json.dumps(record),encoding="utf-8");return path
    def activation(self):
        return {"active_families":[{"contract":{"feature":f,"decision_window_minutes":10,"standardization_lookback_sessions":n}} for f,n in [("OPEN_RETURN",2),("GAP_FROM_PRIOR_CLOSE",2),("OPEN_RETURN",3)]]}
    def row(self,key,value,available=True):return {"key":key+"|10","available":available,"value":value}

    def test_feature_specific_history_and_missing_previous_close(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            self.seal(root,"2026-10-13",[self.row("OPEN_RETURN",1),self.row("GAP_FROM_PRIOR_CLOSE",None,False)])
            self.seal(root,"2026-10-14",[self.row("OPEN_RETURN",2),self.row("GAP_FROM_PRIOR_CLOSE",3)])
            self.seal(root,"2026-10-15",[])
            original={p.name:p.read_bytes() for p in root.iterdir()}
            activation=self.activation();before=copy.deepcopy(activation)
            out=warmup_coverage(activation,root)
            self.assertEqual(out["verified_ledger_records"],3)
            cohort=out["by_lookback"][0]
            self.assertEqual((cohort["family_count"],cohort["prior_feature_observations_min"],cohort["prior_feature_observations_max"]),(2,1,2))
            self.assertEqual((cohort["additional_prior_observations_min"],cohort["additional_prior_observations_max"]),(0,1))
            self.assertEqual(out["families_with_full_prior_feature_count"],1)
            self.assertTrue(out["coverage_is_not_signal_qualification"])
            self.assertTrue(out["first_signal_still_requires_later_eligible_session_current_feature_and_nonzero_mad"])
            self.assertFalse(out["promotion_authority"]);self.assertEqual(out["scientific_credit"],0)
            self.assertEqual(activation,before)
            self.assertEqual(original,{p.name:p.read_bytes() for p in root.iterdir()})

    def test_unavailable_or_nonfinite_features_do_not_count(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            self.seal(root,"2026-10-13",[self.row("OPEN_RETURN",float("nan")),self.row("GAP_FROM_PRIOR_CLOSE",9,False)])
            out=warmup_coverage(self.activation(),root)
            self.assertEqual(out["families_with_full_prior_feature_count"],0)
            self.assertEqual(out["by_lookback"][0]["additional_prior_observations_min"],2)

    def test_mutated_ledger_cannot_advance_coverage(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);p=self.seal(root,"2026-10-13",[self.row("OPEN_RETURN",1)])
            obj=json.loads(p.read_text());obj["feature_observations"][0]["value"]=99;p.write_text(json.dumps(obj))
            with self.assertRaisesRegex(RuntimeError,"WARMUP_LEDGER_BINDING_MISMATCH"):warmup_coverage(self.activation(),root)

    def test_mismatched_session_cannot_count_as_another_day(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);p=self.seal(root,"2026-10-13",[]);p.rename(root/"2026-10-14.json")
            with self.assertRaisesRegex(RuntimeError,"WARMUP_LEDGER_BINDING_MISMATCH"):warmup_coverage(self.activation(),root)

    def test_duplicate_feature_cannot_inflate_session_count(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);self.seal(root,"2026-10-13",[self.row("OPEN_RETURN",1),self.row("OPEN_RETURN",2)])
            with self.assertRaisesRegex(RuntimeError,"DUPLICATE_SESSION_FEATURE"):warmup_coverage(self.activation(),root)

    def test_empty_history_keeps_all_families_short_of_coverage(self):
        with tempfile.TemporaryDirectory() as temp:
            out=warmup_coverage(self.activation(),Path(temp))
            self.assertEqual(out["family_count"],3)
            self.assertEqual(out["verified_ledger_records"],0)
            self.assertEqual(out["families_with_full_prior_feature_count"],0)

if __name__=="__main__":unittest.main()
