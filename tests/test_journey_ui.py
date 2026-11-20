from streamlit.testing.v1 import AppTest
from core import data_access as d
from core import journey_ui as j


def app():
    return AppTest.from_file(str(d.ROOT/'app.py'),default_timeout=40).run()


def test_explore_route_needs_no_profile():
    at=app()
    assert at.button(key='home_explore')
    at.selectbox(key='home_occupation').set_value('11-1011').run()
    at.button(key='home_explore').click().run()
    assert not at.exception and not at.error
    assert at.radio[0].value=='Career Dashboard'
    assert at.selectbox(key='career_soc').value=='11-1011'
    assert at.session_state['profile']=={}
    assert len(at.metric)==3
    at.button(key='footer_home').click().run()
    assert at.radio[0].value=='Home'


def test_new_user_guided_route_and_save():
    at=app()
    at.button(key='home_plan').click().run()
    assert at.radio[0].value=='Personal Profile'
    at.session_state['skill_editor_0']={'edited_rows':{0:{'rating':4},1:{'rating':2},2:{'rating':0}},'added_rows':[],'deleted_rows':[]}
    at.button[0].click().run()
    assert len(at.session_state['profile']['ratings'])==3
    at.button(key='footer_next').click().run()
    assert at.radio[0].value=='Career Recommendations'
    assert not at.exception and not at.error
    at.button(key='footer_next').click().run()
    assert at.radio[0].value=='Transition Simulator'
    assert not at.exception


def test_home_does_not_create_sample_personal_data():
    at=app()
    assert at.session_state['profile']=={}
    assert len(at.metric)==3
    assert at.metric[0].value=='830'
    assert at.metric[1].value=='673'
    assert not at.exception and not at.error


def test_journey_requires_matching_scenario():
    state={'profile':{'ratings':{'a':1,'b':2,'c':3}},'planning_target':'11-1011','saved_scenario':{'target':'15-1252'}}
    result=j.journey_state(state)
    assert result['next_page']=='Transition Simulator'
    assert result['flags']==[True,True,False,False,False]
    state['saved_scenario']['target']='11-1011'
    assert j.journey_state(state)['next_page']=='Career Development Plan'
    state['plan_unavailable_target']='11-1011'
    assert j.journey_state(state)['next_page']=='Personal Report'


def test_home_resume_saved_profile():
    at=app()
    from core import planning as planning
    ids=list(planning.skill_reference().id[:3])
    at.session_state['profile']={'version':1,'name':'Returning user','current_soc':'15-1252','annual_income':60000.,'desired_income':80000.,'weekly_hours':5.,'history':'','ratings':dict(zip(ids,[4.,3.,2.]))}
    at.run()
    at.button(key='home_plan').click().run()
    assert at.radio[0].value=='Career Recommendations'
    assert not at.exception and not at.error
