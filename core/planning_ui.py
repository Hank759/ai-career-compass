"""Personal planning pages. Profiles remain in session unless explicitly exported."""
import json
import sqlite3
import pandas as pd
import streamlit as st
from core import data_access as d
from core import planning as p
from core import workspace as ws
from core import learning_tasks as learning

@st.cache_data(ttl=300,max_entries=16)
def reference(kind,version):
    return getattr(p,kind)()

@st.cache_data(ttl=300,max_entries=32)
def annual(soc,version):
    return p.history(soc)

def save_profile(profile):
    p.validate_profile(profile)
    if profile!=st.session_state.get('profile'):
        st.session_state['scenario_comparisons']=[]
        st.session_state.pop('saved_scenario',None)
        st.session_state.pop('report_prepared_target',None)
        st.session_state.pop('plan_unavailable_target',None)
        st.session_state['plan_done']={}
        st.session_state['plan_horizons']={}
    st.session_state.profile=profile

def render(page):
    st.title(page)
    try:
        version=d.fingerprint()
        if page=='Personal Profile':
            profile_page(version);return
        if page=='Historical Trends':
            history_page(version);return
        profile=st.session_state.get('profile',{})
        if not profile:
            st.info('Start with Personal Profile and save your details. Your skills are assessed by you, not inferred from your job title.')
            return
        m=reference('matrix',version)
        if page=='Career Recommendations':
            recommendations(profile,m);return
        cat=reference('wage_catalog',version)
        target=target_selector(cat,'planning_'+page)
        if page=='Transition Simulator':
            simulator(profile,target,cat)
        elif page=='Career Development Plan':
            development(profile,target,m)
        elif page=='Personal Report':
            personal_report(profile,target,m)
    except (ValueError,KeyError,sqlite3.Error,OSError) as exc:
        st.error(f'Unable to complete this step: {exc}')

def target_selector(cat,key):
    codes=list(cat.code);titles=cat.set_index('code').occupation.to_dict()
    previous=st.session_state.get('planning_target')
    index=codes.index(previous) if previous in codes else 0
    target=st.selectbox('Target occupation',codes,index=index,format_func=lambda x:f'{x} — {titles[x]}',key=key)
    st.session_state.planning_target=target
    return target

def profile_page(version):
    st.caption('This session uses US labour-market data and USD. Profile data is held in this browser session; export it to keep a copy. Reopening the app may start a new session.')
    upload=st.file_uploader('Restore a profile or complete workspace (JSON)',type=['json'],key='profile_upload')
    if upload is not None and st.button('Import profile',key='import_profile'):
        try:
            if upload.size>200000:
                raise ValueError('Profile must be smaller than 200 KB')
            value=json.loads(upload.getvalue())
            if isinstance(value,dict) and value.get('kind')=='career_workspace':
                ws.restore_workspace(st.session_state,value)
            else:
                save_profile(value)
                st.session_state['profile_revision']=st.session_state.get('profile_revision',0)+1
            st.success('Saved data restored. Review the profile below; workspace files also restore your target, simulation and plan progress.')
        except (ValueError,TypeError,UnicodeError) as exc:
            st.error(f'Profile could not be imported: {exc}')
    saved=st.session_state.get('profile',{})
    ref=reference('skill_reference',version)
    cat=reference('wage_catalog',version)
    codes=list(cat.code);titles=cat.set_index('code').occupation.to_dict()
    current=saved.get('current_soc','15-1252')
    ref=ref.copy();ref['rating']=pd.Series(ref.id.map(saved.get('ratings',{})),dtype='float64')
    rev=st.session_state.get('profile_revision',0)
    with st.form('personal_form_'+str(rev)):
        name=st.text_input('Name or nickname (optional)',value=saved.get('name',''),max_chars=100,key=f'profile_name_{rev}')
        soc=st.selectbox('Current occupation',codes,index=codes.index(current) if current in codes else 0,format_func=lambda x:f'{x} — {titles[x]}',key=f'profile_current_{rev}')
        income=st.number_input('Your current annual income (USD; 0 if none)',min_value=0.0,max_value=100000000.0,value=float(saved.get('annual_income',0)),step=1000.0,key=f'profile_income_{rev}')
        desired=st.number_input('Desired annual income (USD; 0 to omit wage preference)',min_value=0.0,max_value=100000000.0,value=float(saved.get('desired_income',0)),step=1000.0,key=f'profile_desired_{rev}')
        hours=st.number_input('Learning hours available per week',min_value=0.5,max_value=168.0,value=float(saved.get('weekly_hours',5)),step=0.5,key=f'profile_hours_{rev}')
        history=st.text_area('Career history and interests (optional; for your plan/report, not scored)',value=saved.get('history',''),max_chars=5000,key=f'profile_history_{rev}')
        st.subheader('Your skill self-assessment')
        st.write('Rate at least three skills: 0 = no familiarity, 5 = very confident. Leave unassessed skills blank. These are your self-ratings, not O*NET proficiency requirements.')
        st.caption('Self-rating guide: 0 = unfamiliar; 1–2 = need support; 3 = independent with basic tasks; 4–5 = confident. This is a self-assessment, not an official qualification scale.')
        edited=st.data_editor(ref,disabled=['id','skill'],hide_index=True,num_rows='fixed',column_order=['skill','rating'],
            column_config={'id':None,'skill':'Skill','rating':st.column_config.NumberColumn('Self-rating (0–5)',min_value=0,max_value=5,step=1)},
            key=f'skill_editor_{rev}',alt='Editable skill self-assessment with blank values for unassessed skills')
        submitted=st.form_submit_button('Save profile')
    if submitted:
        ratings={str(r.id):float(r.rating) for r in edited.itertuples() if pd.notna(r.rating)}
        save_profile({'version':1,'name':name,'current_soc':soc,'annual_income':income,'desired_income':desired,
                      'weekly_hours':hours,'history':history,'ratings':ratings})
        st.success(f'Profile saved with {len(ratings)} assessed skills.')
    if st.session_state.get('profile'):
        bundle=ws.export_workspace(st.session_state)
        st.download_button('Back up complete workspace',json.dumps(bundle,ensure_ascii=False,indent=2,allow_nan=False).encode('utf-8'),
                           'career_workspace.json','application/json',key='export_workspace')
        st.caption('Complete backups include your profile, selected target, saved simulation, scenario comparisons, learning progress, plan duration and recommendation weight. Import this file above to resume in a new session.')
        st.download_button('Export profile',json.dumps(st.session_state.profile,ensure_ascii=False,indent=2).encode('utf-8'),
                           'career_profile.json','application/json',key='export_profile')

def history_page(version):
    cat=reference('wage_catalog',version)
    codes=list(cat.code);titles=cat.set_index('code').occupation.to_dict()
    soc=st.selectbox('Occupation',codes,format_func=lambda x:f'{x} — {titles[x]}',key='history_soc')
    f=annual(soc,version)
    st.warning('These are separate May 2022–2025 OEWS estimates. Survey panels, methods and classifications can change. Do not interpret differences as a personal wage trajectory or an AI effect.')
    fields={'Median annual wage (USD)':'median_annual_wage','Mean annual wage (USD)':'mean_annual_wage','Employment':'employment'}
    selected=st.selectbox('Choose an annual measure',list(fields),key='history_measure')
    measure=fields[selected]
    chart=f[['year',measure]].dropna(subset=[measure]).copy()
    if not chart.empty:
        chart['year']=chart.year.astype(str)
        st.bar_chart(chart,x='year',y=measure,x_label='Reference year',y_label=selected,alt='Separately published annual OEWS estimates for the selected occupation; not a personal wage trajectory')
    else:
        st.info('No values are available to chart for this measure. Review the other records below.')
    st.dataframe(f,hide_index=True,alt='Separate annual national OEWS estimates and source files')
    st.caption('Wages are nominal USD, without inflation adjustment. Missing years remain absent; no interpolation or growth-rate forecast is applied.')
    st.download_button('Download annual estimates',f.to_csv(index=False).encode('utf-8-sig'),'annual_estimates.csv','text/csv',key='download_history')

def recommendations(profile,m):
    st.caption('A transparent comparison tool, not a prediction of suitability, job availability or hiring success. Your history/interests text is not scored.')
    weight=st.slider('Weight on assessed-skill alignment',0.0,1.0,float(st.session_state.get('recommendation_weight',.8)),0.05,key='skill_weight')
    st.caption('The remaining weight goes to national median wage / desired wage, capped at 1. Missing wage or a zero wage goal uses skill alignment alone. Unassessed skills are excluded rather than treated as zero.')
    if len(profile['ratings'])<3:
        st.info('Return to Personal Profile and assess at least three skills to generate comparisons.');return
    st.session_state['recommendation_weight']=weight
    if len(set(profile['ratings'].values()))==1:
        st.warning('All assessed skills have the same rating, so they provide little differentiation between occupations. Add varied assessments where justified; tied scores are ordered by SOC code, not evidence of better suitability.')
    result=p.recommend(profile,m,weight)
    if float(result.assessment_coverage.max())<0.25:
        st.warning('Fewer than a quarter of reference skills are assessed. More assessments will make the comparison better informed.')
    top=result.head(25)
    display=top.copy()
    for col in ['comparison_score','skill_alignment','assessment_coverage','wage_preference']:
        display[col]=(display[col]*100).round(1)
    st.dataframe(display,hide_index=True,column_order=['occupation','comparison_score','assessment_coverage','median_wage','exposure_ai','exposure_language','exposure_image'],column_config={
        'code':'SOC code','occupation':'Occupation','comparison_score':st.column_config.NumberColumn('Comparison score / 100',format='%.1f'),
        'skill_alignment':st.column_config.NumberColumn('Assessed-skill alignment / 100',format='%.1f'),
        'assessment_coverage':st.column_config.NumberColumn('Skills assessed (%)',format='%.1f'),
        'wage_preference':st.column_config.NumberColumn('Wage preference / 100',format='%.1f'),
        'median_wage':st.column_config.NumberColumn('National median annual wage (USD)',format='$%.0f'),
        'employment':'Published employment','exposure_ai':'AI exposure','exposure_language':'Language exposure','exposure_image':'Image exposure'},
        alt='Career comparisons with heuristic scores, assessed-skill coverage and national wage benchmarks')
    st.caption('Exposure columns show raw source indices (general AI, language model and image generation), not percentages; blanks mean unavailable. Exposure is displayed for comparison, not used as a job-loss penalty in the ranking.')
    st.caption('Score and coverage columns are on a 0–100 scale, not probabilities. Low assessment coverage limits the comparison. Occupations without usable skill data are excluded; all wage records remain available in Career Dashboard.')
    if top.empty:
        st.info('No comparable occupations have sufficient reference data.');return
    selections=top
    previous=st.session_state.get('planning_target')
    if previous and previous not in set(top.code):
        prior=reference('wage_catalog',d.fingerprint())
        selections=pd.concat([top,prior[prior.code==previous]],ignore_index=True)
        st.caption('Your previously selected target remains selectable even if it is outside the current shortlist.')
    target=target_selector(selections,'recommendation_target')
    matched=result[result.code==target]
    if not matched.empty:
        row=matched.iloc[0]
        with st.container(border=True):
            st.subheader('Why this comparison?')
            st.write(f'Assessed-skill alignment: {row.skill_alignment*100:.1f}/100. Skill assessment coverage: {row.assessment_coverage*100:.1f}%.')
            if pd.notna(row.wage_preference):
                st.write(f'Comparison score {row.comparison_score*100:.1f}/100 = {weight:.0%} skill alignment + {1-weight:.0%} wage preference. The wage term is capped at the stated goal.')
            else:
                st.write('Only the assessed-skill term is available: no wage goal was set or the wage estimate is missing. This row uses a different evidence basis from rows with both terms.')
            st.caption('These are rule-based comparisons. A high score does not establish qualifications, licensing eligibility or hiring prospects.')
    from core.data_ui import exposure_panel
    exposure_panel(target,d.fingerprint(),'Career Recommendations')
    gap=p.gaps(profile,target,m)
    important=gap.dropna(subset=['self_rating']).head(8)
    if not important.empty:
        st.bar_chart(important.set_index('skill')[['priority']],alt='Learning priority weights for assessed skills; higher values suggest reviewing the skill sooner')
    st.subheader('Skill learning priorities')
    st.dataframe(gap,hide_index=True,alt='Skill importance, self-ratings and transparent learning priority weights')
    st.caption('Priority = mean O*NET importance × (1 − self-rating / 5). Importance is not a required proficiency level. Blank ratings need assessment; O*NET specializations are averaged without employment weights.')
    st.download_button('Download comparisons',display.to_csv(index=False).encode('utf-8-sig'),'career_comparisons.csv','text/csv',key='download_recommendations')

def simulator(profile,target,cat):
    row=cat[cat.code==target].iloc[0]
    bench=None if pd.isna(row.median_wage) else float(row.median_wage)
    st.caption('Deterministic planning assumptions, not a salary or employment forecast. Costs and income are nominal USD.')
    if bench is None:
        st.info('No published median annual wage exists for this occupation. Enter your own post-transition income assumption.')
    else:
        st.write(f'National 2025 median wage benchmark: ${bench:,.0f}. You can change the assumption below.')
    previous=st.session_state.get('saved_scenario') or {}
    if previous.get('target')!=target:
        previous={}
    previous_result=previous.get('result',{})
    with st.form('scenario_form'):
        target_income=st.number_input('Assumed annual income after transition (USD)',min_value=0.0,max_value=100000000.0,value=float(previous.get('target_income',bench or 0.0)),step=1000.0,key='target_income_'+target)
        months=st.number_input('Transition duration (months)',min_value=1.0,max_value=120.0,value=float(previous_result.get('training_months',6)),step=1.0,key='scenario_months_'+target)
        cost=st.number_input('Total training and transition fees (USD)',min_value=0.0,max_value=10000000.0,value=float(previous_result.get('training_cost',1000)),step=100.0,key='scenario_cost_'+target)
        retained=st.slider('Current earnings retained during transition (%)',0,100,int(round(previous.get('earnings_fraction',1)*100)),key='retained_income_'+target)
        calculate=st.form_submit_button('Calculate and save scenario')
    if calculate:
        value=p.simulate(profile['annual_income'],target_income,months,cost,retained/100,profile['weekly_hours'])
        st.session_state.saved_scenario={'target':target,'current_income':profile['annual_income'],'target_income':target_income,
            'earnings_fraction':retained/100,'weekly_hours':profile['weekly_hours'],'result':value}
    saved=st.session_state.get('saved_scenario')
    if not saved or saved['target']!=target:
        st.info('Calculate a scenario for this target to see costs, payback and sensitivity.');return
    r=saved['result']
    with st.container(horizontal=True):
        st.metric('Transition cost (USD)',f'${r["total_transition_cost"]:,.0f}',border=True)
        st.metric('Monthly income change (USD)',f'${r["monthly_income_change"]:,.0f}',border=True)
        payback=r['payback_months_after_transition']
        st.metric('Payback after transition',f'{payback:.1f} months' if payback is not None else 'No positive income gain',border=True)
    st.dataframe(pd.DataFrame([r]),hide_index=True,alt='Saved transition cost, income-change and payback assumptions')
    st.caption('Results reflect the last calculated scenario. Recalculate after changing inputs. Payback starts after transition; it is unavailable when assumed income does not increase. Taxes, financing, discounting and job-search delays are excluded.')
    rows=[]
    for income_factor in [.8,1,1.2]:
        for duration_factor in [.75,1,1.25]:
            v=p.simulate(saved['current_income'],saved['target_income']*income_factor,r['training_months']*duration_factor,r['training_cost'],saved['earnings_fraction'],saved['weekly_hours'])
            rows.append({'income_assumption_factor':income_factor,'duration_factor':duration_factor,**v})
    scenario_comparison(profile,saved)
    st.subheader('Sensitivity to your assumptions')
    st.dataframe(pd.DataFrame(rows),hide_index=True,alt='Nine what-if combinations of income and transition duration assumptions')

def scenario_comparison(profile,saved):
    from core.scenario_tools import add_comparison,comparison_rows
    items=st.session_state.setdefault('scenario_comparisons',[])
    st.subheader('Compare your saved scenarios')
    st.caption('Save the currently calculated result, not unsaved form edits. Up to five named scenarios can be compared; all use the current profile baseline. Comparisons are included in complete workspace backups.')
    with st.form('comparison_form'):
        name=st.text_input('Scenario label',max_chars=60,placeholder='For example: part-time retraining',key='comparison_label')
        add=st.form_submit_button('Add calculated scenario to comparison')
    if add:
        try:
            st.session_state['scenario_comparisons']=add_comparison(items,name,saved,profile)
            st.success('Scenario added to comparison.')
        except ValueError as exc:st.warning(str(exc))
    items=st.session_state['scenario_comparisons']
    if not items:return
    table=pd.DataFrame(comparison_rows(items))
    st.dataframe(table,hide_index=True,alt='Named transition scenarios with assumed income, costs and simple payback')
    st.caption('Blank payback means assumed income does not increase. No missing payback is converted to zero. This is a what-if comparison, not a forecast.')
    st.download_button('Download scenario comparison',table.to_csv(index=False).encode('utf-8-sig'),'scenario_comparison.csv','text/csv',key='download_scenario_comparison')
    remove=st.selectbox('Scenario to remove',[x['name'] for x in items],key='comparison_remove_name')
    st.button('Remove selected scenario',key='comparison_remove',on_click=remove_comparison,args=(remove,))


def remove_comparison(name):
    st.session_state['scenario_comparisons']=[x for x in st.session_state.get('scenario_comparisons',[]) if x['name']!=name]


def development(profile,target,m):
    g=p.gaps(profile,target,m)
    if g.empty:
        st.session_state['plan_unavailable_target']=target
        st.info('No direct skill reference is available for this occupation. Review the combined-occupation mapping before creating an automatic skill plan.');return
    st.caption('A suggested practice schedule, not an estimate of the time needed to qualify. Self-assess unassessed skills before relying on the priority order.')
    horizons=st.session_state.setdefault('plan_horizons',{})
    weeks=st.number_input('Planning horizon (weeks)',min_value=1,max_value=104,value=int(horizons.get(target,12)),key='plan_weeks_'+target)
    horizons[target]=int(weeks)
    focus=g[g.self_rating.notna() & (g.priority>0)].head(5)
    unknown=g[g.self_rating.isna()]
    if len(unknown):
        st.info(f'{len(unknown)} reference skills remain unassessed. The schedule below uses assessed skills only.')
    if focus.empty:
        st.info('There are no assessed skills with a positive learning priority. Assess blank skills in Personal Profile, or revisit ratings if appropriate.');return
    saved=st.session_state.setdefault('plan_done',{})
    rows=learning.build_plan(g,target,weeks,profile['weekly_hours'],saved)
    st.caption('Exercises below are app-authored practice suggestions, not official O*NET training requirements or course endorsements. Equipment-related practice should use simulation or appropriate supervision.')
    for row in rows:
        token=target+'_'+row['id']
        complete=st.checkbox(f'{row["skill"]} ({row["hours_per_week"]:.1f} hours/week, {row["allocated_hours"]:.1f} hours total)',value=bool(saved.get(token,False)),key='check_'+token)
        st.write(row['exercise'])
        st.caption('Completion evidence: '+row['evidence'])
        saved[token]=complete
        row['complete']=complete
    completed=sum(bool(row['complete']) for row in rows)
    st.progress(completed/len(rows),text=f'{completed} of {len(rows)} learning tasks completed')
    st.write(f'Weekly budget: {profile["weekly_hours"]:g} hours · Total: {weeks*profile["weekly_hours"]:g} hours. Allocate time across tasks; qualification and job search are additional considerations.')
    st.download_button('Download learning checklist',pd.DataFrame(rows).to_csv(index=False).encode('utf-8-sig'),'learning_plan.csv','text/csv',key='download_plan')

def personal_report(profile,target,m):
    saved=st.session_state.get('saved_scenario')
    if saved and saved['target']!=target:
        saved=None
    done={k:v for k,v in st.session_state.get('plan_done',{}).items() if k.startswith(target+'_')}
    payload=p.report(profile,target,m,saved,done)
    from core.data_ui import exposure_panel
    exposure_panel(target,d.fingerprint(),'Personal Report')
    payload['scenario_comparisons']=[item for item in st.session_state.get('scenario_comparisons',[]) if item['scenario']['target']==target]
    payload['target_exposure']=json.loads(d.exposure(target).to_json(orient='records'))
    payload['learning_plan']=learning.build_plan(p.gaps(profile,target,m),target,st.session_state.get('plan_horizons',{}).get(target,12),profile['weekly_hours'],done)
    weight=st.session_state.get('recommendation_weight',0.8)
    payload['recommendation_skill_weight']=weight
    payload['comparison_summary']=json.loads(p.recommend(profile,m,weight).head(10).to_json(orient='records')) if len(profile['ratings'])>=3 else []
    st.subheader(payload['target']['title'])
    st.write(f'Profile: {profile["name"] or "Unnamed"} · Assessed skills: {len(profile["ratings"])}')
    st.dataframe(pd.DataFrame(payload['skill_priorities']),hide_index=True,alt='Personal report skill-priority summary')
    if saved is None:
        st.info('No saved scenario for this target. The report will explicitly record scenario as unavailable.')
    st.download_button('Download complete report (JSON)',json.dumps(payload,ensure_ascii=False,indent=2,allow_nan=False).encode('utf-8'),
                       'career_report.json','application/json',key='download_report_json')
    lines=['# Personal career planning report','',f'Target: {target} — {payload["target"]["title"]}',
           f'Profile: {profile["name"] or "Unnamed"}',f'Current occupation: {profile["current_soc"]}',
           f'Current annual income (user input, USD): {profile["annual_income"]}',
           f'Desired annual income (user input, USD): {profile["desired_income"]}',
           f'Learning hours per week: {profile["weekly_hours"]}','', '## Career history and interests',profile['history'],'','## Skill priorities']
    for r in payload['skill_priorities']:
        lines.append(f'- {r["skill"]}: importance {r["importance"]:.2f}; self-rating {r["self_rating"]}; priority {r["priority"]}')
    lines+=['','## Target AI exposure (raw source indices)',json.dumps(payload['target_exposure'],ensure_ascii=False,indent=2),'','## Career comparison summary',json.dumps(payload['comparison_summary'],ensure_ascii=False,indent=2),f'Skill weight: {weight}','','## Scenario',json.dumps(saved,ensure_ascii=False,indent=2),'','## Saved comparison scenarios for this target',json.dumps(payload['scenario_comparisons'],ensure_ascii=False,indent=2),'','## Learning plan and completion evidence',json.dumps(payload['learning_plan'],ensure_ascii=False,indent=2),'','## Completed learning tasks',json.dumps(payload['completed_tasks'],indent=2),'','## Methods and limitations']
    lines += [f'- {k}: {v}' for k,v in payload['methodology'].items()]
    st.download_button('Download readable report (Markdown)','\n'.join(lines).encode('utf-8'),'career_report.md','text/markdown',key='download_report_md')
    st.session_state['report_prepared_target']=target
    st.caption('Exports include your personal inputs; keep them private. The report is a planning aid and contains its calculation assumptions and limitations.')

UI_COPY_REVISION = 'english-20261120'
