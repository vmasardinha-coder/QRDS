#!/usr/bin/env python3
"""Run the definitive PIT study with primary-source continuity evidence enabled.

Research-only wrapper. It changes identity continuity evidence only; it does not
change selection rules, factors, weights, prices, returns, execution, or engine
state. See migration/GATE_BTC_IDENTITY_CONTINUITY_EVIDENCE.md.
"""
from __future__ import annotations

import gate_btc_survivorship_definitive_runner as runner

EVIDENCE_BACKED_CONTINUITIES = {
    "THETA": {"theta", "thetanetwork"},
    "HBAR": {"hedera", "hederahashgraph"},
    "FET": {"fetchai", "artificialsuperintelligencealliance"},
    "INJ": {"injective", "injectiveprotocol"},
}


def apply_continuity_evidence() -> None:
    for symbol, aliases in EVIDENCE_BACKED_CONTINUITIES.items():
        runner.definitive.KNOWN_CONTINUITIES.setdefault(symbol, set()).update(aliases)


def main() -> int:
    apply_continuity_evidence()
    return runner.main()


if __name__ == "__main__":
    raise SystemExit(main())
