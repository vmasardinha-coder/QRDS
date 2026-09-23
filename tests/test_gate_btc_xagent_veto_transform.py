import unittest

from tools.gate_btc_factory.xagent_veto_transform import (
    aggregate_assessor_states,
    aggregate_named_assessors,
)


class TestXagentVetoTransform(unittest.TestCase):
    def test_all_allow(self):
        r = aggregate_assessor_states(["ALLOW", "ALLOW"])
        self.assertEqual(r.aggregate_decision, "ALLOW")
        self.assertEqual(r.allow_count, 2)
        self.assertEqual(r.veto_count, 0)
        self.assertEqual(r.unavailable_count, 0)
        self.assertEqual(r.allow_fraction, 1.0)

    def test_any_veto_has_priority(self):
        r = aggregate_assessor_states(["ALLOW", "ABSTAIN_UNAVAILABLE", "VETO"])
        self.assertEqual(r.aggregate_decision, "VETO")
        self.assertEqual(r.veto_count, 1)
        self.assertEqual(r.unavailable_count, 1)

    def test_unavailable_is_not_neutral(self):
        r = aggregate_assessor_states(["ALLOW", "ABSTAIN_UNAVAILABLE"])
        self.assertEqual(r.aggregate_decision, "ABSTAIN")
        self.assertEqual(r.unavailable_fraction, 0.5)

    def test_empty_fails_closed(self):
        with self.assertRaises(ValueError):
            aggregate_assessor_states([])

    def test_invalid_state_fails_closed(self):
        with self.assertRaises(ValueError):
            aggregate_assessor_states(["ALLOW", "NEUTRAL"])

    def test_named_assessors_emit_no_economics_or_runtime_activation(self):
        d = aggregate_named_assessors({"risk_a": "ALLOW", "risk_b": "VETO"})
        self.assertEqual(d["aggregate_decision"], "VETO")
        self.assertEqual(d["assessor_ids"], ["risk_a", "risk_b"])
        self.assertIsNone(d["economic_direction"])
        self.assertIsNone(d["position_size_mapping"])
        self.assertIsNone(d["return_horizon"])
        self.assertFalse(d["economic_claim"])
        self.assertFalse(d["promotion_authority"])
        self.assertFalse(d["engine_feed"])
        self.assertEqual(d["orders"], 0)
        self.assertEqual(d["real_capital"], 0)
        self.assertFalse(d["runtime_activation"])
        self.assertTrue(d["assessor_binding_required"])


if __name__ == "__main__":
    unittest.main()
