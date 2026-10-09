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


def sample(original_id="42", cancellation_id="42"):
    columns = ("CodigoInstrumento;AcaoAtualizacao;PrecoNegocio;QuantidadeNegociada;"
               "HoraFechamento;CodigoIdentificadorNegocio;TipoSessaoPregao\n")
    rows = (f"WINV26;0;100,0;2;09:00:01.000;{original_id};1\n"
            f"WINV26;2;100,0;2;09:00:02.000;{cancellation_id};1\n")
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as z:
        z.writestr("2026-10-08_NEGOCIOSAVISTA.TXT", columns + rows)
    return stream.getvalue()


class CancelIdentityAuditTests(unittest.TestCase):
    def test_matching_execution_is_reported_but_session_still_fails_closed(self):
        with self.assertRaisesRegex(RuntimeError, "'matched_original_count': 1") as caught:
            process_zip(sample(), "2026-10-08", {"WIN": "WINV26", "WDO": "WDOV26"})
        self.assertIn("IDENTITIES_INSPECTED_ZERO_CREDIT", str(caught.exception))
        self.assertIn("'cancel_rows': 1", str(caught.exception))

    def test_unmatched_cancel_remains_fail_closed_and_visible(self):
        with self.assertRaisesRegex(RuntimeError, "'matched_original_count': 0"):
            process_zip(sample(cancellation_id="999"), "2026-10-08",
                        {"WIN": "WINV26", "WDO": "WDOV26"})


if __name__ == "__main__":
    unittest.main()
