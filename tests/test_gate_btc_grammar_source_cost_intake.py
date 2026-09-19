import json
from tools.gate_btc_factory.grammar_source_cost_intake import build


def prereg(sig='a'*64):
    return {
        'schema':'qrds.factory.grammar_scout_separate_prereg.v1',
        'family_id':'XAGRAMMAR_'+sig[:12].upper(),
        'grammar_signature':sig,
        'channel_id':'TEST_CHANNEL',
        'mechanism':'ex-ante test mechanism',
        'required_new_data':['official data'],
        'official_free_source_candidates':['B3'],
        'status':'PREREGISTERED_AWAITING_SOURCE_COST_QUALIFICATION',
        'source_qualification_required':True,
        'cost_applicability_required':True,
        'economics_read':False,
        'historical_testing_started':False,
    }


def test_cumulative_preregs_transport_even_when_incremental_handoff_is_empty(tmp_path):
    d=tmp_path/'preregs'; d.mkdir()
    (d/'XAGRAMMAR_AAAAAAAAAAAA.json').write_text(json.dumps(prereg()),encoding='utf-8')
    out=build(d)
    assert out['mode']=='CUMULATIVE_PREREG_TO_SOURCE_COST_GATE_ONLY'
    assert out['transported_count']==1
    row=out['families'][0]
    assert row['status']=='QUEUED_FOR_SOURCE_COST_QUALIFICATION'
    assert row['source_qualified'] is False
    assert row['cost_applicability_proven'] is False
    assert row['economics_read'] is False
    assert row['historical_testing_started'] is False


def test_fail_closed_if_economics_or_history_already_opened(tmp_path):
    d=tmp_path/'preregs'; d.mkdir()
    p=prereg(); p['economics_read']=True
    (d/'XAGRAMMAR_AAAAAAAAAAAA.json').write_text(json.dumps(p),encoding='utf-8')
    try:
        build(d)
    except ValueError as e:
        assert 'FAIL_CLOSED' in str(e)
        return
    raise AssertionError('expected fail closed')


def test_fail_closed_on_duplicate_signature(tmp_path):
    d=tmp_path/'preregs'; d.mkdir()
    p=prereg()
    (d/'XAGRAMMAR_AAAAAAAAAAAA.json').write_text(json.dumps(p),encoding='utf-8')
    q=dict(p); q['family_id']='XAGRAMMAR_BBBBBBBBBBBB'
    (d/'XAGRAMMAR_BBBBBBBBBBBB.json').write_text(json.dumps(q),encoding='utf-8')
    try:
        build(d)
    except ValueError as e:
        assert 'duplicate grammar signature' in str(e)
        return
    raise AssertionError('expected fail closed')
