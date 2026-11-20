"""Validated, named snapshots of user-assumed transition scenarios."""
from core import workspace as w

def add_comparison(items,name,scenario,profile):
    if not isinstance(name,str) or not name.strip():raise ValueError('Enter a scenario label')
    candidate={'kind':'career_workspace','version':2,'profile':profile,'target':scenario['target'],
      'scenario':scenario,'completed_tasks':{},'plan_horizons':{},'skill_weight':.8,
      'scenario_comparisons':list(items)+[{'name':name.strip(),'scenario':scenario}]}
    return w.validate_workspace(candidate)['scenario_comparisons']

def comparison_rows(items):
    rows=[]
    for item in items:
        s=item['scenario'];r=s['result']
        rows.append({'Scenario':item['name'],'Target SOC':s['target'],'Assumed annual income (USD)':s['target_income'],
          'Transition months':r['training_months'],'Total cost (USD)':r['total_transition_cost'],
          'Monthly income change (USD)':r['monthly_income_change'],
          'Payback after transition (months)':r['payback_months_after_transition']})
    return rows
