from __future__ import annotations

import csv
import gzip
import io
import json
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

from tools.gate_btc_v2a_coinpaprika_shadow import compare, digest, main, parse_candidate, read_baseline


def sample_candidate():
    return [{"id": f"coin-{n}", "name": f"Coin {n}", "symbol": f"C{n}",
             "rank": n, "quotes": {"USD": {"market_cap": 1000000 - n}}}
            for n in range(1, 251)]


class CoinPaprikaShadowTests(unittest.TestCase):
    def test_ranked_top_250_and_no_scientific_credit(self):
        raw = json.dumps(list(reversed(sample_candidate()))).encode()
        top = parse_candidate(raw)
        self.assertEqual([item["rank"] for item in top], list(range(1, 251)))
        baseline = [{"id": f"old-{n}", "symbol": f"C{n}"} for n in range(1, 251)]
        report = compare(top, baseline, observed_at="2026-09-30T12:00:00Z",
                         baseline_date="2026-09-27", raw_sha256=digest(raw))
        self.assertEqual(report["symbol_overlap_count"], 250)
        self.assertFalse(report["identity_equivalence_claim"])
        self.assertFalse(report["source_substitution_performed"])
        self.assertFalse(report["feeds_frozen_engine"])
        self.assertEqual(report["scientific_credit"], 0)
        self.assertFalse(report["backfill"])

    def test_ambiguous_rank_rejected(self):
        rows = sample_candidate()
        rows[1]["rank"] = 1
        with self.assertRaisesRegex(ValueError, "ambiguous"):
            parse_candidate(json.dumps(rows).encode())

    def test_invalid_live_response_is_archived_before_rejection(self):
        raw = json.dumps(sample_candidate()[:10]).encode()
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "evidence"
            import sys
            from unittest.mock import MagicMock
            response = MagicMock()
            response.__enter__.return_value.read.return_value = raw
            argv = ["shadow", "--baseline-snapshot", "unused.json",
                    "--baseline-archive", "unused.csv.gz", "--output", str(output)]
            with patch.object(sys, "argv", argv), patch(
                    "tools.gate_btc_v2a_coinpaprika_shadow.urllib.request.urlopen",
                    return_value=response):
                with self.assertRaisesRegex(ValueError, "incomplete"):
                    main()
            self.assertEqual((output / "COINPAPRIKA_RAW.json").read_bytes(), raw)
            self.assertFalse((output / "COMPARISON.json").exists())

    def test_baseline_hash_is_required(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            out = io.StringIO()
            writer = csv.DictWriter(out, fieldnames=["id", "symbol"])
            writer.writeheader()
            writer.writerows({"id": f"old-{n}", "symbol": f"C{n}"} for n in range(1, 251))
            raw = out.getvalue().encode()
            compressed = gzip.compress(raw, mtime=0)
            archive = root / "source.csv.gz"
            archive.write_bytes(compressed)
            snapshot = root / "snapshot.json"
            snapshot.write_text(json.dumps({
                "universe_row_count": 250,
                "source_data_as_of": "2026-09-27",
                "source_hashes": {"universe_sha256": digest(raw)},
                "universe_archive": {"archive_sha256": digest(compressed),
                                     "raw_sha256": digest(raw)}
            }))
            _, rows = read_baseline(snapshot, archive)
            self.assertEqual(len(rows), 250)
            archive.write_bytes(compressed + b"altered")
            with self.assertRaisesRegex(ValueError, "hash mismatch"):
                read_baseline(snapshot, archive)


if __name__ == "__main__":
    unittest.main()
