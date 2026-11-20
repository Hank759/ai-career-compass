import copy,json
import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest
from core import data_access as d,planning as p,regional,pathways,workspace
from core.demo_workspace import example_workspace

def learner():return copy.deepcopy(example_workspace()['profile'])

def test_price_adjustment_matches_formula_and_keeps_missing():
    rows=pd.DataFrame({'area':['06','72','06'],'area_title':['California','Puerto Rico','Changed California boundary'],'a_median':[100000.,100000.,100000.],'year':[2025]*3})
    result=regional.adjust(rows,'State')
    assert result.iloc[0].rpp==110.720
    assert result.iloc[0].price_adjusted_wage==pytest.approx(100000/1.1072)
    assert result.price_match.tolist()==[True,False,False]
    assert result.iloc[1:].price_adjusted_wage.isna().all()
    assert result.a_median.tolist()==[100000.]*3

def test_metro_requires_both_code_and_name():
    rows=pd.DataFrame({'area':['10180','10180'],'area_title':['Abilene, TX','Different geography'],'a_median':[50000.,50000.],'year':[2025]*2})
    result=regional.adjust(rows,'Metro')
    assert result.price_match.tolist()==[True,False]
    assert result.iloc[0].price_adjusted_wage==pytest.approx(50000/.90364)

def test_regional_ranking_uses_selected_area_wages_and_filters():
    profile={**learner(),'preferred_region':{'scope':'State','area':'06','wage_basis':'Price-adjusted proxy'}}
    p.validate_profile(profile)
    wages,context=regional.recommendation_inputs(profile)
    assert context['area_title']=='California' and set(wages.area)=={'06'}
    ranked,other,basis=p.comparison_groups(profile,p.matrix(),.8,wages)
    assert basis=='Skills + wage' and not ranked.empty
    row=ranked.iloc[0]
    raw=regional.wage_catalog('State','06').set_index('code').loc[row.code]
    assert row.median_wage==pytest.approx(raw.median_wage/1.1072)
    assert row.comparison_score==pytest.approx(.8*row.skill_alignment+.2*min(row.median_wage/profile['desired_income'],1))
    assert set(ranked.code)|set(other.code)<=set(wages.code)

def test_education_matches_actual_modal_categories_without_degree_hierarchy():
    modal=pathways.modal_profiles()
    code=next(code for code,rows in modal.items() if len({r['Category'] for r in rows})==1)
    category=modal[code][0]['Category'];other=next(c for c in pathways.categories() if c!=category)
    rows=pd.DataFrame({'code':[code,'made-up']})
    profile={**learner(),'education_category':category,'education_filter':pathways.FILTERS[1]}
    result=pathways.annotate(rows,profile)
    assert result.code.tolist()==[code]
    assert pathways.annotate(rows,{**profile,'education_category':other}).empty
    planned=pathways.annotate(rows,{**profile,'education_category':other,'planned_education':[category],'education_filter':pathways.FILTERS[2]})
    assert planned.code.tolist()==[code] and planned.iloc[0].education_pathway=='Planned education matches'
    assert pathways.annotate(rows,learner()).iloc[1].education_pathway=='No usable education reference'

def test_modal_matches_never_use_incomplete_suppressed_distributions():
    usable=pathways.distributions()
    for rows in pathways.modal_profiles().values():
        for code in {r['O*NET-SOC Code'] for r in rows}:
            profile=usable[usable['O*NET-SOC Code']==code]
            assert profile.Category.nunique()==12
            assert 99.9<=profile.share.sum()<=100.1

def test_adjusted_report_labels_and_review_escape():
    from core.report_html import render
    profile={**learner(),'preferred_region':{'scope':'State','area':'06','wage_basis':'Price-adjusted proxy'}}
    payload=p.report(profile,'11-1011',p.matrix())
    payload.update(recommendation_geography={'scope':'State','area_title':'California','basis':'Price-adjusted proxy','wage_year':2025,'rpp_year':2024},
        target_qualification_review={'status':pathways.REVIEWS[1],'notes':'<script>private</script>'},
        comparison_summary=[{'occupation':'Example','median_wage':90000.,'comparison_score':.8}])
    html=render(payload)
    assert 'Desired purchasing power (US-average price units)' in html
    assert 'Price-adjusted wage proxy (US-average price units)' in html
    assert '&lt;script&gt;private&lt;/script&gt;' in html and '<script>' not in html

def test_qualification_filter_is_explicit_and_roundtrips_old_workspaces():
    profile={**learner(),'education_category':'6','planned_education':['8'],'education_filter':pathways.FILTERS[0],
        'qualification_reviews':{'11-1011':{'status':pathways.REVIEWS[1],'notes':'Check local authority'}},'exclude_qualification_gaps':True,
        'preferred_region':{'scope':'State','area':'06','wage_basis':'Nominal USD'}}
    p.validate_profile(profile)
    assert pathways.annotate(pd.DataFrame({'code':['11-1011','15-1252']}),profile).code.tolist()==['15-1252']
    bundle=workspace.export_workspace({'profile':profile})
    restored={};workspace.restore_workspace(restored,json.loads(json.dumps(bundle)))
    assert restored['profile']==profile
    old=example_workspace();restored={};workspace.restore_workspace(restored,old)
    assert restored['profile']==old['profile']

@pytest.mark.parametrize('fields',[{'education_category':[]},{'planned_education':['fake']},{'education_filter':'fake'},
    {'qualification_reviews':{'11-1011':{'status':'Verified by app','notes':''}}},
    {'preferred_region':{'scope':'State','area':'XX','wage_basis':'Nominal USD'}}])
def test_invalid_new_preferences_rejected(fields):
    with pytest.raises(ValueError):p.validate_profile({**learner(),**fields})

def test_new_profile_preferences_apply_and_render_across_workflow():
    at=AppTest.from_file(str(d.ROOT/'app.py'),default_timeout=40).run()
    at.session_state['profile']=learner()
    at.radio[0].set_value('Personal Profile').run()
    at.selectbox(key='profile_region_scope_0').set_value('State').run()
    at.selectbox(key='profile_region_area_State_0').set_value('06').run()
    at.selectbox(key='profile_region_basis_State_0').set_value('Price-adjusted proxy').run()
    at.selectbox(key='profile_education_0').set_value('6')
    next(b for b in at.button if b.label=='Save profile').click().run()
    assert at.session_state['profile']['education_category']=='6'
    assert at.session_state['profile']['preferred_region']['area']=='06'
    at.radio[0].set_value('Career Recommendations').run()
    assert not at.exception and not at.error
    assert any('California' in x.value and 'Price-adjusted proxy' in x.value for x in at.markdown)
    next(b for b in at.button if b.label=='Save qualification review').click().run()
    at.radio[0].set_value('Transition Simulator').run()
    assert any('California' in x.value and 'nominal median' in x.value for x in at.markdown)
    next(b for b in at.button if b.label=='Calculate and save scenario').click().run()
    at.radio[0].set_value('Personal Report').run()
    assert not at.exception and not at.error
    assert any('qualification notes' in x.value for x in at.subheader)

def test_regional_page_shows_prices_and_allows_switch():
    at=AppTest.from_file(str(d.ROOT/'app.py'),default_timeout=40).run()
    at.radio[0].set_value('Regional Analysis').run()
    at.segmented_control(key='regional_wage_basis').set_value('Price-adjusted proxy').run()
    assert not at.exception and not at.error
    assert any('price_adjusted_wage' in x.value.columns or 'Price-adjusted wage proxy' in x.value.columns for x in at.dataframe)
    at.selectbox(key='region_scope').set_value('Metro').run()
    assert not at.exception and not at.error
