import json
import re
from pathlib import Path

MANIFEST = Path(__file__).with_name("hypothesis_seed_manifest.json")
REQUIRED_TOP = {"schema_version", "generated_utc", "source_repository", "source_branch", "policy", "candidates"}
REQUIRED_CANDIDATE = {
    "candidate_id", "source_file", "source_sha", "source_url", "candidate_family",
    "hypothesis", "qrds_role", "alpha_imported", "notable_mechanics", "status"
}
FORBIDDEN_PERFORMANCE_KEYS = {
    "profit", "profit_pct", "return", "return_pct", "sharpe", "sortino",
    "win_rate", "max_drawdown", "expectancy", "profit_factor"
}
SHA40 = re.compile(r"^[0-9a-f]{40}$")
ID = re.compile(r"^FT-HYP-[0-9]{3}$")


def fail(message: str) -> None:
    raise SystemExit(f"FAIL: {message}")


data = json.loads(MANIFEST.read_text(encoding="utf-8"))
missing = REQUIRED_TOP - set(data)
if missing:
    fail(f"missing top-level fields: {sorted(missing)}")

policy = data["policy"]
for flag in ("RESEARCH_ONLY", "SHADOW_ONLY", "require_independent_qrds_validation"):
    if policy.get(flag) is not True:
        fail(f"policy.{flag} must be true")
if policy.get("import_external_performance_claims") is not False:
    fail("external performance claims must remain disabled")
if policy.get("auto_promote_to_qrds_family") is not False:
    fail("automatic promotion must remain disabled")

candidates = data["candidates"]
if not candidates:
    fail("at least one candidate is required")

seen_ids = set()
seen_families = set()
for index, candidate in enumerate(candidates):
    missing = REQUIRED_CANDIDATE - set(candidate)
    if missing:
        fail(f"candidate[{index}] missing fields: {sorted(missing)}")
    cid = candidate["candidate_id"]
    if not ID.match(cid):
        fail(f"invalid candidate_id: {cid}")
    if cid in seen_ids:
        fail(f"duplicate candidate_id: {cid}")
    seen_ids.add(cid)
    family = candidate["candidate_family"]
    if family in seen_families:
        fail(f"duplicate candidate_family: {family}")
    seen_families.add(family)
    if not SHA40.match(candidate["source_sha"]):
        fail(f"invalid source SHA for {cid}")
    if candidate["status"] != "candidate_only":
        fail(f"{cid} must remain candidate_only until QRDS validation completes")
    if candidate["alpha_imported"] is not False:
        fail(f"{cid} cannot import external alpha claims")
    forbidden = FORBIDDEN_PERFORMANCE_KEYS & set(candidate)
    if forbidden:
        fail(f"{cid} contains forbidden external performance fields: {sorted(forbidden)}")
    if not candidate["notable_mechanics"]:
        fail(f"{cid} must identify concrete mechanics")

print(f"PASS: {len(candidates)} candidate families validated")
for candidate in candidates:
    print(f"- {candidate['candidate_id']}: {candidate['candidate_family']} [{candidate['qrds_role']}]")
