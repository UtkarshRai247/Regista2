# Task 26 — Holdout replication, then the player results

Written 2026-09-28 by the research lead after reading
docs/results/25-engine-rebuild-v5.md. The engine built in Task 25
(corrected coordinates) is the accepted engine, subject to Step 1.
Answers to Task 25's questions: (1) the holdout gate still applies —
it is Step 1 here; (2) Execution's cross-team defect is scheduled after
the abstract and is out of scope here; (3) the reading is correct: the
recalibrated rule (R1_K10) is the offside rule.

This task SUPERSEDES docs/specs/task-20-player-results.md (written for
the old coordinates). Nothing in the engine changes in this task.

The accepted engine ("engine v5") = Task 25's artifacts:
value_model_for_v5.json, value_model_against_v5.json,
pass_success_model_v3.json, offside rule R1_K10, softmax temperature
0.1562, policy as scored in policy_score_v8.py, Decision/Risk from
step8_regate.py.

## Step 0 — Commit this brief alone. Record the hash.

## Step 1 — Holdout replication (never-touched matches)
Data: data/raw_holdout/ (Task 23 Step 4). Keep every holdout output in
separate `*_holdout` paths; never mix with study data.
(a) Run task24_evidence.py's checks on the holdout: share of
    team-periods with mean shot x > 60, opponent-keeper x in shot
    frames. (Confirms the same team-relative coordinates.)
(b) Score the holdout with the FROZEN engine v5 models — no retraining,
    no refitting, no recalibration of anything. Grid, EV, offside
    R1_K10, policy at T=0.1562, Decision, all as in Task 25.
(c) Run the outcome-validation battery on holdout team-matches with
    specifications unchanged, decision_z standardised within the
    holdout. Report every specification that can be computed and say
    which cannot (and why).
GATE, fixed since Task 23: xg H-O1 decision_z coefficient POSITIVE with
p < 0.05. If it fails, stop after Step 1 and report — no player
results until we understand why. Also report the holdout's
competitions, match count and n team-matches; note plainly that the
holdout is women's international football and the study sample is
mostly men's.

## Step 2 — Re-run tempo on corrected coordinates
`src/tempo/redesign_metrics.py` uses the old direction function
(Task 24 Step 1(c)). Route it to engine_v2's corrected
`team_period_directions` (+1 everywhere) and re-run MOVE_ON_SPEED and
HOLD_VARIATION with their preregistered specification unchanged.
Report reliability, the 0.70 bar verdict, and the move_on_speed /
hold_variation correlation, before (Task 16b) and after.

## Step 3 — Player-level threshold by reliability (fixed rule)
Decision's 100-split reliability at 100, 150, 200, 250, 300, 400, 500,
with units surviving at each. RULE: the threshold is the LOWEST at which
median reliability reaches 0.70. If none does, use 200 and mark every
player result PROVISIONAL with its reliability inline. Do not choose it
by looking at any ranking.

## Step 4 — Leaderboard
Players pooled across contexts at the Step 3 threshold, Decision per 100
eligible passes shrunk toward the mean at the measured reliability.
Report: qualifying count; top 20 and bottom 20 with name, position
group, competitions, eligible passes, raw and shrunken Decision; the
same as within-position-group z-scores; and a separate full table for
the DEEP / DEFENSIVE MIDFIELD position group only (every qualifying
player, ranked by within-group z).
Report the ranks of the plan v3 section 5 fixed list — Kroos, Modric,
Verratti, Busquets, De Bruyne, Xhaka, de Jong, Kimmich, Rodri, Pedri,
Gundogan, Grillitsch, Shaparenko — overall and within position group.
This list is output only and never a criterion.
Write the full ranking to data/processed/leaderboard_v5.parquet.

## Step 5 — How the dimensions relate
At the Step 3 threshold: correlation matrix among Decision, Risk,
move_on_speed, hold_variation, median_time_on_ball, completion rate,
progressive passes per 90, xA per 90 — overall AND within the deep /
defensive midfield group. Report pairs beyond |0.7|. (Task 25 found
Decision vs xA per 90 at r = +0.71 overall; report it within position.)

## Step 6 — Study B rebuilt: does decision quality travel?
As plan v2 section 4 and Amendments v2-5, v2-6.1 specify:
  - Stage 1: player x team-context means and SEs, >= 20 eligible passes.
  - Stage 2: crossed random effects for player and team context,
    weighted by stage-1 variance; fixed effects for zone shares and
    pressure share. Zones MUST use corrected coordinates: if any Study
    B code imports decision_engine's old pitch_direction, route it to
    engine_v2's corrected function and say so.
  - Interval: parametric bootstrap (the coverage-validated method), with
    the profile-likelihood interval alongside.
  - Gate E counts; secondary position-matched refit; mover correlation
    disattenuated per v2-5.3 PH-B2.
  - Apply the v2-5.4 claim tiers unchanged; report Tier 1 and Tier 2 as
    ALLOWED or NOT ALLOWED.
If Step 6 cannot finish cleanly, commit Steps 1-5 first and report
Step 6 as partial.

## HARD RULES
- No engine change, retraining, feature or threshold change, except
  Step 2's direction routing for tempo and Step 6's for Study B zones.
- Commit the results page after Step 5, then again after Step 6.
- The named-player ranks are output, never input. Report the
  leaderboard as computed, whoever is on it.
- Memory gate as in Task 25 before every corpus-scale step.
- No memory writes. Don't edit docs/JOURNAL.md. No interpretation.
- When finished, reply only that the task is done plus commit hashes.

## Output
docs/results/26-holdout-and-player-results.md (template).
