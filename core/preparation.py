"""Published O*NET preparation references; never an eligibility assessment."""
import json
from functools import lru_cache
from pathlib import Path

@lru_cache(maxsize=1)
def source():
    return json.loads((Path(__file__).resolve().parents[1]/'data/reference/job_zones.json').read_text(encoding='utf-8'))

def profiles(soc):
    data=source()
    zones={r['Job Zone']:r for r in data['zones']}
    return [{**r,'reference':zones.get(r['Job Zone']), 'sources':data['sources']}
            for r in data['profiles'] if r['O*NET-SOC Code'][:7]==soc]

def panel(soc,onet_code=None):
    import streamlit as st
    rows=profiles(soc)
    if onet_code is not None:
        rows=[r for r in rows if r['O*NET-SOC Code']==onet_code]
    st.subheader('Education, experience and training')
    st.caption('Published O*NET Job Zone references describe typical preparation, not your eligibility, a mandatory degree or the time you personally need to qualify. Licensing and employer-specific requirements are not checked.')
    if not rows:
        st.info('No direct O*NET preparation reference is available for this occupation. No requirements are inferred from similar job titles.')
        return
    if len(rows)>1:
        st.caption('This SOC occupation contains multiple O*NET specializations. Review each relevant profile; preparation requirements are not averaged.')
    for row in rows:
        with st.expander(row['Title']+' · '+row['O*NET-SOC Code']):
            ref=row['reference']
            if ref is None:
                st.info('The source Job Zone has no matching reference description.')
            else:
                st.write(ref['Name'])
                st.caption('The descriptions below apply to the whole Job Zone. Examples may describe other occupations in this zone; they are not specific degree or training requirements for the selected occupation.')
                for field in ['Education','Experience','Job Training']:
                    st.markdown('**'+field+'**')
                    st.write(ref[field])
            st.caption('Source date: '+str(row['Date'])+' · Rating source: '+str(row['Domain Source'])+'. The bundled source combines Job Zones 1–2 under code 2; this app preserves that wording.')
            st.caption('Source files: '+', '.join(row['sources']))
            st.link_button('View this occupation on O*NET OnLine','https://www.onetonline.org/link/summary/'+row['O*NET-SOC Code'])
