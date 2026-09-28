# Task 35 — Were the results tests strong enough? A power check and a pass-level test

Written 2026-09-28 by the research lead. No engine change. Holdout
untouched. BENCHMARK-v5 unchanged.

## Why
Tasks 32-34 judged player measures by team-match regressions: about
380 team-matches, with xG as the outcome. With team-context fixed
effects (PH-O2) a team contributes only 2-3 matches on average, so the
test compares a team with itself across very few games. Read off the
reported standard errors, PH-O2 could only detect effects of roughly
0.35 xG per match per SD, and LINEUP H-O1 roughly 0.19. Those are
larger than the gap between good and average teams. So "not detected"
may mean "the test could not see it", not "it is not there". This task
measures that directly, then runs a far more powerful test, fully
specified here before anything runs.

## Step 0 — Commit this brief alone. Record the hash.

## Step 1 — Minimum detectable effects of the tests already run
For every out-of-match test in Tasks 32 (Step 5), 33 (Step 4a) and 34
(R3): report the coefficient SE and the minimum detectable effect at
80% power, alpha 0.05 (2.8 x SE), in xG (or goals) per match per SD.
Report the between-team-context SD of team mean xG per match for
scale.

## Step 2 — The pass-level out-of-match test (P-test)
UNIT: an eligible pass (engine v5 corpus, 292 matches).
OUTCOME Y: realised net xG in the next 10 events after the pass
(sum of StatsBomb shot xG by the passer's team minus by the opponent,
events i+1 ... i+10, same window convention as the value model).
PLAYER SCORE S: the passer's mean of the measure in his OTHER matches
(leave-one-match-out), only passers with >= 100 eligible passes
elsewhere; standardised across passes.
SITUATION CONTROL g: a cross-fitted XGBoost regression predicting Y
from origin information only — the same feature set, folds and
hyperparameters as Task 33's f(state) — with g_oof as a covariate.
MODEL: Y ~ S + g_oof + role FE (Task 32 roles) + team-match FE
(the passer's team in that match). The team-match FE means every
comparison is between teammates in the same game: team strength,
opponent and game are held fixed. Standard errors clustered by passer.
MEASURES TESTED (each in its own model):
  (a) v5 Decision (cross-fitted, pass_der_crossfit_v5)
  (b) v6 Decision (Task 33, Decision_v6)
  (c) v5 ev_chosen (cross-fitted)
  (d) reception: unit = reception (Task 34), Y = net xG in the next 10
      events after the reception, S = receiver's other-match RQ_rel,
      same controls with g refit on reception origin features.
POSITIVE CONTROL (shows the test can detect a real player skill): unit
  = pass, Y = pass completed (0/1), S = passer's other-match completion
  rate, same controls. Expected clearly positive; if it is not, the
  P-test design is broken and (a)-(d) are not interpreted.
Report for each: n passes, n passers, coefficient per SD of S (xG per
pass and per 100 passes), 95% CI, p, and the MDE at 80% power. Apply a
Holm correction across (a)-(d) and report both raw and adjusted p.

## Step 3 — Same test within deep midfielders only
Repeat (a)-(d) restricting passes to the 111 deep midfielders (Task 27
group). Same reporting.

## HARD RULES
- No engine change, no new EV corpus, no change to any earlier
  artifact. Holdout untouched.
- The P-test specification above is fixed; report any operational
  choice you have to make in the deviations section.
- No memory writes. Don't edit docs/JOURNAL.md. No interpretation.
- When finished, reply only that the task is done plus commit hashes.

## Output
docs/results/35-power-and-pass-level-test.md (template). Commit per rule 9.
