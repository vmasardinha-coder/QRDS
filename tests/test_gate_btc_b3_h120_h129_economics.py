from __future__ import annotations

import io
import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
for path in (ROOT, TOOLS):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

try:
    import requests
except ModuleNotFoundError:  # Keep the repository's dependency-light local suite runnable.
    import pip._vendor.requests as requests

    sys.modules["requests"] = requests

from tools import gate_btc_b3_h120_h129_economics as economics
from tools import gate_btc_b3_h120_h129_guarded as guarded
from tools import gate_btc_b3_h120_h129_source_probe as source_probe


class FakeResponse:
    def __init__(self, content: bytes):
        self.content = content
        self.status_code = 200
        self.headers = {"content-type": "application/zip"}

    def raise_for_status(self):
        return None


def price_xml(rows):
    fields = []
    for row in rows:
        ticker, volume = row[0], row[1]
        fin = "" if len(row) > 2 and row[2] == "regular-only" else f"<FinInstrmQty>{volume}</FinInstrmQty>"
        fields.append(
            "<BizGrp><Document><PricRpt>"
            f"<SctyId><TckrSymb>{ticker}</TckrSymb></SctyId>"
            "<TradDtls><TradQty>10</TradQty></TradDtls>"
            f"<FinInstrmAttrbts>{fin}<RglrTraddCtrcts>{volume}</RglrTraddCtrcts>"
            "<OpnIntrst>100</OpnIntrst><FrstPric>100</FrstPric><MinPric>90</MinPric>"
            "<MaxPric>110</MaxPric><LastPric>105</LastPric></FinInstrmAttrbts>"
            "</PricRpt></Document></BizGrp>"
        )
    return ("<root>" + "".join(fields) + "</root>").encode()


def price_report(rows, earlier_rows=None):
    xml = price_xml(rows)
    body = io.BytesIO()
    with zipfile.ZipFile(body, "w", zipfile.ZIP_DEFLATED) as archive:
        if earlier_rows is None:
            archive.writestr("PriceReport.xml", xml)
        else:
            nested = io.BytesIO()
            with zipfile.ZipFile(nested, "w", zipfile.ZIP_DEFLATED) as inner:
                early = zipfile.ZipInfo("BVBG.086.01_early.xml", date_time=(2026, 8, 7, 17, 0, 0))
                late = zipfile.ZipInfo("BVBG.086.01_late.xml", date_time=(2026, 8, 7, 19, 0, 0))
                inner.writestr(early, price_xml(earlier_rows)); inner.writestr(late, xml)
            archive.writestr("PR260807.zip", nested.getvalue())
    return body.getvalue()


class H120H129ContractIdentityTests(unittest.TestCase):
    def test_source_qa_and_economics_share_exact_identity_contract(self):
        self.assertEqual(economics.FUTURE_RE.pattern, source_probe.FUTURE_RE.pattern)
        self.assertEqual(economics.XML_MEMBER_SELECTION, source_probe.XML_MEMBER_SELECTION)

    def test_front_selection_excludes_higher_volume_option(self):
        response = FakeResponse(
            price_report(
                [
                    ("WINQ26", 200),
                    ("WDOQ26", 100),
                    ("WDOQ26C005500", 100000),
                ]
            )
        )

        with mock.patch.object(economics.requests, "get", return_value=response):
            result = economics.parse_day("2026-08-07")

        self.assertEqual(result["status"], "PASS")
        selected = {row["asset"]: row for row in result["rows"]}
        self.assertEqual(selected["WIN"]["ticker"], "WINQ26")
        self.assertEqual(selected["WDO"]["ticker"], "WDOQ26")
        self.assertEqual(selected["WDO"]["volume"], 100.0)

    def test_latest_official_xml_snapshot_is_selected(self):
        response = FakeResponse(
            price_report(
                [("WINQ26", 200), ("WDOQ26", 100)],
                earlier_rows=[("WINQ26", 999999), ("WDOQ26", 999999)],
            )
        )

        with mock.patch.object(economics.requests, "get", return_value=response):
            result = economics.parse_day("2026-08-07")

        selected = {row["asset"]: row for row in result["rows"]}
        self.assertEqual(selected["WIN"]["volume"], 200.0)
        self.assertEqual(selected["WDO"]["volume"], 100.0)
        self.assertEqual(result["xml_name"], "BVBG.086.01_late.xml")
        self.assertEqual(result["xml_member_count"], 2)

    def test_malformed_latest_snapshot_falls_back_to_latest_well_formed_member(self):
        nested = io.BytesIO()
        with zipfile.ZipFile(nested, "w", zipfile.ZIP_DEFLATED) as inner:
            early = zipfile.ZipInfo("valid.xml", date_time=(2021, 1, 4, 17, 0, 0))
            late = zipfile.ZipInfo("malformed.xml", date_time=(2021, 1, 4, 19, 0, 0))
            inner.writestr(early, price_xml([("WINQ26", 200), ("WDOQ26", 100)]))
            inner.writestr(late, b"<root><broken></root>")
        outer = io.BytesIO()
        with zipfile.ZipFile(outer, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("PR210104.zip", nested.getvalue())

        with mock.patch.object(economics.requests, "get", return_value=FakeResponse(outer.getvalue())):
            result = economics.parse_day("2021-01-04")

        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["xml_name"], "valid.xml")
        self.assertEqual([item["xml_name"] for item in result["xml_members_rejected"]], ["malformed.xml"])

    def test_regular_contract_volume_is_used_only_when_total_is_absent(self):
        response = FakeResponse(price_report([("WINQ26", 200, "regular-only"), ("WDOQ26", 100)]))

        with mock.patch.object(economics.requests, "get", return_value=response):
            result = economics.parse_day("2026-08-07")

        selected = {row["asset"]: row for row in result["rows"]}
        self.assertEqual(selected["WIN"]["volume"], 200.0)
        self.assertEqual(selected["WIN"]["volume_source"], "RglrTraddCtrcts")

    def test_option_cannot_satisfy_missing_wdo_future(self):
        response = FakeResponse(price_report([("WINQ26", 200), ("WDOQ26P005500", 100000)]))

        with mock.patch.object(economics.requests, "get", return_value=response):
            result = economics.parse_day("2026-08-07")

        self.assertEqual(result["status"], "DATA_GAP_ASSET")
        self.assertEqual([row["ticker"] for row in result["rows"]], ["WINQ26"])

    def test_programming_error_is_not_converted_to_data_gap(self):
        response = FakeResponse(price_report([("WINQ26", 200), ("WDOQ26", 100)]))

        with mock.patch.object(economics.requests, "get", return_value=response), mock.patch.object(
            economics, "price_report_rows", side_effect=ValueError("programming defect")
        ):
            with self.assertRaisesRegex(ValueError, "programming defect"):
                economics.parse_day("2026-08-07")


class H120H129FamilyCoverageTests(unittest.TestCase):
    def setUp(self):
        self.sessions = pd.bdate_range("2025-01-02", periods=80).strftime("%Y-%m-%d").tolist()
        rows = []
        for day in self.sessions:
            for asset in economics.ASSETS:
                rows.append(
                    {
                        "date": day,
                        "asset": asset,
                        "ticker": f"{asset}Q25",
                        "trade_count": 10.0,
                        "volume": 100.0,
                        "oi": 1000.0,
                        "open": 100.0,
                        "low": 90.0,
                        "high": 110.0,
                        "close": 105.0,
                    }
                )
        self.daily = pd.DataFrame(rows)

    def test_complete_exact_session_joins_cover_every_family(self):
        coverage = economics.family_join_coverage(self.daily, self.sessions)

        self.assertEqual(set(coverage), set(economics.FAMS))
        self.assertTrue(all(item["coverage"] == 1.0 for item in coverage.values()))
        self.assertEqual(coverage["H120"]["completed_session_lags"], [1, 2])
        self.assertEqual(coverage["H127"]["completed_session_lags"], [1, 2, 3])
        self.assertEqual(coverage["H129"]["warmup_sessions"], 60)

    def test_missing_oi_blocks_only_h122_coverage(self):
        affected_days = self.sessions[1:10]
        mask = self.daily["date"].isin(affected_days) & (self.daily["asset"] == "WDO")
        self.daily.loc[mask, "oi"] = np.nan

        coverage = economics.family_join_coverage(self.daily, self.sessions)

        self.assertLess(coverage["H122"]["coverage"], 0.90)
        for family in set(economics.FAMS) - {"H122"}:
            self.assertEqual(coverage[family]["coverage"], 1.0)

    def test_missing_trade_counts_propagate_only_to_dependent_families(self):
        affected_days = self.sessions[61:70]
        mask = self.daily["date"].isin(affected_days) & (self.daily["asset"] == "WIN")
        self.daily.loc[mask, "trade_count"] = np.nan

        coverage = economics.family_join_coverage(self.daily, self.sessions)

        dependent = {"H120", "H121", "H123", "H124", "H125", "H126", "H127", "H128", "H129"}
        self.assertTrue(all(coverage[family]["coverage"] < 0.90 for family in dependent))
        self.assertEqual(coverage["H122"]["coverage"], 1.0)

    def test_no_economic_rows_are_computed_for_disabled_families(self):
        sessions = {}
        for day in self.sessions:
            sessions[day] = pd.DataFrame(
                {
                    "open_WIN": np.linspace(100.0, 101.0, 60),
                    "close_WIN": np.linspace(100.1, 101.1, 60),
                    "open_WDO": np.linspace(50.0, 51.0, 60),
                    "close_WDO": np.linspace(50.1, 51.1, 60),
                }
            )
        daily = self.daily.copy()
        daily["ret"] = 1.0
        daily["z_trade_count"] = 2.0
        daily["z_avg_size"] = 2.0
        daily["z_turnover"] = 2.0
        daily["z_range_per_trade"] = 2.0

        enabled = economics.gen(sessions, 5, daily, families=("H120",))
        result = economics.gen(sessions, 5, daily, families=())

        self.assertFalse(enabled.empty)
        self.assertEqual(set(enabled["family"]), {"H120"})
        self.assertTrue(result.empty)

    def test_all_data_gap_input_closes_without_entering_economic_rows(self):
        sessions = {day: pd.DataFrame() for day in self.sessions}

        result = economics.gen(sessions, 5, pd.DataFrame(), families=())

        self.assertTrue(result.empty)


class H120H129CausalCalendarTests(unittest.TestCase):
    def test_missing_official_session_does_not_compress_daily_change(self):
        days = pd.bdate_range("2025-01-02", periods=25).strftime("%Y-%m-%d").tolist()
        records = []
        missing = days[20]
        for index, day in enumerate(days):
            if day == missing:
                records.append({"date": day, "status": "DATA_GAP_DELIVERY_OR_SCHEMA", "rows": []})
                continue
            rows = []
            for asset in economics.ASSETS:
                rows.append(
                    {
                        "date": day,
                        "asset": asset,
                        "ticker": f"{asset}Q25",
                        "trade_count": 100.0 + index,
                        "volume": 1000.0 + index,
                        "volume_source": "FinInstrmQty",
                        "oi": 10000.0,
                        "open": 100.0,
                        "low": 99.0,
                        "high": 102.0,
                        "close": 101.0,
                    }
                )
            records.append({"date": day, "status": "PASS", "rows": rows})

        daily = economics.daily_table_from_records(days, records)
        following = daily[(daily["date"] == days[21]) & (daily["asset"] == "WIN")].iloc[0]

        self.assertTrue(np.isnan(following["d_trade_count"]))
        self.assertTrue(np.isnan(following["z_trade_count"]))


class H120H129ShardedIngestionTests(unittest.TestCase):
    def minimal_plan(self, days):
        payload = {
            "schema": guarded.PLAN_SCHEMA,
            "cutoff_exclusive": economics.CUTOFF,
            "source_repo": economics.b.SOURCE_REPO,
            "source_commit": economics.b.SOURCE_COMMIT,
            "intraday_encoding": guarded.INTRADAY_ENCODING,
            "intraday_sources": [],
            "discovery_sessions": days,
            "replication_sessions": [],
            "requested_days": days,
            "discovery_sync_sessions": len(days),
            "replication_sync_sessions": 0,
            "discovery_median_common_bar_coverage": 1.0,
            "replication_median_common_bar_coverage": 0.0,
            "provider": "B3",
            "daily_source": "BVBG.086.01 full PriceReport PR{YYMMDD}.zip",
            "contract_identity_regex": economics.FUTURE_RE.pattern,
            "xml_member_selection": economics.XML_MEMBER_SELECTION,
            "economics_run": False,
            "orders": 0,
            "real_capital": 0,
            "engine_feed": False,
            "not_approved": True,
        }
        payload["plan_sha256"] = guarded.canonical_sha(payload)
        return payload

    def gap_record(self, day):
        compact = day[2:4] + day[5:7] + day[8:10]
        return {
            "date": day,
            "status": "DATA_GAP_DELIVERY_OR_SCHEMA",
            "rows": [],
            "url": economics.BASE.format(date=compact),
            "attempt_errors": [{"attempt": 3, "error": "Timeout: expected fixture"}],
            "error": "Timeout: expected fixture",
        }

    def test_chunk_reassembly_requires_exact_dates_and_hashes(self):
        days = ["2025-01-02", "2025-01-03", "2025-01-06", "2025-01-07"]
        plan = self.minimal_plan(days)
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for shard in range(2):
                selected = days[shard::2]
                records = [self.gap_record(day) for day in selected]
                payload = {
                    "schema": guarded.CHUNK_SCHEMA,
                    "request_plan_sha256": plan["plan_sha256"],
                    "shard_index": shard,
                    "shard_count": 2,
                    "dates": selected,
                    "records": records,
                    "records_sha256": guarded.canonical_sha(records),
                }
                guarded.write_json(root / f"B3_H120_H129_DAILY_CHUNK_{shard}.json", payload)

            records, provenance = guarded.load_chunks(plan, root)
            self.assertEqual([record["date"] for record in records], days)
            self.assertEqual(len(provenance), 2)

            path = root / "B3_H120_H129_DAILY_CHUNK_1.json"
            tampered = json.loads(path.read_text()); tampered["records"][0]["error"] = "changed"
            guarded.write_json(path, tampered)
            with self.assertRaisesRegex(RuntimeError, "CHUNK_RECORD_HASH_MISMATCH"):
                guarded.load_chunks(plan, root)

    def test_pinned_intraday_csv_is_decoded_as_latin1_and_hashed(self):
        raw = (
            "Ativo;Data;Hora;Abertura;Máximo;Mínimo;Fechamento;Volume;Quantidade\n"
            "WINFUT;02/01/2025;09:00:00;100;101;99;100,5;10;20\n"
        ).encode("latin-1")
        response = FakeResponse(raw)

        with mock.patch.object(guarded.requests, "get", return_value=response):
            frame, provenance = guarded.pinned_intraday_load("WIN", "2024_26", 5)

        self.assertEqual(len(frame), 1)
        self.assertEqual(provenance["encoding"], "latin-1")
        self.assertEqual(provenance["raw_sha256"], economics.hashlib.sha256(raw).hexdigest())


if __name__ == "__main__":
    unittest.main()
