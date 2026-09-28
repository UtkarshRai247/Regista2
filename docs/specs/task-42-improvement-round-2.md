# Task 42 — Improvement round 2: outcomes that fit a deep midfielder's job, and press resistance

Written 2026-09-28 by the research lead after reading
docs/results/41-vetting-round-2.md, before any result. Study sample and
PFF WC2022 only (holdout spent). Everything is labelled "study sample
only". BENCHMARK-v6 is the comparison.

Answers to Task 41's questions: Q1 yes, a football-terms size must use
the within-role SD, and is only reported for roles where the effect is
established; Q2 the floors are fine.

## Why
Task 41 found the pass-level result is carried by forwards, and no
within-deep-midfielder test survives one correction across the family.
One reason is structural: the outcome so far is net xG in the next 10
events. A deep midfielder's pass is usually far from goal, so it rarely
leads to a shot within 10 events, and the test is nearly blind to what
his job actually is: moving the ball up the pitch and not losing it
under pressure. This task (A) uses outcomes that fit that job, and (B)
measures press resistance, the pattern the most-praised 6s showed
(taking the ball in tight space). New tests will be many, so the claim
rule at the bottom is strict and fixed now.

## Step 0 — Commit this brief alone. Record the hash.

## Step 1 (A) — Role-appropriate outcomes (StatsBomb possessions)
From the pass's (or reception's) team perspective, using StatsBomb's
`possession` id:
  Y_F3  = 1 if the team has an on-ball event (Pass, Carry, Ball
          Receipt*, Dribble, Shot) at normalised x >= 80 later in the
          SAME possession; else 0. Only for units starting at x < 80.
  Y_SHOT = 1 if the same possession contains a later shot by the team.
Report base rates overall and for deep midfielders.
P-test (Task 35 Step 2 design; g refit per outcome with Task 35's
function and settings; role FE; team-match FE; SE by player) for:
  S = v5 Decision (passes), RQ_rel (receptions, Task 34),
      MOVE_ON_SPEED (passes, Task 39's S).
Positive control (completion) on the same rows, as before.
Run for all players and for the 111 deep midfielders. Report coef per
100 units per SD, CI, p, MDE.

## Step 2 (B) — Press resistance (StatsBomb 360, all 292 matches)
Unit: completed Ball Receipt* with a 360 frame, receiver = actor.
PRESSURED: nearest visible opponent <= 3 units, OR StatsBomb
under_pressure on the receipt.
Next action: the receiver's own next on-ball event in the same
possession (Pass, Carry, Dribble, Shot).
  PR_keep = 1 if the team still has the ball at the event after that
            action (no turnover, miscontrol, dispossession or failed
            pass/dribble); else 0.
  PR_fwd  = 1 if PR_keep AND the action's end x minus the reception x
            is >= 5 units.
Baseline: cross-fitted XGBoost classifier (Task 35 folds; objective
binary:logistic, n_estimators 300, max_depth 6, learning_rate 0.05,
subsample 0.8, seed 20260928) from context only: reception x, y;
nearest-opponent distance; opponents within 5 units; play pattern;
period; minute. No identity.
PR = outcome - p_oof; player score = mean over pressured receptions.
Report: n pressured receptions, base rates, baseline AUC.
R1 (deep midfielders): step8_regate.py's reliability function at 50,
   100 and 150 pressured receptions. PASS if median at 100 >= 0.60.
R2: P-test with unit = pressured reception, S = other-match PR
   (>= 50 pressured receptions elsewhere), outcomes Y_F3 and net xG
   (window 10), all players and deep midfielders.
R3: praised list (Task 41 Step 7's method and list, within-role z,
   permutation p) for PR_keep and PR_fwd.
Table: Task 29's method within the 111 deep midfielders (output only).

## Step 3 (C) — Progressive availability (PFF WC2022)
AV_prog: as Task 38's AVAILABLE, AND the teammate is at least 5 m
nearer the opponent goal than the ball. Baseline refit as Task 38.
R1 (deep midfielders) and R2 (all outfield and deep midfielders) as
Task 38; praised-list check as Task 41 Step 7.

## Claim rule (fixed now)
- Family = every WITHIN-DEEP-MIDFIELDER results test in this task
  (Steps 1-3), Holm-adjusted together. A within-DM results claim is
  allowed only if Holm p < 0.05 AND the positive control on the same
  rows has p < 0.05. It is labelled "study sample only, not externally
  confirmed", and the page also reports the Holm p when Task 41's
  12-test family is added.
- A stability claim (R1) needs the stated bar.
- The praised-list checks are two-sided and reported only. The
  pre-declared direction of interest is HIGHER on PR_keep and PR_fwd
  (the praised players are thought to escape pressure) and none for
  AV_prog. No claim about "elite" players is made unless p < 0.05 in a
  pre-declared direction.

## HARD RULES
- No change to engine v5, v6 Decision, RQ, AV, tempo or earlier
  artifacts; only the new outcomes and measures above.
- Holdout untouched.
- Commit the results page after Step 1, then at the end.
- Memory gate as in Task 25.
- No memory writes. Don't edit docs/JOURNAL.md. No interpretation.
- When finished, reply only that the task is done plus commit hashes.

## Output
docs/results/42-improvement-round-2.md (template). Commit per rule 9.
