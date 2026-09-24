# Task 13: Build objectives O2 and O3 (values only)
Date: 2026-09-23
Status: PARTIAL

## 1. Headline
O3's required win-probability function (WP-299) FAILED its pre-registered calibration gate (2 of 100 qualifying buckets off by >10 percentage points, both at a 1-goal lead in the first ~5-10 minutes of the match), so per the standing instruction O3 is UNVALIDATED and was not built at all — no `options_o3.parquet`, no Decision_O3, no Execution_O3. O2 (chance creation) was built successfully: the regression has modest held-out explanatory power (R²=0.138, n=225,460 held-out rows from 60 held-out matches) and its calibration deciles track observed mean xG reasonably well, but ~1.75% of its predictions are negative — an impossible value for accumulated xG. Where both exist, Decision_O1 and Decision_O2 correlate strongly (pass level r=0.824, n=171,618; player level r=0.856, n=2,097 players) but still pick a different best option in 28.9% of passes.

## 2. What I did
Governing spec: `docs/specs/analysis-plan-v3.md` (plan v3 + Amendment v3-1), executed via `docs/specs/task-13-objectives.md`. Single reproducing command: `python src/decision_engine/task13_objectives.py` (writes `data/task13_objectives.json` plus the intermediate files listed in Section 7).

- **Step 0**: committed `docs/specs/analysis-plan-v3.md` alone (commit `194ecd6`), before touching any objective.
- **Preflight**: live memory-pressure check (reusing `task09b_horizon.py`'s gate functions verbatim) — free=57%, available=4.67GB, passed the >=40%/>=3GB preflight gate.
- **Self-check (feature construction)**: verified my combined O2/concede row-builder reproduces `task09_horizon.build_match_rows_horizon`'s already-validated feature columns exactly on 3 sample matches, before trusting it at scale.
- **Row cache**: built one combined per-action-row cache (299/299 matches, 1,136,007 rows) with the frozen `possession_value.py` feature set (`ball_x, ball_y, prev_x, prev_y, time_remaining_period, score_diff, play_pattern_code`) and two new per-row labels computed in the same pass: O2's cumulative shot-xG sum over the next 10 actions (no early break — every shot by the row's own team in the window counts) and the concede model's binary label (1 if the window's first goal is scored by the opponent, mirroring O1's own frozen break-on-first-goal construction). Memory-gated every 50 matches (all checkpoints stayed at 56-63% free, well above the 20%/1.5GB runtime floor).
- **Step 1 (O2 regressor)**: `xgb.XGBRegressor` with the frozen hyperparameters (n_estimators=300, max_depth=5, learning_rate=0.05, subsample=0.8, colsample_bytree=0.8, random_state=42), match-level 80/20 split (239 train / 60 test matches) per the brief's own instruction for this step. Held-out R²=0.1381, MAE=0.01015. Calibration deciles below.
- **Step 2 (concede classifier)**: `xgb.XGBClassifier`, identical frozen hyperparameters to O1, O1's own row-level random split (the brief does not require match-level split here). Held-out AUC=0.8736. Calibration deciles below.
- **Step 3 (WP-299)**: estimated per-minute scoring rates for leading/level/trailing teams from the 299 matches' own goal timestamps (state = the scoring team's own goal-difference sign immediately before that goal; exposure = team-minutes spent in each state, which is why leading and trailing exposure are always numerically identical by construction). Built WP(d, m) via a discretized (1-minute-step) backward Markov recursion — the Poisson-process identity in plan v3 section 2 doesn't specify a computational method, so this is disclosed as my own construction, not an invented methodology. Validated by sampling both teams' (goal-difference, minutes-remaining) state at every integer minute of every match, bucketed by exact d and 5-minute-wide m bins (bucket width not specified in the brief, disclosed here). **Gate FAILED**: 2 of 100 buckets with n>=100 were off by more than 10 percentage points (both at d=+-1, m_bin=85 — i.e. a one-goal lead with 85-89 minutes still remaining, meaning within roughly the first 5-10 minutes of the match). Per the user's explicit instruction, O3 was marked UNVALIDATED and Step 4 did not compute EV_O3/Decision_O3/`options_o3.parquet` at all.
- **Step 4 (recompute EV over all 1,237,611 `options_policy.parquet` rows)**: built a vectorized per-option context (direction, `time_remaining_period`, `score_diff`, `minutes_remaining`), self-checked against a slow per-row rebuild on 3 sample matches before trusting it at scale. Computed EV_O2 for every option (`expected_value.py`'s exact symmetric success/turnover framing, using the O2 regressor's `.predict()` in place of a classifier's `.predict_proba()`), wrote `data/processed/options_o2.parquet`. O3's equivalent step did not run (gate failed). Computed Decision_O2/Execution_O2 via a parametrized copy of `decompose.build_per_pass_table`/`compute_realized_values` (frozen `decompose.py` untouched); computed Decision_O1/Execution_O1 by calling `decompose.build_per_pass_table` directly, unmodified, on the same `options_policy.parquet` (O1's classifier value function is unchanged, so no parametrized copy was needed there). Sanity checks: pass-level and player-level (player_id only, no names, no ranking) correlation of Decision_O1 vs Decision_O2, and the share of passes where the argmax-EV option differs between O1 and O2.

## 3. Numbers

**Step 1 — O2 regressor** (n_train=910,547 rows / 239 matches, n_test=225,460 rows / 60 matches; positive-label rate — label_xg>0 — 4.84% train-set-wide):
- Held-out R² = 0.1381, MAE = 0.01015
- Calibration deciles (bin = predicted-value decile, `n`, mean predicted vs mean actual):

| bin | n | mean_predicted | mean_actual |
|---|---|---|---|
| (-0.29, 0.00118] | 22546 | 0.00032 | 0.00144 |
| (0.00118, 0.00177] | 22549 | 0.00150 | 0.00178 |
| (0.00177, 0.00228] | 22543 | 0.00202 | 0.00223 |
| (0.00228, 0.00277] | 22546 | 0.00253 | 0.00222 |
| (0.00277, 0.00336] | 22546 | 0.00305 | 0.00290 |
| (0.00336, 0.00414] | 22546 | 0.00374 | 0.00296 |
| (0.00414, 0.00546] | 22546 | 0.00472 | 0.00461 |
| (0.00546, 0.00801] | 22546 | 0.00663 | 0.00569 |
| (0.00801, 0.0126] | 22546 | 0.01002 | 0.01045 |
| (0.0126, 2.002] | 22546 | 0.02346 | 0.02250 |

1.75% of held-out predictions are negative (min = -0.289); an impossible value for accumulated xG (see Section 5).

**Step 2 — concede classifier** (n_train=908,805, n_test=227,202; positive rate 0.21%):
- Held-out AUC = 0.8736
- Calibration deciles:

| bin | n | mean_predicted | mean_actual |
|---|---|---|---|
| (-0.0009859, 0.000213] | 22721 | 0.00015 | 0.00004 |
| (0.000213, 0.000312] | 22721 | 0.00026 | 0.00022 |
| (0.000312, 0.000406] | 22719 | 0.00036 | 0.00018 |
| (0.000406, 0.000515] | 22720 | 0.00046 | 0.00018 |
| (0.000515, 0.000658] | 22720 | 0.00058 | 0.00075 |
| (0.000658, 0.000874] | 22720 | 0.00076 | 0.00079 |
| (0.000874, 0.00125] | 22720 | 0.00104 | 0.00110 |
| (0.00125, 0.00208] | 22720 | 0.00160 | 0.00114 |
| (0.00208, 0.00447] | 22720 | 0.00305 | 0.00251 |
| (0.00447, 0.718] | 22721 | 0.01286 | 0.01426 |

**Step 3 — WP-299** (299 matches, goals excluding period-5 shootouts):
- Estimated per-minute scoring rates: leading = 0.019178 goals/team-minute (294 goals / 15,330.2 team-minutes), level = 0.013682 (372 / 27,189.7), trailing = 0.013242 (203 / 15,330.2). Leading and trailing exposure are identical by construction (one team leads exactly when the other trails).
- Grid: d in [-15, 15], m in [0, 128] minutes.
- Validation: 58,232 sampled (team, minute) states, Brier score = 0.1093.
- Gate: **FAILED**. Of 186 total (d, m_bin) buckets, 100 have n>=100; of those, 2 exceed the 10-percentage-point threshold (both d=+-1, m_bin=85, n=234, predicted 77.7%/22.3% vs observed 62.6%/37.4%, off by 15.07pp). The two next-largest gaps among the n>=100 buckets are 5.47pp (m_bin=80) and 4.46pp (m_bin=60) — the failure is concentrated at the single most extreme early-match bucket, not spread across the grid. Full table of all 100 n>=100 buckets (sorted by minutes-remaining bucket, one row per (d, m_bin)):

| d | m_bin | n | mean_predicted | mean_observed | abs_diff_pp |
|---|---|---|---|---|---|
| -3 | 0 | 165 | 0.0000 | 0.0000 | 0.00 |
| -2 | 0 | 287 | 0.0002 | 0.0000 | 0.02 |
| -1 | 0 | 572 | 0.0147 | 0.0210 | 0.62 |
| 0 | 0 | 658 | 0.5000 | 0.5000 | 0.00 |
| 1 | 0 | 572 | 0.9853 | 0.9790 | 0.62 |
| 2 | 0 | 287 | 0.9998 | 1.0000 | 0.02 |
| 3 | 0 | 165 | 1.0000 | 1.0000 | 0.00 |
| -3 | 5 | 156 | 0.0000 | 0.0000 | 0.00 |
| -2 | 5 | 281 | 0.0018 | 0.0000 | 0.18 |
| -1 | 5 | 579 | 0.0434 | 0.0613 | 1.79 |
| 0 | 5 | 716 | 0.5000 | 0.5000 | 0.00 |
| 1 | 5 | 579 | 0.9566 | 0.9387 | 1.79 |
| 2 | 5 | 281 | 0.9982 | 1.0000 | 0.18 |
| 3 | 5 | 156 | 1.0000 | 1.0000 | 0.00 |
| -3 | 10 | 165 | 0.0002 | 0.0000 | 0.02 |
| -2 | 10 | 271 | 0.0049 | 0.0000 | 0.49 |
| -1 | 10 | 590 | 0.0683 | 0.0864 | 1.82 |
| 0 | 10 | 754 | 0.5000 | 0.5000 | 0.00 |
| 1 | 10 | 590 | 0.9317 | 0.9136 | 1.82 |
| 2 | 10 | 271 | 0.9951 | 1.0000 | 0.49 |
| 3 | 10 | 165 | 0.9998 | 1.0000 | 0.02 |
| -3 | 15 | 144 | 0.0006 | 0.0000 | 0.06 |
| -2 | 15 | 245 | 0.0089 | 0.0000 | 0.89 |
| -1 | 15 | 607 | 0.0896 | 0.0923 | 0.26 |
| 0 | 15 | 830 | 0.5000 | 0.5000 | 0.00 |
| 1 | 15 | 607 | 0.9104 | 0.9077 | 0.26 |
| 2 | 15 | 245 | 0.9911 | 1.0000 | 0.89 |
| 3 | 15 | 144 | 0.9994 | 1.0000 | 0.06 |
| -3 | 20 | 111 | 0.0012 | 0.0000 | 0.12 |
| -2 | 20 | 258 | 0.0138 | 0.0078 | 0.60 |
| -1 | 20 | 602 | 0.1080 | 0.1030 | 0.50 |
| 0 | 20 | 886 | 0.5000 | 0.5000 | 0.00 |
| 1 | 20 | 602 | 0.8920 | 0.8970 | 0.50 |
| 2 | 20 | 258 | 0.9862 | 0.9922 | 0.60 |
| 3 | 20 | 111 | 0.9988 | 1.0000 | 0.12 |
| -3 | 25 | 101 | 0.0020 | 0.0000 | 0.20 |
| -2 | 25 | 263 | 0.0189 | 0.0057 | 1.32 |
| -1 | 25 | 613 | 0.1241 | 0.1330 | 0.89 |
| 0 | 25 | 914 | 0.5000 | 0.5000 | 0.00 |
| 1 | 25 | 613 | 0.8759 | 0.8670 | 0.89 |
| 2 | 25 | 263 | 0.9811 | 0.9943 | 1.32 |
| 3 | 25 | 101 | 0.9980 | 1.0000 | 0.20 |
| -3 | 30 | 103 | 0.0030 | 0.0000 | 0.30 |
| -2 | 30 | 246 | 0.0243 | 0.0020 | 2.23 |
| -1 | 30 | 633 | 0.1380 | 0.1501 | 1.21 |
| 0 | 30 | 940 | 0.5000 | 0.5000 | 0.00 |
| 1 | 30 | 633 | 0.8620 | 0.8499 | 1.21 |
| 2 | 30 | 246 | 0.9757 | 0.9980 | 2.23 |
| 3 | 30 | 103 | 0.9970 | 1.0000 | 0.30 |
| -2 | 35 | 254 | 0.0298 | 0.0217 | 0.82 |
| -1 | 35 | 600 | 0.1506 | 0.1625 | 1.19 |
| 0 | 35 | 1030 | 0.5000 | 0.5000 | 0.00 |
| 1 | 35 | 600 | 0.8494 | 0.8375 | 1.19 |
| 2 | 35 | 254 | 0.9702 | 0.9783 | 0.82 |
| -2 | 40 | 263 | 0.0352 | 0.0380 | 0.28 |
| -1 | 40 | 633 | 0.1617 | 0.1588 | 0.30 |
| 0 | 40 | 1036 | 0.5000 | 0.5000 | 0.00 |
| 1 | 40 | 633 | 0.8383 | 0.8412 | 0.30 |
| 2 | 40 | 263 | 0.9648 | 0.9620 | 0.28 |
| -2 | 45 | 201 | 0.0406 | 0.0373 | 0.33 |
| -1 | 45 | 658 | 0.1715 | 0.1588 | 1.27 |
| 0 | 45 | 1150 | 0.5000 | 0.5000 | 0.00 |
| 1 | 45 | 658 | 0.8285 | 0.8412 | 1.27 |
| 2 | 45 | 201 | 0.9594 | 0.9627 | 0.33 |
| -2 | 50 | 171 | 0.0462 | 0.0292 | 1.70 |
| -1 | 50 | 669 | 0.1802 | 0.1816 | 0.15 |
| 0 | 50 | 1234 | 0.5000 | 0.5000 | 0.00 |
| 1 | 50 | 669 | 0.8198 | 0.8184 | 0.15 |
| 2 | 50 | 171 | 0.9538 | 0.9708 | 1.70 |
| -2 | 55 | 150 | 0.0514 | 0.0333 | 1.81 |
| -1 | 55 | 616 | 0.1881 | 0.2208 | 3.26 |
| 0 | 55 | 1404 | 0.5000 | 0.5000 | 0.00 |
| 1 | 55 | 616 | 0.8119 | 0.7792 | 3.26 |
| 2 | 55 | 150 | 0.9486 | 0.9667 | 1.81 |
| -2 | 60 | 110 | 0.0563 | 0.0273 | 2.91 |
| -1 | 60 | 621 | 0.1954 | 0.2399 | 4.46 |
| 0 | 60 | 1490 | 0.5000 | 0.5000 | 0.00 |
| 1 | 60 | 621 | 0.8046 | 0.7601 | 4.46 |
| 2 | 60 | 110 | 0.9437 | 0.9727 | 2.91 |
| -1 | 65 | 563 | 0.2020 | 0.2114 | 0.94 |
| 0 | 65 | 1702 | 0.5000 | 0.5000 | 0.00 |
| 1 | 65 | 563 | 0.7980 | 0.7886 | 0.94 |
| -1 | 70 | 513 | 0.2080 | 0.2251 | 1.72 |
| 0 | 70 | 1858 | 0.5000 | 0.5000 | 0.00 |
| 1 | 70 | 513 | 0.7920 | 0.7749 | 1.72 |
| -1 | 75 | 442 | 0.2135 | 0.2421 | 2.86 |
| 0 | 75 | 2044 | 0.5000 | 0.5000 | 0.00 |
| 1 | 75 | 442 | 0.7865 | 0.7579 | 2.86 |
| -1 | 80 | 333 | 0.2185 | 0.2733 | 5.47 |
| 0 | 80 | 2300 | 0.5000 | 0.5000 | 0.00 |
| 1 | 80 | 333 | 0.7815 | 0.7267 | 5.47 |
| -1 | 85 | 234 | 0.2232 | 0.3739 | **15.07** |
| 0 | 85 | 2508 | 0.5000 | 0.5000 | 0.00 |
| 1 | 85 | 234 | 0.7768 | 0.6261 | **15.07** |
| 0 | 90 | 2534 | 0.5000 | 0.5000 | 0.00 |
| 0 | 95 | 754 | 0.5000 | 0.5000 | 0.00 |
| 0 | 100 | 194 | 0.5000 | 0.5000 | 0.00 |
| 0 | 105 | 158 | 0.5000 | 0.5000 | 0.00 |
| 0 | 110 | 162 | 0.5000 | 0.5000 | 0.00 |
| 0 | 115 | 170 | 0.5000 | 0.5000 | 0.00 |

Full table of all 186 buckets (including n<100) saved to `data/processed/task13_wp_bucket_table.csv`.

**Step 4 — sanity checks** (O1 vs O2 only; O3 not built):
- n passes with both Decision_O1 and Decision_O2 = 171,618; n players (bare player_id) = 2,097.
- Pass-level correlation, Decision_O1 vs Decision_O2: r = 0.8241.
- Player-level correlation (mean Decision per player_id), Decision_O1 vs Decision_O2: r = 0.8558.
- Share of passes where the argmax-EV option differs between O1 and O2: 28.86% (n=171,618).

## 4. Deviations from the brief
1. O2's and the concede model's row-building were combined into a single per-match, per-action-row pass (one scan of the event stream produces both labels) instead of two separate builds. Both need the identical feature/window construction; this is an implementation efficiency, not a change to either target's definition.
2. The O2 regressor's `eval_metric` was set to `"rmse"` rather than reusing the frozen classifier's `"logloss"`, since `logloss` is not defined for a continuous target. All other hyperparameters are unchanged.
3. The WP-299 construction method (discretized 1-minute-step backward Markov recursion) and the validation bucket width (5-minute bins) are my own choices where plan v3 section 2 specifies the identity and gate but not a computational method or bucket granularity.
4. "Minutes remaining" (needed for WP, not used elsewhere) is defined as that match's own last recorded timestamp (excluding period-5 shootouts) minus elapsed time — this handles knockout matches with extra time (18 of the 299 matches have periods 3-5) without a separate rule. Penalty shootouts (period 5) are excluded from goal-rate estimation, validation state sampling, and the option-context build, since no Pass options exist in a shootout and shootout goals aren't part of ordinary run-of-play scoring dynamics.
5. `data/processed/options_o2.parquet`'s columns are the join keys `options_policy.parquet` already uses (match_id, event_id, team, period, candidate_x, candidate_y, chosen) plus O2's own v_success/v_turnover/ev — not a full duplicate of every `options_policy.parquet` column, since p_success and policy_probability are unchanged and available there directly.
6. Player-level correlation in Step 4 pools each objective's per-pass Decision to bare `player_id` only (no names, no ranking, nothing about any individual player printed) — satisfies "no leaderboards, no player names" while still answering the brief's own request for a player-level correlation.
7. `docs/specs/task-13b-wp-corpus.md` (a different, not-yet-run task's spec file, already sitting untracked in the repo) is committed in this task's final batch alongside `task-13-objectives.md`, per CLAUDE.md rule 9's instruction to commit all new files under `docs/` at the end of every task. It is not part of Task 13's own work.

## 5. Problems and surprises
1. **O3 was not built.** The WP-299 calibration gate failed at exactly one location in the grid: a one-goal lead within the first ~5-10 minutes of the match (m_bin=85, n=234), where the model predicts a 77.7% win probability for the leader but the observed rate in the sample is 62.6% — the model is overconfident about early single-goal leads. This is also the smallest of the n>=100 buckets in that (d=+-1) series (the next-lower-minutes bucket, m_bin=80, n=333, is off by only 5.47pp), so it sits right at the edge of the gate's own n>=100 threshold; whether this is a real structural pattern (early goals are less predictive of the final result than a memoryless per-minute rate model assumes) or a small-sample artifact at exactly the wrong bucket is not resolved by this task. Per the standing instruction, this is reported and O3's build is stopped here rather than patched (e.g., by finer state-space granularity, a different bucket width, or excluding that bucket) — any of those would be a methodology change I am not authorized to make.
2. **O2's regressor produces impossible negative values.** 1.75% of held-out predictions are negative, and the calibration table's first decile spans predicted values from -0.289 to 0.00118 — an unconstrained `XGBRegressor` has no floor at zero, while true accumulated xG cannot be negative. This does not appear to distort the reported calibration (the first decile's mean predicted, 0.00032, is still close to its mean actual, 0.00144), but any downstream use of Decision_O2/Execution_O2/EV_O2 inherits this property from the frozen-pipeline choice of an unconstrained regressor. Not corrected here (would be a silent methodology change); flagged as a question below.
3. **Both new targets are heavily imbalanced.** The concede label is positive in only 0.21% of action-state rows (1,930 of ~908,805 training rows), and O2's label is nonzero in only 4.84% of rows. The concede model's AUC (0.8736) is a reasonable discrimination measure under imbalance, but with under 2,000 positive training examples its estimated probabilities in the sparse tail (the calibration table's top decile) carry more sampling uncertainty than the smooth-looking decile table alone suggests.
4. Nothing was found broken in the reused frozen machinery (`possession_value.py`, `pitch_direction.py`, `decompose.build_per_pass_table`) — both self-checks (feature construction against `task09_horizon.build_match_rows_horizon`, and the vectorized option-context build against a slow per-row rebuild) passed exactly on their sample matches before being trusted at full scale.

## 6. Questions for the research lead
1. O3's WP-299 gate failure is concentrated in exactly one bucket at the edge of the n>=100 threshold (Section 5.1). Is Task 13b's corpus-based WP alternative (already specced, a separate task) the intended next step, or does this specific failure pattern (early-match, modest-lead states) suggest the three-state (leading/level/trailing) construction itself is too coarse regardless of which corpus estimates the rates? I am not proposing either as a fix — this is a question about which direction is worth pursuing, not a request to patch O3 now.
2. Is O2's ~1.75%-negative-prediction property (Section 5.2) acceptable to use as-is for Task 14's comparisons, or should Decision_O2/EV_O2 be clipped/floored before further use? Either choice changes O2's values, so I did not decide this myself.
3. `options_o2.parquet`'s minimal key-column design (Section 4.5) may not carry everything Task 14 needs. Please confirm the column set is sufficient, or tell me what to add, before Task 14 re-joins it.

## 7. Files produced
- `src/decision_engine/task13_objectives.py` — this task's full implementation (row-builder, O2 regressor, concede classifier, WP-299 construction/validation, EV/Decision/Execution recomputation, sanity checks). Committed.
- `docs/specs/analysis-plan-v3.md` — plan v3 + Amendment v3-1. Committed separately at Step 0, commit `194ecd6`.
- `docs/specs/task-13-objectives.md`, `docs/specs/task-13b-wp-corpus.md` — this task's own spec, and a different future task's spec already sitting in the repo (Section 4.7). Committed.
- `docs/results/13-objectives.md` — this page. Committed.
- `data/processed/task13_o2_concede_parts/*.parquet` (299 files) — cached per-match action-state rows with both new labels. Not committed (data/).
- `data/processed/o2_value_model.json` — trained O2 XGBRegressor. Not committed.
- `data/processed/concede_model.json` — trained concede XGBClassifier. Not committed.
- `data/processed/options_o2.parquet` — EV_O2/v_success/v_turnover for all 1,237,611 options. Not committed.
- `data/processed/options_o3.parquet` — **not written** (WP gate failed).
- `data/processed/task13_wp_bucket_table.csv` — full 186-row WP validation bucket table. Not committed.
- `data/task13_objectives.json` — full machine-readable summary (all numbers in this page trace back to it). Not committed.

## 8. Confidence
O2's numbers (R², MAE, calibration, AUC-equivalent correlation checks) are as trustworthy as the rest of this project's frozen pipeline — same features, same hyperparameters, same symmetric EV construction, two independent self-checks passed before trusting the new code at scale. The weakest link is O3: it does not exist as a validated object in this task, and the one bucket that sank it is also the smallest bucket in its own local neighborhood, so I cannot say with confidence whether a corpus-sized WP estimate (Task 13b) would pass or fail the same gate. Decision_O1-vs-Decision_O2 correlations (0.82 pass-level, 0.86 player-level) are on the full eligible-pass population (171,618 passes, 2,097 players), not a subsample, so those numbers are not sample-size-limited, but they say nothing about which objective is "right" — that is Task 14's referee tests, not this task's.
