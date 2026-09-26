# Task 18: Sharpen the policy baseline, then re-validate without circularity
Date: 2026-09-25
Status: COMPLETE

## Section checklist
- Step 0 (commit brief): COMPLETE
- Step 1 (restricted candidate set + temperature calibration, judged on held-out policy accuracy only): COMPLETE — reading: policy is now BEHAVIORAL, with a disclosed coverage caveat
- Step 2 (recompute Decision/Execution/Risk with the calibrated policy; re-gate T6; re-run separation): COMPLETE — T6 PASS (0.704 at 200, above 0.60)
- Step 3 (cross-fitting harness, out-of-fold vs in-sample AUC, full outcome battery on cross-fitted Decision): COMPLETE — did not run out of time; ran to completion

Overall: COMPLETE, all four steps ran. No leaderboards, no player identity anywhere in Steps 1-4 (Step 3 continues that discipline). Step 3's outcome battery uses team and possession aggregates only.

## 1. Headline
Both defects the brief targeted are real, and both are now addressed. The policy baseline (Task 17) was fixed by restricting candidates (p_success>=0.05, not offside, distance<=45y) and calibrating a softmax temperature (T=0.158, fit on held-out policy log-likelihood only): median effective options fell from 421.7 to 56.3 and the policy-weighted/unweighted EV correlation fell from 0.9986 to 0.855 — both pre-specified criteria for "behavioral" are met — but only 54.5% of held-out passes retain their actual chosen destination under the restriction, overwhelmingly because 43.6% of REAL, completed passes are flagged `offside_destination` by engine v2's existing offside heuristic (Section 5). With the calibrated policy, Decision's reliability at 200 passes is 0.704 (down from 0.780, still comfortably above the 0.60 gate), and the outcome-validation battery — rerun honestly under Task 09's 5-fold cross-fitting harness — **does not collapse**: every Decision_z coefficient from Task 17 keeps its sign and, with one exception (xG under H-O2's full control set), keeps statistical significance, though every coefficient shrinks by roughly 30-45%. Task 17's reversal of engine v1's result was real, not purely the value model predicting itself — but it was inflated by in-sample circularity by a meaningful amount, and the offside-flag anomaly is now the most important open question for this line of work.

## 2. What I did
- Read `docs/specs/task-18-policy-crossfit.md` and committed it alone (`d5404eb`).
- Step 1 (`src/engine_v2/policy_baseline_fix.py`): match-disjoint train/test split (233/59 matches, seed 42); restricted-candidate filter; softmax temperature fit by maximizing held-out log-likelihood on training matches; reported before/after on the held-out test matches. No Decision or outcome value was consulted anywhere in this step.
- Step 2 (`src/engine_v2/policy_score_v2.py`, `src/engine_v2/step2_regate.py`): applied the calibrated policy (restriction + fixed T) to the full 106,141,669-row corpus; recomputed Decision and Risk (Execution is unaffected by the policy and was reused unchanged); re-ran the T6 reliability sweep and the separation check; reported old vs new.
- Step 3 (`src/engine_v2/crossfit.py`, `src/engine_v2/outcome_validation_crossfit.py`): reused `data/splits/cv_folds.csv` (Task 09's frozen 5-fold, seed-20260920, competition-season-stratified assignment — its match set is a strict superset of engine v2's 292 matches, so no rebuild was needed). Retrained the pass-success model, both value models, and the policy model per fold on the other four folds; scored each held-out fold out-of-fold; recomputed EV, Decision, Risk and Execution from out-of-fold values only; reran the full outcome-validation battery (H-O1/H-O2/PH-O1/PH-O2/PH-O3/PH-O4) on the cross-fitted Decision.
- No file under `src/decision_engine/` or any earlier Task 15/17 `src/engine_v2/` file was modified — confirmed via `git status`/`git diff` at the end.
- Reproduce with (from repo root, `.venv` active, run in order from `src/engine_v2/`):
  `python policy_baseline_fix.py && python policy_score_v2.py && python step2_regate.py && python crossfit.py && python outcome_validation_crossfit.py`
- Total wall clock: ~36 minutes (Steps 1-2: ~10 minutes; Step 3: ~26 minutes, including one code-fix restart after a duplicate-column crash on the first attempt — see Section 5).

## 3. Numbers

### Step 1 — policy baseline fix (match-disjoint split: 233 train / 59 test matches, seed 42)

| metric (held-out test matches) | BEFORE (full set, T=1) | AFTER (restricted + calibrated T) |
|---|---|---|
| coverage (chosen candidate survives) | 100.0% | **54.5%** |
| top-1 accuracy (among covered passes) | 6.81% | 10.24% |
| top-3 accuracy (among covered passes) | 18.80% | 26.69% |
| mean log-likelihood/pass (covered) | −5.748 | −3.967 |
| median effective options | 421.7 | **56.3** |
| median top-10 probability mass | 0.0384 | 0.5304 |
| median top-50 probability mass | 0.1490 | 0.7564 |
| corr(policy-weighted, unweighted mean EV) | 0.9986 | **0.8554** |

Fitted temperature: **T = 0.1579** (fit by maximizing log-likelihood of the chosen destination on training-match restricted candidates only). Restricted candidates per pass (test matches): mean 152.5, median 155, p90 199.

**Pre-specified reading: BEHAVIORAL** — median effective options (56.3) < 100 AND correlation (0.855) < 0.95, both conditions met. Per the hard rule, no further iteration was performed and nothing was tuned on a Decision or outcome value — every number above is a policy-accuracy metric (top-1/top-3/log-likelihood/entropy/mass concentration), never Decision.

### Step 2 — recompute and re-gate (n=250,814 of 250,850 passes; 36 excluded for zero surviving restricted candidates)

Reliability of Decision (100-split, Spearman-Brown, old vs new):

| threshold | n_units | old median | new median |
|---|---|---|---|
| 100 | 607 | 0.685 | 0.614 |
| 150 | 364 | 0.764 | 0.705 |
| **200** | **252** | **0.780** | **0.704** |
| 250 | 166 | 0.845 | 0.784 |
| 300 | 117 | 0.884 | 0.828 |
| 400 | 77 | 0.922 | 0.872 |
| 500 | 54 | 0.936 | 0.888 |

**T6 (new): Decision reliability @200 = 0.704. Pass condition (>=0.60): PASS** (lower than the old, still-behavioral-but-diffuse policy's 0.780, but with a wide margin over the gate).

Separation check (n=252 qualifying units), old vs new:

| metric | old r | new r |
|---|---|---|
| completion_pct | −0.299 | −0.178 |
| progressive_passes_per_90 | −0.420 | −0.300 |
| xa_per_90 | +0.547 | +0.530 |
| move_on_speed (tempo) | −0.097 | −0.255 |
| hold_variation (tempo) | −0.107 | −0.220 |

Correlations with completion rate/progressive rate weakened; correlations with the two tempo metrics strengthened (roughly 2x in magnitude); xA/90 stayed the strongest and most stable relationship.

### Step 3 — cross-fitting (5 folds, `data/splits/cv_folds.csv`, seed 20260920; 292 matches, 250,814 passes, 223,901 with valid Execution)

Out-of-fold vs in-sample AUC/accuracy:

| model | in-sample (Task 15/17) | out-of-fold |
|---|---|---|
| pass_success (AUC) | 0.9067 | **0.9043** |
| M_for (AUC) | 0.8706 | **0.8240** |
| M_against (AUC) | 0.9108 | **0.8789** |
| policy (top-1 accuracy) | 0.1024* | 0.1041 |
| policy (top-3 accuracy) | 0.2669* | 0.2672 |

*Task 18 Step 1's own held-out (non-cross-fitted) figure for the calibrated policy, the closest available in-sample-style comparator (Task 15/17's original diffuse policy's 6.8%/18.8% is not comparable since it predates the Step 1/2 fix).

Pass-success shows almost no in-sample flattery (−0.24pp). Both value models show a real gap (M_for −4.66pp, M_against −3.19pp) — smaller than Task 09's own possession-value gap on engine v1 (0.799→0.743, −5.6pp) but the same direction and a similar order of magnitude. The policy's OOF accuracy is statistically indistinguishable from its single-split held-out figure — no material flattery there.

**Outcome-validation battery, cross-fitted Decision vs. Task 17's in-sample Decision** (n=583 team-match units both times):

Outcome = xG:

| Spec | Task 17 in-sample coef [CI] | p | Cross-fitted coef [CI] | p |
|---|---|---|---|---|
| H-O1 | +0.2690 [0.192, 0.346] | 5.75e-12 | **+0.1684** [0.094, 0.243] | 9.87e-06 |
| H-O2 | +0.1355 [0.050, 0.221] | 1.86e-03 | **+0.0453** [−0.032, 0.123] | 0.251 (n.s.) |
| PH-O1 | +0.2765 [0.196, 0.357] | 1.83e-11 | **+0.1744** [0.098, 0.251] | 7.03e-06 |
| PH-O2 | +0.2833 [0.164, 0.402] | 2.93e-06 | **+0.1721** [0.067, 0.277] | 1.27e-03 |
| PH-O4 | +0.3384 [0.257, 0.420] | 4.44e-16 | **+0.2208** [0.144, 0.298] | 2.12e-08 |

Outcome = goals:

| Spec | Task 17 in-sample coef [CI] | p | Cross-fitted coef [CI] | p |
|---|---|---|---|---|
| H-O1 | +0.3183 [0.173, 0.464] | 1.74e-05 | **+0.2182** [0.089, 0.347] | 9.19e-04 |
| H-O2 | +0.2752 [0.120, 0.431] | 5.17e-04 | **+0.1477** [0.018, 0.277] | 0.0255 |
| PH-O1 | +0.3285 [0.176, 0.481] | 2.38e-05 | **+0.2123** [0.083, 0.341] | 1.26e-03 |
| PH-O2 | +0.4148 [0.225, 0.605] | 1.92e-05 | **+0.2755** [0.120, 0.431] | 5.07e-04 |
| PH-O4 | +0.3861 [0.243, 0.529] | 1.23e-07 | **+0.2698** [0.141, 0.398] | 3.95e-05 |

Possession level (n=26,647 in-sample vs. n=26,644 cross-fitted — 3 fewer, from fold-boundary bookkeeping, not a material difference):

| Outcome | in-sample effect [CI] | p | cross-fitted effect [CI] | p |
|---|---|---|---|---|
| (a) ends_in_shot (avg. marg. effect) | +0.0575 [0.052, 0.062] | 4.76e-111 | **+0.0374** [0.032, 0.043] | 7.69e-47 |
| (b) possession_xg (OLS) | +0.0152 [0.013, 0.017] | 2.25e-54 | **+0.0091** [0.008, 0.010] | 4.40e-37 |

**Every cross-fitted coefficient keeps the sign of its in-sample counterpart.** Every one remains statistically significant at p<0.03 except xG under H-O2 (p=0.251, the specification with the most controls: possession_share, is_home, completion_rate, progressive_rate, xa_per_pass, and comp-season fixed effects — the richest, and thus tightest, specification). Magnitudes shrink by roughly 30-45% across the board (e.g. PH-O3(a)'s effect: 0.0575→0.0374, a 35% reduction; PH-O3(b): 0.0152→0.0091, a 40% reduction). **v1's own v2-8.4 claim rule (PH-O2 and PH-O3(a) both positive with CI excluding zero) is satisfied even under cross-fitting**: PH-O2(xG) +0.172 [0.067, 0.277]; PH-O3(a) +0.0374 [0.032, 0.043].

## 4. Deviations from the brief
None from `task-18-policy-crossfit.md`'s Steps 0-3 or hard rules. Disclosed constructions:
- **The train/test split used to fit and evaluate Step 1's changes** is a fresh match-disjoint `GroupShuffleSplit` (seed 42, 20% test) over all 292 matches, not a reconstruction of whichever exact split happened to fall out of Task 15/17's own training-pool-construction RNG sequence (never persisted to disk as an explicit match list). Judged purely on held-out policy accuracy either way, consistent with the hard rule.
- **The policy model IS retrained per fold in Step 3**, extending Task 09's original three-model procedure (pass-success, one value model, policy) to engine v2's four-model architecture (pass-success, M_for, M_against, policy) — the brief's own wording ("the two value models and the pass-success model") emphasizes the count difference from v1's single value model, and Task 09's own preregistered v2-4.2 procedure explicitly retrains "all three models," including the policy — retraining engine v2's policy too is the faithful extension of that precedent, not a scope addition.
- **The policy-training-pool restriction filter for TRAIN folds uses each candidate's original (Task 15) in-sample p_success**, not a fold-specific out-of-fold value, as a data-selection criterion only (which rows are eligible training examples) — the policy model's own features never include p_success, so this does not leak label information into it. HELD-OUT test-fold candidates are always restricted using their own fold-specific out-of-fold p_success, so the final cross-fitted EV/Decision for every held-out pass uses no in-sample information.
- **Step 1's fitted temperature (T=0.1579) is reused fixed across all 5 cross-fit folds**, not refit per fold, since it is a single global scalar already validated on held-out policy accuracy and refitting it 5 more times would add complexity for a parameter that governs calibration sharpness, not a decision-relevant threshold.

## 5. Problems and surprises
- **The restricted policy's 54.5% coverage is a serious, and unexpected, limitation.** Breaking it down (Section 1's headline): only 0.12% of real chosen passes fail the p_success>=0.05 filter and only 3.6% fail the distance<=45y filter, but **43.6% of real, completed, actually-played passes are flagged `offside_destination`** by engine v2's existing heuristic. Real completed passes are almost never actually offside (the receiving player would be flagged by the referee), so a 43.6% flag rate on real chosen destinations strongly suggests engine v2's offside heuristic (built in Task 15: "beyond the second-rearmost visible opponent and beyond the ball, in the attacking direction") over-fires — this is a defect in the ENGINE surfaced by this task's diagnostics, not something Task 18 was asked or permitted to fix ("Fix the policy, not Decision" scopes this task to the policy baseline only). It is reported here as the most important open finding, per Section 6.
- **T6's reliability fell from 0.780 to 0.704** with the calibrated policy — still comfortably above the 0.60 gate, but a real decrease, not an improvement, alongside the diffuseness fix. A sharper, more selective policy baseline apparently introduces somewhat more split-half noise into Decision (plausibly because policy_weighted_ev now depends on a smaller, more variable candidate set per pass — median 155 candidates instead of ~423) — reported plainly, not investigated further per the hard rule against tuning.
- **The outcome-validation reversal from Task 17 (engine v1 negative/null, engine v2 positive/significant) substantially survives cross-fitting**, with one exception (xG under H-O2's full control set loses significance) and a consistent ~30-45% attenuation everywhere else. This means Task 17's finding was NOT simply "the value model predicting itself" — but the honest, out-of-fold test shows real in-sample inflation on the order of a third to a half of the originally reported effect sizes. Both facts are true simultaneously and are reported together, per the hard rule against choosing one over the other.
- **The first Step 3 run crashed** (`ValueError: cannot reindex on an axis with duplicate labels`) from a duplicate `distance_u` column (already present in `CANDIDATE_FEATURES`, redundantly requested again in an explicit column list) — the identical class of bug already hit and fixed once in Step 1's own script. Fixed and rerun to completion; no partial or corrupted output from the failed run was used anywhere in this report.
- Step 3's possession count (26,644) is 3 lower than Task 17's in-sample possession count (26,647) — a minor discrepancy from fold-boundary bookkeeping (a handful of possessions whose passes span a fold assignment edge case), not investigated further since it changes n by 0.01%.

## 6. Questions for the research lead
1. **The 43.6% offside-flag rate on real, completed passes (Section 5) looks like a defect in engine v2's offside heuristic itself**, not a policy problem. Should a future task audit and, if needed, fix `features.py`'s `offside_destination` construction? Until then, any restricted-candidate-set analysis (including this task's own Step 1/2 policy) inherits this limitation, and the 54.5% coverage figure should be read as a symptom of it, not an independent finding about how often real passes are genuinely borderline-offside.
2. **T6's reliability decrease (0.780→0.704) alongside the diffuseness fix** — is this an acceptable trade-off (still well above the 0.60 gate) or worth a dedicated investigation into whether a different restriction/temperature combination could sharpen the policy without costing reliability? This task's hard rules forbid that further iteration here.
3. **The one specification that loses significance under cross-fitting (xG, H-O2, p=0.251)** is also the one with the most controls (public metrics + fixed effects). Is this a meaningful signal that the effect is partly explained by those controls once in-sample flattery is removed, or is it more simply explained by reduced power (the richest specification has the most parameters relative to n=583)? Not adjudicated here, per the hard rule against interpretation.

## 7. Files produced
- `src/engine_v2/policy_baseline_fix.py` — Step 1. Committed, commit `833e568`.
- `src/engine_v2/policy_score_v2.py`, `src/engine_v2/step2_regate.py` — Step 2. Committed, commit `833e568`.
- `src/engine_v2/crossfit.py`, `src/engine_v2/outcome_validation_crossfit.py` — Step 3. Committed, commit `833e568`.
- `data/engine_v2_step1_policy_baseline_fix.json`, `engine_v2_step2_recompute.json`, `engine_v2_step2b_regate.json`, `engine_v2_step3_crossfit.json`, `engine_v2_step3_outcome_validation_crossfit.json` — step summaries (all numbers in Section 3 come from these). Not committed (data/).
- `data/processed/engine_v2/pass_policy_summary_v2.parquet`, `pass_der_v2.parquet`, `pass_der_crossfit.parquet` — per-pass tables for the calibrated-policy and cross-fitted Decision/Execution/Risk. Not committed (data/).
- `docs/specs/task-18-policy-crossfit.md` — the executed task spec, committed alone, commit `d5404eb`.
- `docs/results/18-policy-and-crossfit.md` — this page. Committed, commit `833e568`.

## 8. Confidence
High for Step 1 (deterministic, judged only on held-out policy metrics as instructed, both pre-specified criteria clearly met) and for Step 2's T6 re-gate (clean margin over the 0.60 threshold). High for Step 3's mechanical execution (out-of-fold AUCs are sane and in the expected direction/magnitude versus Task 09's own precedent; every regression specification matches Task 17's exactly, verified coefficient-by-coefficient). Moderate for what Step 3 means substantively: the reversal from engine v1 survives cross-fitting in sign and (mostly) in significance, which is a real, positive finding for engine v2 — but the ~30-45% attenuation is large enough that a reader should not treat Task 17's original magnitudes as the honest estimate. The weakest link in the whole task is the offside-flag anomaly (Section 5/6): it caps the restricted policy's real-world applicability at 54.5% coverage and was outside this task's authority to fix.
