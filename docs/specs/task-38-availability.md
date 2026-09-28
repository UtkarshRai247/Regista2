# Task 38 — "Always available": do elite deep midfielders make themselves an option? (PFF WC2022)

Written 2026-09-28 by the research lead after reading
docs/results/36-pff-ingest.md, before any availability number exists.

Answers to Task 36's questions:
Q1: use the top-level Event Data (v2.5 spec).
Q2: do NOT align StatsBomb events to tracking for this task. PFF's own
    events carry a synchronised snapshot of all 22 players (identity,
    position, speed, visibility) and the ball, so this task uses PFF
    events and their embedded snapshots only. StatsBomb is used only
    for shot xG (via Task 36's shot pairs) and for positions/roles via
    the player map.
Q3: map Morocco #1 "Bono" to Yassine Bounou (unique team + shirt match);
    record the override. He is a goalkeeper and excluded below anyway.
Q4: choices accepted as made.
Q5: add the two missing extra-time tracking matches to the data notes
    in this task's results page; nothing else.

## Question
Coaches say elite deep midfielders are "always available". StatsBomb's
snapshots only identify the player on the ball, so we could never see
a player who was open and NOT passed to. PFF's snapshots identify
everyone. This task measures how often a player is a genuinely open
option at his teammates' passes, whether that is stable, and whether it
shows up in results.

## Data
PFF possession events of type PA (pass) and CR (cross), nonEvent false,
periods 1-4, all 64 matches. At each such event, the embedded snapshot.
Coordinates: PFF metres, converted to the passing team's attacking frame
with Task 36's conversion (so +x is always toward the opponent goal).

## Step 0 — Commit this brief alone. Record the hash.

## Step 1 — The measure (fixed now)
For every pass/cross event, for every OUTFIELD teammate of the passer
(not the passer, not the goalkeeper) present in the snapshot:
  d_ball  = distance from the ball to the teammate
  space   = distance from the teammate to the nearest opponent
  lane    = minimum distance from any opponent to the straight segment
            ball -> teammate
  AVAILABLE = (5 m <= d_ball <= 40 m) AND (space >= 3 m) AND
              (lane >= 2 m)
Baseline p(context): XGBoost classifier, cross-fitted over 5 folds of
MATCHES (seed 20260928), predicting AVAILABLE from things the teammate
does not control: ball x and y; passer under pressure (PFF pressureType
not null); number of opponents within 10 m of the ball; score
difference for the passing team; period; minute; the teammate's PFF
positionGroupType. NO player or team identity, and NOT the teammate's
own location (getting to the right place is part of the skill).
objective binary:logistic, n_estimators 300, max_depth 6,
learning_rate 0.05, subsample 0.8.
AV = AVAILABLE - p_oof (per moment). Player score = mean AV.
Sensitivity AV_vis: the same, restricted to moments where the teammate
AND his nearest opponent are VISIBLE.
Report: n moments, base rate of AVAILABLE, baseline out-of-fold AUC,
and how often an AVAILABLE teammate was the pass target (PFF
targetPlayerId) vs a non-available one.

## Step 2 — Groups
Deep midfielder (DM) = at least 50% of his WC2022 StatsBomb eligible
passes at Center/Left/Right Defensive Midfield (Task 27's rule, applied
to WC2022 matches only), and at least 3 matches and 300 moments in PFF.
Report the list and n.

## Step 3 — Tests (bars fixed now)
R1 Stability (DM): for each DM with >= 4 matches, 100 random splits of
   his MATCHES into halves; correlate half-means across players;
   Spearman-Brown to full length. PASS if median >= 0.60. Also report
   for all outfield players with >= 4 matches, and for AV_vis.
R2 Results (pass-level, out-of-match, same design as Task 35 (d)):
   unit = a completed reception by a player (PFF receiverPlayerId);
   Y = net xG over the next 10 PFF possession events (StatsBomb xG of
   Task 36-paired shots; unpaired PFF shots excluded, count reported);
   S = the receiver's mean AV from his OTHER matches (>= 2 other
   matches); controls: g = cross-fitted XGBoost of Y on the reception's
   location, pressure, period, minute (Task 35's hyperparameters), role
   FE (PFF positionGroupType), team-match FE; SE clustered by player.
   Run for all outfield receivers (PRIMARY) and for DMs (report).
   PASS (primary) if coefficient > 0 and p < 0.05. Report MDE.
R3 Distinct from what we have (DM, report only): correlations of
   player AV with v5 Decision (cross-fitted, WC2022 passes), Task 34
   RQ_rel (WC2022 receptions) and receptions per match.

## Step 4 — DM table (output only)
Task 29's method (within-group noise, DerSimonian-Laird, shrinkage,
90% intervals) on AV per moment, within the DM group. Every DM: team,
matches, moments, raw AV, shrunken AV, interval; the Q test; count of
intervals entirely above / below the group mean, with names. Also the
same columns for AV_vis. Names are output, never a criterion.

## What may be claimed (fixed now)
- R1 and R2 pass: "being available is a stable skill, and players who
  are more available in other matches create more from their
  receptions."
- R1 passes, R2 fails: a stable trait; no evidence it shows up in
  results in this sample (state the MDE).
- R1 fails: no player-level availability claim.
- If AV and AV_vis disagree on R1 or R2, both are reported and the
  claim is limited to what AV_vis supports.

## HARD RULES
- No change to engine v5, Tasks 33-37 artifacts, or Task 36's data.
- Holdout untouched (it has no PFF data anyway).
- Memory gate as in Task 25; one match in memory at a time.
- No memory writes. Don't edit docs/JOURNAL.md. No interpretation.
- When finished, reply only that the task is done plus commit hashes.

## Output
docs/results/38-availability.md (template). Commit per rule 9.
