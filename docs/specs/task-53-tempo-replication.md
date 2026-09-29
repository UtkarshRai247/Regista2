# Task 53 — Tempo replication on the locked half (2015/16 La Liga, Serie A, Ligue 1), and a praised-list name audit

Written 2026-09-29 by the research lead after reading
docs/results/52-tempo-development.md, BEFORE any replication row has
been opened. This is the ONLY use of the replication half. Holdout and
reserved data untouched.

## Answers to Task 52's questions
1. M6 is dropped from this replication: its baseline R^2 is negative and
   near-zero time gaps dominate it. A fixed version may come later.
2. Step 3's T equalling the existing time on ball is fine; what is new is
   g_T without team demeaning and the measures built on r.
3. M2 stays exactly as run in Task 52 (FK = 0 for spells not ending in a
   completed pass within 1.5 s). Report the "drop excluded spells"
   version as a sensitivity only.
4. Distance to goal centre is fine. M1 is not replicated (see below).
5. Yes. 6. Yes. 9. Yes (completion for pass units). 10. Yes.
7. The study replication half is too small for deep-midfielder tests
   (15-16 DMs met the key floors in development). No study-sample gate is
   set; study replication rows are NOT opened in this task.
8. Disattenuate only when both reliabilities are >= 0.30; never clip;
   always report the raw r.
M1 (tempo intelligence) and M5 (tempo timing) are not replicated: both
need 360 frames, and within deep midfielders they were not stable on
the study development half (-0.015, 0.038).

## Step 0 — The research lead commits this brief alone; record the hash.

## Step 1 — Praised-list name audit (before opening replication rows)
Task 52 matched "de Jong" to Siem de Jong. Build the praised list by
StatsBomb player_id, not by name: for each of Kroos, Modric, Verratti,
Busquets, De Bruyne, Xhaka, Frenkie de Jong, Kimmich, Rodri (Rodrigo
Hernandez Cascante), Pedri, Gundogan, Grillitsch, Shaparenko, list
every player_id in ALL datasets used (study, holdout, PFF map, 2015/16,
reserved) whose name could match, and keep only the intended player.
Commit the ID list as docs/splits/praised_ids.csv. Then re-check
which players each earlier praised-list test (Tasks 41, 42, 43, 44, 45,
48, 52) actually included, and report any wrong matches (for example
Siem or Luuk de Jong, or another "Rodri"). Do NOT re-run those tests;
only report the audit. Every praised-list test from here uses the ID
list.

## Step 2 — Build the measures on the REPLICATION leagues
2015/16 La Liga (11, 27), Serie A (12, 27), Ligue 1 (7, 27), from raw
per-match events. Definitions exactly as Task 52 (Step 3, M2, M3,
Amendment A's categories and M4), with every baseline refit on
replication-league folds only (5 match folds, seed 20260929).
Deep midfielders: Task 44's rule within the replication leagues. Report
n (players, DMs, matches). Existing comparators (PR2_flag_keep, W) read
from existing tables with a replication-league filter, as Clarification
B allowed.

## Step 3 — The pre-registered replication family (fixed now)
STABILITY (each its own claim; Task 38's method, >= 10 matches, DMs):
  S1 M4_ACCEL, S2 M4_SLOW, S3 M4_SWITCH, S4 M3_speed, S5 M2.
  PASS each if median >= 0.60.
RESULTS (Task 44 P-test design; passes for M4, receptions for M2/M3;
role FE; team-match FE; SE by player; completion control for passes,
retention for receptions). Holm across R1-R7 together:
  R1 DM:  M4_SWITCH -> Y_F3, entered with PR2_flag_keep; coef > 0.
  R2 DM:  M3_speed -> Y_F3; coef < 0 (faster than typical goes with
          LESS progression in development).
  R3 DM:  M2 -> POSS_XG; coef > 0.
  R4 ALL: M4_ACCEL -> Y_F3; coef > 0.
  R5 ALL: M4_SLOW -> Y_F3; coef < 0.
  R6 ALL: M4_SWITCH -> Y_F3; coef > 0.
  R7 ALL: M2 -> Y_F3; coef > 0.
  CONFIRMED (each): Holm p < 0.05, the stated sign, and the control on
  the same rows positive with p < 0.05.
CULMINATION (DMs; 1,000-player bootstrap):
  C1 corr(M4_ACCEL, PR2_flag_keep) < 0, 95% CI excluding 0.
  C2 corr(M2, PR2_flag_keep) > 0, 95% CI excluding 0.
  Also report K1's full matrix and the PC1 share for
  {PR2_flag_keep, W, M4_ACCEL, M2}.

## Step 4 — Report only
- Every D3 cell of Task 52 for these measures (all/DM x Y_F3/POSS_XG).
- K2 for each measure with PR2_flag_keep.
- Praised list by ID (direction higher for M2; none for the rest).
- Deep-midfield tables (Task 29's method) for every measure that passes
  its stability claim, with the named-player rows by ID.

## HARD RULES
- Single use of the replication half. Nothing beyond what is listed.
- No change to Task 52's definitions (other than the ID-based praised
  list). Study replication rows NOT opened. Holdout and reserved
  untouched.
- Memory gate as in Task 25. Commit after Step 1, again at the end.
- No memory writes. Don't edit docs/JOURNAL.md. No interpretation.
- When finished, reply only that the task is done plus commit hashes.

## Output
docs/results/53-tempo-replication.md (template). Commit per rule 9.
