# Task 05: Study A, discovery half

Date: 2026-09-20
Status: COMPLETE

## Per-section checklist (per brief docs/specs/task-05-study-a-discovery.md)
- Step 0 (git hygiene, Amendment v2-1 commit): COMPLETE
- Step 1 (pass-level type values, discovery only): COMPLETE
- Step 2 (statistics for all 107 analyzable pairs): COMPLETE
- Step 3 (candidates): COMPLETE
- Step 4 (descriptive context): COMPLETE
- Hard rules (confirmation untouched, no Gate D/sensitivity/realized
  values, full unsorted table, no interpretation): COMPLETE

## 1. Headline
Of the 107 analyzable (cell, option-type) pairs in the discovery half,
10 meet all three plan-3.4 candidate conditions (G > 0 with CI excluding
zero, P > 0.5, L ≥ 0.5 goal-equivalents/38-match season); all 10 are
`lateral_short` or `lateral_medium` types, none under pressure. This is
a discovery-stage list only — none of these have been checked against
confirmation data or Gate D yet (Task 06).

## 2. What I did
Reproduce with: `.venv/bin/python src/decision_engine/task05_study_a_discovery.py`
(after Step 0's git commits, done separately — see below).

- **Step 0**: appended the brief's verbatim item "9." to `CLAUDE.md`'s
  "Reporting discipline" section (see Section 5 — that list's own
  numbering has a pre-existing gap I did not try to fix). Committed all
  currently untracked/modified files under `src/` and `docs/` (plus
  `CLAUDE.md`) except `docs/specs/analysis-plan-v2.md`, in one commit
  (`74a794e`, "Track all code and docs through Task 04"). Committed
  `analysis-plan-v2.md` (Amendment v2-1) separately (`71eb345`). Did not
  touch `docs/JOURNAL.md`.
- **Step 1**: read `data/splits/match_split.csv`, took the 148 discovery
  match IDs. Loaded `options_typed.parquet`, `passes_situation.parquet`,
  and `options_ev.parquet` with a pyarrow `filters=[("match_id", "in",
  discovery_ids)]` pushdown on every read — confirmation rows never enter
  a DataFrame. `options_typed.parquet` (Task 04) only kept normalized
  coordinates, so I recovered each option's raw candidate position by
  re-applying `pitch_direction.normalize_xy` (self-inverse) with the same
  per-(team, period) direction, then joined to `options_ev.parquet` on
  `(match_id, event_id, candidate_x, candidate_y)` rounded to 6 decimals
  (see Section 5 for why rounding was necessary and how a rare duplicate-
  position collision was handled). For every pass: `EV*_k` = max `ev`
  among each available option type, chosen type `j`, `g_k = EV*_k -
  EV*_j` for every available `k != j`; attached each pass's situation
  cell from `passes_situation.parquet`.
- **Step 2**: independently re-derived the analyzable-pair set from this
  task's own discovery-only data (≥100 chosen in discovery, plan 3.2) —
  got 107, matching Task 04. For each of the 107 pairs: `G` (mean `g_k`
  over qualifying passes), `P` (share with `g_k > 0`), `s` (share of
  passes with `k` available where `k` was chosen — the broader
  denominator per plan 3.3), `L` per Amendment v2-1.1 (`G × qualifying
  passes/team-match × 38`). Bootstrapped `G`'s 95% CI by resampling the
  148 discovery matches (seed 20260920, 1,000 draws, one shared resample
  index matrix reused across all 107 pairs, per-match sum/count
  aggregation as the brief's implementation hint specifies). Wrote all
  107 rows, sorted by `(zone, under_pressure, game_state, option_type)`
  — never by effect size — to `data/processed/study_a_discovery.parquet`.
- **Step 3**: applied plan 3.4 conditions 1-3 exactly to the 107-row
  table. 10 pairs passed all three. Wrote them to
  `docs/results/05-study-a-candidates.csv` and committed it on its own
  (`e310785`), before writing this page.
- **Step 4**: for each of the 10 candidates, computed the mean number of
  type-`k` options per qualifying pass vs. the mean number of the pass's
  own chosen type `j`'s options, and the share of qualifying passes from
  `CLUB_COMPETITIONS` ("focal-team club matches" — every club
  competition-season in this sample is focal-team-built, per Amendment
  v2-1.2) vs. `INTL_COMPETITIONS` (tournaments).

## 3. Numbers

**Join** (Step 1): 616,038 discovery-half option rows in
`options_typed.parquet`; 616,038 matched to `options_ev.parquet`
(100.0% match rate) after resolving 2 duplicate-position key groups (see
Section 5). 85,746 discovery-half passes (of 171,618 total, i.e. the
148/299 discovery matches).

**Analyzable pairs**: 107 (independently reproduced from this task's own
data, matching Task 04's count).

**Candidates**: 10 of 107.

**Full 107-pair table** (sorted by zone, pressure, game state, option
type — not by effect size; `pressure` = under_pressure; `n_passes`/
`n_matches` are the qualifying-pass/contributing-match counts behind
`G`/`P`/`L`):

| zone | pressure | game_state | type | G | 95% CI | P | s | L | n_passes | n_matches |
|---|---|---|---|---|---|---|---|---|---|---|
| defensive | no | leading | backward_medium | -0.00824 | [-0.01252, -0.00448] | 0.523 | 0.142 | -1.914 | 703 | 106 |
| defensive | no | leading | backward_short | -0.00746 | [-0.00947, -0.00521] | 0.381 | 0.198 | -2.754 | 1243 | 117 |
| defensive | no | leading | forward_medium | -0.00340 | [-0.00419, -0.00248] | 0.180 | 0.200 | -1.774 | 1746 | 114 |
| defensive | no | leading | forward_short | -0.00257 | [-0.00374, -0.00146] | 0.282 | 0.299 | -1.048 | 1448 | 121 |
| defensive | no | leading | lateral_long | -0.00207 | [-0.00243, -0.00168] | 0.324 | 0.130 | -1.446 | 2484 | 120 |
| defensive | no | leading | lateral_medium | -0.00008 | [-0.00072, 0.00059] | 0.548 | 0.317 | -0.055 | 2712 | 124 |
| defensive | no | leading | lateral_short | 0.00029 | [-0.00022, 0.00078] | 0.529 | 0.330 | 0.174 | 2087 | 121 |
| defensive | no | level | backward_medium | -0.01385 | [-0.01626, -0.01152] | 0.458 | 0.135 | -2.713 | 1129 | 128 |
| defensive | no | level | backward_short | -0.00909 | [-0.01037, -0.00787] | 0.358 | 0.199 | -2.995 | 2167 | 135 |
| defensive | no | level | forward_long | -0.00369 | [-0.00411, -0.00315] | 0.112 | 0.091 | -1.033 | 1186 | 120 |
| defensive | no | level | forward_medium | -0.00241 | [-0.00286, -0.00187] | 0.207 | 0.207 | -1.105 | 3052 | 140 |
| defensive | no | level | forward_short | -0.00142 | [-0.00209, -0.00074] | 0.343 | 0.274 | -0.545 | 2664 | 140 |
| defensive | no | level | lateral_long | -0.00177 | [-0.00212, -0.00145] | 0.311 | 0.144 | -1.184 | 4744 | 138 |
| defensive | no | level | lateral_medium | -0.00044 | [-0.00092, 0.00002] | 0.516 | 0.340 | -0.298 | 4864 | 141 |
| defensive | no | level | lateral_short | 0.00025 | [-0.00020, 0.00071] | 0.516 | 0.340 | 0.131 | 3620 | 139 |
| defensive | no | trailing | backward_medium | -0.02623 | [-0.03419, -0.01877] | 0.359 | 0.137 | -5.297 | 643 | 112 |
| defensive | no | trailing | backward_short | -0.01447 | [-0.01740, -0.01136] | 0.331 | 0.201 | -4.900 | 1230 | 122 |
| defensive | no | trailing | forward_medium | -0.00122 | [-0.00308, 0.00076] | 0.270 | 0.212 | -0.443 | 1353 | 124 |
| defensive | no | trailing | forward_short | 0.00009 | [-0.00173, 0.00198] | 0.398 | 0.252 | 0.031 | 1313 | 126 |
| defensive | no | trailing | lateral_long | -0.00214 | [-0.00305, -0.00124] | 0.327 | 0.159 | -1.304 | 2339 | 127 |
| defensive | no | trailing | lateral_medium | -0.00123 | [-0.00228, -0.00022] | 0.480 | 0.351 | -0.799 | 2454 | 126 |
| defensive | no | trailing | lateral_short | 0.00140 | [0.00044, 0.00227] | 0.549 | 0.337 | 0.707 | 1919 | 125 |
| defensive | yes | leading | forward_short | -0.00234 | [-0.00430, -0.00054] | 0.319 | 0.332 | -0.254 | 260 | 87 |
| defensive | yes | leading | lateral_medium | 0.00066 | [-0.00034, 0.00161] | 0.533 | 0.226 | 0.101 | 460 | 106 |
| defensive | yes | leading | lateral_short | -0.00041 | [-0.00179, 0.00095] | 0.480 | 0.328 | -0.052 | 371 | 103 |
| defensive | yes | level | backward_short | -0.00812 | [-0.01000, -0.00623] | 0.351 | 0.249 | -0.675 | 407 | 117 |
| defensive | yes | level | forward_medium | 0.00009 | [-0.00123, 0.00159] | 0.333 | 0.219 | 0.008 | 459 | 116 |
| defensive | yes | level | forward_short | 0.00035 | [-0.00081, 0.00162] | 0.400 | 0.320 | 0.034 | 492 | 116 |
| defensive | yes | level | lateral_medium | 0.00019 | [-0.00083, 0.00115] | 0.481 | 0.229 | 0.028 | 889 | 130 |
| defensive | yes | level | lateral_short | 0.00039 | [-0.00064, 0.00138] | 0.507 | 0.346 | 0.049 | 681 | 123 |
| defensive | yes | trailing | forward_short | -0.00054 | [-0.00414, 0.00297] | 0.411 | 0.287 | -0.054 | 258 | 95 |
| defensive | yes | trailing | lateral_medium | -0.00417 | [-0.00656, -0.00181] | 0.464 | 0.270 | -0.575 | 446 | 111 |
| defensive | yes | trailing | lateral_short | -0.00186 | [-0.00493, 0.00095] | 0.477 | 0.414 | -0.200 | 300 | 99 |
| final | no | leading | backward_medium | -0.00780 | [-0.00974, -0.00564] | 0.166 | 0.217 | -2.829 | 1270 | 118 |
| final | no | leading | backward_short | -0.00467 | [-0.00618, -0.00335] | 0.272 | 0.314 | -1.632 | 1250 | 119 |
| final | no | leading | forward_short | -0.00112 | [-0.00288, 0.00060] | 0.461 | 0.213 | -0.364 | 1150 | 120 |
| final | no | leading | lateral_long | -0.00268 | [-0.00328, -0.00207] | 0.406 | 0.137 | -1.601 | 2157 | 122 |
| final | no | leading | lateral_medium | 0.00157 | [0.00048, 0.00269] | 0.563 | 0.302 | 1.063 | 2460 | 123 |
| final | no | leading | lateral_short | 0.00208 | [0.00137, 0.00282] | 0.567 | 0.351 | 1.059 | 1875 | 123 |
| final | no | level | backward_long | -0.00712 | [-0.00769, -0.00653] | 0.107 | 0.109 | -1.751 | 1055 | 122 |
| final | no | level | backward_medium | -0.00656 | [-0.00710, -0.00598] | 0.162 | 0.211 | -2.858 | 3027 | 140 |
| final | no | level | backward_short | -0.00367 | [-0.00431, -0.00306] | 0.281 | 0.286 | -1.386 | 2606 | 140 |
| final | no | level | forward_medium | -0.00193 | [-0.00344, -0.00044] | 0.528 | 0.151 | -0.378 | 1217 | 135 |
| final | no | level | forward_short | -0.00263 | [-0.00347, -0.00180] | 0.447 | 0.208 | -0.852 | 2181 | 138 |
| final | no | level | lateral_long | -0.00220 | [-0.00252, -0.00188] | 0.367 | 0.134 | -1.494 | 4862 | 141 |
| final | no | level | lateral_medium | 0.00103 | [0.00059, 0.00147] | 0.554 | 0.349 | 0.697 | 4860 | 141 |
| final | no | level | lateral_short | 0.00141 | [0.00102, 0.00182] | 0.578 | 0.328 | 0.730 | 3655 | 141 |
| final | no | trailing | backward_medium | -0.00914 | [-0.01030, -0.00783] | 0.155 | 0.215 | -3.690 | 1508 | 125 |
| final | no | trailing | backward_short | -0.00618 | [-0.00762, -0.00474] | 0.266 | 0.270 | -1.999 | 1268 | 126 |
| final | no | trailing | forward_medium | -0.00388 | [-0.00745, -0.00042] | 0.531 | 0.142 | -0.757 | 637 | 112 |
| final | no | trailing | forward_short | -0.00284 | [-0.00432, -0.00113] | 0.472 | 0.193 | -0.851 | 1105 | 124 |
| final | no | trailing | lateral_long | -0.00205 | [-0.00259, -0.00145] | 0.381 | 0.143 | -1.196 | 2283 | 126 |
| final | no | trailing | lateral_medium | 0.00142 | [0.00059, 0.00221] | 0.561 | 0.339 | 0.853 | 2341 | 126 |
| final | no | trailing | lateral_short | 0.00154 | [0.00096, 0.00219] | 0.570 | 0.332 | 0.693 | 1747 | 125 |
| final | yes | leading | backward_short | -0.00786 | [-0.01126, -0.00466] | 0.256 | 0.335 | -0.773 | 238 | 90 |
| final | yes | leading | lateral_medium | 0.00043 | [-0.00110, 0.00193] | 0.541 | 0.272 | 0.055 | 399 | 111 |
| final | yes | leading | lateral_short | 0.00250 | [0.00090, 0.00428] | 0.552 | 0.347 | 0.280 | 324 | 105 |
| final | yes | level | backward_medium | -0.00575 | [-0.00738, -0.00406] | 0.195 | 0.214 | -0.557 | 436 | 112 |
| final | yes | level | backward_short | -0.00441 | [-0.00571, -0.00315] | 0.297 | 0.326 | -0.427 | 481 | 119 |
| final | yes | level | forward_short | -0.00450 | [-0.00590, -0.00299] | 0.435 | 0.202 | -0.424 | 439 | 115 |
| final | yes | level | lateral_medium | 0.00033 | [-0.00042, 0.00106] | 0.510 | 0.266 | 0.050 | 885 | 125 |
| final | yes | level | lateral_short | 0.00060 | [-0.00022, 0.00142] | 0.544 | 0.353 | 0.076 | 671 | 119 |
| final | yes | trailing | backward_short | -0.00543 | [-0.00746, -0.00328] | 0.313 | 0.292 | -0.482 | 252 | 98 |
| final | yes | trailing | lateral_medium | 0.00119 | [-0.00031, 0.00276] | 0.550 | 0.250 | 0.152 | 422 | 115 |
| final | yes | trailing | lateral_short | 0.00037 | [-0.00122, 0.00206] | 0.533 | 0.351 | 0.038 | 315 | 107 |
| middle | no | leading | backward_medium | -0.00620 | [-0.00711, -0.00527] | 0.213 | 0.152 | -5.913 | 3386 | 121 |
| middle | no | leading | backward_short | -0.00316 | [-0.00366, -0.00264] | 0.287 | 0.223 | -3.305 | 3878 | 125 |
| middle | no | leading | forward_medium | -0.00241 | [-0.00282, -0.00196] | 0.303 | 0.152 | -2.817 | 4404 | 125 |
| middle | no | leading | forward_short | -0.00257 | [-0.00302, -0.00208] | 0.272 | 0.208 | -2.975 | 4320 | 125 |
| middle | no | leading | lateral_long | -0.00027 | [-0.00043, -0.00014] | 0.395 | 0.130 | -0.575 | 7760 | 121 |
| middle | no | leading | lateral_medium | 0.00060 | [0.00046, 0.00075] | 0.545 | 0.308 | 1.169 | 7392 | 126 |
| middle | no | leading | lateral_short | -0.00007 | [-0.00028, 0.00015] | 0.468 | 0.330 | -0.117 | 5914 | 124 |
| middle | no | level | backward_long | -0.01012 | [-0.01095, -0.00918] | 0.083 | 0.060 | -3.050 | 1642 | 133 |
| middle | no | level | backward_medium | -0.00745 | [-0.00782, -0.00703] | 0.143 | 0.158 | -7.404 | 7171 | 143 |
| middle | no | level | backward_short | -0.00372 | [-0.00401, -0.00342] | 0.260 | 0.212 | -3.732 | 7425 | 144 |
| middle | no | level | forward_long | -0.00375 | [-0.00423, -0.00331] | 0.220 | 0.070 | -1.247 | 1861 | 137 |
| middle | no | level | forward_medium | -0.00358 | [-0.00378, -0.00336] | 0.211 | 0.154 | -3.791 | 7857 | 144 |
| middle | no | level | forward_short | -0.00265 | [-0.00290, -0.00240] | 0.278 | 0.206 | -2.756 | 7715 | 143 |
| middle | no | level | lateral_long | -0.00026 | [-0.00032, -0.00019] | 0.355 | 0.135 | -0.534 | 15384 | 144 |
| middle | no | level | lateral_medium | 0.00070 | [0.00060, 0.00079] | 0.536 | 0.353 | 1.261 | 13467 | 144 |
| middle | no | level | lateral_short | 0.00009 | [-0.00001, 0.00020] | 0.478 | 0.314 | 0.137 | 11020 | 144 |
| middle | no | trailing | backward_medium | -0.01319 | [-0.01459, -0.01181] | 0.128 | 0.164 | -14.537 | 4234 | 126 |
| middle | no | trailing | backward_short | -0.00735 | [-0.00855, -0.00618] | 0.238 | 0.194 | -7.154 | 3894 | 128 |
| middle | no | trailing | forward_medium | -0.00479 | [-0.00572, -0.00395] | 0.243 | 0.155 | -4.063 | 3323 | 127 |
| middle | no | trailing | forward_short | -0.00268 | [-0.00359, -0.00176] | 0.354 | 0.207 | -2.256 | 3370 | 127 |
| middle | no | trailing | lateral_long | 0.00001 | [-0.00016, 0.00018] | 0.355 | 0.152 | 0.011 | 7213 | 128 |
| middle | no | trailing | lateral_medium | 0.00114 | [0.00093, 0.00134] | 0.537 | 0.350 | 1.840 | 6499 | 128 |
| middle | no | trailing | lateral_short | 0.00040 | [0.00014, 0.00062] | 0.496 | 0.302 | 0.526 | 5322 | 128 |
| middle | yes | leading | backward_medium | -0.00497 | [-0.00611, -0.00381] | 0.297 | 0.186 | -0.722 | 455 | 112 |
| middle | yes | leading | backward_short | -0.00211 | [-0.00281, -0.00146] | 0.331 | 0.242 | -0.387 | 614 | 115 |
| middle | yes | leading | forward_short | -0.00254 | [-0.00325, -0.00187] | 0.298 | 0.238 | -0.488 | 610 | 112 |
| middle | yes | leading | lateral_long | 0.00002 | [-0.00024, 0.00028] | 0.429 | 0.111 | 0.005 | 893 | 118 |
| middle | yes | leading | lateral_medium | 0.00086 | [0.00054, 0.00120] | 0.541 | 0.250 | 0.239 | 1001 | 122 |
| middle | yes | leading | lateral_short | 0.00002 | [-0.00043, 0.00055] | 0.428 | 0.328 | 0.005 | 771 | 121 |
| middle | yes | level | backward_medium | -0.00662 | [-0.00742, -0.00583] | 0.232 | 0.169 | -1.036 | 943 | 131 |
| middle | yes | level | backward_short | -0.00360 | [-0.00412, -0.00311] | 0.283 | 0.249 | -0.637 | 1173 | 137 |
| middle | yes | level | forward_medium | -0.00240 | [-0.00291, -0.00186] | 0.357 | 0.149 | -0.396 | 1008 | 132 |
| middle | yes | level | forward_short | -0.00179 | [-0.00224, -0.00131] | 0.336 | 0.240 | -0.336 | 1253 | 136 |
| middle | yes | level | lateral_long | -0.00001 | [-0.00023, 0.00022] | 0.406 | 0.122 | -0.001 | 1806 | 138 |
| middle | yes | level | lateral_medium | 0.00077 | [0.00056, 0.00100] | 0.506 | 0.258 | 0.222 | 2025 | 140 |
| middle | yes | level | lateral_short | 0.00029 | [0.00003, 0.00056] | 0.456 | 0.326 | 0.068 | 1544 | 138 |
| middle | yes | trailing | backward_medium | -0.01219 | [-0.01447, -0.01009] | 0.197 | 0.191 | -1.803 | 467 | 108 |
| middle | yes | trailing | backward_short | -0.00696 | [-0.00884, -0.00533] | 0.289 | 0.264 | -1.121 | 526 | 112 |
| middle | yes | trailing | forward_short | -0.00114 | [-0.00251, 0.00014] | 0.383 | 0.252 | -0.189 | 546 | 114 |
| middle | yes | trailing | lateral_long | 0.00050 | [-0.00001, 0.00098] | 0.426 | 0.113 | 0.122 | 853 | 117 |
| middle | yes | trailing | lateral_medium | 0.00139 | [0.00082, 0.00200] | 0.514 | 0.251 | 0.341 | 920 | 126 |
| middle | yes | trailing | lateral_short | 0.00078 | [-0.00012, 0.00178] | 0.480 | 0.303 | 0.157 | 723 | 119 |

**The 10 candidates and their Step 4 descriptive context** (mean options
of type `k` per pass vs. mean options of the pass's own chosen type `j`;
club/tournament share):

| zone | pressure | game_state | type | G | P | s | L | n_passes | mean n(k) | mean n(j) | % club-focal | % tournament |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| defensive | no | trailing | lateral_short | 0.00140 | 0.549 | 0.337 | 0.707 | 1919 | 1.49 | 1.97 | 51.4% | 48.6% |
| final | no | leading | lateral_medium | 0.00157 | 0.563 | 0.302 | 1.063 | 2460 | 2.00 | 1.68 | 55.0% | 45.0% |
| final | no | leading | lateral_short | 0.00208 | 0.567 | 0.351 | 1.059 | 1875 | 1.54 | 1.84 | 57.6% | 42.4% |
| final | no | level | lateral_medium | 0.00103 | 0.554 | 0.349 | 0.697 | 4860 | 1.98 | 1.67 | 41.5% | 58.5% |
| final | no | level | lateral_short | 0.00141 | 0.578 | 0.328 | 0.730 | 3655 | 1.55 | 1.87 | 42.6% | 57.4% |
| final | no | trailing | lateral_medium | 0.00142 | 0.561 | 0.339 | 0.853 | 2341 | 2.01 | 1.71 | 47.5% | 52.5% |
| final | no | trailing | lateral_short | 0.00154 | 0.570 | 0.332 | 0.693 | 1747 | 1.53 | 1.90 | 46.1% | 53.9% |
| middle | no | leading | lateral_medium | 0.00060 | 0.545 | 0.308 | 1.169 | 7392 | 2.08 | 1.70 | 57.8% | 42.2% |
| middle | no | level | lateral_medium | 0.00070 | 0.536 | 0.353 | 1.261 | 13467 | 2.02 | 1.70 | 42.7% | 57.3% |
| middle | no | trailing | lateral_medium | 0.00114 | 0.537 | 0.350 | 1.840 | 6499 | 1.84 | 1.73 | 47.3% | 52.7% |

## 4. Deviations from the brief
None. The join was implemented exactly as specified (on candidate
position), the 107-pair table is unsorted by effect size, and no Gate D,
sensitivity check, or realized value was computed.

## 5. Problems and surprises

- **Floating-point round-trip noise in the join key.** `normalize_xy` is
  mathematically self-inverse, but re-applying it twice in IEEE-754
  double precision is not always bit-exact: on one sample match, an
  exact-float join on the recovered raw candidate position matched only
  97.4% of rows (diffs of order 1e-14 — e.g. `14.378239102762286` vs.
  `14.37823910276228`). Rounding both sides to 6 decimals before joining
  fixed this; verified 100.0% match rate at full discovery scale
  (616,038/616,038).
- **2 genuine duplicate-position collisions.** In 2 of the 85,746
  discovery passes, two distinct teammates in the same freeze frame are
  recorded at the exact same coordinates (confirmed identical `distance`
  too). A plain key-merge would have cross-joined these 2-into-2 groups
  into 4 rows each, inflating counts. I paired same-key duplicates
  positionally (an occurrence-rank tiebreaker on both sides) instead of
  cross-joining. This is inconsequential to every downstream statistic:
  I confirmed both duplicate rows in `options_ev.parquet` carry
  byte-identical `p_success` and `ev` (0.001332/0.001332 and
  0.004266/0.004266 respectively), since every model feature for an
  option is a function of its own position, which was identical for the
  pair.
- **`CLAUDE.md`'s "Reporting discipline" list is pre-existing truncated.**
  It stops mid-sentence at a numbered item "5." (line 92: "...must
  reflect the weakest evidence, not the most promising. If a"). The
  brief's Step 0.3 gives an exact verbatim item "9." to append; I
  appended it exactly as given, immediately after the truncated "5." —
  I did not invent items 6-8 or attempt to complete item 5's sentence,
  since that would be inventing content the research lead didn't
  provide. The file now has a "5." and a "9." with nothing between them.
  This predates this task and isn't something I'm positioned to fix.
- Nothing else was missing, broken, or malformed.

## 6. Questions for the research lead
None. Every definition in plan section 3 and Amendment v2-1 was
implementable exactly as written.

## 7. Files produced
- `data/processed/study_a_discovery.parquet` — the full 107-row pair
  table (all columns in Section 3's first table), sorted by cell then
  type. Gitignored (derived, not committed).
- `docs/results/05-study-a-candidates.csv` — the 10 candidates (columns:
  cell, type, G, CI, P, s, L). Committed at `e310785`.
- `data/task05_study_a_discovery.json` — full run summary (join report,
  analyzable-pair count, candidate descriptive context). Gitignored.
- `src/decision_engine/task05_study_a_discovery.py` — the script that
  produces all of the above.
- `CLAUDE.md` — appended item 9 to "Reporting discipline" (see Section 5).
- Git commits made this task: `74a794e` ("Track all code and docs
  through Task 04" — bulk commit of previously-untracked `src/`/`docs/`/
  `CLAUDE.md`), `71eb345` (Amendment v2-1 to `analysis-plan-v2.md`;
  `sha256 = 0c34743f30cbfde0c9c9b4d83ee409090c90a3259e68b773fef060c6183c2764`),
  `e310785` (the candidates CSV), `4394648` (this script and this
  results page, per the new `CLAUDE.md` item 9), and one further tiny
  commit recording `4394648`'s hash on this line (a commit cannot
  contain its own hash).

## 8. Confidence
High. The join match rate reached exactly 100% after accounting for and
resolving a real (if rare) floating-point/duplicate-position issue, both
independently verified rather than assumed away. The independently
re-derived analyzable-pair count (107) matches Task 04's exactly, which
is a strong cross-task consistency check. The bootstrap CI implementation
follows the brief's own stated implementation hint (per-match sums/counts,
then resample) precisely, and every one of the 107 pairs' 1,000 bootstrap
draws produced a valid (non-NaN) ratio. The weakest link is that this is
discovery-only: none of these 10 candidates have been checked against
confirmation data, Gate D, or any sensitivity check yet, so none should
be treated as a finding until Task 06.
