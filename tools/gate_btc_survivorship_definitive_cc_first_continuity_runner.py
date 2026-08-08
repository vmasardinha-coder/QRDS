#!/usr/bin/env python3
"""Run staged direct-USD PIT recovery with evidence-backed continuities.

Research-only wrapper layered on the CC-first staging runner. It keeps the
trade-level Bybit archive deferred and adds only primary-source documented
identity continuities and classification corrections. No strategy, factor,
weight, price, return, execution, or frozen-engine rule is changed.
"""
from __future__ import annotations

import re

import gate_btc_survivorship_definitive_cc_first_runner as staged

EVIDENCE_BACKED_CONTINUITIES = {
    "THETA": {"theta", "thetanetwork"},
    "HBAR": {"hedera", "hederahashgraph"},
    "FET": {"fetchai", "artificialsuperintelligencealliance"},
    "INJ": {"injective", "injectiveprotocol"},
    "SNX": {"synthetix", "synthetixnetworktoken"},
    "SXP": {"sxp", "solar", "swipe"},
}

# PIT-only single-character ticker exceptions backed by primary project evidence.
# This does not modify the canonical V2A standard_ticker rule and does not admit
# any other one-character symbol.
EVIDENCE_BACKED_SINGLE_CHAR = {
    "W": {"name": "wormhole", "slug": "wormhole"},
    "T": {"name": "threshold", "slug": "threshold"},
}

# Stablecoin identities missing from the frozen symbol/name filter because CMC
# now exposes historical markets under later/current labels. These exact
# symbol+name pairs are excluded from the directional PIT universe; the
# canonical V2A stable list is not modified.
EVIDENCE_BACKED_PIT_STABLES = {
    "XTN": {"neutrinousd"},
    "FEI": {"feiusd"},
}

# Intentionally absent from same-token continuity:
# - DYDX / ethDYDX: documented bridge/conversion across chains/tokens.
# - KNC / KNCL: documented old-contract to new-contract token migration.
# - BORG / CHSB and BTTOLD / BTT: token migrations/redenominations are not
#   admitted by this continuity layer.

_ORIGINAL_IDENTITY_AUDIT = staged.runner._cascade_identity_audit
_ORIGINAL_STABLE_SYMBOL = staged.runner.definitive.stable_symbol


def _norm(value: object) -> str:
    return re.sub(r"[^a-z0-9]", "", str(value or "").lower())


def _single_char_evidence_ok(symbol: str, names: list[str], slugs: list[str]) -> bool:
    evidence = EVIDENCE_BACKED_SINGLE_CHAR.get(str(symbol))
    if evidence is None:
        return False
    name_norms = {_norm(v) for v in names if _norm(v)}
    slug_norms = {_norm(v) for v in slugs if _norm(v)}
    return name_norms == {evidence["name"]} and slug_norms == {evidence["slug"]}


def _stable_symbol_with_evidence(v2a, symbol: str, name: str) -> bool:
    if _ORIGINAL_STABLE_SYMBOL(v2a, symbol, name):
        return True
    allowed_names = EVIDENCE_BACKED_PIT_STABLES.get(str(symbol), set())
    return bool(allowed_names and _norm(name) in allowed_names)


def _identity_audit_with_single_char_evidence(snapshots, coinlist, v2a):
    identity = _ORIGINAL_IDENTITY_AUDIT(snapshots, coinlist, v2a)
    for symbol in EVIDENCE_BACKED_SINGLE_CHAR:
        mask = identity["symbol"].astype(str) == symbol
        if not bool(mask.any()):
            continue
        names = sorted(set(snapshots.loc[snapshots["symbol"].astype(str) == symbol, "name"].astype(str)))
        slugs = []
        if "cmc_slug" in snapshots.columns:
            slugs = sorted({str(v) for v in snapshots.loc[snapshots["symbol"].astype(str) == symbol, "cmc_slug"].dropna()})
        if _single_char_evidence_ok(symbol, names, slugs):
            identity.loc[mask, "exchange_identity_ok"] = True
            identity.loc[mask, "identity_confidence"] = "CURATED_PIT_SINGLE_CHAR"
    return identity


def apply_continuity_evidence() -> None:
    for symbol, aliases in EVIDENCE_BACKED_CONTINUITIES.items():
        staged.runner.definitive.KNOWN_CONTINUITIES.setdefault(symbol, set()).update(aliases)
    staged.runner._cascade_identity_audit = _identity_audit_with_single_char_evidence
    staged.runner.definitive.stable_symbol = _stable_symbol_with_evidence


def main() -> int:
    apply_continuity_evidence()
    return staged.main()


if __name__ == "__main__":
    raise SystemExit(main())
