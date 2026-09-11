import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tests.test_gate_btc_delta_v12_engine import EngineRunMixin, price_panel
from tools import gate_btc_delta_paper_report as v11
from tools import gate_btc_delta_v12_report as rep


class ReportTests(EngineRunMixin, unittest.TestCase):
    """The report is rendered from ledgers a real engine run produced.

    A fixture hand-written to the shape the report expects would pass while
    production failed, which is exactly how the STATUS field renames broke this
    chain twice. The engine writes the files; the report reads them.
    """

    def render(self, root: Path):
        ledger = root / "ledger"
        document = rep.build_html(ledger)
        status = json.loads((ledger / "STATUS.json").read_text())
        return document, status

    def test_the_anchor_day_renders_and_says_it_is_waiting(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.run_engine(root)
            document, status = self.render(root)
        self.assertEqual(status["observed_days"], 0)
        self.assertIn("Ancora fixada, aguardando o primeiro fechamento", document)
        self.assertIn(status["anchor_date"], document)
        # Nothing is invented on a day with no observation: no NAV of 1.000000,
        # no daily return of +0.0000%, no bar chart of four zeros.
        self.assertIn("Nenhuma posicao simulada em aberto nesta data.", document)
        self.assertIn("Nenhum dia contabilizado ainda.", document)
        self.assertNotIn("1.000000", document)
        self.assertNotIn("+0.0000%", document)

    def test_a_booked_series_renders_nav_positions_and_the_gate(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.run_engine(root, price_panel(days=70))
            status = self.advance(root, 71, 75)
            document, _ = self.render(root)
        self.assertGreater(status["observed_days"], 0)
        self.assertNotIn("aguardando o primeiro fechamento", document)
        for name in status["books"]:
            self.assertIn(name, document)
        self.assertIn("chart-nav", document)
        self.assertIn("Portao de evidencia", document)
        self.assertIn(status["data_as_of"], document)

    def test_funding_is_labelled_as_a_component_of_gross_not_a_fourth_term(self):
        # net = gross - cost, funding already inside gross. Same convention as
        # V11; the old four-column header invited the opposite reading.
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.run_engine(root, price_panel(days=70))
            self.advance(root, 71, 75)
            document, _ = self.render(root)
        self.assertIn("Funding (em Bruto)", document)
        self.assertIn("Liquido = Bruto - Custo", document)
        self.assertIn("NAO e subtraido de novo", document)

    def test_the_report_says_the_v12_gate_window_is_this_same_prospective_series(self):
        # In V11 the gate is decided on the engine's own window, which is not the
        # shadow sample. In V12 the two are the same series. Saying so is what
        # stops "elegivel" from meaning two different things across the reports.
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.run_engine(root, price_panel(days=70))
            self.advance(root, 71, 75)
            document, _ = self.render(root)
        self.assertIn("No V12 a janela do portao E esta mesma serie prospectiva", document)
        self.assertIn("No V11 nao e assim", document)
        self.assertIn("nao comparaveis", document)

    def test_risk_figures_are_the_engine_numbers_not_a_second_calculation(self):
        # The report must never restate the ledger. Every figure it prints for a
        # book has to be the one STATUS carries.
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.run_engine(root, price_panel(days=70))
            status = self.advance(root, 71, 78)
            document, _ = self.render(root)
        for name, book in status["books"].items():
            self.assertIn(rep.percent(book["total_return"]), document, name)
            self.assertIn(rep.percent(book["max_drawdown"]), document, name)
            if book.get("product_compatible_sharpe_rf0") is not None:
                self.assertIn(rep.number(book["product_compatible_sharpe_rf0"]), document, name)

    def test_an_undefined_sharpe_is_a_dash_not_a_zero(self):
        self.assertEqual(rep.number(None), "—")
        self.assertEqual(rep.percent(None), "—")
        self.assertEqual(rep.number(0.0), "0.00")

    def test_books_keep_contract_order_never_performance_order(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.run_engine(root, price_panel(days=70))
            self.advance(root, 71, 74)
            ledger = root / "ledger"
            nav = v11.read_csv_rows(ledger / "DAILY_NAV.csv")
            status = json.loads((ledger / "STATUS.json").read_text())
        ledger_order = []
        for row in nav:
            if row["strategy"] not in ledger_order:
                ledger_order.append(row["strategy"])
        self.assertEqual(rep.book_order(nav, status["books"]), ledger_order)

    def test_the_leaderboard_disclaimer_and_the_independence_notice_are_present(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.run_engine(root, price_panel(days=70))
            self.advance(root, 71, 73)
            document, _ = self.render(root)
        self.assertIn("nao e ranking e nao autoriza promocao", document)
        self.assertIn("independente do V11", document)
        self.assertIn("RESEARCH_ONLY", document)

    def test_an_unsafe_status_is_refused_rather_than_rendered(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.run_engine(root)
            path = root / "ledger" / "STATUS.json"
            status = json.loads(path.read_text())
            status["orders_generated"] = 1
            path.write_text(json.dumps(status))
            with self.assertRaises(v11.ReportError):
                rep.build_html(root / "ledger")

    def test_a_missing_ledger_is_refused_with_a_readable_reason(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(v11.ReportError):
                rep.build_html(Path(td))


class CommandLineTests(EngineRunMixin, unittest.TestCase):
    """The workflow reaches this file only through argv, so argv is what is tested."""

    def test_main_writes_the_report_next_to_the_ledger(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.run_engine(root, price_panel(days=70))
            self.advance(root, 71, 72)
            code = rep.main(["--runtime-dir", str(root / "ledger")])
            self.assertEqual(code, 0)
            self.assertTrue((root / "ledger" / "REPORT.html").is_file())

    def test_main_writes_to_an_explicit_output_path(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.run_engine(root)
            out = root / "out" / "v12.html"
            self.assertEqual(rep.main(["--runtime-dir", str(root / "ledger"),
                                       "--output", str(out)]), 0)
            self.assertTrue(out.is_file())

    def test_allow_missing_exits_clean_before_the_engine_has_ever_run(self):
        with tempfile.TemporaryDirectory() as td:
            self.assertEqual(rep.main(["--runtime-dir", td, "--allow-missing"]), 0)
            self.assertFalse((Path(td) / "REPORT.html").exists())

    def test_without_allow_missing_a_missing_ledger_is_an_error(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(v11.ReportError):
                rep.main(["--runtime-dir", td])

    def test_running_it_as_a_plain_script_works_like_the_workflow_does(self):
        # In-process main() imports this file as part of the tools package, which
        # puts the repository root on sys.path for free. A workflow runs
        # `python tools/<name>.py`, which does not, and the package import at the
        # top of the module failed there while every test above still passed.
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.run_engine(root, price_panel(days=70))
            self.advance(root, 71, 72)
            script = Path(rep.__file__).resolve()
            done = subprocess.run(
                [sys.executable, str(script), "--runtime-dir", str(root / "ledger")],
                capture_output=True, text=True, cwd=script.parents[1])
            self.assertEqual(done.returncode, 0, done.stderr)
            self.assertTrue((root / "ledger" / "REPORT.html").is_file())
            self.assertEqual(json.loads(done.stdout)["schema"], rep.SCHEMA)

    def test_running_it_as_a_module_works_too(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.run_engine(root)
            repo = Path(rep.__file__).resolve().parents[1]
            done = subprocess.run(
                [sys.executable, "-m", "tools.gate_btc_delta_v12_report",
                 "--runtime-dir", str(root / "ledger")],
                capture_output=True, text=True, cwd=repo)
            self.assertEqual(done.returncode, 0, done.stderr)
            self.assertTrue((root / "ledger" / "REPORT.html").is_file())


if __name__ == "__main__":
    unittest.main()
