# Task 04 — Freeze the new plan, join situation context, prepare Studies A-C

Governing document: docs/specs/analysis-plan-v2.md. Read it fully first.
This task PREPARES data. It computes no Study A, B or C result.

## Step 0 — Freeze the preregistration
Commit docs/specs/analysis-plan-v2.md and this file. Record the commit
hash and the SHA-256 of analysis-plan-v2.md in the results page.
Append D-012, D-013 and D-014 (text below) to docs/DECISIONS.md.
Do NOT edit docs/JOURNAL.md — the research lead maintains it.

## Step 1 — Situation context for every pass (171,618 expected)
Join from the StatsBomb events, using event_id:
- under_pressure (true/false; missing means false — confirm how
  statsbombpy represents it and report)
- period, minute, second
- score difference for the passing team at the moment of the pass,
  counting every goal event before it (own goals and penalties included;
  shootouts excluded). VALIDATE: the reconstructed final score must
  equal the recorded final score for every one of the 299 matches.
  Report any mismatch by match_id and STOP if any exist.
- play_pattern
- passer zone (thirds, and channel as a secondary field) from the
  NORMALIZED coordinates via src/decision_engine/pitch_direction.py
- total visible players in the pass's freeze frame
- team context label = team x competition-season
Report the pass count and state explicitly if it is not 171,618.

## Step 2 — Option typing
- First confirm the unit of the distance column (StatsBomb units or
  meters) and report the evidence. Convert 15m and 30m accordingly and
  report the converted thresholds.
- Type every option by direction (forward / lateral / backward, using
  normalized coordinates and the 45 / 135 degree rules) and length
  (short / medium / long). Also type the chosen option of every pass.
- Sanity check: report the share of options in each of the 9 types.

## Step 3 — Discovery / confirmation split
Split the 299 matches 50/50, stratified by competition-season, seed
20260920. Save to data/splits/match_split.csv (match_id, competition_id,
season_id, half). Commit this file to git — it is derived and small, not
raw data. Report the per-competition counts in each half.

## Step 4 — Feasibility counts (COUNTS ONLY)
Using the DISCOVERY half only:
- passes per situation cell (18 cells)
- for each (cell, option type): times the type was available, and times
  it was chosen. Flag every pair with >= 100 chosen (analyzable under
  plan section 3.2). Report how many of the 162 pairs are analyzable.
Using the full sample:
- Study B: players by number of team contexts at the 20-pass floor;
  number with 2+ contexts; number who are club-plus-international
  movers; number of movers with the same position group in both.
- Club competition structure: for each competition-season, number of
  distinct teams, matches per team, and whether it is built around one
  focal team (and which).
- Distribution of visible players per frame; the median (this defines
  "high visibility" for sensitivity check 3.6b).

## HARD RULES
- Do NOT compute or look at EV, g_k, Decision, Execution, realized
  value, or any value quantity by cell, option type, team context,
  competition or player. Counts only. This is what keeps the
  preregistration clean.
- Do NOT touch the confirmation half beyond counting passes per
  competition in the split.
- Do NOT retrain or modify any model.
- If any definition in the plan cannot be implemented as written, STOP
  and ask in Section 6. Do not improvise.

## Decisions to append to docs/DECISIONS.md

## D-012 — Research question pivot
Date: 2026-09-20
Decision: The headline moves from market pricing to decision-making
itself: Study A (sport-wide blind spots), Study B (player vs system),
Study C (choice vs execution). The market test becomes a scoping note.
Reason: The market test was powered only for ~22% effects per SD (n=125
player-seasons). The original research question was about measuring
registas, not their market price. The new studies use pass-level data
where sample size is not the binding constraint.
Alternatives rejected: More market work; women's replication (cut for
time); lowering the pass threshold (buys power with noise).
Reversible? No, not before Oct 1.

## D-013 — Preregistration v2
Date: 2026-09-20
Decision: docs/specs/analysis-plan-v2.md governs all new analysis. It
was written before any situation-level data was joined.
Reversible? Only by dated amendment.

## D-014 — Discovery / confirmation split
Date: 2026-09-20
Decision: Study A is run on a match-level 50/50 split, seed 20260920,
committed before any Study A statistic exists.
Reversible? No.

## Output
docs/results/04-situation-context.md following the template, plus:
data/processed/passes_situation.parquet, data/processed/options_typed.parquet
(gitignored), data/splits/match_split.csv (committed).
