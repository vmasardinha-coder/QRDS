import json
import unittest

from tools.gate_btc_2_v2a_btw_bitget_qualification_runner import parse_payload


def envelope(data):
    return json.dumps({"code":"00000","msg":"success","requestTime":1,"data":data}).encode()


class TestBTWBitgetQualificationRunner(unittest.TestCase):
    def test_parse_payload_known_schema(self):
        rows=parse_payload(envelope([["1704067200000","1","2","0.5","1.5","10","15","15"]]))
        self.assertEqual(rows[0]["day"],"2024-01-01")
        self.assertEqual(rows[0]["open"],1.0)
        self.assertEqual(rows[0]["high"],2.0)
        self.assertEqual(rows[0]["base_volume"],10.0)

    def test_bad_envelope_fails_closed(self):
        with self.assertRaises(ValueError):
            parse_payload(json.dumps({"code":"40000","data":[]}).encode())

    def test_unknown_row_schema_fails_closed(self):
        with self.assertRaises(ValueError):
            parse_payload(envelope([["1","2"]]))

    def test_negative_volume_fails_closed(self):
        with self.assertRaises(ValueError):
            parse_payload(envelope([["1704067200000","1","2","0.5","1.5","-1","15","15"]]))

    def test_bad_ohlc_fails_closed(self):
        with self.assertRaises(ValueError):
            parse_payload(envelope([["1704067200000","1","0.8","0.5","1.5","10","15","15"]]))


if __name__ == "__main__":
    unittest.main()
