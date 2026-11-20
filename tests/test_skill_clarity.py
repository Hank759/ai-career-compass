from streamlit.testing.v1 import AppTest
from core import data_access as d

def dashboard():
    at=AppTest.from_file(str(d.ROOT/'app.py'),default_timeout=40).run()
    at.radio[0].set_value('Career Dashboard').run()
    at.selectbox(key='career_soc').set_value('27-4021').run()
    return at

def summary(at):
    return next(x.value for x in at.dataframe if list(x.value.columns)==['Skill','Importance','Skill category'])

def test_category_filter_and_all_skills():
    at=dashboard()
    assert not at.exception and not at.error
    assert len(summary(at))==20
    at.toggle(key='dashboard_skills_all').set_value(True).run()
    code=at.selectbox(key='onet_profile').value
    assert len(summary(at))==len(d.skills(code))
    at.segmented_control(key='dashboard_skill_category').set_value('Essential').run()
    assert set(summary(at)['Skill category'])=={'Essential'}
    expected=d.skills(code);expected=expected[expected.family=='Essential']
    assert len(summary(at))==len(expected)
    at.segmented_control(key='dashboard_skill_category').set_value('Transferable').run()
    assert set(summary(at)['Skill category'])=={'Transferable'}
    assert not at.exception and not at.error

def test_source_details_keep_provenance_and_scores():
    at=dashboard()
    table=summary(at)
    raw=d.skills(at.selectbox(key='onet_profile').value)
    assert list(table.Importance)==list(raw.head(20).importance)
    details=next(x.value for x in at.dataframe if 'Skill ID' in x.value.columns)
    assert {'Source date','Rating source','Skill category'}.issubset(details.columns)
    assert len(details)==len(raw)
    assert len(at.metric)==3
