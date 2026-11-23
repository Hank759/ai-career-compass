"""Self-contained, escaped and printable career reports; no external assets."""
from html import escape
import math


def value(item):
    if item is None:return 'Not available'
    if isinstance(item,bool):return 'Yes' if item else 'No'
    if isinstance(item,float):return f'{item:,.3f}'.rstrip('0').rstrip('.') if math.isfinite(item) else 'Not available'
    return escape(str(item))


def table(rows,columns):
    if not rows:return '<p>No records available.</p>'
    head=''.join('<th scope="col">'+escape(label)+'</th>' for _,label in columns)
    body=''.join('<tr>'+''.join('<td>'+value(row.get(key))+'</td>' for key,_ in columns)+'</tr>' for row in rows)
    return '<div class="table"><table><thead><tr>'+head+'</tr></thead><tbody>'+body+'</tbody></table></div>'


def render(payload):
    profile=payload['profile'];target=payload['target']
    context=payload.get('recommendation_geography') or {}
    adjusted=context.get('basis',(profile.get('preferred_region') or {}).get('wage_basis'))=='Price-adjusted proxy'
    goal_label='Desired purchasing power (US-average price units)' if adjusted else 'Desired annual income (USD)'
    wage_label='Price-adjusted wage proxy (US-average price units)' if adjusted else 'Median annual wage (USD)'
    sections=['<h1>AI Career Compass</h1><p class="subtitle">Personal career planning report · U.S. data · USD</p>',
        '<h2>'+escape(target['title'])+' <small>'+escape(target['code'])+'</small></h2>',
        '<p>Prepared for: '+value(profile['name'] or 'Unnamed learner')+'</p>',
        '<p>This report is a planning aid. Scores are not hiring probabilities, and exposure is not a probability of job loss. Use your own judgment and verify requirements before making decisions.</p>',
        '<h2>Your starting point</h2>',table([profile],[('current_soc','Current SOC'),('annual_income','Current annual income (USD)'),('desired_income',goal_label),('weekly_hours','Learning hours/week')]),
        '<h3>Career history and interests</h3><p class="preserve">'+value(profile['history'] or 'Not provided')+'</p>',
        '<h2>Target AI exposure</h2>',table(payload.get('target_exposure',[]),[('metric','Source metric'),('score','Original index'),('source_code','Original SOC code'),('match_method','Matching basis'),('source_file','Source'),('crosswalk_url','Crosswalk source')]),
        '<p>No available data match at present for missing exposure metrics. A mapped historical reference retains the original source score; it is not a newly measured estimate for the current occupation classification.</p>',
        '<p>Three separate source indices; compare occupations within the same metric. Negative indices are valid. Missing data is not zero. Classification versions are not fully reconciled.</p>',
        '<h2>Career comparisons</h2><p>Scoring basis: '+value(payload.get('comparison_basis'))+'. Skill weight: '+value(payload.get('recommendation_skill_weight'))+'. Scores below use 0–1 units.</p>',
        table(payload.get('comparison_summary',[]),[('occupation','Occupation'),('comparison_score','Score (0–1)'),('assessment_coverage','Assessment coverage (0–1)'),('median_wage',wage_label),('education_pathway','Education pathway'),('qualification_review','Self-reported qualification review')]),
        '<h2>Education, experience and training</h2><p>Job Zone descriptions apply to the whole preparation group, including other occupations. They are not specific mandatory degrees, licensing checks or an assessment of your eligibility.</p>']
    context=payload.get('recommendation_geography') or {}
    if context:
        sections.append('<h3>Selected labour market and wage basis</h3>'+table([context],[('scope','Scope'),('area_title','Area'),('basis','Wage basis'),('wage_year','Wage year'),('rpp_year','Price year')]))
        if context.get('basis')=='Price-adjusted proxy':sections.append('<p>Comparison wages above are purchasing-power proxies, not nominal USD. Simulator income remains nominal USD.</p>')
    review=payload.get('target_qualification_review')
    if review:
        sections.append('<h3>Personal qualification review (unverified)</h3><p>'+value(review.get('status'))+'</p><p class="preserve">'+value(review.get('notes') or 'No notes entered')+'</p>')
    preferences=payload.get('education_preferences')
    if preferences:
        from core.pathways import categories
        names=categories()
        sections.append('<p>Current education: '+value(names.get(preferences.get('education_category'),'Not entered'))+'. Planned categories: '+value('; '.join(names.get(code,code) for code in (preferences.get('planned_education') or [])) or 'None')+'. Filter: '+value(preferences.get('education_filter') or 'All education pathways')+'.</p>')
    if payload.get('career_side_by_side'):
        import pandas as pd
        from core.comparison_tools import display_comparison
        comparison=display_comparison(pd.DataFrame(payload['career_side_by_side']),adjusted)
        sections.append('<h2>Selected careers side by side</h2>'+table(comparison.to_dict('records'),[(name,name) for name in comparison.columns]))
        sections.append('<p>Comparison scores use 0–100 units here. Exposure indices retain source units. Blank scenario costs or durations mean no current saved scenario; no training prices or qualification times are inferred.</p>')
    sensitivity=payload.get('sensitivity_analysis')
    if sensitivity:
        sections.append('<h2>Input sensitivity</h2>'+table(sensitivity['summary'],[('occupation','Occupation'),('saved_score_rank','Saved score rank'),('best_tested_rank','Best tested rank'),('worst_tested_rank','Worst tested rank'),('top_10_band_cases','Top-10 score band (cases)'),('tested_cases','Tested cases')]))
        sections.append('<p>'+value(sensitivity['method'])+'</p>')
    for row in payload.get('preparation_references',[]):
        sections.append('<h3>'+value(row['Title'])+' · '+value(row['O*NET-SOC Code'])+'</h3>')
        ref=row.get('reference')
        if ref:
            sections.append('<p>'+value(ref['Name'])+'</p>')
            for field in ['Education','Experience','Job Training']:
                sections.append('<p><strong>'+field+': </strong>'+value(ref[field])+'</p>')
        sections.append('<p class="muted">Source date: '+value(row['Date'])+' · '+value(row['Domain Source'])+'</p>')
    if not payload.get('preparation_references'):sections.append('<p>No direct preparation reference is available.</p>')
    scenario=payload.get('scenario')
    sections.append('<h2>Saved transition scenario</h2>')
    if scenario:
        sections.append(table([scenario],[('current_income','Current annual income (USD)'),('target_income','Assumed annual income after transition (USD)'),('earnings_fraction','Earnings retained (0–1)')]))
        sections.append(table([scenario['result']],[('training_months','Transition months'),('training_cost','Fees (USD)'),('earnings_forgone','Earnings forgone (USD)'),('total_transition_cost','Total cost (USD)'),('monthly_income_change','Monthly income change (USD)'),('payback_months_after_transition','Payback months after transition')]))
    else:sections.append('<p>No saved scenario for this target.</p>')
    comparisons=payload.get('scenario_comparisons',[])
    if comparisons:
        sections.append('<h3>Saved comparison scenarios</h3>')
        rows=[{'name':r['name'],'income':r['scenario']['target_income'],**r['scenario']['result']} for r in comparisons]
        sections.append(table(rows,[('name','Scenario'),('income','Assumed annual income (USD)'),('training_months','Months'),('total_transition_cost','Total cost (USD)'),('payback_months_after_transition','Payback months')]))
    sections.extend(['<h2>Skill priorities</h2>',table(payload.get('skill_priorities',[]),[('skill','Skill'),('importance','Importance'),('self_rating','Self-rating (0–5)'),('priority','Learning priority')]),
        '<h2>Learning activities</h2>',table(payload.get('learning_plan',[]),[('skill','Skill'),('exercise','Practice suggestion'),('evidence','Completion evidence'),('allocated_hours','Allocated hours'),('complete','Completed')]),
        '<p>Practice suggestions are app-authored, not official training requirements. Hours are a time budget, not time to qualification.</p>',
        '<h2>Methods and limitations</h2>'])
    for key,description in payload.get('methodology',{}).items():
        sections.append('<p><strong>'+escape(key.replace('_',' ').capitalize())+': </strong>'+value(description)+'</p>')
    sections.append('<footer>Keep this file private: it contains your personal inputs. Complete workspace backups are required to restore the interactive app; this report does not replace a workspace backup.</footer>')
    css='''body{font:15px/1.6 system-ui,sans-serif;color:#182e39;max-width:1100px;margin:40px auto;padding:0 24px}h1{color:#11685d}h2{border-bottom:1px solid #b8cfca;padding-bottom:8px;margin-top:32px}small,.muted,.subtitle,footer{color:#52676f}small{font-size:.65em}table{border-collapse:collapse;width:100%;font-size:13px}th,td{border:1px solid #cbd7db;padding:9px;text-align:left;vertical-align:top}th{background:#e8f3f0}tr{break-inside:avoid}.table{overflow-x:auto}.preserve{white-space:pre-wrap}footer{border-top:1px solid #cbd7db;margin-top:32px;padding-top:16px}@media print{body{max-width:none;margin:0;padding:0;font-size:11px}.table{overflow:visible}table{font-size:10px}h2,h3{break-after:avoid}thead{display:table-header-group}@page{size:A4 landscape;margin:15mm}}'''
    return '<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>AI Career Compass — Personal report</title><style>'+css+'</style></head><body>'+''.join(sections)+'</body></html>'
