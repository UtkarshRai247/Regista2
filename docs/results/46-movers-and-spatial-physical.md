# Task 46: Player or team? And spatial vs physical press resistance
Date: 2026-09-28
Status: PARTIAL (Part A run; Part B NOT RUN yet — interim commit after Part A required by the brief)

**Development task (exploratory)**: study sample, PFF WC2022 and 2015/16 (third use of 2015/16). Holdout spent and untouched. The reserved data was not opened.

## Checklist
| Section | Status |
|---|---|
| Step 0 — brief | COMPLETE, with a deviation: committed by the research lead in 105e500 **together with the Task 47 brief**, not alone |
| RESERVED data listed by id, not opened | COMPLETE |
| Memory gate | COMPLETE (54% free, ~4.59 GB, 19:57 PDT) |
| Part A-i — movers (PH-B2) and variance split | COMPLETE |
| Part A-ii — 2015/16 club vs study national team | COMPLETE |
| Part B | NOT RUN |

## 1. Headline
**Part A claim allowed:** "press resistance travels with the player across teams".
- A-i (study sample, club vs country movers): r_true = **0.924**, 95% CI **[0.735, 1.000]**, on only **24 movers**.
- The deep-midfield version is unmeasurable: 4 movers, and the international split-half reliability is negative. It is not claimed.
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

### Part A claim (fixed rule, applied mechanically)
- **All players:** A-i r_true's 95% lower bound 0.735 > 0, so the statement "press resistance travels with the player across teams" is allowed.
- **Deep midfielders:** not claimed. A-i is unmeasurable (4 movers).

## 4. Deviations from the brief
- **Step 0:** the brief was not committed alone.
- **Movers** use Study B's PH-B2 definition exactly (club side vs international side), as the brief says "exactly as Study B's PH-B2". Players with ≥2 contexts that are all club or all international are not movers. Of the 90 players with ≥2 contexts, 24 are club-and-country movers.
- **Variance split:** units need ≥30 pressured receptions (the brief's context floor; Study B used 20). Covariates are Study B's zone shares, without the pressure share, which is constant here.

## 5. Problems and surprises
- **A-i rests on 24 movers.** The CI upper bound hits the cap of 1.0.
- **Deep-midfield movers are too few** (4) for a measurable disattenuated correlation. The variance-split S interval for deep midfielders spans almost the whole range (0.000-1.000; 72 units, 53 players).
- **A-ii's deep-midfield r_true is capped at 1.0**, on 12 players with a national-team reliability of 0.447.

## 6. Questions for the research lead
- None yet.

## 7. Files produced (so far)
- `src/engine_v2/task46_part_a.py`, `data/engine_v2_task46_part_a.json`, `data/processed/engine_v2/task46_study_pr_flag.parquet` (data not committed).
- Commits: brief 105e500 (research lead); this interim page: recorded in the final version.

## 8. Confidence
Study B's machinery is reused unchanged. The weakest link is the mover count (24 players; 4 deep midfielders).
