# Task 23 — Why does scenario_c fail? Diagnostics only, no model changes

Written 2026-09-27 by the research lead. The author has chosen to keep
working on the engine past Task 22's "no Task 22b" stop rule. That
choice is disclosed here and must be disclosed in any abstract or paper:
the engine has now failed its acceptance battery or a premise check
three times (19d, 21, 22) and any later acceptance is post hoc.

Two things change because of that, decided now, before any result:
1. This task changes NOTHING in the engine. It only measures. Every fix
   so far assumed the value model was the problem; nobody has taken the
   failing scenario apart to check.
2. Any engine accepted after this point must ALSO replicate on matches
   it has never touched (Step 4) before a single player claim is made.

## Step 0 — Commit this brief alone. Record the hash.

## Step 1 (D1) — Take scenario_c apart
Using `test_t4_synthetic.py`'s own frames and Task 19d's models
(`value_model_for_v2.json`, `value_model_against_v2.json`, the current
pass-success model), for ALL THREE scenarios print: p_success,
V_net_success, V_net_turnover, EV, and every STATE_FEATURES value of the
success state and the turnover state.
For scenario_c, also report where each of p_success, V_net_success,
V_net_turnover and EV falls as a PERCENTILE of the same quantity across
the Task 19d corpus (`options_ev_v2`), using a fixed sample: 50,000 rows
from each of 30 matches chosen with seed 20260927 from ALL match files
(not the first 30 alphabetically — note that the committed test uses the
first 30; report both p90 values).
Also report how unusual scenario_c's frame is for the value model:
the distribution of `n_visible_players` in the value-model training rows
(`value_model_rows_v2.parquet`), the share of training rows with 6 or
fewer visible players, and whether the synthetic frame contains a
goalkeeper (it lists 4 opponents at x=70 and 1 teammate).

## Step 2 (D2) — Is a ball behind the defence dangerous IN THE MIDDLE?
From `value_model_rows_diagnostic_v4.parquet`, in-possession rows only,
new labels (Task 22's corrected rows). Split by band (80-100, 100-120) x
channel (CENTRAL = |ball_y - 40| <= 10, WIDE = everything else) x beyond
line (yes/no). Report n, P(score in 10), P(concede in 10) per cell, and
the same split with play_pattern "From Corner" / "From Free Kick" /
"From Throw In" rows removed as a sensitivity. Nothing is gated here.
Commit the script.

## Step 3 (D3) — What is in the top decile?
From the Task 19d corpus sample in Step 1, describe the options with EV
at or above p90: distribution of destination band (normalised x),
channel (as above), pass distance, p_success, and share that are exact
teammate positions. Compare with the full sample. No interpretation.

## Step 4 — Prepare the untouched holdout (download and ingest only)
Using the existing ingestion code, pull StatsBomb events and 360 frames
for the 360-covered competition-seasons NOT in the study sample
(Women's Euro 2022, Women's World Cup 2023, Women's Euro 2025; the data
audit lists them). Write them to a SEPARATE directory
(`data/raw_holdout/`), never into `data/raw/`. Report match counts and
frame coverage. Run NO model, feature or outcome code on them.

## HARD RULES
- No changes to any engine file, model, feature, threshold or test.
- No retraining. No new EV corpus.
- Holdout data is downloaded and counted, nothing else.
- No leaderboards, no player identity, no interpretation.
- No memory writes. Don't edit docs/JOURNAL.md.
- When finished, reply only that the task is done plus commit hashes.

## Output
docs/results/23-scenario-c-diagnostics.md (template). Commit per rule 9.

---

## Research lead's decision rules (written before Task 23 runs; the
## next task is chosen by these, not by what looks promising)
R1. If scenario_c's V_net_success is at or above the corpus p90 of
    V_net_success but its EV is not, the value model is doing its job
    and the shortfall is p_success or the EV formula. The next task
    targets that, not the value model.
R2. If D2 shows CENTRAL beyond-line scoring higher than central
    not-beyond in BOTH bands, but scenario_c's V_net_success is below
    p90, the model is failing to learn a pattern the data contains.
    One fix attempt on the value model is allowed.
R3. If D2 shows central beyond-line NOT scoring higher in either band,
    this data does not support scenario_c's football premise. The
    engine cannot pass its battery as written. Engine work stops for
    Oct 1. The test is NOT rewritten.
R4. If the synthetic frame is far outside the training data (no
    goalkeeper, and 6-or-fewer-visible frames under 1% of training
    rows), that is reported as a flaw in the test itself and recorded
    for the paper. Whether T4 is amended is a separate, disclosed
    decision, and an amended test can only count if the engine ALSO
    passes the holdout replication.
Holdout gate for any accepted engine: the cross-fitted team-match xG
result (H-O1) must have the same sign and p < 0.05 on the holdout. If
not, no player claim, regardless of the battery.
Hard stop: if no engine has passed the battery AND the holdout by
Tuesday Sep 29, 9:00 am Pacific, engine work stops for SSAC27.
