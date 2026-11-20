"""Transparent career-planning calculations, without predictive claims."""
import json
import math
import pandas as pd
from core import data_access as d
from core import preparation

def skill_reference():
    return d.frame('''SELECT DISTINCT "Element ID" AS id,"Element Name" AS skill FROM raw_essential_skills
       UNION SELECT DISTINCT "Element ID","Element Name" FROM raw_transferable_skills ORDER BY skill''')

def validate_profile(p):
    if not isinstance(p,dict) or p.get('version')!=1:
        raise ValueError('Unsupported profile format')
    allowed={'version','name','current_soc','annual_income','desired_income','weekly_hours','history','ratings',
        'education_category','planned_education','education_filter','qualification_reviews','exclude_qualification_gaps','preferred_region'}
    if set(p)-allowed:
        raise ValueError('Unknown profile fields')
    if not isinstance(p.get('current_soc'),str) or p.get('current_soc') not in set(d.catalog().code):
        raise ValueError('Select a published occupation')
    for k,high in [('annual_income',1e8),('desired_income',1e8),('weekly_hours',168)]:
        v=p.get(k)
        if isinstance(v,bool) or not isinstance(v,(float,int)) or not math.isfinite(v) or not 0<=v<=high:
            raise ValueError(f'Invalid {k}')
    if p['weekly_hours']<0.5:
        raise ValueError('Weekly learning hours must be at least 0.5')
    from core import pathways
    categories=set(pathways.categories())
    if p.get('education_category') is not None and (not isinstance(p['education_category'],str) or p['education_category'] not in categories):
        raise ValueError('Unknown education category')
    planned=p.get('planned_education',[])
    if not isinstance(planned,list) or len(planned)>12 or any(not isinstance(v,str) or v not in categories for v in planned) or len(set(planned))!=len(planned):
        raise ValueError('Invalid planned education categories')
    if p.get('education_filter',pathways.FILTERS[0]) not in pathways.FILTERS:
        raise ValueError('Invalid education filter')
    if not isinstance(p.get('exclude_qualification_gaps',False),bool):
        raise ValueError('Invalid qualification filter')
    reviews=p.get('qualification_reviews',{})
    if not isinstance(reviews,dict) or len(reviews)>830:raise ValueError('Invalid qualification reviews')
    known=set(d.catalog().code)
    for code,review in reviews.items():
        if code not in known or not isinstance(review,dict) or set(review)!={'status','notes'} or review['status'] not in pathways.REVIEWS or not isinstance(review['notes'],str) or len(review['notes'])>2000:
            raise ValueError('Invalid qualification review')
    region=p.get('preferred_region')
    if region is not None:
        if not isinstance(region,dict) or set(region)!={'scope','area','wage_basis'} or region['scope'] not in ('National','State','Metro') or region['wage_basis'] not in ('Nominal USD','Price-adjusted proxy'):
            raise ValueError('Invalid preferred region')
        if region['scope']=='National':
            if region['area'] is not None or region['wage_basis']!='Nominal USD':raise ValueError('National comparisons use nominal USD')
        elif not isinstance(region['area'],str) or region['area'] not in set(d.options(region['scope'],'area').code):
            raise ValueError('Unknown preferred area')
    for k,size in [('name',100),('history',5000)]:
        if not isinstance(p.get(k),str) or len(p[k])>size:
            raise ValueError(f'Invalid {k}')
    if not isinstance(p.get('ratings'),dict) or set(p['ratings'])-set(skill_reference().id):
        raise ValueError('Invalid skill identifiers')
    for v in p['ratings'].values():
        if isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or not 0<=v<=5:
            raise ValueError('Skill ratings must be between 0 and 5')
    return p

def matrix():
    parts=[]
    for table in ['raw_essential_skills','raw_transferable_skills']:
        f=d.frame(f'''SELECT substr("O*NET-SOC Code",1,7) AS code,"Element ID" AS id,"Data Value" AS importance
         FROM {table} WHERE "Scale ID"='IM' AND COALESCE("Recommend Suppress",'N')<>'Y'
         AND COALESCE("Not Relevant",'N')<>'Y' ''')
        f['importance']=pd.to_numeric(f.importance,errors='coerce')
        parts.append(f)
    f=pd.concat(parts).dropna().groupby(['code','id'],as_index=False).importance.mean()
    return f.pivot(index='code',columns='id',values='importance')

def wage_catalog():
    return d.frame('''SELECT r.OCC_CODE AS code,r.OCC_TITLE AS occupation,b.a_median AS median_wage,b.tot_emp AS employment
       FROM raw_national_m2025_dl r JOIN sources s ON s.table_name='raw_national_m2025_dl'
       JOIN bls_observations b ON b.source_id=s.id AND b.source_row=r._src_row WHERE r.O_GROUP='detailed' ''')

def recommend(profile,m,weight=0.8,wages=None):
    validate_profile(profile)
    if len(profile['ratings'])<3:
        raise ValueError('Assess at least three skills first; leave unknown skills blank')
    if not 0<=weight<=1:
        raise ValueError('Invalid preference weight')
    ratings=pd.Series(profile['ratings'],dtype=float)/5
    common=m.columns.intersection(ratings.index)
    if len(common)<3:
        raise ValueError('At least three assessed skills must have usable reference data')
    w=m[common]
    denominator=w.sum(axis=1,min_count=1).replace(0,float('nan'))
    alignment=w.mul(ratings[common]).sum(axis=1,min_count=1)/denominator
    coverage=w.notna().mul(1).sum(axis=1)/m.notna().sum(axis=1)
    wages=wage_catalog() if wages is None else wages
    out=wages.merge(pd.DataFrame({'skill_alignment':alignment,'assessment_coverage':coverage}),left_on='code',right_index=True,how='inner')
    out=out[out.code!=profile['current_soc']].copy()
    goal=profile['desired_income']
    out['wage_preference']=out.median_wage.div(goal).clip(upper=1) if goal>0 else float('nan')
    # Missing wage does not become zero: only the skill term is available for those rows.
    out['comparison_score']=out.skill_alignment
    mask=out.wage_preference.notna()
    out.loc[mask,'comparison_score']=weight*out.loc[mask,'skill_alignment']+(1-weight)*out.loc[mask,'wage_preference']
    raw=d.frame("SELECT code,metric,score FROM exposure_scores WHERE code_type='SOC Code'")
    if raw.duplicated(['code','metric']).any():
        raise ValueError('Ambiguous exposure source records')
    exposure=raw.pivot(index='code',columns='metric',values='score').rename(columns={
        'AIOE':'exposure_ai','Language Modeling AIOE':'exposure_language','Image Generation AIOE':'exposure_image'})
    out=out.merge(exposure,left_on='code',right_index=True,how='left')
    return out.dropna(subset=['comparison_score']).sort_values(['comparison_score','code'],ascending=[False,True]).reset_index(drop=True)


def comparison_groups(profile,m,weight=0.8,wages=None):
    """Rank only rows with the same evidence basis; retain unavailable-wage rows separately."""
    from core.pathways import annotate
    result=annotate(recommend(profile,m,weight,wages),profile)
    combined=profile['desired_income']>0 and weight<1
    if combined:
        ranked=result[result.wage_preference.notna()].copy()
        supplementary=result[result.wage_preference.isna()].copy()
        basis='Skills + wage'
    else:
        ranked=result.copy()
        supplementary=result.iloc[:0].copy()
        basis='Skills only'
    ranked['score_basis']=basis
    supplementary['score_basis']='Skills only (wage unavailable)'
    return ranked.reset_index(drop=True),supplementary.reset_index(drop=True),basis


def gaps(profile,target,m):
    if target not in m.index:
        return pd.DataFrame(columns=['id','skill','importance','self_rating','priority'])
    f=m.loc[target].dropna().rename('importance').reset_index()
    f=f.merge(skill_reference(),on='id')
    f['self_rating']=f.id.map(profile['ratings'])
    f['priority']=f.importance*(1-f.self_rating/5)
    return f.sort_values(['priority','importance'],ascending=False,na_position='last')

def simulate(current,target,months,cost,earnings_fraction,weekly_hours):
    vals=[current,target,months,cost,earnings_fraction,weekly_hours]
    if any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) for v in vals):
        raise ValueError('Scenario inputs must be finite numbers')
    if min(current,target,cost)<0 or months<=0 or weekly_hours<=0 or weekly_hours>168 or not 0<=earnings_fraction<=1:
        raise ValueError('Scenario inputs are outside valid ranges')
    forgone=current*(1-earnings_fraction)*months/12
    total=cost+forgone
    gain=(target-current)/12
    return {'training_months':months,'learning_hours':weekly_hours*52*months/12,
        'training_cost':cost,'earnings_forgone':forgone,'total_transition_cost':total,
        'monthly_income_change':gain,'payback_months_after_transition':total/gain if gain>0 else None}

def history(soc):
    frames=[]
    for year in range(2022,2026):
        table=f'raw_national_m{year}_dl'
        f=d.frame(f'''SELECT b.year,r.OCC_TITLE AS title,b.tot_emp AS employment,b.a_mean AS mean_annual_wage,b.a_median AS median_annual_wage,s.path AS source
          FROM {table} r JOIN sources s ON s.table_name=? JOIN bls_observations b ON b.source_id=s.id AND b.source_row=r._src_row
          WHERE r.OCC_CODE=? AND r.O_GROUP='detailed' AND r.NAICS='000000' AND r.OWN_CODE='1235' ''',(table,soc))
        frames.append(f)
    return pd.concat(frames,ignore_index=True)

def report(profile,target,m,scenario=None,completed=None):
    validate_profile(profile)
    g=gaps(profile,target,m)
    record=wage_catalog();record=record[record.code==target]
    title=record.iloc[0].occupation if len(record) else target
    return {'report_version':1,'profile':profile,'target':{'code':target,'title':title},
       'preparation_references':preparation.profiles(target),
       'skill_priorities':json.loads(g.head(10).to_json(orient='records')),
       'scenario':scenario,'completed_tasks':completed or {},
       'methodology':{'geographic_scope':'U.S. occupational and labour-market data; published territories where available. All monetary amounts are USD. No Hong Kong or mainland China wage estimates.',
       'skills':'Mean IM importance across available O*NET specializations; self-ratings are not occupational requirements.',
       'recommendations':'Heuristic weighted assessed-skill alignment plus optional national median-wage preference. Not a suitability or hiring probability.',
       'wages':'Nominal USD, US national May 2025 published estimates; not personal salary predictions.',
       'simulation':'User-assumed deterministic scenario; excludes taxes, financing, discounting and job-search uncertainty.',
       'classification':'12 combined occupations remain unresolved; exact exposure-code matches are not a full vintage crosswalk.',
       'history':'Separate annual OEWS estimates, not a longitudinal panel or a causal AI effect.'}}
