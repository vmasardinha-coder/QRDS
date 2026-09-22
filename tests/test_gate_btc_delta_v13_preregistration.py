"""Uma serie sucessora nao pode herdar evidencia nem retunar premissa.

O V12 fechou por lacuna de dados, nao por resultado. Isso torna a sucessora
perigosa de um jeito especifico: doze observacoes ja estao na mesa, e qualquer
parametro que mude agora muda depois de ve-las. Estes testes prendem as duas
metades -- o que o encerramento tem de registrar e o que a sucessora tem de
carregar intacto.
"""
from __future__ import annotations

import json
import unittest
from pathlib import Path

V12 = Path("migration/reporting/delta_v12_engine_contract.json")
V13 = Path("migration/reporting/delta_v13_engine_contract.json")
CLOSURE = Path("migration/reporting/delta_v12_engine_closure.json")

SAFETY = {
    "research_only": True, "shadow_only": True, "not_approved": True,
    "engine_feed": False, "exchange_auth_allowed": False,
    "orders": 0, "real_capital": 0, "methodology_changes": 0,
    "promotion_eligible": False, "official_replica_claim": False,
}


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


class V12ClosureTests(unittest.TestCase):
    def setUp(self) -> None:
        self.closure = load(CLOSURE)

    def test_the_cause_recorded_is_the_gap_and_not_the_return(self) -> None:
        self.assertEqual(self.closure["decision"],
                         "SERIES_TERMINATED_BY_DATA_GAP_NOT_BY_RESULT")
        self.assertIn("not because of what the twelve observed days returned",
                      self.closure["why_this_is_not_a_result_driven_decision"])

    def test_the_terminal_state_is_recorded_exactly(self) -> None:
        terminal = self.closure["terminal_state"]
        self.assertEqual(terminal["anchor_date"], "2026-09-06")
        self.assertEqual(terminal["first_booked_close"], "2026-09-08")
        self.assertEqual(terminal["last_observed_close"], "2026-09-19")
        self.assertEqual(terminal["observed_days"], 12)
        self.assertEqual(terminal["ledger_rows"], 48)
        self.assertEqual(terminal["engine_version_of_every_committed_row"],
                         "DELTA_V12_ENGINE_1.0")
        self.assertLess(terminal["observed_days"], terminal["evidence_gate_min_observations"])

    def test_backfill_and_re_anchor_are_both_refused_in_writing(self) -> None:
        refused = self.closure["what_was_considered_and_refused"]
        self.assertIn("REFUSED", refused["backfill_the_two_missing_days"])
        self.assertIn("REFUSED", refused["re_anchor_this_series"])
        self.assertIn("REFUSED", refused["shorten_the_series_to_end_at_2026_09_19"])
        self.assertIn("REFUSED", refused["carry_the_twelve_observations_into_the_successor"])

    def test_the_ledger_is_declared_untouched(self) -> None:
        disposition = self.closure["disposition_of_the_evidence"]
        self.assertIn("byte-untouched", disposition["the_twelve_observations_remain"])
        self.assertIn("No row is rewritten", disposition["the_twelve_observations_remain"])

    def test_the_closed_record_is_never_evidence_for_anything(self) -> None:
        nots = " ".join(self.closure["disposition_of_the_evidence"]["what_they_are_not"])
        self.assertIn("not evidence toward any 60-observation gate", nots)
        self.assertIn("not promotable", nots)
        self.assertIn("not comparable", nots)

    def test_the_successor_inherits_nothing(self) -> None:
        successor = self.closure["successor"]
        self.assertEqual(successor["contract"], str(V13))
        self.assertIs(successor["inherits_evidence"], False)
        self.assertIs(successor["inherits_anchor"], False)
        self.assertIs(successor["inherits_counter"], False)

    def test_governance_flags_survive_the_closure(self) -> None:
        for key, expected in SAFETY.items():
            self.assertEqual(self.closure["safety"][key], expected, key)


class V13PreregistrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.v12 = load(V12)
        self.v13 = load(V13)

    def test_it_is_a_new_series_with_its_own_identity(self) -> None:
        self.assertEqual(self.v13["version"], "DELTA_V13_ENGINE_1.0")
        self.assertEqual(self.v13["schema"], "gate_btc.delta_v13_engine_contract.v1")
        self.assertEqual(self.v13["frozen_date"], "2026-09-22")
        self.assertEqual(self.v13["status"], "PREREGISTERED_AWAITING_FIRST_ANCHOR")

    def test_the_anchor_is_null_and_cannot_be_backdated(self) -> None:
        # O ponto central: nenhum fechamento que ja existe pode virar esta ancora.
        anchor = self.v13["anchor"]
        self.assertIsNone(anchor["anchor_date"])
        self.assertIs(anchor["backdating_prohibited"], True)
        self.assertEqual(anchor["not_before"], self.v13["frozen_date"])
        self.assertIn("never chosen later", anchor["anchor_rule"])

    def test_the_counter_starts_at_zero_with_no_credit_carried_over(self) -> None:
        evidence = self.v13["evidence"]
        self.assertEqual(evidence["counter_starts_at"], 0)
        self.assertEqual(evidence["min_observations"], 60)
        self.assertIn("No observation from", evidence["no_credit_for_prior_series"])

    def test_nothing_is_inherited_from_the_closed_series(self) -> None:
        supersession = self.v13["supersession"]
        self.assertEqual(supersession["supersedes"], "DELTA_V12_ENGINE")
        self.assertEqual(supersession["closure_record"], str(CLOSURE))
        for key in ("inherits_evidence", "inherits_anchor",
                    "inherits_counter", "inherits_ledger"):
            self.assertIs(supersession[key], False, key)
        self.assertNotEqual(supersession["ledger_path"], "runtime/ledgers/delta_v12_engine")

    def test_no_frozen_premise_is_retuned_after_seeing_twelve_days(self) -> None:
        # A tentacao concreta: mexer num limiar, num custo ou num tamanho de
        # selecao agora seria retunar contra retornos ja observados.
        for key in ("costs", "risk", "universe", "funding", "annualization_days",
                    "risk_free_annual", "selection_size_policy",
                    "selection_size_rationale_recorded_before_any_return"):
            self.assertEqual(self.v13[key], self.v12[key], key)
        for key in ("top_n", "bottom_n", "persistence_days", "minimum_signal_history",
                    "score", "signal_lookbacks", "selected_fraction_of_universe",
                    "execution_timing", "signal_timing"):
            self.assertEqual(self.v13["selection"][key], self.v12["selection"][key], key)
        for key in ("min_observations", "min_product_sharpe", "max_drawdown",
                    "gap_policy", "leaderboard_role"):
            self.assertEqual(self.v13["evidence"][key], self.v12["evidence"][key], key)

    def test_the_corrected_cross_section_is_an_original_premise_not_a_correction(self) -> None:
        selection = self.v13["selection"]
        self.assertEqual(selection["cross_section_panel"], "ADMITTED_ON_OR_BEFORE_THE_DAY")
        self.assertIn("original premise", selection["cross_section_panel_rationale"])
        # Uma preregistracao nova nao carrega historico de emenda de outra.
        self.assertNotIn("supersedes", selection)
        self.assertNotIn("amendments", self.v13)

    def test_the_books_are_this_series_own(self) -> None:
        books = self.v13["books"]["books"]
        self.assertEqual(len(books), 4)
        self.assertTrue(all(b.startswith("V13_") for b in books), books)
        self.assertIs(self.v13["books"]["retrospective_winner_selection_forbidden"], True)

    def test_the_three_records_are_never_compared(self) -> None:
        self.assertIn("never ranked against either",
                      self.v13["supersession"]["never_compare"])
        self.assertIn("never compared", self.v13["relationship_to_v11"])

    def test_governance_flags_are_intact(self) -> None:
        for key, expected in SAFETY.items():
            self.assertEqual(self.v13["safety"][key], expected, key)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
