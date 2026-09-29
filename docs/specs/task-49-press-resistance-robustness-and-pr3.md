# Task 49 — Press resistance: robustness, the "fewer chances" puzzle, and a value-based version (PR v3)

Written 2026-09-28 (late evening, Pacific) by the research lead after
reading results 48, BEFORE any result of this task exists.
This REPLACES the version committed in 1647750 (never run). The regista
scorecard in that version is PINNED for later; its spec stays in git at
1647750.

## Why
Task 48 taught three things:
1. The two confirmed results (C4 travels club <-> country; C6 team-
   adjusted PR -> reaching the final third) were never checked for role
   persisting or for men vs women (1,184 of 1,985 reserved matches are
   women's). -> Part A.
2. Keeping the ball under pressure goes with FEWER chances (2015/16 all
   players −0.046, p = 7e-5; reserved DMs −0.083, p = 0.022). The
   outcome counts only the next 10 events, which may cut off slow,
   recycled possessions. -> Part B.
3. PR2_flag_keep scores any completed pass as success, so a safe
   backward pass counts the same as a line-breaking one (Task 45: top
   DMs recycle backward 37% vs 32%). -> Part C builds PR v3, which
   credits what the escape achieved, in possession-value terms.

## Step 0 — Commit this brief alone. Record the hash.
Memory gate as in Task 25 before each Part.

## Part A — Robustness of C4 and C6 (reserved data; report only)
A disclosed SECOND LOOK at the reserved data, allowed only as a
robustness check of already-confirmed results (BENCHMARK-v6 rule 2).
These checks can only weaken the claims. RULE, fixed now: whichever
version is weaker governs how the result is worded. Nothing else runs
on the reserved data. Holdout untouched. Reuse Task 48 artifacts/code.

A1. C4 by gender (competitions.json competition_gender). Task 48's C4
    recipe unchanged. Run a group only if >= 15 movers; else report n.
A2. C4 role- and zone-adjusted: residualise each context unit's
    PR2_flag_keep mean by WLS (weight = pressured receptions) on the
    player's reserved-data Task 32 role (categorical; MIXED its own
    level) and the unit's zone shares (event-only, as the covariates in
    Task 46 A-i). Rebuild sides from residuals, recompute split-half
    reliabilities on residuals (Task 27 Step 3's approach), rerun C4.
    All movers, then men / women.
A3. C4 within Task 48's 193 deep midfielders if >= 15 movers; else n.
A4. C6 (Task 48's model) for men's and women's competitions separately.
Report n, reliabilities, r_obs, r_true, 95% CI (C4); coef, CI, p, MDE,
control (C6).

## Part B — The "fewer chances" puzzle (2015/16 only; development; 4th use)
Measure unchanged: Task 44's PR2_flag_keep, S = other-match mean
(>= 50 elsewhere), Task 44's P-test (event-only g, fe_fit, retention
control on the same rows). Only the outcome Y changes. Outcomes:
 Y_poss   xG of the receiver's team from the reception to the end of
          that possession (StatsBomb possession id).
 Y_poss2  Y_poss minus the opponent's xG in the NEXT opponent
          possession (counter-attack risk after a loss or turnover).
 Y_w20, Y_w30  net xG over events i+1..i+20 and i+1..i+30.
 (Y_w10 = Task 44's net xG, re-reported for reference.)
Run for deep midfielders (Task 44's 185) and all players. Report coef
per 100 per SD, 95% CI, p, MDE, control. Also a descriptive table:
pressured spells by ending (completed forward / sideways / backward
pass, as in Task 45's dx rule; loss), with mean Y_F3, Y_w10 and Y_poss.
Reading rule, fixed now: if the sign turns non-negative on Y_poss for
all players, the Task 44/48 negative is recorded as a window artefact;
if it stays negative with p < 0.05, it is recorded as real.

## Part C — PR v3: value-based press resistance (2015/16; development)
C1. Event-only possession value model V (engine v5's logic on events):
    two XGBoost classifiers, P(team in possession scores within the next
    10 events, counting the current event) and P(it concedes within 10).
    V = P_for − P_against. Rows = events by the team in possession only
    (Fix A); a scoring shot is labelled 1 (Fix B). Features: x, y,
    distance and angle to goal, event type, under_pressure, body part
    where present, period, minute, score difference, previous event's
    type and end location. Cross-fitted on Task 44's 5 match folds
    (seed 20260928). Report OOF AUCs, calibration by decile (bar <= 5
    pp), and V by x band (must rise toward goal, as G2).
C2. Spell value: for each Task 43 pressured spell, dV = V(end) − V(at
    reception), both from the receiver's team's perspective.
    V(end) = V at the next event after the spell's ending action; if
    that event belongs to the opponent, use −V(opponent). State the
    exact rule used for the end of match or period.
C3. PR3 = dV − E[dV | context], E from the event-only g features
    (cross-fitted, same folds). Player score = mean over his spells.
C4. Tests (bars fixed now; all development, no claim beyond "study"):
    - Stability (Task 38's method, >= 10 matches): DM and all. Bar 0.60.
    - Praised list (Task 41's method, direction higher): unadjusted and
      A1 team-demeaned.
    - P-test with S = other-match PR3 (>= 50 elsewhere), Y = Y_F3 and
      Y_poss (from Part B), DM and all; control on the same rows.
    - Correlation with PR2_flag_keep (players >= 50 spells), DM and all.
    - DM table (Task 29's method), output only.
    - Holm across the four P-tests.

## HARD RULES
- Reserved data: Part A only. Holdout untouched. Study sample and PFF
  not used.
- No change to any definition fixed in Tasks 32-48; PR3 is a new
  measure and PR2_flag_keep stays as it is.
- Named-player ranks are output only, never a criterion.
- No memory writes. Don't edit docs/JOURNAL.md. No interpretation.
- Commit after each Part (interim page allowed), and at the end.
- When finished, reply only that the task is done plus commit hashes.

## Output
docs/results/49-press-resistance-robustness-and-pr3.md (template).
Commit per rule 9.
