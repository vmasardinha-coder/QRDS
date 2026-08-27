#!/usr/bin/env python3
from __future__ import annotations

import copy
import hashlib
import json
import math
from pathlib import Path
from typing import Any

VOLATILE_SOURCE_KEYS = {"member_sha256", "v2a_zip_sha256"}
VOLATILE_TOP_LEVEL_KEYS = {"snapshot_sha256", "scientific_identity_sha256", "identity_scheme"}


class MomentumIdentityConflict(RuntimeError):
    pass


def _norm_number(x: Any) -> Any:
    if isinstance(x, bool) or x is None:
        return x
    if isinstance(x, int):
        return x
    if isinstance(x, float):
        if not math.isfinite(x):
            raise ValueError("non-finite numeric value forbidden in Momentum identity")
        return 0.0 if x == 0.0 else x
    return x


def _normalize(value: Any, path: tuple[str, ...] = ()) -> Any:
    value = _norm_number(value)
    if isinstance(value, dict):
        out = {}
        for k in sorted(value):
            if not path and k in VOLATILE_TOP_LEVEL_KEYS:
                continue
            if path == ("source",) and k in VOLATILE_SOURCE_KEYS:
                continue
            out[k] = _normalize(value[k], path + (k,))
        return out
    if isinstance(value, list):
        rows = [_normalize(x, path + ("[]",)) for x in value]
        # Row order is representational. Scientific rank remains explicit in
        # rank_m1/rank_m2 and therefore remains identity-bearing.
        if path in (("m1", "rows"), ("m2", "rows")):
            return sorted(rows, key=lambda x: (str(x.get("asset", "")), json.dumps(x, sort_keys=True, separators=(",", ":"))))
        return rows
    return value


def scientific_identity_payload(payload: dict) -> dict:
    """Deterministic, cutoff-causal projection used for identity comparison.

    Raw archive/member hashes remain persisted for audit but are deliberately
    excluded from scientific identity: they cover container/file bytes beyond
    the requested historical cutoff and can change after that cutoff. The
    cutoff-filtered source row count/member identifier, full M1/M2 outputs,
    explicit ranks, summaries and safety contract remain identity-bearing.
    """
    if not isinstance(payload, dict):
        raise TypeError("Momentum payload must be a dict")
    required = {"schema", "cutoff", "classification", "source", "m1", "m2", "safety"}
    missing = sorted(required - payload.keys())
    if missing:
        raise ValueError(f"Momentum payload missing identity fields: {missing}")
    return _normalize(copy.deepcopy(payload))


def canonical_bytes(payload: dict) -> bytes:
    body = scientific_identity_payload(payload)
    return (json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")


def scientific_sha256(payload: dict) -> str:
    return hashlib.sha256(canonical_bytes(payload)).hexdigest()


def compare_scientific_identity(existing: dict, candidate: dict) -> tuple[bool, dict]:
    a = scientific_identity_payload(existing)
    b = scientific_identity_payload(candidate)
    if a == b:
        return True, {"status": "IDENTICAL_SCIENTIFIC_IDENTITY", "differences": []}

    diffs: list[dict] = []

    def walk(x: Any, y: Any, path: str = "$") -> None:
        if len(diffs) >= 50:
            return
        if type(x) is not type(y):
            diffs.append({"path": path, "existing": x, "candidate": y, "reason": "TYPE"})
            return
        if isinstance(x, dict):
            for k in sorted(set(x) | set(y)):
                p = f"{path}.{k}"
                if k not in x:
                    diffs.append({"path": p, "existing": "<MISSING>", "candidate": y[k], "reason": "MISSING_EXISTING"})
                elif k not in y:
                    diffs.append({"path": p, "existing": x[k], "candidate": "<MISSING>", "reason": "MISSING_CANDIDATE"})
                else:
                    walk(x[k], y[k], p)
                if len(diffs) >= 50:
                    return
        elif isinstance(x, list):
            if len(x) != len(y):
                diffs.append({"path": path, "existing": len(x), "candidate": len(y), "reason": "LENGTH"})
            for i, (xi, yi) in enumerate(zip(x, y)):
                walk(xi, yi, f"{path}[{i}]")
                if len(diffs) >= 50:
                    return
        elif x != y:
            diffs.append({"path": path, "existing": x, "candidate": y, "reason": "VALUE"})

    walk(a, b)
    return False, {"status": "SCIENTIFIC_IDENTITY_MISMATCH", "differences": diffs}


def load_strict_predecessor(ledger_dir: Path, cutoff: str) -> dict | None:
    """Load greatest snapshot cutoff strictly less than cutoff.

    The target cutoff itself is never its own predecessor. Any future snapshot
    makes reconstruction non-monotonic and fails closed.
    """
    predecessors: list[tuple[str, dict]] = []
    for p in sorted(ledger_dir.glob("*.json")):
        if p.name == "STATUS.json":
            continue
        d = json.loads(p.read_text(encoding="utf-8"))
        c = str(d.get("cutoff", ""))
        if not c:
            raise MomentumIdentityConflict(f"ledger snapshot without cutoff: {p.name}")
        if c > cutoff:
            raise MomentumIdentityConflict("non-monotonic cutoff forbidden")
        if c < cutoff:
            predecessors.append((c, d))
    return max(predecessors, key=lambda x: x[0])[1] if predecessors else None


def resolve_existing_snapshot(existing: dict, candidate: dict) -> dict:
    """Resolve a duplicate cutoff without mutating the append-only anchor.

    Equal cutoff-causal scientific content is an idempotent no-op and retains
    the original persisted snapshot hash. Any scientific difference is a hard
    conflict, irrespective of raw archive provenance.
    """
    if existing.get("cutoff") != candidate.get("cutoff"):
        raise MomentumIdentityConflict("duplicate resolver cutoff mismatch")
    same, detail = compare_scientific_identity(existing, candidate)
    if not same:
        raise MomentumIdentityConflict(json.dumps(detail, sort_keys=True, separators=(",", ":")))
    anchor = existing.get("snapshot_sha256")
    if not isinstance(anchor, str) or len(anchor) != 64:
        raise MomentumIdentityConflict("existing append-only snapshot has invalid anchor hash")
    return {
        "status": "ALREADY_RECORDED",
        "result": "IDEMPOTENT_SUCCESS",
        "snapshot_sha256": anchor,
        "scientific_identity_sha256": scientific_sha256(candidate),
        "raw_provenance_changed": existing.get("source", {}) != candidate.get("source", {}),
    }
