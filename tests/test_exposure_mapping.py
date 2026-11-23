import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest
from core import data_access as d,planning as p
from core.exposure_mapping import PAIRS,resolve,SOURCE
from core.demo_workspace import example_workspace

def test_reviewed_mappings_preserve_each_source_value():
    assert len(PAIRS)==8 and len(set(PAIRS.values()))==8
    for current,old in PAIRS.items():
        rows=d.exposure(current)
        original=d.frame("SELECT metric,score FROM exposure_scores WHERE code_type='SOC Code' AND code=?",(old,)).set_index('metric')
        assert len(rows)==3 and set(rows.source_code)=={old}
        assert set(rows.match_method)=={'Mapped historical reference'}
        assert set(rows.crosswalk_url)=={SOURCE}
        for r in rows.itertuples():assert r.score==pytest.approx(original.loc[r.metric,'score'])
    assert len(d.exposure_coverage())==681
    assert len(d.catalog())==830

def test_no_split_or_merge_inference():
    assert d.exposure('15-1252').empty  # software developers: multiple predecessors
    assert d.exposure('15-1242').empty  # database administrators: predecessor split
    assert d.exposure('29-1291').empty

def test_exact_metric_precedes_historical_and_duplicates_fail():
    raw=pd.DataFrame([{'code':'15-1244','metric':'AIOE','score':2.,'source_file':'exact'},
                      {'code':'15-1142','metric':'AIOE','score':1.,'source_file':'old'},
                      {'code':'15-1142','metric':'Language Modeling AIOE','score':3.,'source_file':'old'}])
    result=resolve(raw,['15-1244']).set_index('metric')
    assert result.loc['AIOE','score']==2.
    assert result.loc['AIOE','match_method']=='Exact source code'
    assert result.loc['Language Modeling AIOE','score']==3.
    with pytest.raises(ValueError):resolve(pd.concat([raw,raw]),['15-1244'])

def test_ui_mapped_reference_and_missing_message():
    at=AppTest.from_file(str(d.ROOT/'app.py'),default_timeout=60).run()
    at.radio[0].set_value('Career Dashboard').run()
    at.selectbox(key='career_soc').set_value('15-1244').run()
    assert not at.exception and not at.error
    assert [r.value for r in at.metric]==['0.790','0.475','1.476']
    assert any('15-1142' in x.value and 'Historical reference' in x.value for x in at.info)
    at.selectbox(key='career_soc').set_value('29-1291').run()
    assert any('No available exposure data match at present' in x.value for x in at.info)
    assert [r.value for r in at.metric]==['Not available']*3
    at.toggle(key='data_only_exposure').set_value(True).run()
    assert '29-1291' not in at.session_state['career_soc']
    assert at.session_state['career_soc'] in set(d.exposure_coverage().code)
    at.toggle(key='data_only_exposure').set_value(False).run()
    at.selectbox(key='career_soc').set_value('29-1291').run()
    assert not at.exception and not at.error

def test_recommendations_use_same_resolver_without_affecting_scores():
    profile=example_workspace()['profile'];m=p.matrix()
    result=p.recommend(profile,m)
    row=result[result.code=='15-1244'].iloc[0]
    assert row.exposure_ai==pytest.approx(.7895315)
    assert row.exposure_match=='Mapped historical reference'
    assert row.comparison_score==pytest.approx(.8*row.skill_alignment+.2*row.wage_preference)
