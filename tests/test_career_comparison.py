import copy,json
import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest
from core import planning as p,data_access as d,comparison_tools as c,workspace
from core.demo_workspace import example_workspace

def test_sensitivity_ties_and_one_at_a_time_changes():
    profile={'ratings':{'a':3,'b':3,'c':3},'desired_income':0}
    matrix=pd.DataFrame([[1.,1.,1.],[5.,0.,0.]],columns=['a','b','c'],index=['A','B'])
    ranked=pd.DataFrame({'code':['A','B'],'occupation':['A','B'],'skill_alignment':[.6,.6],'wage_preference':[float('nan')]*2})
    original=copy.deepcopy(profile)
    summary,cases=c.sensitivity(profile,matrix,1.,ranked)
    assert len(cases)==7
    assert summary.saved_score_rank.tolist()==[1.,1.]
    assert summary.best_tested_rank.tolist()==[1.,1.]
    assert summary.worst_tested_rank.tolist()==[2.,2.]
    assert summary.top_10_band_cases.tolist()==[7,7]
    assert profile==original

def test_clipped_rating_endpoints_do_not_duplicate_tests():
    profile={'ratings':{'a':0,'b':5,'c':3},'desired_income':0}
    matrix=pd.DataFrame([[1.,1.,1.]],columns=['a','b','c'],index=['A'])
    ranked=pd.DataFrame({'code':['A'],'occupation':['A'],'skill_alignment':[8/15],'wage_preference':[float('nan')]})
    _,cases=c.sensitivity(profile,matrix,.8,ranked)
    assert len(cases)==5 and len(set(cases))==5

def test_weight_and_skill_trials_use_actual_formula_and_fixed_group():
    profile=example_workspace()['profile'];matrix=p.matrix()
    ranked,_,_=p.comparison_groups(profile,matrix,.8)
    summary,cases=c.sensitivity(profile,matrix,.8,ranked)
    assert 'Skill weight 0.75' in cases and 'Skill weight 0.85' in cases
    expected=ranked.comparison_score.round(12).rank(method='min',ascending=False)
    assert summary.saved_score_rank.tolist()==expected.tolist()
    for weight in [.75,.85]:
        trial=p.recommend(profile,matrix,weight).set_index('code').loc[list(ranked.code)]
        ranks=trial.comparison_score.round(12).rank(method='min',ascending=False)
        assert (summary.best_tested_rank.to_numpy()<=ranks.to_numpy()).all()
        assert (summary.worst_tested_rank.to_numpy()>=ranks.to_numpy()).all()

def test_side_by_side_keeps_missing_costs_and_original_exposure():
    profile=example_workspace()['profile'];matrix=p.matrix();ranked,_,_=p.comparison_groups(profile,matrix)
    codes=list(ranked.code[:3]);table=c.side_by_side(profile,matrix,ranked,codes)
    assert table.saved_training_fees.isna().all()
    assert table.saved_transition_months.isna().all()
    assert table.code.tolist()==codes
    pd.testing.assert_series_equal(table.exposure_ai,ranked.exposure_ai.head(3).reset_index(drop=True))
    display=c.display_comparison(table)
    import pyarrow as pa
    pa.Table.from_pandas(display)  # transposed numeric/text values must serialize without automatic fixes
    assert len(display.columns)==4 and 'Measure' in display
    assert 'Comparison score / 100' in set(display.Measure)

@pytest.mark.parametrize('choices',[['fake'],['11-1011']*2,['11-1011']*4,'11-1011',{}])
def test_invalid_comparison_selection(choices):
    with pytest.raises(ValueError):p.validate_profile({**example_workspace()['profile'],'comparison_codes':choices})

def test_comparison_selection_roundtrip_and_stale_controls_clear():
    profile={**example_workspace()['profile'],'comparison_codes':['11-1011','11-3021']}
    value=workspace.export_workspace({'profile':profile})
    state={'career_compare_codes':['15-1252'],'run_career_sensitivity':True,'career_sensitivity_requested':True}
    workspace.restore_workspace(state,json.loads(json.dumps(value)))
    assert state['profile']['comparison_codes']==profile['comparison_codes']
    assert not any(key in state for key in ['career_compare_codes','run_career_sensitivity','career_sensitivity_requested'])

def test_comparison_ui_sensitivity_and_report():
    at=AppTest.from_file(str(d.ROOT/'app.py'),default_timeout=40).run()
    at.button(key='start_guided_example').click().run()
    assert any(x.value=='Compare careers side by side' for x in at.subheader)
    assert len(at.multiselect(key='career_compare_codes').value)==3
    at.toggle(key='run_career_sensitivity').set_value(True).run()
    assert not at.exception and not at.error
    assert any('Best tested rank' in f.value.columns for f in at.dataframe)
    selected=at.session_state['profile']['comparison_codes']
    at.multiselect(key='career_compare_codes').set_value(selected[:1]).run()
    assert any('Choose at least two' in x.value for x in at.info)
    at.multiselect(key='career_compare_codes').set_value(selected[:2]).run()
    at.toggle(key='run_career_sensitivity').set_value(True).run()
    at.radio[0].set_value('Personal Report').run()
    assert not at.exception and not at.error
    at.radio[0].set_value('Career Recommendations').run()
    assert at.multiselect(key='career_compare_codes').value==selected[:2]
    assert at.toggle(key='run_career_sensitivity').value

def test_printable_comparison_and_sensitivity_are_escaped():
    from core.report_html import render
    profile=example_workspace()['profile'];m=p.matrix();ranked,_,_=p.comparison_groups(profile,m)
    rows=c.side_by_side(profile,m,ranked,list(ranked.code[:2]))
    rows.loc[0,'occupation']='<script>fake</script>'
    summary,cases=c.sensitivity(profile,m,.8,ranked)
    payload=p.report(profile,'11-1011',m)
    payload.update(career_side_by_side=json.loads(rows.to_json(orient='records')),
        sensitivity_analysis={'summary':json.loads(summary.head(2).to_json(orient='records')),'cases':cases,'method':'Fixed-group what-if tests; not confidence.'})
    html=render(payload)
    assert 'Selected careers side by side' in html and 'Input sensitivity' in html
    assert '<script>' not in html and '&lt;script&gt;fake&lt;/script&gt;' in html
