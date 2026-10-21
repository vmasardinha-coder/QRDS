#!/usr/bin/env python3
"""Validate a separately authorized, frozen-scope research dependency release."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RELEASE_AUTHORITY = ROOT / "artifacts/gate_btc_2/post_review_release_20261020/SYSTEM12_RESEARCH_RELEASE.json"
RELEASE_SEMANTIC_SHA256 = "cde3be3f5be425c374eba062faa2a9e30eccff6f88cb74e8417b6aa74780fc25"
REVIEW_SEMANTIC_SHA256 = "00ae74518d9e391c90d7cf0cff7ac59a2004c5f3d79f7ccc360ff8032df56a12"


def digest(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(",", ":"),
                                     allow_nan=False).encode()).hexdigest()


def retain_post_review_release(result, contract, review, release):
    out = {**result, "post_review_release_status": "NOT_PROVIDED",
        "system12_complete": False, "system13_dependency_released": False,
        "system12_completion_authorized": False, "system13_release_authorized": False}
    if release is None:
        return out
    try:
        effect = release["research_effect"]
        valid = (
            digest(release) == RELEASE_SEMANTIC_SHA256
            and release["schema"] == "gate_btc.2_0.system12_post_review_research_release.v1"
            and release["authorized"] is True
            and release["subject_contract_semantic_sha256"] == digest(contract)
            and release["adjudication_semantic_sha256"] == digest(review) == REVIEW_SEMANTIC_SHA256
            and release["bindings"] == contract["bindings"] == review["subjects"]["bindings"]
            and release["scope"] == contract["scope"] == review["scope"]
            and review["decision"] == "PASS"
            and result["adjudication_receipt_status"] == "VERIFIED_SEPARATE_AGENT_ADJUDICATION"
            and result["independent_adjudication_executed"] is True
            and result["replication_continuity_status"] == "VERIFIED_FROZEN_IMPLEMENTATION_PARITY_RECEIPT"
            and all(effect[k] is True for k in ("system12_complete",
                "system13_dependency_released", "research_only", "shadow_only"))
            and all(effect[k] is False for k in ("engine_feed", "automatic_promotion",
                "economic_claim_authorized", "system13_complete"))
            and all(type(effect[k]) is int and effect[k] == 0
                for k in ("scientific_credit", "orders", "real_capital_brl"))
        )
    except (KeyError, TypeError, ValueError):
        valid = False
    if not valid:
        return {**out, "post_review_release_status": "INVALID",
                "status": "BLOCKED_INVALID_POST_REVIEW_RELEASE",
                "system12_complete": False, "system13_dependency_released": False,
                "system12_completion_authorized": False, "system13_release_authorized": False,
                "next_action": "VERIFY_SEPARATE_RELEASE_WITHOUT_CHANGING_FROZEN_SUBJECTS"}
    out.update(post_review_release_status="VERIFIED_FROZEN_SCOPE_RESEARCH_RELEASE",
        post_review_release_semantic_sha256=digest(release),
        post_review_release_scope=release["scope"],
        system12_completion_authorized=True, system13_release_authorized=True,
        system13_complete=False, economic_claim_authorized=False,
        research_only=True, shadow_only=True, engine_feed=False, automatic_promotion=False,
        scientific_credit=0, orders=0, real_capital_brl=0)
    if result.get("upstream_system11_ready") is True:
        out.update(status="SYSTEM12_FROZEN_PARITY_COMPLETE_SYSTEM13_RESEARCH_DEPENDENCY_RELEASED",
            system12_complete=True, system13_dependency_released=True,
            next_action="BIND_QRDS_GOVERNED_SYSTEM13_PANEL_BEFORE_INTEGRATED_QLIB_RESEARCH")
    return out
