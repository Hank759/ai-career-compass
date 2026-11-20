"""App-authored practice suggestions; not official training requirements."""
EXERCISES = {
'2.A.2.b':('Learn an unfamiliar concept and apply it to a small work example.','A concept summary and one worked example.'),
'2.A.1.b':('Practise summarising a conversation and ask the speaker to confirm your understanding.','A corrected summary and feedback notes.'),
'2.B.2.i':('Break a realistic work problem into causes, constraints and three candidate solutions.','A problem map and a reasoned solution choice.'),
'2.B.1.b':('Plan a small shared task with dependencies, responsibilities and hand-offs.','A task board and hand-off checklist.'),
'2.A.2.a':('Compare two claims about a work issue and check the assumptions and evidence.','A one-page evidence comparison.'),
'2.B.3.j':('Create a maintenance checklist for a simulated or documented piece of equipment.','A mock maintenance log; no unsupervised physical work.'),
'2.B.3.c':('Compare three tools against requirements, cost assumptions and compatibility.','A weighted tool-selection matrix.'),
'2.B.3.d':('Write and test an installation procedure in a safe sandbox or simulation.','A setup checklist, test results and rollback steps.'),
'2.B.1.e':('Teach a short concept to a peer, then check their understanding.','A lesson outline, short quiz and feedback.'),
'2.B.4.e':('Evaluate a work decision under at least three possible outcomes.','A decision table with explicit assumptions.'),
'2.A.2.c':('Try two study approaches for a small topic and compare recall.','A study log and an explanation of the better approach.'),
'2.B.5.b':('Build a mock project budget and compare planned with assumed actual spending.','A budget and variance explanation.'),
'2.B.5.c':('Plan materials for a mock project and consider shortages and waste.','An inventory and resource allocation sheet.'),
'2.B.5.d':('Assign a mock project team roles, feedback checkpoints and workload.','A role matrix and a feedback plan.'),
'2.A.1.e':('Solve a quantitative work example and independently check the units and result.','A worked calculation with checks.'),
'2.A.2.d':('Choose success measures for a small task and review progress against them.','A monitoring log with corrective actions.'),
'2.B.1.d':('Role-play a negotiation with objectives, alternatives and trade-offs.','A preparation sheet and a reflection on the agreement.'),
'2.B.3.h':('Practise a documented operating procedure in a simulator or supervised setting.','A procedure checklist and observations.'),
'2.B.3.a':('Turn a user need into measurable operating requirements and constraints.','A requirements document with acceptance criteria.'),
'2.B.3.g':('Review a mock operating log and identify unusual values and responses.','An annotated log and an escalation checklist.'),
'2.B.1.c':('Prepare an evidence-based proposal tailored to a specific audience.','A short proposal and peer feedback.'),
'2.B.3.e':('Build a small program that automates a repetitive task and test edge cases.','Source code, example inputs and test results.'),
'2.B.3.m':('Design checks for a sample output and investigate one defect.','A test checklist and a defect analysis.'),
'2.A.1.a':('Read a technical article and summarise its claim, evidence and limitations.','An accurate one-page summary.'),
'2.B.3.l':('Diagnose a mock equipment fault using documentation or a simulation.','A repair decision tree; supervised practice only.'),
'2.A.1.f':('Form a testable hypothesis and design a safe small experiment.','A method, observations and limitations.'),
'2.B.1.f':('Map a user problem and propose a response that addresses the underlying need.','A service journey and response checklist.'),
'2.B.1.a':('Analyse a fictional interaction from several participants’ perspectives.','Perspective notes and questions to check assumptions.'),
'2.A.1.d':('Deliver a three-minute explanation of a work topic and request feedback.','A talk outline and improvement notes.'),
'2.B.4.g':('Map a process and examine how changing one part affects the rest.','A system map and a what-if analysis.'),
'2.B.4.h':('Define outcome measures for a process and compare two improvement options.','An evaluation rubric and comparison.'),
'2.B.3.b':('Sketch a prototype that addresses a user need and test it against requirements.','A prototype and a short user-test record.'),
'2.B.5.a':('Plan a week, record actual effort and revise priorities.','A time log and an improved weekly schedule.'),
'2.B.3.k':('Investigate a simulated fault using hypotheses and controlled checks.','A troubleshooting log with the identified cause.'),
'2.A.1.c':('Draft a concise work memo, revise it for the audience and check clarity.','A before-and-after memo with feedback.')}


def build_plan(gaps,target,weeks,weekly_hours,completed=None):
    if not 1<=weeks<=104 or weekly_hours<=0:
        raise ValueError('Invalid learning plan budget')
    focus=gaps[gaps.self_rating.notna() & (gaps.priority>0)].head(5)
    if focus.empty:return []
    done=completed or {}
    rows=[]
    for r in focus.itertuples():
        action,evidence=EXERCISES.get(r.id,('Practise this skill in a small work example.','A completed example and feedback.'))
        token=target+'_'+r.id
        rows.append({'id':r.id,'skill':r.skill,'exercise':action,'evidence':evidence,
            'weeks':int(weeks),'hours_per_week':weekly_hours/len(focus),
            'allocated_hours':weeks*weekly_hours/len(focus),'complete':bool(done.get(token,False))})
    return rows
