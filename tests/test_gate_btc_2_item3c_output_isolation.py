import json
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import gate_btc_2_item3c_forward_collector as collector

class OutputIsolationTests(unittest.TestCase):
    def invoke(self, stage):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp); runtime = base / "runtime"; runtime.mkdir()
            out = base / "out"; out.mkdir()
            (out / "STATUS.json").write_text('{"status":"OLD_CAPTURE"}')
            (out / "SESSION_RECORD.json").write_text('{"session":"2026-10-16","record_sha256":"stale"}')
            (out / "keep.txt").write_text("unrelated diagnostic")
            prereg = {"status":"PREREGISTERED_BEFORE_FIRST_FORWARD_OBSERVATION",
                "upstream_binding":{"runtime_manifest":"manifest.json","required_status":"ACTIVATED_PENDING_FIRST_OBSERVATION"},
                "ledger":{"root":"ledger"}}
            manifest = {"status":"ACTIVATED_PENDING_FIRST_OBSERVATION","d0":"2026-09-23","active_families":[]}
            fixed = datetime.fromisoformat("2026-10-19T19:05:00-03:00")
            expected = "WAIT_SOURCE_BINDING"
            if stage == "wrong_manifest": manifest["status"] = "OTHER"
            if stage == "future_d0": manifest["d0"] = "2026-10-20"; expected = "WAIT_D0"
            if stage == "weekend": fixed = datetime.fromisoformat("2026-10-18T19:05:00-03:00"); expected = "WAIT_B3_WEEKDAY"
            if stage == "before_window": fixed = datetime.fromisoformat("2026-10-19T09:00:00-03:00"); expected = "WAIT_DAILY_BATCH_WINDOW"
            if stage == "no_families": expected = "WAIT_NO_ACTIVE_FAMILIES"
            if stage == "idempotent":
                expected = "IDEMPOTENT_ALREADY_COLLECTED"
                manifest["active_families"] = [{"contract":{"decision_window_minutes":10}}]
                (runtime / "ledger").mkdir()
                (runtime / "ledger/2026-10-19.json").write_text('{"record_sha256":"immutable-existing"}')
            if stage != "missing_manifest":
                (runtime / "manifest.json").write_text(json.dumps(manifest))
            if stage == "invalid_prereg": prereg["status"] = "INVALID"
            pp = base / "prereg.json"; pp.write_text(json.dumps(prereg))
            before = {str(p.relative_to(runtime)):p.read_bytes() for p in runtime.rglob("*") if p.is_file()}
            class Clock(datetime):
                @classmethod
                def now(cls, tz=None): return fixed
            argv=["collector","--runtime-root",str(runtime),"--prereg",str(pp),"--out-dir",str(out)]
            with patch.object(sys,"argv",argv), patch.object(collector,"datetime",Clock), patch.dict(sys.modules,{"MetaTrader5":None}):
                if stage == "invalid_prereg":
                    with self.assertRaisesRegex(RuntimeError,"COLLECTOR_PREREG_MISMATCH"): collector.main()
                    self.assertFalse((out / "STATUS.json").exists())
                else:
                    self.assertEqual(collector.main(),0)
                    self.assertEqual(json.loads((out / "STATUS.json").read_text())["status"],expected)
            self.assertFalse((out / "SESSION_RECORD.json").exists(), "old capture leaked into a non-capture batch")
            self.assertEqual((out / "keep.txt").read_text(),"unrelated diagnostic")
            after = {str(p.relative_to(runtime)):p.read_bytes() for p in runtime.rglob("*") if p.is_file()}
            self.assertEqual(before, after)

    def test_wait_batches_cannot_publish_previous_session(self):
        for stage in ["missing_manifest","wrong_manifest","future_d0","weekend","before_window","no_families"]:
            with self.subTest(stage=stage): self.invoke(stage)

    def test_idempotent_batch_has_no_new_session_artifact(self):
        self.invoke("idempotent")

    def test_prereg_failure_leaves_no_old_publishable_output(self):
        self.invoke("invalid_prereg")

if __name__=="__main__": unittest.main()
