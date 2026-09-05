import json
import tempfile
import unittest
from pathlib import Path
from tools.gate_btc_2_prospective_dataset_epoch_cutover import D0_SCHEMA,EPOCH_ID,PREREG_COMMIT,REGISTRY_SCHEMA,assess,write_d0_if_eligible
class ProspectiveDatasetEpochCutoverTests(unittest.TestCase):
    def _write(self,path,payload): path.parent.mkdir(parents=True,exist_ok=True); path.write_text(json.dumps(payload),encoding="utf-8")
    def _status(self,sid,attempted,loaded,failed,coverage,prospective=True):
        d={"latest_snapshot_id":sid,"latest_attempted_symbols":attempted,"latest_loaded_symbols":loaded,"latest_failed_symbols":failed,"latest_coverage_ratio":coverage,"survivorship_bias_present":True,"historical_model_survivorship_bias_present":True,"future_point_in_time_only":True,"retrospective_backfill_allowed":False,"research_only":True,"shadow_only":True,"not_approved":True,"promotion_allowed":False,"orders_generated":0,"real_capital_used":0,"feeds_frozen_engine":False}
        if prospective: d.update({"prospective_point_in_time_universe_observed":True,"prospective_point_in_time_universe_bias_present":False})
        return d
    def _snapshot(self,sid,run_utc,attempted,loaded,failed,coverage,prospective=True):
        d={"snapshot_id":sid,"source_run_utc":run_utc,"attempted_symbols":attempted,"loaded_symbols":loaded,"failed_symbols":failed,"coverage_ratio":coverage,"survivorship_bias_present":True,"historical_model_survivorship_bias_present":True,"retrospective_reconstruction":False,"research_only":True,"shadow_only":True,"not_approved":True,"promotion_allowed":False,"orders_generated":0,"real_capital_used":0,"feeds_frozen_engine":False,"record_sha256":"r"*64,"source_hashes":{"manifest_sha256":"m"*64,"universe_sha256":"u"*64,"quality_sha256":"q"*64},"universe_archive":{"archive_path":"universe.gz","archive_sha256":"a"*64},"quality_archive":{"archive_path":"quality.gz","archive_sha256":"b"*64},"failures_archive":{"archive_path":"failures.gz","archive_sha256":"c"*64}}
        if prospective: d.update({"prospective_point_in_time_universe_observed":True,"prospective_point_in_time_universe_bias_present":False})
        return d
    def _registry(self,symbols):
        return {"schema":REGISTRY_SCHEMA,"epoch_id":EPOCH_ID,"entries":[{"symbol":s,"qualification":"QUALIFIED_EXACT_SOURCE","source_identity":f"official:{s}","source_symbol":f"{s}-USD","provenance_sha256":(s.lower()[:1] or "a")*64,"timezone":"UTC","cutoff_semantics":"canonical_daily_cutoff","qa_pass":True,"observed_vs_derived":"OBSERVED"} for s in symbols]}
    def test_legacy_snapshot_without_explicit_prospective_pit_cannot_start_d0(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); sid="legacy"; status=root/"STATUS.json"; snaps=root/"snapshots"; registry=root/"registry.json"
            self._write(status,self._status(sid,2,2,0,1.0,False)); self._write(snaps/f"{sid}.json",self._snapshot(sid,"2026-09-04T09:00:00Z",2,2,0,1.0,False)); self._write(registry,self._registry(["A","B"])); result=assess(status,snaps,registry)
            self.assertFalse(result["cutover_eligible"]); self.assertIn("PROSPECTIVE_POINT_IN_TIME_UNIVERSE_NOT_PROVEN",result["blockers"]); self.assertIn("PROSPECTIVE_PIT_STATUS_NOT_PROVEN",result["blockers"])
    def test_complete_new_snapshot_is_eligible_despite_preserved_historical_warning(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); sid="post"; status=root/"STATUS.json"; snaps=root/"snapshots"; registry=root/"registry.json"; symbols=["A","B"]
            self._write(status,self._status(sid,2,2,0,1.0)); self._write(snaps/f"{sid}.json",self._snapshot(sid,"2026-09-04T09:00:00Z",2,2,0,1.0)); self._write(registry,self._registry(symbols)); result=assess(status,snaps,registry)
            self.assertTrue(result["cutover_eligible"],result["blockers"]); self.assertTrue(result["historical_model_survivorship_bias_present"]); self.assertFalse(result["prospective_point_in_time_universe_bias_present"]); d0=root/"D0.json"; self.assertTrue(write_d0_if_eligible(result,d0)); frozen=json.loads(d0.read_text()); self.assertEqual(frozen["schema"],D0_SCHEMA); self.assertEqual(frozen["epoch_id"],EPOCH_ID); self.assertEqual(frozen["preregistration_commit_sha"],PREREG_COMMIT); self.assertFalse(frozen["prospective_point_in_time_universe_bias_present"]); self.assertFalse(write_d0_if_eligible(result,d0))
    def test_pre_prereg_and_incomplete_still_fail(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); sid="pre"; status=root/"STATUS.json"; snaps=root/"snapshots"; registry=root/"registry.json"
            self._write(status,self._status(sid,2,1,1,0.5)); self._write(snaps/f"{sid}.json",self._snapshot(sid,"2026-09-03T04:00:00Z",2,1,1,0.5)); result=assess(status,snaps,registry)
            self.assertFalse(result["cutover_eligible"]); self.assertIn("SNAPSHOT_NOT_STRICTLY_POST_PREREGISTRATION",result["blockers"]); self.assertIn("V2A_SYMBOL_LOAD_GAP",result["blockers"]); self.assertIn("FULL_QUALIFIED_EXACT_SOURCE_REGISTRY_NOT_MATERIALIZED",result["blockers"])
    def test_incomplete_registry_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); sid="post"; status=root/"STATUS.json"; snaps=root/"snapshots"; registry=root/"registry.json"
            self._write(status,self._status(sid,2,2,0,1.0)); self._write(snaps/f"{sid}.json",self._snapshot(sid,"2026-09-04T09:00:00Z",2,2,0,1.0)); self._write(registry,self._registry(["A"])); result=assess(status,snaps,registry); self.assertFalse(result["cutover_eligible"]); self.assertIn("QUALIFIED_SOURCE_REGISTRY_NOT_FULL_UNIVERSE",result["blockers"])
if __name__=="__main__": unittest.main()
