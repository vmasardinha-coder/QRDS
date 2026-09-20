import json
from tools.gate_btc_factory.grammar_source_cost_intake import build


def prereg(sig='a'*64, frozen_semantics=None, channel='TEST_CHANNEL'):
    row = {
        'schema':'qrds.factory.grammar_scout_separate_prereg.v1',
        'family_id':'XAGRAMMAR_'+sig[:12].upper(),
        'grammar_signature':sig,
        'channel_id':channel,
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


def semantics():
    return {
        'feature':'FROZEN_FEATURE',
        'window':'FROZEN_WINDOW',
        'lookback':'FROZEN_LOOKBACK',
        'target':'FROZEN_TARGET',
    }


def semantic_freeze(sig='a'*64, channel='TEST_CHANNEL'):
    return {
        'schema':'qrds.factory.grammar_semantic_prereg.v1',
        'frozen_before_source_cost':True,
        'outcome_blind':True,
        'economics_read':False,
        'historical_testing_started':False,
        'families':[{
            'family_id':'XAGRAMMAR_'+sig[:12].upper(),
            'grammar_signature':sig,
            'channel_id':channel,
            'frozen_semantics':semantics(),
        }],
        'safety':{
            'RESEARCH_ONLY':True,
            'SHADOW_ONLY':True,
            'NOT_APPROVED':True,
            'ENGINE_FEED':False,
            'ORDERS':0,
            'REAL_CAPITAL':0,
            'NO_RETUNE':True,
            'NO_BACKFILL':True,
            'NO_COUNTER_RESET':True,
            'FAIL_CLOSED':True,
            'H1_H31_UNTOUCHED':True,
        },
    }


def test_cumulative_legacy_prereg_is_visible_but_semantically_blocked(tmp_path):
    d=tmp_path/'preregs'; d.mkdir()
    (d/'XAGRAMMAR_AAAAAAAAAAAA.json').write_text(json.dumps(prereg()),encoding='utf-8')
    out=build(d)
    assert out['mode']=='CUMULATIVE_PREREG_TO_SOURCE_COST_GATE_ONLY'
    assert out['transported_count']==1
    assert out['semantic_ready_count']==0
    assert out['semantic_prereg_applied_count']==0
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
    (d/'XAGRAMMAR_AAAAAAAAAAAA.json').write_text(
        json.dumps(prereg(frozen_semantics=semantics())),encoding='utf-8'
    )
    out=build(d)
    assert out['semantic_ready_count']==1
    assert out['semantic_prereg_applied_count']==0
    assert out['blocked_semantics_count']==0
    row=out['families'][0]
    assert row['status']=='QUEUED_FOR_SOURCE_COST_QUALIFICATION'
    assert row['semantic_preregistration_complete'] is True
    assert row['frozen_semantics']==semantics()
    assert row['semantic_source']=='ORIGINAL_PREREGISTRATION'


def test_separate_outcome_blind_semantic_prereg_unblocks_legacy_family(tmp_path):
    d=tmp_path/'preregs'; d.mkdir()
    (d/'XAGRAMMAR_AAAAAAAAAAAA.json').write_text(json.dumps(prereg()),encoding='utf-8')
    freeze=tmp_path/'semantic.json'
    freeze.write_text(json.dumps(semantic_freeze()),encoding='utf-8')
    out=build(d, freeze)
    assert out['semantic_ready_count']==1
    assert out['semantic_prereg_applied_count']==1
    assert out['blocked_semantics_count']==0
    row=out['families'][0]
    assert row['status']=='QUEUED_FOR_SOURCE_COST_QUALIFICATION'
    assert row['frozen_semantics']==semantics()
    assert row['semantic_source']=='SEPARATE_OUTCOME_BLIND_SEMANTIC_PREREG_V1'
    assert row['semantic_prereg_sha256']


def test_fail_closed_on_semantic_identity_mismatch(tmp_path):
    d=tmp_path/'preregs'; d.mkdir()
    (d/'XAGRAMMAR_AAAAAAAAAAAA.json').write_text(json.dumps(prereg()),encoding='utf-8')
    freeze=semantic_freeze(); freeze['families'][0]['channel_id']='WRONG_CHANNEL'
    p=tmp_path/'semantic.json'; p.write_text(json.dumps(freeze),encoding='utf-8')
    try:
        build(d,p)
    except ValueError as e:
        assert 'identity mismatch' in str(e)
        return
    raise AssertionError('expected fail closed')


def test_fail_closed_on_orphan_semantic_family(tmp_path):
    d=tmp_path/'preregs'; d.mkdir()
    freeze=tmp_path/'semantic.json'; freeze.write_text(json.dumps(semantic_freeze()),encoding='utf-8')
    try:
        build(d,freeze)
    except ValueError as e:
        assert 'not present in immutable prereg ledger' in str(e)
        return
    raise AssertionError('expected fail closed')


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
        assert 'duplicate grammar identity' in str(e)
        return
    raise AssertionError('expected fail closed')
