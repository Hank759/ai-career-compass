import pytest
from streamlit.testing.v1 import AppTest
from core import data_access as d
from core import planning as p

def test_exposure_is_prominent_on_data_pages():
    at=AppTest.from_file(str(d.ROOT/'app.py'),default_timeout=40).run()
    for page in ['Career Dashboard','Regional Analysis','Industry Analysis']:
        at.radio[0].set_value(page).run()
        at.selectbox(key='career_soc').set_value('11-1011').run()
        assert not at.exception and not at.error
        assert len(at.metric)==3
        scores=d.exposure('11-1011').set_index('metric').score
        assert at.metric[0].value==f'{scores["AIOE"]:.3f}'
        assert at.metric[1].value==f'{scores["Language Modeling AIOE"]:.3f}'
        assert at.metric[2].value==f'{scores["Image Generation AIOE"]:.3f}'

def test_missing_exposure_not_zero():
    present=set(d.frame("SELECT DISTINCT code FROM exposure_scores WHERE code_type='SOC Code'").code)
    missing=next(code for code in d.catalog().code if code not in present)
    at=AppTest.from_file(str(d.ROOT/'app.py'),default_timeout=40).run()
    at.radio[0].set_value('Career Dashboard').run()
    at.selectbox(key='career_soc').set_value(missing).run()
    assert not at.exception and not at.error
    assert [x.value for x in at.metric]==['Not available']*3

def test_exposure_columns_are_unscaled_source_values():
    ids=list(p.skill_reference().id[:5])
    profile={'version':1,'name':'Test','current_soc':'15-1252','annual_income':60000.,'desired_income':0.,'weekly_hours':5.,'history':'', 'ratings':dict(zip(ids,[5.,4.,3.,2.,0.]))}
    out=p.recommend(profile,p.matrix())
    chief=out[out.code=='11-1011'].iloc[0]
    source=d.exposure('11-1011').set_index('metric').score
    assert chief.exposure_ai==pytest.approx(source['AIOE'])
    assert chief.exposure_language==pytest.approx(source['Language Modeling AIOE'])
    assert chief.comparison_score==chief.skill_alignment
