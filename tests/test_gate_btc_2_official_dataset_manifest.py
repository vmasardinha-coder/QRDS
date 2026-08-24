import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from tools.gate_btc_2_official_dataset_manifest import (
    BLOCKED,
    READY,
    build_manifest,
    canonical_hash,
    validate_contract,
)


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "tools" / "gate_btc_2_official_dataset_contract_v1.json"


def exact_json(payload: dict) -> str:
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def load_contract() -> dict:
    return json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))


def readiness(*, blocked_scope: str | None = None) -> dict:
    scopes = ["BTC_CORE", "D50_ECONOMIC", "D50_QUALIFIED", "MULTIASSET_V2A"]
    tracks = {}
    for scope in scopes:
        blocked = scope == blocked_scope
        tracks[scope] = {
            "status": "BLOCKED" if blocked else "READY_FOR_SCOPED_DATASET_MANIFEST",
            "blockers": ["REAL_EVIDENCE_INCOMPLETE"] if blocked else [],
            "dataset_sealed": False,
            "official_challenger_runs_allowed": False,
        }
    payload = {
        "schema": "gate_btc.2_0.dataset_seal_readiness.v1",
        "assessment_kind": "READINESS_ONLY_NOT_A_DATASET_SEAL",
        "status": "BLOCKED" if blocked_scope else "READY_FOR_SCOPED_DATASET_MANIFEST",
        "expected_cutoff": "2026-08-23",
        "hard_failures": [],
        "delivery_gaps": ["REAL_EVIDENCE_INCOMPLETE"] if blocked_scope else [],
        "ready_scopes": [scope for scope in scopes if scope != blocked_scope],
        "blocked_scopes": [blocked_scope] if blocked_scope else [],
        "tracks": tracks,
        "stage_3_dataset_sealed": False,
        "official_challenger_runs_allowed": False,
        "research_only": True,
        "shadow_only": True,
        "not_approved": True,
        "engine_feed": False,
        "orders_generated": 0,
        "real_capital_used": 0,
        "promotion_allowed": False,
    }
    payload["assessment_sha256"] = canonical_hash(payload)
    return payload


def tabular_schema(schema_id: str, fmt: str) -> dict:
    return {
        "schema": "gate_btc.2_0.tabular_dataset_schema.v1",
        "schema_id": schema_id,
        "format": fmt,
        "timezone": "UTC",
        "columns": [
            {"name": "symbol", "type": "string", "role": "identifier"},
            {
                "name": "observation_timestamp_utc",
                "type": "string",
                "role": "observation_timestamp",
            },
            {
                "name": "available_at_utc",
                "type": "string",
                "role": "available_at",
            },
            {"name": "value", "type": "number", "role": "measurement"},
        ],
        "primary_key": ["symbol", "observation_timestamp_utc"],
        "economic_fields": [],
        "future_known_metadata_allowed": False,
    }


def build_package(root: Path, contract: dict) -> dict:
    (root / "data").mkdir()
    (root / "schemas").mkdir()
    (root / "provenance").mkdir()
    btc_schema = tabular_schema("gate_btc.2_0.btc_core_fixture.v1", "csv")
    v2a_schema = tabular_schema("gate_btc.2_0.v2a_fixture.v1", "jsonl")
    btc_schema_path = root / "schemas" / "btc_core.json"
    v2a_schema_path = root / "schemas" / "v2a.json"
    btc_schema_path.write_text(exact_json(btc_schema), encoding="utf-8")
    v2a_schema_path.write_text(exact_json(v2a_schema), encoding="utf-8")

    btc_path = root / "data" / "btc_core.csv"
    btc_path.write_text(
        "symbol,observation_timestamp_utc,available_at_utc,value\n"
        "BTC,2026-08-22T00:00:00Z,2026-08-22T00:00:05Z,1\n"
        "BTC,2026-08-23T00:00:00Z,2026-08-23T00:00:05Z,2\n",
        encoding="utf-8",
    )
    v2a_path = root / "data" / "v2a.jsonl"
    v2a_rows = [
        {
            "symbol": "BTC",
            "observation_timestamp_utc": "2026-08-23T00:00:00Z",
            "available_at_utc": "2026-08-23T00:01:00Z",
            "value": 1,
        },
        {
            "symbol": "ETH",
            "observation_timestamp_utc": "2026-08-23T00:00:00Z",
            "available_at_utc": "2026-08-23T00:01:00Z",
            "value": 2,
        },
    ]
    v2a_path.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in v2a_rows),
        encoding="utf-8",
    )

    sources = [
        {
            "source_id": "SRC-BTC-OFFICIAL",
            "provider": "Fixture Official Provider",
            "source_reference": "immutable://btc/2026-08-23",
            "access_class": "official_free",
            "license_status": "auditable_fixture",
            "observed_or_derived": "observed",
            "timezone": "UTC",
            "causal_availability_rule": "available_at_utc is provider publication time",
            "immutable_reference": True,
            "provenance_path": "provenance/btc.json",
        },
        {
            "source_id": "SRC-V2A-DERIVED",
            "provider": "QRDS Data Fixture",
            "source_reference": "immutable://v2a/2026-08-23",
            "access_class": "internal_derived",
            "license_status": "internal_project_artifact",
            "observed_or_derived": "derived",
            "timezone": "UTC",
            "causal_availability_rule": "available only after all observed inputs",
            "immutable_reference": True,
            "provenance_path": "provenance/v2a.json",
        },
    ]
    for source in sources:
        provenance = {
            "schema": "gate_btc.2_0.source_provenance.v1",
            **{
                field: source[field]
                for field in (
                    "source_id",
                    "provider",
                    "source_reference",
                    "access_class",
                    "license_status",
                    "observed_or_derived",
                    "timezone",
                    "causal_availability_rule",
                    "immutable_reference",
                )
            },
        }
        provenance_path = root / source["provenance_path"]
        provenance_path.write_text(exact_json(provenance), encoding="utf-8")
        source["expected_provenance_sha256"] = hashlib.sha256(
            provenance_path.read_bytes()
        ).hexdigest()
    partitions = [
        {
            "partition_id": "BTC_CORE_DAILY",
            "scope": "BTC_CORE",
            "relative_path": "data/btc_core.csv",
            "schema_path": "schemas/btc_core.json",
            "source_id": "SRC-BTC-OFFICIAL",
            "observed_or_derived": "observed",
            "format": "csv",
            "granularity": "daily",
            "expected_sha256": hashlib.sha256(btc_path.read_bytes()).hexdigest(),
            "expected_schema_sha256": hashlib.sha256(btc_schema_path.read_bytes()).hexdigest(),
        },
        {
            "partition_id": "MULTIASSET_V2A_DAILY",
            "scope": "MULTIASSET_V2A",
            "relative_path": "data/v2a.jsonl",
            "schema_path": "schemas/v2a.json",
            "source_id": "SRC-V2A-DERIVED",
            "observed_or_derived": "derived",
            "format": "jsonl",
            "granularity": "daily",
            "expected_sha256": hashlib.sha256(v2a_path.read_bytes()).hexdigest(),
            "expected_schema_sha256": hashlib.sha256(v2a_schema_path.read_bytes()).hexdigest(),
        },
    ]
    return {
        "schema": "gate_btc.2_0.official_dataset_descriptor.v1",
        "dataset_id": "GATE_BTC_2_OFFICIAL_FIXTURE",
        "dataset_version": "2026-08-23.v1",
        "baseline_commit_sha": "38de132bcac86f3c0703dd20633fa131b2650d8b",
        "created_at_utc": "2026-08-24T00:00:00Z",
        "cutoff_utc": "2026-08-23T23:59:59Z",
        "contract_sha256": contract["contract_sha256"],
        "required_readiness_scopes": list(contract["required_readiness_scopes"]),
        "sources": sources,
        "partitions": partitions,
        "policies": copy.deepcopy(contract["policies"]),
        "safety": copy.deepcopy(contract["safety"]),
    }


class GateBTC2OfficialDatasetManifestTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.contract = load_contract()
        self.descriptor = build_package(self.root, self.contract)

    def tearDown(self):
        self.temp.cleanup()

    def test_frozen_contract_hash_is_valid(self):
        self.assertEqual(validate_contract(self.contract), [])

    def test_complete_exact_package_is_only_ready_for_explicit_review(self):
        payload = build_manifest(
            self.root,
            self.descriptor,
            readiness(),
            self.contract,
        )
        repeated = build_manifest(
            self.root,
            self.descriptor,
            readiness(),
            self.contract,
        )
        self.assertEqual(payload["status"], READY)
        self.assertEqual(payload["manifest_sha256"], repeated["manifest_sha256"])
        self.assertEqual(payload["represented_dataset_scopes"], ["BTC_CORE", "MULTIASSET_V2A"])
        self.assertEqual([item["row_count"] for item in payload["file_inventory"]], [2, 2])
        self.assertFalse(payload["official_dataset_sealed"])
        self.assertFalse(payload["official_challenger_runs_allowed"])
        self.assertFalse(payload["economics_consumed"])
        self.assertEqual(payload["safety"]["orders_generated"], 0)
        self.assertEqual(payload["safety"]["real_capital_used"], 0)

    def test_real_readiness_blocker_cannot_be_hidden_by_complete_files(self):
        payload = build_manifest(
            self.root,
            self.descriptor,
            readiness(blocked_scope="MULTIASSET_V2A"),
            self.contract,
        )
        self.assertEqual(payload["status"], BLOCKED)
        self.assertIn("READINESS_SCOPE_BLOCKED:MULTIASSET_V2A", payload["blocking_reasons"])
        self.assertIn(
            "READINESS:MULTIASSET_V2A:REAL_EVIDENCE_INCOMPLETE",
            payload["blocking_reasons"],
        )

    def test_exact_data_hash_tampering_fails_closed(self):
        (self.root / "data" / "btc_core.csv").write_text("tampered\n", encoding="utf-8")
        payload = build_manifest(self.root, self.descriptor, readiness(), self.contract)
        self.assertEqual(payload["status"], BLOCKED)
        self.assertIn("PARTITION_BTC_CORE_DAILY_DATA_HASH_MISMATCH", payload["blocking_reasons"])

    def test_exact_source_provenance_tampering_fails_closed(self):
        path = self.root / "provenance" / "btc.json"
        provenance = json.loads(path.read_text(encoding="utf-8"))
        provenance["provider"] = "Mutated Provider"
        path.write_text(exact_json(provenance), encoding="utf-8")
        payload = build_manifest(self.root, self.descriptor, readiness(), self.contract)
        self.assertEqual(payload["status"], BLOCKED)
        self.assertIn(
            "SOURCE_SRC-BTC-OFFICIAL_PROVENANCE_HASH_MISMATCH",
            payload["blocking_reasons"],
        )
        self.assertIn(
            "SOURCE_SRC-BTC-OFFICIAL_PROVENANCE_FIELD_MISMATCH:provider",
            payload["blocking_reasons"],
        )

    def test_schema_hash_and_economic_fields_fail_closed(self):
        schema_path = self.root / "schemas" / "btc_core.json"
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        schema["economic_fields"] = ["value"]
        schema_path.write_text(exact_json(schema), encoding="utf-8")
        self.descriptor["partitions"][0]["expected_schema_sha256"] = hashlib.sha256(
            schema_path.read_bytes()
        ).hexdigest()
        payload = build_manifest(self.root, self.descriptor, readiness(), self.contract)
        self.assertIn(
            "SCHEMA_BTC_CORE_DAILY_ECONOMIC_FIELDS_FORBIDDEN",
            payload["blocking_reasons"],
        )
        self.assertFalse(payload["official_dataset_sealed"])

    def test_future_available_row_fails_closed(self):
        path = self.root / "data" / "btc_core.csv"
        path.write_text(
            "symbol,observation_timestamp_utc,available_at_utc,value\n"
            "BTC,2026-08-23T00:00:00Z,2026-08-24T00:00:00Z,1\n",
            encoding="utf-8",
        )
        self.descriptor["partitions"][0]["expected_sha256"] = hashlib.sha256(
            path.read_bytes()
        ).hexdigest()
        payload = build_manifest(self.root, self.descriptor, readiness(), self.contract)
        self.assertIn(
            "PARTITION_BTC_CORE_DAILY_AVAILABLE_AFTER_CUTOFF_ROW_1",
            payload["blocking_reasons"],
        )

    def test_duplicate_primary_key_fails_closed(self):
        path = self.root / "data" / "btc_core.csv"
        path.write_text(
            "symbol,observation_timestamp_utc,available_at_utc,value\n"
            "BTC,2026-08-23T00:00:00Z,2026-08-23T00:01:00Z,1\n"
            "BTC,2026-08-23T00:00:00Z,2026-08-23T00:01:00Z,2\n",
            encoding="utf-8",
        )
        self.descriptor["partitions"][0]["expected_sha256"] = hashlib.sha256(
            path.read_bytes()
        ).hexdigest()
        payload = build_manifest(self.root, self.descriptor, readiness(), self.contract)
        self.assertIn(
            "PARTITION_BTC_CORE_DAILY_PRIMARY_KEY_INVALID_ROW_2",
            payload["blocking_reasons"],
        )

    def test_path_escape_is_rejected(self):
        outside = self.root.parent / "outside-gate2.csv"
        outside.write_text("outside\n", encoding="utf-8")
        try:
            self.descriptor["partitions"][0]["relative_path"] = "../outside-gate2.csv"
            self.descriptor["partitions"][0]["expected_sha256"] = hashlib.sha256(
                outside.read_bytes()
            ).hexdigest()
            payload = build_manifest(self.root, self.descriptor, readiness(), self.contract)
            self.assertIn(
                "PARTITION_BTC_CORE_DAILY_DATA_PATH_INVALID",
                payload["blocking_reasons"],
            )
        finally:
            outside.unlink(missing_ok=True)

    def test_readiness_hash_mutation_fails_closed(self):
        assessment = readiness()
        assessment["status"] = "MUTATED_AFTER_HASH"
        payload = build_manifest(self.root, self.descriptor, assessment, self.contract)
        self.assertIn("READINESS_HASH_INVALID", payload["blocking_reasons"])

    def test_policy_relaxation_and_source_kind_drift_fail_closed(self):
        self.descriptor["policies"]["economic_calibration_allowed"] = True
        self.descriptor["partitions"][0]["observed_or_derived"] = "derived"
        payload = build_manifest(self.root, self.descriptor, readiness(), self.contract)
        self.assertIn("DESCRIPTOR_POLICIES_MISMATCH", payload["blocking_reasons"])
        self.assertIn(
            "PARTITION_BTC_CORE_DAILY_SOURCE_KIND_MISMATCH",
            payload["blocking_reasons"],
        )


if __name__ == "__main__":
    unittest.main()
