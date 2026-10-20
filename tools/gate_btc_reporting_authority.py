"""Resolve reporting authorities without touching any scientific ledger."""
import json
import re
import hashlib
from pathlib import Path


def active_status_path(ledger_root: Path, filename: str = "STATUS.json") -> Path:
    pointer = ledger_root / "ACTIVE_EPOCH.json"
    if not pointer.is_file():
        return ledger_root / filename
    obj = json.loads(pointer.read_text(encoding="utf-8-sig"))
    relative = obj.get("relative_path")
    if not isinstance(relative, str) or not re.fullmatch(r"epochs/[A-Za-z0-9_-]+", relative):
        raise ValueError("INVALID_REPORTING_ACTIVE_EPOCH_PATH")
    target = ledger_root / relative / filename
    if not target.resolve().is_relative_to(ledger_root.resolve()):
        raise ValueError("REPORTING_ACTIVE_EPOCH_ESCAPES_LEDGER")
    # Once an epoch is selected, missing evidence must never fall back to legacy.
    return target


def h1_status_path(ledger_root: Path) -> Path:
    """Canonical checkpoint and structural collection have separate clocks."""
    canonical = ledger_root / "CANONICAL_STATUS.json"
    return canonical if canonical.is_file() else ledger_root / "STATUS.json"


def m3_status_path(ledger_root: Path) -> Path:
    """M3 declares its active epoch in the root status, not ACTIVE_EPOCH.json."""
    root_status = ledger_root / "STATUS.json"
    if not root_status.is_file():
        return root_status
    obj = json.loads(root_status.read_text(encoding="utf-8-sig"))
    if "active_epoch" not in obj:
        return root_status
    relative = obj["active_epoch"]
    if not isinstance(relative, str) or not re.fullmatch(r"epochs/[A-Za-z0-9_-]+", relative):
        raise ValueError("INVALID_M3_REPORTING_ACTIVE_EPOCH_PATH")
    target = ledger_root / relative / "STATUS.json"
    if not target.resolve().is_relative_to(ledger_root.resolve()):
        raise ValueError("M3_REPORTING_ACTIVE_EPOCH_ESCAPES_LEDGER")
    # Missing selected evidence stays missing; never use the mixed legacy total.
    return target


def closed_v12_status(raw: dict, closure_path: Path | None = None) -> dict:
    """Project a main-branch terminal decision without rewriting the old ledger."""
    path = closure_path or Path(__file__).resolve().parents[1] / "migration/reporting/delta_v12_engine_closure.json"
    if not path.is_file():
        return raw
    closure = json.loads(path.read_text())
    if (closure.get("closes") != "DELTA_V12_ENGINE" or
            closure.get("status") != "CLOSED_NO_FURTHER_OBSERVATIONS_POSSIBLE"):
        raise ValueError("INVALID_V12_CLOSURE_AUTHORITY")
    terminal = closure["terminal_state"]
    if raw.get("observed_days") is not None and raw["observed_days"] != terminal["observed_days"]:
        raise ValueError("V12_COUNTER_DIVERGES_FROM_TERMINAL_AUTHORITY")
    return {**raw, "raw_status_preserved": raw.get("status"), "status": closure["status"],
            "reporting_disposition": "DESCRIPTIVE_ONLY_AND_NOW_FROZEN",
            "closure_source": "migration/reporting/delta_v12_engine_closure.json",
            "closure_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "closure_date": closure["closed_on"], "promotion_allowed": False,
            "scientific_credit": 0, "observed_days": terminal["observed_days"]}


def system12_summary(root: Path) -> dict:
    """Observability of implementation parity only; never an adjudication."""
    paths = {name: root / filename for name, filename in {
        "readiness": "READINESS.json", "contract": "IMPLEMENTATION_REPLICATION_CONTRACT.json",
        "implementation": "IMPLEMENTATION_REPLICATION.json"}.items()}
    data = {k: json.loads(p.read_text()) if p.is_file() else None for k, p in paths.items()}
    result = {"reporting_only": True, "scientific_authority": False, "scientific_credit": 0,
              "system12_complete": False, "system13_dependency_released": False,
              "independent_adjudication_executed": False,
              "readiness_status": (data["readiness"] or {}).get("status"),
              "source": "gate_btc_2/system12/IMPLEMENTATION_REPLICATION.json",
              "source_sha256": {k: hashlib.sha256(p.read_bytes()).hexdigest()
                                for k, p in paths.items() if p.is_file()}}
    contract, report = data["contract"], data["implementation"]
    if not report:
        return {**result, "status": "STRUCTURAL_READINESS_ONLY_NO_IMPLEMENTATION_RECEIPT",
                "implementation_replication_pass": False}
    required_checks = {"all_events_compared", "dataset_gate", "deterministic_independent_executor",
                       "event_parity", "minimum_executions", "reference_semantic_digest",
                       "scenario_count", "scenario_parity", "size_monotonicity"}
    contract_hash = hashlib.sha256(json.dumps(contract, sort_keys=True, separators=(",", ":"),
                                            allow_nan=False).encode()).hexdigest() if contract else None
    valid = bool(contract and contract.get("schema") == "gate_btc.2_0.system12_implementation_replication_contract.v1"
        and report.get("schema") == "gate_btc.2_0.system12_implementation_replication.v1"
        and report.get("contract_sha256") == contract_hash
        and report.get("bindings") == contract.get("bindings")
        and report.get("status") == "PASS_IMPLEMENTATION_PARITY_PENDING_INDEPENDENT_ADJUDICATION"
        and report.get("implementation_replication_pass") is True
        and report.get("independent_replication_executed") is True
        and report.get("event_mismatches") == 0 and report.get("scenario_mismatches") == []
        and report.get("scenario_count") == contract.get("required_scenario_count") == 300
        and all(report.get("checks", {}).get(k) is True for k in required_checks)
        and report.get("system12_complete") is False and report.get("system13_dependency_released") is False
        and report.get("independent_adjudication_executed") is False
        and report.get("scientific_credit") == 0 and report.get("orders") == 0
        and report.get("real_capital_brl") == 0 and report.get("engine_feed") is False)
    summary = {**result, "status": "PASS_IMPLEMENTATION_PARITY_PENDING_INDEPENDENT_ADJUDICATION" if valid
            else "BLOCKED_IMPLEMENTATION_RECEIPT_BINDING_OR_BOUNDARY_MISMATCH",
            "implementation_replication_pass": valid, "compared_events": report.get("compared_events"),
            "scenario_count": report.get("scenario_count"), "workflow_run_url": report.get("workflow_run_url"),
            "contract_sha256": report.get("contract_sha256"),
            "next_action": "INDEPENDENT_ADJUDICATION_OF_HASH_BOUND_IMPLEMENTATION_REPLICATION"}



    return _system12_adjudication_summary(summary, data["readiness"], contract)


def _system12_adjudication_summary(summary, readiness, contract):
    """Project the pinned existing decision; do not adjudicate or release it."""
    if not summary["implementation_replication_pass"]:
        return summary
    readiness = readiness or {}
    authority = Path(__file__).resolve().parents[1] / "artifacts/gate_btc_2"
    review_path = authority / "separate_reviews_20261019/SISTEMA12_PARECER.json"
    contract_path = authority / "SYSTEM12_IMPLEMENTATION_REPLICATION_V1_20261010.json"
    digest = lambda obj: hashlib.sha256(json.dumps(
        obj, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()
    expected = "00ae74518d9e391c90d7cf0cff7ac59a2004c5f3d79f7ccc360ff8032df56a12"
    try:
        from .gate_btc_system12_post_review_release import RELEASE_AUTHORITY, retain_post_review_release
    except ImportError:
        from gate_btc_system12_post_review_release import RELEASE_AUTHORITY, retain_post_review_release
    released = None
    try:
        review = json.loads(review_path.read_text(encoding="utf-8"))
        if RELEASE_AUTHORITY.is_file():
            release = json.loads(RELEASE_AUTHORITY.read_text(encoding="utf-8"))
            candidate = retain_post_review_release(readiness, contract, review, release)
            keys = ("system12_complete", "system13_dependency_released",
                    "system12_completion_authorized", "system13_release_authorized")
            if (candidate.get("post_review_release_status") == "VERIFIED_FROZEN_SCOPE_RESEARCH_RELEASE"
                    and readiness.get("post_review_release_semantic_sha256") == candidate.get("post_review_release_semantic_sha256")
                    and readiness.get("status") == candidate.get("status")
                    and all(readiness.get(k) is candidate.get(k) for k in keys)):
                released = candidate
        frozen = json.loads(contract_path.read_text(encoding="utf-8"))
        valid = (
            digest(review) == expected
            and contract == frozen
            and review["contract_semantic_sha256"] == digest(contract)
            and review["subjects"]["bindings"] == contract["bindings"]
            and readiness["schema"] == "gate_btc.2_0.system12_readiness.v1"
            and readiness["replication_continuity_status"] == "VERIFIED_FROZEN_IMPLEMENTATION_PARITY_RECEIPT"
            and readiness["frozen_replication_contract_sha256"] == digest(contract)
            and readiness["frozen_replication_bindings"] == contract["bindings"]
            and readiness["adjudicated_bindings"] == contract["bindings"]
            and readiness["adjudication_receipt_status"] == "VERIFIED_SEPARATE_AGENT_ADJUDICATION"
            and readiness["adjudication_receipt_semantic_sha256"] == expected
            and readiness["adjudication_scope"] == review["scope"]
            and readiness["adjudication_decision"] == review["decision"] == "PASS"
            and readiness["independent_adjudication_executed"] is True
            and (released is not None or all(readiness[k] is False for k in (
                "system12_complete", "system13_dependency_released",
                "system12_completion_authorized", "system13_release_authorized")))
            and all(readiness[k] is False for k in ("engine_feed", "automatic_promotion"))
            and all(type(readiness[k]) is int and readiness[k] == 0
                    for k in ("scientific_credit", "orders", "real_capital_brl"))
        )
    except (KeyError, TypeError, ValueError, OSError):
        valid = False
    if not valid:
        return {**summary, "adjudication_reporting_status": "NO_VERIFIED_BOUND_READINESS"}
    out = {**summary,
        "raw_implementation_status_preserved": summary["status"],
        "source": "gate_btc_2/system12/READINESS.json",
        "source_sha256": {**summary["source_sha256"],
            "pinned_adjudication": hashlib.sha256(review_path.read_bytes()).hexdigest(),
            "frozen_contract_authority": hashlib.sha256(contract_path.read_bytes()).hexdigest()},
        "adjudication_reporting_status": "VERIFIED_PINNED_READINESS_PROJECTION",
        "adjudication_receipt_status": readiness["adjudication_receipt_status"],
        "adjudication_receipt_semantic_sha256": expected,
        "adjudication_scope": review["scope"],
        "adjudication_decision": "PASS",
        "independent_adjudication_executed": True}
    if released is not None and released["system13_dependency_released"] is True:
        keys = ("status", "next_action", "system12_complete", "system13_dependency_released",
                "system12_completion_authorized", "system13_release_authorized",
                "post_review_release_status", "post_review_release_semantic_sha256",
                "post_review_release_scope", "system13_complete", "economic_claim_authorized")
        out.update({k: released[k] for k in keys})
        out["source_sha256"]["post_review_release"] = hashlib.sha256(RELEASE_AUTHORITY.read_bytes()).hexdigest()
        return out
    if (readiness.get("upstream_system11_ready") is True
            and readiness.get("status") == "FROZEN_PARITY_ADJUDICATED_PENDING_FORMAL_RELEASE"):
        out.update(status=readiness["status"],
            next_action="BIND_EXPLICIT_POST_REVIEW_RELEASE_WITHOUT_REFREEZE")
    else:
        out.update(status="BLOCKED_CURRENT_READINESS_WITH_FROZEN_ADJUDICATION_RETAINED",
            next_action="VERIFY_CURRENT_READINESS_WITHOUT_REOPENING_FROZEN_ADJUDICATION")
    return out
