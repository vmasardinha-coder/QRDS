import unittest
from datetime import datetime,timedelta
from tools.gate_btc_h31_close_window import closed_holding_window

class ClosedWindowTests(unittest.TestCase):
    def source(self):
        entry=datetime.fromisoformat("2026-10-15T09:30:00-03:00")
        rows={}
        for i in range(25):
            t=entry+timedelta(minutes=5*i)
            rows[t]={"timestamp":t.isoformat(),"open":100,"high":101,"low":99,"close":100}
        return entry,entry+timedelta(minutes=120),rows

    def test_forming_exit_bar_cannot_change_close_excursion(self):
        entry,exit_,rows=self.source()
        before=closed_holding_window(rows,entry,exit_)
        rows[exit_]["high"]=10000
        rows[exit_]["low"]=1
        after=closed_holding_window(rows,entry,exit_)
        self.assertEqual(before,after)
        self.assertEqual(len(after),24)
        self.assertEqual(max(x["high"] for x in after),101)
        self.assertNotIn(rows[exit_],after)

    def test_missing_closed_bar_is_rejected_without_imputation(self):
        entry,exit_,rows=self.source()
        del rows[entry+timedelta(minutes=35)]
        with self.assertRaisesRegex(RuntimeError,"INCOMPLETE_CLOSED_HOLD"):closed_holding_window(rows,entry,exit_)

    def test_frozen_horizon_and_physical_ohlc_are_enforced(self):
        entry,exit_,rows=self.source()
        with self.assertRaisesRegex(RuntimeError,"DURATION"):closed_holding_window(rows,entry,exit_+timedelta(minutes=5))
        rows[entry]["high"]=99
        with self.assertRaisesRegex(RuntimeError,"OHLC"):closed_holding_window(rows,entry,exit_)


class ExistingCloseTests(unittest.TestCase):
    def test_auxiliary_changes_do_not_append_and_economic_conflicts_fail(self):
        import json,hashlib,tempfile
        from pathlib import Path
        from tools.gate_btc_h31_close_window import prior_close_hash
        event={"event_type":"PAPER_CLOSE","session":"2026-10-15","entry":100,"exit":101,"MFE_bps":100,"MAE_bps":0}
        digest=hashlib.sha256(json.dumps(event,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            path=root/(digest+".json")
            path.write_text(json.dumps(dict(event,event_hash_sha256=digest)))
            before=path.read_bytes()
            self.assertEqual(prior_close_hash(root,dict(event,MFE_bps=999)),digest)
            self.assertEqual(before,path.read_bytes())
            self.assertEqual(len(list(root.glob("*.json"))),1)
            with self.assertRaisesRegex(RuntimeError,"ECONOMIC_CLOSE"):
                prior_close_hash(root,dict(event,exit=102))
            event["event_hash_sha256"]="wrong"
            path.write_text(json.dumps(event))
            with self.assertRaisesRegex(RuntimeError,"HASH_MISMATCH"):
                prior_close_hash(root,event)
