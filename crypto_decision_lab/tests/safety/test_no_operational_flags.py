"""
Verify that operational_decision_allowed is False in all contexts
produced by the research pipeline entry points.
"""

import pytest
from crypto_decision_lab.safety.gates import build_safe_context


class TestNoOperationalFlags:
    def test_default_safe_context_has_operational_false(self):
        ctx = build_safe_context()
        assert ctx["operational_decision_allowed"] is False

    def test_cannot_set_operational_true(self):
        with pytest.raises(AssertionError):
            build_safe_context(operational_decision_allowed=True)

    def test_cannot_set_orders_generated_true(self):
        with pytest.raises(AssertionError):
            build_safe_context(orders_generated=True)

    def test_cannot_set_real_capital_true(self):
        with pytest.raises(AssertionError):
            build_safe_context(real_capital_used=True)

    def test_app_mode_is_research_only(self):
        from crypto_decision_lab import APP_MODE
        assert APP_MODE == "INTERACTIVE_RESEARCH_ONLY"
