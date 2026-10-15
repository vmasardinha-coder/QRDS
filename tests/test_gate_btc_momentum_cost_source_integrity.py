import copy
import csv
import gzip
import hashlib
import io
import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch
from tools.gate_btc_momentum_cost_diagnostic import prices_for,project,main
from tests import test_gate_btc_momentum_cost_diagnostic as fixtures

class CostSourceIntegrityTests(unittest.TestCase):
    def write_fixture(self,base):
        epoch=base/"canonical/epochs/hold_20260928";epoch.mkdir(parents=True)
        ledger,prices=fixtures.MomentumCostDiagnosticTest().fixture()
        ledger["epoch_id"]="hold_20260928";ledger["rows"]=ledger["rows"][:1]
        row=ledger["rows"][0];folder=epoch/"source_prices"/row["cutoff"];folder.mkdir(parents=True)
        table=[{"date":row["cutoff"],"symbol":a,"close_usd":v,"source":"test_public_source"} for a,v in sorted(prices[0].items())]
        buf=io.StringIO();writer=csv.DictWriter(buf,fieldnames=list(table[0]));writer.writeheader();writer.writerows(table)
        with zipfile.ZipFile(folder/"required_prices.zip","w",zipfile.ZIP_DEFLATED) as z:z.writestr("data/processed/qos_v2a_master_daily.csv",buf.getvalue())
        response="retained physical source"
        raw={"sources":[{"http_status":200,"raw_utf8":response,"raw_sha256":hashlib.sha256(response.encode()).hexdigest()}]}
        (folder/"RAW_SOURCES.json.gz").write_bytes(gzip.compress(json.dumps(raw).encode(),mtime=0))
        manifest={"cutoff":row["cutoff"],"available_at_utc":"2026-10-02T02:00:00+00:00","prices":table,
                  "required_assets":sorted(prices[0]),"price_count":len(table),
                  "prices_zip_sha256":self.sha(folder/"required_prices.zip"),"raw_archive_sha256":self.sha(folder/"RAW_SOURCES.json.gz")}
        row["evidence"]={"source_available_at_utc":manifest["available_at_utc"]}
        self.reseal(epoch,ledger,manifest)
        return epoch,ledger,manifest,folder
    def sha(self,path):return hashlib.sha256(path.read_bytes()).hexdigest()
    def reseal(self,epoch,ledger,manifest):
        path=epoch/"source_prices"/ledger["rows"][0]["cutoff"]/"MANIFEST.json"
        path.write_bytes((json.dumps(manifest)+"\n").encode())
        ledger["rows"][0]["evidence"]["price_manifest_sha256"]=self.sha(path)
        (epoch/"LEDGER.json").write_bytes((json.dumps(ledger)+"\n").encode())
    def test_bound_archives_csv_and_raw_responses_are_verified(self):
        with tempfile.TemporaryDirectory() as temp:
            epoch,ledger,_,_=self.write_fixture(Path(temp))
            self.assertEqual(prices_for(ledger["rows"][0],epoch)["BTC"],1)
    def test_each_corrupted_archive_is_rejected(self):
        for name in ["required_prices.zip","RAW_SOURCES.json.gz"]:
            with tempfile.TemporaryDirectory() as temp:
                epoch,ledger,_,folder=self.write_fixture(Path(temp))
                path=folder/name;path.write_bytes(path.read_bytes()+b"changed")
                with self.assertRaisesRegex(ValueError,"SOURCE_ARCHIVE_CORRUPT"):prices_for(ledger["rows"][0],epoch)
    def test_even_resealed_zip_cannot_disagree_with_manifest(self):
        with tempfile.TemporaryDirectory() as temp:
            epoch,ledger,manifest,folder=self.write_fixture(Path(temp))
            with zipfile.ZipFile(folder/"required_prices.zip","w") as z:
                z.writestr("data/processed/qos_v2a_master_daily.csv","date,symbol,close_usd,source\n2026-10-01,BTC,99,test_public_source\n")
            manifest["prices_zip_sha256"]=self.sha(folder/"required_prices.zip");self.reseal(epoch,ledger,manifest)
            with self.assertRaisesRegex(ValueError,"PRICE_ARCHIVE_MANIFEST_DISAGREEMENT"):prices_for(ledger["rows"][0],epoch)
    def test_raw_response_inner_hash_is_checked_after_outer_reseal(self):
        with tempfile.TemporaryDirectory() as temp:
            epoch,ledger,manifest,folder=self.write_fixture(Path(temp))
            path=folder/"RAW_SOURCES.json.gz";raw=json.loads(gzip.decompress(path.read_bytes()))
            raw["sources"][0]["raw_utf8"]="changed"
            path.write_bytes(gzip.compress(json.dumps(raw).encode(),mtime=0))
            manifest["raw_archive_sha256"]=self.sha(path);self.reseal(epoch,ledger,manifest)
            with self.assertRaisesRegex(ValueError,"RAW_SOURCE_RESPONSE_CHANGED"):prices_for(ledger["rows"][0],epoch)
    def test_empty_raw_response_archive_is_not_physical_evidence(self):
        with tempfile.TemporaryDirectory() as temp:
            epoch,ledger,manifest,folder=self.write_fixture(Path(temp))
            path=folder/"RAW_SOURCES.json.gz";path.write_bytes(gzip.compress(b'{"sources":[]}'))
            manifest["raw_archive_sha256"]=self.sha(path);self.reseal(epoch,ledger,manifest)
            with self.assertRaisesRegex(ValueError,"MISSING_PHYSICAL_SOURCE_RESPONSES"):prices_for(ledger["rows"][0],epoch)
    def test_wrong_btc_gross_benchmark_is_rejected(self):
        ledger,prices=fixtures.MomentumCostDiagnosticTest().fixture();ledger["rows"][3]["btc_nav"]=2
        with self.assertRaisesRegex(ValueError,"GROSS_BTC_RECONCILIATION_FAILED"):project(ledger,prices,10)
    def test_hold_cannot_silently_change_quantities_even_if_nav_matches(self):
        ledger,prices=fixtures.MomentumCostDiagnosticTest().fixture()
        ledger["rows"][2]["quantities_after_close"]["M1_TOP10"]["A0"]=0.15
        ledger["rows"][2]["quantities_after_close"]["M1_TOP10"]["A1"]=0.05
        with self.assertRaisesRegex(ValueError,"GROSS_QUANTITIES_CHANGED_ON_HOLD"):project(ledger,prices,10)
    def test_terminal_exit_is_separate_and_not_charged_twice(self):
        ledger,prices=fixtures.MomentumCostDiagnosticTest().fixture()
        result=project(ledger,prices,100)["summary"]["M1_TOP10"]
        self.assertAlmostEqual(result["nav_model_net"],1/1.01)
        self.assertAlmostEqual(result["hypothetical_cash_after_exit"],(1/1.01)*0.99)
        self.assertAlmostEqual(result["cost_nav_units_total"],0.01/1.01)
    def test_cli_publish_is_read_only_idempotent_and_refuses_conflict(self):
        with tempfile.TemporaryDirectory() as temp:
            base=Path(temp);epoch,_,_,_=self.write_fixture(base)
            before={p.relative_to(epoch):self.sha(p) for p in epoch.rglob("*") if p.is_file()}
            args=["diagnostic","--epoch",str(epoch),"--one-way-cost-bps","0","5","10","25","--output-root",str(base/"cost")]
            with patch.object(sys,"argv",args):
                self.assertEqual(main(),0);self.assertEqual(main(),0)
            report=next((base/"cost").rglob("REPORT.json"))
            data=json.loads(report.read_bytes())
            self.assertTrue(data["source_archive_bytes_verified"])
            self.assertEqual(len(data["scenarios"]),4)
            self.assertEqual(before,{p.relative_to(epoch):self.sha(p) for p in epoch.rglob("*") if p.is_file()})
            report.write_bytes(b"changed")
            with patch.object(sys,"argv",args),self.assertRaisesRegex(ValueError,"IMMUTABLE_COST_DIAGNOSTIC_CONFLICT"):main()
    def test_cli_cannot_write_inside_canonical_tree(self):
        with tempfile.TemporaryDirectory() as temp:
            epoch,_,_,_=self.write_fixture(Path(temp))
            with patch.object(sys,"argv",["diagnostic","--epoch",str(epoch),"--one-way-cost-bps","10","--output",str(epoch/"REPORT.json")]):
                with self.assertRaisesRegex(ValueError,"CANNOT_OVERWRITE_CANONICAL"):main()
    def test_cli_bad_archive_publishes_blocked_not_fake_net(self):
        with tempfile.TemporaryDirectory() as temp:
            base=Path(temp);epoch,_,_,folder=self.write_fixture(base)
            (folder/"required_prices.zip").unlink()
            with patch.object(sys,"argv",["diagnostic","--epoch",str(epoch),"--one-way-cost-bps","10","--output-root",str(base/"cost")]):
                self.assertEqual(main(),2)
            report=json.loads(next((base/"cost").rglob("REPORT.json")).read_bytes())
            self.assertEqual(report["status"],"BLOCKED_MISSING_OR_INVALID_BOUND_GROSS_EVIDENCE")
            self.assertNotIn("scenarios",report)
            self.assertEqual(report["prospective_net_credit"],0)

if __name__=="__main__":unittest.main()
