"""Streamlit views backed by explicit source policies."""
import sqlite3
import pandas as pd
import streamlit as st
from core import data_access as data

@st.cache_data(ttl=300,max_entries=64)
def load(kind,version,*args):
    return getattr(data,kind)(*args)

def choose(label,df,key):
    titles=df.set_index('code')['title'].to_dict()
    return st.selectbox(label,list(df.code),format_func=lambda c: f'{c} — {titles[c]}',key=key)

def render(page):
    st.title(page)
    try:
        version=data.fingerprint()
        if page=='Data & Methodology':
            methodology(version)
            return
        occupations=load('catalog',version)
        soc=choose('Occupation (BLS published classification)',occupations,'career_soc')
        exposure_panel(soc,version,page)
        if page=='Career Dashboard':
            dashboard(soc,version)
        elif page=='Regional Analysis':
            scope=st.selectbox('Geography',['State','Metro'],key='region_scope')
            df=load('observations',version,scope,soc)
            from core.regional import comparison_panel
            comparison_panel(df,scope)
            show_observations(df)
            st.caption('May 2025 · Cross-industry · Ownership 1235. Areas are separate comparisons; no combined employment total is calculated.')
        elif page=='Industry Analysis':
            scope=st.selectbox('Industry data',['National industry','State industry (research)'],key='industry_scope')
            area=None
            if scope.startswith('State'):
                area=choose('State',load('options',version,scope,'area'),'industry_area')
                st.warning('Research estimates are shown separately from standard estimates. Only the allsectors source is used.')
            show_observations(load('observations',version,scope,soc,area))
            st.caption('May 2025 · Sector level only. Ownership coverage follows the selected source; do not combine with ownership-specific files or other industry levels.')
    except (FileNotFoundError,sqlite3.Error,ValueError,KeyError) as exc:
        st.error(f'Data could not be loaded: {exc}')

def show_observations(df):
    if df.empty:
        st.info('No published record is available for this selection.')
        return
    if len(df)>1:
        label='industry_title' if df.industry_title.nunique()>1 else 'area_title'
        chart=df[[label,'a_median']].dropna(subset=['a_median']).sort_values('a_median',ascending=False).head(10)
        if not chart.empty:
            st.subheader('Published median annual wages · Top 10 in this selection')
            st.caption('Nominal USD, without cost-of-living adjustment. Only published records for the selected occupation are compared.')
            st.bar_chart(chart,x=label,y='a_median',horizontal=True,x_label='Median annual wage (USD)',y_label='Industry' if label=='industry_title' else 'Area',alt='Ten highest published median annual wages in the current occupation and geography or industry selection')
    cols=['area_title','industry_title','tot_emp','a_mean','a_median','h_mean','research','source_file','source_row']
    display=df[cols].rename(columns={'tot_emp':'Employment','a_mean':'Mean annual wage (USD)',
        'a_median':'Median annual wage (USD)','h_mean':'Mean hourly wage (USD)',
        'area_title':'Area','industry_title':'Industry','research':'Research estimate',
        'source_file':'Source','source_row':'Source row'})
    st.dataframe(display,hide_index=True,alt='Published employment and wages for the selected occupation')
    st.caption('Blank wage/employment cells mean unavailable or suppressed. They are never replaced with zero. Annual wages are nominal USD, without cost-of-living adjustment.')

def dashboard(soc,version):
    df=load('observations',version,'National',soc)
    show_observations(df)
    profiles=load('onet_profiles',version,soc)
    if profiles.empty:
        st.info('This BLS occupation has no direct O*NET base-code match. Its published wages remain available; no skills or exposure values are inferred from component occupations.')
    else:
        st.subheader('O*NET occupation profiles')
        st.caption('The seven-character SOC base code links to one or more O*NET specializations. BLS wages above refer to the parent occupation, not an individual specialization.')
        code=choose('Profile',profiles,'onet_profile')
        st.write(profiles.set_index('code').loc[code,'description'])
        from core import preparation
        preparation.panel(soc,code)
        skill=load('skills',version,code)
        st.subheader('Skill importance')
        st.caption('O*NET importance describes how important a skill is to this occupation. It is not your proficiency, a hiring threshold or an AI exposure score.')
        st.markdown('**Skill category:** Essential includes foundational skills such as reading and active listening. Transferable includes cross-functional skills such as problem solving and service orientation. Neither category is automatically more important, and category labels do not add a separate recommendation weight.')
        if skill.empty:
            st.info('No usable skill importance ratings are available for this profile.')
        else:
            category=st.segmented_control('Skill category',['All skills','Essential','Transferable'],default='All skills',key='dashboard_skill_category') or 'All skills'
            selected=skill if category=='All skills' else skill[skill.family==category]
            show_all=st.toggle('Show all available skills',key='dashboard_skills_all')
            visible=selected if show_all else selected.head(20)
            st.caption(f'Showing {len(visible)} of {len(selected)} available skills in this selection, ordered by importance. Suppressed and not-relevant rows are excluded.')
            if visible.empty:
                st.info('No ratings are available in this skill category.')
            else:
                summary=visible[['skill','importance','family']].rename(columns={'skill':'Skill','importance':'Importance','family':'Skill category'})
                st.dataframe(summary,hide_index=True,column_config={
                    'Importance':st.column_config.NumberColumn('Importance (1–5)',format='%.2f',help='O*NET IM importance: 1 = not important; 5 = extremely important. This is not a personal proficiency rating.')},
                    alt='Occupational skill importance and category for the selected profile')
                st.download_button('Download selected skills',selected.rename(columns={'family':'skill_category'}).to_csv(index=False).encode('utf-8-sig'),
                    'occupation_skills.csv','text/csv',key='download_dashboard_skills')
            with st.expander('Skill source details'):
                details=selected.rename(columns={'element_id':'Skill ID','skill':'Skill','importance':'Importance','date':'Source date','domain_source':'Rating source','family':'Skill category'})
                st.dataframe(details,hide_index=True,alt='Source identifiers, dates and rating origins for the selected skills')
                st.caption('The source date belongs to the skill rating, not to the wage data. Rating source identifies the source type recorded by O*NET. Skill category preserves the original Essential Skills or Transferable Skills table grouping.')


def exposure_panel(soc,version,context='Career Dashboard'):
    st.subheader('AI exposure')
    scores=load('exposure',version,soc)
    labels=[('AIOE','General AI exposure (AIOE)'),
            ('Language Modeling AIOE','Language-model exposure'),
            ('Image Generation AIOE','Image-generation exposure')]
    if scores.metric.duplicated().any():
        raise ValueError('Multiple exposure observations for one metric; review the source before display.')
    values=scores.set_index('metric')['score'].to_dict()
    with st.container(horizontal=True):
        for metric,label in labels:
            value=values.get(metric)
            st.metric(label,f'{float(value):.3f}' if pd.notna(value) else 'Not available',
                      border=True,help='Original source index. Negative values are valid. This is not a percentage or a probability of job loss.')
    st.caption('Source: Felten exposure datasets. These are three distinct indices, not a combined risk score or job-loss probability. Exact SOC-code matching only; source and current classification versions are not fully reconciled.')
    if scores.empty:
        st.info(f'No exact-code exposure estimate is available for SOC {soc}. Missing data is not zero exposure, and no value is inferred from a similar job title.')
    if context in ('Regional Analysis','Industry Analysis'):
        st.caption('Occupation-level reference only: these values do not change by region or industry. They are not regional AIGE or industry AIIE estimates.')
    with st.expander('How to read these exposure indices'):
        st.write('Compare occupations within the same metric. A higher index indicates greater exposure in that source measure; it does not establish that a worker will lose a job or that one AI technology is more dangerous than another.')
        st.write('These datasets link AI applications with occupational abilities. The app does not have a validated occupation-specific task contribution breakdown, so it cannot attribute the displayed score to individual tasks. Skill importance below is a separate O*NET measure.')
        st.markdown('[Original datasets and methodology — Felten, Raj and Seamans](https://github.com/AIOE-Data/AIOE)')
    with st.expander('Exposure source details'):
        st.dataframe(scores,hide_index=True,alt='Original AI exposure indices and source files for the selected SOC occupation')

def methodology(version):
    st.subheader('Geographic scope and currency')
    st.info('This version uses U.S. occupational and labour-market data, including territories where the source publishes them. All wage and scenario amounts are USD. It is not a Hong Kong or mainland China labour-market model.')
    st.write('BLS supplies employment and wages; O*NET supplies skills and education response distributions; Felten supplies exposure indices. Regional Analysis offers a purchasing-power proxy using bundled 2024 BEA all-items regional price parities against 2025 wages. National and industry wages remain nominal.')
    st.subheader('Source selection')
    policy=pd.DataFrame([{'View':k,'Source':v[1]} for k,v in data.TABLES.items()])
    st.dataframe(policy,hide_index=True,alt='Source file selected for each application view')
    st.write('State-industry allsectors duplicates the twelve partition files: the full-row hash multiplicities match for all 867,905 rows. This application uses allsectors only and exposes sectors only, avoiding overlap between industry levels.')
    st.write('National, state and metro wages use standard cross-industry files with ownership code 1235. Industry views use the coverage published in the selected sector source; research estimates remain labeled. Raw records are retained unchanged.')
    st.subheader('Occupation mapping audit')
    audit=load('mapping_audit',version)
    review=audit[audit.status!='base_code_match']
    st.dataframe(review,hide_index=True,alt='Occupations requiring mapping review and candidate component codes')
    st.download_button('Download complete mapping audit',audit.to_csv(index=False).encode('utf-8-sig'),
                       'occupation_mapping_audit.csv','text/csv',key='download_mapping')
    st.markdown('[BLS classification and combined-occupation explanations](https://www.bls.gov/oes/oes_ques.htm)')
    st.caption('Candidate components come from the BLS FAQ historical classification table; they are not a verified 2025-to-current-O*NET crosswalk. They are shown for review only. No combined score, component employment split, or automatic skill average is calculated.')
    st.write('Personal Profile, annual historical estimates, heuristic career comparisons, learning plans and assumption-based transition scenarios are now available. Profiles persist only in session unless exported. BEA purchasing-power adjustment remains unimplemented; scenario costs are not individual job-loss predictions.')

UI_COPY_REVISION = 'english-20261120'
