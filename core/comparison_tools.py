"""Career trade-offs and deterministic input sensitivity, without confidence claims."""
import pandas as pd
from core import planning as p,preparation


def sensitivity(profile,m,weight,ranked):
    if ranked.empty:return pd.DataFrame(),[]
    codes=list(ranked.code);base=ranked.set_index('code')
    ratings=pd.Series(profile['ratings'],dtype=float)/5
    common=m.columns.intersection(ratings.index)
    importance=m.reindex(codes)[common]
    denominator=importance.sum(axis=1,min_count=1).replace(0,float('nan'))
    scenarios=[];ranks=[]
    def case(label,alignment,skill_weight):
        score=alignment.copy()
        available=base.wage_preference.notna()
        score.loc[available]=skill_weight*alignment.loc[available]+(1-skill_weight)*base.loc[available,'wage_preference']
        ranks.append(score.round(12).rank(method='min',ascending=False))
        scenarios.append(label)
    case('Saved inputs',base.skill_alignment,weight)
    if profile['desired_income']>0 and base.wage_preference.notna().all():
        for candidate in sorted({max(0.,round(weight-.05,8)),min(1.,round(weight+.05,8))}-{weight}):
            case(f'Skill weight {candidate:g}',base.skill_alignment,candidate)
    for skill in common:
        for delta in [-1,1]:
            original=profile['ratings'][skill];changed=max(0,min(5,original+delta))
            if changed==original:continue
            altered=ratings.copy();altered[skill]=changed/5
            alignment=importance.mul(altered[common]).sum(axis=1,min_count=1)/denominator
            case(f'{skill}: {original:g} to {changed:g}',alignment,weight)
    trials=pd.concat(ranks,axis=1)
    out=base[['occupation']].copy()
    out['saved_score_rank']=ranks[0]
    out['best_tested_rank']=trials.min(axis=1)
    out['worst_tested_rank']=trials.max(axis=1)
    out['top_10_band_cases']=(trials<=10).sum(axis=1)
    out['tested_cases']=len(scenarios)
    return out.reset_index().rename(columns={'index':'code'}),scenarios


def side_by_side(profile,m,ranked,codes,state=None):
    state=state or {};lookup=ranked.set_index('code');rows=[]
    for code in codes:
        if code not in lookup.index:continue
        r=lookup.loc[code]
        gaps=p.gaps(profile,code,m)
        priorities=gaps[gaps.self_rating.notna() & (gaps.priority>0)].head(3)
        zones=preparation.profiles(code)
        scenario=state.get('saved_scenario') or {}
        current=scenario.get('target')==code
        rows.append({'code':code,'occupation':r.occupation,'comparison_score':float(r.comparison_score),
            'skill_alignment':float(r.skill_alignment),'assessment_coverage':float(r.assessment_coverage),
            'wage_benchmark':r.median_wage,'exposure_ai':r.exposure_ai,'exposure_language':r.exposure_language,'exposure_image':r.exposure_image,
            'education_pathway':r.education_pathway,'qualification_review':r.qualification_review,
            'preparation_groups':'; '.join(sorted({z['reference']['Name'] for z in zones if z.get('reference')})) or 'Not available',
            'learning_priorities':'; '.join(priorities.skill) or 'No assessed priorities available',
            'saved_training_fees':scenario['result']['training_cost'] if current else None,
            'saved_transition_months':scenario['result']['training_months'] if current else None})
    return pd.DataFrame(rows)


def display_comparison(rows,price_adjusted=False):
    if rows.empty:return pd.DataFrame()
    display=rows.copy()
    for col in ['comparison_score','skill_alignment','assessment_coverage']:display[col]=(display[col]*100).round(1)
    names={'comparison_score':'Comparison score / 100','skill_alignment':'Assessed-skill alignment / 100','assessment_coverage':'Skills assessed (%)',
        'wage_benchmark':'Wage proxy (US-average price units)' if price_adjusted else 'Median annual wage (USD)',
        'exposure_ai':'General AI exposure','exposure_language':'Language-model exposure','exposure_image':'Image-generation exposure',
        'education_pathway':'Education pathway','qualification_review':'Qualification review (self-reported)',
        'preparation_groups':'O*NET preparation groups','learning_priorities':'Three assessed learning priorities',
        'saved_training_fees':'Latest saved scenario fees (USD)','saved_transition_months':'Latest saved transition duration (months)'}
    display['occupation']=display.occupation+' · '+display.code
    display=display.drop(columns='code').set_index('occupation').rename(columns=names)
    def text(value):
        if pd.isna(value):return ''
        if isinstance(value,float):return f'{value:,.3f}'.rstrip('0').rstrip('.')
        return str(value)
    return display.map(text).T.rename_axis('Measure').reset_index()
