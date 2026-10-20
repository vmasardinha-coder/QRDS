import copy
import unittest
from tools.gate_btc_pit150_source_crosswalk import build_crosswalk


class CrosswalkTests(unittest.TestCase):
    def setUp(self):
        self.diagnostic = {"attempted_symbols": 150, "loaded_symbols": 149, "failed_symbols": 1,
                           "rows": [{"symbol": "BTW", "coin_id": "bitway", "action_class": "SOURCE_RECOVERY_CANDIDATE",
                                     "failure_reason": "no candles", "observed_history_rows": None}]}
        self.registry = {"entry_count": 1, "entries": [{"symbol": "BTW", "source_identity": "BITGET_SPOT",
                           "source_symbol": "BTWUSDT", "source_admitted": True}]}

    def test_symbol_match_never_proves_asset_identity_or_admission(self):
        inputs = copy.deepcopy((self.diagnostic, self.registry))
        report = build_crosswalk(self.diagnostic, self.registry)
        self.assertEqual(report["assets"][0]["identity_evidence"], "REGISTRY_COIN_ID_MISSING")
        self.assertFalse(report["assets"][0]["cross_contract_identity_proven"])
        self.assertFalse(report["assets"][0]["pit150_source_substitution_authorized"])
        self.assertFalse(report["engine_feed"])
        self.assertEqual(report["prospective_credit"], 0)
        self.assertEqual((self.diagnostic, self.registry), inputs)

    def test_even_same_coin_id_requires_contract_proofs(self):
        self.registry["entries"][0]["coin_id"] = "bitway"
        report = build_crosswalk(self.diagnostic, self.registry)
        self.assertEqual(report["identity_evidence_counts"], {"COIN_ID_MATCH_ONLY": 1})
        self.assertFalse(report["assets"][0]["cross_contract_identity_proven"])

    def test_mismatch_and_absent_candidate_remain_explicit(self):
        self.registry["entries"][0]["coin_id"] = "different-coin"
        self.assertEqual(build_crosswalk(self.diagnostic, self.registry)["assets"][0]["identity_evidence"], "COIN_ID_MISMATCH")
        self.registry = {"entry_count": 0, "entries": []}
        self.assertEqual(build_crosswalk(self.diagnostic, self.registry)["registry_candidate_matches"], 0)

    def test_bad_denominator_duplicate_or_count_fails_closed(self):
        for key, value in [("attempted_symbols", 137), ("failed_symbols", 2)]:
            diagnostic = copy.deepcopy(self.diagnostic)
            diagnostic[key] = value
            with self.assertRaises(ValueError):
                build_crosswalk(diagnostic, self.registry)
        self.registry["entries"].append(copy.deepcopy(self.registry["entries"][0]))
        self.registry["entry_count"] = 2
        with self.assertRaises(ValueError):
            build_crosswalk(self.diagnostic, self.registry)

    def test_prior_exclusion_is_visible_but_never_repairs_legacy_gap(self):
        report = build_crosswalk(self.diagnostic, {"entry_count": 0, "entries": []}, ["BTW"])
        row = report["assets"][0]
        self.assertEqual(row["worklist_state"], "PRIOR_STRUCTURAL_EXCLUSION_HISTORICAL_GAP_PRESERVED")
        self.assertFalse(row["legacy_gap_resolved"])
        self.assertFalse(row["prior_exclusion_identity_revalidated"])
        self.assertEqual(report["legacy_failed_symbols"], 1)
        self.assertEqual(report["pit150_denominator_preserved"], 150)

    def test_qualified_contract_has_its_own_state_without_legacy_admission(self):
        self.registry["entries"][0].update(qa_pass=True, qualification="QUALIFIED_EXACT_SOURCE")
        report = build_crosswalk(self.diagnostic, self.registry)
        row = report["assets"][0]
        self.assertEqual(row["worklist_state"], "QUALIFIED_SOURCE_CONTRACT_PRESENT_PIT150_REPAIR_NOT_PROVEN")
        self.assertFalse(row["pit150_source_substitution_authorized"])
        self.assertEqual(row["identity_evidence"], "REGISTRY_COIN_ID_MISSING")

    def test_unqualified_ticker_candidate_is_not_reported_as_qualified(self):
        row = build_crosswalk(self.diagnostic, self.registry)["assets"][0]
        self.assertEqual(row["worklist_state"], "SOURCE_DISCOVERY_OR_QUALIFICATION_PENDING")

    def test_conflicting_or_malformed_prior_inventory_fails_closed(self):
        self.registry["entries"][0].update(qa_pass=True, qualification="QUALIFIED_EXACT_SOURCE")
        with self.assertRaises(ValueError):
            build_crosswalk(self.diagnostic, self.registry, ["BTW"])
        for bad in ["BTW", ["BTW", "BTW"], [None], [""]]:
            with self.assertRaises(ValueError):
                build_crosswalk(self.diagnostic, self.registry, bad)



class CurrentDiagnosticBindingTests(unittest.TestCase):
    def test_current_snapshot_and_counts_are_bound(self):
        from tools.gate_btc_pit150_source_crosswalk import validate_authoritative_status
        diagnostic={"snapshot_id":"2026-10-15-run-1","source_run_id":1,"data_as_of":"2026-10-15",
                    "attempted_symbols":150,"loaded_symbols":126,"failed_symbols":24}
        status={"latest_snapshot_id":"2026-10-15-run-1","latest_source_run_id":"1","latest_source_data_as_of":"2026-10-15",
                "latest_attempted_symbols":150,"latest_loaded_symbols":126,"latest_failed_symbols":24}
        self.assertEqual(validate_authoritative_status(diagnostic,status)["loaded_symbols"],126)
        for key,value in [("snapshot_id","2026-10-14-run-0"),("source_run_id",2),("data_as_of","2026-10-14"),
                          ("attempted_symbols",149),("loaded_symbols",124),("failed_symbols",26)]:
            bad=dict(diagnostic);bad[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):
                validate_authoritative_status(bad,status)

    def test_directory_selection_uses_status_not_lexical_last_file(self):
        import tempfile,json,subprocess,sys
        from pathlib import Path
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/"diagnostics").mkdir()
            diagnostic={"snapshot_id":"2026-10-15-run-1","source_run_id":1,"data_as_of":"2026-10-15",
                        "attempted_symbols":150,"loaded_symbols":150,"failed_symbols":0,"rows":[]}
            status={"latest_snapshot_id":diagnostic["snapshot_id"],"latest_source_run_id":1,"latest_source_data_as_of":"2026-10-15",
                    "latest_attempted_symbols":150,"latest_loaded_symbols":150,"latest_failed_symbols":0}
            (root/"diagnostics/2026-10-15-run-1.json").write_text(json.dumps(diagnostic))
            (root/"diagnostics/zzzz-unrelated.json").write_text("{}")
            (root/"status.json").write_text(json.dumps(status))
            (root/"registry.json").write_text(json.dumps({"entry_count":0,"entries":[]}))
            script=Path(__file__).resolve().parents[1]/"tools/gate_btc_pit150_source_crosswalk.py"
            subprocess.run([sys.executable,str(script),"--diagnostic-dir",str(root/"diagnostics"),"--status",str(root/"status.json"),
                            "--registry",str(root/"registry.json"),"--output",str(root/"result.json")],check=True,capture_output=True)
            out=json.loads((root/"result.json").read_text())
            self.assertEqual(out["data_as_of"],"2026-10-15")
            self.assertEqual(out["authoritative_status_binding"]["failed_symbols"],0)


class PriorReviewContinuityTests(unittest.TestCase):
    def inputs(self, category="SHORT_SOURCE_HISTORY"):
        diagnostic={"attempted_symbols":150,"loaded_symbols":149,"failed_symbols":1,
                    "data_as_of":"2026-10-17","rows":[{"symbol":"SOFID","coin_id":"sofiusd",
                    "action_class":"SEMANTIC_SCOPE_REVIEW","failure_reason":"no candles","observed_history_rows":None}]}
        review={"review_date":"2026-10-15","cases":[{"symbol":"SOFID","coin_id":"sofiusd",
                "category":category,"evidence":"115 completed days at the recorded cutoff",
                "baseline_cutoff":"2026-10-14","next_action":"Collect until full qualification; no admission yet."}]}
        return diagnostic, {"entry_count":0,"entries":[]}, review

    def test_history_review_does_not_reopen_source_discovery_or_admit_prices(self):
        diagnostic,registry,review=self.inputs()
        original=copy.deepcopy((diagnostic,registry,review))
        out=build_crosswalk(diagnostic,registry,["SOFID"],review)
        row=out["assets"][0]
        self.assertEqual(row["operational_work_state"],"HISTORY_COLLECTION_SOURCE_ALREADY_IDENTIFIED")
        self.assertTrue(row["bounded_source_review_completed"])
        self.assertFalse(row["coverage_dependency_resolved"])
        self.assertFalse(row["pit150_source_substitution_authorized"])
        self.assertFalse(row["prior_exclusion_identity_revalidated"])
        self.assertEqual((out["legacy_loaded_symbols"],out["legacy_failed_symbols"],out["pit150_denominator_preserved"]),(149,1,150))
        self.assertEqual((diagnostic,registry,review),original)

    def test_scope_and_native_access_remain_distinct(self):
        for category,state in [("FUND_SCOPE_REVIEW","AWAITING_EXECUTION_SOURCE_OR_PROSPECTIVE_SCOPE_DECISION"),
                               ("ACCESS_IDENTITY_REVIEW","AWAITING_NATIVE_SOURCE_ACCESS_OR_IDENTITY_PROOF")]:
            diagnostic,registry,review=self.inputs(category)
            self.assertEqual(build_crosswalk(diagnostic,registry,["SOFID"],review)["assets"][0]["operational_work_state"],state)

    def test_symbol_collision_does_not_apply_old_review(self):
        diagnostic,registry,review=self.inputs()
        review["cases"][0]["coin_id"]="different-asset"
        row=build_crosswalk(diagnostic,registry,["SOFID"],review)["assets"][0]
        self.assertIn("IDENTITY_MISMATCH",row["prior_case_review_binding"])
        self.assertNotIn("bounded_source_review_completed",row)

    def test_future_review_or_duplicate_identity_fails_closed(self):
        diagnostic,registry,review=self.inputs()
        review["review_date"]="2026-10-18"
        with self.assertRaises(ValueError):build_crosswalk(diagnostic,registry,["SOFID"],review)
        review["review_date"]="2026-10-15";review["cases"].append(copy.deepcopy(review["cases"][0]))
        with self.assertRaises(ValueError):build_crosswalk(diagnostic,registry,["SOFID"],review)

    def test_current_qualified_source_contract_takes_precedence(self):
        diagnostic,registry,review=self.inputs()
        registry={"entry_count":1,"entries":[{"symbol":"SOFID","coin_id":"sofiusd","source_admitted":True,
                  "qa_pass":True,"qualification":"QUALIFIED_EXACT_SOURCE"}]}
        row=build_crosswalk(diagnostic,registry,[],review)["assets"][0]
        self.assertEqual(row["operational_work_state"],"QUALIFIED_SOURCE_CONTRACT_PRESENT_PIT150_REPAIR_NOT_PROVEN")
        self.assertFalse(row["pit150_source_substitution_authorized"])


if __name__ == "__main__":
    unittest.main()


class NativeCandidateAuditContinuityTests(unittest.TestCase):
    def inputs(self, cutoff="2026-10-19", coin_id="grx-chain", registry=None):
        import json
        from tools.gate_btc_pit150_source_crosswalk import NATIVE_AUDIT_PATH
        diagnostic = {"data_as_of": cutoff, "attempted_symbols": 150, "loaded_symbols": 149,
            "failed_symbols": 1, "rows": [{"symbol": "GRX", "coin_id": coin_id,
                "action_class": "SOURCE_RECOVERY_CANDIDATE", "failure_reason": "no candles",
                "observed_history_rows": None}]}
        report = build_crosswalk(diagnostic, registry or {"entry_count": 0, "entries": []})
        audit = json.loads(NATIVE_AUDIT_PATH.read_text(encoding="utf-8"))
        return report, audit

    def test_existing_rejected_review_replaces_no_prior_case_without_admission(self):
        from tools.gate_btc_pit150_source_crosswalk import retain_native_candidate_audit
        report, audit = self.inputs()
        before = copy.deepcopy((report, audit))
        out = retain_native_candidate_audit(report, audit)
        row = out["assets"][0]
        self.assertTrue(row["bounded_source_review_completed"])
        self.assertEqual(row["operational_work_state"], "AWAITING_RECONCILED_NATIVE_SOURCE_ARCHIVE")
        self.assertEqual(row["prior_native_candidate_audit"]["hour_complete_utc_days"], 194)
        self.assertEqual(row["prior_native_candidate_audit"]["hour_positive_execution_utc_days"], 154)
        self.assertFalse(row["coverage_dependency_resolved"])
        self.assertFalse(row["pit150_source_substitution_authorized"])
        self.assertEqual(out["legacy_loaded_symbols"], 149)
        self.assertEqual(out["scientific_credit"], 0)
        self.assertEqual((report, audit), before)

    def test_symbol_collision_and_earlier_diagnostics_do_not_inherit_review(self):
        from tools.gate_btc_pit150_source_crosswalk import retain_native_candidate_audit
        for kwargs in ({"coin_id": "another-grx"}, {"cutoff": "2026-10-16"}):
            with self.subTest(kwargs=kwargs):
                report, audit = self.inputs(**kwargs)
                self.assertEqual(retain_native_candidate_audit(report, audit), report)

    def test_changed_receipt_cannot_clear_source_failure(self):
        from tools.gate_btc_pit150_source_crosswalk import retain_native_candidate_audit
        report, audit = self.inputs()
        audit["grx"]["candidate_qa_pass"] = True
        with self.assertRaisesRegex(ValueError, "binding mismatch"):
            retain_native_candidate_audit(report, audit)

    def test_later_qualified_contract_is_not_downgraded_by_old_review(self):
        from tools.gate_btc_pit150_source_crosswalk import retain_native_candidate_audit
        registry = {"entry_count": 1, "entries": [{"symbol": "GRX", "coin_id": "grx-chain",
            "source_admitted": True, "qa_pass": True, "qualification": "QUALIFIED_EXACT_SOURCE"}]}
        report, audit = self.inputs(registry=registry)
        out = retain_native_candidate_audit(report, audit)
        self.assertEqual(out["assets"][0]["operational_work_state"],
            "QUALIFIED_SOURCE_CONTRACT_PRESENT_PIT150_REPAIR_NOT_PROVEN")

    def test_outside_selection_case_keeps_prior_review_without_repair_credit(self):
        from tools.gate_btc_pit150_source_crosswalk import retain_native_candidate_audit
        report, audit = self.inputs()
        row = report["assets"].pop()
        report["tracked_cases_not_current_failures"] = [row]
        out = retain_native_candidate_audit(report, audit)
        self.assertTrue(out["tracked_cases_not_current_failures"][0]["bounded_source_review_completed"])
        self.assertFalse(out["tracked_cases_not_current_failures"][0]["legacy_gap_resolved"])
