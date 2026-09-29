# Task 52 — Freeze v9, lock a development/replication split, and develop three new tempo measures

Written 2026-09-29 by the research lead, before any result and before
any split exists. Holdout and reserved data untouched (both spent).

## Why
The eye test says registas "dictate the tempo". Our tempo measures
(MOVE_ON_SPEED, HOLD_VARIATION) measure speed, not control; they remove
each team's average in the match, which may strip out the regista's
influence on his team's rhythm; and MOVE_ON_SPEED is not stable within
deep midfielders (0.475, 2015/16). This task develops three measures on
a DEVELOPMENT half only. The REPLICATION half is locked and may not be
read until Task 53, written after this task's results.

## Step 0 — The research lead commits this brief alone; record the hash.

## Step 1 — Freeze BENCHMARK v9
`docs/BENCHMARK-v9.md` is committed by the research lead with this
brief. Snapshot into `data/benchmark_v9/` (not committed) the Task 50
and Task 51 JSONs and per-unit tables, including the scorecard parquets
and the regenerated W tables (write them to disk now if they only exist
in memory). Manifest `docs/benchmark/manifest-v9.txt` (path, size,
SHA-256; committed). Tag `benchmark-v9`. Do not push.

## Step 2 — Lock the split (before any tempo computation)
2015/16: DEVELOPMENT = Premier League (2, 27) and Bundesliga (9, 27);
         REPLICATION = La Liga (11, 27), Serie A (12, 27), Ligue 1 (7, 27).
Study sample (292 matches): within each competition-season, sort match
ids, permute with numpy default_rng(20260929), first floor(n/2) =
DEVELOPMENT, rest = REPLICATION.
Write the lists to `docs/splits/tempo_split.csv` (competition_id,
season_id, match_id, half) and commit it BEFORE Step 3. From here on,
no code in this task may load events, frames or any derived table rows
for REPLICATION matches.

## Step 3 — Time on ball (shared definition)
For each completed Ball Receipt* (receiver = actor): T = seconds from
the receipt's timestamp to the receiver's next Pass in the same
possession, provided no other player has an on-ball event in between.
Spells ending in a shot, a loss, a foul or a period end are excluded.
Keep 0 < T <= 15 s. Report n and the distribution, and compare with the
existing tempo module's time-on-ball on the same development rows
(correlation).
Baseline g_T: cross-fitted XGBoost regression of log T (5 match folds
within development, seed 20260929; Task 35's hyperparameters) on
context the player does not control: reception x, y; play pattern;
under_pressure; period; minute; score difference; and, for the study
sample only, the number of visible opponents within 10 units.
NO team, team-match or player identity; NO team demeaning.
r = log T - g_T_oof (negative = faster than typical for the situation).

## Step 4 — The three measures (fixed now)
M1 TEMPO INTELLIGENCE (study sample only; needs 360 frames).
  OPENING at a reception, from its freeze frame: some visible teammate
  (not the receiver) is >= 10 units nearer the opponent goal than the
  receiver, has no visible opponent within 5 units, and has no visible
  opponent within 2 units of the straight line from the receiver to
  him. TI = mean r on receptions WITHOUT an opening minus mean r on
  receptions WITH one (higher = holds when there is nothing on,
  releases quickly when there is). Needs >= 30 receptions of each kind.
  Report the share of receptions with an OPENING.
M2 QUICK AND SAFE UNDER PRESSURE (2015/16 and study).
  Unit: pressured completed reception (Task 44's flag rule). FK = 1 if
  the spell ends with his COMPLETED pass released within 1.5 s (T <=
  1.5); else 0 (including slow completions and losses). Baseline:
  cross-fitted XGBoost classifier (Task 42's settings) on the Step 3
  context. M2 = mean(FK - p_oof). Needs >= 50 pressured receptions.
  Report only: the same with 1.0 s and 2.0 s.
M3 RELEASE SPEED, NOT TEAM-DEMEANED (2015/16 and study).
  M3_speed = -(mean r) (higher = faster). M3_var = SD of r.
  Needs >= 100 timed receptions.

## Step 5 — Tests on the DEVELOPMENT half (report only)
Deep midfielders: 2015/16 = Task 44's rule applied within the
development leagues; study = Task 27's 111 restricted to development
matches. Report n for each.
D1 Stability: Task 38's method (random halves of a player's MATCHES),
   players >= 10 matches (2015/16) / >= 4 (study); DMs and all.
D2 Travels (M2, M3 only): players with a 2015/16 development-league club
   context and a study-development national-team context (>= 50
   pressured receptions for M2, >= 100 timed receptions for M3 each);
   Task 46 A-ii's disattenuated correlation and bootstrap. Also Task 46
   A-i's club vs country within study development matches if >= 15
   movers qualify.
D3 Results: Task 44's P-test design (unit = completed reception; S =
   other-match measure; event-only g for 2015/16, Task 42's reception g
   for study; role FE; team-match FE; SE by player; retention control),
   outcomes Y_F3 and POSS_XG (Task 50's definition), DMs and all.
D4 Distinctness: within DMs, correlations of each measure with
   PR2_flag_keep, W, MOVE_ON_SPEED, HOLD_VARIATION.
D5 Praised list (Task 41's list and method): report T and p; declared
   direction higher for M1 and M2, none for M3.
Nothing here is gated; the gates for Task 53's replication will be
written after this page is read and before REPLICATION rows are opened.

## HARD RULES
- Never load REPLICATION rows. Holdout and reserved untouched.
- No change to earlier definitions or artifacts.
- Memory gate as in Task 25. Commit after Step 2 (the split), again at
  the end.
- No memory writes. Don't edit docs/JOURNAL.md. No interpretation.
- When finished, reply only that the task is done plus commit hashes.

## Output
docs/results/52-tempo-development.md (template). Commit per rule 9.
