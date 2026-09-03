import json
import unittest
from pathlib import Path

ENGINE = Path('migration/reporting/delta_v12_engine_contract.json')
UNIVERSE = Path('migration/reporting/delta_v12_universe_expansion_contract.json')
V11 = Path('migration/canonical/delta/config_delta_v11.json')


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding='utf-8-sig'))


class DeltaV12EngineContractTests(unittest.TestCase):
    def setUp(self):
        self.engine = load(ENGINE)
        self.universe = load(UNIVERSE)
        self.v11 = load(V11)

    def test_selection_size_is_frozen_at_ten_and_ten(self):
        selection = self.engine['selection']
        self.assertEqual((selection['top_n'], selection['bottom_n']), (10, 10))
        self.assertAlmostEqual(selection['selected_fraction_of_universe'], 0.20, 12)

    def test_another_selection_size_cannot_be_backdated_to_this_freeze(self):
        policy = self.engine['selection_size_policy']
        self.assertIn('NEW preregistration', policy)
        self.assertIn('never be added or switched after observing', policy)
        self.assertIn('backdated', policy)

    def test_risk_premises_are_inherited_from_v11_unchanged(self):
        # A parallel engine that silently retunes risk is not the same strategy on
        # a bigger universe; it is a different strategy with a familiar name.
        for key, value in self.engine['risk'].items():
            self.assertEqual(value, self.v11[key], key)
        self.assertEqual(self.engine['selection']['persistence_days'], self.v11['persistence_days'])
        self.assertEqual(self.engine['selection']['signal_lookbacks'], self.v11['signal_lookbacks'])
        self.assertEqual(self.engine['evidence']['min_observations'],
                         self.v11['evidence_gate_min_observations'])

    def test_costs_are_tiered_and_match_the_universe_contract(self):
        bands = {b['band']: b['slippage_bps_per_side']
                 for b in self.universe['cost_model_by_liquidity_band']['bands']}
        self.assertEqual(self.engine['costs']['slippage_by_band'], bands)
        values = [bands[b] for b in ('1-30', '31-50', '51-75', '76-100')]
        self.assertEqual(values, sorted(values))
        # The flat V11 slippage must not survive into the tail.
        self.assertGreater(values[-1], self.v11['slippage_bps_per_side'])
        self.assertEqual(self.engine['costs']['fee_bps_per_side'], self.v11['fee_bps_per_side'])

    def test_anchor_is_unset_and_cannot_be_backdated(self):
        anchor = self.engine['anchor']
        self.assertIsNone(anchor['anchor_date'])
        self.assertTrue(anchor['backdating_prohibited'])
        self.assertEqual(anchor['initial_nav'], 1.0)
        self.assertIn('DIAGNOSTIC_ONLY', anchor['historical_replay_status'])

    def test_all_four_books_run_in_parallel_with_no_retrospective_winner(self):
        books = self.engine['books']
        self.assertEqual(len(books['books']), 4)
        self.assertTrue(books['parallel_variants_required'])
        self.assertTrue(books['retrospective_winner_selection_forbidden'])
        self.assertEqual(self.engine['evidence']['leaderboard_role'], 'DESCRIPTIVE_ONLY')

    def test_other_strata_require_their_own_preregistration(self):
        self.assertEqual(self.engine['universe']['stratum'], 'TOP100')
        self.assertIn('SEPARATE_PREREGISTRATION_REQUIRED',
                      self.engine['universe']['other_strata_status'])

    def test_safety_boundary_forbids_promotion_orders_and_capital(self):
        safety = self.engine['safety']
        for key in ('research_only', 'shadow_only', 'not_approved'):
            self.assertTrue(safety[key], key)
        for key in ('engine_feed', 'exchange_auth_allowed', 'promotion_eligible',
                    'official_replica_claim'):
            self.assertFalse(safety[key], key)
        for key in ('orders', 'real_capital', 'methodology_changes'):
            self.assertEqual(safety[key], 0, key)

    def test_an_implemented_status_is_backed_by_a_real_implementation(self):
        """The status may only claim implementation once the code exists.

        This began as an assertion that nothing was implemented yet, which was
        the right guard while the premises were frozen and no engine existed.
        Now that one does, the same intent is served by refusing a status that
        claims more than the tree contains, in either direction.
        """
        from pathlib import Path

        status = self.engine['status']
        if status == 'PREREGISTERED_NOT_YET_IMPLEMENTED':
            self.assertIn('NO_IMPLEMENTATION_NO_RESULT', self.engine['decision'])
            self.assertNotIn('implementation', self.engine)
            return
        self.assertEqual(status, 'IMPLEMENTED_PROSPECTIVE_COLLECTION')
        implementation = self.engine['implementation']
        for key in ('tool', 'tests'):
            self.assertTrue(Path(implementation[key]).is_file(),
                            f"{key} {implementation[key]} does not exist")
        self.assertNotIn('NO_IMPLEMENTATION', self.engine['decision'])

    def test_an_implemented_contract_still_promises_no_result(self):
        # Implementation is not evidence. Nothing here may claim a result, and
        # the anchor stays null until a production run establishes it.
        self.assertFalse(self.engine['safety']['promotion_eligible'])
        self.assertEqual(self.engine['evidence']['min_observations'], 60)
        self.assertTrue(self.engine['anchor']['backdating_prohibited'])
        self.assertIsNone(self.engine['anchor']['anchor_date'])


if __name__ == '__main__':
    unittest.main()
