import json
from tools.gate_btc_factory.grammar_source_cost_intake import build


def prereg(sig='a'*64, frozen_semantics=None):
    row = {
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
    if frozen_semantics is not None:
        row['frozen_semantics'] = frozen_semantics
    return row


def test_cumulative_legacy_prereg_is_visible_but_semantically_blocked(tmp_path):
    d=tmp_path/'preregs'; d.mkdir()
    (d/'XAGRAMMAR_AAAAAAAAAAAA.json').write_text(json.dumps(prereg()),encoding='utf-8')
    out=build(d)
    assert out['mode']=='CUMULATIVE_PREREG_TO_SOURCE_COST_GATE_ONLY'
    assert out['transported_count']==1
    assert out['semantic_ready_count']==0
    assert out['blocked_semantics_count']==1
    row=out['families'][0]
    assert row['status']=='BLOCKED_PREREG_SEMANTICS_UNDECIDABLE'
    assert row['semantic_preregistration_complete'] is False
    assert row['source_qualified'] is False
    assert row['cost_applicability_proven'] is False
    assert row['economics_read'] is False
    assert row['historical_testing_started'] is False
    assert row['next_stage']=='SEPARATE_SEMANTIC_PREREGISTRATION_REQUIRED_BEFORE_SOURCE_COST'


def test_future_complete_semantic_prereg_reaches_source_cost_queue(tmp_path):
    d=tmp_path/'preregs'; d.mkdir()
    semantics={
        'feature':'FROZEN_FEATURE',
        'window':'FROZEN_WINDOW',
        'lookback':'FROZEN_LOOKBACK',
        'target':'FROZEN_TARGET',
    }
    (d/'XAGRAMMAR_AAAAAAAAAAAA.json').write_text(
        json.dumps(prereg(frozen_semantics=semantics)),encoding='utf-8'
    )
    out=build(d)
    assert out['semantic_ready_count']==1
    assert out['blocked_semantics_count']==0
    row=out['families'][0]
    assert row['status']=='QUEUED_FOR_SOURCE_COST_QUALIFICATION'
    assert row['semantic_preregistration_complete'] is True
    assert row['frozen_semantics']==semantics


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
