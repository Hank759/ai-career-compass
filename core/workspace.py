"""Validated JSON round-trip for the personal planning workspace."""
import math
from core import planning as p


def validate_workspace(value):
    if not isinstance(value,dict) or value.get('kind')!='career_workspace' or value.get('version')!=1:
        raise ValueError('Unsupported workspace file')
    fields={'kind','version','profile','target','scenario','completed_tasks','plan_horizons','skill_weight'}
    if set(value)!=fields:
        raise ValueError('Workspace has missing or unknown fields')
    profile=p.validate_profile(value['profile'])
    codes=set(p.wage_catalog().code)
    target=value['target']
    if target is not None and (not isinstance(target,str) or target not in codes):
        raise ValueError('Unknown target occupation')
    weight=value['skill_weight']
    if isinstance(weight,bool) or not isinstance(weight,(int,float)) or not math.isfinite(weight) or not 0<=weight<=1:
        raise ValueError('Skill weight must be between 0 and 1')
    done=value['completed_tasks']
    skills=set(p.skill_reference().id)
    if not isinstance(done,dict) or len(done)>2000:
        raise ValueError('Invalid learning-task progress')
    for token,complete in done.items():
        code,sep,skill=token.partition('_')
        if not sep or code not in codes or skill not in skills or not isinstance(complete,bool):
            raise ValueError('Invalid learning-task progress')
    horizons=value['plan_horizons']
    if not isinstance(horizons,dict) or len(horizons)>len(codes):
        raise ValueError('Invalid plan horizons')
    for code,weeks in horizons.items():
        if code not in codes or isinstance(weeks,bool) or not isinstance(weeks,int) or not 1<=weeks<=104:
            raise ValueError('Planning horizon must be 1–104 whole weeks')
    scenario=value['scenario']
    if scenario is not None:
        if not isinstance(scenario,dict) or not isinstance(scenario.get('target'),str) or scenario['target'] not in codes:
            raise ValueError('Invalid scenario occupation')
        r=scenario.get('result')
        if not isinstance(r,dict):
            raise ValueError('Scenario inputs are missing')
        months=r.get('training_months');cost=r.get('training_cost')
        income=scenario.get('target_income');fraction=scenario.get('earnings_fraction')
        result=p.simulate(profile['annual_income'],income,months,cost,fraction,profile['weekly_hours'])
        if months>120 or cost>1e7 or income>1e8:
            raise ValueError('Scenario inputs exceed the form limits')
        # Recompute from user inputs. Never trust imported calculated totals.
        scenario={'target':scenario['target'],'current_income':profile['annual_income'],
                  'target_income':income,'earnings_fraction':fraction,'weekly_hours':profile['weekly_hours'],'result':result}
    return {'kind':'career_workspace','version':1,'profile':profile,'target':target,
            'scenario':scenario,'completed_tasks':done.copy(),'plan_horizons':horizons.copy(),'skill_weight':float(weight)}


def export_workspace(state):
    return validate_workspace({'kind':'career_workspace','version':1,'profile':state.get('profile',{}),
        'target':state.get('planning_target'),'scenario':state.get('saved_scenario'),
        'completed_tasks':state.get('plan_done',{}),'plan_horizons':state.get('plan_horizons',{}),
        'skill_weight':state.get('recommendation_weight',.8)})


def restore_workspace(state,value):
    clean=validate_workspace(value)  # fully validate before changing session state
    for key in list(state):
        if key.startswith(('check_','plan_weeks_','target_income_','scenario_months_','scenario_cost_','retained_income_','planning_')) or key in ('skill_weight','recommendation_target'):
            del state[key]
    state.pop('report_prepared_target',None)
    state.pop('plan_unavailable_target',None)
    state['profile']=clean['profile']
    state['planning_target']=clean['target']
    state['plan_done']=clean['completed_tasks']
    state['plan_horizons']=clean['plan_horizons']
    state['recommendation_weight']=clean['skill_weight']
    if clean['scenario'] is None:
        state.pop('saved_scenario',None)
    else:
        state['saved_scenario']=clean['scenario']
    state['profile_revision']=state.get('profile_revision',0)+1
