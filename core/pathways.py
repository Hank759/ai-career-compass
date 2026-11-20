"""Education survey comparisons and explicitly self-reported qualification reviews."""
import json
from functools import lru_cache
from pathlib import Path
import pandas as pd

FILTERS=['All education pathways','Current education matches','Current or planned education matches']
REVIEWS=['Not reviewed','Additional qualification needed','Reviewed — no gap identified (self-reported)']

@lru_cache(maxsize=1)
def source():
    return json.loads((Path(__file__).resolve().parents[1]/'data/reference/education.json').read_text(encoding='utf-8'))

def categories():
    return {r['Category']:r['Category Description'] for r in source()['categories']}

@lru_cache(maxsize=1)
def distributions():
    rows=pd.DataFrame(source()['rows'])
    rows['share']=pd.to_numeric(rows['Data Value'],errors='coerce')
    rows=rows[(rows['Recommend Suppress']!='Y') & rows.share.between(0,100)].copy()
    rows['education']=rows.Category.map(categories())
    return rows

@lru_cache(maxsize=1)
def modal_profiles():
    rows=distributions()
    complete=rows.groupby('O*NET-SOC Code').Category.transform('nunique')==len(categories())
    total=rows.groupby('O*NET-SOC Code').share.transform('sum')
    rows=rows[complete & total.between(99.9,100.1)]
    # Retain all tied modal responses; never impose a linear degree equivalence.
    top=rows.groupby('O*NET-SOC Code').share.transform('max')
    rows=rows[(rows.share==top) & (top>0)]
    return {soc:group.to_dict('records') for soc,group in rows.groupby(rows['O*NET-SOC Code'].str[:7])}

def annotate(frame,profile):
    out=frame.copy();current=profile.get('education_category');planned=set(profile.get('planned_education',[]))
    modal=modal_profiles()
    def match(code):
        rows=modal.get(code,[])
        if not rows:return 'No usable education reference'
        if not current and not planned:return 'Education not entered'
        options={r['Category'] for r in rows}
        if current in options:return 'Current education matches'
        if options & planned:return 'Planned education matches'
        return 'Other education pathway'
    out['education_pathway']=out.code.map(match)
    reviews=profile.get('qualification_reviews',{})
    out['qualification_review']=out.code.map(lambda code:reviews.get(code,{}).get('status',REVIEWS[0]))
    mode=profile.get('education_filter',FILTERS[0])
    if mode==FILTERS[1]:out=out[out.education_pathway=='Current education matches']
    elif mode==FILTERS[2]:out=out[out.education_pathway.isin(['Current education matches','Planned education matches'])]
    if profile.get('exclude_qualification_gaps',False):out=out[out.qualification_review!=REVIEWS[1]]
    return out

def panel(profile,target):
    import streamlit as st
    st.subheader('Your education pathway and qualification review')
    st.caption('Matching uses the most frequently reported education category for at least one O*NET specialization, including ties. It requires all education categories to be usable and response shares to total approximately 100%. It does not compare degree quality, subject, equivalence or legal eligibility. A different or higher degree does not automatically substitute for another category.')
    rows=distributions();rows=rows[rows['O*NET-SOC Code'].str[:7]==target]
    status=annotate(pd.DataFrame({'code':[target]}),{**profile,'education_filter':FILTERS[0],'exclude_qualification_gaps':False}).iloc[0].education_pathway
    st.write('Education pathway: '+status)
    if not rows.empty:
        with st.expander('Published education response distributions'):
            st.dataframe(rows[['O*NET-SOC Code','Title','education','share','N','Date','Domain Source']].rename(columns={'education':'Reported education category','share':'Response share (%)','N':'Respondents'}),hide_index=True,alt='Published education category response shares, kept separate by O*NET specialization')
            st.caption('Response shares are survey results, not admission or hiring probabilities. Suppressed rows are excluded; remaining shares are not renormalized. Source: '+source()['source'])
    saved=profile.get('qualification_reviews',{}).get(target,{})
    with st.form('qualification_review_'+target):
        review=st.selectbox('Your qualification review for this target',REVIEWS,index=REVIEWS.index(saved.get('status',REVIEWS[0])),key='qualification_status_'+target)
        notes=st.text_area('Qualifications, licences or requirements to verify',value=saved.get('notes',''),max_chars=2000,help='Record the occupation, location, authority, required credential and what you still need to check.',key='qualification_notes_'+target)
        submit=st.form_submit_button('Save qualification review')
    if submit:
        updated={**profile,'qualification_reviews':{**profile.get('qualification_reviews',{}),target:{'status':review,'notes':notes}}}
        st.session_state['profile']=updated
        st.session_state.pop('report_prepared_target',None)
        st.success('Self-reported review saved. It will be included in workspace backups and reports.')
    st.caption('Qualification status is your own review, not verification by the app. Check the relevant licensing authority and employer for the occupation and location. No automatic licence or credential verification is available.')
