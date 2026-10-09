import io
import sys
import types
import unittest
import zipfile

try:
    import requests  # noqa: F401
except ImportError:
    sys.modules["requests"] = types.ModuleType("requests")

from tools.gate_btc_b3_h1_parser import process_zip


def sample(original_id="42", cancellation_id="42", original_price="100,0", extra_original=False):
    columns = ("CodigoInstrumento;AcaoAtualizacao;PrecoNegocio;QuantidadeNegociada;"
               "HoraFechamento;CodigoIdentificadorNegocio;TipoSessaoPregao\n")
    rows = (f"WINV26;0;{original_price};2;09:00:01.000;{original_id};1\n"
            + (f"WINV26;0;{original_price};2;09:00:01.500;{original_id};1\n" if extra_original else "")
            + f"WINV26;2;100,0;2;09:00:02.000;{cancellation_id};1\n"
            + "WINV26;0;105,0;3;09:00:03.000;43;1\n")
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as z:
        z.writestr("2026-10-08_NEGOCIOSAVISTA.TXT", columns + rows)
    return stream.getvalue()


class CancelIdentityAuditTests(unittest.TestCase):
    def test_exact_delete_removes_only_matched_original(self):
        m1, m5, stats, _ = process_zip(sample(), "2026-10-08",
                                        {"WIN": "WINV26", "WDO": "WDOV26"})
        self.assertEqual(stats["cancel_rows"], 1)
        self.assertEqual(stats["cancelled_original_rows_removed"], 1)
        self.assertEqual(stats["cancellation_reconciliation"], "EXACT_ONE_TO_ONE_DELETE_NEW")
        self.assertEqual(stats["cancellation_identity_audit"]["evidence"][0]["matched_original_count"], 1)
        self.assertEqual(m1.iloc[0]["volume"], 3)
        self.assertEqual(m1.iloc[0]["open"], 105)
        self.assertEqual(m5.iloc[0]["trades"], 1)

    def test_unmatched_cancel_remains_fail_closed_and_visible(self):
        with self.assertRaisesRegex(RuntimeError, "'matched_original_count': 0"):
            process_zip(sample(cancellation_id="999"), "2026-10-08",
                        {"WIN": "WINV26", "WDO": "WDOV26"})

    def test_price_mismatch_or_ambiguous_original_fails_closed(self):
        front = {"WIN": "WINV26", "WDO": "WDOV26"}
        with self.assertRaisesRegex(RuntimeError, "'cancel_rows': 1"):
            process_zip(sample(original_price="110,0"), "2026-10-08", front)
        with self.assertRaisesRegex(RuntimeError, "'matched_original_count': 2"):
            process_zip(sample(extra_original=True), "2026-10-08", front)


if __name__ == "__main__":
    unittest.main()
