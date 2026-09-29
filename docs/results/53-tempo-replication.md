# Task 53: Tempo replication on the locked half (2015/16 La Liga, Serie A, Ligue 1) and praised-list name audit
Date: 2026-09-29
Status: COMPLETE (every step run; deviations in Section 4)

**This is the single use of the 2015/16 replication half.** The family (S1-S5, R1-R7, C1-C2) was fixed in the brief (8bc71aa) before any replication row was opened.
- The study replication half was not opened: the guard's study id set was empty, and a test call was refused.
- Holdout and reserved data untouched. Holdout names were not read either (Section 4).
- Existing comparators were read with a replication-league filter (listed in Section 3).

## Checklist
| Section | Status |
|---|---|
| Step 0: brief committed alone | COMPLETE (8bc71aa, by the research lead) |
| Step 1: praised-list ID audit, `docs/splits/praised_ids.csv`, check of earlier tests | COMPLETE (cdb6b1e; committed before any replication row was opened). Holdout: no player-level name table; not opened |
| Step 2: measures on the replication leagues, baselines refit on replication folds | COMPLETE (1,137 matches; 141 DMs) |
| Step 3: STABILITY S1-S5 | COMPLETE: 5 of 5 PASS |
| Step 3: RESULTS R1-R7 (Holm) | COMPLETE: R1, R4, R5, R6, R7 CONFIRMED; R2, R3 NOT CONFIRMED |
| Step 3: CULMINATION C1, C2; K1 matrix; PC1 share | COMPLETE: C1, C2 CONFIRMED |
| Step 4: D3 cells, K2, praised list by ID, DM tables, M2 sensitivity | COMPLETE |
| Memory gate (Task 25) | COMPLETE (build 52% / 4.23 GB; tests 49% / 4.44 GB) |

## 1. Headline
Replication, single use:
- **Stability:** all five claims pass within 141 deep midfielders (medians 0.688-0.898).
- **Results:** R1, R4, R5, R6 and R7 are CONFIRMED. R2 (M3_speed → Y_F3, DMs; Holm p 0.447) and R3 (M2 → POSS_XG, DMs; Holm p 0.206) are NOT CONFIRMED.
- **Culmination:** C1 (r -0.292) and C2 (r +0.686) are CONFIRMED. On the same pressured receptions, every M2 success (FK = 1) is also a PR2 keep (60,359 of 60,359), so C2 includes a correlation built into the two definitions.
- **Praised list:** the tests by ID rest on 4 present players, and none has p < 0.05.

## 2. What I did
Reproduce with (from `src/engine_v2/`):
1. `python task53_praised_audit.py`
2. `python -W ignore task53_build.py`
3. `python -W ignore task53_tests.py`

- **Step 1** (`task53_praised_audit.py`): read player-level tables only.
  - Tables: `leaderboard_v5c` (study), `pff/player_map.csv` (PFF map), `task44_roles` (2015/16, all five leagues, player-level), `task48_roles` (reserved).
  - For each of the 13 names it listed every Task 27 `name_matches` hit and every loose surname hit, and kept the one intended id.
  - Wrote `docs/splits/praised_ids.csv` and read each earlier test's included ids from its saved JSON. No test was re-run.
- **Step 2** (`task53_build.py`): Task 52's per-match builder (`task52_build.match_units`, unchanged definitions).
  - Its guard id sets were switched in place to the 1,137 replication ids, with the study set emptied. A call on a study match and on a 2015/16 development match was refused.
  - Every baseline was refit on replication folds (5 match folds, seed 20260929; sizes 228/228/227/227/227): g_T, the M2 FK classifiers at 1.0 / 1.5 / 2.0 s, and the four M4 category classifiers.
  - M1, M5 and M6 were not built (M6's raw columns were dropped).
  - M2 sensitivity: pressured receptions whose spell ends in his Pass or a loss, with the baseline refit on those units.
- **Steps 3-4** (`task53_tests.py`): Task 52's test helpers, unchanged.
  - DMs: Task 44's rule on replication eligible passes.
  - S1-S5: Task 38's R1 within DMs, >= 10 matches.
  - R1-R7: `fe_fit`, or `fit_multi` for R1 with [M4_SWITCH, PR2_flag_keep]. Completion control for passes, retention control for receptions, on the same rows. Holm across R1-R7.
  - C1 / C2 and K1: player-level r within DMs, 1,000-player bootstrap (seed 20260929). Disattenuated only when both D1 reliabilities are >= 0.30; never clipped.
  - Report only: K2 (`fit_multi`); praised list with `perm_test` by ID; Task 29 DM tables (`task42_step2.dm_table`).

## 3. Numbers
### Step 1: praised-list ID audit

| List name | intended player_id | name in data | present in (player-level tables) | other exact `name_matches` hits (not intended) | loose surname-only hits |
|---|---|---|---|---|---|
| Kroos | 5574 | Toni Kroos | 2015/16;reserved;study | none | 0 |
| Modric | 5463 | Luka Modrić | 2015/16;pff_map;reserved;study | none | 0 |
| Verratti | 3166 | Marco Verratti | 2015/16;study | none | 0 |
| Busquets | 5203 | Sergio Busquets i Burgos | 2015/16;pff_map;reserved;study | none | 0 |
| De Bruyne | 3089 | Kevin De Bruyne | 2015/16;pff_map;reserved;study | none | 0 |
| Xhaka | 3500 | Granit Xhaka | 2015/16;pff_map;reserved;study | none | 0 |
| de Jong | 8118 | Frenkie de Jong | pff_map;reserved;study | 2015/16 8061 Siem Stefan de Jong; 2015/16 20057 Nigel de Jong; pff_map 20033 Luuk de Jong | 1 |
| Kimmich | 5579 | Joshua Kimmich | pff_map;reserved;study | none | 0 |
| Rodri | 6765 | Rodrigo Hernández Cascante | pff_map;reserved;study | none | 71 |
| Pedri | 30486 | Pedro González López | pff_map;study | none | 36 |
| Gundogan | 10287 | İlkay Gündoğan | pff_map;reserved;study | none | 0 |
| Grillitsch | 11396 | Florian Grillitsch | study | none | 0 |
| Shaparenko | 21294 | Mykola Shaparenko | study | none | 0 |

Earlier praised-list tests, ids actually included (from the saved JSONs; no test re-run):

| Test cell | ids included | not intended |
|---|---|---|
| Task 41 step7.v5_decision | 3089, 3166, 3500, 5203, 5463, 5574, 5579, 6765, 8118, 10287, 11396, 21294, 30486 | none |
| Task 41 step7.rq_rel | 3089, 3166, 3500, 5203, 5463, 5574, 5579, 6765, 8118, 10287, 11396, 21294, 30486 | none |
| Task 41 step7.AV | 3089, 3500, 5203, 5463, 5579, 6765, 8118, 10287, 30486 | none |
| Task 41 step7.AV_vis | 3089, 3500, 5203, 5463, 5579, 6765, 8118, 10287, 30486 | none |
| Task 42 r3.pr_keep | 3089, 3166, 3500, 5203, 5463, 5574, 5579, 6765, 8118, 10287, 30486 | none |
| Task 42 r3.pr_fwd | 3089, 3166, 3500, 5203, 5463, 5574, 5579, 6765, 8118, 10287, 30486 | none |
| Task 42 (PFF) praised_list | 3089, 3500, 5203, 5463, 5579, 6765, 8118, 10287, 30486 | none |
| Task 43 step4.pr2_keep | 3089, 3166, 3500, 5203, 5463, 5574, 5579, 6765, 8118, 10287, 30486 | none |
| Task 43 step4.pr2_fwd | 3089, 3166, 3500, 5203, 5463, 5574, 5579, 6765, 8118, 10287, 30486 | none |
| Task 44 praised.move_on_speed | 3089, 3166, 5203, 5463, 5574 | none |
| Task 44 praised.hold_variation | 3089, 3166, 5203, 5463, 5574 | none |
| Task 44 praised.pr2_flag_keep | 3089, 3166, 5203, 5463, 5574 | none |
| Task 44 praised.pr2_flag_fwd | 3089, 3166, 5203, 5463, 5574 | none |
| Task 45 steps1_2.unadjusted | 3089, 3166, 5203, 5463, 5574 | none |
| Task 45 steps1_2.A1 | 3089, 3166, 5203, 5463, 5574 | none |
| Task 45 steps1_2.A2 | 3089, 3166, 5203, 5463, 5574 | none |
| Task 48 report_only.praised_pr2_flag_keep | 3089, 3500, 5203, 5463, 5574, 5579, 6765, 8118 | none |
| Task 48 report_only.praised_w | 3089, 3500, 5203, 5463, 5574, 5579, 6765, 8118 | none |
| Task 52 2015/16.D5.M2 | 3089 | none |
| Task 52 2015/16.D5.M2_1.0 | 3089 | none |
| Task 52 2015/16.D5.M2_2.0 | 3089 | none |
| Task 52 2015/16.D5.M3_speed | 3089 | none |
| Task 52 2015/16.D5.M3_var | 3089 | none |
| Task 52 2015/16.D5.M4_ACCEL | 3089, 3500, 8061 | 8061 |
| Task 52 2015/16.D5.M4_KEEP | 3089, 3500, 8061 | 8061 |
| Task 52 2015/16.D5.M4_SLOW | 3089, 3500, 8061 | 8061 |
| Task 52 2015/16.D5.M4_SWITCH | 3089, 3500, 8061 | 8061 |
| Task 52 2015/16.D5.M6 | 3089 | none |
| Task 52 2015/16.D5.M6_on_SLOW | 3089 | none |
| Task 52 2015/16.D5.MOVE_ON_SPEED | 3089 | none |
| Task 52 study.D5.M2 | 3089, 3166, 3500, 5203, 5463, 5579, 6765, 8118, 11396, 30486 | none |
| Task 52 study.D5.M2_1.0 | 3089, 3166, 3500, 5203, 5463, 5579, 6765, 8118, 11396, 30486 | none |
| Task 52 study.D5.M2_2.0 | 3089, 3166, 3500, 5203, 5463, 5579, 6765, 8118, 11396, 30486 | none |
| Task 52 study.D5.M3_speed | 3089, 3166, 3500, 5203, 5463, 5574, 5579, 6765, 8118, 10287, 11396, 21294, 30486 | none |
| Task 52 study.D5.M3_var | 3089, 3166, 3500, 5203, 5463, 5574, 5579, 6765, 8118, 10287, 11396, 21294, 30486 | none |
| Task 52 study.D5.M4_ACCEL | 3089, 3166, 3500, 5203, 5463, 5574, 5579, 6765, 8118, 10287, 11396, 21294, 30486 | none |
| Task 52 study.D5.M4_KEEP | 3089, 3166, 3500, 5203, 5463, 5574, 5579, 6765, 8118, 10287, 11396, 21294, 30486 | none |
| Task 52 study.D5.M4_SLOW | 3089, 3166, 3500, 5203, 5463, 5574, 5579, 6765, 8118, 10287, 11396, 21294, 30486 | none |
| Task 52 study.D5.M4_SWITCH | 3089, 3166, 3500, 5203, 5463, 5574, 5579, 6765, 8118, 10287, 11396, 21294, 30486 | none |
| Task 52 study.D5.M6 | 3089, 3166, 3500, 5203, 5463, 5574, 5579, 6765, 8118, 10287, 11396, 21294, 30486 | none |
| Task 52 study.D5.M6_on_ACCEL | 3166, 3500 | none |
| Task 52 study.D5.M6_on_SLOW | 3166, 3500, 5203, 5579 | none |
| Task 52 study.D5.MOVE_ON_SPEED | 3166, 3500, 5203, 5463, 5574, 5579, 6765, 8118, 30486 | none |
| Task 52 study.D5.M1 | 3089, 3166, 3500, 5203, 5463, 5574, 5579, 6765, 8118, 10287, 11396, 21294, 30486 | none |
| Task 52 study.D5.M5 | 3089, 3166, 3500, 5203, 5463, 5574, 5579, 6765, 8118, 10287, 11396, 21294, 30486 | none |

Name-matching notes saved by earlier tasks: Task 44 praised_list_matches['de Jong'] = ['Siem Stefan de Jong', 'Nigel de Jong']; Task 48 praised_list_matches['de Jong'] = ['Frenkie de Jong'].

### Step 2: replication build (2015/16 La Liga, Serie A, Ligue 1)

- Matches 1,137 (fold sizes {'0': 228, '1': 228, '2': 227, '3': 227, '4': 227}); players with completed receptions 1,639; with eligible passes 1,500; with a role (>= 100 eligible passes) 1257; **deep midfielders 141** (Task 44's rule within the replication leagues).
- Completed receptions 853,633; spell ends: pass 745,071, loss 68,555, shot 19,845, foul 16,795, other_on_ball 3,172, period_end 195. Timed (0 < T <= 15) 652,120: median 1.28 s [q25 0.65, q75 2.24]; T <= 0 excluded 92,816; T > 15 excluded 135. g_T out-of-fold R^2 0.061.
- Pressured completed receptions (M2 units) 247,429; FK base rate / baseline AUC at 1.0, 1.5, 2.0 s: 0.163/0.635, 0.244/0.611, 0.298/0.612. Sensitivity units (pass or loss endings) 220,895, base rate 0.273, AUC 0.602.
- Eligible passes 945,785; M4 baseline AUC ACCEL 0.643, KEEP 0.582, SLOW 0.617, SWITCH 0.674.
- Pass-category shares, all / DM: ACCEL 0.205 / 0.196; KEEP 0.547 / 0.563; SLOW 0.221 / 0.209; SWITCH 0.027 / 0.033.

Players meeting each floor (all / DM): M2 1160 / 141; M2_1.0 1160 / 141; M2_2.0 1160 / 141; M2_sens 1127 / 141; M3_speed 1255 / 141; M3_var 1255 / 141; M4_ACCEL 1257 / 141; M4_KEEP 1257 / 141; M4_SLOW 1257 / 141; M4_SWITCH 1257 / 141; PR2_flag_keep 1147 / 141; W 1324 / 141.

### Step 3: pre-registered family

**STABILITY** (Task 38's method, DMs, >= 10 matches; PASS if median >= 0.60)

| Claim | measure | n DMs | median | p5 | p95 | result |
|---|---|---|---|---|---|---|
| S1 | M4_ACCEL | 141 | 0.898 | 0.876 | 0.918 | PASS |
| S2 | M4_SLOW | 141 | 0.844 | 0.808 | 0.873 | PASS |
| S3 | M4_SWITCH | 141 | 0.830 | 0.790 | 0.867 | PASS |
| S4 | M3_speed | 141 | 0.806 | 0.765 | 0.847 | PASS |
| S5 | M2 | 141 | 0.688 | 0.625 | 0.748 | PASS |

**RESULTS** (per 100 units per SD of other-match S; Holm across R1-R7)

| Claim | group | measure -> outcome | stated sign | coef | 95% CI | p | Holm p | n rows / players | control coef [95% CI] (p) | result |
|---|---|---|---|---|---|---|---|---|---|---|
| R1 | DM | M4_SWITCH -> Y_F3 (with PR2_flag_keep) | > 0 | +0.7430 | [+0.4128, +1.0731] | 1.03e-05 | 3.09e-05 | 145,936 / 141 | +3.072 [+2.572, +3.572] (2.2e-33) | CONFIRMED |
| R2 | DM | M3_speed -> Y_F3 | < 0 | -0.1468 | [-0.5251, +0.2315] | 0.447 | 0.447 | 117,210 / 141 | +2.913 [+2.397, +3.430] (2.1e-28) | NOT CONFIRMED |
| R3 | DM | M2 -> POSS_XG | > 0 | +0.0309 | [-0.0063, +0.0682] | 0.103 | 0.206 | 133,368 / 141 | +2.859 [+2.392, +3.327] (4e-33) | NOT CONFIRMED |
| R4 | all | M4_ACCEL -> Y_F3 | > 0 | +0.6274 | [+0.4464, +0.8084] | 1.1e-11 | 7.71e-11 | 728,072 / 1248 | +4.123 [+3.915, +4.331] (0) | CONFIRMED |
| R5 | all | M4_SLOW -> Y_F3 | < 0 | -0.6239 | [-0.8218, -0.4261] | 6.37e-10 | 3.82e-09 | 728,072 / 1248 | +4.123 [+3.915, +4.331] (0) | CONFIRMED |
| R6 | all | M4_SWITCH -> Y_F3 | > 0 | +0.3684 | [+0.2234, +0.5133] | 6.32e-07 | 2.53e-06 | 728,072 / 1248 | +4.123 [+3.915, +4.331] (0) | CONFIRMED |
| R7 | all | M2 -> Y_F3 | > 0 | +0.6314 | [+0.4244, +0.8385] | 2.29e-09 | 1.14e-08 | 585,744 / 1149 | +7.078 [+6.741, +7.415] (0) | CONFIRMED |

R1's PR2_flag_keep coefficient in the same model: +0.3551 [+0.0298, +0.6804], p 0.0324.

**CULMINATION** (DMs; 1,000-player bootstrap 95% CI)

| Claim | pair | stated sign | n | r | 95% CI | result |
|---|---|---|---|---|---|---|
| C1 | PR2_flag_keep|M4_ACCEL | < 0 | 141 | -0.292 | [-0.439, -0.122] | CONFIRMED |
| C2 | PR2_flag_keep|M2 | > 0 | 141 | +0.686 | [+0.597, +0.763] | CONFIRMED |

**K1 full matrix (DMs).** D1 reliabilities (DM): PR2_flag_keep 0.674, W 0.763, M2 0.688, M3_speed 0.806, M4_ACCEL 0.898, M4_SLOW 0.844, M4_SWITCH 0.830. Disattenuated only when both >= 0.30; never clipped.

| Pair | n | r [95% boot CI] | disattenuated r [95% boot CI] |
|---|---|---|---|
| PR2_flag_keep|W | 141 | -0.216 [-0.357, -0.055] | -0.301 [-0.497, -0.077] |
| PR2_flag_keep|M2 | 141 | +0.686 [+0.597, +0.763] | 1.007 [+0.876, +1.120] |
| PR2_flag_keep|M3_speed | 141 | -0.231 [-0.390, -0.046] | -0.314 [-0.530, -0.062] |
| PR2_flag_keep|M4_ACCEL | 141 | -0.292 [-0.439, -0.122] | -0.375 [-0.564, -0.157] |
| PR2_flag_keep|M4_SLOW | 141 | +0.154 [-0.009, +0.302] | 0.205 [-0.011, +0.400] |
| PR2_flag_keep|M4_SWITCH | 141 | +0.060 [-0.103, +0.235] | 0.080 [-0.138, +0.314] |
| W|M2 | 141 | -0.321 [-0.459, -0.177] | -0.443 [-0.633, -0.244] |
| W|M3_speed | 141 | -0.274 [-0.421, -0.118] | -0.350 [-0.537, -0.150] |
| W|M4_ACCEL | 141 | -0.062 [-0.200, +0.075] | -0.075 [-0.241, +0.091] |
| W|M4_SLOW | 141 | +0.118 [-0.028, +0.266] | 0.148 [-0.035, +0.331] |
| W|M4_SWITCH | 141 | +0.018 [-0.177, +0.205] | 0.023 [-0.222, +0.258] |
| M2|M3_speed | 141 | +0.237 [+0.058, +0.400] | 0.318 [+0.077, +0.537] |
| M2|M4_ACCEL | 141 | -0.049 [-0.215, +0.133] | -0.062 [-0.273, +0.169] |
| M2|M4_SLOW | 141 | +0.100 [-0.073, +0.263] | 0.131 [-0.096, +0.346] |
| M2|M4_SWITCH | 141 | -0.068 [-0.239, +0.142] | -0.090 [-0.317, +0.188] |
| M3_speed|M4_ACCEL | 141 | +0.245 [+0.098, +0.380] | 0.288 [+0.116, +0.447] |
| M3_speed|M4_SLOW | 141 | -0.049 [-0.202, +0.118] | -0.059 [-0.245, +0.143] |
| M3_speed|M4_SWITCH | 141 | -0.234 [-0.377, -0.074] | -0.287 [-0.461, -0.091] |
| M4_ACCEL|M4_SLOW | 141 | -0.598 [-0.692, -0.489] | -0.687 [-0.794, -0.562] |
| M4_ACCEL|M4_SWITCH | 141 | +0.159 [+0.001, +0.311] | 0.184 [+0.001, +0.360] |
| M4_SLOW|M4_SWITCH | 141 | -0.084 [-0.237, +0.052] | -0.100 [-0.282, +0.062] |

PC1 share of variance, {PR2_flag_keep, W, M4_ACCEL, M2}: 0.474 (n 141 DMs; eigenvalues 1.898, 1.101, 0.733, 0.269).

### Step 4: report only

**D1, all measures** (DM / all; players >= 10 matches)

| Measure | DM: n, median [p5, p95] | all: n, median [p5, p95] |
|---|---|---|
| M2 | 141, 0.688 [0.625, 0.748] | 1193, 0.678 [0.652, 0.705] |
| M2_1.0 | 141, 0.619 [0.535, 0.694] | 1193, 0.596 [0.558, 0.627] |
| M2_2.0 | 141, 0.693 [0.625, 0.747] | 1193, 0.706 [0.681, 0.732] |
| M2_sens | 141, 0.646 [0.561, 0.695] | 1188, 0.656 [0.625, 0.689] |
| M3_speed | 141, 0.806 [0.765, 0.847] | 1214, 0.807 [0.793, 0.828] |
| M3_var | 141, 0.681 [0.630, 0.751] | 1214, 0.855 [0.841, 0.865] |
| M4_ACCEL | 141, 0.898 [0.876, 0.918] | 1151, 0.883 [0.874, 0.892] |
| M4_KEEP | 141, 0.835 [0.796, 0.869] | 1151, 0.743 [0.719, 0.763] |
| M4_SLOW | 141, 0.844 [0.808, 0.873] | 1151, 0.872 [0.861, 0.881] |
| M4_SWITCH | 141, 0.830 [0.790, 0.867] | 1151, 0.715 [0.685, 0.737] |
| PR2_flag_keep | 141, 0.674 [0.605, 0.742] | 1191, 0.755 [0.733, 0.774] |
| W | 141, 0.763 [0.730, 0.800] | 1223, 0.926 [0.919, 0.930] |

**D3 cells** (receptions for M2/M3, passes for M4)

| Measure | group | outcome | coef | 95% CI | p | n rows / players | control coef (p) | dummy check within / dummies |
|---|---|---|---|---|---|---|---|---|
| M2 | DM | y_f3 | +0.5279 | [+0.0206, +1.0352] | 0.0414 | 116,677 / 141 | +2.956 (5.1e-30) | +0.01040 / +0.01040 |
| M2 | DM | poss_xg | +0.0309 | [-0.0063, +0.0682] | 0.103 | 133,368 / 141 | +2.859 (4e-33) | +0.00160 / +0.00160 |
| M2 | all | y_f3 | +0.6314 | [+0.4244, +0.8385] | 2.29e-09 | 585,744 / 1149 | +7.078 (0) | +0.00970 / +0.00970 |
| M2 | all | poss_xg | +0.0009 | [-0.0191, +0.0209] | 0.932 | 786,596 / 1149 | +7.390 (0) | +0.00081 / +0.00081 |
| M3_speed | DM | y_f3 | -0.1468 | [-0.5251, +0.2315] | 0.447 | 117,210 / 141 | +2.913 (2.1e-28) | +0.01597 / +0.01597 |
| M3_speed | DM | poss_xg | +0.0059 | [-0.0338, +0.0456] | 0.769 | 133,963 / 141 | +2.831 (1.5e-32) | -0.00288 / -0.00288 |
| M3_speed | all | y_f3 | -0.1200 | [-0.2902, +0.0501] | 0.167 | 624,690 / 1250 | +7.030 (0) | +0.00656 / +0.00656 |
| M3_speed | all | poss_xg | -0.0352 | [-0.0540, -0.0163] | 0.000252 | 825,678 / 1250 | +7.370 (0) | +0.00007 / +0.00007 |
| M3_var | DM | y_f3 | +0.0875 | [-0.4094, +0.5844] | 0.73 | 117,210 / 141 | +2.913 (2.1e-28) | +0.02930 / +0.02930 |
| M3_var | DM | poss_xg | -0.0238 | [-0.0676, +0.0199] | 0.285 | 133,963 / 141 | +2.831 (1.5e-32) | -0.00073 / -0.00073 |
| M3_var | all | y_f3 | -0.5930 | [-0.8643, -0.3216] | 1.84e-05 | 624,690 / 1250 | +7.030 (0) | -0.00425 / -0.00425 |
| M3_var | all | poss_xg | -0.0279 | [-0.0539, -0.0018] | 0.0361 | 825,678 / 1250 | +7.370 (0) | -0.00032 / -0.00032 |
| M4_ACCEL | DM | y_f3 | +0.4438 | [+0.0781, +0.8095] | 0.0174 | 146,894 / 141 | +3.046 (6.6e-33) | -0.00884 / -0.00884 |
| M4_ACCEL | DM | poss_xg | -0.0278 | [-0.0643, +0.0088] | 0.136 | 167,786 / 141 | +3.048 (7.3e-40) | +0.00158 / +0.00158 |
| M4_ACCEL | all | y_f3 | +0.6274 | [+0.4464, +0.8084] | 1.1e-11 | 728,072 / 1248 | +4.123 (0) | -0.00020 / -0.00020 |
| M4_ACCEL | all | poss_xg | +0.0070 | [-0.0105, +0.0245] | 0.433 | 932,979 / 1248 | +4.522 (0) | +0.00131 / +0.00131 |
| M4_SLOW | DM | y_f3 | -0.3976 | [-0.7400, -0.0552] | 0.0228 | 146,894 / 141 | +3.046 (6.6e-33) | +0.01729 / +0.01729 |
| M4_SLOW | DM | poss_xg | +0.0200 | [-0.0119, +0.0519] | 0.22 | 167,786 / 141 | +3.048 (7.3e-40) | +0.00114 / +0.00114 |
| M4_SLOW | all | y_f3 | -0.6239 | [-0.8218, -0.4261] | 6.37e-10 | 728,072 / 1248 | +4.123 (0) | -0.00810 / -0.00810 |
| M4_SLOW | all | poss_xg | -0.0012 | [-0.0222, +0.0198] | 0.911 | 932,979 / 1248 | +4.522 (0) | -0.00026 / -0.00026 |
| M4_SWITCH | DM | y_f3 | +0.7218 | [+0.3814, +1.0623] | 3.25e-05 | 146,894 / 141 | +3.046 (6.6e-33) | +0.00339 / +0.00339 |
| M4_SWITCH | DM | poss_xg | -0.0323 | [-0.0732, +0.0085] | 0.121 | 167,786 / 141 | +3.048 (7.3e-40) | +0.00275 / +0.00275 |
| M4_SWITCH | all | y_f3 | +0.3684 | [+0.2234, +0.5133] | 6.32e-07 | 728,072 / 1248 | +4.123 (0) | +0.00018 / +0.00018 |
| M4_SWITCH | all | poss_xg | +0.0061 | [-0.0087, +0.0209] | 0.419 | 932,979 / 1248 | +4.522 (0) | +0.00131 / +0.00131 |

**K2** (DM passes; per 100 passes per SD; same rows within each measure)

| Measure | outcome | n rows / players | tempo alone | tempo with PR2_flag_keep | PR2 alone | PR2 with tempo |
|---|---|---|---|---|---|---|
| M2 | y_f3 | 145,936 / 141 | +0.190 [-0.191, +0.570] p 0.33 | +0.050 [-0.447, +0.547] p 0.84 | +0.256 [-0.096, +0.608] p 0.15 | +0.218 [-0.246, +0.682] p 0.36 |
| M3_speed | y_f3 | 145,920 / 141 | -0.150 [-0.443, +0.143] p 0.32 | -0.115 [-0.417, +0.187] p 0.46 | +0.259 [-0.093, +0.612] p 0.15 | +0.236 [-0.124, +0.596] p 0.2 |
| M3_var | y_f3 | 145,920 / 141 | +0.149 [-0.279, +0.577] p 0.5 | +0.197 [-0.235, +0.629] p 0.37 | +0.259 [-0.093, +0.612] p 0.15 | +0.295 [-0.063, +0.652] p 0.11 |
| M4_ACCEL | y_f3 | 145,936 / 141 | +0.441 [+0.071, +0.811] p 0.02 | +0.495 [+0.121, +0.870] p 0.0095 | +0.256 [-0.096, +0.608] p 0.15 | +0.340 [+0.001, +0.679] p 0.049 |
| M4_SLOW | y_f3 | 145,936 / 141 | -0.409 [-0.756, -0.063] p 0.02 | -0.425 [-0.779, -0.070] p 0.019 | +0.256 [-0.096, +0.608] p 0.15 | +0.288 [-0.044, +0.620] p 0.089 |
| M4_SWITCH | y_f3 | 145,936 / 141 | +0.705 [+0.356, +1.054] p 7.7e-05 | +0.743 [+0.413, +1.073] p 1e-05 | +0.256 [-0.096, +0.608] p 0.15 | +0.355 [+0.030, +0.680] p 0.032 |
| M2 | poss_xg | 166,724 / 141 | +0.050 [+0.010, +0.089] p 0.014 | +0.097 [+0.044, +0.150] p 0.00036 | -0.000 [-0.045, +0.045] p 1 | -0.074 [-0.133, -0.014] p 0.016 |
| M3_speed | poss_xg | 166,707 / 141 | +0.011 [-0.026, +0.048] p 0.57 | +0.011 [-0.026, +0.048] p 0.56 | -0.000 [-0.046, +0.045] p 0.98 | +0.002 [-0.044, +0.048] p 0.94 |
| M3_var | poss_xg | 166,707 / 141 | -0.013 [-0.055, +0.028] p 0.53 | -0.014 [-0.057, +0.030] p 0.54 | -0.000 [-0.046, +0.045] p 0.98 | -0.003 [-0.050, +0.044] p 0.91 |
| M4_ACCEL | poss_xg | 166,724 / 141 | -0.031 [-0.068, +0.006] p 0.1 | -0.032 [-0.070, +0.007] p 0.11 | -0.000 [-0.045, +0.045] p 1 | -0.005 [-0.052, +0.042] p 0.83 |
| M4_SLOW | poss_xg | 166,724 / 141 | +0.022 [-0.010, +0.054] p 0.19 | +0.022 [-0.010, +0.054] p 0.18 | -0.000 [-0.045, +0.045] p 1 | -0.002 [-0.046, +0.043] p 0.94 |
| M4_SWITCH | poss_xg | 166,724 / 141 | -0.037 [-0.078, +0.004] p 0.074 | -0.037 [-0.079, +0.004] p 0.074 | -0.000 [-0.045, +0.045] p 1 | -0.005 [-0.050, +0.040] p 0.83 |

**Praised list by ID** (docs/splits/praised_ids.csv; Task 41's perm_test)

| Measure | declared direction | n qualifying | n present | T | p (two-sided) | present |
|---|---|---|---|---|---|---|
| M2 | higher | 1101 | 4 | +0.748 | 0.131 | Marco Verratti, Sergio Busquets i Burgos, Luka Modrić, Toni Kroos |
| M3_speed | none | 1189 | 4 | -0.771 | 0.116 | Marco Verratti, Sergio Busquets i Burgos, Luka Modrić, Toni Kroos |
| M3_var | none | 1189 | 4 | -0.277 | 0.574 | Marco Verratti, Sergio Busquets i Burgos, Luka Modrić, Toni Kroos |
| M4_ACCEL | none | 1257 | 4 | -0.662 | 0.182 | Marco Verratti, Sergio Busquets i Burgos, Luka Modrić, Toni Kroos |
| M4_SLOW | none | 1257 | 4 | -0.326 | 0.519 | Marco Verratti, Sergio Busquets i Burgos, Luka Modrić, Toni Kroos |
| M4_SWITCH | none | 1257 | 4 | +0.469 | 0.328 | Marco Verratti, Sergio Busquets i Burgos, Luka Modrić, Toni Kroos |
| M4_KEEP | none | 1257 | 4 | +0.890 | 0.0721 | Marco Verratti, Sergio Busquets i Burgos, Luka Modrić, Toni Kroos |

**Deep-midfield tables (Task 29's method via task42_step2.dm_table) for measures passing their stability claim.** Values are per unit (M3_speed = -r). Top 10, bottom 5 and every praised-list player by ID.

*M4_ACCEL*: 141 DMs; group mean -0.0139; tau^2 0.00193; Q 1731.4 (140 df); clearly above 46, clearly below 39.

| rank | player | matches | units | raw mean | shrunk | 90% interval | praised |
|---|---|---|---|---|---|---|---|
| 1 | Étienne Didot | 23 | 1090 | +0.1013 | +0.0912 | [+0.0699, +0.1126] |  |
| 2 | Fernando Damián Tissone | 12 | 542 | +0.1026 | +0.0840 | [+0.0550, +0.1129] |  |
| 3 | Isaac Cofie | 29 | 901 | +0.0836 | +0.0743 | [+0.0519, +0.0967] |  |
| 4 | Daniel García Carrillo | 35 | 1702 | +0.0676 | +0.0628 | [+0.0454, +0.0803] |  |
| 5 | Robert Gucher | 24 | 508 | +0.0702 | +0.0576 | [+0.0296, +0.0856] |  |
| 6 | Rubén Salvador Pérez Del Mármol | 31 | 1350 | +0.0625 | +0.0571 | [+0.0379, +0.0763] |  |
| 7 | Mirko Gori | 28 | 914 | +0.0622 | +0.0549 | [+0.0326, +0.0773] |  |
| 8 | Romain Saïss | 35 | 1651 | +0.0592 | +0.0548 | [+0.0372, +0.0725] |  |
| 9 | Paolo Sammarco | 28 | 829 | +0.0551 | +0.0480 | [+0.0249, +0.0712] |  |
| 10 | Francesco Lodi | 24 | 1183 | +0.0527 | +0.0472 | [+0.0265, +0.0679] |  |
| 103 | Toni Kroos | 32 | 2339 | -0.0396 | -0.0384 | [-0.0543, -0.0225] | yes |
| 133 | Sergio Busquets i Burgos | 35 | 2299 | -0.0784 | -0.0753 | [-0.0911, -0.0595] | yes |
| 137 | Didier Ndong Ibrahim | 34 | 1705 | -0.0923 | -0.0877 | [-0.1052, -0.0702] |  |
| 138 | Roque Mesa Quevedo | 34 | 2016 | -0.1004 | -0.0958 | [-0.1124, -0.0793] |  |
| 139 | Gélson da Conceição Tavares Fernandes | 33 | 1539 | -0.1026 | -0.0970 | [-0.1152, -0.0788] |  |
| 140 | José Vicente Gómez Umpiérrez | 21 | 1013 | -0.1232 | -0.1129 | [-0.1351, -0.0908] |  |
| 141 | Nampalys Mendy | 38 | 2914 | -0.1232 | -0.1189 | [-0.1333, -0.1044] |  |

*M4_SLOW*: 141 DMs; group mean +0.0025; tau^2 0.00118; Q 1073.2 (140 df); clearly above 30, clearly below 37.

| rank | player | matches | units | raw mean | shrunk | 90% interval | praised |
|---|---|---|---|---|---|---|---|
| 1 | Seko Fofana | 31 | 1115 | +0.1179 | +0.1028 | [+0.0824, +0.1232] |  |
| 2 | Abdoulaye Doucouré | 30 | 1137 | +0.1038 | +0.0907 | [+0.0703, +0.1110] |  |
| 3 | Giuseppe Vives | 33 | 1370 | +0.0982 | +0.0875 | [+0.0686, +0.1064] |  |
| 4 | Gélson da Conceição Tavares Fernandes | 33 | 1539 | +0.0926 | +0.0833 | [+0.0651, +0.1014] |  |
| 5 | Didier Ndong Ibrahim | 34 | 1705 | +0.0791 | +0.0717 | [+0.0543, +0.0892] |  |
| 6 | Matías Vecino Falero | 30 | 1914 | +0.0716 | +0.0653 | [+0.0482, +0.0824] |  |
| 7 | Yacouba Sylla | 20 | 880 | +0.0659 | +0.0554 | [+0.0324, +0.0784] |  |
| 8 | Fabien Lemoine | 32 | 1561 | +0.0582 | +0.0525 | [+0.0343, +0.0706] |  |
| 9 | Benjamin Stambouli | 26 | 1303 | +0.0519 | +0.0459 | [+0.0262, +0.0656] |  |
| 10 | Roque Mesa Quevedo | 34 | 2016 | +0.0474 | +0.0436 | [+0.0271, +0.0601] |  |
| 47 | Sergio Busquets i Burgos | 35 | 2299 | +0.0162 | +0.0151 | [-0.0007, +0.0309] | yes |
| 106 | Toni Kroos | 32 | 2339 | -0.0210 | -0.0191 | [-0.0350, -0.0033] | yes |
| 137 | Lucas Deaux | 16 | 604 | -0.0613 | -0.0473 | [-0.0737, -0.0209] |  |
| 138 | Francesco Lodi | 24 | 1183 | -0.0551 | -0.0475 | [-0.0680, -0.0269] |  |
| 139 | Rio Antonio Zoba Mavuba | 35 | 1384 | -0.0543 | -0.0481 | [-0.0668, -0.0293] |  |
| 140 | Ignacio Camacho Barnola | 23 | 1142 | -0.0790 | -0.0679 | [-0.0887, -0.0471] |  |
| 141 | Étienne Didot | 23 | 1090 | -0.0872 | -0.0745 | [-0.0957, -0.0534] |  |

*M4_SWITCH*: 141 DMs; group mean +0.0057; tau^2 0.000208; Q 1092.9 (140 df); clearly above 28, clearly below 39.

| rank | player | matches | units | raw mean | shrunk | 90% interval | praised |
|---|---|---|---|---|---|---|---|
| 1 | Jessy Pi | 36 | 1601 | +0.0615 | +0.0560 | [+0.0486, +0.0634] |  |
| 2 | Carlos Henrique Casimiro | 23 | 1029 | +0.0588 | +0.0511 | [+0.0421, +0.0601] |  |
| 3 | Federico Viviani | 19 | 1016 | +0.0475 | +0.0413 | [+0.0321, +0.0504] |  |
| 4 | Yacouba Sylla | 20 | 880 | +0.0441 | +0.0378 | [+0.0282, +0.0474] |  |
| 5 | Claudio Marchisio | 23 | 1386 | +0.0385 | +0.0347 | [+0.0267, +0.0428] |  |
| 6 | Álvaro Medrán Just | 20 | 598 | +0.0395 | +0.0322 | [+0.0212, +0.0432] |  |
| 7 | Lucas Deaux | 16 | 604 | +0.0380 | +0.0309 | [+0.0198, +0.0420] |  |
| 8 | Roberto Trashorras Gayoso | 36 | 2338 | +0.0305 | +0.0287 | [+0.0223, +0.0351] |  |
| 9 | Toni Kroos | 32 | 2339 | +0.0300 | +0.0282 | [+0.0217, +0.0347] | yes |
| 10 | Daniel García Carrillo | 35 | 1702 | +0.0291 | +0.0269 | [+0.0196, +0.0341] |  |
| 44 | Sergio Busquets i Burgos | 35 | 2299 | +0.0090 | +0.0088 | [+0.0023, +0.0152] | yes |
| 137 | Yannick Cahuzac | 30 | 1120 | -0.0162 | -0.0134 | [-0.0220, -0.0048] |  |
| 138 | Rene Krhin | 23 | 523 | -0.0194 | -0.0135 | [-0.0250, -0.0020] |  |
| 139 | Gélson da Conceição Tavares Fernandes | 33 | 1539 | -0.0176 | -0.0152 | [-0.0228, -0.0077] |  |
| 140 | Jérémy Clément | 26 | 1288 | -0.0202 | -0.0171 | [-0.0253, -0.0089] |  |
| 141 | Jorge Luiz Frello Filho | 35 | 3470 | -0.0204 | -0.0189 | [-0.0245, -0.0134] |  |

*M3_speed*: 141 DMs; group mean +0.0679; tau^2 0.0225; Q 889.7 (140 df); clearly above 36, clearly below 32.

| rank | player | matches | units | raw mean | shrunk | 90% interval | praised |
|---|---|---|---|---|---|---|---|
| 1 | Víctor Sánchez Mata | 29 | 618 | +0.4719 | +0.4064 | [+0.3071, +0.5057] |  |
| 2 | Daniel García Carrillo | 35 | 905 | +0.4363 | +0.3897 | [+0.3021, +0.4774] |  |
| 3 | Pablo Fornals Malla | 27 | 497 | +0.4604 | +0.3880 | [+0.2821, +0.4939] |  |
| 4 | Tomás Pina Isla | 26 | 415 | +0.4526 | +0.3741 | [+0.2628, +0.4854] |  |
| 5 | Ignacio Camacho Barnola | 23 | 629 | +0.4382 | +0.3729 | [+0.2693, +0.4764] |  |
| 6 | Jorge Luiz Frello Filho | 35 | 2578 | +0.3724 | +0.3455 | [+0.2721, +0.4188] |  |
| 7 | Thomas Ayasse | 14 | 343 | +0.3823 | +0.2970 | [+0.1686, +0.4254] |  |
| 8 | Francisco Manuel Rico Castro | 28 | 500 | +0.3458 | +0.2953 | [+0.1902, +0.4004] |  |
| 9 | Omar Mascarell González | 26 | 430 | +0.3520 | +0.2951 | [+0.1847, +0.4055] |  |
| 10 | Romain Saïss | 35 | 934 | +0.3039 | +0.2745 | [+0.1874, +0.3616] |  |
| 56 | Sergio Busquets i Burgos | 35 | 1638 | +0.1273 | +0.1214 | [+0.0431, +0.1996] | yes |
| 99 | Toni Kroos | 32 | 1765 | -0.0159 | -0.0072 | [-0.0866, +0.0722] | yes |
| 137 | Álvaro Medrán Just | 20 | 408 | -0.2332 | -0.1659 | [-0.2824, -0.0493] |  |
| 138 | Roque Mesa Quevedo | 34 | 1481 | -0.2202 | -0.1897 | [-0.2699, -0.1095] |  |
| 139 | Leandro Greco | 26 | 687 | -0.2570 | -0.2045 | [-0.3036, -0.1054] |  |
| 140 | Blerim Džemaili | 27 | 546 | -0.3376 | -0.2661 | [-0.3696, -0.1625] |  |
| 141 | Tomás Eduardo Rincón Hernández | 33 | 1191 | -0.3200 | -0.2749 | [-0.3589, -0.1909] |  |

*M2*: 141 DMs; group mean +0.0774; tau^2 0.00366; Q 647.4 (140 df); clearly above 18, clearly below 23.

| rank | player | matches | units | raw mean | shrunk | 90% interval | praised |
|---|---|---|---|---|---|---|---|
| 1 | Jorge Luiz Frello Filho | 35 | 663 | +0.2946 | +0.2743 | [+0.2439, +0.3047] |  |
| 2 | Gélson da Conceição Tavares Fernandes | 33 | 272 | +0.2399 | +0.2090 | [+0.1657, +0.2524] |  |
| 3 | Nampalys Mendy | 38 | 502 | +0.1935 | +0.1800 | [+0.1461, +0.2139] |  |
| 4 | Thiago Motta | 31 | 572 | +0.1857 | +0.1741 | [+0.1417, +0.2066] |  |
| 5 | Claudio Marchisio | 23 | 253 | +0.1944 | +0.1705 | [+0.1256, +0.2155] |  |
| 6 | Danilo Cataldi | 18 | 130 | +0.2082 | +0.1653 | [+0.1084, +0.2223] |  |
| 7 | Gary Alexis Medel Soto | 29 | 206 | +0.1846 | +0.1594 | [+0.1111, +0.2076] |  |
| 8 | Mehdi Mostefa Sbaa | 24 | 175 | +0.1826 | +0.1546 | [+0.1033, +0.2059] |  |
| 9 | Sergio Busquets i Burgos | 35 | 429 | +0.1651 | +0.1535 | [+0.1173, +0.1897] | yes |
| 10 | Lucas Rodrigo Biglia | 27 | 361 | +0.1655 | +0.1519 | [+0.1128, +0.1910] |  |
| 23 | Toni Kroos | 32 | 354 | +0.1262 | +0.1186 | [+0.0795, +0.1578] | yes |
| 137 | Tiemoué Bakayoko | 18 | 158 | -0.0530 | -0.0154 | [-0.0688, +0.0380] |  |
| 138 | William Jean Rémy | 28 | 176 | -0.0501 | -0.0165 | [-0.0676, +0.0345] |  |
| 139 | Álvaro Medrán Just | 19 | 199 | -0.0723 | -0.0356 | [-0.0849, +0.0137] |  |
| 140 | Blerim Džemaili | 26 | 221 | -0.0687 | -0.0360 | [-0.0831, +0.0112] |  |
| 141 | Alfred John Momar N''Diaye | 34 | 308 | -0.0892 | -0.0605 | [-0.1018, -0.0192] |  |

**M2 sensitivity: drop spells excluded from T** (report only; not part of the family)

- S5-equivalent stability (DMs): n 141, median 0.646 [0.561, 0.695].
- R3_equiv: +0.0320 [-0.0058, +0.0698], p 0.0968, n 133,091 / 141; control +2.904 (p 1.5e-33).
- R7_equiv: +0.5805 [+0.3716, +0.7893], p 5.09e-08, n 577,215 / 1114; control +7.087 (p 0).

### Existing-table reads (Clarification B)

- `data/processed/engine_v2/task44_receptions.parquet`: filter match_id in 2015/16 REPLICATION (guard switched) ids (1137); rows kept 853,633
- `data/processed/engine_v2/task52_w_1516.parquet`: filter match_id in 2015/16 REPLICATION (guard switched) ids (1137); rows kept 853,633

Memory gate readings: [('replication tests', 49.0, 4.44)] (tests); 52.0 % / 4.23 GB (build).

## 4. Deviations from the brief
- **Holdout names not audited.** The brief asks for name matches "in ALL datasets used", including the holdout. The holdout has no player-level name table (only events, frames and match tables), and I did not open its event files to protect the holdout. Its three competition-seasons (53/106, 53/315, 72/107) are women's tournaments.
- **M2 sensitivity reading.** "Drop excluded spells" was run as: keep pressured receptions whose spell ends in his Pass or in a loss; drop those ending in a shot, a foul, a period end, another player's on-ball event, or no end found. Losses are kept because M2's definition counts them as FK = 0. The baseline was refit on these units.
- **R1 control.** The completion control was fitted on exactly the rows of the joint [M4_SWITCH, PR2_flag_keep] model, with S = other-match completion (>= 100 elsewhere).
- **DM tables on this page** show the top 10, the bottom 5 and every praised-list player present. Full tables are in `data/engine_v2_task53.json`. M3_speed's table uses per-unit values -r, so higher = faster, as the measure is defined.
- **K1 set.** K1 covers {PR2_flag_keep, W, M2, M3_speed, M4_ACCEL, M4_SLOW, M4_SWITCH}: Task 52's 2015/16 K1 set without M6 (dropped by the brief), plus M4_SWITCH (in the family). The disattenuation reliabilities are this task's D1 within DMs.
- **Guard message wording.** When a study or development id is refused, the inherited Task 52 message calls it "REPLICATION". The refusal is correct; only the word is inherited.

## 5. Problems and surprises
- **C2 and the PR2|M2 correlation include a component shared by construction.** M2 and PR2_flag_keep are both built on pressured receptions: 247,429 units, 141 DMs. FK = 1 requires his completed pass, and in the data every FK = 1 unit has keep_spell = 1 (60,359 of 60,359). What this would invalidate if taken at face value: reading C2's r = +0.686 (disattenuated 1.007, above 1, not clipped) as evidence that two separate traits co-occur. Part of the correlation comes from the definitions.
- **R7 (M2 → Y_F3, all players) and K2.** The retention control on R7's rows is also large (+7.078). K2 shows M2's Y_F3 coefficient within DMs falling from +0.190 (p 0.33) alone to +0.050 (p 0.84) with PR2_flag_keep. R7 itself was run as specified, without PR2_flag_keep.
- **Praised list by ID in the replication leagues** covers 4 present players (Verratti, Busquets, Modrić, Kroos) of 1,101-1,257 qualifying. Only Busquets and Kroos are DMs, so they are the only ones in the DM tables.
- **Task 52's page is affected by the audit.** Its 2015/16 D5 M4 rows (`docs/results/52-tempo-development.md`) included Siem Stefan de Jong (8061), not Frenkie de Jong. Tasks 44 and 45 dropped "de Jong" because it matched two players (Siem and Nigel), so Frenkie was absent there, not wrongly replaced. No other earlier test included a non-intended id.
- **T <= 0:** 92,816 pass-ending spells (12.5% of 745,071) have identical timestamps and are excluded by the 0 < T rule, as in Task 52.

## 6. Questions for the research lead
1. **C2:** given that FK = 1 implies keep = 1 on the same units, is C2 to be reported as specified, or should a version exist that separates the shared units? No such version was run.
2. **Holdout audit:** should the holdout's names be audited from its event files (which would touch holdout files), or is "women's tournaments only; not opened" sufficient?
3. **M2 sensitivity:** confirm the reading of "drop excluded spells" (losses kept).

## 7. Files produced
- **Scripts:**
  - `src/engine_v2/task53_praised_audit.py`: Step 1.
  - `src/engine_v2/task53_build.py`: Step 2.
  - `src/engine_v2/task53_tests.py`: Steps 3-4.
- `docs/splits/praised_ids.csv`: the ID list (13 rows).
- **Data, not committed:**
  - `data/engine_v2_task53_audit.json`
  - `data/processed/engine_v2/task53_1516rep_{receptions,passes}.parquet` (replication units)
  - `data/engine_v2_task53_build.json`, `data/engine_v2_task53.json`
- **Commits:**
  - cdb6b1e: Step 1.
  - The final commit hash is recorded below.
- **Side effects:** none beyond the files above.
- **Not mine and not committed:** pre-existing uncommitted changes to `docs/JOURNAL.md` and the untracked `AGENTS.md`.

## 8. Confidence
- **Strong:**
  - The family ran exactly as fixed, on the only use of the replication half.
  - The guard admitted only replication ids.
  - The dummy checks agree on every D3 cell.
- **Weakest links:**
  - C2's component shared by construction.
  - The praised-list tests with 4 players.
  - The operational readings carried over from Task 52: spell rules, M2 units, category thresholds.
