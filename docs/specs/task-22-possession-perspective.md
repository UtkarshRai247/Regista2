# Task 22 — Value model rows: the possessing team's view, and a label that counts its own goal

Written 2026-09-27 by the research lead, before any code for this task
exists. The author has decided to continue the engine rather than submit
a methods or tempo abstract. This is the FINAL engine attempt before the
SSAC27 abstract deadline (Oct 1). If it fails any stop condition below,
the engine is not accepted before Oct 1 and no engine-based player claim
is made. There is no Task 22b.

## Why (two defects found by reading code, not by looking at T4)

Task 21 closed with an exact zero: 0 goals in 2,602 rows (band 80-100,
ball beyond the line, teammate within 5u). The project's standing rule
is that a null is a suspected bug until audited. Reading
`value_models.py` `build_match_rows` (reused unchanged from engine v1's
`possession_value.py`) finds two:

DEFECT A — WRONG PERSPECTIVE. Every event with a location and a frame
becomes a training row, valued from the ACTING team's view (`team =
row["team"]`, direction and labels for that team). But ~13.5% of events
are by the team NOT in possession (checked on match 3764440: mostly
Pressure, plus Duel, Clearance, Interception, Block, Goal Keeper). A high
press on the opponent's keeper is therefore recorded as "my team has the
ball at x=105, beyond their defensive line, teammate nearby" — and it
rarely scores for the pressing team within 10 actions. The model is
taught that advanced states beyond the line are unproductive using
states in which the team does not have the ball. This is literally the
"knows where the ball is, not who has it" problem, and it is a data
definition error, not a missing feature.

DEFECT B — THE LABEL SKIPS ITS OWN EVENT. The lookahead is
`for k in range(i + 1, ...)`. A shot that scores is event i, so its own
row gets label_for = 0. Shots are taken disproportionately from exactly
the states scenario_c is about (behind the line, near goal), so the most
dangerous states are systematically labelled as not scoring.

Both defects date from engine v1 and were carried through every task
since.

## Disclosure (goes in the results page and the paper)
This task was written AFTER T4 scenario_c failed (Task 19d) and AFTER
Task 21, which was itself declared the last fix. The author chose to
continue. The justification is that A and B are definitional errors
found by reading code, of the same kind as the Task 19c/19d sort-index
bugs, not a new feature search. The results must be reported in full
whether they help or hurt.

## Predictions, recorded before running (reported right or wrong)
P1. A majority of the 2,602 rows in Task 21's zero cell are
    out-of-possession rows.
P2. After the fix, in-possession rows beyond the line score MORE than
    in-possession rows not beyond the line, in bands 80-100 and 100-120.
P3. T2's direction flips: more numerical advantage ahead predicts a
    HIGHER scoring probability (T2's pass condition is magnitude only;
    the sign is reported, not gated).

## Step 0 — Commit this brief alone. Record the hash.
In a second commit, add `docs/CHAT-HANDOFF.md` and
`docs/specs/task-20-player-results.md` (both currently untracked).
Do NOT stage or commit `docs/JOURNAL.md` in this task (research lead's
file, has pending edits).

## Step 1 — Revert Task 21's features from the model, change nothing else yet
Remove `distance_to_nearest_teammate_u`, `teammates_within_5u`,
`teammates_within_10u` from `STATE_FEATURES` (Task 21's premise failed).
Leave their computation in both feature builders so
`test_frame_features_agree.py` still runs and passes. The starting point
is therefore Task 19d's model definition.

## Step 2 — Rebuild rows with the two fixes, then the premise check
In a new builder (next free `_vN` suffix; do not edit Task 15's frozen
outputs):
  (A) Keep ONLY rows where `team == possession_team`. Report counts of
      rows dropped, overall and by event type.
  (B) Lookahead starts at the event itself: `range(i, ...)`. Everything
      else about the window (LOOKAHEAD=10, no possession reset, own-goal
      handling) unchanged.
Write the training rows (in-possession only, new labels) to the new rows
file. Separately write a DIAGNOSTIC file of ALL rows with columns
`event_id, type, team, possession_team, in_possession, label_for_old,
label_for_new, label_against_old, label_against_new` plus the state
features, for the tables below. Commit the script that builds the tables
(Task 21's Step 3 table was not reproducible; do not repeat that).

Report:
  T-a. For Task 21's zero cell (band 80-100, beyond line, teammate
       within 5u): share out-of-possession and its top event types. (P1)
  T-b. Number of rows whose label_for changes old -> new, and how many of
       those are Shot events.
  T-c. PREMISE TABLE, in-possession rows only, new labels:
       P(score in 10) and P(concede in 10) by band (0-40, 40-60, 60-80,
       80-100, 100-120) x beyond line (yes/no), with n per cell.
PREMISE HOLDS if, in BOTH bands 80-100 and 100-120, beyond-line scores
strictly higher than not-beyond. If it does not hold, STOP here: no
retraining, report, done.

## Step 3 — Retrain and recompute (only if the premise holds)
Retrain M_for and M_against on the new rows (same hyperparameters, same
split seed). Report held-out AUC and calibration vs Task 19d.
Print one worked example from a real frame showing that both EV branches
(success = passing team in possession at destination; turnover =
opponent in possession at destination) are built from the possessing
team's perspective in `features.py`. If either branch is not, STOP and
report.
Recompute EV corpus-wide into a new options_ev directory, refit the
softmax temperature, re-score the policy, recompute Decision and Risk,
re-run T6 and the separation check. Execution is NOT recomputed or
reported in this task (Study C is out of scope for the abstract).
R4 offside rule, grid, pass-success model, policy features: unchanged.

## Step 4 — Falsification battery
T1 (restate, unchanged), T2 (report magnitude verdict AND sign, P3),
T3, T4 all three scenarios, T5, T6. T4's corpus percentile MUST be
computed on THIS task's new EV corpus (Task 19d's first run got this
wrong). Report every test with its pass condition and the Task 15,
19c, 19d values alongside.
STOP CONDITIONS: if ANY of T2, T3, T4 (any scenario), T5, T6 fails,
STOP after reporting. Do not run Step 5. (This closes the gap in Task
19d, where a T4 failure did not stop the task.)

## Step 5 — Cross-fitted outcome validation (only if Step 4 fully passes)
New crossfit script: per-fold value models trained on the NEW rows
file; this task's refit temperature (report if it differs from 0.1572).
Full battery, specifications unchanged. Columns: engine v1 published,
Task 19c, Task 19d, this task.

## HARD RULES
- Changes allowed: Step 1's removal, fixes A and B. Nothing else — no
  hyperparameters, features, thresholds, horizon, grid, offside rule or
  test definitions. Report `git diff --stat`.
- One run. If a stop condition fires, no alternative construction is
  tried.
- Single machine (this Mac). No distributed setup.
- Every quantity before and after, including regressions.
- No leaderboards, no player identity, no interpretation.
- No memory writes. Don't edit docs/JOURNAL.md.
- When finished, reply only that the task is done plus commit hashes.

## Output
docs/results/22-possession-perspective.md (template). Commit per rule 9.
