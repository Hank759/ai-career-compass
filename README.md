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

56 tests passed in the preparation environment. All 11 pages returned ready in an isolated runtime. Cloud/Linux builds are not yet verified. This package is deployment-ready preparation, not proof of a published website.

A Dockerfile is included for compatible container hosts. It listens on port 7860. Docker itself was not available for a local container-build test. Hugging Face is optional; confirm its current account/plan requirements before choosing it.

## Data and visitor privacy

Bundled data comes from the project's BLS OEWS, O*NET and Felten source files. Preserve their attribution and applicable terms when redistributing. Source paths remain recorded for traceability.

Visitor profiles, simulations and learning progress remain in their Streamlit session and are not saved as shared database rows. Visitors should export their workspace to keep it between sessions. Do not commit personal exports, passwords or API keys. The deployment bundle excludes the local environment, private exports and development logs.

Exposure indices are not job-loss probabilities. Missing values are not zero. Career rankings are heuristic comparisons; scenarios depend on visitor assumptions. Classification-version mapping and cost-of-living adjustment remain limited as explained in the app.

Official deployment guide: https://docs.streamlit.io/deploy/streamlit-community-cloud
Official access/sharing guide: https://docs.streamlit.io/deploy/streamlit-community-cloud/share-your-app

## Usability update

Home now offers Start guided example without file transfer. Replacing an existing session requires confirmation and keeps an in-session return copy; export a permanent backup first. Career comparisons explain their score basis. Transition Simulator supports up to five named comparison snapshots, CSV export and removal. Version-2 workspace backups include comparisons; version-1 backups still import. Updating a profile clears snapshots calculated for the old baseline.
