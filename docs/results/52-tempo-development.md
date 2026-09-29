# Task 52: Freeze v9, lock a development/replication split, develop tempo measures (incl. Amendment A)
Date: 2026-09-29
Status: COMPLETE (every step run on the DEVELOPMENT half; deviations in Section 4. Several study-sample deep-midfielder cells rest on 15-16 players.)

**Development half only. The REPLICATION half was not opened.**
- Every per-match file was opened through a guard that asserts its match id is in `docs/splits/tempo_split.csv`'s DEVELOPMENT half. A test call on a replication id was refused.
- Existing comparators and controls were read with a development match-id filter, per Clarification B. Each read is listed in Section 2.

Holdout and reserved data untouched. Datasets and uses:
- 2015/16 development leagues: further use after Tasks 44-47, 50 and 51.
- Study development half: study sample, as usual.

Report only: nothing on this page is gated.

## Checklist
| Section | Status |
|---|---|
| Step 0: brief, Amendment A, Clarification B committed by the research lead | COMPLETE (b098ffe; 049972a; 88b99fe) |
| Step 1: BENCHMARK v9 snapshot, manifest, tag | COMPLETE (53b48a9; tag `benchmark-v9`, not pushed). W 2015/16, W study and study tempo residuals with ids written to disk first |
| Step 2: split locked and committed before any tempo computation | COMPLETE (af9eaf1) |
| Step 3: time on ball, g_T, comparison with the existing time on ball | COMPLETE |
| Step 4: M1, M2 (+1.0 / 2.0 s), M3_speed, M3_var | COMPLETE |
| Amendment A: pass categories, M4 (ACCEL, KEEP, SLOW, SWITCH), M5, M6 (+ on ACCEL / SLOW) | COMPLETE |
| Step 5 / Amendment tests: D1, D2, D3, D4, D5 | COMPLETE (D2's DM subgroup has 2-4 players; A-i run only where >= 15 movers) |
| Step 6: K1 (raw + disattenuated r, bootstrap CIs, PC1 share), K2 | COMPLETE (study K1 disattenuation undefined where a D1 reliability <= 0) |
| Memory gate (Task 25) | COMPLETE (builder: 57% / 4.8 GB, 56% / 4.6 GB; tests: 48% / 4.28 GB, 46% / 3.75 GB) |

## 1. Headline
The study-sample deep-midfielder cells rest on small groups:
- K2 study: 15 players (the DMs meeting the PR2_flag_keep floor).
- D4 / K1 study pairs involving PR2_flag_keep or M2: 15-16 players.
- D2's DM subgroup: 2-4 players.

On the study development half, the D1 within-DM reliabilities are near or below zero for M1 (-0.015), M5 (0.038), M4_SLOW (0.091), PR2_flag_keep (-0.013) and v5 Decision (-0.213), across 40-42 players. Several disattenuated K1 correlations therefore fall far outside [-1, 1].

On the 2015/16 development leagues (43 DMs), D1 is:
- M4_ACCEL 0.907, M3_speed 0.849, M2 0.715;
- M6 0.260;
- MOVE_ON_SPEED 0.567 and PR2_flag_keep 0.615 on this half.

## 2. What I did
Reproduce with (from `src/engine_v2/`):
1. `python task52_snapshot.py`
2. `python task52_split.py`
3. `python -W ignore task52_build.py`
4. `python -W ignore task52_tests.py`

- **Step 1.**
  - Wrote the tables that existed only in memory:
    - `task52_w_1516.parquet` / `task52_w_study.parquet` via `task46_part_b.fit_w`, reproducing Task 46 exactly: n 1,158,231 / AUC 0.6289478647 and n 271,830 / AUC 0.6134970381.
    - `tempo_task52_study_{move,hold}_residuals_ids.parquet` via Task 39's recipe, with `rm.main` redirected to a temporary folder; asserted identical to the v2 residuals.
  - Copied 16 files into `data/benchmark_v9/` and wrote `docs/benchmark/manifest-v9.txt`. The manifest records that Task 50 wrote no per-unit tables (JSON only).
  - Commit 53b48a9, then tag `benchmark-v9`.
- **Step 2.** `docs/splits/tempo_split.csv` (1,843 rows), from match metadata only.
  - 2015/16 DEVELOPMENT = Premier League 380 + Bundesliga 34 = 414 matches; REPLICATION = 1,137.
  - Study DEVELOPMENT = 143 of 292. By competition-season: Ligue 1 21/22 13, Ligue 1 22/23 15, Bundesliga 23/24 15, La Liga 20/21 17, WC 2022 32, MLS 2023 1, Euro 2020 25, Euro 2024 25.
  - Committed as af9eaf1 before any tempo code ran.
- **Steps 3-4 and Amendment A** (`task52_build.py`): per development match, from raw events, frames and the EV grid only. Definitions are in the module docstring. In summary:
  - **Spell.** From each completed Ball Receipt*, walk forward to the receiver's next Pass. Spells are excluded for a receiver Shot, a loss (receiver Miscontrol / Dispossessed / incomplete Dribble, or a possession change), any foul event, a period end, or another player's on-ball event. Keep 0 < T <= 15.
  - **g_T.** Cross-fitted `XGBRegressor` (Task 35's settings) of log T on:
    - reception x, y; play pattern; the receipt's under_pressure; period; minute; score difference;
    - study only: visible opponents within 10 u of the receiver.
    - It uses 5 development match folds, seed 20260929. r = log T - g_T_oof.
  - **M1 OPENING.** From the receipt's freeze frame, as in the brief. "Nearer the opponent goal" is read as distance to (120, 40). The receiver's location is the frame's actor where present.
  - **M2.** Units are pressured completed receptions (Task 44 flag rule via `task44_gate.receipt_flags`). FK = the spell ends in his completed Pass at T <= 1.5 s (also 1.0 and 2.0). Baseline: cross-fitted `XGBClassifier` (Task 42's settings) on the same context.
  - **Pass categories** on eligible passes:
    - 2015/16: `task44_build.eligible_passes`.
    - Study: the pass ids in each development match's `options_ev_v4` file.
    - One classifier per category on origin context.
  - **M5.** Restricted set = `policy_score_v8`'s filters (p_success >= 0.05, distance_u <= 45, not `offside_v4`, recomputed per development match). OPPORTUNITY = best EV among candidates with forward_progress_u >= 15 exceeds the best EV among the rest.
  - **M6.** Completed eligible passes. V_before / V_after use the team's 3rd previous / 3rd subsequent on-ball event (Pass, Ball Receipt*, Carry, Dribble, Shot) in the possession. Baseline: `XGBRegressor` on origin context + V_before.
  - **Outcomes.** Y_F3 (`task42_outcomes`), POSS_XG (`task50_puzzle.match_outcomes`) and keep_spell (`task43_spells`), all from the same development raw events.
- **Tests** (`task52_tests.py`):
  - **Player values** use each measure's formula and floor, from per-(player, match) sums. This makes D1 halves and the other-match S used by D3 and K2 exact.
  - **D1:** Task 38's R1 (100 random halves of a player's matches, Spearman-Brown median, seed 20260928), with the measure's own formula applied per half.
  - **D2:** `task46_part_a.disattenuated`.
  - **D3:** `task35_ptest.fe_fit`, with g cross-fitted on development folds:
    - 2015/16: event-only `task44_build.G_FEATURES`.
    - Study: Task 35 / 42's `F_STATE_FEATURES`.
  - **D4:** Pearson r with Fisher CIs.
  - **D5:** `task41_lists_availability.perm_test`.
  - **K1:** 1,000-player bootstrap.
  - **K2:** `task41_ptest_vetting.fit_multi`.
  - **DM groups:**
    - 2015/16: Task 44's rule (`task44_build` lines 165-172) on development eligible passes gives 43.
    - Study: Task 27's 111 restricted to players with development eligible passes gives 106.
    - Role FE / perm_test roles use the same position-share rule on development passes.

**Existing-table reads (Clarification B).** Each was read with a pyarrow filter `match_id in DEVELOPMENT ids`, then re-filtered in pandas, keeping existing baselines:
- `data/processed/engine_v2/task44_receptions.parquet` — filter: match_id in 2015/16 DEVELOPMENT ids (414); rows kept 304,598
- `data/processed/engine_v2/task52_w_1516.parquet` — filter: match_id in 2015/16 DEVELOPMENT ids (414); rows kept 304,598
- `data/processed/tempo_task44_move_residuals_ids.parquet` — filter: match_id in 2015/16 DEVELOPMENT ids (414); rows kept 172,822
- `data/processed/tempo_task44_hold_residuals_ids.parquet` — filter: match_id in 2015/16 DEVELOPMENT ids (414); rows kept 215,529
- `data/processed/engine_v2/task46_study_pr_flag.parquet` — filter: match_id in study DEVELOPMENT ids (143); rows kept 29,124
- `data/processed/engine_v2/task52_w_study.parquet` — filter: match_id in study DEVELOPMENT ids (143); rows kept 131,539
- `data/processed/tempo_task52_study_move_residuals_ids.parquet` — filter: match_id in study DEVELOPMENT ids (143); rows kept 84,708
- `data/processed/tempo_task52_study_hold_residuals_ids.parquet` — filter: match_id in study DEVELOPMENT ids (143); rows kept 98,783
- `data/processed/engine_v2/pass_der_crossfit_v5.parquet` — filter: match_id in study DEVELOPMENT ids (143); rows kept 120,927
- `data/processed/engine_v2/value_model_rows_v5.parquet` — filter: match_id in study DEVELOPMENT ids (143); rows kept 400,913
- `data/processed/tempo_task44_time_on_ball.parquet` / `tempo_time_on_ball.parquet`: the existing time on ball, for the Step 3 comparison, with the same filter.
- Player-level tables (not match rows): `task44_roles.parquet` (`player_name` only, for D5) and `leaderboard_v5c.parquet` (`player_name`, `is_deep_midfield`).

## 3. Numbers
Units for D3 / K2: coefficient per SD of the other-match S, x100 (per 100 units). For Y_F3 that is percentage points of the probability; for POSS_XG it is xG.
### Step 3 and unit counts

| Dataset | dev matches | completed receptions | timed (0<T<=15) | T median [q25, q75] s | T<=0 excluded | T>15 excluded | g_T OOF R^2 | corr with existing time-on-ball (n joined) | pressured receptions (M2) | eligible passes | M6 units | M6 baseline OOF R^2 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2015/16 | 414 | 304,598 | 227,504 | 1.29 [0.67, 2.29] | 37,434 | 109 | 0.047 | r 1.0000, mean abs diff 0 (181,930) | 85,653 | 340,865 | 190,198 | -0.373 |
| study | 143 | 131,539 | 106,779 | 1.33 [0.76, 2.34] | 11,909 | 18 | 0.129 | r 1.0000, mean abs diff 0 (87,797) | 30,202 | 120,927 | 82,258 | -0.285 |

Spell end reasons: 2015/16: pass 265,047, loss 25,397, shot 7,739, foul 5,136, other_on_ball 1,058, period_end 221; study: pass 118,706, loss 7,789, shot 2,733, foul 1,985, other_on_ball 293, period_end 33

Baseline fit: 2015/16: FK AUC 1.0/1.5/2.0 s = 0.638/0.610/0.604 (base rates 0.155/0.232/0.284); M4 AUC ACCEL 0.657, KEEP 0.587, SLOW 0.611, SWITCH 0.660; study: FK AUC 1.0/1.5/2.0 s = 0.643/0.622/0.616 (base rates 0.187/0.280/0.341); M4 AUC ACCEL 0.636, KEEP 0.613, SLOW 0.663, SWITCH 0.636

Study: OPENING share among timed receptions with a freeze frame = 0.484 (n 95,539); OPPORTUNITY share among eligible passes = 0.625.

### Pass categories (share of eligible passes)

| Dataset | group | ACCEL | KEEP | SLOW | SWITCH |
|---|---|---|---|---|---|
| 2015/16 | all | 0.204 | 0.540 | 0.231 | 0.024 |
| 2015/16 | DM | 0.185 | 0.575 | 0.214 | 0.027 |
| study | all | 0.149 | 0.572 | 0.258 | 0.021 |
| study | DM | 0.132 | 0.596 | 0.250 | 0.022 |

### 2015/16 development leagues (PL + Bundesliga; 2015/16 further use) — DM group n = 43

**D1 stability (Task 38's method, per-half formula; players >= 10 matches) and players meeting each floor.**

| Measure | DM: n players, median [p5, p95] | all: n players, median [p5, p95] | players meeting floor (all / DM) |
|---|---|---|---|
| M2 | 43, 0.715 [0.599, 0.801] | 407, 0.707 [0.663, 0.743] | 378 / 43 |
| M2_1.0 | 43, 0.666 [0.532, 0.776] | 407, 0.661 [0.597, 0.708] | 378 / 43 |
| M2_2.0 | 43, 0.655 [0.511, 0.759] | 407, 0.711 [0.657, 0.752] | 378 / 43 |
| M3_speed | 43, 0.849 [0.790, 0.895] | 416, 0.831 [0.804, 0.851] | 412 / 43 |
| M3_var | 43, 0.674 [0.538, 0.790] | 416, 0.833 [0.811, 0.853] | 412 / 43 |
| M4_ACCEL | 43, 0.907 [0.871, 0.933] | 390, 0.893 [0.877, 0.909] | 431 / 43 |
| M4_KEEP | 43, 0.890 [0.837, 0.927] | 390, 0.763 [0.726, 0.800] | 431 / 43 |
| M4_SLOW | 43, 0.862 [0.803, 0.912] | 390, 0.874 [0.843, 0.895] | 431 / 43 |
| M4_SWITCH | 43, 0.735 [0.596, 0.821] | 390, 0.709 [0.653, 0.755] | 431 / 43 |
| M6 | 43, 0.260 [0.058, 0.444] | 382, 0.170 [0.123, 0.241] | 372 / 43 |
| M6_on_ACCEL | 42, 0.507 [0.323, 0.667] | 284, 0.179 [0.093, 0.259] | 57 / 12 |
| M6_on_SLOW | 43, 0.403 [0.192, 0.618] | 363, 0.292 [0.221, 0.367] | 221 / 38 |
| PR2_flag_keep | 43, 0.615 [0.450, 0.745] | 405, 0.765 [0.724, 0.791] | 369 / 43 |
| W | 43, 0.826 [0.766, 0.886] | 419, 0.912 [0.899, 0.922] | 445 / 43 |
| MOVE_ON_SPEED | 43, 0.567 [0.333, 0.710] | 381, 0.642 [0.560, 0.688] | 285 / 42 |
| HOLD_VARIATION | 43, 0.816 [0.749, 0.874] | 386, 0.784 [0.753, 0.817] | 327 / 43 |

**D3 P-test (per 100 units per SD of other-match S; receptions for M1-M3, passes for M4-M6).**

| Measure | group | outcome | coef | 95% CI | p | n rows / players | control coef (p) | dummy check within / dummies |
|---|---|---|---|---|---|---|---|---|
| M2 | DM | y_f3 | +0.0297 | [-0.4636, +0.5230] | 0.906 | 34,459 / 43 | +2.268 (7.2e-20) | +0.00761 / +0.00761 |
| M2 | DM | poss_xg | +0.1158 | [+0.0163, +0.2154] | 0.0226 | 41,225 / 43 | +2.224 (1.4e-28) | +0.00059 / +0.00059 |
| M2 | all | y_f3 | +0.3698 | [+0.0442, +0.6954] | 0.026 | 187,856 / 370 | +6.940 (8.4e-152) | +0.01223 / +0.01223 |
| M2 | all | poss_xg | +0.0019 | [-0.0282, +0.0321] | 0.899 | 267,335 / 370 | +7.580 (3.9e-190) | +0.00027 / +0.00027 |
| M3_speed | DM | y_f3 | -0.2745 | [-0.9752, +0.4261] | 0.443 | 34,765 / 43 | +2.291 (1.6e-19) | +0.01066 / +0.01066 |
| M3_speed | DM | poss_xg | +0.0386 | [-0.0390, +0.1163] | 0.329 | 41,563 / 43 | +2.238 (7.5e-28) | +0.00099 / +0.00099 |
| M3_speed | all | y_f3 | -0.1076 | [-0.4085, +0.1933] | 0.483 | 203,593 / 411 | +6.881 (2.8e-156) | +0.01292 / +0.01292 |
| M3_speed | all | poss_xg | -0.0370 | [-0.0684, -0.0056] | 0.0208 | 283,397 / 411 | +7.518 (4.5e-193) | -0.00076 / -0.00076 |
| M3_var | DM | y_f3 | -0.2843 | [-0.8142, +0.2456] | 0.293 | 34,765 / 43 | +2.291 (1.6e-19) | -0.01147 / -0.01147 |
| M3_var | DM | poss_xg | -0.0261 | [-0.0925, +0.0403] | 0.441 | 41,563 / 43 | +2.238 (7.5e-28) | -0.00272 / -0.00272 |
| M3_var | all | y_f3 | -0.3131 | [-0.7217, +0.0956] | 0.133 | 203,593 / 411 | +6.881 (2.8e-156) | +0.00788 / +0.00788 |
| M3_var | all | poss_xg | -0.0323 | [-0.0753, +0.0106] | 0.14 | 283,397 / 411 | +7.518 (4.5e-193) | -0.00165 / -0.00165 |
| M4_ACCEL | DM | y_f3 | +0.2727 | [-0.3213, +0.8667] | 0.368 | 44,038 / 43 | +2.773 (5.5e-44) | +0.03039 / +0.03039 |
| M4_ACCEL | DM | poss_xg | +0.0455 | [-0.0225, +0.1136] | 0.19 | 52,358 / 43 | +2.936 (4.7e-39) | +0.00076 / +0.00076 |
| M4_ACCEL | all | y_f3 | +0.6118 | [+0.3037, +0.9198] | 9.93e-05 | 242,102 / 412 | +4.198 (2e-151) | +0.00574 / +0.00574 |
| M4_ACCEL | all | poss_xg | +0.0264 | [-0.0019, +0.0548] | 0.0678 | 323,517 / 412 | +4.620 (3.3e-231) | +0.00083 / +0.00083 |
| M4_SLOW | DM | y_f3 | -0.0383 | [-0.4449, +0.3683] | 0.854 | 44,038 / 43 | +2.773 (5.5e-44) | -0.01044 / -0.01044 |
| M4_SLOW | DM | poss_xg | -0.0053 | [-0.0654, +0.0548] | 0.862 | 52,358 / 43 | +2.936 (4.7e-39) | -0.00052 / -0.00052 |
| M4_SLOW | all | y_f3 | -0.5654 | [-0.8876, -0.2431] | 0.000584 | 242,102 / 412 | +4.198 (2e-151) | -0.00339 / -0.00339 |
| M4_SLOW | all | poss_xg | -0.0230 | [-0.0544, +0.0085] | 0.152 | 323,517 / 412 | +4.620 (3.3e-231) | -0.00108 / -0.00108 |
| M4_SWITCH | DM | y_f3 | +0.5307 | [-0.1778, +1.2393] | 0.142 | 44,038 / 43 | +2.773 (5.5e-44) | +0.01549 / +0.01549 |
| M4_SWITCH | DM | poss_xg | -0.0410 | [-0.1096, +0.0275] | 0.241 | 52,358 / 43 | +2.936 (4.7e-39) | +0.00165 / +0.00165 |
| M4_SWITCH | all | y_f3 | +0.5437 | [+0.2759, +0.8116] | 6.93e-05 | 242,102 / 412 | +4.198 (2e-151) | -0.00687 / -0.00687 |
| M4_SWITCH | all | poss_xg | +0.0134 | [-0.0080, +0.0347] | 0.22 | 323,517 / 412 | +4.620 (3.3e-231) | +0.00041 / +0.00041 |
| M6 | DM | y_f3 | +0.2016 | [-0.0395, +0.4426] | 0.101 | 44,028 / 43 | +2.772 (2.4e-45) | -0.01753 / -0.01753 |
| M6 | DM | poss_xg | -0.0471 | [-0.0732, -0.0210] | 0.000411 | 52,347 / 43 | +2.925 (7.4e-39) | +0.00009 / +0.00009 |
| M6 | all | y_f3 | +0.0115 | [-0.1948, +0.2178] | 0.913 | 236,842 / 371 | +4.170 (2.3e-146) | -0.00781 / -0.00781 |
| M6 | all | poss_xg | +0.0049 | [-0.0181, +0.0279] | 0.676 | 315,772 / 371 | +4.636 (5.8e-221) | -0.00007 / -0.00007 |

**D4 within-DM correlations (player values, dev units, floors applied).**

| Measure | vs PR2_flag_keep | vs W | vs MOVE_ON_SPEED | vs HOLD_VARIATION |
|---|---|---|---|---|
| M2 | 0.340 [+0.04, +0.58] n 43 | -0.394 [-0.62, -0.11] n 43 | 0.025 [-0.28, +0.33] n 42 | -0.481 [-0.68, -0.21] n 43 |
| M2_1.0 | 0.242 [-0.06, +0.51] n 43 | -0.241 [-0.50, +0.06] n 43 | -0.016 [-0.32, +0.29] n 42 | -0.515 [-0.71, -0.25] n 43 |
| M2_2.0 | 0.412 [+0.13, +0.63] n 43 | -0.389 [-0.62, -0.10] n 43 | -0.010 [-0.31, +0.30] n 42 | -0.526 [-0.71, -0.27] n 43 |
| M3_speed | -0.224 [-0.49, +0.08] n 43 | -0.233 [-0.50, +0.07] n 43 | 0.192 [-0.12, +0.47] n 42 | -0.693 [-0.82, -0.50] n 43 |
| M3_var | -0.312 [-0.56, -0.01] n 43 | 0.101 [-0.21, +0.39] n 43 | 0.105 [-0.21, +0.40] n 42 | -0.070 [-0.36, +0.24] n 43 |
| M4_ACCEL | -0.475 [-0.68, -0.20] n 43 | 0.087 [-0.22, +0.38] n 43 | 0.214 [-0.10, +0.49] n 42 | 0.059 [-0.25, +0.35] n 43 |
| M4_KEEP | 0.250 [-0.05, +0.51] n 43 | -0.262 [-0.52, +0.04] n 43 | -0.276 [-0.54, +0.03] n 42 | -0.134 [-0.42, +0.17] n 43 |
| M4_SLOW | 0.235 [-0.07, +0.50] n 43 | 0.291 [-0.01, +0.54] n 43 | 0.134 [-0.18, +0.42] n 42 | 0.113 [-0.19, +0.40] n 43 |
| M4_SWITCH | -0.041 [-0.34, +0.26] n 43 | -0.186 [-0.46, +0.12] n 43 | 0.045 [-0.26, +0.34] n 42 | -0.031 [-0.33, +0.27] n 43 |
| M6 | 0.112 [-0.19, +0.40] n 43 | -0.108 [-0.40, +0.20] n 43 | 0.060 [-0.25, +0.36] n 42 | -0.207 [-0.48, +0.10] n 43 |
| M6_on_ACCEL | 0.069 [-0.53, +0.62] n 12 | 0.069 [-0.53, +0.62] n 12 | -0.223 [-0.71, +0.40] n 12 | 0.122 [-0.49, +0.65] n 12 |
| M6_on_SLOW | -0.250 [-0.53, +0.08] n 38 | -0.175 [-0.47, +0.15] n 38 | 0.201 [-0.13, +0.49] n 38 | 0.008 [-0.31, +0.33] n 38 |

**D5 praised list (Task 41's list and perm_test).**

| Measure | declared direction | n qualifying | n present | T | p (two-sided) | present |
|---|---|---|---|---|---|---|
| M2 | higher | 359 | 1 | +0.554 | 0.535 | Kevin De Bruyne |
| M2_1.0 | none | 359 | 1 | +0.745 | 0.441 | Kevin De Bruyne |
| M2_2.0 | none | 359 | 1 | +0.720 | 0.479 | Kevin De Bruyne |
| M3_speed | none | 386 | 1 | +0.907 | 0.329 | Kevin De Bruyne |
| M3_var | none | 386 | 1 | -0.153 | 0.758 | Kevin De Bruyne |
| M4_ACCEL | none | 431 | 3 | +0.256 | 0.64 | Kevin De Bruyne, Granit Xhaka, Siem Stefan de Jong |
| M4_KEEP | none | 431 | 3 | +0.579 | 0.301 | Kevin De Bruyne, Granit Xhaka, Siem Stefan de Jong |
| M4_SLOW | none | 431 | 3 | -0.878 | 0.125 | Kevin De Bruyne, Granit Xhaka, Siem Stefan de Jong |
| M4_SWITCH | none | 431 | 3 | +0.672 | 0.22 | Kevin De Bruyne, Granit Xhaka, Siem Stefan de Jong |
| M6 | none | 372 | 1 | -0.333 | 0.726 | Kevin De Bruyne |
| M6_on_ACCEL | none | — | 0 | — | — | none |
| M6_on_SLOW | none | 221 | 1 | -0.429 | 0.605 | Kevin De Bruyne |

### study sample development half (as usual) — DM group n = 106

**D1 stability (Task 38's method, per-half formula; players >= 4 matches) and players meeting each floor.**

| Measure | DM: n players, median [p5, p95] | all: n players, median [p5, p95] | players meeting floor (all / DM) |
|---|---|---|---|
| M2 | 40, 0.166 [-0.149, 0.438] | 270, 0.491 [0.426, 0.568] | 109 / 16 |
| M2_1.0 | 40, 0.267 [-0.090, 0.540] | 270, 0.441 [0.333, 0.525] | 109 / 16 |
| M2_2.0 | 40, 0.159 [-0.221, 0.462] | 270, 0.509 [0.441, 0.567] | 109 / 16 |
| M3_speed | 42, 0.385 [0.090, 0.584] | 292, 0.599 [0.538, 0.657] | 229 / 39 |
| M3_var | 42, 0.232 [-0.075, 0.485] | 292, 0.613 [0.541, 0.669] | 229 / 39 |
| M4_ACCEL | 42, 0.513 [0.423, 0.683] | 274, 0.502 [0.353, 0.578] | 270 / 51 |
| M4_KEEP | 42, 0.400 [0.157, 0.571] | 274, 0.409 [0.306, 0.497] | 270 / 51 |
| M4_SLOW | 42, 0.091 [-0.202, 0.339] | 274, 0.515 [0.435, 0.579] | 270 / 51 |
| M4_SWITCH | 42, 0.632 [0.415, 0.734] | 274, 0.400 [0.326, 0.470] | 270 / 51 |
| M6 | 42, 0.361 [-0.150, 0.502] | 270, 0.098 [-0.001, 0.192] | 169 / 36 |
| M6_on_ACCEL | 27, 0.085 [-0.275, 0.363] | 155, -0.340 [-1.292, 0.050] | 6 / 2 |
| M6_on_SLOW | 40, 0.039 [-0.453, 0.338] | 249, 0.147 [0.024, 0.283] | 35 / 5 |
| PR2_flag_keep | 40, -0.013 [-0.554, 0.341] | 268, 0.484 [0.411, 0.558] | 102 / 15 |
| W | 42, 0.675 [0.553, 0.774] | 295, 0.797 [0.778, 0.825] | 302 / 48 |
| MOVE_ON_SPEED | 41, 0.254 [-0.018, 0.437] | 267, 0.404 [0.264, 0.501] | 83 / 14 |
| HOLD_VARIATION | 42, 0.479 [0.258, 0.683] | 272, 0.518 [0.455, 0.571] | 94 / 17 |
| M1 | 42, -0.015 [-0.623, 0.358] | 291, 0.250 [-0.028, 0.415] | 197 / 51 |
| M5 | 42, 0.038 [-0.213, 0.255] | 274, 0.023 [-0.091, 0.161] | 264 / 52 |
| Decision | 42, -0.213 [-0.559, 0.125] | 274, 0.441 [0.352, 0.533] | 270 / 51 |

**D3 P-test (per 100 units per SD of other-match S; receptions for M1-M3, passes for M4-M6).**

| Measure | group | outcome | coef | 95% CI | p | n rows / players | control coef (p) | dummy check within / dummies |
|---|---|---|---|---|---|---|---|---|
| M2 | DM | y_f3 | +1.7475 | [+1.1845, +2.3106] | 1.18e-09 | 7,000 / 15 | +0.589 (0.61) | +0.01314 / +0.01314 |
| M2 | DM | poss_xg | +0.0996 | [-0.3734, +0.5726] | 0.68 | 8,581 / 15 | +0.131 (0.88) | -0.00915 / -0.00915 |
| M2 | all | y_f3 | -0.0774 | [-0.6824, +0.5277] | 0.802 | 33,826 / 97 | +4.671 (3.1e-18) | -0.00868 / -0.00868 |
| M2 | all | poss_xg | -0.0642 | [-0.2162, +0.0878] | 0.408 | 47,335 / 97 | +4.890 (3.1e-18) | -0.00063 / -0.00063 |
| M3_speed | DM | y_f3 | -0.6059 | [-1.9301, +0.7183] | 0.37 | 10,192 / 35 | +1.557 (7.4e-05) | -0.00319 / -0.00319 |
| M3_speed | DM | poss_xg | -0.1939 | [-0.4084, +0.0206] | 0.0764 | 12,500 / 35 | +0.907 (0.024) | -0.00146 / -0.00146 |
| M3_speed | all | y_f3 | -0.3844 | [-0.8531, +0.0843] | 0.108 | 51,706 / 194 | +3.917 (9.4e-24) | -0.00300 / -0.00300 |
| M3_speed | all | poss_xg | +0.0190 | [-0.0565, +0.0945] | 0.622 | 67,332 / 194 | +4.255 (8.9e-24) | +0.00146 / +0.00146 |
| M3_var | DM | y_f3 | -0.3551 | [-2.1622, +1.4520] | 0.7 | 10,192 / 35 | +1.557 (7.4e-05) | +0.01160 / +0.01160 |
| M3_var | DM | poss_xg | -0.3768 | [-0.5703, -0.1833] | 0.000135 | 12,500 / 35 | +0.907 (0.024) | -0.00261 / -0.00261 |
| M3_var | all | y_f3 | -0.0788 | [-0.7609, +0.6033] | 0.821 | 51,706 / 194 | +3.917 (9.4e-24) | +0.00918 / +0.00918 |
| M3_var | all | poss_xg | +0.1033 | [-0.0006, +0.2071] | 0.0513 | 67,332 / 194 | +4.255 (8.9e-24) | +0.00177 / +0.00177 |
| M4_ACCEL | DM | y_f3 | +0.4812 | [-0.7738, +1.7362] | 0.452 | 10,852 / 43 | +1.080 (0.14) | -0.00356 / -0.00356 |
| M4_ACCEL | DM | poss_xg | +0.1073 | [-0.1672, +0.3818] | 0.444 | 13,470 / 43 | +0.480 (0.47) | -0.00588 / -0.00588 |
| M4_ACCEL | all | y_f3 | +0.6930 | [+0.1939, +1.1921] | 0.0065 | 51,001 / 223 | +1.684 (3.3e-13) | +0.00440 / +0.00440 |
| M4_ACCEL | all | poss_xg | +0.0169 | [-0.0537, +0.0876] | 0.638 | 67,151 / 223 | +1.899 (2.2e-11) | +0.00037 / +0.00037 |
| M4_SLOW | DM | y_f3 | +0.5290 | [-0.4360, +1.4939] | 0.283 | 10,852 / 43 | +1.080 (0.14) | +0.01150 / +0.01150 |
| M4_SLOW | DM | poss_xg | +0.0208 | [-0.1481, +0.1896] | 0.809 | 13,470 / 43 | +0.480 (0.47) | +0.00396 / +0.00396 |
| M4_SLOW | all | y_f3 | -0.8655 | [-1.3456, -0.3853] | 0.000411 | 51,001 / 223 | +1.684 (3.3e-13) | -0.00742 / -0.00742 |
| M4_SLOW | all | poss_xg | +0.0334 | [-0.0475, +0.1143] | 0.419 | 67,151 / 223 | +1.899 (2.2e-11) | -0.00043 / -0.00043 |
| M4_SWITCH | DM | y_f3 | -0.7856 | [-1.3801, -0.1910] | 0.0096 | 10,852 / 43 | +1.080 (0.14) | -0.00441 / -0.00441 |
| M4_SWITCH | DM | poss_xg | -0.0850 | [-0.2157, +0.0458] | 0.203 | 13,470 / 43 | +0.480 (0.47) | -0.01049 / -0.01049 |
| M4_SWITCH | all | y_f3 | +0.2582 | [-0.1519, +0.6684] | 0.217 | 51,001 / 223 | +1.684 (3.3e-13) | +0.00228 / +0.00228 |
| M4_SWITCH | all | poss_xg | +0.0367 | [-0.0300, +0.1034] | 0.281 | 67,151 / 223 | +1.899 (2.2e-11) | +0.00017 / +0.00017 |
| M6 | DM | y_f3 | +1.0902 | [-0.1640, +2.3445] | 0.0884 | 9,497 / 29 | +1.753 (0.028) | +0.03248 / +0.03248 |
| M6 | DM | poss_xg | +0.3101 | [+0.1318, +0.4884] | 0.000653 | 11,789 / 29 | +1.294 (0.041) | +0.00710 / +0.00710 |
| M6 | all | y_f3 | +0.2539 | [-0.0811, +0.5889] | 0.137 | 44,117 / 144 | +1.375 (1.8e-06) | +0.00543 / +0.00543 |
| M6 | all | poss_xg | +0.0063 | [-0.0479, +0.0606] | 0.818 | 57,370 / 145 | +1.761 (2.3e-05) | +0.00000 / +0.00000 |
| M1 | DM | y_f3 | -0.2861 | [-1.8496, +1.2773] | 0.72 | 10,608 / 37 | +1.711 (4.8e-05) | +0.01113 / +0.01113 |
| M1 | DM | poss_xg | -0.0196 | [-0.3077, +0.2685] | 0.894 | 13,062 / 37 | +1.227 (0.0032) | +0.00581 / +0.00581 |
| M1 | all | y_f3 | +0.4755 | [+0.0655, +0.8855] | 0.023 | 47,200 / 161 | +3.531 (6.4e-15) | +0.00482 / +0.00482 |
| M1 | all | poss_xg | +0.0346 | [-0.0429, +0.1122] | 0.381 | 61,948 / 161 | +4.022 (7.7e-20) | +0.00074 / +0.00074 |
| M5 | DM | y_f3 | +1.5393 | [+0.0528, +3.0258] | 0.0424 | 11,147 / 44 | +1.152 (0.1) | -0.01660 / -0.01660 |
| M5 | DM | poss_xg | +0.2269 | [-0.0018, +0.4557] | 0.0519 | 13,893 / 44 | +0.485 (0.46) | -0.00217 / -0.00217 |
| M5 | all | y_f3 | +0.1607 | [-0.3148, +0.6361] | 0.508 | 46,298 / 205 | +1.814 (1.7e-11) | +0.00349 / +0.00349 |
| M5 | all | poss_xg | +0.0755 | [+0.0086, +0.1425] | 0.027 | 63,047 / 205 | +1.983 (1.1e-10) | +0.00168 / +0.00168 |

**D4 within-DM correlations (player values, dev units, floors applied).**

| Measure | vs PR2_flag_keep | vs W | vs MOVE_ON_SPEED | vs HOLD_VARIATION |
|---|---|---|---|---|
| M2 | 0.612 [+0.15, +0.86] n 15 | 0.139 [-0.38, +0.59] n 16 | 0.017 [-0.59, +0.61] n 11 | 0.315 [-0.29, +0.74] n 13 |
| M2_1.0 | 0.391 [-0.15, +0.75] n 15 | 0.137 [-0.39, +0.59] n 16 | 0.092 [-0.54, +0.66] n 11 | 0.337 [-0.26, +0.75] n 13 |
| M2_2.0 | 0.743 [+0.37, +0.91] n 15 | -0.046 [-0.53, +0.46] n 16 | -0.203 [-0.72, +0.45] n 11 | 0.351 [-0.25, +0.76] n 13 |
| M3_speed | -0.252 [-0.68, +0.30] n 15 | -0.182 [-0.47, +0.14] n 39 | 0.172 [-0.39, +0.64] n 14 | -0.383 [-0.73, +0.12] n 17 |
| M3_var | -0.322 [-0.72, +0.23] n 15 | 0.225 [-0.10, +0.50] n 39 | -0.143 [-0.63, +0.42] n 14 | 0.071 [-0.42, +0.53] n 17 |
| M4_ACCEL | 0.347 [-0.20, +0.73] n 15 | 0.369 [+0.09, +0.59] n 47 | -0.434 [-0.78, +0.13] n 14 | -0.318 [-0.69, +0.19] n 17 |
| M4_KEEP | -0.506 [-0.81, +0.01] n 15 | -0.018 [-0.30, +0.27] n 47 | -0.126 [-0.62, +0.43] n 14 | 0.387 [-0.12, +0.73] n 17 |
| M4_SLOW | 0.188 [-0.36, +0.64] n 15 | -0.279 [-0.52, +0.01] n 47 | 0.618 [+0.13, +0.86] n 14 | -0.111 [-0.56, +0.39] n 17 |
| M4_SWITCH | 0.345 [-0.20, +0.73] n 15 | -0.035 [-0.32, +0.25] n 47 | -0.240 [-0.68, +0.33] n 14 | -0.114 [-0.56, +0.39] n 17 |
| M6 | -0.391 [-0.75, +0.15] n 15 | 0.315 [-0.01, +0.58] n 36 | 0.419 [-0.14, +0.78] n 14 | -0.446 [-0.76, +0.04] n 17 |
| M6_on_ACCEL | n 2 | n 2 | n 2 | n 2 |
| M6_on_SLOW | -0.195 [-0.92, +0.83] n 5 | 0.267 [-0.80, +0.93] n 5 | -0.648 [-0.97, +0.55] n 5 | -0.399 [-0.95, +0.75] n 5 |
| M1 | -0.413 [-0.76, +0.13] n 15 | 0.039 [-0.26, +0.33] n 44 | -0.082 [-0.59, +0.47] n 14 | -0.176 [-0.61, +0.33] n 17 |
| M5 | 0.311 [-0.24, +0.71] n 15 | -0.338 [-0.58, -0.05] n 44 | 0.044 [-0.50, +0.56] n 14 | 0.247 [-0.27, +0.65] n 17 |

**D5 praised list (Task 41's list and perm_test).**

| Measure | declared direction | n qualifying | n present | T | p (two-sided) | present |
|---|---|---|---|---|---|---|
| M2 | higher | 95 | 10 | +0.338 | 0.236 | Kevin De Bruyne, Marco Verratti, Granit Xhaka, Sergio Busquets i Burgos, Luka Modrić, Joshua Kimmich, Rodrigo Hernández Cascante, Frenkie de Jong, Florian Grillitsch, Pedro González López |
| M2_1.0 | none | 95 | 10 | +0.298 | 0.304 | Kevin De Bruyne, Marco Verratti, Granit Xhaka, Sergio Busquets i Burgos, Luka Modrić, Joshua Kimmich, Rodrigo Hernández Cascante, Frenkie de Jong, Florian Grillitsch, Pedro González López |
| M2_2.0 | none | 95 | 10 | +0.176 | 0.533 | Kevin De Bruyne, Marco Verratti, Granit Xhaka, Sergio Busquets i Burgos, Luka Modrić, Joshua Kimmich, Rodrigo Hernández Cascante, Frenkie de Jong, Florian Grillitsch, Pedro González López |
| M3_speed | none | 219 | 13 | -0.381 | 0.138 | Kevin De Bruyne, Marco Verratti, Granit Xhaka, Sergio Busquets i Burgos, Luka Modrić, Toni Kroos, Joshua Kimmich, Rodrigo Hernández Cascante, Frenkie de Jong, İlkay Gündoğan, Florian Grillitsch, Mykola Shaparenko, Pedro González López |
| M3_var | none | 219 | 13 | -0.202 | 0.423 | Kevin De Bruyne, Marco Verratti, Granit Xhaka, Sergio Busquets i Burgos, Luka Modrić, Toni Kroos, Joshua Kimmich, Rodrigo Hernández Cascante, Frenkie de Jong, İlkay Gündoğan, Florian Grillitsch, Mykola Shaparenko, Pedro González López |
| M4_ACCEL | none | 270 | 13 | +0.334 | 0.198 | Kevin De Bruyne, Marco Verratti, Granit Xhaka, Sergio Busquets i Burgos, Luka Modrić, Toni Kroos, Joshua Kimmich, Rodrigo Hernández Cascante, Frenkie de Jong, İlkay Gündoğan, Florian Grillitsch, Mykola Shaparenko, Pedro González López |
| M4_KEEP | none | 270 | 13 | +0.232 | 0.38 | Kevin De Bruyne, Marco Verratti, Granit Xhaka, Sergio Busquets i Burgos, Luka Modrić, Toni Kroos, Joshua Kimmich, Rodrigo Hernández Cascante, Frenkie de Jong, İlkay Gündoğan, Florian Grillitsch, Mykola Shaparenko, Pedro González López |
| M4_SLOW | none | 270 | 13 | -0.476 | 0.0635 | Kevin De Bruyne, Marco Verratti, Granit Xhaka, Sergio Busquets i Burgos, Luka Modrić, Toni Kroos, Joshua Kimmich, Rodrigo Hernández Cascante, Frenkie de Jong, İlkay Gündoğan, Florian Grillitsch, Mykola Shaparenko, Pedro González López |
| M4_SWITCH | none | 270 | 13 | +0.110 | 0.676 | Kevin De Bruyne, Marco Verratti, Granit Xhaka, Sergio Busquets i Burgos, Luka Modrić, Toni Kroos, Joshua Kimmich, Rodrigo Hernández Cascante, Frenkie de Jong, İlkay Gündoğan, Florian Grillitsch, Mykola Shaparenko, Pedro González López |
| M6 | none | 169 | 13 | -0.127 | 0.608 | Kevin De Bruyne, Marco Verratti, Granit Xhaka, Sergio Busquets i Burgos, Luka Modrić, Toni Kroos, Joshua Kimmich, Rodrigo Hernández Cascante, Frenkie de Jong, İlkay Gündoğan, Florian Grillitsch, Mykola Shaparenko, Pedro González López |
| M6_on_ACCEL | none | 5 | 2 | +0.000 | 1 | Marco Verratti, Granit Xhaka |
| M6_on_SLOW | none | 33 | 4 | +0.579 | 0.0886 | Marco Verratti, Granit Xhaka, Sergio Busquets i Burgos, Joshua Kimmich |
| M1 | higher | 184 | 13 | -0.227 | 0.38 | Kevin De Bruyne, Marco Verratti, Granit Xhaka, Sergio Busquets i Burgos, Luka Modrić, Toni Kroos, Joshua Kimmich, Rodrigo Hernández Cascante, Frenkie de Jong, İlkay Gündoğan, Florian Grillitsch, Mykola Shaparenko, Pedro González López |
| M5 | higher | 202 | 13 | +0.452 | 0.0807 | Kevin De Bruyne, Marco Verratti, Granit Xhaka, Sergio Busquets i Burgos, Luka Modrić, Toni Kroos, Joshua Kimmich, Rodrigo Hernández Cascante, Frenkie de Jong, İlkay Gündoğan, Florian Grillitsch, Mykola Shaparenko, Pedro González López |

### D2 travels (Task 46 A-ii recipe: 2015/16 development club context vs study development national-team context)

| Measure | floor | n players | rel club / rel intl | r_obs | r_true [95% CI] | DM n | A-i movers (study dev club vs country) | A-i r_true [95% CI] |
|---|---|---|---|---|---|---|---|---|
| M2 | 50 | 8 | 0.639 / 0.831 | 0.666 | +0.914 [-0.560, +1.000] | 2 | 10 | not run (< 15 movers) |
| M3_speed | 100 | 21 | 0.941 / 0.821 | 0.181 | +0.206 [-0.447, +0.696] | 3 | 20 | +0.788 [+0.518, +1.000] |
| M4_ACCEL | 100 | 27 | 0.856 / 0.526 | 0.227 | +0.339 [+0.029, +1.000] | 4 | 21 | +0.760 [+0.135, +1.000] |
| M4_SLOW | 100 | 27 | 0.846 / 0.707 | 0.541 | +0.700 [+0.276, +1.000] | 4 | 21 | +0.263 [-0.695, +1.000] |
| M4_SWITCH | 100 | 27 | 0.758 / 0.616 | 0.083 | +0.121 [-0.479, +0.840] | 4 | 21 | +0.604 [+0.044, +1.000] |
| M6 | 100 | 14 | 0.832 / -0.157 | 0.571 | unmeasurable (a reliability < 0.10) | 2 | 15 | +0.277 [-1.000, +1.000] |

### K1 common core — 2015/16 development leagues (PL + Bundesliga; 2015/16 further use), deep midfielders

D1 reliabilities used (DM): PR2_flag_keep 0.615, W 0.826, M2 0.715, M3_speed 0.849, M4_ACCEL 0.907, M4_SLOW 0.862, M6 0.260

| Pair | n | r [95% boot CI] | disattenuated r [95% boot CI] |
|---|---|---|---|
| PR2_flag_keep|W | 43 | -0.186 [-0.489, +0.111] | -0.260 [-0.686, +0.155] |
| PR2_flag_keep|M2 | 43 | +0.340 [+0.032, +0.587] | 0.513 [+0.049, +0.886] |
| PR2_flag_keep|M3_speed | 43 | -0.224 [-0.407, +0.011] | -0.310 [-0.563, +0.015] |
| PR2_flag_keep|M4_ACCEL | 43 | -0.475 [-0.705, -0.122] | -0.637 [-0.944, -0.164] |
| PR2_flag_keep|M4_SLOW | 43 | +0.235 [-0.122, +0.501] | 0.322 [-0.168, +0.688] |
| PR2_flag_keep|M6 | 43 | +0.112 [-0.267, +0.260] | 0.280 [-0.669, +0.651] |
| W|M2 | 43 | -0.394 [-0.641, -0.102] | -0.513 [-0.834, -0.133] |
| W|M3_speed | 43 | -0.233 [-0.560, +0.103] | -0.278 [-0.669, +0.123] |
| W|M4_ACCEL | 43 | +0.087 [-0.253, +0.404] | 0.100 [-0.292, +0.466] |
| W|M4_SLOW | 43 | +0.291 [-0.077, +0.607] | 0.345 [-0.092, +0.719] |
| W|M6 | 43 | -0.108 [-0.280, +0.387] | -0.233 [-0.605, +0.834] |
| M2|M3_speed | 43 | +0.499 [+0.269, +0.721] | 0.641 [+0.346, +0.925] |
| M2|M4_ACCEL | 43 | -0.125 [-0.377, +0.188] | -0.155 [-0.468, +0.234] |
| M2|M4_SLOW | 43 | -0.046 [-0.330, +0.260] | -0.059 [-0.421, +0.331] |
| M2|M6 | 43 | +0.023 [-0.233, +0.284] | 0.053 [-0.541, +0.658] |
| M3_speed|M4_ACCEL | 43 | +0.149 [-0.118, +0.350] | 0.170 [-0.134, +0.399] |
| M3_speed|M4_SLOW | 43 | -0.066 [-0.336, +0.194] | -0.077 [-0.393, +0.226] |
| M3_speed|M6 | 43 | +0.085 [-0.138, +0.313] | 0.181 [-0.294, +0.666] |
| M4_ACCEL|M4_SLOW | 43 | -0.361 [-0.614, -0.059] | -0.408 [-0.694, -0.066] |
| M4_ACCEL|M6 | 43 | -0.346 [-0.538, -0.107] | -0.713 [-1.109, -0.220] |
| M4_SLOW|M6 | 43 | -0.093 [-0.276, +0.411] | -0.197 [-0.584, +0.868] |

PC1 share of variance, {PR2_flag_keep, W, M4_ACCEL, M6}: 0.428 (n 43 DMs; eigenvalues 1.711, 0.956, 0.885, 0.449).

### K1 common core — study sample development half (as usual), deep midfielders

D1 reliabilities used (DM): PR2_flag_keep -0.013, W 0.675, Decision -0.213, M1 -0.015, M2 0.166, M3_speed 0.385, M4_ACCEL 0.513, M4_SLOW 0.091, M5 0.038, M6 0.361

| Pair | n | r [95% boot CI] | disattenuated r [95% boot CI] |
|---|---|---|---|
| PR2_flag_keep|W | 15 | +0.033 [-0.471, +0.741] | — — |
| PR2_flag_keep|Decision | 15 | -0.100 [-0.665, +0.605] | — — |
| PR2_flag_keep|M1 | 15 | -0.413 [-0.778, +0.019] | — — |
| PR2_flag_keep|M2 | 15 | +0.612 [+0.045, +0.912] | — — |
| PR2_flag_keep|M3_speed | 15 | -0.252 [-0.661, +0.252] | — — |
| PR2_flag_keep|M4_ACCEL | 15 | +0.347 [-0.392, +0.909] | — — |
| PR2_flag_keep|M4_SLOW | 15 | +0.188 [-0.301, +0.648] | — — |
| PR2_flag_keep|M5 | 15 | +0.311 [-0.230, +0.710] | — — |
| PR2_flag_keep|M6 | 15 | -0.391 [-0.879, +0.243] | — — |
| W|Decision | 47 | +0.423 [+0.070, +0.672] | — — |
| W|M1 | 44 | +0.039 [-0.183, +0.250] | — — |
| W|M2 | 16 | +0.139 [-0.377, +0.710] | 0.413 [-1.124, +2.116] |
| W|M3_speed | 39 | -0.182 [-0.522, +0.102] | -0.357 [-1.024, +0.199] |
| W|M4_ACCEL | 47 | +0.369 [+0.102, +0.618] | 0.627 [+0.173, +1.049] |
| W|M4_SLOW | 47 | -0.279 [-0.563, +0.096] | -1.122 [-2.266, +0.385] |
| W|M5 | 44 | -0.338 [-0.579, -0.014] | -2.100 [-3.597, -0.088] |
| W|M6 | 36 | +0.315 [-0.212, +0.629] | 0.639 [-0.429, +1.275] |
| Decision|M1 | 47 | -0.030 [-0.368, +0.285] | — — |
| Decision|M2 | 16 | -0.111 [-0.525, +0.222] | — — |
| Decision|M3_speed | 39 | -0.092 [-0.383, +0.212] | — — |
| Decision|M4_ACCEL | 51 | +0.323 [+0.110, +0.518] | — — |
| Decision|M4_SLOW | 51 | -0.354 [-0.551, -0.106] | — — |
| Decision|M5 | 46 | -0.263 [-0.547, +0.069] | — — |
| Decision|M6 | 36 | +0.486 [+0.043, +0.768] | — — |
| M1|M2 | 16 | -0.120 [-0.487, +0.259] | — — |
| M1|M3_speed | 37 | -0.118 [-0.466, +0.278] | — — |
| M1|M4_ACCEL | 47 | -0.128 [-0.377, +0.122] | — — |
| M1|M4_SLOW | 47 | +0.027 [-0.247, +0.295] | — — |
| M1|M5 | 42 | -0.228 [-0.482, +0.097] | — — |
| M1|M6 | 35 | -0.013 [-0.405, +0.345] | — — |
| M2|M3_speed | 16 | -0.109 [-0.519, +0.316] | -0.430 [-2.049, +1.249] |
| M2|M4_ACCEL | 16 | +0.076 [-0.601, +0.650] | 0.259 [-2.056, +2.224] |
| M2|M4_SLOW | 16 | +0.247 [-0.083, +0.539] | 2.003 [-0.671, +4.372] |
| M2|M5 | 16 | +0.235 [-0.216, +0.673] | 2.947 [-2.699, +8.425] |
| M2|M6 | 16 | -0.474 [-0.775, -0.143] | -1.932 [-3.164, -0.583] |
| M3_speed|M4_ACCEL | 39 | +0.283 [-0.073, +0.564] | 0.636 [-0.165, +1.267] |
| M3_speed|M4_SLOW | 39 | +0.052 [-0.269, +0.367] | 0.276 [-1.437, +1.959] |
| M3_speed|M5 | 37 | +0.316 [-0.187, +0.655] | 2.603 [-1.542, +5.392] |
| M3_speed|M6 | 35 | +0.079 [-0.245, +0.390] | 0.213 [-0.658, +1.046] |
| M4_ACCEL|M4_SLOW | 51 | -0.422 [-0.613, -0.189] | -1.951 [-2.830, -0.874] |
| M4_ACCEL|M5 | 46 | -0.038 [-0.367, +0.265] | -0.273 [-2.618, +1.887] |
| M4_ACCEL|M6 | 36 | -0.042 [-0.434, +0.346] | -0.098 [-1.009, +0.804] |
| M4_SLOW|M5 | 46 | -0.046 [-0.392, +0.283] | -0.785 [-6.626, +4.777] |
| M4_SLOW|M6 | 36 | -0.002 [-0.448, +0.514] | -0.013 [-2.468, +2.834] |
| M5|M6 | 34 | -0.256 [-0.580, +0.227] | -2.178 [-4.926, +1.928] |

PC1 share of variance, {PR2_flag_keep, Decision, M4_ACCEL, M5}: 0.469 (n 15 DMs; eigenvalues 1.877, 1.391, 0.451, 0.281).

### K2 adds beyond? — 2015/16 development leagues (PL + Bundesliga; 2015/16 further use), deep-midfielder passes (per 100 passes per SD; same rows within each measure)

| Measure | outcome | n rows / players | tempo alone | tempo with PR2_flag_keep | PR2 alone | PR2 with tempo |
|---|---|---|---|---|---|---|
| M2 | y_f3 | 43,579 / 43 | -0.217 [-0.746, +0.312] p 0.42 | -0.347 [-0.928, +0.234] p 0.24 | +0.301 [-0.170, +0.773] p 0.21 | +0.428 [-0.014, +0.870] p 0.058 |
| M3_speed | y_f3 | 43,579 / 43 | -0.908 [-1.556, -0.260] p 0.006 | -0.898 [-1.546, -0.251] p 0.0066 | +0.301 [-0.170, +0.773] p 0.21 | +0.274 [-0.175, +0.722] p 0.23 |
| M4_ACCEL | y_f3 | 43,579 / 43 | +0.234 [-0.354, +0.822] p 0.44 | +0.549 [-0.117, +1.214] p 0.11 | +0.301 [-0.170, +0.773] p 0.21 | +0.606 [+0.029, +1.183] p 0.04 |
| M4_SLOW | y_f3 | 43,579 / 43 | -0.039 [-0.430, +0.353] p 0.85 | -0.114 [-0.569, +0.341] p 0.62 | +0.301 [-0.170, +0.773] p 0.21 | +0.337 [-0.209, +0.882] p 0.23 |
| M4_SWITCH | y_f3 | 43,579 / 43 | +0.738 [+0.055, +1.422] p 0.034 | +0.732 [+0.053, +1.412] p 0.035 | +0.301 [-0.170, +0.773] p 0.21 | +0.290 [-0.167, +0.747] p 0.21 |
| M6 | y_f3 | 43,576 / 43 | +0.171 [-0.063, +0.404] p 0.15 | +0.108 [-0.160, +0.376] p 0.43 | +0.301 [-0.170, +0.773] p 0.21 | +0.261 [-0.237, +0.758] p 0.3 |
| M2 | poss_xg | 51,845 / 43 | +0.060 [-0.019, +0.140] p 0.14 | +0.069 [-0.014, +0.151] p 0.1 | -0.004 [-0.069, +0.061] p 0.91 | -0.028 [-0.086, +0.030] p 0.35 |
| M3_speed | poss_xg | 51,845 / 43 | +0.013 [-0.056, +0.082] p 0.71 | +0.013 [-0.056, +0.082] p 0.71 | -0.004 [-0.069, +0.061] p 0.91 | -0.003 [-0.068, +0.062] p 0.92 |
| M4_ACCEL | poss_xg | 51,845 / 43 | +0.046 [-0.026, +0.117] p 0.21 | +0.061 [-0.021, +0.143] p 0.14 | -0.004 [-0.069, +0.061] p 0.91 | +0.030 [-0.037, +0.096] p 0.38 |
| M4_SLOW | poss_xg | 51,845 / 43 | -0.006 [-0.070, +0.057] p 0.84 | -0.006 [-0.072, +0.060] p 0.86 | -0.004 [-0.069, +0.061] p 0.91 | -0.002 [-0.068, +0.064] p 0.95 |
| M4_SWITCH | poss_xg | 51,845 / 43 | -0.038 [-0.108, +0.032] p 0.29 | -0.038 [-0.108, +0.032] p 0.29 | -0.004 [-0.069, +0.061] p 0.91 | -0.002 [-0.065, +0.060] p 0.94 |
| M6 | poss_xg | 51,842 / 43 | -0.047 [-0.076, -0.018] p 0.0014 | -0.051 [-0.085, -0.016] p 0.0039 | -0.004 [-0.069, +0.061] p 0.91 | +0.016 [-0.047, +0.078] p 0.62 |

### K2 adds beyond? — study sample development half (as usual), deep-midfielder passes (per 100 passes per SD; same rows within each measure)

| Measure | outcome | n rows / players | tempo alone | tempo with PR2_flag_keep + Decision | PR2 alone | PR2 with tempo | Decision alone | Decision with tempo |
|---|---|---|---|---|---|---|---|---|
| M1 | y_f3 | 6,849 / 15 | -1.094 [-2.467, +0.279] p 0.12 | -0.703 [-2.993, +1.587] p 0.55 | +1.072 [-0.095, +2.239] p 0.072 | +0.395 [-2.085, +2.876] p 0.75 | +2.065 [-2.199, +6.328] p 0.34 | +2.927 [-3.772, +9.625] p 0.39 |
| M2 | y_f3 | 6,851 / 15 | +1.610 [+0.490, +2.729] p 0.0048 | +1.461 [-0.078, +3.001] p 0.063 | +1.072 [-0.095, +2.239] p 0.072 | +0.732 [-0.385, +1.850] p 0.2 | +2.064 [-2.199, +6.327] p 0.34 | +3.079 [-0.531, +6.688] p 0.095 |
| M3_speed | y_f3 | 6,849 / 15 | -2.612 [-3.972, -1.251] p 0.00017 | -3.255 [-4.121, -2.390] p 1.7e-13 | +1.072 [-0.095, +2.239] p 0.072 | +0.105 [-0.662, +0.873] p 0.79 | +2.065 [-2.199, +6.328] p 0.34 | +6.165 [+0.767, +11.563] p 0.025 |
| M4_ACCEL | y_f3 | 6,851 / 15 | +1.129 [-0.061, +2.319] p 0.063 | +0.014 [-1.438, +1.465] p 0.99 | +1.072 [-0.095, +2.239] p 0.072 | +1.065 [-0.465, +2.595] p 0.17 | +2.064 [-2.199, +6.327] p 0.34 | +2.041 [-4.164, +8.245] p 0.52 |
| M4_SLOW | y_f3 | 6,851 / 15 | +0.438 [-0.735, +1.611] p 0.46 | +0.902 [-0.513, +2.316] p 0.21 | +1.072 [-0.095, +2.239] p 0.072 | +0.827 [-0.482, +2.137] p 0.22 | +2.064 [-2.199, +6.327] p 0.34 | +4.408 [+0.268, +8.548] p 0.037 |
| M4_SWITCH | y_f3 | 6,851 / 15 | -0.140 [-4.527, +4.248] p 0.95 | -3.650 [-7.515, +0.215] p 0.064 | +1.072 [-0.095, +2.239] p 0.072 | +1.602 [+0.506, +2.698] p 0.0042 | +2.064 [-2.199, +6.327] p 0.34 | +2.154 [-3.070, +7.378] p 0.42 |
| M5 | y_f3 | 6,851 / 15 | +2.382 [+1.600, +3.164] p 2.3e-09 | +2.504 [+0.668, +4.341] p 0.0075 | +1.072 [-0.095, +2.239] p 0.072 | -0.250 [-1.661, +1.161] p 0.73 | +2.064 [-2.199, +6.327] p 0.34 | +1.162 [-4.693, +7.016] p 0.7 |
| M6 | y_f3 | 6,739 / 15 | +1.613 [+0.536, +2.691] p 0.0033 | +1.274 [+0.293, +2.256] p 0.011 | +1.050 [-0.092, +2.192] p 0.072 | +0.686 [-0.271, +1.644] p 0.16 | +1.536 [-1.638, +4.710] p 0.34 | +0.029 [-4.815, +4.872] p 0.99 |
| M1 | poss_xg | 8,530 / 15 | -0.294 [-0.628, +0.040] p 0.085 | -0.735 [-1.533, +0.062] p 0.071 | +0.175 [-0.153, +0.504] p 0.3 | -0.518 [-1.200, +0.164] p 0.14 | -0.733 [-2.668, +1.202] p 0.46 | +0.198 [-2.136, +2.532] p 0.87 |
| M2 | poss_xg | 8,534 / 15 | +0.048 [-0.457, +0.553] p 0.85 | -0.050 [-0.704, +0.604] p 0.88 | +0.175 [-0.153, +0.504] p 0.3 | +0.188 [-0.214, +0.590] p 0.36 | -0.733 [-2.668, +1.202] p 0.46 | -0.769 [-2.880, +1.342] p 0.48 |
| M3_speed | poss_xg | 8,530 / 15 | -0.742 [-0.943, -0.542] p 4e-13 | -0.797 [-1.131, -0.463] p 3e-06 | +0.175 [-0.153, +0.504] p 0.3 | -0.042 [-0.285, +0.200] p 0.73 | -0.733 [-2.668, +1.202] p 0.46 | +0.268 [-1.639, +2.175] p 0.78 |
| M4_ACCEL | poss_xg | 8,534 / 15 | +0.118 [-0.293, +0.529] p 0.57 | +0.314 [-0.107, +0.735] p 0.14 | +0.175 [-0.153, +0.504] p 0.3 | +0.012 [-0.330, +0.353] p 0.95 | -0.733 [-2.668, +1.202] p 0.46 | -1.300 [-3.792, +1.192] p 0.31 |
| M4_SLOW | poss_xg | 8,534 / 15 | +0.015 [-0.209, +0.240] p 0.89 | -0.131 [-0.605, +0.343] p 0.59 | +0.175 [-0.153, +0.504] p 0.3 | +0.214 [-0.139, +0.568] p 0.23 | -0.733 [-2.668, +1.202] p 0.46 | -1.074 [-3.772, +1.624] p 0.44 |
| M4_SWITCH | poss_xg | 8,534 / 15 | -0.217 [-1.643, +1.210] p 0.77 | -0.630 [-1.790, +0.531] p 0.29 | +0.175 [-0.153, +0.504] p 0.3 | +0.273 [-0.051, +0.597] p 0.099 | -0.733 [-2.668, +1.202] p 0.46 | -0.728 [-2.519, +1.063] p 0.43 |
| M5 | poss_xg | 8,534 / 15 | +0.435 [+0.191, +0.679] p 0.00047 | +0.802 [+0.467, +1.137] p 2.6e-06 | +0.175 [-0.153, +0.504] p 0.3 | -0.223 [-0.512, +0.066] p 0.13 | -0.733 [-2.668, +1.202] p 0.46 | -1.062 [-3.079, +0.954] p 0.3 |
| M6 | poss_xg | 8,395 / 15 | +0.312 [+0.038, +0.586] p 0.026 | +0.480 [+0.175, +0.786] p 0.0021 | +0.171 [-0.151, +0.493] p 0.3 | +0.053 [-0.197, +0.304] p 0.68 | -0.543 [-1.978, +0.892] p 0.46 | -1.124 [-2.758, +0.510] p 0.18 |




## 4. Deviations from the brief
- **Unrequested cells in the JSON.** The test script's "new measure" filter (`startswith("M")`) also caught the existing comparator MOVE_ON_SPEED, so `engine_v2_task52_tests.json` contains D3, D4 and D5 cells for MOVE_ON_SPEED. They are not shown on this page and were not requested. Its D1 values are needed (K1 / D4 comparators) and are shown.
- **D1 generalised.** Task 38's R1 averages units per half. For TI (M1), M5 (differences of means) and M3_var / HOLD_VARIATION (SDs), I applied the measure's own formula to each half. There is no per-half floor: a half with no unit of a needed kind is dropped from that split's correlation.
- **D2.**
  - "M3" is run as M3_speed only. M3_var is an SD, and the Task 46 recipe needs unit means.
  - D2 is also run for M4_ACCEL / SLOW / SWITCH and M6 (Amendment A applies D1-D5 to them). M5 is study-only, so it has no D2.
  - The DM subgroup is players who are DMs in either dataset's DM group.
  - "Task 46 A-i's club vs country within study development matches" is computed with the same `disattenuated` recipe, not Task 46 A-i's `ph_b2` context-level routine.
- **D3 control for pass units** is the completion control (Task 44's pass-unit control), because retention (keep_spell) is defined only for receptions. Receptions use the retention control.
- **D4 / K1 floors for existing comparators:** PR2_flag_keep >= 50, W >= 100, MOVE_ON_SPEED / HOLD_VARIATION >= 200 (Task 51's), v5 Decision >= 100, all counted on development units only.
- **Study g features** come from `value_model_rows_v5` (an existing derived table, read with the development filter). The g models themselves are refit on development folds.
- **Study DM group** = Task 27's 111 ∩ players with development eligible passes (106). The study role rule was recomputed on development passes, because `task32_step4.assign_roles` reads replication rows.
- **Operational readings (also Section 6):**
  - M1 "nearer the goal" = distance to (120, 40).
  - M2 units = all pressured completed receptions, with FK = 0 for spells not ending in his completed pass within the cut, including spells excluded from T.
  - M5: no forward candidate in the restricted set = no OPPORTUNITY.
  - M6: "open play" = eligible (non-set-piece) passes; the reception is the team's next Ball Receipt* in the possession; V_after's time is measured from that reception.
- **K1 details:**
  - The bootstrap resamples players and holds the D1 reliabilities fixed (not re-estimated per resample).
  - Disattenuated values are not clipped to [-1, 1].
  - Disattenuation is shown as "—" where a D1 reliability is <= 0.
- **K2 rows:** each model trio (tempo alone, tempo + base, base alone) is fitted on the same rows, those with every S in the full model.
- **Step 1 temporary folder** was the system temporary directory (auto-deleted), not the session scratchpad.

## 5. Problems and surprises
- **Step 3's T is the existing measurement.** On the 181,930 (2015/16) and 87,797 (study) receptions that join to the existing tempo module's time on ball, T is identical (r = 1.0000, mean absolute difference 0). Taken at face value, Step 3's T is not a new measurement; only g_T (no team demeaning) and the measures built on r are new.
- **T <= 0 is common.** 37,434 (2015/16) and 11,909 (study) spells ending in his pass have T <= 0 (identical timestamps) and are excluded by the brief's 0 < T rule. That is about 14% and 10% of pass endings.
- **M6 is dominated by extreme velocities from near-zero time gaps.** V_after ranges from -12,000 to +1,825 units/s (2015/16) and -4,411 to +614 (study), against 1st-99th percentiles of about -12 to +17. The M6 baseline's out-of-fold R^2 is negative (-0.373, -0.285). Taken at face value, M6 player values and every M6 test (D1-D5, K1, K2) partly reflect a few extreme units, not typical team speed-ups.
- **Study-sample deep-midfielder samples are small:**
  - 15 DMs meet the PR2_flag_keep floor (>= 50 development pressured receptions).
  - 16 meet M2's floor.
  - 14 meet MOVE_ON_SPEED's and 17 meet HOLD_VARIATION's floor.
  - K2 on the study sample therefore runs on 15 players' passes.
  - D3 study M2 within DMs (15 players, coefficient +1.75, p 1.2e-9) has a retention control that is not positive (+0.59, p 0.61).
- **The existing benchmarked measures are not stable on the study development half within DMs:**
  - PR2_flag_keep D1 = -0.013 (40 players).
  - v5 Decision D1 = -0.213 (42 players).
  - For comparison, PR2_flag_keep is 0.615 on the 2015/16 development DMs.
  - Taken at face value, study-half comparisons with PR2_flag_keep or Decision cannot separate these players. K1's study disattenuation is undefined or explosive (for example M2|M5 2.95, W|M5 -2.10).
- **D2's DM subgroup has 2-4 players**, so no DM travel estimate exists. D2 all-player estimates rest on 8 (M2) to 27 players.
- **D1 for M6 on ACCEL / SLOW passes:** few players meet the >= 100 floor (2015/16: 57 / 221 players; study: 6 / 35).
- **D5 in 2015/16 development leagues:** only De Bruyne (and, for M4, Xhaka and Siem de Jong) of the praised list are present.

## 6. Questions for the research lead
1. **M6 outliers:** V_after / V_before with near-zero seconds produce values in the thousands. Should M6 require a minimum time gap, or be trimmed? (Not done; the brief says only "> 0 s".)
2. **Step 3's T equals the existing time on ball.** Is a new T definition wanted, or is the new part only g_T without team demeaning?
3. **M2 units:** should spells excluded from T (shot, foul, period end, other player's touch) be dropped from M2 instead of counted as FK = 0?
4. **M1 "nearer the opponent goal":** is distance to the goal centre (used) the intended reading, or x-coordinate advance?
5. **D1 for difference and SD measures:** is applying the measure's formula to each half the intended version of Task 38's method?
6. **D2 for M4 / M6 and "M3":** confirm D2 should cover M4 / M6 (Amendment A) and M3_speed only.
7. **Study floors:** with 143 development matches, few study DMs meet the PR2_flag_keep / M2 / tempo floors. Should Task 53's gates use the same floors?
8. **K1:** should disattenuated values be clipped, or omitted when a reliability is below a bar?
9. **Pass-unit control in D3 / K2:** is completion (used) the intended "retention control" for pass units?
10. **M5 with no forward candidate** in the restricted set: counted as no OPPORTUNITY. Is that intended?

## 7. Files produced
- **Scripts:**
  - `src/engine_v2/task52_snapshot.py`: Step 1.
  - `src/engine_v2/task52_split.py`: Step 2.
  - `src/engine_v2/task52_build.py`: Steps 3-4, Amendment A measures.
  - `src/engine_v2/task52_tests.py`: D1-D5, K1, K2.
- `docs/benchmark/manifest-v9.txt`, `docs/splits/tempo_split.csv`.
- **Data, not committed:**
  - `data/benchmark_v9/` (16 files).
  - `data/processed/engine_v2/task52_w_1516.parquet`, `task52_w_study.parquet`.
  - `data/processed/tempo_task52_study_{move,hold}_residuals_ids.parquet`.
  - `data/processed/engine_v2/task52_{1516,study}_{receptions,passes}.parquet` (development units only).
  - `data/engine_v2_task52_build.json`, `data/engine_v2_task52_tests.json`.
- **Commits:**
  - 53b48a9: Step 1; tag `benchmark-v9`, not pushed.
  - af9eaf1: Step 2 split.
  - The final commit hash is recorded below.
- **Side effects:** a system temporary folder during Step 1 (auto-deleted).
- **Not mine and not committed:** pre-existing uncommitted changes to `docs/JOURNAL.md` and the untracked `AGENTS.md`.

## 8. Confidence
- **Strong:** the split and the replication guard. Every per-match open goes through one asserting function, and every derived-table read is filtered and listed.
- **Weakest links:**
  - Study-sample DM cells with 15-16 players.
  - Near-zero or negative study-half reliabilities for PR2_flag_keep, Decision, M1 and M5.
  - M6's outlier-driven values.
  - The operational readings in Section 6.
