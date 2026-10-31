import copy,csv,hashlib,io,json,unittest
from decimal import Decimal
from tools import gate_btc_dynamics_target_intake as m
from tools import gate_btc_dynamics_spot_accounting as book

CREATED="2026-11-01T00:00:00Z"
AVAILABLE="2026-11-01T00:01:00Z"
NOW="2026-11-01T00:02:00Z"

def enc(x):return json.dumps(x,sort_keys=True).encode()
def csvbytes(columns,rows):
    s=io.StringIO();w=csv.writer(s);w.writerow(columns);w.writerows(rows);return s.getvalue().encode()


class TargetIntakeTests(unittest.TestCase):
    def source(self):
        comps=[];profiles=[]
        for name in sorted(m.SPOT|m.DERIVATIVES):
            if name in m.SPOT:
                comps.extend([[name,"AAA",".5"],[name,"CASH",".5"]])
                profiles.append([name,"1","0","1","1","weekly"])
            else:
                comps.extend([[name,"AAA",".5"],[name,"BBB","-.5"]])
                profiles.append([name,".5",".5","0","1","weekly_or_risk_trigger"])
        source={
          m.FILES[0]:enc(dict(version="QOS_V2A1_GATEWAY_SCANNER_0.10",
            mode="public_data_no_api_key_no_orders",technical_status="PASS",
            operational_status="NOT_APPROVED",retrospective_performance_status="PROHIBITED_CURRENT_COMPOSITION",
            snapshot_status="SNAPSHOT_USABLE_RESEARCH_ONLY",run_utc=CREATED,data_as_of="2026-11-01")),
          m.FILES[1]:enc(dict(snapshot_status="SNAPSHOT_USABLE_RESEARCH_ONLY")),
          m.FILES[2]:csvbytes(["strategy","asset","weight"],comps),
          m.FILES[3]:csvbytes(["strategy","gross_long","gross_short_abs","net_exposure","gross_exposure","recommended_rebalance"],profiles)}
        snapshot=dict(schema="gate_btc.gateway_dynamics_prospective_snapshot.v1",technical_status="PASS",
            ledger_eligible=True,research_only=True,shadow_only=True,operational_status="NOT_APPROVED",
            orders_generated=0,real_capital_used=0,retrospective_performance_status="PROHIBITED_CURRENT_COMPOSITION",
            snapshot_sha256="a"*64,sequence=1,created_at_utc=CREATED,data_as_of="2026-11-01",
            source_artifacts={k:hashlib.sha256(v).hexdigest() for k,v in source.items()})
        pointer=dict(research_only=True,operational_status="NOT_APPROVED",orders_generated=0,
            real_capital_used=0,run_id=42,branch="main",head_sha="b"*40,published_at_utc=AVAILABLE,data_cutoff="2026-10-31")
        return snapshot,source,pointer
    def admit(self,s=None,files=None,p=None,**kw):
        a,b,c=self.source();args=dict(snapshot_raw=enc(s or a),source_files=files or b,
            pointer_raw=enc(p or c),producer_run_id=42,now_utc=NOW);args.update(kw)
        return m.admit(**args)
    def rehash(self,s,files):
        s["source_artifacts"]={k:hashlib.sha256(v).hexdigest() for k,v in files.items()}

    def test_exact_file_proof_and_three_targets_five_derivative_profiles(self):
        out=self.admit()
        self.assertEqual(sum(v["spot_target_weights"] is not None for v in out["profiles"].values()),3)
        self.assertEqual(out["profiles_activated"],0)
        self.assertEqual(out["economic_observations_created"],0)
        self.assertEqual(out["scanner_data_as_of"],"2026-11-01")
        self.assertEqual(out["producer_market_cutoff"],"2026-10-31")
        self.assertEqual(out["source_available_at_utc"],AVAILABLE)
        self.assertEqual(m.spot_weights(out,"Dynamic_Defense"),{"AAA":"0.5","CASH":"0.5"})

    def test_publication_is_not_silently_replaced_by_capture_clock(self):
        s,files,p=self.source()
        with self.assertRaisesRegex(ValueError,"publication"):
            self.admit(s,files,p,now_utc="2026-11-01T00:00:30Z")
        self.assertEqual(self.admit()["source_created_at_utc"],CREATED)

    def test_changed_file_rejected_before_targets_are_admitted(self):
        s,files,p=self.source();files[m.FILES[2]]+=b"\n"
        with self.assertRaisesRegex(ValueError,"hash mismatch"):self.admit(s,files,p)
        with self.assertRaisesRegex(ValueError,"producer run mismatch"):self.admit(producer_run_id=43)

    def test_duplicate_asset_and_unknown_profile_rejected_even_if_rehashed(self):
        for mode in ["duplicate","unknown"]:
            s,files,p=self.source()
            files[m.FILES[2]]+=(b"QOS_Base,AAA,.1\n" if mode=="duplicate" else b"Unreviewed,AAA,1\n")
            self.rehash(s,files)
            with self.assertRaises(ValueError):self.admit(s,files,p)

    def test_nonfinite_and_short_spot_weights_rejected(self):
        for value in ["NaN","-.5"]:
            s,files,p=self.source()
            files[m.FILES[2]]=files[m.FILES[2]].replace(b"QOS_Base,AAA,.5",("QOS_Base,AAA,"+value).encode())
            self.rehash(s,files)
            with self.assertRaises(ValueError):self.admit(s,files,p)

    def test_numeric_dust_only_goes_to_cash_and_is_disclosed(self):
        s,files,p=self.source()
        files[m.FILES[2]]=files[m.FILES[2]].replace(b"QOS_Base,AAA,.5",b"QOS_Base,AAA,.50000000000000001")
        self.rehash(s,files);out=self.admit(s,files,p);q=out["profiles"]["QOS_Base"]
        self.assertEqual(Decimal(q["cash_numeric_correction"]),Decimal("-1e-17"))
        self.assertEqual(Decimal(q["spot_target_weights"]["AAA"]),Decimal(".50000000000000001"))
        self.assertEqual(sum(map(Decimal,q["spot_target_weights"].values())),1)

    def test_material_missing_allocation_is_not_invented_cash(self):
        s,files,p=self.source()
        files[m.FILES[2]]=files[m.FILES[2]].replace(b"QOS_Base,AAA,.5",b"QOS_Base,AAA,.4")
        files[m.FILES[3]]=files[m.FILES[3]].replace(b"QOS_Base,1,0,1,1",b"QOS_Base,.9,0,.9,.9")
        self.rehash(s,files)
        with self.assertRaisesRegex(ValueError,"allocation residual"):self.admit(s,files,p)

    def test_source_fixture_and_profile_total_mismatch_rejected(self):
        for mode in ["fixture","totals"]:
            s,files,p=self.source()
            if mode=="fixture":
                x=json.loads(files[m.FILES[0]]);x["mode"]="offline_fixture_no_network";files[m.FILES[0]]=enc(x)
            else:files[m.FILES[3]]=files[m.FILES[3]].replace(b"QOS_Base,1,0,1,1",b"QOS_Base,.8,0,.8,.8")
            self.rehash(s,files)
            with self.assertRaises(ValueError):self.admit(s,files,p)

    def test_target_hash_and_derivative_separation_preserved(self):
        out=self.admit()
        for name in m.DERIVATIVES:
            with self.assertRaisesRegex(ValueError,"derivative"):m.spot_weights(out,name)
        out["profiles"]["QOS_Base"]["spot_target_weights"]["CASH"]="0"
        with self.assertRaisesRegex(ValueError,"admission changed"):m.spot_weights(out,"QOS_Base")

    def test_explicit_binding_reaches_rebalancer_and_chains_source_identity(self):
        out=self.admit();name="Dynamic_Defense"
        instrument=book.SpotInstrument("AAA","SYNTHETIC_ASSET","TEST","AAAUSD","USD","1","0","0")
        protocol=book.SpotProtocol("GATE_BTC_DYNAMICS_SPOT_"+name+"_V1","USD","2026-11-01T00:00:00Z","1000",60,(instrument,))
        initial=book.genesis(protocol)
        state,r=m.rebalance_admitted(initial,protocol,out,name,rebalance_id="bound",
            quotes={"AAA":book.Mark("100","2026-11-01T00:01:01Z","c"*64)},executed_at_utc=NOW)
        self.assertEqual(dict(state.positions),{"AAA":Decimal(5)});self.assertEqual(state.cash,500)
        self.assertEqual(r["source_profile"],name)
        self.assertEqual(r["source_admission_sha256"],out["admission_sha256"])
        self.assertEqual(state.chain_sha256,book.digest({k:v for k,v in r.items() if k!="chain_sha256"}))
        self.assertFalse(r["production_activation"])
        with self.assertRaisesRegex(ValueError,"exact profile"):
            m.rebalance_admitted(initial,protocol,out,"QOS_Base",rebalance_id="wrong",
                quotes={},executed_at_utc=NOW)
        with self.assertRaisesRegex(ValueError,"quote must follow"):
            m.rebalance_admitted(initial,protocol,out,name,rebalance_id="early",
                quotes={"AAA":book.Mark("100","2026-11-01T00:00:30Z","c"*64)},executed_at_utc=NOW)
        self.assertEqual(initial,book.genesis(protocol))

    def test_duplicate_json_fields_and_csv_headers_rejected(self):
        with self.assertRaises(ValueError):m.parse_json(b'{"a":1,"a":2}')
        with self.assertRaises(ValueError):m.table(b"asset,asset\nA,B\n",["asset"])

    def test_admission_is_idempotent_without_new_observation_credit(self):
        a=self.admit();z=self.admit(now_utc="2026-11-01T00:03:00Z")
        self.assertEqual(a["admission_sha256"],z["admission_sha256"])
        self.assertEqual(a["economic_observations_created"],0)


if __name__=="__main__":unittest.main()
