import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from tools.gate_btc_2_source_admission import (
    BLOCKED,
    CURRENT_BLOCKED,
    OUTPUT_SAFETY,
    READY,
    build_current_preflight,
    build_source_admission,
    canonical_hash,
    validate_contract,
)


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "tools" / "gate_btc_2_source_admission_contract_v1.json"


def exact_json(payload: dict) -> str:
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_contract() -> dict:
    return json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))


def add_hash(payload: dict, field: str) -> dict:
    payload[field] = canonical_hash(payload)
    return payload


def schema(source_role: str, availability_mode: str) -> dict:
    columns = [
        {"name": "instrument", "type": "string", "role": "identifier"},
        {
            "name": "observation_timestamp_utc",
            "type": "string",
            "role": "observation_timestamp",
        },
    ]
    if availability_mode == "ROW_LEVEL_PROVIDER_OR_VERIFIABLE_CAPTURE":
        columns.append(
            {"name": "available_at_utc", "type": "string", "role": "available_at"}
        )
    if source_role == "OHLC":
        columns.extend(
            [
                {"name": "open", "type": "number", "role": "open"},
                {"name": "high", "type": "number", "role": "high"},
                {"name": "low", "type": "number", "role": "low"},
                {"name": "close", "type": "number", "role": "close"},
                {"name": "volume", "type": "number", "role": "volume"},
                {"name": "confirmed", "type": "boolean", "role": "confirmation"},
            ]
        )
    else:
        columns.extend(
            [
                {"name": "funding_rate", "type": "number", "role": "funding_rate"},
                {"name": "confirmed", "type": "boolean", "role": "confirmation"},
            ]
        )
    return {
        "schema": "gate_btc.2_0.tabular_dataset_schema.v1",
        "schema_id": f"gate_btc.2_0.{source_role.lower()}_fixture.v1",
        "format": "csv",
        "timezone": "UTC",
        "columns": columns,
        "primary_key": ["instrument", "observation_timestamp_utc"],
        "economic_fields": [],
        "future_known_metadata_allowed": False,
    }


def d50_status(ohlc_hash: str, funding_hash: str) -> dict:
    payload = {
        "schema": "gate_btc.d50_measurement_status.v1",
        "research_only": True,
        "shadow_only": True,
        "not_approved": True,
        "promotion_allowed": False,
        "orders_generated": 0,
        "real_capital_used": 0,
        "prospective_immutable_ledger": {
            "historical_backfill_counts_as_prospective": False,
            "mutation_performed": False,
            "source_hashes": {"ohlc": ohlc_hash, "funding": funding_hash},
        },
    }
    return add_hash(payload, "status_sha256")


def build_package(root: Path, contract: dict) -> tuple[dict, dict]:
    for directory in ("data", "schemas", "provenance"):
        (root / directory).mkdir()
    ohlc_path = root / "data" / "btc_ohlc.csv"
    ohlc_path.write_text(
        "instrument,observation_timestamp_utc,open,high,low,close,volume,confirmed\n"
        "BTCUSDT,2026-08-23T00:00:00Z,60000,60100,59900,60050,10,true\n"
        "BTCUSDT,2026-08-23T01:00:00Z,60050,60200,60000,60150,11,true\n",
        encoding="utf-8",
    )
    funding_path = root / "data" / "btc_funding.csv"
    funding_path.write_text(
        "instrument,observation_timestamp_utc,available_at_utc,funding_rate,confirmed\n"
        "BTCUSDT,2026-08-23T00:00:00Z,2026-08-23T00:00:05Z,0.0001,true\n"
        "BTCUSDT,2026-08-23T08:00:00Z,2026-08-23T08:00:05Z,-0.0002,true\n",
        encoding="utf-8",
    )
    paths = {"OHLC": ohlc_path, "FUNDING": funding_path}
    modes = {
        "OHLC": "FILE_LEVEL_CONSERVATIVE_GIT_COMMIT",
        "FUNDING": "ROW_LEVEL_PROVIDER_OR_VERIFIABLE_CAPTURE",
    }
    sources = []
    partitions = []
    for role in ("OHLC", "FUNDING"):
        source_id = f"SRC_{role}"
        schema_path = root / "schemas" / f"{role.lower()}.json"
        schema_path.write_text(exact_json(schema(role, modes[role])), encoding="utf-8")
        commit = "38de132bcac86f3c0703dd20633fa131b2650d8b"
        evidence_type = (
            "FIRST_REPOSITORY_COMMIT_TIMESTAMP"
            if role == "OHLC"
            else "PROVIDER_PUBLICATION_TIMESTAMP"
        )
        evidence_reference = commit if role == "OHLC" else "provider://funding/publication-time"
        source = {
            "source_id": source_id,
            "source_role": role,
            "provider": "Fixture Exchange",
            "venue": "FIXTURE",
            "market_type": "linear_perpetual",
            "instrument": "BTCUSDT",
            "normalized_asset": "BTC",
            "source_reference": f"immutable://fixture/{role.lower()}/2026-08-23",
            "access_class": "official_free_fixture",
            "license_status": "auditable_fixture",
            "observed_or_derived": "observed",
            "timezone": "UTC",
            "causal_availability_rule": (
                "all file rows unavailable before first repository commit"
                if role == "OHLC"
                else "row available_at_utc is provider publication timestamp"
            ),
            "immutable_reference": True,
            "availability_evidence_type": evidence_type,
            "availability_evidence_reference": evidence_reference,
            "provenance_path": f"provenance/{role.lower()}.json",
        }
        provenance = {
            "schema": "gate_btc.2_0.source_admission_provenance.v1",
            **{
                key: value
                for key, value in source.items()
                if key != "provenance_path"
            },
            "retrieved_at_utc": "2026-08-23T10:00:00Z",
            "retrieval_method": "deterministic fixture export",
            "original_filename": paths[role].name,
            "content_sha256": file_hash(paths[role]),
        }
        provenance_path = root / source["provenance_path"]
        provenance_path.write_text(exact_json(provenance), encoding="utf-8")
        source["expected_provenance_sha256"] = file_hash(provenance_path)
        sources.append(source)
        first = "2026-08-23T00:00:00Z"
        last = "2026-08-23T01:00:00Z" if role == "OHLC" else "2026-08-23T08:00:00Z"
        partitions.append(
            {
                "partition_id": f"BTC_{role}",
                "source_id": source_id,
                "source_role": role,
                "relative_path": f"data/{paths[role].name}",
                "schema_path": f"schemas/{role.lower()}.json",
                "format": "csv",
                "granularity": "hourly" if role == "OHLC" else "8h",
                "expected_sha256": file_hash(paths[role]),
                "expected_schema_sha256": file_hash(schema_path),
                "availability_mode": modes[role],
                "file_available_at_utc": (
                    "2026-08-23T10:00:00Z" if role == "OHLC" else None
                ),
                "row_count": 2,
                "first_observation_utc": first,
                "last_observation_utc": last,
                "contains_unconfirmed_rows": False,
                "recovered_historical": role == "OHLC",
            }
        )
    hashes = {item["source_role"]: item["expected_sha256"] for item in partitions}
    descriptor = {
        "schema": "gate_btc.2_0.source_admission_bundle.v1",
        "bundle_id": "GATE_BTC_2_BTC_CORE_D50_FIXTURE",
        "bundle_version": "2026-08-23.v1",
        "baseline_commit_sha": "38de132bcac86f3c0703dd20633fa131b2650d8b",
        "created_at_utc": "2026-08-23T11:00:00Z",
        "cutoff_utc": "2026-08-23T23:59:59Z",
        "assessment_at_utc": "2026-08-24T00:00:00Z",
        "contract_sha256": contract["contract_sha256"],
        "scopes": ["BTC_CORE", "D50_ECONOMIC", "D50_QUALIFIED"],
        "d50_claimed_source_hashes": hashes,
        "sources": sources,
        "partitions": partitions,
        "prospective_credit": {
            "frozen_ledger_mutations": 0,
            "historical_rows_credited": 0,
            "recovered_historical_rows_credited": 0,
            "source_admission_counter_increments": 0,
        },
        "policies": copy.deepcopy(contract["policies"]),
        "safety": copy.deepcopy(contract["safety"]),
    }
    return descriptor, d50_status(hashes["OHLC"], hashes["FUNDING"])


def current_inventory() -> dict:
    payload = {
        "schema": "gate_btc.2_0.official_evidence_inventory.v1",
        "status": "BLOCKED_NO_ADMISSIBLE_OFFICIAL_DATASET_CANDIDATE",
        "runtime_commit": "695183cbdb1310b4ec609040b78140e0ea7386ac",
        "expected_cutoff": "2026-08-23",
        "admissible_candidate_count": 0,
        "physical_evidence": [
            {
                "path": "runtime/manual_public_data/BTC_BINANCE_SPOT_1h.csv",
                "sha256": "a" * 64,
            }
        ],
        "d50": {
            "source_hashes": {"ohlc": "f" * 64, "funding": "2" * 64},
            "source_paths_present": False,
        },
        "manual_market_evidence": {
            "files": [
                {
                    "asset": "BTC",
                    "venue": "BINANCE_SPOT",
                    "path": "runtime/manual_public_data/BTC_BINANCE_SPOT_1h.csv",
                    "rows": 5000,
                    "last_observation_utc": "2026-07-03T20:00:00Z",
                },
                {
                    "asset": "BTC",
                    "venue": "HYPERLIQUID_PERP",
                    "path": "runtime/manual_public_data/BTC_HYPERLIQUID_PERP_1h.csv",
                    "rows": 5000,
                    "last_observation_utc": "2026-07-04T15:00:00Z",
                },
                {
                    "asset": "BTC",
                    "venue": "OKX_SWAP",
                    "path": "runtime/manual_public_data/BTC_OKX_SWAP_1h.csv",
                    "rows": 5000,
                    "last_observation_utc": "2026-07-04T17:00:00Z",
                },
            ]
        },
        "safety": copy.deepcopy(OUTPUT_SAFETY),
    }
    return add_hash(payload, "inventory_sha256")


class GateBTC2SourceAdmissionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.contract = load_contract()
        self.descriptor, self.status = build_package(self.root, self.contract)

    def tearDown(self):
        self.temp.cleanup()

    def build(self):
        return build_source_admission(
            self.root,
            self.descriptor,
            self.status,
            self.contract,
        )

    def test_frozen_contract_hash_and_parent_binding_are_valid(self):
        self.assertEqual(validate_contract(self.contract), [])

    def test_complete_exact_bundle_is_only_ready_for_explicit_review(self):
        payload = self.build()
        repeated = self.build()
        self.assertEqual(payload["status"], READY)
        self.assertEqual(payload["assessment_sha256"], repeated["assessment_sha256"])
        self.assertEqual(payload["source_roles_present"], ["FUNDING", "OHLC"])
        self.assertTrue(payload["explicit_review_required"])
        self.assertFalse(payload["source_admitted"])
        self.assertFalse(payload["official_dataset_sealed"])
        self.assertFalse(payload["economics_allowed"])

    def test_recovered_history_receives_zero_prospective_credit(self):
        payload = self.build()
        self.assertEqual(payload["historical_recovery"]["recovered_partition_count"], 1)
        self.assertEqual(payload["historical_recovery"]["prospective_rows_credited"], 0)
        self.assertFalse(payload["historical_recovery"]["backfill_performed"])
        self.assertEqual(payload["safety"]["prospective_rows_credited"], 0)
        self.assertEqual(payload["safety"]["ledger_mutations"], 0)

    def test_exact_data_hash_tamper_fails_closed(self):
        (self.root / "data" / "btc_ohlc.csv").write_text("tampered\n", encoding="utf-8")
        payload = self.build()
        self.assertEqual(payload["status"], BLOCKED)
        self.assertIn("PARTITION_BTC_OHLC_DATA_HASH_MISMATCH", payload["blocking_reasons"])

    def test_status_only_hash_claim_cannot_replace_exact_bytes(self):
        self.status["prospective_immutable_ledger"]["source_hashes"]["ohlc"] = "0" * 64
        self.status.pop("status_sha256")
        add_hash(self.status, "status_sha256")
        payload = self.build()
        self.assertIn("BUNDLE_D50_OHLC_STATUS_HASH_MISMATCH", payload["blocking_reasons"])

    def test_provenance_tamper_fails_closed(self):
        path = self.root / "provenance" / "ohlc.json"
        provenance = json.loads(path.read_text(encoding="utf-8"))
        provenance["provider"] = "Mutated Provider"
        path.write_text(exact_json(provenance), encoding="utf-8")
        payload = self.build()
        self.assertIn("SOURCE_SRC_OHLC_PROVENANCE_HASH_MISMATCH", payload["blocking_reasons"])
        self.assertIn(
            "SOURCE_SRC_OHLC_PROVENANCE_FIELD_MISMATCH:provider",
            payload["blocking_reasons"],
        )

    def test_git_commit_availability_is_conservative_not_provider_time(self):
        source = next(item for item in self.descriptor["sources"] if item["source_role"] == "OHLC")
        source["availability_evidence_type"] = "PROVIDER_PUBLICATION_TIMESTAMP"
        payload = self.build()
        self.assertIn("PARTITION_BTC_OHLC_GIT_AVAILABILITY_EVIDENCE_INVALID", payload["blocking_reasons"])
        self.assertIn(
            "SOURCE_SRC_OHLC_PROVENANCE_FIELD_MISMATCH:availability_evidence_type",
            payload["blocking_reasons"],
        )

    def test_row_available_after_cutoff_fails_closed(self):
        path = self.root / "data" / "btc_funding.csv"
        text = path.read_text(encoding="utf-8").replace(
            "2026-08-23T08:00:05Z", "2026-08-24T08:00:05Z"
        )
        path.write_text(text, encoding="utf-8")
        partition = next(item for item in self.descriptor["partitions"] if item["source_role"] == "FUNDING")
        partition["expected_sha256"] = file_hash(path)
        self.descriptor["d50_claimed_source_hashes"]["FUNDING"] = file_hash(path)
        self.status["prospective_immutable_ledger"]["source_hashes"]["funding"] = file_hash(path)
        self.status.pop("status_sha256")
        add_hash(self.status, "status_sha256")
        payload = self.build()
        self.assertIn("PARTITION_BTC_FUNDING_ROW_2_AVAILABLE_AFTER_CUTOFF", payload["blocking_reasons"])

    def test_missing_row_available_at_role_fails_closed(self):
        schema_path = self.root / "schemas" / "funding.json"
        payload = json.loads(schema_path.read_text(encoding="utf-8"))
        payload["columns"] = [
            item for item in payload["columns"] if item["role"] != "available_at"
        ]
        schema_path.write_text(exact_json(payload), encoding="utf-8")
        partition = next(item for item in self.descriptor["partitions"] if item["source_role"] == "FUNDING")
        partition["expected_schema_sha256"] = file_hash(schema_path)
        result = self.build()
        self.assertIn("SCHEMA_BTC_FUNDING_ROW_AVAILABLE_AT_REQUIRED", result["blocking_reasons"])

    def test_unconfirmed_ohlc_row_fails_closed(self):
        path = self.root / "data" / "btc_ohlc.csv"
        path.write_text(
            path.read_text(encoding="utf-8").replace(
                "60150,11,true", "60150,11,false"
            ),
            encoding="utf-8",
        )
        partition = next(item for item in self.descriptor["partitions"] if item["source_role"] == "OHLC")
        partition["expected_sha256"] = file_hash(path)
        self.descriptor["d50_claimed_source_hashes"]["OHLC"] = file_hash(path)
        self.status["prospective_immutable_ledger"]["source_hashes"]["ohlc"] = file_hash(path)
        self.status.pop("status_sha256")
        add_hash(self.status, "status_sha256")
        result = self.build()
        self.assertIn("PARTITION_BTC_OHLC_ROW_2_UNCONFIRMED", result["blocking_reasons"])
        self.assertIn("PARTITION_BTC_OHLC_UNCONFIRMED_DISCLOSURE_MISMATCH", result["blocking_reasons"])

    def test_partial_ohlc_without_funding_cannot_pass(self):
        self.descriptor["sources"] = [
            item for item in self.descriptor["sources"] if item["source_role"] == "OHLC"
        ]
        self.descriptor["partitions"] = [
            item for item in self.descriptor["partitions"] if item["source_role"] == "OHLC"
        ]
        payload = self.build()
        self.assertIn("BUNDLE_EXACTLY_TWO_SOURCES_REQUIRED", payload["blocking_reasons"])
        self.assertIn("BUNDLE_SOURCE_ROLE_COVERAGE_INVALID", payload["blocking_reasons"])
        self.assertFalse(payload["source_admitted"])

    def test_cross_role_market_mismatch_and_unverified_license_fail_closed(self):
        funding = next(
            item for item in self.descriptor["sources"] if item["source_role"] == "FUNDING"
        )
        funding["venue"] = "OTHER_EXCHANGE"
        funding["license_status"] = "unknown"
        payload = self.build()
        self.assertIn("BUNDLE_CROSS_ROLE_MARKET_IDENTITY_MISMATCH", payload["blocking_reasons"])
        self.assertIn("SOURCE_SRC_FUNDING_LICENSE_STATUS_INVALID", payload["blocking_reasons"])
        self.assertFalse(payload["source_admitted"])

    def test_economic_field_in_source_schema_is_forbidden(self):
        path = self.root / "schemas" / "ohlc.json"
        payload = json.loads(path.read_text(encoding="utf-8"))
        payload["economic_fields"] = ["future_return"]
        path.write_text(exact_json(payload), encoding="utf-8")
        partition = next(item for item in self.descriptor["partitions"] if item["source_role"] == "OHLC")
        partition["expected_schema_sha256"] = file_hash(path)
        result = self.build()
        self.assertIn("SCHEMA_BTC_OHLC_ECONOMIC_FIELDS_FORBIDDEN", result["blocking_reasons"])
        self.assertFalse(result["economics_allowed"])

    def test_unsafe_prospective_credit_is_rejected(self):
        self.descriptor["prospective_credit"]["recovered_historical_rows_credited"] = 2
        payload = self.build()
        self.assertIn("BUNDLE_PROSPECTIVE_CREDIT_UNSAFE", payload["blocking_reasons"])
        self.assertEqual(payload["safety"]["prospective_rows_credited"], 0)

    def test_path_escape_is_rejected(self):
        outside = self.root.parent / "outside-source-admission.csv"
        outside.write_text("outside\n", encoding="utf-8")
        try:
            partition = next(item for item in self.descriptor["partitions"] if item["source_role"] == "OHLC")
            partition["relative_path"] = "../outside-source-admission.csv"
            partition["expected_sha256"] = file_hash(outside)
            self.descriptor["d50_claimed_source_hashes"]["OHLC"] = file_hash(outside)
            result = self.build()
            self.assertIn("PARTITION_BTC_OHLC_DATA_PATH_INVALID", result["blocking_reasons"])
        finally:
            outside.unlink(missing_ok=True)

    def test_current_inventory_maps_to_exact_fail_closed_gap(self):
        payload = build_current_preflight(current_inventory(), self.contract)
        repeated = build_current_preflight(current_inventory(), self.contract)
        self.assertEqual(payload["status"], CURRENT_BLOCKED)
        self.assertEqual(payload["preflight_sha256"], repeated["preflight_sha256"])
        self.assertEqual(payload["complete_role_count"], 0)
        self.assertEqual(len(payload["recoverable_manual_btc_ohlc"]), 3)
        self.assertEqual(payload["exact_physical_hash_matches"], {"FUNDING": [], "OHLC": []})
        self.assertIn("D50_FUNDING_CLAIM_HAS_NO_EXACT_PHYSICAL_MATCH", payload["blocking_reasons"])
        self.assertIn("D50_OHLC_CLAIM_HAS_NO_EXACT_PHYSICAL_MATCH", payload["blocking_reasons"])
        self.assertFalse(payload["source_admitted"])
        self.assertFalse(payload["official_dataset_sealed"])

    def test_current_inventory_hash_tamper_is_visible_and_still_blocked(self):
        inventory = current_inventory()
        inventory["expected_cutoff"] = "2099-01-01"
        payload = build_current_preflight(inventory, self.contract)
        self.assertEqual(payload["status"], CURRENT_BLOCKED)
        self.assertIn("EVIDENCE_INVENTORY_HASH_INVALID", payload["blocking_reasons"])
        self.assertEqual(payload["prospective_rows_credited"], 0)


if __name__ == "__main__":
    unittest.main()
