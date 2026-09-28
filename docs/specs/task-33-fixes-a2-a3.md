# Task 33 — The two triggered fixes (A3, A2), judged by the out-of-match test

Written 2026-09-28 by the research lead after reading
docs/results/32-critique-diagnostics.md. Both pre-declared fix triggers
fired (A2, A3). Task 32 also showed that the same-match outcome test is
largely mechanical (out-of-match LINEUP xG: +0.08, p = 0.17) and that
raw chosen-option EV beats Decision in-sample. So the gate for this
task is the OUT-OF-MATCH test, decided now, before anything runs.

What does NOT change: value models, pass-success model, policy model,
grid, offside rule R1_K10, the EV corpus, fold assignment. The holdout
is untouched. BENCHMARK-v5 stays the rollback point.

## Step 0 — Commit this brief alone. Record the hash.

## Step 1 (fix A3) — Score incomplete passes by where they were aimed
For every INCOMPLETE eligible pass, in its freeze frame, among visible
teammates (teammate = True, not the passer):
  - keep those within 15 degrees of the pass direction (start -> end
    location), measured from the passer, AND within 10 units of the
    pass end location;
  - the intended target is the one closest to the end location.
If a target exists: the chosen option becomes that teammate's
teammate-destination candidate row (is_teammate_destination == 1 at his
location); if no such row exists, the grid cell containing his location.
If no target exists: the pass is EXCLUDED from Decision (flagged, kept
in the data). Completed passes are unchanged. Report counts: retargeted,
excluded, unchanged; and the median distance moved by retargeted passes.

## Step 2 — Cross-fitted EV for the corrected chosen options
New `crossfit_v6.py`: identical to crossfit_v5.py (same folds, models,
temperature, offside rule) except that the chosen option is Step 1's.
Output per pass: ev_chosen (corrected, out-of-fold), policy_weighted_ev
(unchanged), excluded flag. Report the per-pass correlation of the new
ev_chosen with v5's.

## Step 3 (fix A2) — A baseline that is unbiased by construction
Replace "EV of the typical choice" with "EV a player typically ACHIEVES
from this situation": an XGBoost regression f(state) predicting the
out-of-fold ev_chosen from ORIGIN information only —
  - the value model's STATE_FEATURES computed at the passer's location
    from the pass's freeze frame (same feature function),
  - play pattern, under_pressure flag, period, minute.
  - NO destination information, NO player or team identity.
Cross-fitted with the SAME 5 match folds; objective reg:squarederror,
n_estimators 300, max_depth 6, learning_rate 0.05, subsample 0.8,
seed 20260928. Report out-of-fold R^2.
Decision_v6 = ev_chosen (Step 2) - f_oof(state).
Also keep, for comparison, Decision_policy_v6 = ev_chosen (Step 2) -
policy_weighted_ev.
Sanity (must hold by construction; report, do not tune): mean
Decision_v6 by zone, pass length and outcome, each within +/-10% of the
v5 overall mean Decision (0.0026745) of zero, i.e. |mean| < 0.00027.
If not, report why before continuing.

## Step 4 — Evaluation, all cross-fitted, beside v5 (Task 32 code reused)
(a) GATE — out-of-match LINEUP test (Task 32 Step 5 code unchanged):
    H-O1 for xG and goals, and PH-O2, for Decision_v6. Also run it for
    ev_chosen alone and for f(state) alone (report only).
(b) Same-match battery (H-O1, H-O2, PH-O1, PH-O2, PH-O4; xG and goals)
    for Decision_v6. Also H-O1 with f(state) and Decision_v6 together.
(c) Reliability: T6 at 200 (all roles), and Task 32 Step 4's
    within-role reliability and role share of variance, for
    Decision_v6.
(d) Player tables: Task 28 method (overall) and Task 29 method (deep
    midfield) on Decision_v6. Report the Q test, intervals entirely
    above / below, with names, the six named deep midfielders, and
    Spearman vs the v5 cross-fitted tables.
(e) Repeat (a) for Decision_policy_v6 (report only).

## GATE (fixed now)
Decision_v6 PASSES if Step 4(a) LINEUP H-O1 for xG has a positive
coefficient with p < 0.05.
- PASS: v6 becomes the candidate engine. The next brief (written before
  any holdout number exists) runs the same out-of-match test on the
  women's holdout as the final check.
- FAIL: no engine version measures a decision skill that shows up in
  other matches' results. v5 remains the benchmark, and what the paper
  may claim is decided by the author with the research lead.
Goals, PH-O2 and everything else are reported, not gated.

## HARD RULES
- Only Steps 1-3's changes. No retraining of value, pass-success or
  policy models; no new EV corpus; no change to folds, grid, offside.
- Holdout untouched.
- Commit the results page after Step 3, then at the end.
- Memory gate as in Task 25.
- No memory writes. Don't edit docs/JOURNAL.md. No interpretation.
- When finished, reply only that the task is done plus commit hashes.

## Output
docs/results/33-fixes-a2-a3.md (template). Commit per rule 9.
