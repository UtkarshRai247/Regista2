# Task 34 — Reception quality: do the best deep midfielders receive in more space?

Written 2026-09-28 by the research lead BEFORE reading Task 33's results
(committed by the research lead immediately, before opening
docs/results/33-fixes-a2-a3.md, so the timestamp shows it). Nothing in
this plan may be changed after Task 33 is read, except to fix a factual
error, which must be marked as such.

## Question
Coaches say elite deep midfielders are "always free". Our pass-choice
measure starts once the player has the ball, so it treats the space he
created as circumstance. This task measures that space directly.

## Prior work (checked)
StatsBomb already publishes "ball receipts in space": counts of
receptions by distance to the nearest defender (0-2, 2-5, 5-10, 10+
yards), and SkillCorner has pressure-at-reception metrics from tracking
data. So raw "space at reception" is NOT new. What would be new here:
adjusting for pitch zone, situation and team style, and testing it the
way we tested Decision: within-role stability, following players
across teams, and predicting other matches.

## Data
Ball Receipt* events with no failure outcome, receiver = the frame's
actor, 360 frame present (about 93% of receptions). Engine v5
coordinates (team-relative, no flipping). 292 matches (the same set as
engine v5). Holdout untouched.

## Step 0 — Commit this brief alone (the research lead has already done
## so; record that hash). Do not modify this file.

## Step 1 — The measure
space = distance from the receiver to the nearest VISIBLE opponent,
capped at 15 units.
Expected space f(context), an XGBoost regression, cross-fitted with the
SAME 5 match folds as engine v5, from context only:
  receiver x and y; play pattern; number of visible opponents in the
  frame; period; minute; the opponent team-context's mean space allowed
  to receivers in its OTHER matches.
  NO player identity, NO own-team identity.
  objective reg:squarederror, n_estimators 300, max_depth 6,
  learning_rate 0.05, subsample 0.8, seed 20260928.
RQ = space - f_oof(context)            (context-adjusted)
RQ_rel = RQ - mean RQ of the receiver's teammates in the same
         team-context, excluding himself       (team-relative)
Report: n receptions; out-of-fold R^2 of f; mean RQ by zone (must be
near zero by construction); distributions.

## Step 2 — Tests (bars fixed now)
Roles and deep-midfield group: Task 32 Step 4's role rule (>= 50% of
passes at the role's positions); deep midfield = Task 27's 111.
R1 Stability within deep midfielders: step8_regate.py's reliability
   function on RQ_rel, units = player x competition-season, at 100, 200
   and 300 receptions. PASS if median reliability at 200 >= 0.60.
   Also report for every role and for all roles.
R2 Follows the player across teams: players with >= 2 team-contexts of
   >= 50 receptions each; correlation of RQ_rel between contexts,
   disattenuated with the Study B PH-B2 procedure and its bootstrap.
   PASS if the 95% lower bound > 0. Report n players.
R3 Predicts other matches: Task 32 Step 5's LINEUP construction, but
   over receptions: each reception contributes its receiver's mean RQ
   from his OTHER matches (receivers with >= 50 receptions elsewhere);
   unit score = mean over the match's receptions; keep units with
   >= 70% coverage. H-O1 for xG. PASS if coefficient > 0 and p < 0.05.
   Also report goals, and PH-O2 (team-context FE) for both.
R4 Distinct from what we have: within deep midfielders, correlations of
   player RQ_rel with Decision (v5 cross-fitted), move_on_speed,
   median_time_on_ball, completion rate, receptions per team pass while
   on the pitch (first to last event in the match). Report only.

## Step 3 — Deep-midfield table
Task 29's method (within-group noise, DerSimonian-Laird, shrinkage,
90% intervals) applied to RQ_rel per reception. Report the Q test,
every player's n, raw, shrunken and interval, the count entirely above /
below the group mean with names, and the six named deep midfielders.
Output only — names never used as a criterion.

## What may be claimed (fixed now)
- R1 and R3 both pass: "reception quality is a stable deep-midfield
  trait that shows up in other matches' results" may be claimed.
- R1 passes, R3 fails: a stable trait, no evidence it affects results.
- R1 fails: no player-level claim about reception quality.
- R2 is reported with its interval and qualifies any claim.
- PH-O2 is reported beside R3; if it is not positive, the paper says
  the R3 result cannot be separated from team quality.

## HARD RULES
- No change to engine v5 or any Task 33 artifact.
- Holdout untouched.
- Commit the results page after Step 1, then at the end.
- Memory gate as in Task 25.
- No memory writes. Don't edit docs/JOURNAL.md. No interpretation.
- When finished, reply only that the task is done plus commit hashes.

## Output
docs/results/34-reception-quality.md (template). Commit per rule 9.
