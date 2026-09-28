# Task 37 — Confirm the pass-level result on the untouched holdout (final holdout use)

Written 2026-09-28 by the research lead after reading
docs/results/35-power-and-pass-level-test.md, before any holdout number
for this test exists. Per BENCHMARK-v5 rule 3, this is the ONE remaining
use of the women's holdout. It is spent after this task.

## Why
Task 35's pass-level test (P-test) is the first test with enough power to
see an individual skill while holding team, opponent and game fixed. On
the study sample, v5 Decision measured in a player's OTHER matches
predicted the chance value created by his passes relative to teammates
in the same game (+0.075 xG per 100 passes per SD, Holm p = 0.0087),
with the positive control working. The P-test was designed after
earlier tests failed; that is disclosed. This task checks it on data
never used in any design choice.

## What is tested (fixed now)
PRIMARY: v5 Decision, scored by the FROZEN engine v5 exactly as in
Task 26 Step 1 (no retraining, refitting or recalibration).
Holdout: the 126 women's international matches in data/raw_holdout/
(Task 26's scored outputs).

## Step 0 — Commit this brief alone. Record the hash.

## Step 1 — Build the holdout P-test inputs
- Origin features: the value model's STATE_FEATURES at the passer's
  location from each pass's freeze frame, with engine v5's feature
  function (corrected coordinates), plus Task 33's f(state) extras.
- g: ONE XGBoost regression of Y on those origin features, trained on
  ALL study-sample passes (Task 35's specification and hyperparameters),
  then applied unchanged to holdout passes. Also one completion g for
  the positive control, same way.
- Y: realised net xG in events i+1 ... i+10 (Task 35's convention).
- S: passer's leave-one-match-out mean v5 Decision over OTHER HOLDOUT
  matches, passers with >= 100 eligible passes elsewhere in the holdout.
- Roles: Task 32 Step 4's rule applied to holdout positions.
Report: n passes, n passers, n team-matches, and how many passers
qualify per competition.

## Step 2 — The test
Model and inference exactly as Task 35 Step 2: Y ~ S + g + role FE +
team-match FE, SE clustered by passer.
POSITIVE CONTROL first: Y = completed (0/1), S = other-match completion
rate, completion g. If it is not positive with p < 0.05, the holdout
cannot answer the question: report that and do not interpret the
primary.
GATE: v5 Decision coefficient POSITIVE with p < 0.05 (two-sided).
Report coefficient per SD (per pass and per 100 passes), 95% CI, p,
MDE at 80% power, beside Task 35's study value.

## Step 3 — Report only (no gate)
Same test within the holdout's deep midfielders (Task 27's >= 50% DM
share rule applied to holdout positions), if at least 20 qualify;
otherwise say how many qualified.

## HARD RULES
- No engine change, retraining on holdout, or tuning of any kind.
- This is the final holdout use; do not run any other analysis on the
  holdout in this task.
- No memory writes. Don't edit docs/JOURNAL.md. No interpretation.
- When finished, reply only that the task is done plus commit hashes.

## Output
docs/results/37-holdout-ptest.md (template). Commit per rule 9.
