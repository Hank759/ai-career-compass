from streamlit.testing.v1 import AppTest
from core import data_access as d
from core.demo_workspace import example_workspace
from core.workspace import validate_workspace

def test_fictional_example_is_valid_and_transparent():
    value=example_workspace()
    assert validate_workspace(value)==value
    assert value['profile']['name']=='Example learner (fictional)'
    assert 'Fictional' in value['profile']['history']
    assert value['scenario'] is None
    assert value['profile']['current_soc']!=value['target']
    assert len(d.exposure(value['target']))==3

def test_home_scope_and_demo_do_not_overwrite_profile():
    at=AppTest.from_file(str(d.ROOT/'app.py'),default_timeout=40).run()
    assert not at.exception and not at.error
    assert any('Includes U.S. states' in c.value for c in at.caption)
    assert at.session_state['profile']=={}
