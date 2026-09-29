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

## AMENDMENT A (2026-09-29, before any run): tempo as CHOICES, and the "culmination" test
Added at the author's direction, before Task 52 has run. It extends
Steps 4-5; nothing above is removed. Same DEVELOPMENT half only; the
REPLICATION half stays locked.

The author's point: dictating tempo is about the CHOICES on the ball
(speed the play up with a forward, incisive pass; keep it; slow it
down and recycle; switch the point of attack), how often and WHEN a
player makes them, and whether his team's play actually speeds up or
slows down. The author's hypothesis: tempo is what press resistance
plus good timing look like to the eye (a "culmination").

### Pass categories (shared; fixed now)
Unit: eligible pass (the dataset's rule: study = engine rule; 2015/16 =
the frame-free rule of dff3e4e). dx = end x - start x (team frame).
  SWITCH = StatsBomb pass switch flag is true.
  ACCEL  = not SWITCH, and (pass technique is Through Ball, OR dx >= 15).
  SLOW   = not SWITCH, and dx <= -5.
  KEEP   = everything else.
Report the share of each, overall and for deep midfielders.

### M4 TEMPO PROFILE (style; 2015/16 dev leagues and study dev half)
For each category, a cross-fitted XGBoost classifier (Task 42 settings,
5 match folds within development, seed 20260929) of the category
indicator on Step 3's origin context (no identity, no team demeaning).
M4_ACCEL, M4_KEEP, M4_SLOW, M4_SWITCH = per-player mean(indicator -
p_oof). Needs >= 100 eligible passes. These describe style, not
quality.

### M5 TEMPO TIMING ("speeds up when it is on"; study dev half only)
Uses engine v5's full-corpus EV grid for development matches (in-sample
option values; disclosed) and the policy-restricted candidate set.
At each eligible pass, OPPORTUNITY = the best EV among ACCEL-type
candidates (candidate dx >= 15 from the ball) exceeds the best EV among
all other candidates.
Baseline: cross-fitted classifier of ACCEL on origin context WITHOUT
OPPORTUNITY. M5 = mean(ACCEL - p_oof | OPPORTUNITY) minus
mean(ACCEL - p_oof | no OPPORTUNITY). Higher = he accelerates when a
forward option is the best one, and holds when it is not. Needs >= 30
passes of each kind. Report the share of passes with OPPORTUNITY.

### M6 TEAM TEMPO SHIFT ("does the team speed up after him?"; 2015/16 dev and study dev)
Unit: eligible COMPLETED pass in open play. Using the team's on-ball
events in the same possession:
  V_before = (pass start x - x of the team's 3rd previous on-ball
             event) / seconds between them
  V_after  = (x of the team's 3rd on-ball event after the reception -
             pass end x) / seconds between them
Both windows must exist within the possession and be > 0 s. The
player's own pass is excluded from V_after by construction.
Baseline: cross-fitted regression of V_after on origin context plus
V_before. M6 = per-player mean(V_after - prediction). Also report M6
separately on his ACCEL and his SLOW passes. Needs >= 100 units.

### Tests for M4-M6 (report only, development half)
D1-D5 of Step 5 apply to M4_ACCEL, M4_SLOW, M4_SWITCH, M5 and M6
(M4_KEEP reported descriptively). For D3 the unit is the pass for
M4-M6. D5 declared direction: higher for M5; none for M4 and M6.

### Step 6 — The culmination test (deep midfielders, development half)
K1 Common core. Correlation matrix among PR2_flag_keep, W,
   v5 Decision (study only), M1, M2, M3_speed, M4_ACCEL, M4_SLOW, M5, M6,
   raw and DISATTENUATED (r / sqrt(rel_a x rel_b), reliabilities from
   D1 on the same half), with 1,000-player bootstrap CIs. Also the
   share of variance on the first principal component of
   {PR2_flag_keep, Decision, M4_ACCEL, M5} (study) and of
   {PR2_flag_keep, W, M4_ACCEL, M6} (2015/16).
K2 Adds beyond? The P-test on passes (Y_F3 and POSS_XG) with every
   player-level S attached to each of his passes (other-match means):
   each tempo measure (M1-M6) entered TOGETHER with PR2_flag_keep (and
   v5 Decision on the study sample). Report each tempo coefficient with
   and without the others, and PR2_flag_keep's with and without tempo.
Reading (for Task 53, report only here): "tempo is largely a
culmination" is supported if a tempo measure's disattenuated
correlations with PR2_flag_keep and/or Decision are large AND its K2
coefficient shrinks toward zero once they are entered; "tempo is its
own trait" if it keeps its coefficient.
No composite score is built in this task.
