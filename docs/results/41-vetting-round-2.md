# Task 41: Vetting round 2 (measurement only), CRITIQUE-v6 items 1a-1f, 2a, 2c, 2d, 3b
Date: 2026-09-28
Status: COMPLETE (every section run; interim page after Step 6 committed in 64e3b4e; deviations in Section 4)

## Checklist
| Section | Status |
|---|---|
| Step 0 — commit brief alone | COMPLETE (7c678c9) |
| Memory gate | COMPLETE (56% free / ~4.71 GB at 15:19 before Steps 1-6; 53% / ~4.48 GB at 15:22 before Steps 7-10) |
| Task 35 reproduction assert | COMPLETE (coef 0.0007469384836865591, SE 0.00024360166295770252, identical) |
| Step 1 (1a) — where he usually plays | COMPLETE |
| Step 2 (1b) — roles | COMPLETE |
| Step 3 (1c) — outcome definition | COMPLETE |
| Step 4 (1d) — inference | COMPLETE |
| Step 5 (1e) — size | COMPLETE |
| Step 6 (1f) — DM bounds | COMPLETE |
| Step 7 (2a) — praised-players list | COMPLETE |
| Step 8 (2c) — availability thresholds | COMPLETE (9 versions; the base version asserted to reproduce Task 38) |
| Step 9 (2d) — RQ and AV together | COMPLETE |
| Step 10 (3b) — one Holm family, within-DM tests | COMPLETE (12 p-values) |
| Commits after Step 6 and at the end | COMPLETE |

## 1. Headline
The base v5 Decision P-test coefficient (+0.0747 xG per 100 passes per SD, n = 168,855 / 440) stays positive with p < 0.01 under every variant tried:
- controls for location and ev_chosen;
- position-label fixed effects;
- three outcome definitions;
- two-way clustering;
- passer bootstrap.

By role, only forwards show it significantly (21 players, +0.612 per 100, p = 2.5e-12). The other five roles, including 88 deep midfielders, are each non-significant.

Across the 12 within-deep-midfielder results tests, none survives Holm (smallest adjusted p = 0.074).
The praised-players list is not distinguishable from random within-role draws on any of the four measures (permutation p 0.27-0.74).
Task 38's negative availability result holds at all nine thresholds (coefficients −0.050 to −0.072 per 100, p 0.002-0.037).

## 2. What I did
- Step 0: committed the brief alone (7c678c9).
- `.venv/bin/python src/engine_v2/task41_ptest_vetting.py`:
  - Regenerates Task 35's inputs with its own functions and asserts the (a) coefficient/SE reproduce.
  - `fit_multi()` is `task35_ptest.fe_fit`'s estimator generalised to several standardised covariates and any fixed-effect label. It is asserted equal to `fe_fit` on the base model.
  - S_x, S_y and S_ev are leave-one-match-out passer means (≥100 elsewhere, `task32_step5.leave_one_match_out`).
  - The Step 3 Y variants use one generalised net-xG function, asserted equal to Task 35's `net_xg_after` for the base window. g is refit for each variant with `task35_ptest.crossfit_g`.
  - Step 4 uses statsmodels two-way clustering (passer, match) and a 1,000-resample passer bootstrap (seed 20260928).
- `.venv/bin/python -W ignore src/engine_v2/task41_lists_availability.py`:
  - Step 7 matches plan v3's list in the 537 with `task27_step1_deep_midfield.name_matches` (all 13 matched uniquely) and uses Task 32 roles (PFF players mapped via the Task 36 player map plus the Bono override).
  - Step 8 recomputes AVAILABLE from the saved d_ball/space/lane and refits the baseline with `availability.fit_oof`. It reuses `availability_tests.r1`/`r2`, and asserts that the space 3 / lane 2 version reproduces Task 38's R1 and R2.
  - Step 9 uses `fit_multi` on Task 38's reception units.
  - Step 10 applies Holm across 12 p-values read from the summary JSONs of Tasks 35, 37, 38 and 39 and this task.
- Reproduce: the two commands above, in order.

## 3. Numbers

### Step 1 (1a) — Decision coefficient with location / EV controls (all models: 168,855 passes, 440 passers; per 100 passes per SD)

| Model | Decision coef | 95% CI | p | other covariates (coef per 100 per SD, p) |
|---|---|---|---|---|
| Base (Task 35) | +0.0747 | [0.0269, 0.1224] | 0.0022 | — |
| A: + S_x + S_y | +0.0795 | [0.0274, 0.1316] | 0.0028 | S_x −0.0266 (0.44); S_y −0.0242 (0.029) |
| B: + S_ev | +0.1119 | [0.0309, 0.1930] | 0.0068 | S_ev −0.0643 (0.21) |
| C: + S_x + S_y + S_ev | +0.1630 | [0.0678, 0.2582] | 0.0008 | S_x +0.0662 (0.17); S_y −0.0371 (0.0034); S_ev −0.1773 (0.027) |
| D: C, with position-label FE (23 labels) instead of role FE | +0.1527 | [0.0374, 0.2679] | 0.0094 | S_x +0.0517 (0.30); S_y −0.0317 (0.13); S_ev −0.1142 (0.21) |

### Step 2 (1b) — within each Task 32 role (S standardised within the role's rows)

| Role | n passes | n players | team-matches | coef per 100 per SD | 95% CI | p | Holm (info) | MDE per 100 |
|---|---|---|---|---|---|---|---|---|
| CB | 54,400 | 135 | 449 | +0.0220 | [−0.0029, 0.0470] | 0.083 | 0.42 | 0.0356 |
| FB | 29,075 | 81 | 412 | +0.0341 | [−0.0755, 0.1437] | 0.542 | 1.0 | 0.1566 |
| DM | 33,889 | 88 | 418 | +0.0087 | [−0.0297, 0.0471] | 0.657 | 1.0 | 0.0548 |
| CM | 11,691 | 26 | 204 | +0.0431 | [−0.1292, 0.2154] | 0.624 | 1.0 | 0.2461 |
| AM/W | 21,615 | 72 | 366 | +0.0111 | [−0.0722, 0.0943] | 0.795 | 1.0 | 0.1190 |
| FW | 10,682 | 21 | 281 | **+0.6122** | [0.4409, 0.7836] | 2.5e-12 | <1e-10 | 0.2448 |

### Step 3 (1c) — outcome definition (g refit each time)

| Y | coef per 100 per SD | 95% CI | p | MDE | Y mean | g OOF R^2 |
|---|---|---|---|---|---|---|
| Base: window 10 | +0.0747 | [0.0269, 0.1224] | 0.0022 | 0.0682 | 0.0056 | 0.045 |
| (a) window 10, excluding shots by the passer himself | +0.0783 | [0.0370, 0.1196] | 0.0002 | 0.0590 | 0.0052 | 0.039 |
| (b) window 5 | +0.0454 | [0.0127, 0.0782] | 0.0065 | 0.0468 | 0.0025 | 0.054 |
| (c) window 15 | +0.0945 | [0.0320, 0.1570] | 0.0030 | 0.0893 | 0.0086 | 0.028 |

### Step 4 (1d) — inference on the base model

| Method | SE (per pass) | 95% CI (per 100) | p |
|---|---|---|---|
| One-way cluster by passer (Task 35) | 0.000244 | [0.0269, 0.1224] | 0.0022 |
| Two-way cluster (passer, match) | 0.000285 | [0.0188, 0.1306] | 0.0088 |
| Passer cluster bootstrap (1,000, percentile) | — | [0.0241, 0.1274] | — (bootstrap mean +0.0744; share of draws ≤ 0: 0.004) |

### Step 5 (1e) — size in football terms
Assumptions (stated as the brief requires):
- The overall coefficient (+0.000747 xG per pass per SD) applies within each role.
- "One SD" is the SD of S in the base model (0.00165 Decision units, across all analysis passes), not a within-role SD.

| Role | median eligible passes per player-match (n player-matches) | xG per match | xG per 38 matches |
|---|---|---|---|
| DM | 42 (849) | 0.031 | 1.19 |
| CM | 33 (358) | 0.025 | 0.94 |
| AM/W | 23 (944) | 0.017 | 0.65 |
| FW | 20 (454) | 0.015 | 0.57 |

### Step 6 (1f) — what the deep-midfield tests rule out

| Sample | DM upper 95% bound (per pass per DM-SD) | all-player coefficient (per pass per SD) | fraction |
|---|---|---|---|
| Study (Task 35 Step 3 / Step 2) | 0.000471 | 0.000747 | 0.63 |
| Holdout (Task 37 Step 3 / Step 2, summary JSON) | 0.000699 | 0.000780 | 0.90 |

The DM coefficients are per SD of S within the DM rows, and the all-player coefficients are per SD across all rows. The fractions therefore compare different SD units.

### Step 7 (2a) — plan v3's praised list (L, 13 names) against four measures
Method:
- Within-role z-score of each qualifying player's measure (Task 32 roles, MIXED kept as its own group).
- T = mean z of the L-players present.
- 10,000 relabellings draw, within each role, as many players as L has in that role (seed 20260928).
- Two-sided p = (1 + #{|T*| ≥ |T|}) / 10,001.
- Pre-declared direction of interest: lower on AV, AV_vis and RQ_rel.

| Measure | qualifying players | L present | T (mean z) | p (two-sided) |
|---|---|---|---|---|
| AV (Task 38; ≥300 moments) | 273 | 9 | +0.293 | 0.365 |
| AV_vis (Task 38; ≥300 visible moments) | 254 | 9 | +0.108 | 0.738 |
| RQ_rel (Task 34; ≥100 receptions) | 495 | 13 | −0.267 | 0.325 |
| v5 Decision per pass (cross-fitted; the 537) | 537 | 13 | +0.290 | 0.274 |

L-players present, with z:
- **AV (9):** Rodri +1.66, Gündoğan +0.01, De Bruyne +1.75, Xhaka −0.26, Busquets −1.39, de Jong −0.36, Pedri +0.68, Modrić +0.06, Kimmich +0.48. Absent (not at WC2022 or <300 moments): Kroos, Verratti, Grillitsch, Shaparenko.
- **AV_vis (9):** Rodri +2.13, Gündoğan −0.28, De Bruyne +0.27, Xhaka −0.38, Busquets −1.52, de Jong −0.83, Pedri +1.23, Modrić +0.26, Kimmich +0.09.
- **RQ_rel (13):** De Bruyne +0.53, Verratti −0.69, Xhaka −0.10, Busquets −0.61, Modrić +0.93, Kroos +1.25, Kimmich −1.08, Rodri −3.17, de Jong +0.80, Gündoğan −0.38, Grillitsch +0.15, Shaparenko −0.33, Pedri −0.78.
- **v5 Decision (13):** De Bruyne +1.16, Verratti +0.44, Xhaka +0.27, Busquets +0.71, Modrić −0.72, Kroos +0.73, Kimmich +0.54, Rodri +0.15, de Jong −0.75, Gündoğan +0.57, Grillitsch +0.60, Shaparenko −0.66, Pedri +0.73.
- Roles of the 13: DM 6, CM 3, AM/W 1, FB 1, CB 1, MIXED 1. On PFF: DM 3, CM 2, CB 1, AM/W 1, MIXED 1, FB 1.

### Step 8 (2c) — availability thresholds (d_ball 5-40 m fixed; baseline refit each time)
R1 covers deep midfielders with ≥4 matches (28 in every version). R2 covers all outfield receivers (43,815 receptions, 381 players in every version).

| space ≥ | lane ≥ | base rate | baseline AUC | R1 DM median [p5, p95] | R2 coef per 100 per SD | 95% CI | p | MDE |
|---|---|---|---|---|---|---|---|---|
| 2 | 1 | 0.549 | 0.707 | 0.694 [0.571, 0.825] | −0.0505 | [−0.0979, −0.0031] | 0.037 | 0.0677 |
| 2 | 2 | 0.360 | 0.739 | 0.677 [0.556, 0.779] | −0.0701 | [−0.1154, −0.0249] | 0.0024 | 0.0647 |
| 2 | 3 | 0.213 | 0.794 | 0.743 [0.650, 0.821] | −0.0683 | [−0.1139, −0.0228] | 0.0033 | 0.0651 |
| 3 | 1 | 0.495 | 0.711 | 0.769 [0.689, 0.858] | −0.0574 | [−0.1062, −0.0087] | 0.021 | 0.0696 |
| **3** | **2** (Task 38) | 0.334 | 0.743 | 0.740 [0.647, 0.814] | −0.0692 | [−0.1146, −0.0238] | 0.0028 | 0.0648 |
| 3 | 3 | 0.213 | 0.794 | 0.743 [0.650, 0.821] | −0.0683 | [−0.1139, −0.0228] | 0.0033 | 0.0651 |
| 5 | 1 | 0.371 | 0.733 | 0.827 [0.754, 0.874] | −0.0668 | [−0.1125, −0.0212] | 0.0041 | 0.0652 |
| 5 | 2 | 0.262 | 0.762 | 0.808 [0.727, 0.862] | −0.0719 | [−0.1168, −0.0271] | 0.0017 | 0.0641 |
| 5 | 3 | 0.178 | 0.807 | 0.790 [0.692, 0.867] | −0.0643 | [−0.1096, −0.0189] | 0.0055 | 0.0648 |

### Step 9 (2d) — space at reception and availability together (Task 38 R2 receptions; SE clustered by receiver)
S_RQ = the receiver's other-match mean RQ_rel from Task 34 (all 292 StatsBomb matches except the reception's own WC2022 match, ≥100 receptions elsewhere). Rows need both S.

| Sample | n receptions | n players | team-matches | S_AV per 100 per SD [95% CI], p | S_RQ per 100 per SD [95% CI], p |
|---|---|---|---|---|---|
| All outfield | 30,505 | 214 | 111 | −0.0628 [−0.1255, −0.0001], 0.050 | −0.1275 [−0.2645, 0.0095], 0.068 |
| Deep midfielders | 5,778 | 37 | 91 | −0.2267 [−0.4881, 0.0348], 0.089 | +0.0119 [−0.1660, 0.1898], 0.896 |

### Step 10 (3b) — one Holm correction across every within-DM results test (12)

| Test | raw p | Holm p |
|---|---|---|
| Task 35 Step 3 (a) v5 Decision | 0.657 | 1.0 |
| Task 35 Step 3 (b) v6 Decision | 0.441 | 1.0 |
| Task 35 Step 3 (c) v5 ev_chosen | 0.958 | 1.0 |
| Task 35 Step 3 (d) reception RQ_rel | 0.0062 | 0.074 |
| Task 37 Step 3 holdout v5 Decision | 0.814 | 1.0 |
| Task 38 R2 DM AV | 0.052 | 0.464 |
| Task 38 R2 DM AV_vis | 0.045 | 0.446 |
| Task 39 Step 3 MOVE_ON_SPEED | 0.028 | 0.308 |
| Task 39 Step 3 HOLD_VARIATION | 0.116 | 0.814 |
| Task 41 Step 2 DM row (v5 Decision) | 0.657 | 1.0 |
| Task 41 Step 9 DM S_AV | 0.089 | 0.714 |
| Task 41 Step 9 DM S_RQ | 0.896 | 1.0 |

None is below 0.05 after Holm.

## 4. Deviations from the brief
- **"Normalised starting x and y"** = the value-model origin features `ball_x`/`ball_y` for each pass (team-relative, attacking toward x = 120).
- **Model D fixed effect:** each pass's StatsBomb `position` label from the event (23 labels in the rows).
- **Bootstrap:** S is standardised once on the full sample and held fixed across resamples. Duplicated passers count as distinct draws, and team-match fixed effects are re-absorbed in each resample.
- **Step 5:** the size uses the SD of S across all passes. A within-role SD would change the per-role numbers; see Q1.
- **Step 7 qualifying rule** (not given in the brief):
  - AV / AV_vis: ≥300 moments (Task 38's DM floor), mapped to a StatsBomb id with a Task 32 role.
  - RQ_rel: ≥100 receptions with a Task 32 role.
  - Decision: the 537 (each with a role).
  - Z-scores are taken within role, including the MIXED group.
  - The permutation p uses the (1 + count)/(1 + N) convention.
- **Step 8** uses the saved d_ball/space/lane from Task 38's moments; the d_ball window stays at 5-40 m.
- **Step 9:** S_RQ excludes the reception's own StatsBomb match, mapped through Task 36's crosswalk.
- **Step 10's family** takes both Step 9 DM coefficients (S_AV and S_RQ) as separate tests. It also contains the same test twice, because the brief lists both: Task 35 Step 3 (a) and this task's Step 2 DM row have identical rows, S and model (p = 0.657 both).

## 5. Problems and surprises
- **The role split has one driver.** Forwards (21 players) carry a coefficient eight times the overall one; the five other roles are each non-significant. Taken at face value, the overall P-test result is driven by forwards, and it does not show that Decision predicts results within any non-forward role at this sample size (MDEs 0.036-0.246).
- **The Decision coefficient rises when S_ev is added** (+0.075 → +0.112 → +0.163 with location), and S_ev's own coefficient is negative (−0.177 in C).
- Excluding the passer's own shots (Step 3a) leaves the coefficient at +0.078. The overall result is therefore not produced by passers' own shots, but this was not checked within forwards.

- **Step 8:** the space 2 / lane 3 and space 3 / lane 3 versions are identical, and space ≥ 2 is implied at lane ≥ 2. The lane distance can never exceed the space distance, because the teammate is the endpoint of the lane segment, so lane ≥ L already implies space ≥ L.
- **Step 8:** all nine R2 coefficients are negative, and eight of nine have p < 0.025. R1 among deep midfielders ranges 0.68-0.83.
- **Step 9, all outfield:** both coefficients are negative (S_AV p = 0.050, S_RQ p = 0.068).
- **Step 7:** RQ_rel's T is negative (−0.27), the pre-declared direction, but not significant (p = 0.33). On AV and AV_vis, T is positive, the opposite of the pre-declared direction.
- **Step 10:** the smallest Holm-adjusted p is 0.074 (Task 35 (d), reception RQ_rel). Taken at face value, no within-deep-midfielder results test in Tasks 35-41 survives a correction across the family.

## 6. Questions for the research lead
- Q1 (Step 5): should "one SD above his role's average" use a within-role SD of S?
- Q2 (Step 7): are the qualifying floors (≥300 moments, ≥100 receptions) the intended ones?

## 7. Files produced
- `src/engine_v2/task41_ptest_vetting.py`, `src/engine_v2/task41_lists_availability.py`.
- `data/engine_v2_task41_steps1_6.json`, `data/engine_v2_task41_steps7_10.json` (not committed).
- Side effects: none else. No memory writes. JOURNAL.md and AGENTS.md untouched. Holdout untouched (the Task 37 summary JSON was only read).
- Commits: brief 7c678c9; interim page after Step 6 64e3b4e; final aa1bb0b.

## 8. Confidence
Steps 1-6 reuse Task 35's estimator, and its reproduction is asserted exactly. The weakest links:
- The role split: there are only 21 forwards, and the whole-sample effect rests on them.
- The deep-midfielder tests: each has fewer than 90 players, and the Holm family has 12 members.
