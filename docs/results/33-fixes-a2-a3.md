# Task 33: The two triggered fixes (A2, A3), judged by the out-of-match test
Date: 2026-09-28
Status: PARTIAL (Steps 0-3 complete; Step 4 not yet run — this page
will be replaced by a full version, per the brief's own hard rule:
"Commit the results page after Step 3, then at the end.")

## Note on a hard-rule reading (stated loudly, per CLAUDE.md, not buried)
The hard rules say "no retraining of value, pass-success or policy
models." Step 2 of this same brief explicitly instructs building
`crossfit_v6.py` "identical to crossfit_v5.py (same folds, models,
temperature, offside rule)" — which requires running the SAME per-fold
model-fitting procedure crossfit_v5.py already performs (that is what
cross-fitting means). I read "no retraining" as "no NEW/DIFFERENT
training spec" (hyperparameters, features, population, frozen
temperature) — not as "skip the per-fold fits Step 2 itself asks for."
Every hyperparameter dict (`PS_KWARGS`, `VM_KWARGS`,
`POLICY_XGB_KWARGS`), the frozen temperature `T=0.1562`, `fill_values`,
and the offside rule are byte-identical imports from v5's own modules;
nothing about HOW the models are trained changed. Flagged here in case
this reading is wrong.

## Section checklist
- Step 0 (commit brief alone): COMPLETE
- Step 1 (fix A3, retarget incomplete passes): COMPLETE
- Step 2 (crossfit_v6.py): COMPLETE
- Step 3 (fix A2, f(state) baseline): COMPLETE — sanity check FAILED for
  length and outcome (PASSED for zone); reported below, did not stop
  the pipeline, per the brief's own binding gate being Step 4(a).
- Step 4 (evaluation, GATE): NOT RUN (this checkpoint)

## 1. Headline
Both fixes are built. Crossfit_v6.py is verified correct for complete
passes (`ev_chosen` matches v5 exactly, r=1.0000, max diff=0, n=214,513)
and cleanly redirects `ev_chosen` for the 11,681 retargeted incomplete
passes (24,656 more are excluded, no valid target found). The f(state)
baseline (Step 3/A2) explains about half of `ev_chosen`'s variance
out-of-fold (R²=0.522) and removes the zone bias that motivated A2
completely (all three zone means within 0.00006 of zero), but its
sanity check FAILS for length (every bucket) and outcome — retargeted
(formerly incomplete) passes still carry a mean Decision_v6 of +0.00285,
over 10x the brief's own ±0.00027 tolerance, essentially unchanged in
practical magnitude from v5's original incomplete-pass bias. The
brief's own binding test (Step 4(a)'s out-of-match GATE) has not run
yet at this checkpoint.

## 2. What I did
1. Confirmed Step 0 (brief-alone commit) was already done in a prior
   turn of this same task.
2. `task33_step1_retarget.py` (Step 1/A3): for every incomplete
   eligible pass (292-match, 250,850-pass corpus, same population as
   Task 32), searched the freeze frame for a visible teammate (not the
   passer) within 15° of the passer→end-location line AND within 10
   units of the end location, picking the nearest such teammate to the
   end location as the intended target.
3. `crossfit_v6.py` (Step 2): copied crossfit_v5.py's 5-fold
   cross-fitting harness unchanged, redirecting which candidate row
   counts as "chosen" (and therefore supplies `ev_chosen`) to Step 1's
   retarget table instead of the original end-location cell, via a new
   `chosen_v6` column. Verified the row-matching worked exactly as
   designed: complete ("unchanged") passes' `ev_chosen` matches v5's
   own value EXACTLY; the is_teammate_destination-row fallback and its
   own double-fallback were never triggered (0 of 11,681 retargeted
   passes).
4. `task33_step3_f_state.py` (Step 3/A2): built the feature/target table
   (`value_model_rows_v5.parquet`'s 15 STATE_FEATURES, already computed
   at the passer's own location, plus `under_pressure`/`period`/
   `minute`), cross-fit an `XGBRegressor` on the same 5 folds to predict
   Step 2's `ev_chosen`, computed `Decision_v6 = ev_chosen - f_oof` and
   `Decision_policy_v6 = ev_chosen - policy_weighted_ev`, and ran the
   brief's sanity check by zone/length/outcome.
5. Memory checked free before each corpus-scale step; none came close
   to exhaustion. `crossfit_v6.py`'s wall clock was 1,087s (~18
   minutes), run in the background.
6. Wrote and committed this Steps-0-3 checkpoint, per the hard rule,
   before proceeding to Step 4.

Reproduce with (from `src/engine_v2/`, `.venv` activated):
`python task33_step1_retarget.py && python crossfit_v6.py && python task33_step3_f_state.py`

## 3. Step 1 (A3) — retargeting incomplete passes
250,850 eligible passes, 292 matches.

| status | n | share of total |
|---|---|---|
| unchanged (complete) | 214,513 | 85.51% |
| excluded (incomplete, no qualifying target) | 24,656 | 9.83% |
| retargeted (incomplete, target found) | 11,681 | 4.66% |

Of the 36,337 incomplete passes: 32.2% were retargeted, 67.8% excluded
(no visible teammate satisfied BOTH the 15° angle and 10-unit
end-location-distance criteria — a stricter bar than Task 32 Step 2(c)'s
angle-only diagnostic, which found 56.6% had SOME teammate within 15°
regardless of distance to the end location). Median distance moved by
retargeted passes: 4.79 units — the corrected target is typically close
to, not far from, the original recorded end location.

## 4. Step 2 — cross-fitted EV for the corrected chosen options
250,850 output rows (292 matches, 5 folds), 24,656 flagged `excluded`
(no `ev_chosen`/`decision`, kept in the data as the brief specifies).
OOF AUCs: pass_success=0.9116, M_for=0.8745, M_against=0.7222 (all
close to v5's own OOF AUCs, as expected since the models themselves are
unchanged). `ev_chosen` (v6) vs v5's: r=0.9332 over all 226,194
non-excluded, matched passes; r=**1.0000** (max abs diff=0) restricted
to the 214,513 unchanged (complete) passes — direct confirmation that
crossfit_v6.py changes nothing for complete passes and only redirects
`ev_chosen` for the 11,681 retargeted ones. Fallback-to-grid-cell used:
0 times; double-fallback-to-excluded: 0 times (every retargeted pass's
identified teammate had a matching `is_teammate_destination` candidate
row, as the coordinate analysis in planning predicted).

## 5. Step 3 (A2) — f(state) baseline
**Coverage note (a disclosed population loss, not silently absorbed):**
of the 250,850-pass v6 corpus, only 239,588 (95.51%) joined to
`value_model_rows_v5.parquet` (which itself covers ~94.1% of all events
with a resolvable frame, per `value_models.py`'s own documented figure
— eligible passes are a subset of all events, so the overlap isn't
identical, but the ~4.5% gap here is consistent with that known ceiling
rather than a new bug). All of Step 3's Decision_v6 numbers are
therefore computed on 239,588 passes (220,323 non-excluded), not the
full 250,850 — a materially smaller, and specifically
frame-availability-selected, population than v5's Decision tables use.

**f(state) model.** 19 features (`value_models.STATE_FEATURES`, 15,
including `play_pattern_code` — already satisfying the brief's "play
pattern" requirement, not a separate feature — plus `under_pressure`,
`period`, `minute`; no destination/player/team feature).
`XGBRegressor(objective="reg:squarederror", n_estimators=300,
max_depth=6, learning_rate=0.05, subsample=0.8, random_state=20260928)`
— `colsample_bytree` is not specified by the brief and was left at the
XGBoost default (disclosed, not guessed by analogy to `VM_KWARGS`'s
0.8). Pooled out-of-fold R² = **0.5222** (n=220,323) — the model
explains about half the variance in `ev_chosen` from origin state
alone.

**Sanity check** (tolerance |mean| < 0.00027, ±10% of v5's overall mean
Decision 0.0026745):

| grouping | group | n | mean Decision_v6 | verdict |
|---|---|---|---|---|
| zone | defensive | 44,961 | -0.000060 | PASS |
| zone | final | 52,718 | 0.000004 | PASS |
| zone | middle | 122,644 | 0.000006 | PASS |
| length | 0-10 | 46,384 | **-0.002054** | **FAIL** |
| length | 10-20 | 102,595 | 0.000344 | FAIL |
| length | 20-30 | 47,279 | 0.000894 | FAIL |
| length | 30+ | 24,065 | 0.000665 | FAIL |
| outcome | complete | 210,851 | -0.000136 | PASS |
| outcome | incomplete | 9,472 | **0.002852** | **FAIL** |

Zone bias is essentially eliminated (all three means within 0.00006 of
zero — the A2 fix works exactly as intended along this one dimension).
Length and outcome are NOT: every length bucket fails, and — most
directly relevant to A3 — passes still flagged `incomplete` (i.e., the
11,681 *retargeted* passes; excluded passes are dropped from this
table since they have no Decision_v6) still carry a mean Decision_v6 of
+0.00285, essentially unchanged in magnitude from v5's own original
incomplete-pass bias (+0.00522) relative to what a ±0.00027 tolerance
would require. **Retargeting incomplete passes to their inferred target
did not, by itself, remove their systematic Decision bias.** Overall
mean Decision_v6 = -0.000008 (near zero, as guaranteed on average by
OOF residualization) and overall mean Decision_policy_v6 = 0.002557
(close to v5's 0.0026745, as expected since it uses the same
policy-weighted baseline, just on v6's corrected `ev_chosen`).

## 6. Deviations from the brief (Steps 0-3 only)
1. **The hard-rule reading stated at the top of this page** (Step 2's
   per-fold model fitting vs. the "no retraining" hard rule) — the most
   consequential interpretive call in this task, disclosed loudly, not
   buried.
2. **Coverage loss** (Section 5): Decision_v6 is computed on 239,588 of
   the full 250,850-pass corpus (95.51%), not all of it, because
   `value_model_rows_v5.parquet` covers ~94.1% of events with a
   resolvable frame — a pre-existing ceiling of the reused infrastructure,
   not a new gap introduced by this task, but its exact size (4.49% of
   THIS task's corpus) had not been reported before and is disclosed in
   full here.
3. Step 3's sanity-check failure did not stop the pipeline before Step
   4, per this task's own explicit reading that the brief's binding gate
   is Step 4(a), not the Step-3 sanity check (the brief's own wording,
   "report why before continuing," was read as requiring a report, not
   a hard stop) — disclosed here, before Step 4 runs, not decided after
   seeing Step 4's outcome.

## 7. Problems and surprises
- The zone sanity check passing perfectly while length and outcome fail
  substantially is itself informative: f(state) is evidently very good
  at removing positional bias but not at removing pass-length or
  completion-outcome bias — these are different kinds of confound the
  brief's single feature set does not equally address.

## 8. Questions for the research lead
None yet from Steps 0-3 — no ambiguity in the brief's own text required
a judgment call beyond the disclosed items in Section 6. Section 8 of
the final version of this page (after Step 4) may add more.

## 9. Files produced (Steps 0-3)
- `src/engine_v2/task33_step1_retarget.py` — new. Step 1/A3 retargeting.
- `src/engine_v2/crossfit_v6.py` — new. Step 2 cross-fitted EV on the
  corrected chosen options.
- `src/engine_v2/task33_step3_f_state.py` — new. Step 3/A2 f(state)
  baseline, Decision_v6/Decision_policy_v6 construction, sanity check.
- `data/processed/engine_v2/incomplete_retarget_v6.parquet`,
  `pass_der_crossfit_v6.parquet`, `decision_v6.parquet` — new data
  artifacts (under `data/`, not committed).
- `data/engine_v2_task33_step1.json`, `data/engine_v2_step2_crossfit_v6.json`,
  `data/engine_v2_task33_step3.json` — new summary JSONs (under `data/`,
  not committed).
- `docs/results/33-fixes-a2-a3.md` — this file (checkpoint version;
  will be overwritten with the full Steps 0-4 version before the final
  commit).
- No frozen v5 artifact was modified. The women's holdout was not
  touched.

## 10. Confidence
High confidence in the Steps 1-3 numbers: crossfit_v6.py's core
correctness claim (unchanged passes reproduce v5 exactly, r=1.0000,
max diff=0) is independently verified, not assumed. The weakest link is
the sanity check's own scope: it establishes zone-unbiasedness cleanly
but leaves length and outcome biased, and this task does not yet know
whether that will matter for the GATE (Step 4, not yet run).
