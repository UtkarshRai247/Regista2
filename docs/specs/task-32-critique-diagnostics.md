# Task 32 — Measurement only: test CRITIQUE-v5's problems A1-A5 and B1

Written 2026-09-28 by the research lead. Nothing in the engine changes.
Every number is reported beside BENCHMARK-v5.md. The women's holdout
(`data/raw_holdout/` and all `*_holdout` outputs) is NOT touched.

Inputs (all existing): per-pass cross-fitted Decision
`pass_der_crossfit_v5.parquet`; full-corpus per-pass
`pass_der_v8.parquet` and `pass_policy_summary_v8.parquet`; the full
EV corpus used by policy_score_v8.py; raw events; Task 27's
`task27_dm_share.parquet`; the outcome-validation code in
`outcome_validation_crossfit_v5.py` / `outcome_validation.py`.

State the exact match count behind every analysis (the corpus has 299
matches in the data audit but 292 in the cross-fit summary; say which
and why).

## Step 0 — Commit this brief alone. Record the hash.

## Step 1 (A2) — Is the "typical choice" baseline unbiased?
Using the cross-fitted per-pass values:
(a) Mean Decision overall, and the share of the 537 qualifying players
    with a positive mean.
(b) Mean Decision, mean ev_chosen and mean policy_weighted_ev by:
    passer zone (normalised x: 0-40, 40-80, 80-120), pass length
    (0-10, 10-20, 20-30, 30+ yards), and pass outcome (complete /
    incomplete).
(c) Calibration: bin passes by decile of policy_weighted_ev; per bin,
    mean policy_weighted_ev vs mean ev_chosen.
(d) Share of passes whose chosen option falls OUTSIDE the policy's
    restricted candidate set (p_success / distance restriction), and
    mean Decision for those vs the rest.
(e) Policy top-1 and top-3 accuracy on v5 (from the cross-fit summary).

## Step 2 (A3) — How much of Decision is execution?
(a) Share of eligible passes that are incomplete; mean Decision
    complete vs incomplete; share of total between-player variance in
    mean Decision contributed by incomplete passes.
(b) Player Decision recomputed on COMPLETED passes only (same
    shrinkage method as Task 28 overall and Task 29 deep midfield).
    Spearman vs the all-passes version for the 537 and the 111.
(c) For incomplete passes: distance from pass end location to the
    nearest visible teammate in the frame, and to the nearest visible
    teammate within 15 degrees of the pass line. Report distributions
    (median, quartiles). This informs a later fix; no fix here.

## Step 3 (A4) — In-sample vs cross-fitted player tables
Rebuild Task 28's overall table and Task 29's deep-midfield table from
the CROSS-FITTED per-pass Decision, same methods. Report: per-pass
correlation between the two Decision versions; Spearman between the
tables (overall, deep midfield); overlap of the overall top 20; the
deep-midfield count of intervals entirely above / below the mean, with
names. (Decided now: cross-fitted tables become the standard from here
on, whatever this shows.)

## Step 4 (A5) — Is Decision stable WITHIN a role?
Assign each qualifying player a role by the share of his eligible
passes at each StatsBomb position (>= 50% in one group, else MIXED):
  CB: Center Back, Left Center Back, Right Center Back
  FB: Left Back, Right Back, Left Wing Back, Right Wing Back
  DM: Center, Left, Right Defensive Midfield
  CM: Center Midfield, Left Center Midfield, Right Center Midfield
  AM/W: Center, Left, Right Attacking Midfield; Left Midfield,
        Right Midfield; Left Wing, Right Wing
  FW: Center Forward, Left Center Forward, Right Center Forward,
      Secondary Striker
(Goalkeepers excluded.) Report counts per role.
(a) T6's reliability function (same units, same method as
    step8_regate.py) run WITHIN each role at 100, 200, 300, 500 passes,
    with units per threshold, beside the all-roles value (0.8191 at
    200).
(b) The share of between-player variance in mean Decision explained by
    role (one-way, weighted by passes).
(c) Study B's PH-B1 refit with these roles as the fixed effects instead
    of the coarse position groups. If this cannot finish within 45
    minutes of compute, skip it and say so.

## Step 5 (A1) — Does Decision predict matches it was not measured in?
Using cross-fitted per-pass Decision, for every team-match unit:
(i) LINEUP version: each pass's passer contributes his mean Decision
    from his OTHER matches (only passers with >= 50 eligible passes
    elsewhere); the unit's score is the pass-weighted mean over the
    match. Keep units where >= 70% of passes are covered; report the
    count kept.
(ii) TEAM version: the team-context's mean Decision over its OTHER
    matches.
Standardise each, then fit xG and goals with the H-O1 specification
(possession share, home, competition-season FE), and for (i) ALSO the
PH-O2 specification (team-context FE, the within-team test). Report
coefficient, SE, p and n beside the same-match v5 values. No outcome
threshold is set; this is reported as measured.

## Step 6 (B1) — Does the typical-choice model earn its place?
All IN-SAMPLE (full-corpus) for a like-for-like comparison, labelled as
such. Per pass: (b1) ev_chosen alone; (b2) ev_chosen minus the mean EV
of ALL candidates for that pass (uniform baseline, from the EV corpus);
(b3) Decision (ev_chosen - policy_weighted_ev). Team-match means,
standardised. For xG and goals under H-O1 and PH-O2: each alone
(coefficient, p, R^2), then b3 together with b1, and b3 together with
b2. Also, within the 111 deep midfielders, correlations among the three
player-level versions.

## Decision rules for choosing fixes (fixed now, before Steps 1-6 run)
- A3 fix (infer the intended target for incomplete passes) is
  prioritised if EITHER Step 2(b)'s deep-midfield Spearman < 0.80 OR
  incomplete passes contribute > 30% of between-player variance.
- A2 fix (recalibrate the typical-choice baseline) is prioritised if
  Step 1(c) shows ev_chosen exceeding policy_weighted_ev in 8 or more of
  10 deciles AND the zone means in Step 1(b) differ from each other by
  more than the overall mean Decision.
- At most two fixes go forward. If both qualify, both; if neither, no
  engine fix, and the remaining days go to controls, sensitivity and
  presentation.
- A1, A5 and B1 do not trigger engine fixes; they decide what the paper
  may claim.

## HARD RULES
- No engine change, retraining or new EV corpus.
- Holdout untouched.
- Memory gate as in Task 25 before any corpus-scale read.
- Commit the results page after Steps 1-3, then again at the end.
- No memory writes. Don't edit docs/JOURNAL.md. No interpretation.
- When finished, reply only that the task is done plus commit hashes.

## Output
docs/results/32-critique-diagnostics.md (template). Commit per rule 9.
