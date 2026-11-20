import math
import json
import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest
from core import data_access as d
from core import planning as p

@pytest.fixture(scope='module')
def m():
    return p.matrix()

@pytest.fixture
def profile():
    ids=list(p.skill_reference().id[:5])
    return {'version':1,'name':'Test','current_soc':'15-1252','annual_income':60000.0,
      'desired_income':80000.0,'weekly_hours':5.0,'history':'Prior roles',
      'ratings':dict(zip(ids,[5.,4.,3.,2.,0.]))}

def test_profile_roundtrip_and_unknown_ratings(profile):
    assert p.validate_profile(json.loads(json.dumps(profile)))==profile
    assert len(profile['ratings'])==5
    assert 0 in profile['ratings'].values()
    bad={**profile,'ratings':{'made-up':3}}
    with pytest.raises(ValueError):p.validate_profile(bad)

@pytest.mark.parametrize('value',[float('nan'),float('inf'),-1,True])
def test_invalid_income(profile,value):
    with pytest.raises(ValueError):p.validate_profile({**profile,'annual_income':value})

def test_require_assessed_skills(profile,m):
    with pytest.raises(ValueError):p.recommend({**profile,'ratings':{}},m)

def test_recommendation_formula_and_coverage(profile,m):
    out=p.recommend(profile,m,.8)
    assert not out.empty and not out.code.duplicated().any()
    assert profile['current_soc'] not in set(out.code)
    assert out.comparison_score.between(0,1).all()
    assert out.assessment_coverage.between(0,1).all()
    r=out.iloc[0]
    if pd.notna(r.wage_preference):
        assert r.comparison_score==pytest.approx(.8*r.skill_alignment+.2*r.wage_preference)
    assert p.recommend({**profile,'desired_income':0},m).comparison_score.equals(p.recommend({**profile,'desired_income':0},m).skill_alignment)

def test_missing_wage_and_unassessed_skill(profile,m):
    out=p.recommend(profile,m)
    missing=out[out.median_wage.isna()]
    assert (missing.comparison_score==missing.skill_alignment).all()
    gaps=p.gaps(profile,'15-1252',m)
    assert gaps.self_rating.isna().any()
    assert gaps.loc[gaps.self_rating.isna(),'priority'].isna().all()

def test_combined_occupation_has_no_invented_skill_plan(profile,m):
    assert p.gaps(profile,'13-1020',m).empty

def test_transition_arithmetic_and_payback():
    r=p.simulate(60000,72000,6,2000,.5,5)
    assert r['earnings_forgone']==15000
    assert r['total_transition_cost']==17000
    assert r['monthly_income_change']==1000
    assert r['payback_months_after_transition']==17
    assert r['learning_hours']==130
    assert p.simulate(60000,60000,6,2000,1,5)['payback_months_after_transition'] is None
    assert p.simulate(60000,50000,6,2000,1,5)['payback_months_after_transition'] is None
    assert p.simulate(0,60000,6,0,1,5)['payback_months_after_transition']==0

@pytest.mark.parametrize('args',[(1,2,0,0,1,5),(1,2,1,0,2,5),(1,2,1,-1,1,5),(1,float('nan'),1,0,1,5)])
def test_invalid_scenario(args):
    with pytest.raises(ValueError):p.simulate(*args)

def test_history_missing_values_preserved():
    f=p.history('27-2011')
    assert list(f.year)==[2022,2023,2024,2025]
    assert f.median_annual_wage.isna().all()
    assert p.history('not-a-code').empty

def test_report_is_valid_json(profile,m):
    report=p.report(profile,'15-1252',m)
    assert json.loads(json.dumps(report,allow_nan=False))['scenario'] is None
    assert report['profile']['ratings']==profile['ratings']

def test_all_pages_and_workflow(profile):
    at=AppTest.from_file(str(d.ROOT/'app.py'),default_timeout=40).run()
    for page in list(at.radio[0].options):
        at.radio[0].set_value(page).run()
        assert not at.exception and not at.error
        assert not any('under development' in x.value for x in at.warning)
    at.session_state['profile']=profile
    at.radio[0].set_value('Career Recommendations').run()
    assert not at.exception
    assert any('comparison_score' in x.value.columns for x in at.dataframe)
    assert any('priority' in x.value.columns for x in at.dataframe)
    target=at.session_state['planning_target']
    at.radio[0].set_value('Transition Simulator').run()
    at.button[0].click().run()
    assert not at.exception and 'saved_scenario' in at.session_state
    at.radio[0].set_value('Career Development Plan').run()
    at.checkbox[0].check().run()
    assert any(at.session_state['plan_done'].values())
    at.radio[0].set_value('Personal Report').run()
    assert not at.exception and not at.error
    at.radio[0].set_value('Personal Profile').run()
    at.text_input[0].set_value('Updated name')
    at.button[0].click().run()
    assert not at.exception and at.session_state['profile']['name']=='Updated name'
    assert 'saved_scenario' not in at.session_state
