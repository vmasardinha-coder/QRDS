import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from gate_btc_h31_intraday_reconciliation import event_digest, reconcile_intraday_events


class H31CloseReconciliationTests(unittest.TestCase):
    def write(self, root, event, filename=None):
        event = dict(event)
        event["event_hash_sha256"] = event_digest(event)
        folder = root / "intraday_events" / event["session"]
        folder.mkdir(parents=True, exist_ok=True)
        (folder / (filename or (event["event_hash_sha256"] + ".json"))).write_text(json.dumps(event))
        return event

    def test_trigger_gap_keeps_closed_return_count_separate(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for session in ("2026-09-21", "2026-09-22"):
                d = self.write(root, {"event_type": "DECISION", "session": session, "trigger_state": "TRIGGER"})
                if session.endswith("21"):
                    self.write(root, {"event_type": "PAPER_CLOSE", "session": session, "decision_hash": event_digest(d)})
            before = {str(p): p.read_bytes() for p in root.rglob("*.json")}
            result = reconcile_intraday_events(root)
            self.assertEqual(result["H31_SHADOW_TRIGGERED_SESSIONS"], 2)
            self.assertEqual(result["H31_SHADOW_CLOSED_TRADES"], 1)
            self.assertEqual(result["H31_SHADOW_TRIGGER_SESSIONS_WITHOUT_CLOSE"], ["2026-09-22"])
            self.assertEqual(result["H31_SHADOW_CLOSE_RECONCILIATION_STATUS"], "PARTIAL_UNCLOSED_TRIGGER_GAPS")
            self.assertEqual(before, {str(p): p.read_bytes() for p in root.rglob("*.json")})

    def test_duplicate_close_does_not_increment(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            d = self.write(root, {"event_type": "DECISION", "session": "2026-09-21", "trigger_state": "TRIGGER"})
            c = self.write(root, {"event_type": "PAPER_CLOSE", "session": d["session"], "decision_hash": event_digest(d)})
            self.write(root, c, "duplicate.json")
            result = reconcile_intraday_events(root)
            self.assertEqual(result["H31_SHADOW_CLOSED_TRADES"], 1)
            self.assertEqual(result["H31_SHADOW_CLOSE_RECONCILIATION_STATUS"], "PASS_TRIGGER_CLOSE_RECONCILIATION")

    def test_orphan_close_does_not_create_return_credit(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.write(root, {"event_type": "PAPER_CLOSE", "session": "2026-09-22", "decision_hash": "not-a-decision"})
            result = reconcile_intraday_events(root)
            self.assertEqual(result["H31_SHADOW_CLOSED_TRADES"], 0)
            self.assertEqual(result["H31_SHADOW_INVALID_EVENT_COUNT"], 1)
            self.assertEqual(result["H31_SHADOW_CLOSE_RECONCILIATION_STATUS"], "FAIL_EVENT_RECONCILIATION")


if __name__ == "__main__":
    unittest.main()
