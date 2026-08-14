import json
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
