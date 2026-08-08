import sys
import unittest
from pathlib import Path

import pandas as pd

TOOLS = Path(__file__).resolve().parents[1] / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import gate_btc_survivorship_definitive_cmc_ranked_runner as runner


class CMCRankedDefinitiveRunnerTests(unittest.TestCase):
    def _base(self):
        return pd.DataFrame([
            {"snapshot_date": "2026-07-31", "rank": 40, "name": "OFFICIAL TRUMP", "symbol": "U1", "cmc_slug": "officialtrump", "symbol_resolution": "UNRESOLVED_AUDIT_KEY", "identity_resolved": False},
            {"snapshot_date": "2026-07-31", "rank": 41, "name": "MemeCore", "symbol": "U2", "cmc_slug": "memecore", "symbol_resolution": "UNRESOLVED_AUDIT_KEY", "identity_resolved": False},
            {"snapshot_date": "2024-01-31", "rank": 20, "name": "Old", "symbol": "OLD", "cmc_slug": "same-slug", "symbol_resolution": "PAGE_MATERIALIZED", "identity_resolved": True},
            {"snapshot_date": "2026-07-31", "rank": 42, "name": "New", "symbol": "U3", "cmc_slug": "same-slug", "symbol_resolution": "UNRESOLVED_AUDIT_KEY", "identity_resolved": False},
            {"snapshot_date": "2026-07-31", "rank": 43, "name": "Already", "symbol": "KEEP", "cmc_slug": "keep", "symbol_resolution": "PAGE_MATERIALIZED", "identity_resolved": True},
        ])

    def test_resolves_only_exact_unresolved_unique_slug(self):
        rows = [
            {"symbol": "TRUMP", "slug": "official-trump", "name": "OFFICIAL TRUMP"},
            {"symbol": "M", "slug": "memecore", "name": "MemeCore"},
            {"symbol": "NEW", "slug": "same-slug", "name": "New"},
            {"symbol": "WRONG", "slug": "keep", "name": "Already"},
        ]
        out, policy = runner._resolve_unresolved_ranked_slugs(self._base(), rows)
        trump = out[out["name"] == "OFFICIAL TRUMP"].iloc[0]
        meme = out[out["name"] == "MemeCore"].iloc[0]
        new = out[out["name"] == "New"].iloc[0]
        keep = out[out["name"] == "Already"].iloc[0]
        self.assertEqual(trump.symbol, "TRUMP")
        self.assertEqual(trump.symbol_resolution, "CMC_RANKED_ACTIVE_SLUG_MAP")
        self.assertEqual(meme.symbol, "M")
        self.assertFalse(bool(new.identity_resolved))
        self.assertEqual(keep.symbol, "KEEP")
        self.assertEqual(policy["historical_conflict_count"], 1)
        self.assertFalse(policy["existing_identity_overwrite_allowed"])
        self.assertFalse(policy["name_based_ranked_backfill_allowed"])

    def test_ambiguous_ranked_slug_fails_closed(self):
        frame = pd.DataFrame([
            {"snapshot_date": "2026-07-31", "rank": 50, "name": "Fartcoin", "symbol": "UX", "cmc_slug": "fartcoin", "symbol_resolution": "UNRESOLVED_AUDIT_KEY", "identity_resolved": False},
        ])
        rows = [
            {"symbol": "FARTCOIN", "slug": "fartcoin", "name": "Fartcoin"},
            {"symbol": "FRTC", "slug": "fartcoin", "name": "Fartcoin"},
        ]
        out, policy = runner._resolve_unresolved_ranked_slugs(frame, rows)
        self.assertFalse(bool(out.iloc[0].identity_resolved))
        self.assertEqual(policy["ranked_ambiguous_slug_count"], 1)

    def test_missing_slug_never_uses_name(self):
        frame = pd.DataFrame([
            {"snapshot_date": "2026-07-31", "rank": 60, "name": "KAITO", "symbol": "UX", "cmc_slug": "", "symbol_resolution": "UNRESOLVED_AUDIT_KEY", "identity_resolved": False},
        ])
        rows = [{"symbol": "KAITO", "slug": "kaito", "name": "KAITO"}]
        out, _ = runner._resolve_unresolved_ranked_slugs(frame, rows)
        self.assertFalse(bool(out.iloc[0].identity_resolved))


if __name__ == "__main__":
    unittest.main()
