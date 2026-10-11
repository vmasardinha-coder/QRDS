import copy
import hashlib
import json
import tempfile
import unittest
from datetime import datetime,timezone
from pathlib import Path
from unittest.mock import patch
from tools.gate_btc_factory import crypto_forward_public_capture as capture
from tools.gate_btc_factory.crypto_forward_source_admission import REQUIRED,evaluate,packet_evidence


def seal(packet):
    packet["packet_sha256"]=hashlib.sha256(json.dumps({k:v for k,v in packet.items() if k!="packet_sha256"},sort_keys=True,separators=(",",":")).encode()).hexdigest()
    return packet


def packet(bucket,delay=120):
    records=[]
    for venue,asset,market in sorted(REQUIRED):
        symbol=(asset+"USDT" if venue=="BINANCE" else asset+"-USD" if venue=="COINBASE" else asset+"-USDT"+("-SWAP" if market in ("PERPETUAL","FUNDING") else ""))
        r={"venue":venue,"asset":asset,"market":market,"symbol":symbol,"raw_sha256":"a"*64}
        if market=="FUNDING":r["funding_rate"]="0.0001"
        else:r["bar"]={"start_ms":bucket,"open":"20","high":"21","low":"19","close":"20","volume":"1"}
        records.append(r)
    return seal({"schema":"qrds.factory.crypto_forward_capture.v1","scientific_credit":0,"historical_backfill_credit":0,"economics_feedback_allowed":False,"status":"COMPLETE_PROSPECTIVE_PACKET","record_count":14,"required_record_count":14,"errors":[],
                 "records":records,"captured_at_utc":datetime.fromtimestamp((bucket+300000)/1000+delay,timezone.utc).isoformat(),
                 "safety":{"ORDERS":0,"REAL_CAPITAL":0,"ENGINE_FEED":False,"RESEARCH_ONLY":True,"SHADOW_ONLY":True,"NOT_APPROVED":True}})


class FullSourceAdmissionTests(unittest.TestCase):
    bucket=1767225600000

    def admission(self,packets):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            for i,p in enumerate(packets):(root/f"{len(packets)-i:03d}.json").write_text(json.dumps(p))
            before={p.name:p.read_bytes() for p in root.glob("*.json")}
            result=evaluate(root)
            self.assertEqual(before,{p.name:p.read_bytes() for p in root.glob("*.json")})
            return result

    def test_status_text_alone_cannot_admit(self):
        result=self.admission([{"status":"COMPLETE_PROSPECTIVE_PACKET"}]*3)
        self.assertFalse(result["source_admitted_forward_only"])
        self.assertEqual(result["complete_consecutive_streak"],0)

    def test_frozen_delay_boundary(self):
        self.assertEqual(packet_evidence(packet(self.bucket,119))[2],"FROZEN_CAPTURE_DELAY_NOT_MET")
        self.assertTrue(packet_evidence(packet(self.bucket,120))[0])

    def test_three_distinct_consecutive_valid_buckets_admit_source_only(self):
        result=self.admission([packet(self.bucket+i*300000) for i in range(3)])
        self.assertTrue(result["source_admitted_forward_only"])
        self.assertEqual(result["complete_consecutive_streak"],3)
        self.assertFalse(result["promotion_allowed"])
        self.assertFalse(result["economics_read"])
        self.assertEqual(result["orders"],0)
        self.assertEqual(result["real_capital"],0)

    def test_duplicate_bucket_does_not_create_continuity(self):
        self.assertFalse(self.admission([packet(self.bucket)]*3)["source_admitted_forward_only"])

    def test_gap_or_incomplete_latest_resets_streak(self):
        self.assertFalse(self.admission([packet(self.bucket+i*600000) for i in range(3)])["source_admitted_forward_only"])
        packets=[packet(self.bucket+i*300000) for i in range(3)]
        packets[-1]["status"]="INCOMPLETE_FAIL_CLOSED"
        self.assertEqual(self.admission(packets)["complete_consecutive_streak"],0)

    def test_hash_roles_funding_and_instrument_are_verified(self):
        p=packet(self.bucket)
        p["records"][0]["symbol"]="OTHER"
        self.assertEqual(packet_evidence(p)[2],"PACKET_HASH_MISMATCH")
        self.assertEqual(packet_evidence(seal(p))[2],"INSTRUMENT_IDENTITY_MISMATCH")
        p=packet(self.bucket);p["records"][-1]=copy.deepcopy(p["records"][0])
        self.assertEqual(packet_evidence(seal(p))[2],"REQUIRED_ROLES_MISMATCH")
        p=packet(self.bucket)
        next(r for r in p["records"] if r["market"]=="FUNDING")["funding_rate"]=None
        self.assertFalse(packet_evidence(seal(p))[0])

    def test_all_bar_buckets_and_raw_hashes_are_verified(self):
        p=packet(self.bucket)
        next(r for r in p["records"] if "bar" in r)["bar"]["start_ms"]+=300000
        self.assertEqual(packet_evidence(seal(p))[2],"BAR_BUCKET_MISMATCH")
        p=packet(self.bucket);p["records"][0]["raw_sha256"]=""
        self.assertEqual(packet_evidence(seal(p))[2],"RAW_HASH_MISSING")

    def test_clock_delay_is_opt_in_for_full_frontier(self):
        with patch.object(capture.time,"time",return_value=7201):
            self.assertEqual(capture.completed_cutoff(),6900)
            self.assertEqual(capture.completed_cutoff(120),6600)
        with patch.object(capture.time,"time",return_value=7320):
            self.assertEqual(capture.completed_cutoff(120),6900)


if __name__=="__main__":
    unittest.main()
