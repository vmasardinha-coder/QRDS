from __future__ import annotations

import unittest

from tools.gate_btc_2_microstructure_shadow_manifest import SPECS
from tools.gate_btc_2_prospective_counter_bridge import STAGE9_RAW_ROLES


class Stage9RoleBindingTests(unittest.TestCase):
    def test_counter_roles_exactly_match_frozen_manifest_roles(self):
        self.assertEqual(tuple(SPECS.keys()), STAGE9_RAW_ROLES)
        self.assertEqual(
            STAGE9_RAW_ROLES,
            ("FUNDING", "OPEN_INTEREST", "PERP_VOLUME", "SPOT_VOLUME"),
        )


if __name__ == "__main__":
    unittest.main()
