# Task 50: Freeze v8, the "fewer chances" puzzle, robustness of C4/C6, DM pooling
Date: 2026-09-29
Status: COMPLETE (every step run; deviations in Section 4, including study DM samples far below the 111-player group)

**Nothing on this page can be called confirmed.** Every dataset has been used before: 2015/16 is a further use after Tasks 44-47, the reserved data is a second use after Task 48, and the study sample is used as usual. The holdout was not touched. Task 49 (withdrawn) was not run.

## Checklist
| Section | Status |
|---|---|
| Step 0: brief committed alone | COMPLETE (ffafd1f, by the research lead) |
| Step 1: BENCHMARK-v8 + Task 49 withdrawal note | COMPLETE (9a05141, by the research lead) |
| Step 1: snapshot, manifest, tag, spot-check | COMPLETE (2540f07; tag `benchmark-v8` on 2540f07, not pushed). The manifest lists Task 46's W tables as never written (Section 4) |
| Memory gate (Task 25) | COMPLETE (checked before every heavy load: Step 2 six readings 43-46% / 3.2-3.8 GB; Step 3 eight readings 50-62% / 4.4-5.9 GB; Step 4 three readings 57-61% / 4.7-5.8 GB; all logged in each JSON's `memory_log`. The crashed first Step 2 run waited once at 38% / 3.1 GB, Section 5) |
| Step 2: puzzle, 2 datasets x {all, DM} x {PR2_flag_keep, A1} x 8 outcomes | COMPLETE |
| Step 3: C4/C6 on men / women / club / national team / excl. Barcelona / excl. Busquets and Walsh | COMPLETE (C4 not run on club-only and national-team-only, read as "C6 only"; Section 6 Q5) |
| Step 4: DM pooling (i) and (ii) | COMPLETE (study cells n = 31 and 88 players of the 111-player group; Section 4) |
| Step 2 interim page commit | COMPLETE (6f6cbf9) |

## 1. Headline
Step 4 (report only; the pre-registered Task 48 C1/C2 did not confirm, and this pooling was decided after seeing them). The study-sample cells rest on 31 players (PR2_flag_keep, 4,047 rows) and 88 players (W, 28,057 rows), not the 111-player DM group.
- (i) PR2_flag_keep -> Y_F3 pooled: +0.677 pp per 100 per SD [0.075, 1.278], p 0.027, I^2 = 0 (fixed = DL, tau^2 = 0).
- (ii) W -> Y_F3 pooled: fixed +0.162 [-0.102, 0.426], p 0.23; DL +0.043 [-0.427, 0.513], p 0.86; I^2 = 0.52.

Step 3 (reserved, second use): C6 is positive with a CI excluding 0 in all six subsets. Its smallest subset is national-team only: 220 matches, 179 players, +2.303 [0.922, 3.684], p 0.0011. C4's r_true CI excludes 0 in the four subsets where it ran; its smallest subset is men only (29 movers, +0.735 [0.436, 0.962]).

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
- Step 3: `.venv/bin/python -W ignore src/engine_v2/task50_robustness.py` writes `data/engine_v2_task50_step3.json`.
  - Task 48's C4 and C6 code (`task48_tests.c4_movers`, `ptest`, `summarise`; the C6 lines of `task48_tests.main` copied into `run_c4_c6`) runs on subsets of `task48_receptions.parquet`.
  - Built per-unit measures stay as saved. Every test-stage step is re-run inside each subset: g cross-fit, retention S, A1 demeaning, leave-match-out S, split-half reliabilities, 1,000-draw bootstrap.
  - Subsets:
    - Men / women come from `gender` in `engine_v2_task48_ingest.json`.
    - Club / national team come from `international` in the same file.
    - Barcelona: every match with a team named `Barcelona` or `Barcelona WFC` (488 matches).
    - Busquets / Walsh: player_ids 5203 (Sergio Busquets i Burgos) and 4658 (Keira Walsh), dropped as units.
  - The full-sample run reproduces Task 48 first.
- Step 4: `.venv/bin/python -W ignore src/engine_v2/task50_pooling.py` writes `data/engine_v2_task50_step4.json`.
  - Study (i): Task 44 Step 2's event-only measure as saved (`task46_study_pr_flag.parquet`, 59,911 pressured units) with the Task 44 P-test design.
    - Y_F3 from `task42_outcomes.match_outcomes`, set missing at x >= 80.
    - g from `task44_build.event_features` on the study events; cross-fit on Task 35's match folds.
    - Roles from `task32_step4.assign_roles` (as Task 42); DM group = `leaderboard_v5c.is_deep_midfield` (111).
    - Retention control S = other-match keep_spell over all completed study receptions (>= 100 elsewhere).
  - Study (ii): Task 46's study W, rebuilt with `task46_part_b.fit_w` exactly as Task 46 did (the table was never saved).
    - The rebuild reproduces Task 46's baseline exactly: n 271,830, AUC 0.6134970381.
    - Then the Task 46 B3 design runs within the 111 DMs: S_W >= 100 elsewhere; control S_keep >= 100.
  - 2015/16 and reserved estimates are read from the saved JSONs: Task 44 P2, Task 46 B3 `DM|y_f3` W_alone, Task 48 C1 and C2.
    - Task 48 saved no SE, so SE = (CI high - CI low) / 3.92.
    - Checking that method on Task 44 P2, which has a saved SE: 0.0040185 recovered vs 0.0040186 saved.
  - Pooling:
    - Inverse-variance fixed effect.
    - DerSimonian-Laird random effects, with tau^2 from `task29_step1_2.dersimonian_laird`, weights 1/(v + tau^2) and SE = 1/sqrt(sum of weights).
    - I^2 = max(0, (Q - df)/Q).
    - Normal 95% CIs.

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

### Step 3: C4 and C6 on subsets (dataset: reserved, second use after Task 48; no correction; no claim)
C6 is in pp of Y_F3 per 100 pressured receptions per SD of other-match A1. The control is the retention control on the same rows, in the same units. C4's bootstrap p = 2 x share of 1,000 draws with r_true <= 0; 0 of 1,000 gives p < 0.002.

| Subset | matches | C6 coef | C6 95% CI | C6 p | C6 n rows / players | control (p) | C4 movers | C4 r_true | C4 95% CI | C4 p | rel club / intl |
|---|---|---|---|---|---|---|---|---|---|---|---|
| full (reproduces Task 48) | 1,985 | +1.281 | [+0.988, +1.573] | 9.21e-18 | 246,255 / 1,817 | +8.586 (1.7e-167) | 127 | +0.650 | [0.500, 0.797] | < 0.002 | 0.857 / 0.762 |
| men only | 801 | +1.699 | [+1.044, +2.354] | 3.7e-07 | 77,800 / 572 | +7.976 (1.3e-25) | 29 | +0.735 | [0.436, 0.962] | < 0.002 | 0.893 / 0.880 |
| women only | 1,184 | +1.109 | [+0.799, +1.418] | 2.16e-12 | 168,455 / 1,245 | +8.579 (7.5e-196) | 98 | +0.593 | [0.417, 0.788] | < 0.002 | 0.850 / 0.715 |
| club only | 1,765 | +1.251 | [+0.953, +1.548] | 1.87e-16 | 232,615 / 1,634 | +8.735 (1.7e-162) | not run (C6 only) | | | | |
| national team only | 220 | +2.303 | [+0.922, +3.684] | 0.00108 | 7,118 / 179 | +7.519 (8.8e-18) | not run (C6 only) | | | | |
| excluding Barcelona matches (488 removed) | 1,497 | +1.130 | [+0.836, +1.424] | 5.17e-14 | 184,169 / 1,532 | +8.577 (3.6e-225) | 94 | +0.681 | [0.495, 0.844] | < 0.002 | 0.833 / 0.732 |
| excluding Busquets and Walsh | 1,985 | +1.285 | [+0.991, +1.579] | 1.06e-17 | 242,010 / 1,815 | +8.533 (4.2e-170) | 125 | +0.642 | [0.478, 0.789] | < 0.002 | 0.852 / 0.766 |

### Step 4: all the deep-midfield evidence together
**Caption: the pre-registered confirmation (Task 48 C1/C2) did not confirm, and this pooling was decided after seeing it.** Report only.
- Datasets:
  - The study sample is used as usual; these two study cells are computed for the first time here.
  - The 2015/16 rows are Task 44 P2 (first use) and Task 46 B3 (further use of 2015/16).
  - The reserved rows are Task 48 C1 / C2 (first use).
- Units: pp of Y_F3 per 100 receptions per SD of S.

**(i) PR2_flag_keep -> Y_F3 within DMs**

| Sample | estimate | SE | 95% CI | p | n rows / players | SE source |
|---|---|---|---|---|---|---|
| study | +0.443 | 0.953 | [-1.426, +2.312] | 0.642 | 4,047 / 31 | fit |
| 2015/16 (Task 44 P2) | +0.775 | 0.402 | [-0.013, +1.562] | 0.054 | 34,822 / 185 | saved |
| reserved (Task 48 C1) | +0.572 | 0.548 | [-0.502, +1.645] | 0.297 | 33,178 / 189 | (CI width)/3.92 |
| **pooled, fixed effect** | **+0.677** | 0.307 | [+0.075, +1.278] | 0.027 | 3 samples | |
| **pooled, DerSimonian-Laird** | **+0.677** | 0.307 | [+0.075, +1.278] | 0.027 | tau^2 = 0 | |

Q = 0.156 (df 2, p 0.925); I^2 = 0.00. Study retention control: +2.895 [1.692, 4.097], p 2.4e-6, n 4,047.

**(ii) W -> Y_F3 within DMs**

| Sample | estimate | SE | 95% CI | p | n rows / players | SE source |
|---|---|---|---|---|---|---|
| study | -0.132 | 0.516 | [-1.144, +0.879] | 0.798 | 28,057 / 88 | fit |
| 2015/16 (Task 46 B3) | +0.333 | 0.159 | [+0.020, +0.645] | 0.037 | 152,663 / 185 | saved |
| reserved (Task 48 C2) | -0.310 | 0.290 | [-0.878, +0.257] | 0.284 | 119,340 / 193 | (CI width)/3.92 |
| **pooled, fixed effect** | **+0.162** | 0.135 | [-0.102, +0.426] | 0.230 | 3 samples | |
| **pooled, DerSimonian-Laird** | **+0.043** | 0.240 | [-0.427, +0.513] | 0.858 | tau^2 = 8.87e-06 (per-SD units) | |

Q = 4.134 (df 2, p 0.127); I^2 = 0.52. Study retention control: +1.135 [0.747, 1.523], p 1.0e-8, n 27,964.

Dummy check (within vs full dummies, per SD): study (i) -0.0143001 / -0.0143001; study (ii) -0.0067928 / -0.0067928. The check uses the first 40 team-matches only, so it does not equal the full estimate.

## 4. Deviations from the brief
- **Step 1, Task 46's W tables are not in the snapshot.** `task46_part_b.py` held them in memory only and never wrote them to disk. The manifest records this on a "MISSING (never written)" line. For Step 4 the study W is rebuilt with Task 46's code (see Step 4 when complete).
- **Step 1, snapshot scope.** The brief lists "summary JSONs and per-unit tables behind results 44-48". I took every Task 44-48 JSON in `data/` and every per-unit parquet those tasks wrote, listed in `src/engine_v2/task50_snapshot.py`. I did not snapshot Task 43's `task43_spells.parquet` / `task43_pressured_spells.parquet` (read by Task 44's gate but written by Task 43), or the raw event folders.
- **Step 2, operational definitions of (d), (e), (f).** The brief gives these in words; the exact event rules I used are in Section 2 and in the module docstring. Every choice is a question in Section 6.
- **Step 4, study samples far smaller than the 111-player DM group.**
  - The brief names "study DM group of 111". The fits contain 31 players (i) and 88 players (ii).
  - The drop comes from the brief's own S floors: >= 50 other-match pressured receptions for (i), >= 100 other-match completed receptions for (ii). In 292 study matches, most DMs do not reach them.
  - I did not lower any floor. This is a sample smaller than the brief states, so I list it here.
- **Step 4, SEs for Task 48 C1 / C2 recovered from the saved CI**, because Task 48 did not save the SE. The method reproduces Task 44 P2's saved SE to 7e-8 (per-SD units).
- **Step 3, C4 not run on club-only or national-team-only.** I read "(C6 only)" as covering both. C4 compares a player's club and national-team contexts, so it cannot be formed within either subset alone.
- **Step 3, "Barcelona"** was taken as both `Barcelona` (men) and `Barcelona WFC` (women), 488 matches in total.
- **Step 3, subset recomputation.** Test-stage quantities (S, A1 team means, g, reliabilities) were recomputed within each subset. The built unit measures (pr2_flag_keep from Task 48's baseline fitted on all reserved data) were not refit.
- **Step 2 and Step 4, extra check.** I ran `dummy_check` on every cell (not in the brief). It is only a verification.

## 5. Problems and surprises
- **First Step 2 run crashed** (KeyError 'S_z') in the reserved DM cells, inside my extra `dummy_check`. On the first 40 team-matches of the DM subset, S has no within-team-match variation, so the check's model drops S. I wrapped the check to record "not computable" and reran all of Step 2. No estimate changed; the reserved DM cells show the check as not computable.
- **Memory gate:** in the first (crashed) run, the reserved half waited once at 38% / 3.1 GB and proceeded at 44% / 3.5 GB. All readings from the final run are in `memory_log` in the JSON.
- **The reading rule matches neither branch in 5 of 8 cells.** In every all-player cell, (a) is negative (p <= 6e-5) while (d) is positive (p 0.019 to 0.094). The brief's first branch needs (a) >= 0, the second needs (d) < 0, so neither applies. Taken at face value, the team's own shot xG in the next 10 events is lower as S rises, while own shot xG over the rest of the same possession is not lower. What this would invalidate: the reading rule's assumption that (a) and (d) move in the same direction, i.e. that the rule is exhaustive. I have not interpreted the pattern.
- **NET_XG_30 in 2015/16 DMs** is more negative (-0.138, p 0.0059) than NET_XG_10 (-0.027, p 0.19). In reserved DMs the order is reversed (-0.046 vs -0.083).
- **Negative g R^2** for XG_AGAINST_10 and NEXT_AGAINST (Section 3). g is a control in the P-test, so a g with no predictive value adds noise but should not bias the S coefficient. I am flagging it because it is not what Task 44 saw for net xG.

- **Step 4, study cells.**
  - The study PR2_flag_keep cell (31 players, SE 0.95) is weighted about 10% in the pooled fixed effect. The pooled (i) estimate therefore rests almost entirely on 2015/16 and reserved, the same two cells that did not confirm individually (p 0.054, 0.297).
  - Taken at face value, the pooled (i) CI excluding 0 would suggest the DM null in Task 48 C1 was a power problem. That reading would rely on a pooling decided after seeing C1, which the caption states.
- **Step 4, W heterogeneity.** The three W samples point in different directions (study -0.13, 2015/16 +0.33, reserved -0.31), with I^2 = 0.52. This is why fixed and DL differ.
- **Step 3.**
  - C6 in national-team-only (+2.30) and men-only (+1.70) is larger than full (+1.28), but those CIs are wide and overlap the full CI.
  - Excluding Barcelona matches lowers C6 to +1.13 [0.84, 1.42] and removes 25% of matches and 62,086 rows.
  - Taken at face value, no subset reverses the sign of C4 or C6.

## 6. Questions for the research lead
1. **Reading rule, unmatched pattern.** In all four all-player cells, (a) < 0 and (d) >= 0. Which branch, if any, applies? Should the rule use signs of point estimates (what I tabulated) or significance?
2. **POSS_XG (d):** I counted only shots by the unit's own team at a later index with the same StatsBomb `possession` number. Is that the intended "later in the SAME possession"?
3. **POSS_LEN (e):** I counted every later event whose `team` is the unit's team inside the same `possession`, including non-ball events such as Pressure or Duel attributed to that team. Should it be on-ball events only, or all events regardless of team?
4. **NEXT_AGAINST (f):** "the opponent's NEXT possession" is the first later possession whose `possession_team` is the opponent, even across half-time. If none exists (end of match), I scored 0. Should those units be excluded instead?

5. **Step 3, club-only / national-team-only for C4:** is my reading that "(C6 only)" applies to both correct? C4 cannot be formed within either subset alone.
6. **Step 3, Barcelona:** did "every match involving Barcelona" mean both clubs (what I ran, 488 matches) or the men's club only?
7. **Step 3, subsets:** should the built measure (pr2_flag_keep's baseline) also be refit within each subset? I kept Task 48's built measures and refit only the test stage.
8. **Step 4, study cells:** the study DM cells have 31 and 88 players, not 111, because of the S floors. Should they stay in the pooling as run, or be reported differently?

## 7. Files produced
- `src/engine_v2/task50_snapshot.py`: Step 1 snapshot + manifest.
- `src/engine_v2/task50_spotcheck.py`: Step 1 spot-check from the snapshot.
- `src/engine_v2/task50_puzzle.py`: Step 2.
- `src/engine_v2/task50_robustness.py`: Step 3; also holds `run_c4_c6` (Task 48's C4/C6 lines) and `mem_gate`.
- `src/engine_v2/task50_pooling.py`: Step 4.
- `docs/benchmark/manifest-v8.txt`: path, size, SHA-256 of the 26 snapshot files (committed).
- `data/benchmark_v8/`: 26 files, 387 MB (not committed).
- `data/engine_v2_task50_spotcheck.json`, `data/engine_v2_task50_step2.json`, `data/engine_v2_task50_step3.json`, `data/engine_v2_task50_step4.json` (not committed).
- Commits:
  - 2540f07: Step 1; tag `benchmark-v8`, not pushed.
  - 6f6cbf9: interim page after Step 2.
  - e6d0fe2: Steps 3-4 and the complete page.
- Side effects: none outside the brief's outputs. Pre-existing uncommitted changes to `docs/JOURNAL.md`, `docs/CHAT-HANDOFF.md` and `AGENTS.md` were not made by me and are not committed by me.

## 8. Confidence
- Step 3: the full-sample run reproduces Task 48 C4 and C6 exactly before any subset. The weakest links are the small subsets: 29 movers for men-only C4, 179 players for national-team C6.
- Step 4: the weakest link is the study (i) cell, 31 players.
- None of it is a confirmation: every dataset is on its second or later use.

Step 2 reproduces the saved 10-event net xG exactly, and both BENCHMARK-v8 reference cells to the printed digits. The weakest links:
- The operational definitions of (d), (e), (f) are mine (Section 6, questions 2-4).
- The DM cells rest on 185-189 players.
- The reserved DM cells could not be dummy-checked.
