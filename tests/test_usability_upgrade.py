import copy
import pytest
from streamlit.testing.v1 import AppTest
from core import data_access as d
from core import planning as p
from core import workspace as w
from core.demo_workspace import example_workspace
from core.scenario_tools import add_comparison

@pytest.fixture
def example():
    return example_workspace()

def calculated(example,target_income=90000):
    profile=example['profile']
    return {'target':example['target'],'current_income':profile['annual_income'],'target_income':target_income,
      'earnings_fraction':1.,'weekly_hours':profile['weekly_hours'],
      'result':p.simulate(profile['annual_income'],target_income,6,1200,1,profile['weekly_hours'])}

def test_legacy_backup_still_imports(example):
    old=copy.deepcopy(example);old['version']=1;old.pop('scenario_comparisons')
    state={};w.restore_workspace(state,old)
    assert state['profile']==old['profile']
    assert state['scenario_comparisons']==[]

def test_comparisons_restore_and_recalculate(example):
    items=add_comparison([],'Part time',calculated(example),example['profile'])
    example['scenario_comparisons']=items
    example['scenario_comparisons'][0]['scenario']['result']['total_transition_cost']=-1
    clean=w.validate_workspace(example)
    assert clean['scenario_comparisons'][0]['scenario']['result']['total_transition_cost']==1200
    state={};w.restore_workspace(state,clean)
    assert w.export_workspace(state)==clean

def test_comparison_limit_and_duplicate_names(example):
    items=[]
    for i in range(5):items=add_comparison(items,'Case '+str(i),calculated(example),example['profile'])
    with pytest.raises(ValueError):add_comparison(items,'Sixth',calculated(example),example['profile'])
    with pytest.raises(ValueError):add_comparison(items[:1],' case 0 ',calculated(example),example['profile'])

def test_example_start_requires_confirmation_and_can_return(example):
    at=AppTest.from_file(str(d.ROOT/'app.py'),default_timeout=40).run()
    original=copy.deepcopy(example['profile']);original['name']='Original learner'
    at.session_state['profile']=original;at.run()
    assert at.button(key='start_guided_example').disabled
    at.checkbox(key='confirm_demo_replace').check().run()
    at.button(key='start_guided_example').click().run()
    assert not at.exception and not at.error
    assert at.radio[0].value=='Career Recommendations'
    assert at.session_state['profile']['name']=='Example learner (fictional)'
    at.button(key='return_my_workspace').click().run()
    assert at.radio[0].value=='Home'
    assert at.session_state['profile']==original

def test_demo_scenario_compare_save_and_remove():
    at=AppTest.from_file(str(d.ROOT/'app.py'),default_timeout=40).run()
    at.button(key='start_guided_example').click().run()
    assert at.radio[0].value=='Career Recommendations'
    assert any(x.value=='Why this comparison?' for x in at.subheader)
    at.button(key='footer_next').click().run()
    next(x for x in at.button if x.label=='Calculate and save scenario').click().run()
    at.text_input(key='comparison_label').set_value('Flexible study')
    next(x for x in at.button if x.label=='Add calculated scenario to comparison').click().run()
    assert not at.exception and not at.error
    assert len(at.session_state['scenario_comparisons'])==1
    at.button(key='comparison_remove').click().run()
    assert at.session_state['scenario_comparisons']==[]

def test_profile_change_clears_comparison_baseline(example):
    from core.planning_ui import save_profile
    at=AppTest.from_file(str(d.ROOT/'app.py'),default_timeout=40).run()
    at.session_state['profile']=example['profile']
    at.session_state['scenario_comparisons']=add_comparison([],'Old baseline',calculated(example),example['profile'])
    at.radio[0].set_value('Personal Profile').run()
    at.text_input[0].set_value('Changed learner')
    next(x for x in at.button if x.label=='Save profile').click().run()
    assert not at.exception and at.session_state['scenario_comparisons']==[]
