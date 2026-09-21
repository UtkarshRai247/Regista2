# Task 02 — Market Value Join and Primary Model

Per D-008, the decision metric is FROZEN before market data is loaded.

## Step 0 — Freeze the metric (do this first, before any download)
Commit the current per-unit Decision outputs to git. Record the commit
hash and the SHA-256 of the per-unit output file in
docs/results/02-market-join.md. Nothing about the metric changes after
this point in this task. If you believe something must change, STOP and
ask.

## Step 1 — Acquire market data
Download dcaribou/transfermarkt-datasets (CC0). Store under data/
(gitignored). Record the snapshot date and source URL in
docs/DATA_LICENSES.md if not already exact.

## Step 2 — Player crosswalk
Match our 102 players to transfermarkt player records.
- Normalize names (accents, case, punctuation, known nickname forms).
- Use player country from StatsBomb lineups as a secondary key.
- Require a unique match. Anything ambiguous goes to a review list.
- Write the crosswalk to data/processed/player_crosswalk.csv with a
  match_method column (exact / normalized / fuzzy / manual_review).
- Report: how many matched automatically, how many are ambiguous, how
  many failed. List every failure and ambiguity by name — 102 players
  is small enough to inspect by hand.

## Step 3 — Attach valuations
For each unit (player-competition-season):
- Take the valuation record dated within 90 days AFTER the
  competition-season end date. If several, take the earliest.
- For the H3 secondary analysis, also take the valuation closest to 12
  months after that date.
- Record each unit's valuation date and the gap in days.

## Step 4 — Build controls
- Age at competition-season end, from the transfermarkt date of birth.
- Position group from StatsBomb.
- Minutes played, completion%, progressive passes/90, goals+assists/90
  from our own outputs.
- Tournament-vs-league indicator.
- Club strength: median market value of the player's club squad at the
  same date, EXCLUDING the player themselves. Note in the results page
  that this control comes from the same source as the outcome.
- Contract expiry if present in the dataset; report whether it is.

## STOP HERE — GATE C. Report before fitting anything.
Report:
- Sample flow from 138 units to the final joined analysis sample.
- Units lost at each of: crosswalk failure, no valuation in window, no
  club strength, missing age.
- Final unit count and distinct player count.
- Descriptive stats for every variable in the primary model.
- Correlation matrix of all predictors and controls, to check for
  collinearity before fitting.
DO NOT fit the primary model until the research lead responds.

## Hard rules
- The primary specification is fixed in Amendment 1 of
  docs/specs/analysis-plan-pillar4.md. Do not modify it.
- Do not fit any model, exploratory or otherwise, before Gate C is
  answered. Do not peek at the Decision-value relationship.
- If a decision is needed that is not specified here, STOP and ask.

## Output
docs/results/02-market-join.md following the template.
