#!/usr/bin/env python3
"""Run staged direct-USD PIT recovery with evidence-backed continuities.

Research-only wrapper layered on the CC-first staging runner. It keeps the
trade-level Bybit archive deferred and adds only primary-source documented
identity continuities. No strategy, factor, weight, price, return, execution,
or frozen-engine rule is changed.
"""
from __future__ import annotations

import gate_btc_survivorship_definitive_cc_first_runner as staged

EVIDENCE_BACKED_CONTINUITIES = {
    "THETA": {"theta", "thetanetwork"},
    "HBAR": {"hedera", "hederahashgraph"},
    "FET": {"fetchai", "artificialsuperintelligencealliance"},
    "INJ": {"injective", "injectiveprotocol"},
    "SNX": {"synthetix", "synthetixnetworktoken"},
    "SXP": {"sxp", "solar", "swipe"},
}

# Intentionally absent from EVIDENCE_BACKED_CONTINUITIES:
# - DYDX / ethDYDX: documented bridge/conversion across chains/tokens.
# - KNC / KNCL: documented old-contract to new-contract token migration.
# The PIT identity gate must keep both cases fail-closed rather than treating
# them as display-name-only continuity.


def apply_continuity_evidence() -> None:
    for symbol, aliases in EVIDENCE_BACKED_CONTINUITIES.items():
        staged.runner.definitive.KNOWN_CONTINUITIES.setdefault(symbol, set()).update(aliases)


def main() -> int:
    apply_continuity_evidence()
    return staged.main()


if __name__ == "__main__":
    raise SystemExit(main())
