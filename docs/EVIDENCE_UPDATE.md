# Evidence and preparation update

Recommendation shortlists and report summaries now use the same evidence basis.
When desired income is positive and skills carry less than 100% weight, only
occupations with published wage estimates enter the combined ranking. Missing
wages remain unavailable; their skill evidence appears separately. Setting the
skill weight to 1.0, or omitting the income goal, compares all usable occupations
on assessed skills alone. Exposure does not affect ranking.

`data/reference/job_zones.json` is an exact projection of 923 rows from the local
archive's `raw_job_zones` and four rows from `raw_job_zone_reference`. Original
field names, dates, rating sources and descriptions are retained. The bundled
source combines Job Zones 1–2 under code 2. Individual O*NET specializations are
shown separately, without averaging their preparation requirements. No reference
is inferred for unresolved combined BLS occupations. These are typical preparation
descriptions, not an individual eligibility, licensing or qualification assessment.

Dashboard, recommendations and personal reports display the reference. JSON and
readable report exports retain it. Existing workspace format remains version 2;
no personal data is added to the source repository.

Exposure interpretation links to the authors' original dataset repository:
https://github.com/AIOE-Data/AIOE. The app retains original indices and explicitly
avoids task-level attributions without a validated contribution breakdown.

Validation: 70 tests passed, including exact comparison with the original SQLite
archive, evidence-group separation, skills-only recovery, missing mappings and
Streamlit page workflows. Public browser verification is performed after push.
