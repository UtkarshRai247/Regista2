# Task 21 — Value model: possession state, not ball position

THE LAST ENGINE FIX. If the falsification battery does not pass after
this, the engine is reported as not meeting its acceptance criteria and
no player-level claim is made.

## Why (evidence, recorded before the change)
Empirical rates from value_model_rows_v2.parquet, P(team scores within
10 actions) by whether the ball is beyond the defensive line:
  band 60-80:  0.31% not beyond, 0.13% beyond
  band 80-100: 0.98% not beyond, 0.28% beyond
  band 100-120: 2.96% not beyond, 1.18% beyond
and conceding rises, 0.48% -> 0.84% in the final band.
The model reading "beyond the line = less dangerous" is therefore
CORRECT for the data as represented. The defect is the representation:
the state features describe where the BALL is, not whether the
possessing team actually has it. Balls through to the keeper, overhit
crosses and passes to nobody outnumber successful through balls, and V
cannot tell them apart.

This is the same class of defect as the location-only value function
the rebuild set out to fix.

## Disclosure
This change is POST HOC — made after T4 scenario_c failed in Task 19d.
It is justified by the empirical table above, not by T4's verdict, and
every affected quantity is reported before and after. That disclosure
goes in the results page and the paper.

## Step 0 — Commit this brief. Record hash.

## Step 1 — Add possession-state features, and nothing else
In value_models.py's frame_ahead_features AND features.py's
state_features_batch (both must agree — they were independently written,
which is how the last bug hid), add exactly:
  - distance_to_nearest_teammate_u (from the valued ball position)
  - teammates_within_5u
  - teammates_within_10u
No other feature changes. No hyperparameter changes. No changes to the
pass-success model, the policy, the grid, the offside rule (R4 stays),
or the horizon.
Print a worked example from one real frame showing the three new values
for a state where the ball is beyond the line with a teammate on it, and
one where it is beyond the line with no teammate near.

## Step 2 — Rebuild, retrain, recompute
Rebuild the value-model training rows, retrain M_for and M_against,
recompute EV, Decision, Risk and Execution corpus-wide with the Task 19c
restriction and refit temperature.
Report held-out AUC and calibration for both models, Task 19d vs now.

## Step 3 — Empirical check the change is supposed to fix
Recompute the table above, now SPLIT by whether a teammate is within 5u
of the ball. Report P(score in 10) for: beyond the line with a teammate
near, beyond the line with none, not beyond with a teammate near, not
beyond with none — per pitch band.
If "beyond the line with a teammate near" does NOT show a higher scoring
rate than "beyond the line with none", the premise of this fix is wrong;
report that plainly and stop before Step 4.

## Step 4 — Full falsification battery
T2, T3, T4 (all three scenarios), T5, T6, plus the separation check.
Report each with its pass condition and the Task 15/19c/19d values.
ALL of T2, T3, T4 and T6 must pass. If any fails, STOP and report — no
further fixes, no tuning, no fourth attempt.

## Step 5 — Cross-fitted outcome validation
Full battery, specifications unchanged. Report columns: engine v1
published, Task 19c, Task 19d, and this task.

## HARD RULES
- Three features, two files, nothing else. Report git diff --stat.
- Both feature builders must produce identical values for the same
  frame; assert it in a committed test.
- Report every quantity before and after, including regressions.
- No leaderboards, no player identity, no interpretation.
- No memory writes. Don't edit docs/JOURNAL.md.
- When finished, reply only that the task is done plus commit hashes.

## Output
docs/results/21-possession-state.md (template). Commit per rule 9.
