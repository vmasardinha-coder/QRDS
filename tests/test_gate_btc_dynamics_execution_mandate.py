import copy,hashlib,json,unittest
from dataclasses import replace
import test_gate_btc_dynamics_source_costs as cost_fixture
import test_gate_btc_dynamics_spot_market_audit as market_fixture
from tools import gate_btc_dynamics_execution_mandate as m
from tools import gate_btc_dynamics_source_costs as cost
from tools import gate_btc_dynamics_spot_accounting as book
from tools import gate_btc_dynamics_market_checked_rebalance as checked


class MandateTests(unittest.TestCase):
    def setUp(self):
        helper=cost_fixture.SourceCostsTests();self.admission,raw=helper.prepare()
        archive=helper.archive();self.cost=cost.audit_costs(archive,hashlib.sha256(archive).hexdigest(),raw,self.admission)
        i=book.SpotInstrument('AAA','BINANCE:SPOT:AAAUSDT','BINANCE','AAAUSDT','USDT','.1','6.0','8.0')
        self.protocol=book.SpotProtocol('GATE_BTC_DYNAMICS_SPOT_QOS_Base_V1','USDT',
            '2026-11-01T00:00:00Z','1000',120,(i,))
        self.state=book.genesis(self.protocol)
        self.fixture=market_fixture.MarketAuditTests();self.fixture.setUp();self.fixture.admission=self.admission
        self.audit=self.fixture.run_audit(max_metadata_age_seconds=600)
        self.quotes={'AAA':book.Mark('10','2026-11-01T00:05:00Z','d'*64)}
        self.refs={'AAA':checked.NotionalReference('AAA','BINANCE:SPOT:AAAUSDT','USDT','10',
            '2026-11-01T00:05:00Z','e'*64,'VWAP',5,'NULL_CONFIRMED','f'*64)}
        self.policy=dict(schema=m.SCHEMA,mandate_id='independent_fixture',profile='QOS_Base',
            protocol_sha256=self.protocol.sha256,target_admission_sha256=self.admission['admission_sha256'],
            cost_audit_sha256=self.cost['cost_audit_sha256'],published_at_utc='2026-11-01T00:02:00Z',
            calendar=[dict(slot_id='one',opens_at_utc='2026-11-01T00:05:00Z',closes_at_utc='2026-11-01T00:07:00Z'),
                      dict(slot_id='two',opens_at_utc='2026-11-01T00:07:00Z',closes_at_utc='2026-11-01T00:20:00Z')],
            minimum_hold_seconds=180,maximum_target_age_seconds=3600,maximum_metadata_age_seconds=300,
            cash_currency='USDT',cash_policy='NONINTEREST_BEARING_NO_FX_NO_BORROWING',
            cost_policy='PER_FILL_SOURCE_FEE_SLIPPAGE_NO_EXTRA_DAILY_DRAG',
            stop_policy='NO_STOP_IN_THIS_EXPLICIT_MANDATE',decision_policy='PREAUTHORIZED_EXACT_TARGET_ONLY',
            precedence=m.PRECEDENCE.copy(),research_only=True,production_activation=False,orders=0,real_capital=0)
    def args(self):
        raw=json.dumps(self.policy,sort_keys=True).encode()
        return dict(state=self.state,protocol=self.protocol,admission=self.admission,audit=self.audit,
            cost_audit=self.cost,mandate_raw=raw,expected_mandate_sha256=hashlib.sha256(raw).hexdigest(),
            mandate_available_at_utc=self.policy['published_at_utc'],slot_id='one',quotes=self.quotes,
            notional_references=self.refs,executed_at_utc='2026-11-01T00:06:00Z')
    def run_mandate(self,**kwargs):
        args=self.args();args.update(kwargs);return m.rebalance_mandated(**args)
    def test_one_atomic_rebalance_preserves_policy_source_and_no_economic_credit(self):
        old=self.state;state,receipt=self.run_mandate()
        self.assertEqual(self.state,old);self.assertEqual(receipt['used_slot_ids'],['one'])
        self.assertEqual(receipt['state_after'],m._state_fields(state))
        self.assertEqual(state.chain_sha256,receipt['chain_sha256'])
        self.assertEqual(book.digest({k:v for k,v in receipt.items() if k!='chain_sha256'}),state.chain_sha256)
        self.assertEqual(receipt['orders'],0);self.assertEqual(receipt['economic_observations_created'],0)
        self.assertGreater(state.cash,book.number('500'))
    def test_no_missing_field_becomes_a_default(self):
        for key in ['calendar','stop_policy','cash_policy','precedence','minimum_hold_seconds']:
            saved=self.policy.pop(key)
            with self.assertRaisesRegex(ValueError,'schema required'):self.run_mandate()
            self.policy[key]=saved
    def test_changed_bytes_and_duplicate_json_fields_block(self):
        with self.assertRaisesRegex(ValueError,'bytes changed'):self.run_mandate(expected_mandate_sha256='a'*64)
        raw=self.args()['mandate_raw'];raw=raw[:-1]+b',"orders":0}'
        with self.assertRaisesRegex(ValueError,'duplicate JSON'):
            self.run_mandate(mandate_raw=raw,expected_mandate_sha256=hashlib.sha256(raw).hexdigest())
    def test_half_open_window_including_open_excluding_close(self):
        self.run_mandate(executed_at_utc='2026-11-01T00:05:00Z')
        for clock in ['2026-11-01T00:04:59Z','2026-11-01T00:07:00Z']:
            with self.assertRaisesRegex(ValueError,'execution window'):self.run_mandate(executed_at_utc=clock)
    def test_unknown_slot_or_weekly_label_is_not_executable(self):
        with self.assertRaisesRegex(ValueError,'not preregistered'):self.run_mandate(slot_id='weekly')
        self.policy['calendar']='weekly'
        with self.assertRaisesRegex(ValueError,'UTC calendar'):self.run_mandate()
    def test_late_or_pre_source_policy_blocks(self):
        for clock in ['2026-11-01T00:00:30Z','2026-11-01T00:05:00Z']:
            self.policy['published_at_utc']=clock
            with self.assertRaises(ValueError):self.run_mandate()
        self.policy['published_at_utc']='2026-11-01T00:02:00Z'
        with self.assertRaisesRegex(ValueError,'availability mismatch'):
            self.run_mandate(mandate_available_at_utc='2026-11-01T00:02:01Z')
    def test_duration_bool_zero_negative_and_float_rejected(self):
        for key,value in [('minimum_hold_seconds',True),('minimum_hold_seconds',-1),
                          ('maximum_target_age_seconds',0),('maximum_metadata_age_seconds',300.0)]:
            original=self.policy[key];self.policy[key]=value
            with self.assertRaisesRegex(ValueError,'integer duration'):self.run_mandate()
            self.policy[key]=original
    def test_no_unsupported_stop_or_inferred_persistence_or_extra_daily_drag(self):
        for key,value in [('stop_policy','STOP_AT_2SIGMA'),('decision_policy','weekly_or_persistence'),
                          ('precedence',list(reversed(m.PRECEDENCE))),
                          ('cash_policy','EARN_INTEREST'),('cost_policy','ADD_DAILY_DRAG')]:
            old=self.policy[key];self.policy[key]=value
            with self.assertRaisesRegex(ValueError,'unsupported policy'):self.run_mandate()
            self.policy[key]=old
    def test_currency_conversion_and_protocol_cost_changes_block(self):
        self.policy['cash_currency']='USD'
        with self.assertRaisesRegex(ValueError,'no USD equivalence'):self.run_mandate()
        self.policy['cash_currency']='USDT'
        p=replace(self.protocol,instruments=(replace(self.protocol.instruments[0],fee_bps_per_side='0'),))
        self.policy['protocol_sha256']=p.sha256
        with self.assertRaisesRegex(ValueError,'costs do not match'):
            self.run_mandate(state=book.genesis(p),protocol=p)
    def test_overlapping_duplicate_and_backward_calendar_blocks(self):
        for change in [dict(slot_id='one'),dict(opens_at_utc='2026-11-01T00:06:59Z'),
                       dict(closes_at_utc='2026-11-01T00:06:00Z')]:
            old=self.policy['calendar'][1].copy();self.policy['calendar'][1].update(change)
            with self.assertRaises(ValueError):self.run_mandate()
            self.policy['calendar'][1]=old
    def test_stale_target_not_renewed_by_recent_policy(self):
        self.policy['maximum_target_age_seconds']=60
        with self.assertRaisesRegex(ValueError,'target outside'):self.run_mandate()
    def second_args(self,state,receipt):
        return dict(state=state,previous_receipt=receipt,slot_id='two',
            executed_at_utc='2026-11-01T00:09:00Z',
            quotes={'AAA':replace(self.quotes['AAA'],price='11',at_utc='2026-11-01T00:08:00Z')},
            notional_references={'AAA':replace(self.refs['AAA'],price='11',at_utc='2026-11-01T00:08:00Z')},
            audit=self.fixture.run_audit(captured_at_utc='2026-11-01T00:07:00Z',
                now_utc='2026-11-01T00:07:30Z',max_metadata_age_seconds=600))
    def test_minimum_hold_and_chained_second_slot(self):
        state,receipt=self.run_mandate();args=self.second_args(state,receipt)
        args['executed_at_utc']='2026-11-01T00:08:59Z'
        with self.assertRaisesRegex(ValueError,'hold has not elapsed'):self.run_mandate(**args)
        args['executed_at_utc']='2026-11-01T00:09:00Z'
        new,second=self.run_mandate(**args)
        self.assertEqual(second['used_slot_ids'],['one','two'])
        self.assertEqual(second['previous_state_chain_sha256'],state.chain_sha256)
        self.assertEqual(receipt['used_slot_ids'],['one'])
    def test_no_slot_reuse_even_with_new_rebalance_id(self):
        state,receipt=self.run_mandate()
        with self.assertRaisesRegex(ValueError,'already consumed'):
            self.run_mandate(state=state,previous_receipt=receipt)
    def test_non_genesis_state_requires_receipt_and_rejects_tampered_chain(self):
        state,receipt=self.run_mandate();args=self.second_args(state,receipt)
        with self.assertRaisesRegex(ValueError,'requires last mandated'):self.run_mandate(**dict(args,previous_receipt=None))
        bad=copy.deepcopy(receipt);bad['used_slot_ids']=[]
        with self.assertRaisesRegex(ValueError,'chain mismatch'):self.run_mandate(**dict(args,previous_receipt=bad))
        with self.assertRaisesRegex(ValueError,'chain mismatch'):
            self.run_mandate(**dict(args,state=replace(state,cash=state.cash+1)))
    def test_policy_or_target_cannot_be_spliced_into_existing_chain(self):
        state,receipt=self.run_mandate();args=self.second_args(state,receipt)
        self.policy['minimum_hold_seconds']=0
        with self.assertRaisesRegex(ValueError,'chain mismatch'):self.run_mandate(**args)
    def test_market_failure_after_policy_validation_is_atomic(self):
        original=self.state
        with self.assertRaisesRegex(ValueError,'notional reference'):
            self.run_mandate(notional_references={})
        self.assertEqual(self.state,original)

if __name__=='__main__':unittest.main()
