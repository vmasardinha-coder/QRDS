import sys
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1] / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import gate_btc_survivorship_definitive_continuity_runner as continuity


class PITIdentityContinuityEvidenceTests(unittest.TestCase):
    def setUp(self):
        continuity.apply_continuity_evidence()

    def test_primary_source_backed_name_changes_are_admitted(self):
        cases = {
            "THETA": (["THETA", "Theta Network"], ["theta", "thetanetwork"]),
            "HBAR": (["Hedera Hashgraph", "Hedera"], ["hederahashgraph", "hedera"]),
            "FET": (["Fetch.ai", "Artificial Superintelligence Alliance"], ["fetch", "artificialsuperintelligencealliance"]),
            "INJ": (["Injective Protocol", "Injective"], ["injectiveprotocol", "injective"]),
        }
        for symbol, (names, slugs) in cases.items():
            with self.subTest(symbol=symbol):
                self.assertTrue(continuity.runner._continuity_ok(symbol, names, slugs))

    def test_unrelated_ticker_reuse_still_fails_closed(self):
        self.assertFalse(
            continuity.runner._continuity_ok(
                "AAA",
                ["Alpha Asset", "Another Asset"],
                ["alphaasset", "anotherasset"],
            )
        )

    def test_fet_evidence_does_not_merge_agix_or_ocean(self):
        self.assertNotIn("AGIX", continuity.EVIDENCE_BACKED_CONTINUITIES)
        self.assertNotIn("OCEAN", continuity.EVIDENCE_BACKED_CONTINUITIES)


if __name__ == "__main__":
    unittest.main()
