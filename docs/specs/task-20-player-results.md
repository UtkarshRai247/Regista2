# Task 20 — The football results: threshold, Study B, leaderboard

Engine v2 is final (Tasks 15, 17, 18, 19). This task produces the
player-level results. No engine change of any kind.

## Step 0 — Commit this brief. Record hash.

## Step 1 — Choose the player-level threshold by reliability (fixed rule)
Report Decision's 100-split reliability curve at 100, 150, 200, 250,
300, 400, 500 with units surviving at each.
RULE, fixed now: the player-level threshold is the LOWEST threshold at
which median reliability reaches 0.70, matching the bar used for the
tempo module. If no threshold reaches 0.70, use 200 and report every
player-level result as PROVISIONAL with its reliability inline.
Apply that threshold everywhere below. Do not choose it by looking at
any ranking.

## Step 2 — Study B rebuilt: does decision quality travel?
The original Study B (Task 07/08) is withdrawn with engine v1. Rebuild
it exactly as plan v2 section 4 and Amendments v2-5, v2-6.1 specify:
  - Stage 1: player x team-context means and standard errors, at least
    20 eligible passes per unit.
  - Stage 2: crossed random effects for player and team context,
    weighted by stage-1 sampling variance, fixed effects for zone shares
    and pressure share.
  - Interval: the PARAMETRIC BOOTSTRAP, which was the coverage-validated
    method (93% coverage; the cluster bootstrap covered 10%). Report the
    profile-likelihood interval alongside.
  - Gate E: report players with 2+ contexts, club-plus-international
    movers, and movers with the same position group.
  - Secondary: position-matched refit; mover correlation, disattenuated
    per v2-5.3 PH-B2.
Apply the v2-5.4 claim tiers unchanged and report Tier 1 and Tier 2 as
ALLOWED or NOT ALLOWED.

## Step 3 — The leaderboard
Players pooled across contexts at the Step 1 threshold. Shrink Decision
toward the mean at the measured reliability from Step 1.
Report: qualifying player count; top 20 and bottom 20 with name,
position group, competitions, eligible passes, raw and shrunken Decision
per 100; and the same as within-position-group z-scores.
Report the ranks of the plan v3 section 5 fixed list — Kroos, Modric,
Verratti, Busquets, De Bruyne, Xhaka, de Jong, Kimmich, Rodri, Pedri,
Gundogan, Grillitsch, Shaparenko — under engine v2, beside their engine
v1 ranks from Task 14b. This is reported for the reader and is NOT a
criterion; nothing may be tuned on it.
Write the full ranking to data/processed/leaderboard_v2.parquet.

## Step 4 — How the dimensions relate
Correlation matrix, at the Step 1 threshold, among: Decision,
Execution, Risk, move_on_speed, hold_variation, median_time_on_ball,
completion rate, progressive passes per 90, xA per 90.
Report which pairs exceed |0.7|.

## HARD RULES
- No engine change, no retraining, no feature change, no threshold
  change beyond Step 1's fixed rule.
- The named-player ranks are output, never an input.
- Report the leaderboard as computed, whoever is on it.
- No memory writes. Don't edit docs/JOURNAL.md. No interpretation.
- When finished, reply only that the task is done plus commit hashes.

## Output
docs/results/20-player-results.md (template). Commit per rule 9.
