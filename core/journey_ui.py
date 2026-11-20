"""Guided entry routes and contextual next steps, without changing personal inputs."""
import sqlite3
import pandas as pd
import streamlit as st
from core import data_access as d

PAGES=['Home','Personal Profile','Career Dashboard','Regional Analysis','Industry Analysis','Historical Trends',
       'Career Recommendations','Transition Simulator','Career Development Plan','Personal Report','Data & Methodology']
HELP={
 'Personal Profile':('Step 1 · Understand your starting point','Enter your occupation, annual income in USD and weekly learning hours. Double-click a rating cell, assess at least three skills and select Save profile. Blank means unassessed; 0 means unfamiliar.'),
 'Career Dashboard':('Explore · Start with AI exposure','Choose an occupation, review its three AI exposure indices, then explore wages and skills. Not available means no matching estimate. Exposure is not a job-loss probability. No profile is required.'),
 'Regional Analysis':('Explore · Compare locations','Choose an occupation and State or Metro geography to compare published nominal wages. The exposure cards are occupation-level references and do not vary by location.'),
 'Industry Analysis':('Explore · Compare industries','Choose an occupation, then national industry or state-industry research estimates. Sources remain separate. The exposure cards are not industry AIIE estimates.'),
 'Historical Trends':('Explore · Review annual estimates','Choose an occupation and measure to review separately published 2022–2025 estimates. The chart is not a personal wage trajectory or evidence of a causal AI effect.'),
 'Career Recommendations':('Step 2 · Compare possible directions','Review scores and skill-assessment coverage, then choose a target to examine exposure and learning priorities. Adjust the weights if needed. Scores are comparison rules, not hiring probabilities.'),
 'Transition Simulator':('Step 3 · Test your transition assumptions','Enter assumed income, duration and fees. Select Calculate and save scenario to review costs, income changes and payback. Results depend on your assumptions.'),
 'Career Development Plan':('Step 4 · Turn your direction into action','Set a planning horizon, practise within your weekly time budget, save work or feedback as evidence and check off progress. Allocated hours are not estimates of time to mastery.'),
 'Personal Report':('Step 5 · Review and save','Review your target and saved scenario, then download a JSON or Markdown report. Return to Personal Profile to back up the complete workspace.'),
 'Data & Methodology':('Understand the results · Data and methodology','Review source selection, duplicate handling, occupation mappings and analytical limitations. No personal profile is required.')}


def go(page):
    if page not in PAGES:raise ValueError('Unknown page')
    st.session_state['main_navigation']=page


def explore(soc):
    st.session_state['career_soc']=soc
    go('Career Dashboard')


def journey_state(state):
    profile=state.get('profile') or {}
    ready=len(profile.get('ratings',{}))>=3
    target=state.get('planning_target')
    scenario=state.get('saved_scenario') or {}
    plan=bool(target and target in state.get('plan_horizons',{}))
    report=bool(target and state.get('report_prepared_target')==target)
    flags=[ready,bool(ready and target),bool(ready and target and scenario.get('target')==target),bool(ready and plan),bool(ready and report)]
    if not ready:next_page='Personal Profile'
    elif not target:next_page='Career Recommendations'
    elif scenario.get('target')!=target:next_page='Transition Simulator'
    elif not plan and state.get('plan_unavailable_target')!=target:next_page='Career Development Plan'
    else:next_page='Personal Report'
    return {'flags':flags,'completed':sum(flags),'next_page':next_page}


@st.cache_data(ttl=300,max_entries=2)
def overview(version):
    catalog=d.catalog()
    coverage=d.frame('''SELECT COUNT(DISTINCT r.OCC_CODE) AS n FROM raw_national_m2025_dl r
       JOIN exposure_scores e ON e.code=r.OCC_CODE AND e.code_type='SOC Code' WHERE r.O_GROUP='detailed' ''').iloc[0]['n']
    return catalog,int(coverage)


def home():
    st.badge('Start with one question, not every feature',icon=':material/explore:',color='primary')
    st.title('AI Career Compass')
    st.subheader('Understand AI exposure. Find your next career step.')
    st.badge('U.S. labour-market data · Currency: USD',color='blue')
    st.caption('Includes U.S. states, the District of Columbia and territories where published. This version does not estimate Hong Kong or mainland China wages or job markets.')
    st.write('Explore an occupation or plan a transition around your skills. Choose one route below; every feature remains available in the sidebar.')
    try:
        cat,covered=overview(d.fingerprint())
    except (OSError,sqlite3.Error,ValueError) as exc:
        st.error(f'Career data could not be loaded. Complete the database build first: {exc}');return
    left,right=st.columns(2,gap='large')
    with left:
        with st.container(border=True,height='stretch'):
            st.badge('Route A · No profile needed',color='blue')
            st.subheader('Explore an occupation')
            st.write('Start with three AI exposure indices, then review wages and skills. Compare locations and industries when you are ready.')
            codes=list(cat.code);titles=cat.set_index('code').title.to_dict()
            preferred=(st.session_state.get('profile') or {}).get('current_soc','11-1011')
            soc=st.selectbox('Search or choose an occupation',codes,index=codes.index(preferred) if preferred in codes else 0,
                 format_func=lambda x:f'{titles[x]} · {x}',key='home_occupation')
            st.caption('Type an occupation title to search. Try Chief Executives first to see all three exposure indices.')
            st.button('Explore AI exposure',icon=':material/analytics:',type='primary',width='stretch',
                      key='home_explore',on_click=explore,args=(soc,))
    status=journey_state(st.session_state)
    with right:
        with st.container(border=True,height='stretch'):
            st.badge('Route B · Start with your skills',color='green')
            st.subheader('Plan a career transition')
            st.write('Assess skills → Compare careers → Test a scenario → Plan practice → Export your report.')
            st.markdown('**Start with two simple steps:**\n\n1. Enter your occupation, income and weekly learning time.\n2. Rate at least three skills and select **Save profile**.')
            st.caption('Your saved progress determines where to continue. Comparisons and scenarios explain their assumptions and limitations.')
            label='Create my profile' if not status['flags'][0] else 'Continue my plan'
            st.button(label,icon=':material/arrow_forward:',type='primary',width='stretch',key='home_plan',
                      on_click=go,args=(status['next_page'],))
    st.divider()
    st.subheader('My planning progress')
    st.progress(status['completed']/5,text=f'{status["completed"]}/5 preparation steps completed; not a measure of job readiness')
    labels=['Profile and 3+ skills saved','Target selected','Target scenario saved','Learning plan prepared','Target report prepared']
    with st.container(horizontal=True):
        for flag,label in zip(status['flags'],labels):
            st.badge(label,color='green' if flag else 'gray',icon=':material/check_circle:' if flag else ':material/radio_button_unchecked:')
    st.caption('Session state may be lost when the session ends. In Personal Profile, select Back up complete workspace to save a file you can import later.')
    st.subheader('Or jump straight into the data')
    with st.container(horizontal=True):
        for label,page,key in [('Regional wages','Regional Analysis','home_regions'),('Industry wages','Industry Analysis','home_industries'),('Annual estimates','Historical Trends','home_history'),('Data and methodology','Data & Methodology','home_methods')]:
            st.button(label,on_click=go,args=(page,),key=key)
    with st.container(horizontal=True):
        st.metric('Published BLS occupations',f'{len(cat):,}',border=True)
        st.metric('With a matching exposure index',f'{covered:,}',border=True)
        st.metric('Wage reference period','May 2025',border=True)
    with st.expander('Try a fictional example before entering personal information'):
        import json
        from core.demo_workspace import example_workspace
        st.write('Download the example, then open Personal Profile and import it. It contains invented learner inputs and no saved scenario. Your current profile is not changed by downloading.')
        st.caption('Back up your own workspace before importing an example. The wage and exposure references remain real source data; the example income and skill ratings are fictional.')
        st.download_button('Download fictional example workspace',json.dumps(example_workspace(),indent=2).encode('utf-8'),'fictional_example_workspace.json','application/json',key='download_example')
    with st.expander('First time here? How to read the results'):
        st.markdown('**What is exposure?** Three source indices describe general AI, language-model and image-generation exposure. They are not job-loss probabilities or a combined risk percentage.\n\n**What are the occupation numbers?** SOC codes identify occupations for data matching; they are not rankings.\n\n**Why are some values blank?** A value may be unpublished, suppressed or unmatched across classifications. Missing is not zero.\n\n**Can the comparison decide for me?** No. It applies transparent rules to your assessed skills and wage preference. Fewer assessments provide less evidence.')


def intro(page):
    if page in HELP:
        stage,tip=HELP[page]
        st.caption(stage)
        st.info(tip)


def footer(page):
    st.divider()
    if page in ('Career Dashboard','Regional Analysis','Industry Analysis','Historical Trends'):
        with st.container(border=True):
            st.markdown('**What would you like to do next?**')
            st.caption('Use the data in your own career plan, or return home to keep exploring.')
            with st.container(horizontal=True):
                st.button('Start or continue my plan',on_click=go,args=(journey_state(st.session_state)['next_page'],),key='footer_plan')
                st.button('Back to Home',on_click=go,args=('Home',),key='footer_home')
        return
    status=journey_state(st.session_state)
    page_next={'Personal Profile':'Career Recommendations','Career Recommendations':'Transition Simulator',
               'Transition Simulator':'Career Development Plan','Career Development Plan':'Personal Report','Personal Report':'Personal Profile'}
    target=page_next.get(page,'Home')
    if not status['flags'][0] and page in page_next:target='Personal Profile'
    labels={'Personal Profile':'Edit profile / back up workspace','Career Recommendations':'Compare career directions','Transition Simulator':'Test transition costs',
            'Career Development Plan':'Plan learning activities','Personal Report':'Prepare my report','Home':'Back to Home'}
    with st.container(border=True):
        st.markdown('**Next step**')
        st.caption('Your data is not automatically saved permanently. After exporting your report, back up the complete workspace too.' if page=='Personal Report' else 'Work at your own pace. Use the sidebar to switch features at any time.')
        with st.container(horizontal=True):
            st.button(labels[target],type='primary',on_click=go,args=(target,),key='footer_next')
            if target!='Home':st.button('Back to Home',on_click=go,args=('Home',),key='footer_home')

UI_COPY_REVISION = 'english-20261120'
