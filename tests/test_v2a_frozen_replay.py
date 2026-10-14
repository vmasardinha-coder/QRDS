import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from tools.v2a_frozen_replay import _load_source


class V2AFrozenReplaySafetyTests(unittest.TestCase):
    def _source(
        self,
        path: Path,
        *,
        operational_status: str = "NOT_APPROVED",
        orders: int = 0,
        extension_count: int = 0,
        trace: dict | None = None,
        with_drv: bool = False,
        drv_source: str = "gate",
    ) -> None:
        manifest = {
            "technical_status": "PASS",
            "operational_status": operational_status,
            "real_orders": orders,
            "capital_used": 0,
            "qualified_source_extension": extension_count,
        }
        with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.writestr(
                "data/processed/qos_v2a_master_daily.csv",
                "date,symbol,close_usd,volume_usd,source\n2026-07-31,BTC,1,1,test\n" +
                (f"2026-07-31,DRV,2,3,{drv_source}\n" if with_drv else ""),
            )
            archive.writestr(
                "data/raw/coingecko_current_universe_v04.csv",
                "symbol\nBTC\n",
            )
            archive.writestr(
                "outputs/download_failures_v2a.csv",
                "symbol,error\n",
            )
            archive.writestr(
                "outputs/v2a_run_manifest.json",
                json.dumps(manifest),
            )
            if trace is not None:
                archive.writestr("outputs/source_attempts_v2a.json",json.dumps(trace))

    def test_safe_source_is_admitted(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            package = Path(directory) / "safe.zip"
            self._source(package)
            loaded = _load_source(package)
            self.assertEqual(loaded["run_manifest"]["operational_status"], "NOT_APPROVED")
            self.assertEqual(len(loaded["member_hashes"]), 3)

    def test_operational_source_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            package = Path(directory) / "unsafe.zip"
            self._source(package, operational_status="APPROVED", orders=1)
            with self.assertRaisesRegex(RuntimeError, "operational status"):
                _load_source(package)

    def test_corrupt_source_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            package = Path(directory) / "corrupt.zip"
            package.write_bytes(b"not-a-zip")
            with self.assertRaises(zipfile.BadZipFile):
                _load_source(package)

    def test_extension_trace_survives_without_changing_price_hashes(self):
        trace={"qualified_extension_selected_count":1,"rows":[{"symbol":"DRV","qualified_extension_attempt":{"status":"SELECTED","source":"gate"}}]}
        with tempfile.TemporaryDirectory()as directory:
            legacy=Path(directory)/"legacy.zip";extended=Path(directory)/"extended.zip"
            self._source(legacy,with_drv=True);self._source(extended,extension_count=1,trace=trace,with_drv=True)
            old,new=_load_source(legacy),_load_source(extended)
            self.assertEqual(old["member_hashes"],new["member_hashes"])
            self.assertEqual(new["qualified_source_extension"],1)
            self.assertEqual(json.loads(new["source_trace_raw"]),trace)

    def test_bitget_extension_round_trip_preserves_hashes_and_rejects_mismatch(self):
        trace={'qualified_extension_selected_count':1,'rows':[{'symbol':'DRV','qualified_extension_attempt':{'status':'SELECTED','source':'bitget'}}]}
        with tempfile.TemporaryDirectory() as directory:
            legacy=Path(directory)/'legacy.zip';extended=Path(directory)/'extended.zip'
            self._source(legacy,with_drv=True,drv_source='bitget')
            self._source(extended,with_drv=True,drv_source='bitget',extension_count=1,trace=trace)
            old,new=_load_source(legacy),_load_source(extended)
            self.assertEqual(old['member_hashes'],new['member_hashes'])
            self.assertEqual(json.loads(new['source_trace_raw']),trace)
            self._source(extended,with_drv=True,drv_source='gate',extension_count=1,trace=trace)
            with self.assertRaisesRegex(RuntimeError,'trace/master'):_load_source(extended)
            trace['rows'][0]['qualified_extension_attempt']['source']='unverified'
            self._source(extended,with_drv=True,drv_source='unverified',extension_count=1,trace=trace)
            with self.assertRaisesRegex(RuntimeError,'trace/master'):_load_source(extended)

    def test_deribit_extension_is_bound_to_master_provider(self):
        trace={'qualified_extension_selected_count':1,'rows':[{'symbol':'DRV','qualified_extension_attempt':{'status':'SELECTED','source':'deribit'}}]}
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'deribit.zip'
            self._source(path,with_drv=True,drv_source='deribit',extension_count=1,trace=trace)
            self.assertEqual(_load_source(path)['qualified_source_extension'],1)
            self._source(path,with_drv=True,drv_source='gate',extension_count=1,trace=trace)
            with self.assertRaisesRegex(RuntimeError,'trace/master'):_load_source(path)

    def test_extension_missing_mismatched_or_duplicate_trace_is_rejected(self):
        bad=[None,{"qualified_extension_selected_count":0,"rows":[]},
             {"qualified_extension_selected_count":2,"rows":[{"symbol":"DRV","qualified_extension_attempt":{"status":"SELECTED"}}]*2}]
        with tempfile.TemporaryDirectory()as directory:
            for i,trace in enumerate(bad):
                path=Path(directory)/f"bad{i}.zip"
                self._source(path,extension_count=2 if i==2 else 1,trace=trace)
                with self.assertRaises(RuntimeError):_load_source(path)

    def test_source_trace_cannot_claim_missing_asset_or_wrong_provider(self):
        with tempfile.TemporaryDirectory()as directory:
            for source,with_drv in [("gate",False),("mexc",True)]:
                path=Path(directory)/f"bad-{source}-{with_drv}.zip"
                trace={"qualified_extension_selected_count":1,"rows":[{"symbol":"DRV","qualified_extension_attempt":{"status":"SELECTED","source":source}}]}
                self._source(path,extension_count=1,trace=trace,with_drv=with_drv)
                with self.assertRaisesRegex(RuntimeError,"trace/master"):_load_source(path)

    def test_manifest_cannot_silently_drop_a_used_extension(self):
        with tempfile.TemporaryDirectory()as directory:
            path=Path(directory)/"omitted.zip"
            trace={"qualified_extension_selected_count":1,"rows":[{"symbol":"DRV","qualified_extension_attempt":{"status":"SELECTED","source":"gate"}}]}
            self._source(path,extension_count=0,trace=trace,with_drv=True)
            with self.assertRaisesRegex(RuntimeError,"omitted"):_load_source(path)


if __name__ == "__main__":
    unittest.main()

