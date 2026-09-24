# Task 13 — Build objectives O2 and O3

Governing document: docs/specs/analysis-plan-v3.md. Read it fully first.
Plan v2 and all its results stand; its objective is O1.
This task BUILDS values only. No leaderboards, no referee tests, no
comparisons. Those are Task 14.

## Step 0 — Commit analysis-plan-v3.md alone. Record hash and SHA-256.

## Step 1 — O2 value model (chance creation)
Same pipeline, features, hyperparameters and 10-action horizon as the
frozen possession-value model; ONLY the target changes: expected xG
accumulated by the possessing team within the next 10 actions (sum of
StatsBomb shot xG for that team in that window; shots by the opponent
do not count here — the opponent side is handled symmetrically below).
Regression, not classification. Report held-out R-squared or MAE by
match-level split, and calibration deciles.
Memory: per-match parquet parts exactly as the horizon rebuild did.
Check live memory pressure before starting and every 50 matches
(proceed if free >= 40% and available >= 3 GB; stop and report below
20% free or under 1.5 GB available).

## Step 2 — Concede model (needed for O3)
Same pipeline and horizon; target: P(the OPPONENT scores within the next
10 actions). Report held-out AUC and calibration.

## Step 3 — Win-probability function (plan v3 section 2)
Estimate per-minute scoring rates for leading, level and trailing teams
from the 299-match sample's goal times. Build WP(goal difference,
minutes remaining) under the Poisson construction. Draws = half a win.
Run the REQUIRED validation: bucket match states by (d, m), compare
predicted WP with observed win rate, report per-bucket n, predicted,
observed, plus the Brier score. If any bucket with n >= 100 is off by
more than 10 percentage points, mark O3 UNVALIDATED and say so
prominently — do not quietly proceed.

## Step 4 — Recompute values for every option
For all 1,237,611 options, compute EV_O2 and EV_O3 per plan v3 section 1,
symmetric for both teams (a turnover is valued by what the opponent
gains). Then Decision_O2 and Decision_O3 per pass, and Execution
likewise. Write data/processed/options_o2.parquet and options_o3.parquet
with the same keys as options_policy.parquet so downstream code can join.
Sanity checks to report: correlation between Decision_O1, Decision_O2
and Decision_O3 at the pass level and at the player level; share of
passes where the argmax option differs between objectives.

## HARD RULES
- Frozen code for everything except the target definition and the value
  function. No feature changes, no hyperparameter changes.
- No leaderboards. No player names. No referee tests. No comparisons
  beyond the correlations in Step 4.
- If a model fails validation, report it and STOP rather than patching.
- No memory writes. Don't edit docs/JOURNAL.md.
- When finished, reply only that the task is done plus commit hashes.

## Output
docs/results/13-objectives.md (template). Commit per rule 9.
