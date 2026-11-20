import json
import sqlite3
from pathlib import Path
import pytest
from streamlit.testing.v1 import AppTest
from core import data_access as d, planning as p, preparation
from core.demo_workspace import example_workspace


def test_preparation_keeps_specializations_and_missing_matches():
    rows=preparation.profiles('11-1011')
    assert rows and rows[0]['O*NET-SOC Code']=='11-1011.00'
    assert rows[0]['reference']['Job Zone']==rows[0]['Job Zone']
    assert preparation.profiles('13-1020')==[]
    data=preparation.source()
    assert len(data['profiles'])==923
    assert len({r['O*NET-SOC Code'] for r in data['profiles']})==923
    assert {r['Job Zone'] for r in data['zones']}=={'2','3','4','5'}
    assert '1-2' in next(r for r in data['zones'] if r['Job Zone']=='2')['Name']
    assert all(r['reference'] is not None for code in ['11-1011','15-1252'] for r in preparation.profiles(code))


def test_mixed_score_bases_never_share_a_ranking():
    profile=example_workspace()['profile'];m=p.matrix()
    ranked,other,basis=p.comparison_groups(profile,m,.8)
    assert basis=='Skills + wage'
    assert not ranked.empty and not other.empty
    assert ranked.wage_preference.notna().all()
    assert other.wage_preference.isna().all()
    assert not set(ranked.code)&set(other.code)
    assert len(ranked)+len(other)==len(p.recommend(profile,m,.8))
    assert ((ranked.comparison_score-(.8*ranked.skill_alignment+.2*ranked.wage_preference)).abs()<1e-12).all()
    for prof,weight in [(profile,1.),({**profile,'desired_income':0},.8)]:
        allskills,excluded,basis=p.comparison_groups(prof,m,weight)
        assert basis=='Skills only' and excluded.empty
        assert len(allskills)==len(ranked)+len(other)
        assert allskills.comparison_score.equals(allskills.skill_alignment)


def test_new_evidence_visible_and_report_uses_same_basis():
    at=AppTest.from_file(str(d.ROOT/'app.py'),default_timeout=40).run()
    at.button(key='start_guided_example').click().run()
    assert not at.exception and not at.error
    assert any('Current comparison basis: Skills + wage' in x.value for x in at.info)
    assert any(x.value=='Education, experience and training' for x in at.subheader)
    assert any('additional occupations without wage' in x.label for x in at.expander)
    at.radio[0].set_value('Personal Report').run()
    assert not at.exception and not at.error
    assert any(x.value=='Education, experience and training' for x in at.subheader)
    report=p.report(example_workspace()['profile'],'11-1011',p.matrix())
    assert report['preparation_references']==preparation.profiles('11-1011')
    json.dumps(report,allow_nan=False)


def test_preparation_matches_original_archive_if_available():
    original=Path('C:/Users/Lenovo/AI-Career-Compass/data/processed/career_compass_v1.sqlite')
    if not original.exists():pytest.skip('Local full archive not available')
    with sqlite3.connect(original.as_uri()+'?mode=ro',uri=True) as c:
        c.row_factory=sqlite3.Row
        expected=[dict(r) for r in c.execute('SELECT "O*NET-SOC Code",Title,"Job Zone",Date,"Domain Source" FROM raw_job_zones')]
        assert expected==preparation.source()['profiles']
        refs=[dict(r) for r in c.execute('SELECT "Job Zone",Name,Experience,Education,"Job Training",Examples,"SVP Range" FROM raw_job_zone_reference')]
        assert refs==preparation.source()['zones']
