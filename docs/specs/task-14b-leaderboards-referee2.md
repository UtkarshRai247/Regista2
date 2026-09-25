# Task 14b — Leaderboards and Referee 2

Governing document: docs/specs/analysis-plan-v3.md, Amendments v3-1 to
v3-5. Read plan sections 4 and 5, and Amendment v3-5, carefully.

## Step 0 — Fix the expert lists, then commit
Replace the Bundesliga 2023/24 rows in data/expert_lists/selections.csv
with the VDV XI listed in Amendment v3-5.2, using the source_org "VDV"
and the URL given there, publication_date 2024-09-10.
Leave every other row untouched. Commit Amendment v3-5 and the corrected
CSV together. Record the hash and the plan's new SHA-256.

## Step 1 — The three leaderboards
For O1, O2 and O3: players pooled across all contexts with >= 200
eligible passes, Decision shrunk toward the mean at reliability 0.744
(the same construction as Task 12, unchanged).
Report, for each objective: the number of qualifying players, and the
top 20 and bottom 20 with name, position group, competitions, total
eligible passes, raw Decision per 100 and shrunken Decision per 100.
Write the FULL ranking for all three to
data/processed/leaderboards_o1_o2_o3.parquet.
Also report the rank of each player on the plan v3 section 5 fixed
list — Kroos, Modric, Verratti, Busquets, De Bruyne, Xhaka, de Jong,
Kimmich, Rodri, Pedri, Gundogan, Grillitsch, Shaparenko — under all
three objectives, in one table, with their pass counts.
Report Spearman rank correlations between the three leaderboards.

## Step 2 — Referee 2 power FIRST (Amendment v3-4.2)
Match the expert lists to our qualifying player-competition-season
units by normalised name plus competition-season. Report: units
qualifying, units matched to a selection, and every selected player who
could NOT be matched, with the reason (did not reach 200 passes,
goalkeeper, name mismatch).
Then report the minimum AUC improvement over the team-strength baseline
detectable at 80% power given those counts. If it exceeds 0.10,
declare Referee 2 UNDERPOWERED and say so before reporting any AUC.

## Step 3 — Referee 2
Team-strength baseline: the team's final league position, or the
tournament round it reached, for that competition-season.
Model (i): selection ~ team strength. Model (ii): selection ~ team
strength + Decision_obj. Compare AUC, with a bootstrap CI on the
difference (1,000 draws, clustered by competition-season).
Report for each objective, plus the v3-5.4 sensitivity excluding the
World Cup 2022 rows.
Apply plan section 4: an objective PASSES only if the AUC improvement's
CI excludes zero. Report PASS / FAIL per objective, and restate the
Referee 1 verdicts (all NOT WIN) alongside.

## Step 4 — Apply plan section 5
State which objective, if any, may be described as BETTER. Given all
three failed Referee 1, the expected answer is NONE; report that
plainly rather than softening it.

## HARD RULES
- No changes to the claim rules, the fixed player list, or the
  thresholds.
- Report all three objectives fully; no filtering or sorting tricks.
- The leaderboard is reported as computed, whoever is on it.
- No interpretation for the paper. No memory writes. Don't edit
  docs/JOURNAL.md.
- When finished, reply only that the task is done plus commit hashes.

## Output
docs/results/14b-leaderboards-referee2.md (template). Commit per rule 9.
