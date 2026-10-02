import csv
import hashlib
import io
import tempfile
import unittest
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from tools.gate_btc_qos_selected_source_probe import SYMBOLS, run


class SelectedSourceQualificationTest(unittest.TestCase):
    def test_eight_exact_spot_archives_with_cdd_overlap(self):
        day0 = "2026-09-30"
        day1 = "2026-10-01"
        payload = {}
        for day in (day0, day1):
            millis = int(datetime.fromisoformat(day).replace(tzinfo=timezone.utc).timestamp() * 1000)
            for symbol in SYMBOLS:
                pair = symbol + "USDT"
                url = f"https://data.binance.vision/data/spot/daily/klines/{pair}/1d/{pair}-1d-{day}.zip"
                row = [millis, 1, 2, 1, 2, 10, millis + 86399999, 20, 1, 1, 1, 0]
                buf = io.BytesIO()
                with zipfile.ZipFile(buf, "w") as archive:
                    archive.writestr(pair + ".csv", ",".join(map(str, row)) + "\n")
                raw = buf.getvalue()
                payload[url] = raw
                payload[url + ".CHECKSUM"] = hashlib.sha256(raw).hexdigest().encode()

        with tempfile.TemporaryDirectory() as directory:
            master = Path(directory) / "master.csv"
            with master.open("w", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=["date", "symbol", "source", "close_usd", "volume_usd"])
                writer.writeheader()
                for symbol in SYMBOLS:
                    writer.writerow(dict(date=day0, symbol=symbol, source="cdd", close_usd=2, volume_usd=20))
            result = run(master, day1, payload.__getitem__)
        self.assertEqual(result["status"], "PASS_PHYSICAL_QUALIFICATION")
        self.assertEqual(len(result["current"]), 8)
        self.assertFalse(result["source_admitted_to_existing_epoch"])
        self.assertEqual(result["scientific_credit"], 0)

    def test_missing_selected_archive_cannot_be_admitted(self):
        with tempfile.TemporaryDirectory() as directory:
            master = Path(directory) / "master.csv"
            master.write_text("date,symbol,source,close_usd,volume_usd\n", encoding="utf-8")
            result = run(master, "2026-10-01", lambda url: (_ for _ in ()).throw(FileNotFoundError(url)))
        self.assertEqual(result["status"], "INCOMPLETE_NO_ADMISSION")
        self.assertFalse(result["exact_current_8_of_8"])


if __name__ == "__main__":
    unittest.main()
