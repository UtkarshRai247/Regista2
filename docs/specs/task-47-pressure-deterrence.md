# Task 47 — Do opponents learn to stop pressing a press-resistant player?

Written 2026-09-28 by the research lead, before any result. DEVELOPMENT
task (exploratory) on 2015/16 (labelled as a further use). The RESERVED
data listed in Task 46 must not be opened. Holdout spent.

## Idea (the author's)
If a player escapes most presses early in a match, opponents may stop
pressing him later because it wastes energy and space. So a player's
early success under pressure should predict LESS pressure on him later
in the same match, beyond what happens to everyone.

## Step 0 — Commit this brief alone. Record the hash.

## Step 1 — Units and measures (fixed now)
Unit: player x match, outfield players, with >= 10 completed receptions
in EACH half (periods 1 and 2 only).
- PRESSURED reception: Task 44's flag rule.
- Expected pressure p(context): cross-fitted XGBoost classifier (Task 42
  settings, 5 match folds, seed 20260928) of PRESSURED on reception x,
  y, play pattern, minute, score difference (at the reception), and the
  player's Task 32 role. No identity.
- P_H = mean(PRESSURED - p) over his receptions in half H (H1, H2).
- E1 = his early escape success: mean PR2_flag_keep over his pressured
  receptions in the FIRST half (>= 5 required; unit dropped otherwise).
Report n units, n players, and base rates.

## Step 2 — Main test
Model: (P_H2 - P_H1) ~ E1 + P_H1 + team-match FE + role FE; SE
clustered by player. P_H1 is included because a player pressed
unusually often early will tend to be pressed less later regardless
(regression to the mean).
PREDICTION (the author's): coefficient on E1 NEGATIVE.
Report coefficient per SD of E1, 95% CI, p.

## Step 3 — Placebo and alternatives
(a) PLACEBO: the same model with the outcome replaced by his TEAMMATES'
    change in pressure (their mean P_H2 - P_H1, excluding him), same
    controls. If his early success also "reduces" pressure on everyone,
    the main result is about the game, not about opponents reading him.
(b) Within the second half only: split H2 into minutes 46-67 and 68-90
    and repeat the main model for each part.
(c) Season level (report only): correlation, within role, between a
    player's season PR2_flag_keep and his season mean P (how pressed he
    is overall), players with >= 10 matches. A negative correlation
    would fit opponents avoiding pressing him.
(d) Deep midfielders only: repeat Step 2 and (a).

## Claim rule (fixed now)
Exploratory. A statement for confirmation on the RESERVED data is
proposed only if Step 2's coefficient is negative with p < 0.05 AND the
placebo (a) is not negative with p < 0.05. Otherwise the idea is
reported as not supported by these data.

## HARD RULES
- Do not open RESERVED data. Holdout untouched.
- No change to earlier definitions or artifacts.
- Memory gate as in Task 25.
- No memory writes. Don't edit docs/JOURNAL.md. No interpretation.
- When finished, reply only that the task is done plus commit hashes.

## Output
docs/results/47-pressure-deterrence.md (template). Commit per rule 9.
