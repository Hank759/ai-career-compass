"""Integration checks against the built local database."""
import sqlite3
import pytest
from core import data_access as d
from streamlit.testing.v1 import AppTest

def test_read_only():
    with d.connect() as c:
        with pytest.raises(sqlite3.OperationalError):
            c.execute('CREATE TABLE forbidden(x)')

def test_published_occupation_kept_once():
    cat=d.catalog()
    assert not cat.code.duplicated().any()
    for scope in d.TABLES:
        df=d.observations(scope,'15-1252')
        assert len(df)>0
        assert not df.duplicated(['year','area','naics','i_group','own_code','occ_code']).any()
        assert df.source_file.nunique()==1
        assert not df.source_file.str.contains('_sec_').any()
        if 'industry' in scope:
            assert set(df.i_group)=={'sector'}

@pytest.mark.parametrize('code',list(d.COMBINED))
def test_combined_not_fanned_out(code):
    assert len(d.observations('National',code))==1
    assert d.onet_profiles(code).empty

def test_mapping_and_unsafe_inputs():
    a=d.mapping_audit()
    assert len(a[a.status=='combined_requires_review'])==12
    assert not any(a.status=='unresolved')
    assert d.observations('National',"' OR 1=1 --").empty
    with pytest.raises(KeyError):
        d.observations('unknown','15-1252')

def test_skill_scale_and_exposure():
    skills=d.skills('15-1252.00')
    assert len(skills)>0
    assert skills.importance.between(1,5).all()
    assert d.exposure('15-1252').metric.is_unique

def test_navigation_and_occupation_change():
    at=AppTest.from_file(str(d.ROOT/'app.py'),default_timeout=30).run()
    assert not at.exception
    for page in ['Career Dashboard','Regional Analysis','Industry Analysis','Data & Methodology']:
        at.radio[0].set_value(page).run()
        assert not at.exception
        assert not at.error
        if page=='Career Dashboard':
            at.selectbox(key='career_soc').set_value('13-1020').run()
            assert not at.exception and not at.error
            assert not any(x.key=='onet_profile' for x in at.selectbox)
        if page=='Industry Analysis':
            at.selectbox(key='industry_scope').set_value('State industry (research)').run()
            assert not at.exception and not at.error
