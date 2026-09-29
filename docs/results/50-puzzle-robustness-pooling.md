# Task 50: Freeze v8, the "fewer chances" puzzle, robustness of C4/C6, DM pooling
Date: 2026-09-29
Status: PARTIAL (interim commit after Step 2, as the brief requires; Steps 3 and 4 still running)

**Nothing on this page can be called confirmed.** Every dataset has been used before: 2015/16 is a further use after Tasks 44-47, the reserved data is a second use after Task 48, and the study sample is used as usual. The holdout was not touched. Task 49 (withdrawn) was not run.

## Checklist
| Section | Status |
|---|---|
| Step 0: brief committed alone | COMPLETE (ffafd1f, by the research lead) |
| Step 1: BENCHMARK-v8 + Task 49 withdrawal note | COMPLETE (9a05141, by the research lead) |
| Step 1: snapshot, manifest, tag, spot-check | COMPLETE (2540f07; tag `benchmark-v8` on 2540f07, not pushed). The manifest lists Task 46's W tables as never written (Section 4) |
| Memory gate (Task 25) | COMPLETE for Step 2 (6 readings, all >= 40% and >= 3 GB at the time of proceeding; one earlier run waited at 38% / 3.1 GB, see Section 5) |
| Step 2: puzzle, 2 datasets x {all, DM} x {PR2_flag_keep, A1} x 8 outcomes | COMPLETE |
| Step 3: C4/C6 subsets | NOT RUN YET (running) |
| Step 4: DM pooling | NOT RUN YET (queued) |

## 1. Headline
Step 2 (report only; 2015/16 further use, reserved second use). XG_FOR_10 (a) has a negative point estimate in all 8 cells. POSS_XG (d) is positive in the 4 all-player cells (p 0.019 to 0.094) and negative in 3 of the 4 DM cells (p >= 0.53). The brief's reading rule therefore matches neither branch in 5 of 8 cells, and matches the "fewer chances" branch in 3 DM cells, where (d) has p >= 0.53 (DM samples: 185-189 players, 40,073-41,414 rows). POSS_LEN rises with S in every cell (p <= 0.005).

## 2. What I did
- Step 1:
  - `.venv/bin/python src/engine_v2/task50_snapshot.py` copies 26 files unmodified into `data/benchmark_v8/` (387 MB) and writes `docs/benchmark/manifest-v8.txt`.
  - `.venv/bin/python -W ignore src/engine_v2/task50_spotcheck.py` recomputes C6 and C4 from the snapshot copies only, using Task 48's code.
  - Commit 2540f07, then `git tag -a benchmark-v8 -m "Benchmark v8 — see docs/BENCHMARK-v8.md"`. Not pushed.
- Step 2: `.venv/bin/python -W ignore src/engine_v2/task50_puzzle.py` writes `data/engine_v2_task50_step2.json`.
  - Units: pressured receptions (`pr2_flag_keep` not null) from the saved receptions tables (`task44_receptions.parquet`, `task48_receptions.parquet`).
  - S: other-match mean with >= 50 elsewhere (`task42_step2.s_loo`) of PR2_flag_keep, and separately of A1.
    - 2015/16 A1 = unit minus team mean (Task 45).
    - Reserved A1 = unit minus team x competition-season mean (Task 48 C6).
  - g: event-only, cross-fitted, refit for every outcome (`task44_tests.crossfit_ev`, saved folds).
  - Model: role FE, team-match FE, SE clustered by player (`task35_ptest.fe_fit` via `task48_tests.ptest`).
  - Retention control: row keep_spell on S = other-match keep_spell over all completed receptions (>= 100 elsewhere), same rows.
  - DM groups: `is_dm` in each dataset's roles table (2015/16: 185; reserved: 193).
  - The new outcomes come from the raw events, one match at a time, in `index` order, from the reception's own team's view:
    - (a) own shot xG in events i+1..i+10.
    - (b) opponent shot xG in events i+1..i+10.
    - (c) own minus opponent shot xG in events i+1..i+20 and i+1..i+30.
    - (d) own shot xG in later events with the same StatsBomb `possession`.
    - (e) count of own-team events after i with the same `possession`.
    - (f) shot xG by the possession team in the first later possession whose `possession_team` is the opponent; 0 if no such possession exists.
  - Check: my recomputed 10-event net xG equals the saved `y_net_xg` exactly in both datasets (max abs difference 0.0).
  - Also run on every cell: `task35_ptest.dummy_check`, which compares the within-transform estimate with a full-dummy OLS on the first 40 team-matches.

## 3. Numbers

### Step 1: spot-check from the snapshot only
| Figure | Recomputed from `data/benchmark_v8/` | BENCHMARK-v8 | Match |
|---|---|---|---|
| Task 48 C6 coefficient (pp per 100 pressured receptions per SD) | +1.280694 | +1.281 | MATCH |
| Task 48 C4 r_true | +0.650115 | +0.650 | MATCH |

### Step 2: the puzzle
Units: coefficient per SD of S, x100, i.e. per 100 pressured receptions. For xG outcomes the units are xG; for POSS_LEN they are events. The outcome mean is in natural units over the fitted rows.

Reproduction of the reference cells before the new outcomes were used:
- 2015/16 all players, PR2_flag_keep, NET_XG_10: -0.0457, p 7.01e-05, n 300,404 / 1,498 (BENCHMARK-v8: -0.046, p 7e-5).
- Reserved DMs: -0.0825, p 0.0223, n 40,073 / 189 (BENCHMARK-v8: -0.0825, p 0.022).
- 2015/16 DMs: -0.0273, p 0.192 (Task 44 saved -0.0273, p 0.192).

**Dataset: 2015/16 (further use after Tasks 44-47). All players; S = other-match PR2_flag_keep.** Retention control on the same rows: +8.396 pp per SD [+7.956, +8.837], p = 2.9e-305, n = 299,973.

| Outcome | coef per SD, x100 | 95% CI (x100) | p | n rows / players | outcome mean (rows) | dummy check within / dummies (per SD) |
|---|---|---|---|---|---|---|
| NET_XG_10 (reference) | -0.0457 | [-0.0682, -0.0232] | 7.01e-05 | 300,404 / 1498 | 0.0045 | -0.003361 / -0.003361 |
| (a) XG_FOR_10 | -0.0448 | [-0.0667, -0.0230] | 5.8e-05 | 300,404 / 1498 | 0.0047 | -0.003064 / -0.003064 |
| (b) XG_AGAINST_10 | +0.0012 | [-0.0036, +0.0060] | 0.623 | 300,404 / 1498 | 0.0002 | +0.000354 / +0.000354 |
| (c) NET_XG_20 | -0.0559 | [-0.0900, -0.0218] | 0.0013 | 300,404 / 1498 | 0.0088 | -0.003360 / -0.003360 |
| (c) NET_XG_30 | -0.0369 | [-0.0794, +0.0057] | 0.0893 | 300,404 / 1498 | 0.0109 | -0.001406 / -0.001406 |
| (d) POSS_XG | +0.0258 | [-0.0028, +0.0545] | 0.0774 | 300,404 / 1498 | 0.0115 | +0.001904 / +0.001904 |
| (e) POSS_LEN | +74.6045 | [+67.5725, +81.6364] | 4.92e-96 | 300,404 / 1498 | 12.2215 | +1.259836 / +1.259836 |
| (f) NEXT_AGAINST | +0.0073 | [-0.0199, +0.0345] | 0.599 | 300,404 / 1498 | 0.0091 | -0.000632 / -0.000632 |

**Dataset: 2015/16 (further use after Tasks 44-47). All players; S = other-match A1.** Retention control on the same rows: +8.396 pp per SD [+7.956, +8.837], p = 2.9e-305, n = 299,973.

| Outcome | coef per SD, x100 | 95% CI (x100) | p | n rows / players | outcome mean (rows) | dummy check within / dummies (per SD) |
|---|---|---|---|---|---|---|
| NET_XG_10 (reference) | -0.0400 | [-0.0598, -0.0203] | 6.92e-05 | 300,404 / 1498 | 0.0045 | -0.002423 / -0.002423 |
| (a) XG_FOR_10 | -0.0393 | [-0.0584, -0.0202] | 5.68e-05 | 300,404 / 1498 | 0.0047 | -0.002320 / -0.002320 |
| (b) XG_AGAINST_10 | +0.0010 | [-0.0031, +0.0052] | 0.628 | 300,404 / 1498 | 0.0002 | +0.000152 / +0.000152 |
| (c) NET_XG_20 | -0.0507 | [-0.0806, -0.0209] | 0.000854 | 300,404 / 1498 | 0.0088 | -0.002317 / -0.002317 |
| (c) NET_XG_30 | -0.0353 | [-0.0726, +0.0019] | 0.0627 | 300,404 / 1498 | 0.0109 | -0.000761 / -0.000761 |
| (d) POSS_XG | +0.0215 | [-0.0036, +0.0466] | 0.0936 | 300,404 / 1498 | 0.0115 | +0.001491 / +0.001491 |
| (e) POSS_LEN | +65.2543 | [+59.1321, +71.3764] | 6.5e-97 | 300,404 / 1498 | 12.2215 | +0.960531 / +0.960531 |
| (f) NEXT_AGAINST | +0.0045 | [-0.0192, +0.0281] | 0.711 | 300,404 / 1498 | 0.0091 | -0.000639 / -0.000639 |

**Dataset: 2015/16 (further use after Tasks 44-47). Deep midfielders; S = other-match PR2_flag_keep.** Retention control on the same rows: +3.692 pp per SD [+2.959, +4.424], p = 5.1e-23, n = 41,414.

| Outcome | coef per SD, x100 | 95% CI (x100) | p | n rows / players | outcome mean (rows) | dummy check within / dummies (per SD) |
|---|---|---|---|---|---|---|
| NET_XG_10 (reference) | -0.0273 | [-0.0684, +0.0137] | 0.192 | 41,414 / 185 | 0.0022 | -0.001048 / -0.001048 |
| (a) XG_FOR_10 | -0.0231 | [-0.0633, +0.0171] | 0.26 | 41,414 / 185 | 0.0025 | -0.001298 / -0.001298 |
| (b) XG_AGAINST_10 | +0.0045 | [-0.0112, +0.0202] | 0.573 | 41,414 / 185 | 0.0003 | -0.000002 / -0.000002 |
| (c) NET_XG_20 | -0.0326 | [-0.1194, +0.0542] | 0.462 | 41,414 / 185 | 0.0054 | -0.005805 / -0.005805 |
| (c) NET_XG_30 | -0.1376 | [-0.2355, -0.0396] | 0.0059 | 41,414 / 185 | 0.0075 | -0.018637 / -0.018637 |
| (d) POSS_XG | +0.0078 | [-0.0780, +0.0935] | 0.859 | 41,414 / 185 | 0.0112 | -0.004758 / -0.004758 |
| (e) POSS_LEN | +34.5117 | [+10.6038, +58.4196] | 0.00467 | 41,414 / 185 | 14.3171 | -2.280084 / -2.280084 |
| (f) NEXT_AGAINST | -0.0498 | [-0.1360, +0.0364] | 0.257 | 41,414 / 185 | 0.0101 | +0.007549 / +0.007549 |

**Dataset: 2015/16 (further use after Tasks 44-47). Deep midfielders; S = other-match A1.** Retention control on the same rows: +3.692 pp per SD [+2.959, +4.424], p = 5.1e-23, n = 41,414.

| Outcome | coef per SD, x100 | 95% CI (x100) | p | n rows / players | outcome mean (rows) | dummy check within / dummies (per SD) |
|---|---|---|---|---|---|---|
| NET_XG_10 (reference) | -0.0213 | [-0.0536, +0.0111] | 0.198 | 41,414 / 185 | 0.0022 | -0.000533 / -0.000533 |
| (a) XG_FOR_10 | -0.0178 | [-0.0495, +0.0140] | 0.273 | 41,414 / 185 | 0.0025 | -0.000663 / -0.000663 |
| (b) XG_AGAINST_10 | +0.0035 | [-0.0087, +0.0158] | 0.572 | 41,414 / 185 | 0.0003 | -0.000001 / -0.000001 |
| (c) NET_XG_20 | -0.0264 | [-0.0951, +0.0423] | 0.451 | 41,414 / 185 | 0.0054 | -0.003110 / -0.003110 |
| (c) NET_XG_30 | -0.1129 | [-0.1882, -0.0377] | 0.00328 | 41,414 / 185 | 0.0075 | -0.009681 / -0.009681 |
| (d) POSS_XG | -0.0013 | [-0.0685, +0.0659] | 0.97 | 41,414 / 185 | 0.0112 | -0.002427 / -0.002427 |
| (e) POSS_LEN | +29.0020 | [+11.5754, +46.4287] | 0.00111 | 41,414 / 185 | 14.3171 | -1.126856 / -1.126856 |
| (f) NEXT_AGAINST | -0.0326 | [-0.1009, +0.0356] | 0.349 | 41,414 / 185 | 0.0101 | +0.003878 / +0.003878 |


**Dataset: reserved (second use after Task 48). All players; S = other-match PR2_flag_keep.** Retention control on the same rows: +8.670 pp per SD [+8.110, +9.230], p = 3.5e-202, n = 352,198.

| Outcome | coef per SD, x100 | 95% CI (x100) | p | n rows / players | outcome mean (rows) | dummy check within / dummies (per SD) |
|---|---|---|---|---|---|---|
| NET_XG_10 (reference) | -0.0404 | [-0.0613, -0.0195] | 0.000148 | 353,437 / 1823 | 0.0047 | -0.000585 / -0.000585 |
| (a) XG_FOR_10 | -0.0417 | [-0.0616, -0.0218] | 4.11e-05 | 353,437 / 1823 | 0.0051 | -0.000518 / -0.000518 |
| (b) XG_AGAINST_10 | +0.0021 | [-0.0045, +0.0087] | 0.538 | 353,437 / 1823 | 0.0004 | +0.000083 / +0.000083 |
| (c) NET_XG_20 | -0.0328 | [-0.0671, +0.0014] | 0.0605 | 353,437 / 1823 | 0.0095 | -0.001862 / -0.001862 |
| (c) NET_XG_30 | -0.0234 | [-0.0663, +0.0194] | 0.284 | 353,437 / 1823 | 0.0121 | -0.001670 / -0.001670 |
| (d) POSS_XG | +0.0386 | [+0.0064, +0.0709] | 0.0189 | 353,437 / 1823 | 0.0139 | -0.001271 / -0.001271 |
| (e) POSS_LEN | +87.0863 | [+76.0884, +98.0843] | 2.55e-54 | 353,437 / 1823 | 13.3334 | +0.881532 / +0.881532 |
| (f) NEXT_AGAINST | +0.0108 | [-0.0172, +0.0387] | 0.451 | 353,437 / 1823 | 0.0094 | +0.000081 / +0.000081 |

**Dataset: reserved (second use after Task 48). All players; S = other-match A1.** Retention control on the same rows: +8.670 pp per SD [+8.110, +9.230], p = 3.5e-202, n = 352,198.

| Outcome | coef per SD, x100 | 95% CI (x100) | p | n rows / players | outcome mean (rows) | dummy check within / dummies (per SD) |
|---|---|---|---|---|---|---|
| NET_XG_10 (reference) | -0.0381 | [-0.0553, -0.0210] | 1.3e-05 | 353,437 / 1823 | 0.0047 | -0.000853 / -0.000853 |
| (a) XG_FOR_10 | -0.0396 | [-0.0560, -0.0233] | 2.05e-06 | 353,437 / 1823 | 0.0051 | -0.000830 / -0.000830 |
| (b) XG_AGAINST_10 | +0.0013 | [-0.0041, +0.0066] | 0.642 | 353,437 / 1823 | 0.0004 | +0.000002 / +0.000002 |
| (c) NET_XG_20 | -0.0347 | [-0.0626, -0.0069] | 0.0146 | 353,437 / 1823 | 0.0095 | -0.001556 / -0.001556 |
| (c) NET_XG_30 | -0.0242 | [-0.0587, +0.0103] | 0.169 | 353,437 / 1823 | 0.0121 | -0.001574 / -0.001574 |
| (d) POSS_XG | +0.0239 | [-0.0021, +0.0499] | 0.0713 | 353,437 / 1823 | 0.0139 | -0.000746 / -0.000746 |
| (e) POSS_LEN | +71.4180 | [+62.2336, +80.6023] | 1.9e-52 | 353,437 / 1823 | 13.3334 | +0.691157 / +0.691157 |
| (f) NEXT_AGAINST | +0.0073 | [-0.0154, +0.0301] | 0.527 | 353,437 / 1823 | 0.0094 | -0.000567 / -0.000567 |

**Dataset: reserved (second use after Task 48). Deep midfielders; S = other-match PR2_flag_keep.** Retention control on the same rows: +5.214 pp per SD [+4.138, +6.289], p = 2.1e-21, n = 40,073.

| Outcome | coef per SD, x100 | 95% CI (x100) | p | n rows / players | outcome mean (rows) | dummy check within / dummies (per SD) |
|---|---|---|---|---|---|---|
| NET_XG_10 (reference) | -0.0825 | [-0.1532, -0.0117] | 0.0223 | 40,073 / 189 | 0.0023 | not computable (S_z has no within variation in the first 40 team-matches) |
| (a) XG_FOR_10 | -0.0718 | [-0.1400, -0.0035] | 0.0393 | 40,073 / 189 | 0.0028 | not computable (S_z has no within variation in the first 40 team-matches) |
| (b) XG_AGAINST_10 | +0.0125 | [-0.0153, +0.0403] | 0.376 | 40,073 / 189 | 0.0005 | not computable (S_z has no within variation in the first 40 team-matches) |
| (c) NET_XG_20 | -0.0567 | [-0.1600, +0.0465] | 0.282 | 40,073 / 189 | 0.0064 | not computable (S_z has no within variation in the first 40 team-matches) |
| (c) NET_XG_30 | -0.0462 | [-0.1883, +0.0959] | 0.524 | 40,073 / 189 | 0.0095 | not computable (S_z has no within variation in the first 40 team-matches) |
| (d) POSS_XG | -0.0333 | [-0.1379, +0.0712] | 0.532 | 40,073 / 189 | 0.0135 | not computable (S_z has no within variation in the first 40 team-matches) |
| (e) POSS_LEN | +72.7381 | [+46.0867, +99.3895] | 8.83e-08 | 40,073 / 189 | 15.1388 | not computable (S_z has no within variation in the first 40 team-matches) |
| (f) NEXT_AGAINST | -0.0361 | [-0.1293, +0.0571] | 0.448 | 40,073 / 189 | 0.0095 | not computable (S_z has no within variation in the first 40 team-matches) |

**Dataset: reserved (second use after Task 48). Deep midfielders; S = other-match A1.** Retention control on the same rows: +5.214 pp per SD [+4.138, +6.289], p = 2.1e-21, n = 40,073.

| Outcome | coef per SD, x100 | 95% CI (x100) | p | n rows / players | outcome mean (rows) | dummy check within / dummies (per SD) |
|---|---|---|---|---|---|---|
| NET_XG_10 (reference) | -0.0651 | [-0.1186, -0.0115] | 0.0172 | 40,073 / 189 | 0.0023 | not computable (S_z has no within variation in the first 40 team-matches) |
| (a) XG_FOR_10 | -0.0565 | [-0.1077, -0.0053] | 0.0307 | 40,073 / 189 | 0.0028 | not computable (S_z has no within variation in the first 40 team-matches) |
| (b) XG_AGAINST_10 | +0.0107 | [-0.0102, +0.0316] | 0.314 | 40,073 / 189 | 0.0005 | not computable (S_z has no within variation in the first 40 team-matches) |
| (c) NET_XG_20 | -0.0471 | [-0.1231, +0.0288] | 0.224 | 40,073 / 189 | 0.0064 | not computable (S_z has no within variation in the first 40 team-matches) |
| (c) NET_XG_30 | -0.0419 | [-0.1456, +0.0619] | 0.429 | 40,073 / 189 | 0.0095 | not computable (S_z has no within variation in the first 40 team-matches) |
| (d) POSS_XG | -0.0165 | [-0.0883, +0.0552] | 0.652 | 40,073 / 189 | 0.0135 | not computable (S_z has no within variation in the first 40 team-matches) |
| (e) POSS_LEN | +62.0001 | [+44.2826, +79.7176] | 6.95e-12 | 40,073 / 189 | 15.1388 | not computable (S_z has no within variation in the first 40 team-matches) |
| (f) NEXT_AGAINST | -0.0292 | [-0.0917, +0.0333] | 0.36 | 40,073 / 189 | 0.0095 | not computable (S_z has no within variation in the first 40 team-matches) |


**Reading rule applied literally (signs of point estimates; the brief does not say whether significance is required).**

| Dataset | Group | S | (a) XG_FOR_10 | (d) POSS_XG | NET_XG_10 | (a) >= 0 and (d) >= 0 with NET_XG_10 < 0 | (a) < 0 and (d) < 0 |
|---|---|---|---|---|---|---|---|
| 2015/16 | all | PR2_flag_keep | -0.0448 (p 5.8e-05) | +0.0258 (p 0.077) | -0.0457 (p 7e-05) | no | no |
| 2015/16 | all | A1 | -0.0393 (p 5.7e-05) | +0.0215 (p 0.094) | -0.0400 (p 6.9e-05) | no | no |
| 2015/16 | DM | PR2_flag_keep | -0.0231 (p 0.26) | +0.0078 (p 0.86) | -0.0273 (p 0.19) | no | no |
| 2015/16 | DM | A1 | -0.0178 (p 0.27) | -0.0013 (p 0.97) | -0.0213 (p 0.2) | no | yes |
| reserved | all | PR2_flag_keep | -0.0417 (p 4.1e-05) | +0.0386 (p 0.019) | -0.0404 (p 0.00015) | no | no |
| reserved | all | A1 | -0.0396 (p 2.1e-06) | +0.0239 (p 0.071) | -0.0381 (p 1.3e-05) | no | no |
| reserved | DM | PR2_flag_keep | -0.0718 (p 0.039) | -0.0333 (p 0.53) | -0.0825 (p 0.022) | no | yes |
| reserved | DM | A1 | -0.0565 (p 0.031) | -0.0165 (p 0.65) | -0.0651 (p 0.017) | no | yes |

Other Step 2 figures:
- Pressured receptions (all units before the S filter):
  - 2015/16: 320,802 in 1,551 matches.
  - Reserved: 430,573 in 1,985 matches.
- Units where NEXT_AGAINST = 0: 292,929 (2015/16) and 393,495 (reserved). Mostly the opponent's next possession had no shot; the code does not separately count "no later opponent possession".
- g out-of-fold R^2 is negative for XG_AGAINST_10 (-0.057 / -0.030) and NEXT_AGAINST (-0.007 / -0.003) in both datasets. The event-only g predicts these outcomes worse than a constant; see Section 5.
- The retention control is identical for S = PR2_flag_keep and S = A1 within a dataset and group. Its S is other-match keep_spell in both cases, and the rows are the same.

## 4. Deviations from the brief
- **Step 1, Task 46's W tables are not in the snapshot.** `task46_part_b.py` held them in memory only and never wrote them to disk. The manifest records this on a "MISSING (never written)" line. For Step 4 the study W is rebuilt with Task 46's code (see Step 4 when complete).
- **Step 1, snapshot scope.** The brief lists "summary JSONs and per-unit tables behind results 44-48". I took every Task 44-48 JSON in `data/` and every per-unit parquet those tasks wrote, listed in `src/engine_v2/task50_snapshot.py`. I did not snapshot Task 43's `task43_spells.parquet` / `task43_pressured_spells.parquet` (read by Task 44's gate but written by Task 43), or the raw event folders.
- **Step 2, operational definitions of (d), (e), (f).** The brief gives these in words; the exact event rules I used are in Section 2 and in the module docstring. Every choice is a question in Section 6.
- **Step 2, extra check.** I ran `dummy_check` on every cell (not in the brief). It is only a verification.

## 5. Problems and surprises
- **First Step 2 run crashed** (KeyError 'S_z') in the reserved DM cells, inside my extra `dummy_check`. On the first 40 team-matches of the DM subset, S has no within-team-match variation, so the check's model drops S. I wrapped the check to record "not computable" and reran all of Step 2. No estimate changed; the reserved DM cells show the check as not computable.
- **Memory gate:** in the first (crashed) run, the reserved half waited once at 38% / 3.1 GB and proceeded at 44% / 3.5 GB. All readings from the final run are in `memory_log` in the JSON.
- **The reading rule matches neither branch in 5 of 8 cells.** In every all-player cell, (a) is negative (p <= 6e-5) while (d) is positive (p 0.019 to 0.094). The brief's first branch needs (a) >= 0, the second needs (d) < 0, so neither applies. Taken at face value, the team's own shot xG in the next 10 events is lower as S rises, while own shot xG over the rest of the same possession is not lower. What this would invalidate: the reading rule's assumption that (a) and (d) move in the same direction, i.e. that the rule is exhaustive. I have not interpreted the pattern.
- **NET_XG_30 in 2015/16 DMs** is more negative (-0.138, p 0.0059) than NET_XG_10 (-0.027, p 0.19). In reserved DMs the order is reversed (-0.046 vs -0.083).
- **Negative g R^2** for XG_AGAINST_10 and NEXT_AGAINST (Section 3). g is a control in the P-test, so a g with no predictive value adds noise but should not bias the S coefficient. I am flagging it because it is not what Task 44 saw for net xG.

## 6. Questions for the research lead
1. **Reading rule, unmatched pattern.** In all four all-player cells, (a) < 0 and (d) >= 0. Which branch, if any, applies? Should the rule use signs of point estimates (what I tabulated) or significance?
2. **POSS_XG (d):** I counted only shots by the unit's own team at a later index with the same StatsBomb `possession` number. Is that the intended "later in the SAME possession"?
3. **POSS_LEN (e):** I counted every later event whose `team` is the unit's team inside the same `possession`, including non-ball events such as Pressure or Duel attributed to that team. Should it be on-ball events only, or all events regardless of team?
4. **NEXT_AGAINST (f):** "the opponent's NEXT possession" is the first later possession whose `possession_team` is the opponent, even across half-time. If none exists (end of match), I scored 0. Should those units be excluded instead?

## 7. Files produced
- `src/engine_v2/task50_snapshot.py`: Step 1 snapshot + manifest.
- `src/engine_v2/task50_spotcheck.py`: Step 1 spot-check from the snapshot.
- `src/engine_v2/task50_puzzle.py`: Step 2.
- `src/engine_v2/task50_robustness.py`: Step 3; also holds `run_c4_c6` (Task 48's C4/C6 lines) and `mem_gate`.
- `src/engine_v2/task50_pooling.py`: Step 4.
- `docs/benchmark/manifest-v8.txt`: path, size, SHA-256 of the 26 snapshot files (committed).
- `data/benchmark_v8/`: 26 files, 387 MB (not committed).
- `data/engine_v2_task50_spotcheck.json`, `data/engine_v2_task50_step2.json` (not committed).
- Commits: 2540f07 (Step 1; tag `benchmark-v8`); this page's Step 2 commit (hash recorded in the final version).
- Side effects: none outside the brief's outputs. Pre-existing uncommitted changes to `docs/JOURNAL.md`, `docs/CHAT-HANDOFF.md` and `AGENTS.md` were not made by me and are not committed by me.

## 8. Confidence
Step 2 reproduces the saved 10-event net xG exactly, and both BENCHMARK-v8 reference cells to the printed digits. The weakest links:
- The operational definitions of (d), (e), (f) are mine (Section 6, questions 2-4).
- The DM cells rest on 185-189 players.
- The reserved DM cells could not be dummy-checked.
