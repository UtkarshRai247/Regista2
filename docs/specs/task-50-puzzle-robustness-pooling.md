# Task 50 — Freeze v8, then three checks that decide what we can say

Written 2026-09-29 by the research lead, before any result. Report only:
every dataset here has been used before, so nothing in this task can be
called confirmed. Label every table with its dataset and which use it
is (2015/16: further use after Tasks 44-47; reserved: second use after
Task 48; study: as usual). Holdout untouched.

Task 49 (written in another chat) is WITHDRAWN and must not be run.

## Step 0 — The research lead commits this brief alone; record that hash.

## Step 1 — Freeze BENCHMARK v8
`docs/BENCHMARK-v8.md` and the Task 49 withdrawal note are already
committed by the research lead; record that hash. Snapshot, unmodified, into `data/benchmark_v8/` (not committed)
the summary JSONs and per-unit tables behind results 44-48 (including
Task 44's 2015/16 reception/spell table, Task 46's W tables, Task 48's
built measures). Record path, size and SHA-256 in
`docs/benchmark/manifest-v8.txt` (committed). Tag `benchmark-v8`,
message "Benchmark v8 — see docs/BENCHMARK-v8.md". Do not push.
Spot-check from the snapshot only: Task 48 C6 coefficient (+1.281) and
C4 r_true (+0.650).

## Step 2 — The "fewer chances" puzzle
Why does keeping the ball under pressure go with reaching the final
third but with LOWER net xG over the next 10 events? One suspected
reason is mechanical: a player who keeps the ball recycles it, so the
possession takes more events and a later shot falls outside the
10-event window.
Design: Task 44's P-test (unit = pressured reception; S =
other-match PR2_flag_keep, >= 50 elsewhere; event-only g refit per
outcome; role FE; team-match FE; SE by player; retention control), run
separately on 2015/16 and on the reserved data, for all players and
for deep midfielders (each dataset's own DM rule). Also with S = the
A1 (team-demeaned) score. Outcomes:
  (a) XG_FOR_10: the team's own shot xG in events i+1 ... i+10
  (b) XG_AGAINST_10: the opponent's shot xG in events i+1 ... i+10
  (c) NET_XG_20 and NET_XG_30: net xG with 20- and 30-event windows
  (d) POSS_XG: the team's shot xG later in the SAME possession, no
      event window
  (e) POSS_LEN: the number of the team's events remaining in the
      possession after the unit
  (f) NEXT_AGAINST: the opponent's shot xG in the opponent's NEXT
      possession
Reading rule (fixed now, report only): if (a) and (d) are >= 0 while
the net-xG-10 result is negative, the negative link is described as a
window or composition effect; if (a) and (d) are negative, the paper
says keeping the ball under pressure goes with fewer chances for the
team, as found.

## Step 3 — How solid are the two confirmed press-resistance results?
Reserved data, second use, report only. Repeat Task 48 C4 and C6
exactly, on these subsets:
  - men's matches only; women's matches only;
  - club matches only; national-team matches only (C6 only);
  - excluding every match involving Barcelona;
  - excluding Sergio Busquets and Keira Walsh (the two largest DM
    samples).
Report n, estimate, CI, p for each. No correction; no claim.

## Step 4 — All the deep-midfield evidence together
The pre-registered DM tests were small and did not confirm. Pool the
independent samples to show the overall picture:
  (i) PR2_flag_keep -> Y_F3 within DMs: study sample (compute with
      Task 44 Step 2's event-only measure on the study sample, Task 44
      P-test design, study DM group of 111), 2015/16 (Task 44 P2), and
      reserved (Task 48 C1).
  (ii) W -> Y_F3 within DMs: study sample (Task 46's study W), 2015/16
      (Task 46 B3), reserved (Task 48 C2).
For each: the per-sample estimates and SEs, the inverse-variance fixed-
effect pooled estimate with 95% CI, the DerSimonian-Laird random-effects
estimate, and I^2. State in the table caption that the pre-registered
confirmation (Task 48 C1/C2) did not confirm and that this pooling was
decided after seeing it.

## HARD RULES
- No new measure definitions; only the outcomes and subsets above.
- No change to earlier artifacts. Holdout untouched. Do not run Task 49.
- Memory gate as in Task 25. Commit the page after Step 2, then at end.
- No memory writes. Don't edit docs/JOURNAL.md. No interpretation.
- When finished, reply only that the task is done plus commit hashes.

## Output
docs/results/50-puzzle-robustness-pooling.md (template). Commit per rule 9.
