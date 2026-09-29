# Task 46: Player or team? And spatial vs physical press resistance
Date: 2026-09-28
Status: COMPLETE (every section run; interim page after Part A committed in 8648d7f; deviations in Section 4)

**Development task (exploratory)**: study sample, PFF WC2022 and 2015/16 (third use of 2015/16). Holdout spent and untouched. The reserved data was not opened.

## Checklist
| Section | Status |
|---|---|
| Step 0 — brief | COMPLETE, with a deviation: committed by the research lead in 105e500 **together with the Task 47 brief**, not alone |
| RESERVED data listed by id, not opened | COMPLETE |
| Memory gate | COMPLETE (54% / 4.59 GB at 19:57 before Part A; 52% / 4.53 GB at 19:59 before Part B) |
| Part A-i — movers (PH-B2) and variance split | COMPLETE |
| Part A-ii — 2015/16 club vs study national team | COMPLETE |
| Part B — W measure (2015/16 and study), B1, B2, B3 | COMPLETE |
| Commits after Part A and at the end | COMPLETE |

## 1. Headline
**Part A claim allowed:** "press resistance travels with the player across teams".
- A-i (study sample, club vs country movers): r_true = **0.924**, 95% CI **[0.735, 1.000]**, on only **24 movers**.
- The deep-midfield version is unmeasurable: 4 movers, and the international split-half reliability is negative. It is not claimed.
- Part B (exploratory; to be confirmed only on the reserved data):
  - Physical willingness W is highly stable (2015/16 deep midfielders 0.802, all players 0.924).
  - Among all study players, W is strongly negatively correlated with spatial RQ_rel (r = −0.754; 1 player in the top quartile of both, 33.4 expected, p = 1e-18).
  - Among deep midfielders the correlation is also negative (RQ_rel vs W −0.473, n = 98; PFF AV_out vs W −0.336, n = 35).
- A-ii (2015/16 club vs national team 5-8 years later, 91 players): r_true = 0.740, 95% CI [0.579, 0.888].

## 2. What I did
- Step 0: the brief was committed by the research lead in 105e500 (with Task 47's brief).
- **RESERVED competition-seasons**, found by listing the directory names under `data/raw_1516/open-data-master/data/matches/` and removing every competition-season already used (study, holdout, 2015/16). No reserved file was opened. The 64 reserved (competition_id, season_id) pairs are:
  (2,44), (11,1), (11,2), (11,21), (11,22), (11,23), (11,24), (11,25), (11,26), (11,278), (11,37), (11,38), (11,39), (11,4), (11,40), (11,41), (11,42), (12,86), (16,1), (16,2), (16,21), (16,22), (16,23), (16,24), (16,25), (16,26), (16,27), (16,276), (16,277), (16,37), (16,39), (16,4), (16,41), (16,44), (16,71), (16,76), (35,75), (37,281), (37,4), (37,42), (37,90), (43,269), (43,270), (43,272), (43,3), (43,51), (43,54), (43,55), (49,107), (49,3), (72,30), (81,275), (81,48), (87,268), (87,279), (87,84), (116,68), (131,281), (135,281), (182,281), (223,282), (1238,108), (1267,107), (1470,274).
- `.venv/bin/python -W ignore src/engine_v2/task46_part_a.py`:
  - **Study PR2_flag_keep** was regenerated with Task 44 Step 2's own functions (`task44_gate.receipt_flags`, `fit_baseline`, Task 35 folds). Its gate correlation with Task 43 reproduced (r = 0.8395, asserted against 0.8395).
  - **A-i units:** player × team context (team × competition × season), with ≥30 pressured receptions.
  - **A-i movers:** Study B's definition (a club context and an international context), used in `task26_step6_study_b.ph_b2`, which is unchanged.
  - **Variance split:** `reml_crossed.fit_reml` with Study B's parametric-bootstrap interval (`method_ii`, 200 draws). Covariates are Study B's zone shares; the pressure share is dropped because it is constant.
  - **A-ii:** the same split-half, disattenuation and 1,000-player bootstrap recipe, applied to 2015/16 club values (≥50 pressured receptions) against study-sample international values (≥30).

## 3. Numbers

### A-i — movers (study sample; PH-B2)
- Units ≥30 pressured receptions: 477 (349 players; 90 players with ≥2 contexts).

| Population | movers | rel (club) | rel (international) | r_obs | r_true | 95% CI |
|---|---|---|---|---|---|---|
| All players | 24 | 0.845 | 0.691 | 0.706 | **0.924** | **[0.735, 1.000]** |
| Deep midfielders | 4 | 0.840 | -2.539 | -0.206 | unmeasurable (a reliability < 0.10) | — |

### A-i — variance split (player vs team context; crossed random effects)

| Population | units | players | var(player) | var(team context) | S = player share | 95% CI (parametric bootstrap) |
|---|---|---|---|---|---|---|
| All players | 477 | 349 | 0.00636 | 0.00224 | **0.740** | [0.635, 0.867] |
| Deep midfielders | 72 | 53 | 0.00131 | 0.00193 | 0.405 | [0.000, 1.000] |

### A-ii — 2015/16 club vs study-sample national team
Time gap: the 2015/16 club season against national-team tournaments at Euro 2020 (played 2021), WC 2022 and Euro 2024, i.e. 5-8 years later.

| Population | players | rel (2015/16) | rel (national) | r_obs | r_true | 95% CI |
|---|---|---|---|---|---|---|
| All players | 91 | 0.856 | 0.722 | 0.582 | 0.740 | [0.579, 0.888] |
| Deep midfielders | 12 | 0.849 | 0.447 | 0.720 | 1.000 (capped) | [0.786, 1.000] |

### Part B — measures
- W, 2015/16: 1,158,231 completed receptions; PRESSURED base rate 0.288; baseline OOF AUC 0.629.
- W, study sample: 271,830 receptions; base rate 0.228; AUC 0.613.
- AV_out (PFF moments with the passer under pressure): 274,945 moments; AVAILABLE base rate 0.245; refit baseline AUC 0.693.

### B1 — W stability, 2015/16 (Task 38's method, ≥10 matches)

| Group | n | median | p5 | p95 | bar 0.60 |
|---|---|---|---|---|---|
| Deep midfielders | 185 | 0.802 | 0.766 | 0.833 | PASS |
| All players | 1636 | 0.924 | 0.917 | 0.929 | PASS |

### B2 — spatial vs physical (Pearson r, 95% CI; top-quartile-of-both overlap against independence, hypergeometric one-sided p in each direction)
Floors:
- S1 (study): RQ_rel ≥100 receptions; W ≥100 receptions; PR ≥50 pressured receptions. Deep midfielders = the study's 111.
- S2 (WC2022): AV_out ≥100 moments; W ≥100 and PR ≥30 on WC2022 StatsBomb matches. Deep midfielders = Task 38's PFF group.

| Pair | n | r | 95% CI | both in top quartile | expected | p (fewer) | p (more) |
|---|---|---|---|---|---|---|---|
| S1 study (360), DM: RQ rel vs W | 98 | -0.473 | [-0.614, -0.303] | 3 | 6.38 | 0.0583 | 0.985 |
| S1 study (360), DM: RQ rel vs PR | 37 | +0.290 | [-0.038, +0.561] | 5 | 2.70 | 0.988 | 0.07 |
| S1 study (360), all: RQ rel vs W | 530 | -0.754 | [-0.788, -0.714] | 1 | 33.38 | 1.34e-18 | 1 |
| S1 study (360), all: RQ rel vs PR | 241 | +0.507 | [+0.407, +0.595] | 31 | 15.44 | 1 | 3.92e-07 |
| S2 PFF WC2022, DM: AV out vs W | 35 | -0.336 | [-0.602, -0.003] | 0 | 2.31 | 0.0443 | 1 |
| S2 PFF WC2022, DM: AV out vs PR | 20 | -0.499 | [-0.771, -0.073] | 0 | 1.25 | 0.194 | 1 |
| S2 PFF WC2022, all: AV out vs W | 194 | -0.134 | [-0.270, +0.007] | 8 | 12.38 | 0.0672 | 0.972 |
| S2 PFF WC2022, all: AV out vs PR | 116 | +0.210 | [+0.029, +0.378] | 9 | 7.25 | 0.867 | 0.264 |

### B3 — results, 2015/16 (Task 44's P-test; unit = completed reception; S = other-match W, ≥100 elsewhere; retention control on the same rows; joint model adds S_PR, ≥50 pressured elsewhere)

| Group | Y | n / players | S_W alone (per 100 per SD) | control | joint: S_W | joint: S_PR |
|---|---|---|---|---|---|---|
| all | Y_F3 | 837,899 / 1737 | -1.4765 [-1.7370, -1.2161], p=1.11e-28 | +7.009, p=0 | -1.3609 [-1.6336, -1.0882], p=1.37e-22 | +0.6918 [0.4987, 0.8848], p=2.15e-12 (768,049 / 1493) |
| all | net xG | 1,124,949 / 1738 | -0.0331 [-0.0555, -0.0106], p=0.00391 | +7.422, p=0 | -0.0480 [-0.0728, -0.0233], p=0.000146 | -0.0315 [-0.0470, -0.0160], p=6.99e-05 (1,047,700 / 1493) |
| DM | Y_F3 | 152,663 / 185 | +0.3325 [0.0204, 0.6446], p=0.0368 | +2.816, p=6.5e-43 | +0.3683 [0.0622, 0.6744], p=0.0184 | +0.5325 [0.2008, 0.8641], p=0.00165 (151,737 / 185) |
| DM | net xG | 176,349 / 185 | -0.0043 [-0.0236, 0.0149], p=0.66 | +2.731, p=8.5e-50 | -0.0045 [-0.0237, 0.0147], p=0.643 | +0.0038 [-0.0171, 0.0246], p=0.721 (175,308 / 185) |

### Claims (fixed rules, applied mechanically)
- **All players:** A-i r_true's 95% lower bound 0.735 > 0, so the statement "press resistance travels with the player across teams" is allowed.
- **Deep midfielders:** not claimed. A-i is unmeasurable (4 movers).
- **Part B** is exploratory. Per the brief, nothing in it is claimed until it is confirmed on the reserved data.

## 4. Deviations from the brief
- **Step 0:** the brief was not committed alone.
- **Movers** use Study B's PH-B2 definition exactly (club side vs international side), as the brief says "exactly as Study B's PH-B2". Players with ≥2 contexts that are all club or all international are not movers. Of the 90 players with ≥2 contexts, 24 are club-and-country movers.
- **Part B floors** are not given in the brief: W ≥100 receptions; RQ_rel ≥100; PR ≥50 (study) / ≥30 (WC2022 subset); AV_out ≥100 moments.
- **Part B deep-midfield groups:** the study's 111 (S1) and Task 38's PFF WC2022 group (S2).
- **AV_out's "passer under pressure"** = Task 38's moment context flag (pressureType ≠ 'N'). Its baseline was refit on those moments with Task 38's `fit_oof`.
- **B3 unit** = every completed reception (the unit W is defined on), not only pressured receptions. S_PR in the joint model is the other-match mean over pressured receptions. Rows lacking S_PR drop from the joint model.
- **Top quartile** = ≥ the 75th percentile within the pair's players. The hypergeometric p is reported in both directions.
- **Variance split:** units need ≥30 pressured receptions (the brief's context floor; Study B used 20). Covariates are Study B's zone shares, without the pressure share, which is constant here.

## 5. Problems and surprises
- **A-i rests on 24 movers.** The CI upper bound hits the cap of 1.0.
- **Deep-midfield movers are too few** (4) for a measurable disattenuated correlation. The variance-split S interval for deep midfielders spans almost the whole range (0.000-1.000; 72 units, 53 players).
- **A-ii's deep-midfield r_true is capped at 1.0**, on 12 players with a national-team reliability of 0.447.
- **B3 across all players: higher other-match W predicts LOWER Y_F3** (−1.48 pp per 100 receptions per SD, p = 1e-28) and lower net xG (p = 0.004). In the joint model, S_PR predicts Y_F3 positively (+0.69, p = 2e-12). Within deep midfielders, both S_W and S_PR are positive for Y_F3 (joint p = 0.018 and 0.0017) and null for net xG.
- **B2, S1 across all players:** RQ_rel correlates +0.51 with PR (31 players in the top quartile of both, 15.4 expected). The spatial measure is negatively related to willingness but positively to success.
- **The S2 deep-midfield samples are small** (35 and 20 players).

## 6. Questions for the research lead
- None.

## 7. Files produced
- `src/engine_v2/task46_part_a.py`, `src/engine_v2/task46_part_b.py`.
- `data/engine_v2_task46_part_a.json`, `data/engine_v2_task46_part_b.json`, `data/processed/engine_v2/task46_study_pr_flag.parquet` (none committed).
- Side effects: none else. No memory writes. JOURNAL.md and AGENTS.md untouched. Reserved data not opened; holdout untouched.
- Commits: brief 105e500 (research lead); interim page 8648d7f; final 6ad0ed7.

## 8. Confidence
Study B's machinery is reused unchanged.
The weakest links:
- The mover count (24 players; 4 deep midfielders).
- Part B's exploratory status: many tests, and nothing confirmed on the reserved data.
