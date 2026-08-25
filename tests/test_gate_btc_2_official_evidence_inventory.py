import copy
import csv
import gzip
import hashlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from tools.gate_btc_2_official_dataset_manifest import canonical_hash
from tools.gate_btc_2_official_evidence_inventory import (
    ASSESSMENT_KIND,
    CLASS_BLOCKED,
    CLASS_DUPLICATE,
    CLASS_STALE,
    MANUAL_MARKET_SPECS,
    SAFETY,
    SCHEMA,
    STATUS,
    build_inventory,
)


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = json.loads(
    (ROOT / "tools" / "gate_btc_2_official_dataset_contract_v1.json").read_text(
        encoding="utf-8"
    )
)
RUNTIME_COMMIT = "a" * 40


def exact_json(payload: dict) -> bytes:
    return (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")


def add_hash(payload: dict, field: str) -> dict:
    payload[field] = canonical_hash(payload)
    return payload


def csv_bytes(columns: list[str], rows: list[dict]) -> bytes:
    buf = io.StringIO(newline="")
    writer = csv.DictWriter(buf, fieldnames=columns, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return buf.getvalue().encode("utf-8")


def safety_payload() -> dict:
    return {
        "research_only": True,
        "shadow_only": True,
        "not_approved": True,
        "orders_generated": 0,
        "real_capital_used": 0,
        "promotion_allowed": False,
    }


def blocked_readiness() -> dict:
    blockers = {
        "BTC_CORE": ["REPORTING_STATUS_NOT_PASS"],
        "D50_ECONOMIC": ["D50_ECONOMIC_BEFORE_EXPECTED_CUTOFF"],
        "D50_QUALIFIED": ["D50_QUALIFICATION_BEFORE_EXPECTED_CUTOFF"],
        "MULTIASSET_V2A": [
            "V2A_INCOMPLETE_POINT_IN_TIME_COVERAGE",
            "V2A_SURVIVORSHIP_BIAS_PRESENT",
            "V2A_SYMBOL_LOAD_GAP",
        ],
    }
    tracks = {
        scope: {
            "status": "BLOCKED",
            "blockers": values,
            "dataset_sealed": False,
            "official_challenger_runs_allowed": False,
        }
        for scope, values in blockers.items()
    }
    payload = {
        "schema": "gate_btc.2_0.dataset_seal_readiness.v1",
        "assessment_kind": "READINESS_ONLY_NOT_A_DATASET_SEAL",
        "status": "BLOCKED",
        "expected_cutoff": "2026-08-23",
        "tracks": tracks,
        "ready_scopes": [],
        "blocked_scopes": sorted(tracks),
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
    return add_hash(payload, "assessment_sha256")


class EvidenceFixture:
    def __init__(self, root: Path):
        self.root = root
        self._v2a()
        self._gateway()
        self._qmaster()
        self._d50()
        self._manual_market()

    def write(self, relative: str, raw: bytes) -> None:
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)

    def write_json(self, relative: str, payload: dict) -> None:
        self.write(relative, exact_json(payload))

    def _v2a(self) -> None:
        base = "runtime/data_quality/v2a"
        snapshot_id = "2026-08-23-run-123"
        universe_columns = [
            "id",
            "symbol",
            "name",
            "market_cap_rank",
            "standard_ticker",
            "is_stable",
            "is_blocked",
        ]
        universe_raw = csv_bytes(
            universe_columns,
            [
                {
                    "id": "bitcoin",
                    "symbol": "BTC",
                    "name": "Bitcoin",
                    "market_cap_rank": "1",
                    "standard_ticker": "True",
                    "is_stable": "False",
                    "is_blocked": "False",
                },
                {
                    "id": "ethereum",
                    "symbol": "ETH",
                    "name": "Ethereum",
                    "market_cap_rank": "2",
                    "standard_ticker": "True",
                    "is_stable": "False",
                    "is_blocked": "False",
                },
            ],
        )
        quality_raw = csv_bytes(
            [
                "data_as_of",
                "attempted_symbols",
                "loaded_symbols",
                "failed_symbols",
                "coverage_ratio",
                "data_quality_status",
                "survivorship_bias_present",
            ],
            [
                {
                    "data_as_of": "2026-08-23",
                    "attempted_symbols": "2",
                    "loaded_symbols": "1",
                    "failed_symbols": "1",
                    "coverage_ratio": "0.5",
                    "data_quality_status": "PASS",
                    "survivorship_bias_present": "True",
                }
            ],
        )
        failures_raw = csv_bytes(
            ["symbol", "reason"],
            [{"symbol": "ETH", "reason": "source returned no candles"}],
        )
        archive_specs = {
            "universe_archive": (
                "coingecko_current_universe.csv.gz",
                universe_raw,
            ),
            "quality_archive": ("data_quality_summary.csv.gz", quality_raw),
            "failures_archive": ("download_failures.csv.gz", failures_raw),
        }
        archive_meta = {}
        for key, (suffix, raw) in archive_specs.items():
            relative = f"archives/{snapshot_id}.{suffix}"
            compressed = gzip.compress(raw, compresslevel=9, mtime=0)
            self.write(f"{base}/{relative}", compressed)
            archive_meta[key] = {
                "archive_path": relative,
                "archive_sha256": hashlib.sha256(compressed).hexdigest(),
                "raw_sha256": hashlib.sha256(raw).hexdigest(),
                "raw_size_bytes": len(raw),
                "archive_format": "gzip_mtime_0_exact_source_bytes",
            }
        snapshot = {
            "schema": "gate_btc.v2a_point_in_time_data_snapshot.v1",
            "snapshot_id": snapshot_id,
            "source_data_as_of": "2026-08-23",
            "source_run_id": "123",
            "attempted_symbols": 2,
            "loaded_symbols": 1,
            "failed_symbols": 1,
            "coverage_ratio": 0.5,
            "universe_row_count": 2,
            "download_failure_row_count": 1,
            "survivorship_bias_present": True,
            "feeds_frozen_engine": False,
            "retrospective_reconstruction": False,
            **safety_payload(),
            **archive_meta,
        }
        add_hash(snapshot, "record_sha256")
        self.write_json(f"{base}/snapshots/{snapshot_id}.json", snapshot)
        status = {
            "schema": "gate_btc.v2a_point_in_time_data_ledger_status.v1",
            "status": "ACTIVE_RESEARCH_ONLY",
            "latest_snapshot_id": snapshot_id,
            "latest_source_data_as_of": "2026-08-23",
            "latest_source_run_id": "123",
            "latest_attempted_symbols": 2,
            "latest_loaded_symbols": 1,
            "latest_failed_symbols": 1,
            "latest_coverage_ratio": 0.5,
            "survivorship_bias_present": True,
            "feeds_frozen_engine": False,
            "retrospective_backfill_allowed": False,
            **safety_payload(),
        }
        add_hash(status, "status_sha256")
        self.write_json(f"{base}/STATUS.json", status)

    def _gateway(self) -> None:
        base = "runtime/universe_snapshots/gateway"
        snapshot_id = "2026-08-24-run-123"
        columns = ["base", "cg_rank", "cg_name", "cg_market_cap", "cg_volume"]
        raw = csv_bytes(
            columns,
            [
                {
                    "base": "BTC",
                    "cg_rank": "1",
                    "cg_name": "Bitcoin",
                    "cg_market_cap": "1",
                    "cg_volume": "1",
                }
            ],
        )
        compressed = gzip.compress(raw, compresslevel=9, mtime=0)
        archive_rel = f"archives/{snapshot_id}.scanner_top500_raw.csv.gz"
        self.write(f"{base}/{archive_rel}", compressed)
        snapshot = {
            "schema": "gate_btc.gateway_point_in_time_universe_snapshot.v1",
            "snapshot_id": snapshot_id,
            "source_data_as_of": "2026-08-24",
            "source_run_id": "123",
            "columns": columns,
            "row_count": 1,
            "raw_csv_size_bytes": len(raw),
            "raw_csv_sha256": hashlib.sha256(raw).hexdigest(),
            "archive_path": archive_rel,
            "archive_sha256": hashlib.sha256(compressed).hexdigest(),
            "gateway_warning_failed_checks": [],
            "feeds_frozen_engine": False,
            "retrospective_reconstruction": False,
            **safety_payload(),
        }
        add_hash(snapshot, "record_sha256")
        self.write_json(f"{base}/snapshots/{snapshot_id}.json", snapshot)
        status = {
            "schema": "gate_btc.gateway_point_in_time_universe_ledger_status.v1",
            "status": "ACTIVE_RESEARCH_ONLY",
            "latest_snapshot_id": snapshot_id,
            "latest_source_data_as_of": "2026-08-24",
            "latest_source_run_id": "123",
            "latest_raw_csv_sha256": hashlib.sha256(raw).hexdigest(),
            "feeds_frozen_engine": False,
            "retrospective_backfill_allowed": False,
            **safety_payload(),
        }
        add_hash(status, "status_sha256")
        self.write_json(f"{base}/STATUS.json", status)

    def _qmaster(self) -> None:
        columns = ["date", "symbol", "close_usd", "volume_usd", "source"]
        raw = csv_bytes(
            columns,
            [
                {
                    "date": "2026-08-22",
                    "symbol": "BTC",
                    "close_usd": "1",
                    "volume_usd": "2",
                    "source": "fixture",
                },
                {
                    "date": "2026-08-23",
                    "symbol": "ETH",
                    "close_usd": "3",
                    "volume_usd": "4",
                    "source": "fixture",
                },
            ],
        )
        sha = hashlib.sha256(raw).hexdigest()
        descriptor = {
            "schema": "gate_btc.qmaster_export.v1",
            "status": "PASS",
            "data_as_of": "2026-08-23",
            "rows": 2,
            "symbols": 2,
            "csv_sha256": sha,
            "source_member_sha256": sha,
            "research_only": True,
            "operational_status": "NOT_APPROVED",
            "orders_generated": 0,
            "real_capital_used": 0,
            "methodology_changed": False,
        }
        descriptor_raw = exact_json(descriptor)
        for prefix in ("runtime", "runtime/qmaster"):
            self.write(f"{prefix}/GATE_BTC_QMASTER_LATEST.csv", raw)
            self.write(f"{prefix}/GATE_BTC_QMASTER_LATEST.txt", descriptor_raw)

    def _d50(self) -> None:
        status = {
            "schema": "gate_btc.d50_measurement_status.v1",
            "prospective_immutable_ledger": {
                "latest_prospective_date": "2026-08-22",
                "source_hashes": {"funding": "1" * 64, "ohlc": "2" * 64},
            },
            **safety_payload(),
        }
        add_hash(status, "status_sha256")
        self.write_json("runtime/ledgers/d50/STATUS.json", status)

    def _manual_market(self) -> None:
        for venue, spec in MANUAL_MARKET_SPECS.items():
            for asset in ("BTC", "ETH", "SOL"):
                relative = spec["path"].format(asset=asset, asset_lower=asset.lower())
                columns = [
                    "timestamp",
                    "open",
                    "high",
                    "low",
                    "close",
                    "volume",
                    "symbol",
                    spec["interval_field"],
                    "source",
                ]
                if venue == "OKX_SWAP":
                    columns.append("confirm")
                rows = []
                if venue != "BYBIT_LINEAR":
                    for day, close, confirm in (("01", "2", "1"), ("02", "3", "0")):
                        row = {
                            "timestamp": f"2026-08-{day}T00:00:00Z",
                            "open": "2",
                            "high": "4",
                            "low": "1",
                            "close": close,
                            "volume": "10",
                            "symbol": spec["symbol"].format(asset=asset),
                            spec["interval_field"]: spec["interval"],
                            "source": spec["source"],
                        }
                        if venue == "OKX_SWAP":
                            row["confirm"] = confirm
                        rows.append(row)
                self.write(relative, csv_bytes(columns, rows))


class GateBTC2OfficialEvidenceInventoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        EvidenceFixture(self.root)
        self.readiness = blocked_readiness()

    def tearDown(self):
        self.temp.cleanup()

    def build(self, *, contract: dict | None = None, readiness: dict | None = None) -> dict:
        return build_inventory(
            self.root,
            RUNTIME_COMMIT,
            readiness or self.readiness,
            contract or CONTRACT,
        )

    def test_exact_fixture_is_blocked_without_descriptor_or_seal(self):
        payload = self.build()
        self.assertEqual(payload["schema"], SCHEMA)
        self.assertEqual(payload["assessment_kind"], ASSESSMENT_KIND)
        self.assertEqual(payload["status"], STATUS)
        self.assertEqual(payload["admissible_candidate_count"], 0)
        self.assertEqual(payload["physical_evidence_count"], 25)
        self.assertEqual(payload["safety"], SAFETY)
        self.assertFalse(payload["safety"]["official_dataset_descriptor_created"])
        self.assertFalse(payload["safety"]["official_dataset_sealed"])

    def test_output_is_deterministic_and_read_only(self):
        before = {
            path.relative_to(self.root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in self.root.rglob("*")
            if path.is_file()
        }
        first = self.build()
        second = self.build()
        after = {
            path.relative_to(self.root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in self.root.rglob("*")
            if path.is_file()
        }
        self.assertEqual(first, second)
        self.assertEqual(before, after)
        unsigned = dict(first)
        claimed = unsigned.pop("inventory_sha256")
        self.assertEqual(claimed, canonical_hash(unsigned))

    def test_exact_bytes_include_sha256_and_git_blob_identity(self):
        payload = self.build()
        item = next(
            artifact
            for artifact in payload["physical_evidence"]
            if artifact["path"] == "runtime/GATE_BTC_QMASTER_LATEST.csv"
        )
        raw = (self.root / item["path"]).read_bytes()
        git_blob = hashlib.sha1(f"blob {len(raw)}\0".encode("ascii") + raw).hexdigest()
        self.assertEqual(item["sha256"], hashlib.sha256(raw).hexdigest())
        self.assertEqual(item["git_blob_sha1"], git_blob)

    def test_manual_market_files_are_physical_but_stale_and_unsealed(self):
        payload = self.build()
        manual = payload["manual_market_evidence"]
        self.assertEqual(manual["file_count"], 12)
        self.assertEqual(manual["nonempty_file_count"], 9)
        self.assertEqual(manual["btc_nonempty_source_count"], 3)
        self.assertEqual(manual["btc_empty_sources"], ["BYBIT_LINEAR"])
        self.assertIn("BTC_CORE_MANUAL_OHLC_LATEST_BEFORE_EXPECTED_CUTOFF", manual["blockers"])
        classifications = {
            item["classification"]
            for item in payload["physical_evidence"]
            if item["evidence_role"] == "MANUAL_PUBLIC_OHLC_CANDIDATE_NOT_OFFICIAL"
        }
        self.assertEqual(classifications, {CLASS_BLOCKED, CLASS_STALE})

    def test_v2a_bytes_do_not_override_incomplete_coverage(self):
        payload = self.build()
        v2a = payload["v2a_latest"]
        self.assertEqual(v2a["loaded_symbols"], 1)
        self.assertEqual(v2a["failed_symbols"], 1)
        self.assertEqual(v2a["coverage_ratio"], 0.5)
        self.assertTrue(v2a["survivorship_bias_present"])
        self.assertIn("V2A_SYMBOL_LOAD_GAP", v2a["blockers"])

    def test_qmaster_aliases_are_exact_and_never_auto_selected(self):
        payload = self.build()
        self.assertEqual(payload["qmaster"]["duplicate_alias_count"], 2)
        self.assertFalse(payload["qmaster"]["canonical_path_auto_selected"])
        duplicates = [
            item
            for item in payload["physical_evidence"]
            if item["classification"] == CLASS_DUPLICATE
        ]
        self.assertEqual(len(duplicates), 2)

    def test_d50_hash_only_references_are_not_source_bytes(self):
        payload = self.build()
        self.assertFalse(payload["d50"]["source_paths_present"])
        self.assertIn(
            "D50_SOURCE_HASHES_HAVE_NO_RUNTIME_PATHS",
            payload["d50"]["blockers"],
        )
        self.assertEqual(
            payload["scope_assessments"]["D50_ECONOMIC"]["admissible_candidate_count"],
            0,
        )

    def test_unclassified_tabular_file_is_reported_fail_closed(self):
        self.root.joinpath("mystery.csv").write_text("a\n1\n", encoding="utf-8")
        payload = self.build()
        self.assertEqual(payload["tabular_discovery"]["unclassified_paths"], ["mystery.csv"])
        self.assertIn(
            "UNCLASSIFIED_TABULAR_EVIDENCE_PRESENT_FAIL_CLOSED",
            payload["scope_assessments"]["BTC_CORE"]["blockers"],
        )

    def test_corrupt_referenced_gzip_is_rejected(self):
        path = self.root / (
            "runtime/data_quality/v2a/archives/"
            "2026-08-23-run-123.coingecko_current_universe.csv.gz"
        )
        path.write_bytes(b"not-gzip")
        with self.assertRaisesRegex(RuntimeError, "corrupt gzip evidence"):
            self.build()

    def test_symlinked_alias_is_rejected(self):
        alias = self.root / "runtime/qmaster/GATE_BTC_QMASTER_LATEST.csv"
        alias.unlink()
        alias.symlink_to(self.root / "runtime/GATE_BTC_QMASTER_LATEST.csv")
        with self.assertRaisesRegex(RuntimeError, "unsafe runtime evidence"):
            self.build()

    def test_readiness_hash_tamper_is_rejected(self):
        readiness = copy.deepcopy(self.readiness)
        readiness["expected_cutoff"] = "2026-08-24"
        with self.assertRaisesRegex(RuntimeError, "readiness assessment_sha256 mismatch"):
            self.build(readiness=readiness)

    def test_unsafe_qmaster_boundary_is_rejected(self):
        path = self.root / "runtime/GATE_BTC_QMASTER_LATEST.txt"
        payload = json.loads(path.read_text())
        payload["real_capital_used"] = 1
        path.write_bytes(exact_json(payload))
        mirror = self.root / "runtime/qmaster/GATE_BTC_QMASTER_LATEST.txt"
        mirror.write_bytes(exact_json(payload))
        with self.assertRaisesRegex(RuntimeError, "unsafe QMASTER field real_capital_used"):
            self.build()

    def test_invalid_frozen_contract_is_rejected(self):
        contract = copy.deepcopy(CONTRACT)
        contract["policies"]["partial_scope_seal_allowed"] = True
        with self.assertRaisesRegex(RuntimeError, "official dataset contract is invalid"):
            self.build(contract=contract)


if __name__ == "__main__":
    unittest.main()
