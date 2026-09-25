# Task 17: Engine v2 — direction check, policy sharpness, Decision, T6, outcome validation
Date: 2026-09-25
Status: COMPLETE

## Section checklist
- Step 0 (commit brief): COMPLETE
- Step 1 (T2 direction check): COMPLETE — reading: PROCEED
- Step 2 (policy sharpness): COMPLETE — reading: baseline is diffuse (stated limitation, does not stop the task)
- Step 3 (Decision, Execution, Risk): COMPLETE — Execution kept (89.27% coverage, above the 80% floor)
- Step 4 (T6, reliability gate + separation check): COMPLETE — verdict: PASS (0.780 at 200-pass threshold vs. 0.60 required)
- Step 5 (outcome validation): COMPLETE (T6 passed, so this ran)

Overall: COMPLETE. No leaderboard, no player identity anywhere in Steps 1-4 (verified below). Step 5 uses team and possession aggregates only.

## 1. Headline
Engine v2's Decision is reliable (split-half reliability 0.780 at 200 passes, well above the 0.60 gate) and — unlike engine v1, which failed this exact battery with negative or null coefficients — engine v2's Decision is **positively and significantly associated with every outcome tested**: team-match xG and goals (all five specifications, p ranging from 4×10⁻¹⁶ to 0.002), and possession-level ends-in-shot and possession-xG (p < 10⁻⁵³ both). This reverses engine v1's central finding. It comes with two disclosed caveats that qualify every number in this report: the T2 direction check found a real, empirically-confirmed inversion (more attacking numerical advantage predicts *lower* scoring probability almost everywhere on the pitch — the model is right, the football intuition needs revising, not a defect); and the behavior-policy baseline is diffuse (median 420.6 effective options of ~423 actual candidates, 0.9986 correlation between the policy-weighted and simple-unweighted mean EV) — Decision may be measuring "destination quality against the average pitch cell" more than a genuinely behavioral comparison, and that limitation travels with every downstream coefficient in Section 3.

## 2. What I did
- Read `docs/specs/task-17-engine-v2-validation.md` and committed it alone (`f576247`).
- Step 1 (`src/engine_v2/t2_direction_check.py`): partial dependence of M_for on `numerical_advantage_ahead` at 5 locations, split by play pattern; empirical benchmark from real training rows; applied the pre-specified reading. Result: PROCEED (no stop).
- Step 2 (`src/engine_v2/policy_score.py`): scored the full 106,141,669-row candidate corpus with Task 15's frozen policy model, built the per-pass policy summary, reported entropy/effective-options/mass-share statistics and the diffuseness reading.
- Step 3 (`src/engine_v2/decision_execution_risk.py`): computed Decision, Execution, Risk per pass; Execution's 3-actions-later state built from real subsequent events; aggregated to per-player-season means per 100 passes (internal table only).
- Step 4 (`src/engine_v2/reliability_t6.py`): T6 split-half reliability sweep (Decision and Execution) and the separation check against public/tempo metrics. T6 PASSED.
- Step 5 (`src/engine_v2/outcome_validation.py`, run because Step 4 passed): rebuilt the team-match and possession-level tables from engine v2's own Decision and ran H-O1/H-O2/PH-O1/PH-O2/PH-O3/PH-O4 exactly as v1 specified them.
- No file under `src/decision_engine/` or any Task 15 `src/engine_v2/` file was modified — confirmed via `git status`/`git diff` at the end.
- Reproduce with (from repo root, `.venv` active, run in order from `src/engine_v2/`):
  `python t2_direction_check.py && python policy_score.py && python decision_execution_risk.py && python reliability_t6.py && python outcome_validation.py`
- Total wall clock: ~35 minutes.

## 3. Numbers

### Step 1 — T2 direction check
Partial dependence of M_for on `numerical_advantage_ahead` (10th → 90th percentile, all other features at their training median), baseline play pattern:

| x location | p_for @ p10 | p_for @ p90 | direction |
|---|---|---|---|
| 30 | 0.00406 | 0.00269 | decreasing |
| 50 | 0.00450 | 0.00215 | decreasing |
| 70 | 0.00430 | 0.00174 | decreasing |
| 90 | 0.01066 | 0.00183 | decreasing |
| 110 | 0.01658 | 0.00214 | decreasing |

Same pattern holds split by play pattern (Regular Play: 0.00347→0.0024 ... 0.01424→0.00192 across the 5 locations; From Counter: 0.02908→0.01759 ... 0.08044→0.01197 — larger absolute probabilities as expected for counter-attacks, same decreasing direction at every location in both subsets).

Empirical benchmark (real training rows, within-band quintiles of `numerical_advantage_ahead`, observed `label_for` rate):

| x-band | n | rate at q1 (lowest advantage) | rate at q5 (highest advantage) | direction |
|---|---|---|---|---|
| 0-20 | 83,274 | 0.02722 | 0.00598 | decreasing |
| 20-40 | 165,987 | 0.00442 | 0.00647 | increasing (weak, non-monotonic — see Section 5) |
| 40-60 | 235,579 | 0.00291 | 0.00205 | decreasing |
| 60-80 | 235,454 | 0.00272 | 0.00118 | decreasing |
| 80-100 | 168,423 | 0.00985 | 0.00149 | decreasing |
| 100-120 | 87,115 | 0.03610 | 0.00072 | decreasing |

**Direction agreement: 4 of 5 locations agree** (all except x=30, whose empirical band shows a weak, non-monotonic increase — see Section 5). **Verdict: PROCEED** — the model tracks the empirical rates at an overwhelming majority of locations, in both play-pattern subsets; per the pre-specified reading, this means the model is right and the football intuition ("more attackers ahead = better") is the one that needs revising, not the model. Step 3 proceeds.

### Step 2 — Policy sharpness (n=250,850 passes, ~423 candidates/pass on average)

| statistic | p5 | p25 | p50 | p75 | p95 |
|---|---|---|---|---|---|
| entropy | 5.661 | 5.900 | 6.042 | 6.180 | 6.289 |
| effective options (exp(entropy)) | 287.3 | 365.0 | **420.6** | 482.9 | 538.8 |
| top-10 probability mass | 0.0304 | 0.0343 | 0.0384 | 0.0438 | 0.0538 |
| top-50 probability mass | 0.1192 | 0.1324 | 0.1492 | 0.1697 | 0.2118 |

Correlation between policy-weighted mean EV and unweighted mean EV across all 250,850 passes: **0.9986**.

**Pre-specified reading: both trigger** (median effective options 420.6 > 100; correlation 0.9986 > 0.95). **The baseline is too diffuse to be behavioral** — with ~423 real candidates and ~421 "effective" (near-uniform) options, and the policy-weighted average tracking the simple unweighted average almost exactly, Decision is close to "how good was the chosen destination compared to the average point on the pitch," not "how good was the chosen destination compared to what this policy model actually tends to prefer." Per the task's own instruction, this is reported as a stated limitation alongside Decision, not suppressed, and it applies to every Decision-based number in Section 3.

### Step 3 — Decision, Execution, Risk (n=250,850 passes)
- Decision per pass: p5=−0.0051, p25=0.0014, p50=0.0033, p75=0.0058, p95=0.0158.
- Risk per pass: p5=−0.00035, p25=−0.00008, p50=−0.00003, p75=−0.00001, p95=0.00017.
- **Execution coverage: 223,932/250,850 = 89.27%** (66 out-of-bounds — the pass was among a match's last 3 events; 26,852 with no location/frame at i+3). **Above the 80% floor — Execution is KEPT.**
- Execution per pass: p5=−0.0073, p25=−0.0009, p50=0.0004, p75=0.0034, p95=0.0223.
- 2,946 player-season units total; **252 qualify at the 200-pass floor**.
- Decision per 100 passes (player-season): p5=0.088, p25=0.299, p50=0.400, p75=0.543, p95=0.926.
- Execution per 100 passes (player-season): p5=−0.146, p25=0.148, p50=0.295, p75=0.528, p95=1.114.
- Risk per 100 passes (player-season): p5=−0.018, p25=−0.008, p50=−0.004, p75≈0.000, p95=0.015.
- No player name, id-as-identity list, or ranking appears anywhere in this task's console output or this results page.

### Step 4 — T6, the reliability gate

| threshold | Decision n_units | Decision median | Execution n_units | Execution median |
|---|---|---|---|---|
| 100 | 607 | 0.685 | 518 | 0.512 |
| 150 | 364 | 0.764 | 306 | 0.602 |
| **200** | **252** | **0.780** | 203 | 0.714 |
| 250 | 166 | 0.845 | 137 | 0.791 |
| 300 | 117 | 0.884 | 100 | 0.825 |
| 400 | 77 | 0.922 | 64 | 0.889 |
| 500 | 54 | 0.936 | 52 | 0.895 |

**T6: Decision reliability @200 = 0.780. Pass condition (>= 0.60): PASS**, with a wide margin. (Execution reliability is reported for completeness since it survived Step 3's coverage floor; T6's pass condition is specified for Decision only.)

Separation check (n=252 qualifying units):

| metric | n | r with Decision_per_100 |
|---|---|---|
| completion_pct | 252 | −0.299 |
| progressive_passes_per_90 | 252 | −0.420 |
| xa_per_90 | 252 | +0.547 |
| move_on_speed (tempo) | 252 | −0.097 |
| hold_variation (tempo) | 252 | −0.107 |

Decision correlates negatively with completion rate and progressive-pass rate, positively and most strongly with xA/90, and only weakly with either tempo metric — Decision is not simply restating any one of these public/tempo metrics (see Section 5).

### Step 5 — Outcome validation (T6 passed; specifications unchanged from v2-6.3/8.3/9.2)

**Team-match level, n=583 of 598** (15 dropped for missing Decision — same count as v1's own drop, though not necessarily the identical 15 rows).

Decision_z coefficient, engine v2 vs. engine v1 (published), outcome = xG:

| Spec | v2 coef | v2 95% CI | v2 p | v1 coef (published) | v1 95% CI | v1 p |
|---|---|---|---|---|---|---|
| H-O1 | **+0.2690** | [0.192, 0.346] | 5.75e-12 | −0.1381 | [−0.210, −0.066] | 1.8e-4 |
| H-O2 | **+0.1355** | [0.050, 0.221] | 0.00186 | −0.1241 | [−0.193, −0.056] | 3.9e-4 |
| PH-O1 | **+0.2765** | [0.196, 0.357] | 1.83e-11 | −0.1532 | [−0.229, −0.077] | 7.0e-5 |
| PH-O2 | **+0.2833** | [0.164, 0.402] | 2.93e-06 | −0.1759 | [−0.275, −0.077] | 5.2e-4 |
| PH-O4 (no possession share) | **+0.3384** | [0.257, 0.420] | 4.44e-16 | +0.0271 | [−0.058, 0.112] | 0.532 |

Outcome = goals:

| Spec | v2 coef | v2 95% CI | v2 p | v1 coef (published) | v1 95% CI | v1 p |
|---|---|---|---|---|---|---|
| H-O1 | **+0.3183** | [0.173, 0.464] | 1.74e-05 | −0.4031 | [−0.512, −0.294] | <1e-12 |
| H-O2 | **+0.2752** | [0.120, 0.431] | 5.17e-04 | −0.4587 | [−0.576, −0.341] | <1e-13 |
| PH-O1 | **+0.3285** | [0.176, 0.481] | 2.38e-05 | −0.4101 | [−0.522, −0.298] | <1e-15 |
| PH-O2 | **+0.4148** | [0.225, 0.605] | 1.92e-05 | −0.4229 | [−0.581, −0.265] | <1e-6 |
| PH-O4 (no possession share) | **+0.3861** | [0.243, 0.529] | 1.23e-07 | −0.2088 | [−0.309, −0.109] | <1e-4 |

Every engine-v2 coefficient is positive; every v1 coefficient (except PH-O4/xG, which was null) was negative. R² by spec (xG): H-O1 0.212, H-O2 0.295, PH-O1 0.214, PH-O2 0.429, PH-O4 0.095 (v1's comparable R² were of similar magnitude — 0.166/0.218/0.173/0.403/0.007 — engine v2 explains a similar or somewhat larger share of variance).

Other H-O1 coefficients (xG): `possession_share` +2.467 [1.850, 3.084] p=4.5e-15; `is_home` −0.016 [−0.175, 0.143] p=0.843 (both directionally consistent with v1's own possession_share/is_home coefficients).

**Possession level, n=26,647 possessions** (>=3 eligible passes; 0 degenerate team-contexts needed dropping, unlike v1's one). 11,262 of the joined eligible passes (4.5%) were stray-opponent touches excluded from their possession's own stats (v1's project-wide figure was 2.9% on its own, differently-defined eligible population).

| Outcome | n | Fit stat | v2 Decision_z effect | v2 95% CI | v2 p | v1 (published) | v1 95% CI | v1 p |
|---|---|---|---|---|---|---|---|---|
| (a) ends_in_shot (avg. marginal effect) | 26,647 | pseudo-R²=0.0640 | **+0.0575** | [0.0524, 0.0625] | 4.76e-111 | +0.0119 | [0.0055, 0.0184] | 3.0e-4 |
| (b) possession_xg (OLS) | 26,647 | R²=0.0578 | **+0.0152** | [0.0133, 0.0171] | 2.25e-54 | −0.00059 | [−0.00157, 0.00039] | 0.236 |

Engine v2's possession-level effect is positive and dramatically more significant for BOTH outcomes (v1's possession_xg effect was null).

**Under v1's own v2-8.4 claim rule** ("decision quality is associated with chance creation" allowed only if PH-O2 and PH-O3(a) are both positive with CIs excluding zero) — **engine v2 satisfies both conditions** (PH-O2/xG +0.283 [0.164,0.402]; PH-O3(a) +0.0575 [0.0524,0.0625]), a rule v1 failed. This project rule, not a new interpretation, is stated here as a fact about which boxes are checked — no claim about what it means for the paper is made in this task, per the hard rule against interpretation here.

## 4. Deviations from the brief
None from `task-17-engine-v2-validation.md`'s Steps 0-5 or hard rules. Constructions disclosed:
- **Step 1's agreement rule** (4/5 = PROCEED) is my own operationalization of the spec's qualitative "if the model's partial dependence tracks the empirical rates ... If the model inverts where the empirical rates do not." The result (4/5 agreeing, with the one disagreement a weak/non-monotonic empirical signal rather than a clean inversion) is not marginal — a different reasonable threshold would not have changed the PROCEED call.
- **Fill values for scoring the full corpus with the policy model** (Step 2) are recomputed from the full 106M-row corpus, not Task 15's training-subsample-derived values (which were never persisted to disk). This affects only the rare zero-visible-opponent rows' NaN imputation — an imputation constant, not a feature or model change.
- **`possession_share`/zone/pressure shares and `completion_rate`/`progressive_rate`/`xa_per_pass`** use engine v2's own eligible-pass population (`options_ev`'s 250,850 `chosen` rows) rather than v1's `passes_situation.parquet` (part of the withdrawn engine, and a different, matching-reduced population) — the natural, disclosed adaptation for an independent engine, not a specification change to the regression itself.
- **`zone` for engine v2** is computed fresh per pass from `passer_x/y` + that match's own direction lookup (not persisted as a column in Task 15's output), using the project's unchanged defensive/middle/final-thirds convention.

## 5. Problems and surprises
- **Step 1's one disagreement (x=30, defensive third)** is weak and non-monotonic in the empirical data (0.0044 → 0.0051 → 0.0042 → 0.0060 → 0.0065 across quintiles) rather than a clean opposing trend — the model's clear monotonic decrease there is not strongly contradicted, just not strongly confirmed either. This is the zone where "numerical advantage" plausibly means something different (e.g., a spell of deep defensive possession) than in the middle and attacking thirds; not investigated further, per the hard rule against retraining/re-diagnosing in this task.
- **Step 2's diffuseness finding is severe** (median 420.6 of ~423 candidates "effective," 0.9986 correlation between policy-weighted and unweighted mean EV) and is the single most important qualifier on every number in Section 3. It means the behavior-policy model, trained on the same 16-feature candidate set as pass-success, is not sharply distinguishing realistic destinations from the bulk of the grid — consistent with Task 15's own disclosed finding that policy top-1/top-3 accuracy (6.8%/18.8%) was far below chance-adjusted expectations for a genuinely sharp policy. If this diffuseness is taken at face value, Decision in this task is closer to a location/context-quality measure than a "chose better than a realistic alternative" measure — this would invalidate reading Section 3's results as evidence of *behavioral* decision quality specifically, as opposed to *destination* quality, which several of the significant outcome-validation results (Section 3) could equally reflect.
- **Section 3's reversal from v1 (negative) to v2 (positive) is large and consistent across every single specification**, not just directionally but by a wide margin in most cases (e.g. PH-O3(a)'s marginal effect is ~4.8x v1's; PH-O3(b) flips from a null, slightly negative v1 coefficient to a highly significant positive one). Given the diffuseness caveat above, part of this reversal plausibly reflects that engine v2's EV construction (fixing Defect 1's algebraic risk-score problem, and Defect 2's blindness to defenders) now genuinely differentiates good and bad destinations, while a diffuse policy baseline means Decision inherits much of that destination-quality signal directly rather than filtering it through a sharp "what would this player normally do" comparison. Both the fix and the diffuseness caveat are real; this task does not adjudicate how much of the reversal is attributable to each.
- The team-match n (583) matched v1's n exactly by coincidence of dropout count (both dropped 15 of 598), not because the same 15 rows were dropped — engine v2's drop reasons (e.g. any match with zero eligible passes surviving Step 2's filters) were not compared row-by-row against v1's own 15 (which included one team-naming join mismatch specific to v1's pipeline).
- 4.5% of PH-O3's joined eligible passes were stray-opponent-touch exclusions, higher than v1's project-wide 2.9% figure — the two figures are computed on different eligible-pass populations (engine v2's 250,850 vs. v1's 171,618) and are not directly comparable without further work not undertaken here.

## 6. Questions for the research lead
1. Step 2's diffuseness finding (Section 3/5) is severe by both pre-specified criteria. Given it qualifies every number in Section 3, should a future task investigate whether a sharper policy is achievable (e.g. richer features, a different model family) before Section 3's positive outcome-validation results are used to support any claim in the paper? This task's hard rules forbid investigating that here.
2. Section 3's reversal from v1's negative-everywhere result to v2's positive-everywhere result is the most consequential finding across Tasks 15-17. Is a dedicated robustness/diagnostic task warranted before this becomes a headline result (e.g., checking whether the reversal survives under a non-diffuse policy, or under alternative Execution/i+3 windowing choices)?
3. Step 1's x=30 disagreement (Section 5) — worth a dedicated defensive-third diagnostic in a future task, or is one weak, non-monotonic disagreement out of five locations sufficient grounds to close this out as "the model is right, with one unresolved zone"?

## 7. Files produced
- `src/engine_v2/validation_common.py` — ported shared infra (spearman_brown, fit_ols, per_pass_reference_flags, load_matches_meta, zone_of, match_competition_lookup). Committed, commit `ac1e87c`.
- `src/engine_v2/t2_direction_check.py` — Step 1. Committed, commit `ac1e87c`.
- `src/engine_v2/policy_score.py` — Step 2. Committed, commit `ac1e87c`.
- `src/engine_v2/decision_execution_risk.py` — Step 3. Committed, commit `ac1e87c`.
- `src/engine_v2/reliability_t6.py` — Step 4. Committed, commit `ac1e87c`.
- `src/engine_v2/outcome_validation.py` — Step 5. Committed, commit `ac1e87c`.
- `data/engine_v2_step{1,2,3,4,5}_*.json` — step summaries (all numbers in Section 3 come from these). Not committed (data/).
- `data/processed/engine_v2/pass_policy_summary.parquet`, `pass_der.parquet`, `player_season_der.parquet` — per-pass and per-player-season Decision/Execution/Risk tables. Not committed (data/); the per-player-season table carries `player_id` but is never displayed with names or ranked anywhere in this task's output.
- `docs/specs/task-17-engine-v2-validation.md` — the executed task spec, committed alone, commit `f576247`.
- `docs/results/17-engine-v2-validation.md` — this page. Committed, commit `ac1e87c`.

## 8. Confidence
High for Steps 1, 3, 4 (deterministic construction, T6 clears its threshold with a wide margin, the reliability curve is clean and monotonic). Moderate-to-low for Step 5's headline reversal specifically: the regressions themselves are mechanically sound (same specifications, same clustering, same standardization as v1, verified against v1's published numbers spec-by-spec), but Step 2's diffuseness finding is a genuine, severe, pre-specified caveat on what Decision is actually measuring, and this task's hard rules forbid investigating how much of Section 3's reversal is attributable to the EV fix versus the diffuse baseline. The weakest link is exactly this: a positive, highly significant outcome-validation result riding on a Decision metric this task's own Step 2 flagged as possibly not behavioral.
