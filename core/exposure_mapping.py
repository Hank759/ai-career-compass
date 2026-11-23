"""Curated, reviewed one-to-one historical references, never split/merge estimates."""
SOURCE='https://www.bls.gov/soc/2018/soc_2018_manual.pdf'
# Verified in both directions: Appendices A and B, PDF pages 230 and 252.
# Definitions may have editorial changes.
PAIRS={'15-1211':'15-1121','15-1212':'15-1122','15-1221':'15-1111',
       '15-1231':'15-1152','15-1232':'15-1151','15-1241':'15-1143',
       '15-1244':'15-1142','15-1251':'15-1131'}

def resolve(raw,codes):
    import pandas as pd
    if raw.duplicated(['code','metric']).any():raise ValueError('Ambiguous exposure source records')
    rows=[];groups={code:group for code,group in raw.groupby('code')}
    for code in codes:
        direct=groups.get(code,raw.iloc[:0]).copy()
        direct['source_code']=code;direct['match_method']='Exact source code'
        direct['crosswalk_url']=''
        rows.append(direct)
        old=PAIRS.get(code)
        if old:
            historical=groups.get(old,raw.iloc[:0])
            mapped=historical[~historical.metric.isin(direct.metric)].copy()
            mapped['source_code']=old;mapped['code']=code
            mapped['match_method']='Mapped historical reference'
            mapped['crosswalk_url']=SOURCE
            rows.append(mapped)
    return pd.concat(rows,ignore_index=True) if rows else pd.DataFrame(columns=[*raw.columns,'source_code','match_method','crosswalk_url'])
