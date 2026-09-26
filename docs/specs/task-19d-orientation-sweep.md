# Task 19d — Systematic sweep for orientation bugs, then fix and re-run

Two instances of the same sort-index bug have now been found by
inspection, the second in a feature the value models depend on. Stop
finding them one at a time.

## Step 0 — Commit this brief. Record hash.

## Step 1 — SWEEP FIRST. Report, do not fix.
Across every file in src/engine_v2/ and any tempo or shared module they
import, find and list EVERY place that:
  (a) calls np.sort, np.argsort, np.partition, sorted(), nsmallest,
      nlargest, or indexes a sorted array;
  (b) uses min/max/argmin/argmax on a spatial coordinate;
  (c) uses a percentile, quantile or rank on a coordinate;
  (d) depends on attacking direction, including every call to
      normalize_xy / normalize_xy_arr and every comparison of an x or y
      value against a constant;
  (e) assumes an ordering of players, e.g. rearmost, deepest, highest,
      last defender, first attacker.
For each, report in a table: file, line, the expression, what the code
INTENDS semantically, and CORRECT / WRONG / UNCLEAR.
This is the whole of Step 1. Do not change any code yet.

## Step 2 — Fix only what Step 1 proved wrong
Apply the minimal change for each WRONG item, listing every edit. For
each fix, print a worked example from one real frame showing the old
value, the new value and why the new one is right — as Task 19c did.
Leave UNCLEAR items alone and list them for the research lead.

## Step 3 — Retrain and recompute what the fixes affect
If any fix touches a value-model feature (defensive_line_x and
ball_beyond_defensive_line are known to), retrain BOTH value models and
recompute EV, Decision, Risk and Execution corpus-wide. Keep the
corrected offside rule (R4) from Task 19c.
Report held-out AUC and calibration for both value models, old vs new.

## Step 4 — Re-run the falsification battery
T2 (value model responds to defensive context), T3 (EV not a risk
score, Spearman < 0.90), T4 (all three synthetic scenarios), T5
(pass-success calibration by length bucket), T6 (Decision reliability
>= 0.60 at 200), and the separation check.
Report each with its pass condition, its verdict, and the previous
value from Tasks 15/17/19c.
If T2, T3 or T6 now fails, STOP and report. Do not tune.

## Step 5 — Re-run cross-fitted outcome validation
Full battery, specifications unchanged, on cross-fitted Decision.
Report columns: engine v1 published, Task 19c cross-fitted, and this
task's cross-fitted figures.

## HARD RULES
- Step 1 is a report. No code changes until it is written out.
- Fix only what the sweep proves wrong. No opportunistic refactoring,
  no feature additions, no hyperparameter changes.
- Report old vs new for every quantity, including regressions.
- No leaderboards, no player identity, no interpretation.
- No memory writes. Don't edit docs/JOURNAL.md.
- When finished, reply only that the task is done plus commit hashes.

## Output
docs/results/19d-orientation-sweep.md (template). Commit per rule 9.
