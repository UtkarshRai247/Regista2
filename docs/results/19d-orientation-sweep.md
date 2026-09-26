# Task 19d: Systematic sweep for orientation bugs, then fix and re-run
Date: 2026-09-26
Status: COMPLETE

## Section checklist
- Step 0 (commit brief): COMPLETE
- Step 1 (sweep, report only, no code changes): COMPLETE
- Step 2 (fix only what the sweep proved wrong): COMPLETE — 2 fixes (one already anticipated from Task 19c, one newly found in `value_models.py`)
- Step 3 (retrain value models, recompute EV/Decision/Risk/Execution): COMPLETE
- Step 4 (re-run falsification battery): COMPLETE — T2/T3/T6 PASS; **T4 scenario_c FAILS** (not a stop condition per the hard rule, which names only T2/T3/T6)
- Step 5 (re-run cross-fitted outcome validation): COMPLETE (ran because T2/T3/T6 did not fail)

Overall: COMPLETE. Exactly two one-token code changes across the whole repo (`git diff --stat` confirms only `features.py` and `value_models.py` touched); no other engine component, no hyperparameter or feature changes. No leaderboards, no player identity, no interpretation.

## 1. Headline
The systematic sweep found exactly one more instance of the same bug already fixed once in Task 19c — and it is the more important one: `value_models.py`'s `frame_ahead_features`, which BUILDS the value models' actual training data (`value_model_rows.parquet`), had the identical `opp_nx_sorted[1]` error, independently of the already-known copy in `features.py`'s `state_features_batch` (used only at inference time). This means M_for and M_against were trained on a corrupted `defensive_line_x`/`ball_beyond_defensive_line` feature throughout Tasks 15/17/18/19/19c. Both occurrences are now fixed (one token each); nothing else in either file changed. Retraining barely moves AUC (M_for 0.8706→0.8660, M_against 0.9108→0.9103) and T2/T3/T6 all still pass — but **T4's scenario_c (through ball beyond a square defensive line, expected in the top EV decile) now fails** (EV=0.00232 vs. a corpus 90th percentile of 0.00402), and the cross-fitted outcome-validation coefficients shrink further, with **two specifications (xG and goals under H-O2, the richest control set) losing significance for the first time** across five tasks of testing. Task 19c's corrected offside rule (R4) was kept unchanged throughout, per the brief.

## 2. What I did
- Read `docs/specs/task-19d-orientation-sweep.md` and committed it alone (`362cda3`).
- Step 1: grepped all 35 files in `src/engine_v2/` (confirmed via import-graph check: this module imports nothing from `src/tempo/` or `src/decision_engine/`, so the sweep scope is exactly these 35 files) for every `np.sort`/`np.argsort`/`np.partition`/`sorted(`/`nsmallest`/`nlargest`/sorted-array indexing, `.min(`/`.max(`/`argmin`/`argmax` on a spatial coordinate, `quantile`/`percentile` on a coordinate, every `normalize_xy`/`normalize_xy_arr` call and constant comparison, and every ordering-of-players assumption. Read every non-trivial hit. Full table below (Section 3). **Wrote this report before changing any code.**
- Step 2: made the two proven-wrong fixes (`opp_nx_sorted[1]` → `opp_nx_sorted[-2]`, one token each, in `features.py`'s `state_features_batch` and `value_models.py`'s `frame_ahead_features`), printed a worked example for each from a real frame before rerunning anything.
- Step 3 (`value_models_v2.py`, `ev_recompute_v2.py`, `policy_score_v6.py`, `step6_regate.py`): retrained both value models on the corrected training data; recomputed EV corpus-wide (106,141,669 rows) via the corrected `state_features_batch` + retrained models; recomputed the policy summary (Task 19c's restriction and fitted temperature reused unchanged — see Section 4); recomputed Execution corpus-wide (it uses the value models too); re-ran T6 and the separation check.
- Step 4 (`falsification_v2.py`): re-ran T3 (Spearman EV vs p_success) and T4 (the three committed synthetic scenarios, against the retrained models); T2 was already run inside `value_models_v2.py`'s retrain; T5 is reported as unaffected (the pass-success model was never touched).
- Step 5 (`crossfit_v4.py`, `outcome_validation_crossfit_v4.py`): re-ran the 5-fold cross-fitting harness (pointed at the corrected `value_model_rows_v2.parquet` for per-fold training; `build_ev_oof_for_match` already recomputes EV fresh via the corrected `state_features_batch`, no path change needed there) and the full outcome-validation battery.
- Task 15's original `value_model_for.json`/`value_model_against.json`/`value_model_rows.parquet`/`options_ev/` and every prior task's own output files are untouched — this task writes to new `_v2` paths throughout, so Tasks 15/17/18/19/19c's own results remain reproducible from their own recorded commits.
- Reproduce with (from repo root, `.venv` active, run in order from `src/engine_v2/`):
  `python value_models_v2.py && python ev_recompute_v2.py && python policy_score_v6.py && python step6_regate.py && python falsification_v2.py && python crossfit_v4.py && python outcome_validation_crossfit_v4.py`
- Total wall clock: ~64 minutes.

## 3. Step 1 — the full sweep (report, no code changed while this was written)

**WRONG (2 found, both fixed in Step 2):**

| File | Line | Expression | Intent | Verdict |
|---|---|---|---|---|
| `features.py` | 104-105 | `defensive_line_x = np.full(K, opp_nx_sorted[1])`; `ball_beyond_defensive_line = ball_n[:,0] > opp_nx_sorted[1]` | "second-rearmost opponent" (2nd-deepest defender) for the value-model state features | **WRONG** — `[1]` is the second-SMALLEST normalized x; the GK sits near the HIGH-x end (their own goal, since the passer attacks toward high x), so `[1]` lands on a pressing forward, not the back line. Correct index is `[-2]`. |
| `value_models.py` | 92-95 | `opp_nx_sorted = np.sort(opp_n[:,0])`; `defensive_line_x = float(opp_nx_sorted[1])` | same "second-rearmost opponent" concept, for `frame_ahead_features` — the function that BUILDS the value models' training rows | **WRONG**, identical bug, independently written (does not call `state_features_batch`). This is the more consequential of the two: it corrupted the actual training data, not just an inference-time feature. |

**Already fixed (Task 19c, not touched again here):**

| File | Line | Expression | Verdict |
|---|---|---|---|
| `features.py` | 170 (was) | `second_rearmost_nx = opp_nx_sorted[-2]` | CORRECT (fixed in Task 19c; the offside test) |

**Historical, frozen, not a live bug (superseded, not touched per project convention of not editing prior tasks' frozen deliverables):**

| File | Line | Expression | Verdict |
|---|---|---|---|
| `offside_diagnostic.py` | 86 | `second_rearmost_nx = float(np.sort(opp_nx)[1])` | Task 19's own original (buggy) diagnostic, explicitly superseded by `offside_diagnostic_v2.py` in Task 19c; this file is a historical record of what was measured before the fix, not a live code path anything else depends on. |

**CORRECT, verified (every other hit from the grep):**

| Category | Files / pattern | Verdict |
|---|---|---|
| Direction-inference core | `geometry.py:36,50,73` (`team_period_directions`'s `sorted(periods)`, `sorted(means, key=means.get)` team-ordering, `normalize_xy`'s 180°-rotation definition) | CORRECT — verified against the geometric definition directly: the team with the LOWER mean shot-x (shoots at the low-x goal) is assigned direction=-1 (needs the flip), matching `ordered[0]`; this is the foundational primitive every other file depends on and behaves as documented. |
| `opponents_ahead_of_ball` / `teammates_ahead_of_ball` | `features.py:101`, `value_models.py:87,106` (`opp_n[:,0] > ball_n[:,0]`) | CORRECT — matches `engine-v2-rebuild.md` section 3's literal definition ("between ball and the opponent goal line" = higher nx than the ball); NOT affected by the `defensive_line_x` bug. |
| `numerical_advantage_ahead` | `features.py`, `value_models.py` (`teammates_ahead - opponents_ahead`) | CORRECT — built from the two already-verified-correct counts above; independently confirmed NOT to depend on `opp_nx_sorted` at all. |
| Euclidean distance min/max | `features.py:73,97,163`, `value_models.py:89` (`d_opp.min(axis=1)`, `perp.min(axis=1)`) | CORRECT — `hypot`-based, direction-independent by construction; no ordering assumption. |
| `opponents_between_ball_and_destination` | `features.py:165-167` (`np.minimum`/`np.maximum` of passer/candidate nx) | CORRECT — symmetric, direction-agnostic regardless of which of the two is "ahead." |
| `lane_congestion` | `features.py:37-74` (perpendicular-distance geometry) | CORRECT — no coordinate-ordering assumption of any kind. |
| Grid cell clipping | `grid.py`'s `chosen_cell` (`min(max(...))`) | CORRECT — operates on RAW (not normalized) coordinates within fixed pitch bounds; direction-agnostic. |
| Attacking-half constant | `offside_v2.py`, `offside_diagnostic_v2.py` (`cand_nx >= 60.0`) | CORRECT — exact half of `PITCH_X=120`. |
| Policy-probability sorting | `policy_baseline_fix.py:87`, `policy_score*.py` (`np.sort(p)[::-1]` for top-10/50 mass); `policy_baseline_fix.py:130` (`.values.argmax()` on a boolean chosen-flag) | CORRECT — these match patterns (a)/(b) literally (a sort, an argmax) but operate on POLICY PROBABILITIES or a boolean flag, never a spatial coordinate; no direction dependency exists to get wrong. |
| Softmax stabilization | every `e = np.exp(s - s.max())` (crossfit\*, ev_policy, policy_baseline_fix, policy_score\*) | CORRECT — standard numerical-stability max-subtraction on raw model scores, not spatial. |
| File/ID sorting | every `sorted(...)` on match IDs, file globs, dict items (dozens of occurrences across nearly every file) | CORRECT — deterministic iteration order only, never spatial. |
| Descriptive percentiles | `np.percentile`/`.quantile(...)` on Decision/Risk/EV/reliability/candidate-count distributions (`decision_execution_risk.py`, `grid.py`, `policy_score*.py`, `reliability_t6.py`, `step*_regate.py`, `t2_direction_check.py`, `value_models.py`, `test_t4_synthetic.py`) | CORRECT — none of these quantities are raw coordinates; no attacking-direction dependency applies. |
| Zone classification | `outcome_validation.py`/`outcome_validation_crossfit.py` (`normalize_xy` then `zone_of(nx)`, thresholds 40/80) | CORRECT — established, symmetric project convention, correctly applied post-normalization. |
| Progressive-pass check | `validation_common.py`'s `per_pass_reference_flags` (`normalize_xy` then `ex - sx >= threshold`) | CORRECT — direction-normalized forward-progress comparison, no ordering-of-players assumption. |

**UNCLEAR: none.** Every hit resolved cleanly to CORRECT or WRONG on direct inspection; nothing required a judgment call or is flagged for the research lead beyond the historical/frozen note above.

## 4. Step 2 — the two fixes and worked examples

Both changes are the identical one-token fix already validated in Task 19c (`[1]` → `[-2]`). Worked example, real frame (match 3764440, event `d57ad50f-...`, Barcelona, direction=+1) — the SAME real opponent geometry demonstrates the bug identically in both functions, since both compute `opp_nx_sorted` from the same kind of frame data:

Opponent normalized x (ascending): `[57.25, 57.45, 64.19, 66.24, 68.49, 69.47, 74.94, 76.13, 76.18, 76.28]`.
- **OLD** `defensive_line_x` (`opp_nx_sorted[1]`): **57.45**.
- **NEW** `defensive_line_x` (`opp_nx_sorted[-2]`): **76.18**.

| ball_x | OLD `ball_beyond_defensive_line` | NEW |
|---|---|---|
| 55.0 | False | False |
| 66.8 | **True** | **False** |
| 81.2 | True | True |

The middle row is the bug: a ball position still 9-10 yards short of the real back line (76.18) was marked "beyond the defensive line" under the old formula. `value_models.py`'s `frame_ahead_features` computes the identical quantity from the identical opponent set, so the same worked numbers apply there directly — confirmed by inspection of both functions' code, not re-derived separately.

`git diff --stat` after Step 2: exactly `features.py` (3 changed lines: the assignment + the comparison, both on the same fix) and `value_models.py` (1 changed line) — no other file touched.

## 5. Step 3 — retrain and recompute

**Value model AUC, old (Task 15) vs new:**

| model | Task 15 AUC | Task 19d AUC | Δ |
|---|---|---|---|
| M_for | 0.8706 | 0.8660 | −0.0046 |
| M_against | 0.9108 | 0.9103 | −0.0005 |

Both essentially unchanged; calibration remained close across deciles in both retrains (full tables in `data/engine_v2_step3_value_models_v2.json`). n_train=781,352, n_test=195,339 for both, identical to Task 15 (same row count, since the fix does not change which events are usable, only one feature's value).

**T2 (value model responds to defensive context), old vs new:** diff=−0.0159 (Task 15) → **−0.0207** (Task 19d) against a materiality threshold of 0.000377 → 0.000377 (recomputed threshold nearly identical, 10% of a similar IQR). **T2_pass: PASS**, with an even larger margin than before (~55x threshold vs. ~41x) — the counter-intuitive DIRECTION (more numerical advantage predicts LOWER scoring probability) persists after the fix, confirming Task 17's finding was not an artifact of this particular bug.

**Execution coverage:** 223,932/250,850 = 89.27%, identical to Task 15's original (structural coverage — whether a valid state exists 3 actions later — does not depend on which value models score it).

**Decision reliability (100-split, Spearman-Brown), Task 19c vs Task 19d:**

| threshold | n_units | Task 19c | Task 19d |
|---|---|---|---|
| 100 | 607 | 0.568 | 0.478 |
| 150 | 364 | 0.648 | 0.566 |
| **200** | **252** | **0.658** | **0.615** |
| 250 | 166 | 0.736 | 0.626 |
| 300 | 117 | 0.764 | 0.642 |
| 400 | 77 | 0.840 | 0.738 |
| 500 | 54 | 0.857 | 0.758 |

**T6: Decision reliability @200 = 0.615. Pass condition (>=0.60): PASS**, continuing the now five-task decline (0.780→0.704→0.623→0.658→0.615) — Task 19c's partial recovery did not hold once the training-side bug was also fixed; the margin over the gate is now the thinnest yet.

**Separation check** (n=252), Task 19c vs Task 19d:

| metric | Task 19c | Task 19d |
|---|---|---|
| completion_pct | −0.082 | **+0.026** (sign flip, small magnitude) |
| progressive_passes_per_90 | −0.236 | −0.244 |
| xa_per_90 | +0.474 | +0.409 |
| move_on_speed (tempo) | −0.178 | −0.155 |
| hold_variation (tempo) | −0.162 | −0.157 |

## 6. Step 4 — falsification battery

| test | pass condition | Task 15/17 value | Task 19c value | Task 19d value | Verdict |
|---|---|---|---|---|---|
| T2 | M_for responds materially to defensive context | diff=−0.0159, ~41x threshold | (not re-run in 19c) | diff=**−0.0207**, ~55x threshold | **PASS** |
| T3 | Spearman(EV, p_success) < 0.90 | 0.599 (Task 15) | (not re-run in 19c) | **0.664** | **PASS** |
| T4 | 3 synthetic scenarios all hold | all 3 hold (Task 15) | all 3 hold | scenario_a PASS, scenario_b PASS, **scenario_c FAIL** | **1 of 3 now fails** |
| T5 | calibration off by <=5pp per length bucket | max 2.73pp (Task 15) | unaffected | **unaffected** (pass-success model/scoring untouched by this task) | PASS (unchanged) |
| T6 | Decision reliability >=0.60 at 200 | 0.780 (Task 17) | 0.658 | **0.615** | **PASS** |

**T4 scenario_c detail**: "through ball to a teammate beyond a square defensive line must be in the top EV decile" — through-ball EV = 0.00232 vs. a corpus-wide 90th percentile of 0.00402 (both computed on the corrected corpus, `options_ev_v2`, for a fair comparison — an initial re-run mistakenly compared against the OLD, uncorrected corpus's percentile and was corrected before reporting). **FAIL.** Per the hard rule, only T2/T3/T6 failing triggers a STOP; T4 is reported here as a genuine finding, and Step 5 proceeded because none of T2/T3/T6 failed.

## 7. Step 5 — cross-fitted outcome validation, three-column comparison

Out-of-fold AUC: pass_success 0.9043 (unchanged — untouched by this task), M_for 0.8175 (Task 19c: 0.8240), M_against 0.8747 (Task 19c: 0.8789). Policy OOF top-1/top-3: 7.60%/20.28% (unchanged from Task 19c — the policy model and its features are unaffected).

**Outcome = xG:**

| Spec | v1 published | Task 19c cross-fitted | Task 19d cross-fitted |
|---|---|---|---|
| H-O1 | −0.1381 p=1.8e-4 | +0.2173 p=4.5e-7 | **+0.1342** [0.051,0.218] p=1.6e-3 |
| H-O2 | −0.1241 p=3.9e-4 | +0.0797 p=0.133 (n.s.) | **+0.0261** [−0.067,0.119] p=0.583 (n.s.) |
| PH-O1 | −0.1532 p=7.0e-5 | +0.2152 p=7.0e-7 | **+0.1329** [0.049,0.216] p=1.8e-3 |
| PH-O2 | −0.1759 p=5.2e-4 | +0.2197 p=4.2e-4 | **+0.1214** [0.001,0.242] p=0.048 |
| PH-O4 | +0.0271 p=0.532 (n.s.) | +0.3487 p=4.4e-17 | **+0.2881** [0.207,0.369] p=3.4e-12 |

**Outcome = goals:**

| Spec | v1 published | Task 19c | Task 19d |
|---|---|---|---|
| H-O1 | −0.4031 p<1e-12 | +0.2133 p=1.8e-3 | **+0.1646** [0.032,0.297] p=0.015 |
| H-O2 | −0.4587 p<1e-13 | +0.1184 p=0.087 (n.s.) | **+0.0615** [−0.071,0.194] p=0.362 (n.s.) |
| PH-O1 | −0.4101 p<1e-15 | +0.2113 p=1.6e-3 | **+0.1653** [0.035,0.295] p=0.013 |
| PH-O2 | −0.4229 p<1e-6 | +0.2596 p=2.0e-3 | **+0.2155** [0.044,0.387] p=0.014 |
| PH-O4 | −0.2088 p<1e-4 | +0.3448 p=8.3e-8 | **+0.3137** [0.186,0.441] p=1.4e-6 |

**Possession level** (n=26,647, same as Task 17/19/19c):

| Outcome | v1 published | Task 19c | Task 19d |
|---|---|---|---|
| (a) ends_in_shot (avg. marg. effect) | +0.0119 p=3.0e-4 | +0.0437 p=7.7e-57 | **+0.0371** [0.032,0.043] p=9.2e-39 |
| (b) possession_xg (OLS) | −0.00059 p=0.236 (n.s.) | +0.0099 p=2.0e-37 | **+0.0087** [0.0072,0.0101] p=1.9e-31 |

**Every Task 19d coefficient keeps the sign of Task 19c's**, but every one shrinks (typically 30-50% smaller for the team-match specs; ~15% smaller at the possession level, which remains highly significant throughout given its much larger n). **xG-H-O2 and goals-H-O2 both lose statistical significance for the first time** across Tasks 17-19d — both are the richest-control-set specification (possession_share + is_home + completion_rate + progressive_rate + xa_per_pass + fixed effects). xG-PH-O2 is now only marginally significant (p=0.048). The possession-level result remains the strongest and most stable evidence across every version of this analysis.

## 8. Deviations from the brief
None from `task-19d-orientation-sweep.md`'s Steps 0-5 or hard rules. Disclosed constructions:
- **Step 3's temperature is reused from Task 19c unchanged, not refit**, because it depends only on the policy model's raw scores over `CANDIDATE_FEATURES` and the `chosen` label — neither of which this task's fixes touch (the fixes are entirely in the value-model feature set, `STATE_FEATURES`, a disjoint set from `CANDIDATE_FEATURES`). Refitting would reproduce the identical value by construction; skipping it avoided ~3 minutes of redundant compute, not a shortcut on correctness.
- **T4's initial re-run compared the new through-ball EV against the OLD corpus's 90th percentile** (a leftover module-level path in the reused `test_t4_synthetic.py` code) — caught and corrected before this report was written, by pointing the comparison at the corrected corpus (`options_ev_v2`). The corrected comparison is what Section 6 reports; the stale-corpus version was discarded, not used anywhere in this page.
- **Retraining writes to new `_v2`-suffixed files rather than overwriting Task 15's originals** (`value_model_for.json`, `value_model_against.json`, `value_model_rows.parquet`, `options_ev/`), so that Tasks 15/17/18/19/19c's own results pages remain exactly reproducible from their own recorded commits, per the project's standing reproducibility requirement — consistent with every prior task's own convention of not modifying earlier frozen outputs.

## 9. Problems and surprises
- **The sweep's single most important finding is that a genuine bug lived in the value models' TRAINING data all along**, not just in an inference-time feature as Task 19c's own report described. Task 19c said `state_features_batch` "feeds the value models' training data" — this was imprecise: `state_features_batch` is used only at EV/Decision/Execution inference time; `value_models.py`'s own separate `frame_ahead_features` (an independently-written function, not calling `state_features_batch`) is what actually built `value_model_rows.parquet`. Both had the identical bug, independently introduced (a copy-paste-adjacent duplication of the same construction, apparently written twice rather than shared).
- **T4 scenario_c's failure is the first falsification-test failure across this entire six-task line of work** (Tasks 15/17/18/19/19c/19d). It is not a hard-rule STOP condition (only T2/T3/T6 are named), but it is a real, substantive finding: the model's response to the "through ball beyond a square defensive line" synthetic scenario weakened enough after the fix to fall out of the top decile. Since fixing `defensive_line_x` changes what "beyond the defensive line" means to the model in a training-consistent way, this could reflect the model now correctly recognizing that MOST candidates it used to (incorrectly) think were "beyond the line" no longer qualify, compressing the EV spread near the top of the distribution — this task does not investigate further, per the hard rule against interpretation, but flags it prominently for Section 10.
- **Two outcome-validation specifications lose significance for the first time**, both under the richest control set (H-O2). If taken at face value, this would narrow the paper's claim from "Decision predicts outcomes across essentially every specification tested" to "most, but not all, specifications, with the weakest results concentrated in the most heavily-controlled models" — this is exactly the kind of headline-weakening finding the project's reporting discipline requires surfacing plainly, not softening.
- **T6's continued decline (now 0.615, the thinnest margin yet over the 0.60 gate across six tasks)** is a real, monotonic-ish trend across a chain of otherwise-independent, individually-justified fixes (policy sharpening, offside correction, now orientation-bug correction). Each fix has been independently well-motivated and each still clears its own gate, but the cumulative trend is a pattern worth the research lead's attention (Section 10).

## 10. Questions for the research lead
1. T4 scenario_c's failure (Section 6/9) is the first falsification-test failure in this line of work. Should a dedicated task investigate WHY the corrected model no longer places this specific synthetic through-ball scenario in the top EV decile (e.g., is the top decile itself now dominated by a different kind of candidate, or has the overall EV distribution's shape changed near its tail), or is one non-blocking synthetic-scenario failure (out of three, with T2/T3/T6 all still passing) an acceptable residual limitation to note and move on from?
2. xG/goals-H-O2 losing significance (Section 7/9) — is this a meaningful signal that Decision's incremental validity over public metrics (completion rate, progressive-pass rate, xA per pass) was partly an artifact of the now-fixed bugs, or is it more simply explained by the compounding effect of three successive corrections each attenuating the effect somewhat? Not adjudicated here, per the hard rule against interpretation.
3. T6's five-task decline (0.780→0.704→0.623→0.658→0.615, Section 9) — each individual fix has been independently justified and gate-passing, but is the CUMULATIVE trend itself worth a dedicated diagnostic before any further engine changes are made, given how thin the current margin is?

## 11. Files produced
- `src/engine_v2/features.py`, `value_models.py` — the two authorized one-token fixes. Committed, commit `<pending>`.
- `src/engine_v2/value_models_v2.py`, `ev_recompute_v2.py`, `policy_score_v6.py`, `step6_regate.py` — Step 3. Committed, commit `<pending>`.
- `src/engine_v2/falsification_v2.py` — Step 4. Committed, commit `<pending>`.
- `src/engine_v2/crossfit_v4.py`, `outcome_validation_crossfit_v4.py` — Step 5. Committed, commit `<pending>`.
- `data/engine_v2_step3_value_models_v2.json`, `engine_v2_step3_recompute_v4.json`, `engine_v2_step3_regate_v4.json`, `engine_v2_step4_falsification_v2.json`, `engine_v2_step4_crossfit_v4.json`, `engine_v2_step5_outcome_validation_crossfit_v4.json` — step summaries (all numbers in Sections 5-7 come from these). Not committed (data/).
- `data/processed/engine_v2/value_model_for_v2.json`, `value_model_against_v2.json`, `value_model_rows_v2.parquet`, `options_ev_v2/*.parquet`, `pass_policy_summary_v6.parquet`, `pass_der_v6.parquet`, `pass_der_crossfit_v4.parquet` — new-path model/data artifacts. Not committed (data/).
- `docs/specs/task-19d-orientation-sweep.md` — the executed task spec, committed alone, commit `362cda3`.
- `docs/results/19d-orientation-sweep.md` — this page. Committed, commit `<pending>`.

## 12. Confidence
High for Step 1 (a mechanical, exhaustive grep-and-read sweep with every hit resolved to a verdict; the direction-inference primitive itself was independently re-verified against its geometric definition, not just assumed correct). High for Step 2/3's mechanical execution (exactly two lines changed repo-wide; retraining is deterministic and AUC/calibration barely moved, as expected for a fix that corrects one feature among many). Moderate-to-low for what Steps 4-5 mean substantively: T2/T3/T6 all still pass, but T4's first-ever failure and two outcome-validation specifications' first-ever loss of significance are real, not artifacts — and they arrive on top of a five-task reliability decline that is now uncomfortably close to its gate. The weakest link in the whole six-task chain is no longer any single known bug (both now-found instances of this exact bug are fixed, and the sweep found no further occurrences) but the cumulative erosion pattern itself, which this task's hard rules correctly forbid investigating further here.
