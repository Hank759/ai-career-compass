from pathlib import Path
import re
from streamlit.testing.v1 import AppTest
from core import data_access as d


def test_product_interface_source_is_english_only():
    files=[d.ROOT/'app.py',*list((d.ROOT/'core').glob('*.py'))]
    for f in files:
        assert not re.search(r'[\u3400-\u4dbf\u4e00-\u9fff]',f.read_text(encoding='utf-8-sig')),f.name


def test_english_guided_home_and_skill_table():
    at=AppTest.from_file(str(d.ROOT/'app.py'),default_timeout=40).run()
    assert at.button(key='home_explore').label=='Explore AI exposure'
    assert at.button(key='home_plan').label=='Create my profile'
    at.button(key='home_plan').click().run()
    assert not at.exception and not at.error
    assert 'skill_cn' not in at.dataframe[0].value.columns
    assert 'rating' in at.dataframe[0].value.columns

def test_stale_import_is_refreshed_without_clearing_state():
    from core import journey_ui
    from core.ui_loader import fresh_ui,REVISION
    journey_ui.UI_COPY_REVISION='outdated'
    refreshed=fresh_ui('core.journey_ui')
    assert refreshed.UI_COPY_REVISION==REVISION
    assert 'Explore an occupation' in refreshed.home.__code__.co_consts
