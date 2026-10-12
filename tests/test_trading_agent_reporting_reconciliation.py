import unittest
from trading_agent.report import _performance_table, build_report, _price, _money, _positions_table, _trades_table
from copy import deepcopy

class AgentReportTests(unittest.TestCase):
    def result(self):
        entry={'nav':56613.27,'benchmark_nav':59545.0,'benchmark2_nav':51140.0}
        state={'currency':'BRL','initial_capital':50000.0,'inception_date':'2026-08-06','cash':-1238.29,'positions':{'BOVA11':{'qty':59679.34/205.55,'avg_cost':205.55}},'history':[entry]}
        return {'state':state,'entry':entry,'prices':{'BOVA11':205.55},'regime':'-'}
    def test_fixed_cdi_goal_and_ibov_context(self):
        report=build_report('2026-10-10',{'b3_estruturadas':self.result()}, {})
        self.assertIn('Alfa vs objetivo (CDI)',report)
        self.assertIn('+10.95%',report)
        self.assertIn('IBOV (comparador informativo)',report)
        self.assertNotIn('Alfa vs o maior',report)
        self.assertIn('Caixa negativo',report)
        self.assertIn('obrigacao da call R$ 1,827.78',report)
    def test_subcent_quote_preserves_precision_while_money_keeps_cents(self):
        self.assertEqual(_price(0.002018,'USD'),'$0.002018')
        self.assertEqual(_price(1e-14,'USD'),'$1e-14')
        self.assertEqual(_price(0,'USD'),'$0.00')
        self.assertEqual(_price(171.82,'USD'),'$171.82')
        self.assertEqual(_money(8365.19,'USD'),'$8,365.19')

    def test_positions_format_small_quotes_without_mutating_state(self):
        state={'positions':{'ONE':{'qty':1000,'avg_cost':0.002018}}}
        before=deepcopy(state)
        rows=_positions_table(state,{'ONE':0.002018},10,'USD')
        self.assertTrue(any('$0.002018' in row and '$2.02' in row for row in rows))
        self.assertEqual(state,before)

    def test_trades_use_quote_precision_without_mutating_trade(self):
        trades=[{'symbol':'ONE','side':'buy','qty':1000,'price':0.002018,'value':2.018}]
        before=deepcopy(trades)
        rows=_trades_table(trades,'USD')
        self.assertTrue(any('$0.002018' in row and '$2.02' in row for row in rows))
        self.assertEqual(trades,before)

    def test_directional_b3_keeps_larger_hurdle(self):
        r=self.result()
        rows=_performance_table(r['state'],r['entry'],'IBOV','CDI','-')
        self.assertTrue(any('Alfa vs o maior (IBOV)' in s for s in rows))
        self.assertFalse(any('objetivo (CDI)' in s for s in rows))

if __name__=='__main__':unittest.main()
