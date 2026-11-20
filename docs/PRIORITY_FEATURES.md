# Education, qualification reviews and regional recommendations

## Education pathway matching

The optional profile fields are backwards-compatible with version-1 profiles and
version-1/2 workspace backups. A user can select completed education and categories
they are willing to pursue. The default keeps every education pathway visible.
Filtering is explicit; it does not add an opaque numerical bonus.

`education.json` projects 9,096 Required Level of Education (RL, element 2.D.1)
observations and the exact 12 category descriptions from the original O*NET
archive. Category response shares, sample size, source date, rating source and
suppression flag are retained. Suppressed and invalid shares are excluded from
display and matching. Modal matching requires a complete usable set of all 12
categories with shares summing to 99.9–100.1 (rounding tolerance). Tied modes are
retained, and individual O*NET specializations are never averaged. A SOC matches
if at least one specialization's modal category matches the user's explicit
selection. Missing or incomplete distributions are not assumed to match.

These are reported education response frequencies, not legal minimums, hiring
probabilities, degree subject requirements or an equivalence service. A doctorate
is not silently substituted for a professional degree, certificate or another
category. Qualification reviews are target-specific, self-reported notes and
statuses. Users can exclude targets they marked as needing additional qualification.
The app does not check licences or certify eligibility; location-specific authority
and employer requirements must be checked independently.

O*NET dictionary: https://www.onetcenter.org/dictionary/30.0/text/education_training_experience.html

## Regional price comparisons

`regional_prices.json` retains 441 all-items (LineCode 1) observations from the
bundled 2024 SARPP and MARPP files, including geography codes/names, year, unit,
description and source. National/rural aggregate rows are not mapped to an
unrelated BLS area. State BEA codes use their state prefix; metro codes are kept
as published. A match requires both area code and normalized area name. Only
the BEA metro suffix is removed when comparing names; no fuzzy matching occurs.

The source coverage matches 51 of 54 BLS state/territory areas and 384 of 393 BLS
metro areas. Unmatched areas, suppressed wages and unavailable prices stay blank.
Code/name agreement does not independently establish unchanged boundaries.

Price-adjusted wage proxy = May 2025 median annual wage / (2024 all-items RPP / 100).
This is a cross-year relative purchasing-power proxy, not a 2025 cost-of-living
estimate, inflation-adjusted real income, after-tax income or a household budget.
Taxes, housing preferences, commuting and moving costs are excluded.

BEA methodology: https://www.bea.gov/data/prices-inflation/regional-price-parities-state-and-metro-area

## Regional rankings and reports

The saved profile selects National, State or Metro and a wage basis. Regional
rankings use occupations with published records for the selected area. There is
no national wage fallback, employment-share weighting or vacancy forecast.
Combined-score rows require the selected wage measure; rows missing a wage or
required price reference are shown separately. Skills-only scoring can retain
those occupations, while keeping the selected area's published record coverage.

For price-adjusted comparisons, desired income is entered in U.S.-average price
units. Simulator cash flows use the area's **nominal** median wage as an editable
benchmark and never silently use a price-adjusted proxy as cash income. Missing
local nominal wages require a user-entered assumption. Profile changes clear old
saved scenarios. Reports and complete backups retain geography, education settings
and self-reported qualification notes. JSON, Markdown and HTML exports identify
the wage basis and the limitations above.

Validation: 89 tests pass. An isolated running server also verified saving a
California purchasing-power profile, education selection, qualification notes,
regional recommendations, nominal scenario inputs and all eleven application
pages, without server warnings or tracebacks.
