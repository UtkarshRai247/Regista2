# Task 49 — Robustness of the two confirmed results, and the regista scorecard

Written 2026-09-28 (late evening, Pacific) by the research lead after
reading results 48, BEFORE any Part A number exists.

## Why
Task 48 confirmed C4 (press resistance travels club <-> country) and C6
(team-adjusted press resistance -> reaching the final third) on the
reserved data. Two things a reviewer will ask were never checked:
(1) is C4 partly role persisting (Task 27 showed this cut Decision's
mover correlation from 0.62 to 0.27), and (2) does it hold in men's and
women's football separately (1,184 of 1,985 reserved matches are
women's). Part A answers these. Part B assembles the headline evidence
table from EXISTING results only.

## Step 0 — Commit this brief alone. Record the hash.

## Part A — Robustness of C4 and C6 on the reserved data (report only)
Status: a disclosed SECOND LOOK at the reserved data, allowed only as a
robustness check of already-confirmed results (BENCHMARK-v6 rule 2).
These checks can only weaken the claims. RULE, fixed now: whichever
version is weaker governs how the result is worded in the abstract.
Nothing else is run on the reserved data. Holdout untouched.
Reuse Task 48's saved artifacts and code; no definition changes.

A1. C4 by gender. Split movers by competition gender (competitions.json
    competition_gender). Same recipe as Task 48 C4 (>= 30 pressured
    receptions per context, split-half reliabilities, disattenuation,
    1,000-player bootstrap). Run a group only if >= 15 movers; else
    report n. Report n, both reliabilities, r_obs, r_true, 95% CI.
A2. C4 role- and zone-adjusted. Before building club and international
    sides, residualise each context unit's PR2_flag_keep mean by WLS
    (weight = pressured receptions) on (i) the player's reserved-data
    Task 32 role (categorical; MIXED as its own level) and (ii) the
    unit's zone shares, computed event-only exactly as the covariates
    in Task 46 A-i. Then rebuild sides from residuals and rerun the C4
    recipe, recomputing split-half reliabilities on residuals (Task 27
    Step 3's approach). All movers, then men / women as in A1.
A3. C4 within deep midfielders (Task 48's 193): run only if >= 15 DM
    movers; else report n.
A4. C6 by gender: Task 48's C6 model (A1 team demeaning, event-only g,
    retention control on the same rows), men's and women's
    competitions separately. Report coef, 95% CI, p, MDE, control.

## Part B — The regista scorecard (compilation only; NO new data runs)
One table answering, for each eye-test trait, the questions below, for
DEEP MIDFIELDERS first and ALL PLAYERS second, each sample on its own
row (study 360 / PFF WC2022 / 2015/16 / holdout / reserved).
Copy every number from its results page and cite file + section. If two
pages disagree, report both and flag it. A cell with no existing test
says "not tested" — do not run anything to fill it.

Traits (rows):
 T1 Decision quality (v5 Decision; v6 as a variant line)
 T2 Press resistance: keeping the ball when pressed (PR2 / PR2_flag_keep,
    unadjusted and A1 team-adjusted)
 T3 Willingness to take the ball when pressed (W)
 T4 Reception space (RQ_rel)
 T5 Availability (AV; mark every cell "PFF — licence pending")
 T6 Tempo: HOLD_VARIATION and MOVE_ON_SPEED

Questions (columns):
 Q1 Stable? split-half stability (bar 0.60), with n.
 Q2 Do deep midfielders genuinely differ? heterogeneity Q (df, p) and
    count above / below the group mean.
 Q3 Player, not team? movers r_true or variance share S, with CI; the
    role/zone-residualised version where one exists (incl. Part A).
 Q4 Linked to results in OTHER matches? P-test coef, 95% CI, p, Holm p
    where given, MDE, and which outcome (net xG or Y_F3).
 Q5 Do the pre-listed praised registas stand out? T, p, n present;
    unadjusted and team-adjusted where both exist.
 Q6 Status per cell: CONFIRMED on untouched data / DEVELOPMENT sample
    only / NOT TESTED / FAILED.

Status rule (fixed now, applied mechanically):
- Q1 "stable" = median >= 0.60. Q3 "player not team" = 95% lower bound
  > 0. Q4 "linked" = p < 0.05 after that task's stated correction, with
  its positive control positive on the same rows.
- CONFIRMED only if the test was pre-declared and run on the holdout or
  reserved data (Tasks 26, 37, 48) or is a Part A check of one.

Two post-hoc pooled estimates, labelled "post hoc, not a test":
fixed-effect inverse-variance pooling (SE from each 95% CI / 3.92) of
 (a) DM press resistance -> Y_F3: Task 44 P2 and Task 48 C1;
 (b) DM Decision -> net xG: Task 35 Step 3 and Task 37 Step 3.
Report pooled coef, 95% CI, p. No other pooling.

Also list, with its page, every figure the handoff marks "(from chat
summary)" that enters the table, and say whether the page agrees.

## HARD RULES
- Part A is the only data run. No definition changes from Tasks 32-48.
- Named-player ranks are output only.
- Memory gate as in Task 25. No memory writes. Don't edit JOURNAL.md.
  No interpretation.
- When finished, reply only that the task is done plus commit hashes.

## Output
docs/results/49-robustness-and-regista-scorecard.md (template).
Commit per rule 9.
