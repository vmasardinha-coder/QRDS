import copy
import unittest

from tools.gate_btc_2_microstructure_shadow_contract import load_json
from tools.gate_btc_2_stage9_source_preregistration import DEFAULT_CONTRACT, DEFAULT_PREREG, validate


class Stage9SourcePreregistrationTests(unittest.TestCase):
    def setUp(self):
        self.contract = load_json(DEFAULT_CONTRACT)
        self.prereg = load_json(DEFAULT_PREREG)

    def test_canonical_preregistration_passes(self):
        self.assertEqual(validate(self.prereg, self.contract), [])

    def test_contract_drift_fails_closed(self):
        mutated = copy.deepcopy(self.prereg)
        mutated["frozen_contract_sha256"] = "0" * 64
        self.assertIn("CONTRACT_BINDING_MISMATCH", validate(mutated, self.contract))

    def test_credit_or_capture_before_admission_fails_closed(self):
        mutated = copy.deepcopy(self.prereg)
        mutated["capture_boundary"]["source_admitted"] = True
        mutated["capture_boundary"]["capture_started"] = True
        self.assertIn("CAPTURE_BOUNDARY_INVALID", validate(mutated, self.contract))

    def test_frozen_dimensions_cannot_change(self):
        mutated = copy.deepcopy(self.prereg)
        mutated["methodology_changes"] = 1
        self.assertIn("FROZEN_DIMENSION_CHANGED", validate(mutated, self.contract))

    def test_required_roles_cannot_change(self):
        mutated = copy.deepcopy(self.prereg)
        mutated["required_source_roles"] = ["FUNDING"]
        self.assertIn("ROLE_BINDING_MISMATCH", validate(mutated, self.contract))


if __name__ == "__main__":
    unittest.main()
