"""Focused career comparisons and user-triggered sensitivity analysis."""
import streamlit as st
from core import comparison_tools as c

@st.cache_data(ttl=300,max_entries=8)
def analysis(profile,m,weight,ranked):
    return c.sensitivity(profile,m,weight,ranked)

def panel(profile,m,weight,ranked,context):
    st.subheader('Compare careers side by side')
    st.caption('Choose two or three careers from the current scoring group. Compare trade-offs before selecting your planning target below.')
    available=list(ranked.code);titles=ranked.set_index('code').occupation.to_dict()
    chosen=[code for code in profile.get('comparison_codes',available[:3]) if code in available]
    chosen=st.multiselect('Careers to compare',available,default=chosen,max_selections=3,format_func=lambda code:titles[code]+' · '+code,key='career_compare_codes')
    if chosen!=profile.get('comparison_codes'):
        profile['comparison_codes']=chosen
        st.session_state['profile']=profile
    if len(chosen)<2:
        st.session_state['career_sensitivity_requested']=False
        st.info('Choose at least two careers for a side-by-side comparison. Your planning target is selected independently below.')
        return
    rows=c.side_by_side(profile,m,ranked,chosen,st.session_state)
    display=c.display_comparison(rows,context['basis']=='Price-adjusted proxy')
    st.dataframe(display,hide_index=True,alt='Side-by-side career scores, wages, exposure, education pathways, preparation groups and learning priorities')
    st.caption('Exposure indices are separate measures, not percentages or a ranking penalty. Blank fees/duration mean no currently saved scenario for that career; the app does not estimate training prices or time to qualification.')
    st.download_button('Download side-by-side comparison',display.to_csv(index=False).encode('utf-8-sig'),'career_side_by_side.csv','text/csv',key='download_career_comparison')
    st.subheader('How sensitive is this shortlist?')
    st.caption('Test one assessed skill at a time by ±1 point and the skill weight by ±0.05 where wage data supports it. Saved inputs and the candidate group remain unchanged. This is a deterministic what-if check, not confidence or a hiring prediction.')
    run=st.toggle('Run sensitivity check',value=st.session_state.get('career_sensitivity_requested',False),key='run_career_sensitivity')
    st.session_state['career_sensitivity_requested']=run
    if run:
        results,cases=analysis(profile,m,weight,ranked)
        selected=results[results.code.isin(chosen)]
        st.dataframe(selected.rename(columns={'occupation':'Occupation','saved_score_rank':'Saved score rank','best_tested_rank':'Best tested rank','worst_tested_rank':'Worst tested rank','top_10_band_cases':'Top-10 score band (cases)','tested_cases':'Tested cases'}),hide_index=True,column_order=['Occupation','Saved score rank','Best tested rank','Worst tested rank','Top-10 score band (cases)','Tested cases'],alt='Score rank ranges under small one-at-a-time changes to assessed skills and score weights')
        st.caption(f'{len(cases)} cases include the saved inputs. Scores rounded to 12 decimal places share ranks when tied, avoiding floating-point noise; a top-10 score band can contain more than ten careers. Rank ranges only cover these tests, not every possible input change. Weight changes are skipped unless every candidate has wage data. A switch to skills-only scoring can add candidates outside this fixed group.')
        with st.expander('Tested changes'):
            st.write('\n\n'.join(cases))
        st.download_button('Download sensitivity results',results.to_csv(index=False).encode('utf-8-sig'),'career_sensitivity.csv','text/csv',key='download_career_sensitivity')
