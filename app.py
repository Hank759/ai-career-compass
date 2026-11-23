import streamlit as st
from core.cloud_data import ensure_database
ensure_database()
from core.ui_loader import fresh_ui
journey = fresh_ui('core.journey_ui')

st.set_page_config(page_title="AI Career Compass",page_icon=":material/explore:",layout="wide",initial_sidebar_state="expanded")
for key,value in {'profile':{},'career_history':[],'transition_scenarios':[],'main_navigation':'Home'}.items():
    st.session_state.setdefault(key,value)

st.sidebar.title("AI Career Compass")
st.sidebar.caption("Career exploration and transition planning")
page=st.sidebar.radio("Navigation",journey.PAGES,key='main_navigation')

page_changed=st.session_state.get('_last_rendered_page')!=page

if page=='Home':
    journey.home()
else:
    journey.intro(page)
    if page in ('Career Dashboard','Regional Analysis','Industry Analysis','Data & Methodology'):
        fresh_ui('core.data_ui').render(page)
    else:
        fresh_ui('core.data_ui')
        fresh_ui('core.planning_ui').render(page)
    journey.footer(page)

# The radio-based navigation does not reset the main scroll position natively.
# This fixed, local script only scrolls sections; no user content enters JavaScript.
if page_changed:
    st.html("<script>/* "+page+" */ requestAnimationFrame(() => { for (const el of document.querySelectorAll('main,section')) { if (el.scrollHeight > el.clientHeight) el.scrollTo({top:0,behavior:'instant'}); } window.scrollTo(0,0); });</script>",unsafe_allow_javascript=True)
st.session_state['_last_rendered_page']=page

status=journey.journey_state(st.session_state)
st.sidebar.divider()
st.sidebar.caption(f'Planning progress: {status["completed"]}/5 preparation steps')
st.sidebar.caption('Not sure where to start? Open Home and choose a route.')
st.sidebar.caption('Version 4.7 | Research Prototype')
st.sidebar.caption("CCAI9009 — Today's Future City")
