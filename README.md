# AI Career Compass

An English-language research prototype for occupational AI exposure, wage comparisons and transparent career-transition planning. No API keys are required.

## Deploy on Streamlit Community Cloud

1. Create a GitHub repository called ai-career-compass. A private repository can keep source access limited; authorize Community Cloud to read it.
2. Upload the CONTENTS of this folder, preserving core/, data/cloud/ and .streamlit/. Do not upload this folder as an extra parent directory. Do not upload the ZIP itself as the app.
3. Sign in at https://share.streamlit.io using GitHub and select Create app.
4. Select your repository, its main branch and app.py. In Advanced settings, choose Python 3.12. Deploy.
5. To allow the teaching team to open it without an invitation, open App settings > Sharing and select This app is public and searchable. Verify the resulting URL in a signed-out/private browser window.
6. Record the working URL for your Moodle submission. The build is not complete until the remote service reports success and an independent browser can run a realistic task.

All code is in English. requirements.txt contains the three direct runtime dependencies. The database is bundled as two compressed parts and restored with SHA-256 verification on first startup. Keep both parts and manifest.json together under data/cloud/. Do not commit an expanded SQLite database.

The public-data application subset supports the same existing pages. Detailed occupations and sector-level industry estimates are retained; duplicate partitions, unused raw data and unused columns are omitted. This subset is labelled application, not a complete raw-data import. Selection details are in data/cloud/manifest.json. The complete inspection database remains on the original local computer.

## Local verification

Use Python 3.12. Install requirements-dev.txt, then run:

    python -m pytest tests -q
    streamlit run app.py

The application is deployed on Streamlit Community Cloud and has been checked in an independent anonymous browser. On 23 November 2026, all 101 tests passed. All 11 pages also returned ready through an isolated running server, including the fictional example, saved scenario and report workflow, with no server warnings or tracebacks. Anonymous online access and the end-to-end workflow were checked again on that date. Docker builds remain untested locally. See `docs/INDEPENDENT_CHECK_2026-11-23.txt` for scope and limitations.

A Dockerfile is included for compatible container hosts. It listens on port 7860. Docker itself was not available for a local container-build test. Hugging Face is optional; confirm its current account/plan requirements before choosing it.

## Data and visitor privacy

Bundled data comes from the project's BLS OEWS, O*NET and Felten source files. Preserve their attribution and applicable terms when redistributing. Source paths remain recorded for traceability.

Visitor profiles, simulations and learning progress remain in their Streamlit session and are not saved as shared database rows. Visitors should export their workspace to keep it between sessions. Do not commit personal exports, passwords or API keys. The deployment bundle excludes the local environment, private exports and development logs.

Exposure indices are not job-loss probabilities. Missing values are not zero. Career rankings are heuristic comparisons; scenarios depend on visitor assumptions. Classification-version mapping and cost-of-living adjustment remain limited as explained in the app.

Official deployment guide: https://docs.streamlit.io/deploy/streamlit-community-cloud
Official access/sharing guide: https://docs.streamlit.io/deploy/streamlit-community-cloud/share-your-app

## Usability update

Home now offers Start guided example without file transfer. Replacing an existing session requires confirmation and keeps an in-session return copy; export a permanent backup first. Career comparisons explain their score basis. Transition Simulator supports up to five named comparison snapshots, CSV export and removal. Version-2 workspace backups include comparisons; version-1 backups still import. Updating a profile clears snapshots calculated for the old baseline.

## Skill table

Career Dashboard now shows Skill, Importance (1–5) and Skill category. Categories preserve the source table grouping; they do not create separate ranking weights. Category filtering, show-all and CSV download are available. Source identifiers, dates and rating origins remain in Skill source details.

## Reports and progress

Personal Report includes a self-contained printable HTML download alongside JSON
and Markdown. Open HTML in a browser to print or save as PDF; no external assets
or script are required. User inputs are HTML-escaped. Personal reports contain
private inputs and remain excluded from version control.

Planning pages include a quick complete-workspace backup. A printable report is
not a workspace restore file. Target selection follows the user across planning
pages. A changed profile clears obsolete scenario form inputs. A plan with no
usable learning tasks is not counted as a prepared learning plan.

## Education and regional planning (4.5)

Personal Profile now saves completed/planned education, explicit pathway filters,
and a preferred state or metro area. Career Recommendations uses the selected
area's wages, with optional BEA price-adjusted proxies, and supports self-reported
qualification reviews. Regional Analysis compares nominal and price-adjusted wages.
Simulator cash flows remain nominal USD. Missing prices, wages and educational
references are never filled with inferred requirements or zeroes. See
`docs/PRIORITY_FEATURES.md` for matching rules, source coverage and limitations.

## Career trade-offs and sensitivity (4.6)

Career Recommendations provides a side-by-side view of two or three careers from
the same scoring group. It preserves raw exposure units, shows educational paths
and learning priorities, and displays fees or duration only for a currently saved
scenario. Chosen occupations are included in complete workspace backups.

An optional sensitivity check changes one assessed skill at a time by one point,
clipped to 0–5, and tests adjacent skill weights (±0.05) only when all candidates
have wage data. The candidate set is fixed. Score ranks round at 12 decimal places
to avoid floating-point noise; ties share ranks. Best/worst ranks and counts in the
top-10 score band are deterministic test results, not confidence, probabilities,
or a complete uncertainty analysis. Weight changes that add new candidate groups
are outside this check. Current-session requested analysis and selected comparison
careers appear in JSON, Markdown and printable HTML reports. Sensitivity results
are recomputed from current inputs, not restored as authoritative cached outputs.

Scoring details, price methodology and education/qualification editing are grouped
in expanders, keeping the main shortlist, target selection and exposure visible.

## Exposure coverage (4.7)

Exposure now combines exact-code records with eight explicitly labelled historical
references verified against the official BLS one-to-one SOC crosswalk. Coverage is
681 of 830 occupations. The remaining 149 retain wage/skill functionality and
display "No available exposure data match at present". Home and data pages offer
an exposure-only filter; no occupations are deleted. Split/merge classifications
remain unresolved. See `docs/EXPOSURE_MATCHING.txt` for source codes and policy.
