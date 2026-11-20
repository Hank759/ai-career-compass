"""Explicit source selection; read-only SQLite access, no crosswalk fan-out."""
from contextlib import contextmanager
from pathlib import Path
import sqlite3
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / 'data/processed/career_compass_v1.sqlite'
BLS_FAQ = 'https://www.bls.gov/oes/oes_ques.htm'
# Historical BLS FAQ composition: candidates for review, not a validated 2025 crosswalk.
COMBINED = {
 '13-1020':['13-1021','13-1022','13-1023'], '13-2020':['13-2022','13-2023'],
 '21-1018':['21-1011','21-1014'], '25-2052':['25-2055','25-2056'],
 '25-9045':['25-9042','25-9043','25-9049'], '29-2010':['29-2011','29-2012'],
 '31-1120':['31-1121','31-1122'], '39-7010':['39-7011','39-7012'],
 '47-4090':['47-4091','47-4099'], '51-2028':['51-2022','51-2023'],
 '51-2090':['51-2092','51-2099'], '53-1047':['53-1042','53-1043','53-1044','53-1049']}
TABLES = {
 'National': ('raw_national_m2025_dl','data/raw/bls/national_M2025_dl.xlsx'),
 'State': ('raw_state_m2025_dl','data/raw/bls/state_M2025_dl.xlsx'),
 'Metro': ('raw_msa_m2025_dl','data/raw/bls/MSA_M2025_dl.xlsx'),
 'National industry': ('raw_natsector_m2025_dl','data/raw/bls/natsector_M2025_dl.xlsx'),
 'State industry (research)': ('raw_oes_research_2025_allsectors','data/raw/bls/state_industry/oes_research_2025_allsectors.xlsx')}

@contextmanager
def connect(db=DB):
    path=Path(db).resolve()
    if not path.is_file():
        raise FileNotFoundError('Build data/processed/career_compass_v1.sqlite first.')
    c=sqlite3.connect(path.as_uri()+'?mode=ro',uri=True)
    c.execute('PRAGMA query_only=ON')
    try:
        info=dict(c.execute('SELECT key,value FROM build_info'))
        if info.get('scope') not in ('full','application') or info.get('schema_version')!='1':
            raise ValueError('This application requires a complete schema-version-1 database.')
        yield c
    finally:
        c.close()

def frame(sql,params=(),db=DB):
    with connect(db) as c:
        return pd.read_sql_query(sql,c,params=params)

def fingerprint():
    s=DB.stat()
    return (s.st_mtime_ns,s.st_size)

def catalog(db=DB):
    return frame('''SELECT OCC_CODE AS code,OCC_TITLE AS title
        FROM raw_national_m2025_dl WHERE O_GROUP='detailed' AND NAICS='000000' AND OWN_CODE='1235'
        ORDER BY OCC_TITLE''',db=db)

def options(scope,kind,db=DB):
    table,_=TABLES[scope]
    if kind not in ('area','industry'):
        raise ValueError('Unknown option kind')
    code,title=('AREA','AREA_TITLE') if kind=='area' else ('NAICS','NAICS_TITLE')
    # Industry panels expose sectors only: no overlapping industry levels.
    where=" WHERE I_GROUP='sector'" if 'industry' in scope else ''
    return frame(f'SELECT DISTINCT {code} AS code,{title} AS title FROM "{table}"{where} ORDER BY {title}',db=db)

def observations(scope,soc,area=None,naics=None,db=DB):
    table,path=TABLES[scope]
    where=['s.path=?',"b.o_group='detailed'",'b.occ_code=?']
    params=[path,soc]
    if area is not None:
        where.append('b.area=?');params.append(area)
    if 'industry' in scope:
        where.append("b.i_group='sector'")
        if naics is not None:
            where.append('b.naics=?');params.append(naics)
    else:
        where.extend(["b.naics='000000'","b.own_code='1235'"])
    df=frame(f'''SELECT b.source_id,b.source_row,b.year,b.area,r.AREA_TITLE AS area_title,
        b.naics,r.NAICS_TITLE AS industry_title,b.i_group,b.own_code,b.occ_code,
        r.OCC_TITLE AS occupation,b.tot_emp,b.a_mean,b.a_median,b.h_mean,b.research,s.path AS source_file
        FROM bls_observations b JOIN sources s ON b.source_id=s.id
        JOIN "{table}" r ON r._src_row=b.source_row
        WHERE {' AND '.join(where)} ORDER BY b.area,b.naics''',params,db)
    keys=['year','area','naics','i_group','own_code','occ_code']
    if df.duplicated(keys).any():
        raise ValueError('Selected source contains duplicate observation keys; review before displaying.')
    return df

def onet_profiles(soc,db=DB):
    # A list of profiles only. Never join this list to wage/employment observations.
    df=frame('''SELECT "O*NET-SOC Code" AS code,Title AS title,Description AS description
       FROM raw_occupation_data WHERE substr("O*NET-SOC Code",1,7)=? ORDER BY "O*NET-SOC Code"''',(soc,),db)
    return df

def exposure(soc,db=DB):
    return frame('''SELECT e.metric,e.score,s.path AS source_file FROM exposure_scores e
       JOIN sources s ON s.id=e.source_id WHERE e.code_type='SOC Code' AND e.code=? ORDER BY e.metric''',(soc,),db)

def skills(onet_code,db=DB):
    pieces=[]
    for table,label in [('raw_essential_skills','Essential'),('raw_transferable_skills','Transferable')]:
        df=frame(f'''SELECT "Element ID" AS element_id,"Element Name" AS skill,
           "Data Value" AS importance,"Date" AS date,"Domain Source" AS domain_source
           FROM {table} WHERE "O*NET-SOC Code"=? AND "Scale ID"='IM'
           AND COALESCE("Recommend Suppress",'N')<>'Y' AND COALESCE("Not Relevant",'N')<>'Y' ''',(onet_code,),db)
        df['family']=label
        df['importance']=pd.to_numeric(df['importance'],errors='coerce')
        pieces.append(df)
    return pd.concat(pieces,ignore_index=True).dropna(subset=['importance']).sort_values('importance',ascending=False)

def mapping_audit(db=DB):
    profiles=frame('SELECT "O*NET-SOC Code" AS code,Title AS title FROM raw_occupation_data',db=db)
    rows=[]
    for r in catalog(db).itertuples(index=False):
        matches=profiles[profiles.code.str[:7]==r.code]
        candidates=COMBINED.get(r.code,[])
        related=profiles[profiles.code.str[:7].isin(candidates)]
        rows.append({'bls_code':r.code,'bls_title':r.title,
          'status':'base_code_match' if len(matches) else 'combined_requires_review' if candidates else 'unresolved',
          'onet_profiles':'; '.join(matches.code), 'candidate_soc_codes':'; '.join(candidates),
          'candidate_onet_profiles':'; '.join(related.code),
          'missing_candidate_soc_codes':'; '.join(x for x in candidates if not any(profiles.code.str[:7]==x)),
          'reference':BLS_FAQ if candidates else '',
          'mapping_use':'profile list only; no wage replication or exposure averaging'})
    return pd.DataFrame(rows)
