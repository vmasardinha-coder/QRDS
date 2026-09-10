from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "tools" / "GATE_BTC_DAILY_EXECUTIVE_RECONCILER_V2.py"


class DailyExecutiveRuntimePrecedenceTests(unittest.TestCase):
    def test_runtime_is_attempted_before_local_qmaster_fallback(self):
        source = TARGET.read_text(encoding="utf-8")
        start = source.index("def sync_qmaster_from_runtime")
        end = source.index("\ndef load_state", start)
        body = source[start:end]
        self.assertLess(body.index('gh = shutil.which("gh")'), body.index("_validated_local_qmaster()"))
        self.assertIn('return QMASTER_CACHE, "REMOTE_RUNTIME_SYNCED"', body)
        self.assertIn('LOCAL_FALLBACK_SNAPSHOT', source)
        self.assertNotIn('return local, "LOCAL_CANONICAL"', body)

    def test_reporting_safety_invariants_remain_explicit(self):
        source = TARGET.read_text(encoding="utf-8")
        for token in (
            '"RESEARCH_ONLY": True',
            '"SHADOW_ONLY": True',
            '"NOT_APPROVED": True',
            '"ORDERS": 0',
            '"REAL_CAPITAL": 0',
            '"ENGINE_FEED": False',
        ):
            self.assertIn(token, source)


if __name__ == "__main__":
    unittest.main()
