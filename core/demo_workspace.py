"""An explicitly fictional workspace for usability testing; never auto-loaded."""
from core import planning as p
from core import workspace as w

def example_workspace():
    ids=list(p.skill_reference().id)
    ratings={key:3.0 for key in ids}
    ratings.update({'2.B.3.e':4.0,'2.A.1.e':4.0,'2.A.1.a':4.0,'2.B.1.d':2.0,'2.B.5.d':2.0})
    profile={'version':1,'name':'Example learner (fictional)','current_soc':'15-1252',
       'annual_income':60000.0,'desired_income':90000.0,'weekly_hours':5.0,
       'history':'Fictional demonstration only. Income and self-ratings are invented examples, not observations about a real person.',
       'ratings':ratings}
    return w.export_workspace({'profile':profile,'planning_target':'11-3021',
       'saved_scenario':None,'plan_done':{},'plan_horizons':{},'recommendation_weight':.8})
