# Task 12 — Total-effect spec, leaderboard, worked example

Governing document: docs/specs/analysis-plan-v2.md, Amendments v2-1 to
v2-9. The v2-8.4 verdict is closed and is not revisited.

## Step 0 — Commit Amendment v2-9 alone. Record hash and SHA-256.

## Step 1 — PH-O4 (v2-9.2)
Refit H-O1 and PH-O1 WITHOUT possession_share, outcomes xG and goals,
clustered by team context. Report the Decision coefficient per SD with
CI and p, in a table alongside the preregistered versions that include
possession share. Label the preregistered ones PRIMARY and PH-O4
DESCRIPTIVE. Do not state a conclusion about which is correct.

## Step 2 — Leaderboard (v2-9.4a)
Players pooled across all contexts with >= 200 eligible passes. Compute
shrunken Decision: mean + 0.744 x (player mean - overall mean), i.e.
empirical-Bayes shrinkage at the measured reliability. Report the top 20
and bottom 20 with player name, position group, competitions
contributing, total eligible passes, raw Decision per 100 and shrunken
Decision per 100. Also report how many players qualify in total.

## Step 3 — Worked example (v2-9.4b)
Among confirmation-half passes in the surviving Study A cells (middle
third, under_pressure = no, game state level OR trailing) where the
chosen type was NOT lateral_medium and a lateral_medium option was
available, select the pass whose g (EV*_lateral_medium - EV*_chosen
type) is the MEDIAN of that set. Report: match, competition, minute,
passing team, the passer's position group, the chosen option and the
best lateral_medium option (coordinates, distance, angle, p_success,
EV, policy probability), the number of options in the frame, the
number of visible players, and what actually happened next (the pass
outcome and the next two events).
Save the pass's full freeze-frame option table to
data/processed/worked_example.csv and commit it.

## HARD RULES
- No new hypotheses. Steps 2 and 3 are descriptive artifacts.
- The median-gap selection rule is fixed. Do not pick a better example.
- Report the leaderboard as computed, whoever is on it.
- No interpretation for the paper. No memory writes. Don't edit
  docs/JOURNAL.md.
- When finished, reply only that the task is done plus commit hashes.

## Output
docs/results/12-artifacts.md (template). Commit per rule 9.
