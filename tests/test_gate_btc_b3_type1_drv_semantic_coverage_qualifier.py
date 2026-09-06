from tools.gate_btc_factory.b3_type1_drv_semantic_coverage_qualifier import qualify


class Raw:
    def __init__(self, b): self.b = b
    def read(self, n, decode_content=True): return self.b[:n]


class Resp:
    def __init__(self, status, data=b'', disp=None, length=None):
        self.status_code = status
        self.raw = Raw(data)
        self.headers = {
            'content-disposition': disp,
            'content-type': 'application/octet-stream',
        }
        if length is not None:
            self.headers['content-length'] = str(length)
    def __enter__(self): return self
    def __exit__(self, *a): return False


class Session:
    def get(self, url, **kwargs):
        if '2026-09-04' in url:
            return Resp(200, b'PK\x03\x04abc', 'attachment; filename=04-09-2026_NEGOCIOSAVISTA_DRV.zip', 42167724)
        return Resp(200, b'', None, 0)


def prereg():
    return {
        'schema': 'qrds.factory.b3_type1_drv_semantic_coverage_prereg.v1',
        'frozen_transport_probe_dates': ['2026-09-04', '2026-01-30'],
        'prior_physical_evidence': {
            'exact_win_identity_observed': True,
            'zip_sha256': 'a' * 64,
            'columns': ['DataReferencia', 'CodigoInstrumento', 'HoraFechamento'],
        },
    }


def test_qualifier_never_opens_gate_or_credit():
    d = qualify(Session(), prereg())
    assert d['positive_transport_dates'] == ['2026-09-04']
    assert d['negative_transport_dates'] == ['2026-01-30']
    assert d['strict_source_gate_green'] is False
    assert d['source_gate_credit'] == 0
    assert d['historical_backfill_credit'] == 0
    assert d['prospective_credit'] == 0
    assert d['economics_read'] is False
    assert d['full_161_session_coverage_proven'] is False
    assert d['timezone_session_semantics_proven'] is False
    assert d['publication_semantics_proven'] is False
    assert d['revision_semantics_proven'] is False
    assert d['point_in_time_valid'] is False
    assert d['data_gap_definitive'] is False
    s = d['safety']
    assert s['research_only'] and s['shadow_only'] and s['not_approved'] and s['fail_closed']
    assert s['engine_feed'] is False and s['orders'] == 0 and s['real_capital'] == 0
    assert s['no_retune'] and s['no_backfill'] and s['no_counter_reset']
    assert s['h1_economics_read'] is False
