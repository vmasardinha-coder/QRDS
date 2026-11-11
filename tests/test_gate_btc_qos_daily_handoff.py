import json
import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile

from tools import gate_btc_qos_daily_handoff as handoff

DAY = "2026-11-08"
RUN = "42572655754"


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


class ScopedDailyHandoffTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.qos = self.root / "runtime"
        self.zip = self.root / handoff.BUNDLE
        self.zip.parent.mkdir()
        self.manifest = self.zip.parent / "QOS_ORCHESTRATION_MANIFEST_test.json"
        self.orchestration = {
            "status": "PASS_WITH_GATEWAY_PENDING", "errors": [],
            "requested_data_cutoff": DAY, "matched_component_close": True,
            "locks": handoff.SAFETY,
            "engines": [{"name": name, "status": "PASS", "manifest": {"data_as_of": DAY}}
                        for name in ("V2A", "Delta")],
        }
        write(self.manifest, self.orchestration)
        self.write_bundle()

    def write_bundle(self, **overrides):
        manifest = dict(data_as_of=DAY, technical_status="PASS", operational_status="NOT_APPROVED",
                        real_orders=0, capital_used=0, evidence_status="RESEARCH_ONLY_NOT_PROMOTED",
                        lookahead_guard="signals execute on next daily bar")
        manifest.update(overrides)
        with ZipFile(self.zip, "w") as z:
            z.writestr("outputs/v2a_run_manifest.json", json.dumps(manifest))
            z.writestr("outputs/qos_v2a_current_portfolios.csv", "portfolio")
            z.writestr("data/processed/qos_v2a_master_daily.csv", "price")

    def seal(self, digest):
        signal = "2026-10-31"
        write(self.qos / "STATUS.json", {
            "status": "ACTIVE_PROSPECTIVE_THREE_TRACK", "latest_snapshot_date": DAY})
        cycle = self.qos / "cycles" / signal
        state_sha = "state-digest"
        write(cycle / "SIGNAL_STATE.json", {"signal_date": signal, "state_sha256": state_sha})
        row = {"source_run_id": RUN, "snapshot_date": DAY,
               "signal_date": signal, "signal_state_sha256": state_sha}
        row["row_sha256"] = handoff.canonical_payload_sha(row, "row_sha256")
        write(cycle / "path/snapshots" / f"{DAY}.json", row)
        manifest = {"cutoff": DAY, "signal_state_sha256": state_sha, "source_run_zip_sha256": digest}
        manifest["manifest_sha256"] = handoff.sha(handoff.packed(manifest))
        write(self.qos / "source_evidence" / signal / DAY / "PRICES.json", manifest)

    def test_partial_daily_is_admitted_only_via_qualified_v2a_receipt(self):
        with self.assertRaisesRegex(ValueError, "QOS_DAILY_HANDOFF_NOT_PUBLISHED"):
            handoff.verify(self.root, DAY, RUN)
        receipt = handoff.build(self.root, DAY, RUN)
        self.assertFalse((self.root / handoff.DAILY_MANIFEST).exists())
        self.seal(receipt["v2a_sha256"])
        self.assertEqual(handoff.sealed_source(self.qos, DAY)[0], RUN)
        handoff.verify(self.root, DAY, RUN, self.qos)

    def test_rejects_stale_delta_and_unsafe_v2a(self):
        self.orchestration["engines"][1]["manifest"]["data_as_of"] = "2026-11-07"
        write(self.manifest, self.orchestration)
        with self.assertRaisesRegex(ValueError, "QOS_COMPONENT_CUTOFF_NOT_ADMITTED:Delta"):
            handoff.build(self.root, DAY, RUN)
        self.orchestration["engines"][1]["manifest"]["data_as_of"] = DAY
        write(self.manifest, self.orchestration)
        self.write_bundle(real_orders=1)
        with self.assertRaisesRegex(ValueError, "QOS_V2A_SAFETY_MISMATCH"):
            handoff.build(self.root, DAY, RUN)
        self.assertFalse((self.root / handoff.RECEIPT).exists())

    def test_same_cutoff_with_different_bundle_cannot_feed_prl_alt(self):
        original = handoff.build(self.root, DAY, RUN)
        self.seal(original["v2a_sha256"])
        self.write_bundle(revision="different bytes, same cutoff")
        with self.assertRaisesRegex(ValueError, "QOS_DAILY_BUNDLE_HASH_MISMATCH"):
            handoff.verify(self.root, DAY, RUN, self.qos)
        handoff.build(self.root, DAY, RUN)
        with self.assertRaisesRegex(ValueError, "QOS_SEALED_BUNDLE_MISMATCH"):
            handoff.verify(self.root, DAY, RUN, self.qos)
        with self.assertRaisesRegex(ValueError, "QOS_DAILY_RECEIPT_SCOPE_MISMATCH"):
            handoff.verify(self.root, "2026-11-07", RUN, self.qos)
