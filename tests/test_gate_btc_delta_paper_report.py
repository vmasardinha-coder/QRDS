import json
import statistics
import tempfile
import unittest
from pathlib import Path

from tests.test_gate_btc_delta_paper_monitor import CONTRACT, STRATS, fixture
from tools import gate_btc_delta_paper_monitor as mon
from tools import gate_btc_delta_paper_report as rep


def build_ledger(root: Path, days: tuple[tuple[str, float], ...]) -> Path:
    runtime = root / 'rt'
    for index, (day, ret) in enumerate(days):
        source = root / f'{day}.zip'
        fixture(source, day, ret)
        mon.process(CONTRACT, source, runtime, str(900 + index))
    return runtime


class TestDeltaPaperReport(unittest.TestCase):
    def test_armed_day_renders_without_economic_series(self):
        with tempfile.TemporaryDirectory() as td:
            runtime = build_ledger(Path(td), (('2026-08-13', 0.0),))
            target = rep.render(runtime)
            page = target.read_text(encoding='utf-8')
            self.assertIn('ARMED_WAITING_FIRST_RETURN', page)
            self.assertIn('Sem retornos prospectivos ainda', page)
            for name in STRATS:
                self.assertIn(name, page)

    def test_full_report_carries_charts_positions_and_movements(self):
        with tempfile.TemporaryDirectory() as td:
            runtime = build_ledger(Path(td), (
                ('2026-08-13', 0.0), ('2026-08-14', 0.01), ('2026-08-15', -0.02),
            ))
            page = rep.render(runtime).read_text(encoding='utf-8')
            self.assertIn('ACTIVE_PROSPECTIVE_PAPER_SHADOW', page)
            # One polyline per book on each of the two time-series charts.
            self.assertEqual(page.count("class='series-line'"), len(STRATS) * 2)
            self.assertEqual(page.count("class='bar'"), len(STRATS))
            self.assertIn('Posicoes simuladas em aberto', page)
            self.assertIn('Movimentacoes simuladas do dia', page)
            self.assertIn('Selecoes com execucao teorica', page)
            # Legend plus direct end labels: identity never rests on colour alone.
            self.assertEqual(page.count("class='legend'"), 2)
            self.assertEqual(page.count("class='series-label'"), len(STRATS) * 2)
            # Governance must be visible in the rendered page.
            self.assertIn('RESEARCH_ONLY', page)
            self.assertIn('ORDERS=0', page)
            self.assertIn('official_replica_claim = false', page)

    def test_render_is_deterministic_and_leaves_ledger_untouched(self):
        with tempfile.TemporaryDirectory() as td:
            runtime = build_ledger(Path(td), (('2026-08-13', 0.0), ('2026-08-14', 0.01)))
            ledger = {p.name: p.read_bytes() for p in runtime.iterdir() if p.name != 'REPORT.html'}
            first = rep.render(runtime).read_bytes()
            second = rep.render(runtime).read_bytes()
            self.assertEqual(first, second)
            after = {p.name: p.read_bytes() for p in runtime.iterdir() if p.name != 'REPORT.html'}
            self.assertEqual(ledger, after)

    def test_risk_metrics_are_undefined_rather_than_misleading(self):
        for series in ([], [0.01], [0.01, 0.01, 0.01]):
            m = rep.risk_metrics(series)
            self.assertIsNone(m['sharpe_rf0'], series)
            self.assertIsNone(m['sharpe_rf_frozen'], series)
            self.assertIsNone(m['annualized_volatility'], series)
            self.assertFalse(m['shadow_sample_at_gate_size'])

    def test_risk_metrics_match_frozen_annualization(self):
        series = [0.01, -0.005, 0.02, -0.01]
        m = rep.risk_metrics(series)
        mean = statistics.fmean(series)
        dev = statistics.stdev(series)
        scale = rep.ANNUALIZATION_DAYS ** 0.5
        self.assertAlmostEqual(m['sharpe_rf0'], mean / dev * scale, 12)
        self.assertAlmostEqual(
            m['sharpe_rf_frozen'],
            (mean - rep.RISK_FREE_ANNUAL / rep.ANNUALIZATION_DAYS) / dev * scale, 12)
        self.assertAlmostEqual(m['annualized_volatility'], dev * scale, 12)
        self.assertLess(m['sharpe_rf_frozen'], m['sharpe_rf0'])
        self.assertEqual(m['observations'], 4)

    def test_report_shows_sharpe_with_insufficient_sample_caveat(self):
        with tempfile.TemporaryDirectory() as td:
            runtime = build_ledger(Path(td), (
                ('2026-08-13', 0.0), ('2026-08-14', 0.01), ('2026-08-15', -0.02), ('2026-08-16', 0.015),
            ))
            page = rep.render(runtime).read_text(encoding='utf-8')
            self.assertIn('Metricas de risco desde a ancora', page)
            self.assertIn('Sharpe rf=0', page)
            self.assertIn('Sharpe rf=4.5%', page)
            self.assertIn('DESCRITIVOS', page)
            self.assertIn(str(rep.EVIDENCE_GATE_MIN_OBSERVATIONS), page)

    def test_unsafe_ledger_status_is_refused(self):
        with tempfile.TemporaryDirectory() as td:
            runtime = build_ledger(Path(td), (('2026-08-13', 0.0), ('2026-08-14', 0.01)))
            status_path = runtime / 'STATUS.json'
            status = json.loads(status_path.read_text(encoding='utf-8'))
            status['orders_generated'] = 1
            status_path.write_text(json.dumps(status), encoding='utf-8')
            with self.assertRaises(rep.ReportError):
                rep.render(runtime)

    def test_missing_ledger_is_reported_not_rendered(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(rep.ReportError):
                rep.render(Path(td) / 'empty')


if __name__ == '__main__':
    unittest.main()


class TestGateWindowIsNamedNotImplied(unittest.TestCase):
    """The audit of 2026-09-11: the report showed 'elegivel' beside a 28-day
    shadow and a caveat about needing 60, with nothing saying the gate verdict
    was decided on the engine's 119-observation window. Both figures were
    correct; the juxtaposition was not. These tests pin the labels."""

    def render(self, days=(('2026-08-13', 0.0), ('2026-08-14', 0.01))):
        td = tempfile.mkdtemp()
        runtime = build_ledger(Path(td), days)
        return rep.render(runtime).read_text(encoding='utf-8')

    def test_the_gate_column_names_the_engine_window_and_its_count(self):
        page = self.render()
        self.assertIn('Portao do motor', page)
        self.assertIn('EXPANDING_FROM_D0', page)
        # 90 engine observations from the fixture, beside 1 shadow observation.
        self.assertIn('90 observacao(oes)', page)

    def test_the_gate_column_says_it_is_not_the_shadow_sample(self):
        page = self.render()
        self.assertIn('NAO na amostra prospectiva desta sombra', page)
        self.assertIn('dois contadores distintos', page)

    def test_the_risk_caveat_no_longer_implies_the_shadow_feeds_the_gate(self):
        page = self.render()
        self.assertIn('Os numeros desta tabela sao da SOMBRA', page)
        self.assertIn('NAO sao a base do portao de evidencia', page)
        # The sentence that made the contradiction readable must be gone.
        self.assertNotIn('Amostra prospectiva de 1 observacao(oes); o portao', page)

    def test_a_ledger_without_the_window_fields_says_so_instead_of_guessing(self):
        td = tempfile.mkdtemp()
        runtime = Path(td) / 'rt'
        for index, (day, ret) in enumerate((('2026-08-13', 0.0), ('2026-08-14', 0.01))):
            source = Path(td) / f'{day}.zip'
            fixture(source, day, ret, gate_window=False)
            mon.process(CONTRACT, source, runtime, str(700 + index))
        page = rep.render(runtime).read_text(encoding='utf-8')
        self.assertIn('anterior ao registro da janela', page)
        self.assertNotIn('EXPANDING_FROM_D0', page)


class TestFundingIsNotPresentedAsAdditive(unittest.TestCase):
    """net = gross - cost, with funding already inside gross. The four-column
    layout invited the reading that funding had been dropped from the net."""

    def test_the_header_and_caveat_state_the_convention(self):
        td = tempfile.mkdtemp()
        runtime = build_ledger(Path(td), (('2026-08-13', 0.0), ('2026-08-14', 0.01)))
        page = rep.render(runtime).read_text(encoding='utf-8')
        self.assertIn('Funding (em Bruto)', page)
        self.assertIn('Liquido = Bruto - Custo', page)
        self.assertIn('NAO e subtraido de novo', page)

    def test_the_rendered_numbers_still_satisfy_net_equals_gross_minus_cost(self):
        # The label must describe the ledger, not replace checking it.
        td = tempfile.mkdtemp()
        runtime = build_ledger(Path(td), (('2026-08-13', 0.0), ('2026-08-14', 0.01)))
        import csv as _csv
        with (runtime / 'DAILY_NAV.csv').open() as handle:
            for row in _csv.DictReader(handle):
                gross = float(row['gross_return'])
                cost = float(row['trading_cost_return'])
                net = float(row['net_return'])
                self.assertAlmostEqual(net, gross - cost, 12)
