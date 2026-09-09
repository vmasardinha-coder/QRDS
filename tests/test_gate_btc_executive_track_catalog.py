import json
import tempfile
import unittest
from pathlib import Path

from tools.gate_btc_executive_track_catalog import build


class ExecutiveTrackCatalogTest(unittest.TestCase):
    def _write(self, root: Path, rel: str, obj: dict) -> Path:
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(obj), encoding="utf-8")
        return p

    def test_separates_ledgers_declarations_and_required_missing_reference(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            artifacts = root / "artifacts"
            requirements = self._write(root, "requirements.json", {
                "schema": "gate_btc.executive_reporting_requirements.v1",
                "required_named_tracks": [{
                    "track_id": "empiricus_delta",
                    "display_name": "Empiricus Delta",
                    "classification": "EXTERNAL_BENCHMARK_REQUIRED_IN_EXECUTIVE_INVENTORY",
                }],
            })
            self._write(artifacts, "gate_btc/v16b/GATE_BTC_V16_FAMILY_GOVERNANCE_20260815.json", {
                "versions": {
                    "V16B": {"role": "FROZEN_BASELINE"},
                    "V16C": {"role": "STRUCTURAL_CHALLENGER", "status": "NOT_YET_FROZEN"},
                    "V16D": {"role": "RISK_ENGINE_CHALLENGER", "status": "NOT_YET_FROZEN"},
                    "V16E": {"role": "ALLOCATION_READY_FINAL", "status": "NOT_YET_FROZEN"},
                }
            })
            self._write(artifacts, "gate_btc/v16b/GATE_BTC_V16C_STRUCTURAL_PREREG_20260815.json", {
                "prereg_id": "V16C_TEST",
                "status": "PREREGISTERED_RESEARCH_CHALLENGER_NOT_LIVE",
            })
            state = {
                "ledger_inventory": {
                    "v16b": {"ledger_id": "v16b", "status": "SCIENTIFIC_BLOCK", "inventory_only": True},
                    "d100": {"ledger_id": "d100", "status": "ACTIVE", "inventory_only": True},
                }
            }

            out = build(state, artifacts, requirements)

            self.assertEqual(set(out["ledger_tracks"]), {"v16b", "d100"})
            self.assertEqual(set(out["declared_nonledger_tracks"]), {"v16c", "v16d", "v16e"})
            self.assertEqual(
                out["declared_nonledger_tracks"]["v16c"]["status"],
                "PREREGISTERED_RESEARCH_CHALLENGER_NOT_LIVE",
            )
            self.assertFalse(out["declared_nonledger_tracks"]["v16c"]["ledger_present"])
            emp = out["required_reporting_references"]["empiricus_delta"]
            self.assertEqual(emp["canonical_evidence_status"], "ABSENT_NOT_INFERRED")
            self.assertFalse(emp["scientific_authority"])
            self.assertIn("empiricus_delta", out["summary"]["missing_canonical_reference_ids"])
            self.assertTrue(out["summary"]["does_not_change_delivery_health"])
            self.assertTrue(out["summary"]["does_not_authorize_science_or_trading"])

    def test_required_reference_detects_named_artifact_without_interpreting_it(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            artifacts = root / "artifacts"
            requirements = self._write(root, "requirements.json", {
                "required_named_tracks": [{
                    "track_id": "empiricus_delta",
                    "display_name": "Empiricus Delta",
                }]
            })
            self._write(artifacts, "benchmarks/EMPIRICUS_DELTA_SOURCE.json", {"anything": "uninterpreted"})
            out = build({"ledger_inventory": {}}, artifacts, requirements)
            emp = out["required_reporting_references"]["empiricus_delta"]
            self.assertEqual(emp["canonical_evidence_status"], "PRESENT")
            self.assertEqual(len(emp["canonical_evidence_matches"]), 1)
            self.assertFalse(emp["scientific_authority"])


if __name__ == "__main__":
    unittest.main()
