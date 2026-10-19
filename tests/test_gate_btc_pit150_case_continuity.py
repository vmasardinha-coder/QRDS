import copy
import csv
import gzip
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from tools.gate_btc_pit150_source_crosswalk import retain_case_history, selected_identities


class CaseContinuityTests(unittest.TestCase):
    def setUp(self):
        self.previous = {"data_as_of": "2026-10-17", "assets": [
            {"symbol": "USX", "pit150_identity": "usx", "next_action": "Public180dayaccess limit remains"},
            {"symbol": "PC0000031", "pit150_identity": "fund", "next_action": "Scope"}]}
        self.current = {"data_as_of": "2026-10-18", "assets": [], "failure_count": 0,
                        "legacy_loaded_symbols": 150, "pit150_denominator_preserved": 150,
                        "engine_feed": False, "prospective_credit": 0}

    def test_disappearance_is_not_resolution_and_inputs_are_immutable(self):
        original = copy.deepcopy((self.previous, self.current))
        out = retain_case_history(self.current, [self.previous], {"other"})
        self.assertEqual(out["tracked_prior_case_count"], 2)
        for case in out["tracked_cases_not_current_failures"]:
            self.assertEqual(case["tracking_status"], "OUTSIDE_CURRENT_SELECTION_NO_REPAIR_PROVEN")
            self.assertFalse(case["coverage_dependency_resolved"])
            self.assertFalse(case["repair_proven_by_disappearance"])
        self.assertEqual((self.previous, self.current), original)
        self.assertEqual((out["failure_count"], out["legacy_loaded_symbols"], out["pit150_denominator_preserved"]), (0,150,150))

    def test_currently_selected_loaded_is_distinct_from_outside_selection(self):
        out = retain_case_history(self.current, [self.previous], {"usx"})
        cases = {r["symbol"]: r for r in out["tracked_cases_not_current_failures"]}
        self.assertEqual(cases["USX"]["tracking_status"], "CURRENTLY_SELECTED_WITHOUT_FAILURE_REPAIR_CAUSE_NOT_PROVEN")
        self.assertEqual(cases["PC0000031"]["tracking_status"], "OUTSIDE_CURRENT_SELECTION_NO_REPAIR_PROVEN")

    def test_missing_membership_proof_stays_unknown(self):
        out = retain_case_history(self.current, [self.previous])
        self.assertFalse(out["selection_membership_verified"])
        self.assertTrue(all(r["tracking_status"] == "NOT_CURRENT_FAILURE_SELECTION_UNVERIFIED" for r in out["tracked_cases_not_current_failures"]))

    def test_repeated_runs_keep_history_once_and_returning_failure_rejoins_active(self):
        first = retain_case_history(self.current, [self.previous], {"other"})
        self.assertEqual(retain_case_history(self.current, [self.previous, first], {"other"}), first)
        current = {**self.current, "assets": [{"symbol":"NEWUSX", "pit150_identity":"usx"}]}
        out = retain_case_history(current, [self.previous, first], {"usx"})
        self.assertEqual(out["tracked_prior_case_count"], 1)
        self.assertEqual(out["assets"][0]["symbol"], "NEWUSX")

    def test_symbol_collision_does_not_erase_old_identity(self):
        current = {**self.current, "assets": [{"symbol":"USX", "pit150_identity":"different-usx"}]}
        self.assertEqual(retain_case_history(current,[self.previous],{"different-usx"})["tracked_prior_case_count"],2)

    def test_malformed_future_and_duplicate_history_fail_closed(self):
        for history in [{**self.previous,"data_as_of":"2026-10-19"},
                        {**self.previous,"assets":[{"symbol":"USX"}]},
                        {**self.previous,"assets":self.previous["assets"]*2}]:
            with self.subTest(history=history), self.assertRaises((ValueError,KeyError)):
                retain_case_history(self.current,[history])

    def test_production_baseline_is_present_and_preserves_the_two_departed_cases(self):
        path = Path(__file__).resolve().parents[1] / 'artifacts/gate_btc_2/pit150_case_continuity_20261019/BASELINE_FOLLOWUP_20261017.json'
        baseline = json.loads(path.read_text())
        self.assertEqual(baseline['data_as_of'], '2026-10-17')
        self.assertEqual(len(baseline['assets']), 20)
        self.assertTrue({'usx', 'tradable-na-rent-financing-platform-sstn'}.issubset(
            {r['pit150_identity'] for r in baseline['assets']}))


class SelectionProofTests(unittest.TestCase):
    def fixture(self, root):
        rows = [{"id": "bitcoin" if i==0 else "ethereum" if i==1 else f"asset-{i}",
                 "symbol":"BTC" if i==0 else "ETH" if i==1 else f"S{i}",
                 "standard_ticker":"True","is_stable":"False","is_blocked":"False"} for i in range(151)]
        stream=io.StringIO();w=csv.DictWriter(stream,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
        raw=stream.getvalue().encode();compressed=gzip.compress(raw,mtime=0)
        (root/'archives').mkdir();(root/'archives/universe.csv.gz').write_bytes(compressed)
        d={"snapshot_id":"test-18","data_as_of":"2026-10-18","source_run_id":"18","attempted_symbols":150,
           "rows":[{"symbol":"S149","coin_id":"asset-149"}]}
        snap={"snapshot_id":"test-18","source_data_as_of":"2026-10-18","source_run_id":"18", "universe_archive":{
            "archive_path":"archives/universe.csv.gz","archive_sha256":hashlib.sha256(compressed).hexdigest(),
            "raw_sha256":hashlib.sha256(raw).hexdigest(),"raw_size_bytes":len(raw)}}
        return d,snap

    def test_exact_archive_selects150_and_excludes151st(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);d,snap=self.fixture(root);ids=selected_identities(snap,root,d)
            self.assertEqual(len(ids),150);self.assertNotIn('asset-150',ids)

    def test_tampered_archive_snapshot_and_failure_identity_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);d,snap=self.fixture(root)
            for bad in [{**snap,"snapshot_id":"other"},{**snap,"universe_archive":{**snap['universe_archive'],"raw_sha256":"0"*64}},
                        {**snap,"universe_archive":{**snap['universe_archive'],"archive_path":"../escape"}}]:
                with self.subTest(bad=bad), self.assertRaises(ValueError):selected_identities(bad,root,d)
            d['rows'][0]['coin_id']='asset-150'
            with self.assertRaises(ValueError):selected_identities(snap,root,d)

    def test_cli_in_place_previous_report_is_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            diagnostic={"snapshot_id":"test","data_as_of":"2026-10-18","source_run_id":1,
                        "attempted_symbols":150,"loaded_symbols":150,"failed_symbols":0,"rows":[]}
            baseline={"data_as_of":"2026-10-17","assets":[{"symbol":"USX","pit150_identity":"usx"}]}
            for name,data in [('diagnostic',diagnostic),('registry',{'entry_count':0,'entries':[]}),('history',baseline)]:
                (root/(name+'.json')).write_text(json.dumps(data))
            cmd=[sys.executable,str(Path(__file__).resolve().parents[1]/'tools/gate_btc_pit150_source_crosswalk.py'),
                 '--diagnostic',str(root/'diagnostic.json'),'--registry',str(root/'registry.json'),
                 '--case-history',str(root/'history.json'),'--previous-followup',str(root/'out.json'),'--output',str(root/'out.json')]
            subprocess.run(cmd,check=True,capture_output=True);first=(root/'out.json').read_bytes()
            subprocess.run(cmd,check=True,capture_output=True);self.assertEqual((root/'out.json').read_bytes(),first)


if __name__=='__main__':unittest.main()
