import json
from streamlit.testing.v1 import AppTest
from core import data_access as d, planning as p, journey_ui as journey
from core.demo_workspace import example_workspace
from core.report_html import render


def app():
    at=AppTest.from_file(str(d.ROOT/'app.py'),default_timeout=40).run()
    at.session_state['profile']=example_workspace()['profile']
    at.session_state['planning_target']='11-3021'
    return at


def test_target_selection_follows_across_pages():
    at=app()
    at.radio[0].set_value('Transition Simulator').run()
    at.selectbox(key='planning_Transition Simulator').set_value('11-1011').run()
    at.radio[0].set_value('Career Development Plan').run()
    assert at.selectbox(key='planning_Career Development Plan').value=='11-1011'
    at.selectbox(key='planning_Career Development Plan').set_value('15-1252').run()
    at.radio[0].set_value('Transition Simulator').run()
    assert at.selectbox(key='planning_Transition Simulator').value=='15-1252'
    assert at.session_state['planning_target']=='15-1252'
    assert not at.exception and not at.error


def test_no_tasks_does_not_mark_plan_prepared():
    at=app();profile=example_workspace()['profile']
    at.session_state['profile']={**profile,'ratings':{k:5 for k in profile['ratings']}}
    at.radio[0].set_value('Career Development Plan').run()
    assert not at.exception and not at.error
    assert '11-3021' not in at.session_state['plan_horizons']
    state={'profile':at.session_state['profile'],'planning_target':'11-3021',
           'plan_horizons':{},'plan_unavailable_target':'11-3021'}
    assert not journey.journey_state(state)['flags'][3]


def test_profile_change_clears_old_scenario_inputs():
    at=app();at.radio[0].set_value('Transition Simulator').run()
    at.number_input(key='scenario_cost_11-3021').set_value(9876.)
    next(b for b in at.button if b.label=='Calculate and save scenario').click().run()
    at.radio[0].set_value('Personal Profile').run()
    at.number_input(key='profile_income_0').set_value(72000.)
    next(b for b in at.button if b.label=='Save profile').click().run()
    at.radio[0].set_value('Transition Simulator').run()
    assert at.number_input(key='scenario_cost_11-3021').value==1000.
    assert 'saved_scenario' not in at.session_state
    assert not at.exception and not at.error


def test_printable_report_escapes_user_content_and_keeps_missing_values():
    profile=example_workspace()['profile']
    profile={**profile,'name':'<script>alert(1)</script>','history':'<img src=x onerror=alert(2)> & notes'}
    payload=p.report(profile,'11-1011',p.matrix())
    payload['target_exposure']=json.loads(d.exposure('11-1011').to_json(orient='records'))
    html=render(payload)
    assert '<script>' not in html and '<img src=' not in html
    assert '&lt;script&gt;' in html and '&lt;img src=x' in html
    assert 'No saved scenario for this target.' in html
    assert '@media print' in html and '<html lang="en">' in html
    assert 'AIOE' in html and '1.334' in html
    assert 'http' not in html  # no remote dependencies or tracking


def test_report_page_and_backup_controls():
    at=app();at.radio[0].set_value('Personal Report').run()
    assert not at.exception and not at.error
    buttons=at.get('download_button')
    assert any(b.label=='Download printable report (HTML)' for b in buttons)
    assert any(b.label=='Quick backup: complete workspace' for b in buttons)
