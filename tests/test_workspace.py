import copy
import json
import pytest
from streamlit.testing.v1 import AppTest
from core import planning as p
from core import workspace as w
from core import data_access as d

@pytest.fixture
def profile():
    ids=list(p.skill_reference().id[:5])
    return {'version':1,'name':'Round-trip','current_soc':'15-1252','annual_income':60000.,'desired_income':80000.,'weekly_hours':5.,'history':'Example', 'ratings':dict(zip(ids,[5.,4.,3.,2.,0.]))}

@pytest.fixture
def bundle(profile):
    target='11-2021'
    scenario={'target':target,'target_income':80000.,'earnings_fraction':.5,
      'current_income':60000.,'weekly_hours':5.,'result':p.simulate(60000,80000,9,1200,.5,5)}
    token=target+'_'+next(iter(profile['ratings']))
    return w.export_workspace({'profile':profile,'planning_target':target,'saved_scenario':scenario,
        'plan_done':{token:True},'plan_horizons':{target:20},'recommendation_weight':.35})

def test_complete_workspace_roundtrip(bundle):
    state={}
    w.restore_workspace(state,json.loads(json.dumps(bundle)))
    assert w.export_workspace(state)==bundle
    assert state['plan_horizons']['11-2021']==20
    assert any(state['plan_done'].values())

def test_import_recomputes_results(bundle):
    bundle['scenario']['result']['total_transition_cost']=-999
    clean=w.validate_workspace(bundle)
    assert clean['scenario']['result']['total_transition_cost']==23700

@pytest.mark.parametrize('field,value',[('skill_weight',float('nan')),('target','not-a-code'),('plan_horizons',{'11-2021':0}),('completed_tasks',{'not-a-task':True})])
def test_bad_import_does_not_modify_state(bundle,field,value):
    bundle[field]=value
    state={'profile':{'unchanged':True}}
    with pytest.raises(ValueError):w.restore_workspace(state,bundle)
    assert state=={'profile':{'unchanged':True}}

def test_profile_matches_form_minimum(profile):
    profile['weekly_hours']=.1
    with pytest.raises(ValueError):p.validate_profile(profile)
    profile['weekly_hours']=.5
    assert p.validate_profile(profile)

def test_persist_saved_scenario_plan_and_weight(profile):
    at=AppTest.from_file(str(d.ROOT/'app.py'),default_timeout=40).run()
    at.session_state['profile']=profile
    at.radio[0].set_value('Career Recommendations').run()
    at.slider(key='skill_weight').set_value(.35).run()
    target=at.session_state['planning_target']
    at.radio[0].set_value('Transition Simulator').run()
    at.number_input(key='scenario_months_'+target).set_value(9.)
    at.number_input(key='scenario_cost_'+target).set_value(1200.)
    at.button[0].click().run()
    assert not at.exception
    assert len(at.metric)==3
    at.radio[0].set_value('Career Development Plan').run()
    at.number_input(key='plan_weeks_'+target).set_value(20).run()
    at.checkbox[0].check().run()
    at.radio[0].set_value('Personal Report').run()
    at.radio[0].set_value('Transition Simulator').run()
    assert at.number_input(key='scenario_months_'+target).value==9
    assert at.number_input(key='scenario_cost_'+target).value==1200
    at.radio[0].set_value('Career Development Plan').run()
    assert at.number_input(key='plan_weeks_'+target).value==20
    assert at.checkbox[0].value
    at.radio[0].set_value('Career Recommendations').run()
    assert at.slider(key='skill_weight').value==.35
    assert not at.exception and not at.error

def test_restored_workspace_renders_in_fresh_session(bundle):
    values={};w.restore_workspace(values,bundle)
    at=AppTest.from_file(str(d.ROOT/'app.py'),default_timeout=40).run()
    for k,v in values.items():at.session_state[k]=v
    at.radio[0].set_value('Personal Profile').run()
    assert not at.exception and not at.error
    at.radio[0].set_value('Transition Simulator').run()
    assert at.number_input(key='scenario_months_11-2021').value==9
    at.radio[0].set_value('Career Development Plan').run()
    assert at.number_input(key='plan_weeks_11-2021').value==20
    assert not at.exception and not at.error

def test_learning_budget_and_evidence(profile):
    from core import learning_tasks as tasks
    rows=tasks.build_plan(p.gaps(profile,'15-1252',p.matrix()),'15-1252',20,5)
    assert rows
    assert sum(r['allocated_hours'] for r in rows)==pytest.approx(100)
    assert sum(r['hours_per_week'] for r in rows)==pytest.approx(5)
    assert all(r['exercise'] and r['evidence'] for r in rows)
    profile['ratings']={k:5 for k in profile['ratings']}
    assert tasks.build_plan(p.gaps(profile,'15-1252',p.matrix()),'15-1252',20,5)==[]


def test_recommendations_preserve_a_manual_target(profile):
    at=AppTest.from_file(str(d.ROOT/'app.py'),default_timeout=40).run()
    at.session_state['profile']=profile
    at.session_state['planning_target']='13-1020'
    at.radio[0].set_value('Career Recommendations').run()
    assert not at.exception and not at.error
    assert at.session_state['planning_target']=='13-1020'
