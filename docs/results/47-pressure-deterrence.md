# Task 47: Do opponents learn to stop pressing a press-resistant player?
Date: 2026-09-28
Status: COMPLETE (every section run; deviations in Section 4)

**Development task (exploratory) on 2015/16, a further use of that season.** The reserved data (Task 46) was not opened. Holdout untouched.

## Checklist
| Section | Status |
|---|---|
| Step 0 — brief | COMPLETE, with a deviation: committed by the research lead in 105e500 **together with the Task 46 brief**, not alone |
| Memory gate | COMPLETE (56% free, ~4.74 GB, 20:05 PDT) |
| Step 1 — units and measures | COMPLETE |
| Step 2 — main test | COMPLETE |
| Step 3 (a)-(d) — placebo, second-half split, season level, deep midfielders | COMPLETE |

## 1. Headline
**Step 2: a player's first-half press escape (E1) predicts a larger drop in the pressure he receives in the second half.** The E1 coefficient is -0.00371 per SD, 95% CI [-0.00640, -0.00103], p = 0.00676, on 11,491 player-matches (1,577 players).
**Placebo (a):** the same E1 predicts a small INCREASE in his teammates' pressure change (+0.00055, p = 0.000719). That is not negative, so under the fixed rule the idea is **proposed for confirmation on the reserved data**.
**Deep midfielders only (d):** E1 is +0.00503, p = 0.31 (185 players), which does not match the all-player sign.

## 2. What I did
- Step 0: the brief was committed by the research lead in 105e500 (with Task 46's brief).
- `.venv/bin/python -W ignore src/engine_v2/task47_deterrence.py`:
  - **Data:** reads Task 44's 2015/16 reception table. PRESSURED is Task 44's flag rule.
  - **Outfield filter:** the receipt `position` from the 2015/16 events removes goalkeepers; periods 1-2 only.
  - **Expected pressure p(context):** XGBoost classifier (Task 42's settings; Task 44's seeded 5 match folds) on reception x, y, play pattern, minute, score difference and Task 32 role (players without a role → "NONE"). Unit value = PRESSURED − p.
  - **Units:** player × match with ≥10 completed receptions in each half. P_H1 and P_H2 are his mean unit values in each half. E1 is his mean PR2_flag_keep over first-half pressured receptions (≥5 required).
  - **Models:** `task41_ptest_vetting.fit_multi`, with team-match fixed effects (his team in that match), role fixed effects and SE clustered by player. E1 and P_H1 are standardised. An all-zero g column is passed and dropped by the estimator.

## 3. Numbers

### Step 1 — units and base rates
- Completed receptions: 1,158,231; outfield in periods 1-2: 1,124,590.
- PRESSURED rate: 0.290. Expected-pressure baseline OOF AUC: 0.684.
- Player-matches with ≥10 receptions in each half: 19,738. Of these, **11,491** also have ≥5 first-half pressured receptions (1,577 players, 3,001 team-matches).
- Means over units: P_H1 +0.0592; P_H2 +0.0207; E1 +0.0115 (from a mean of 8.2 pressured receptions).

### Steps 2-3 — models (coefficients per SD; outcome in units of pressured share)

| Model | n units | players | team-matches | E1 coef | 95% CI | p | P_H1 coef |
|---|---|---|---|---|---|---|---|
| **Step 2 main: his (P_H2 − P_H1)** | 11,491 | 1577 | 3,001 | -0.00371 | [-0.00640, -0.00103] | 0.00676 | -0.09758 (p=0) |
| (a) placebo: teammates' (P_H2 − P_H1) | 11,491 | 1577 | 3,001 | +0.00055 | [+0.00023, +0.00088] | 0.000719 | +0.01152 (p=0) |
| (b) his P(46-67) − P_H1 | 10,958 | 1553 | 2,973 | -0.00529 | [-0.00870, -0.00187] | 0.00244 | -0.09469 (p=0) |
| (b) his P(68-90) − P_H1 | 9,269 | 1485 | 2,914 | -0.00199 | [-0.00583, +0.00184] | 0.308 | -0.09747 (p=0) |
| (d) deep midfielders: main | 1,768 | 185 | 1,474 | +0.00503 | [-0.00459, +0.01466] | 0.305 | -0.08786 (p=5.5e-33) |
| (d) deep midfielders: placebo | 1,768 | 185 | 1,474 | -0.00036 | [-0.00154, +0.00081] | 0.542 | +0.01216 (p=4.2e-46) |

### Step 3 (c) — season level (players with ≥10 matches; Pearson r between season mean PR2_flag_keep and season mean P, within role; report only)

| Role | n | r | 95% CI |
|---|---|---|---|
| AM/W | 364 | -0.441 | [-0.521, -0.355] |
| CB | 276 | -0.101 | [-0.217, +0.017] |
| CM | 111 | -0.510 | [-0.636, -0.358] |
| DM | 215 | -0.261 | [-0.381, -0.132] |
| FB | 294 | -0.330 | [-0.428, -0.224] |
| FW | 199 | -0.291 | [-0.414, -0.159] |
| MIXED | 49 | -0.223 | [-0.474, +0.062] |
| pooled_within_role | 1508 | -0.316 | [-0.361, -0.270] |

### Claim rule (fixed), applied mechanically
- Step 2's E1 coefficient is negative with p < 0.05: **yes** (p = 0.00676).
- Placebo (a) is negative with p < 0.05: **no**. It is positive (p = 0.000719).
- So a statement is **proposed for confirmation on the RESERVED data**. It is exploratory here and not claimed.

## 4. Deviations from the brief
- **Step 0:** the brief was not committed alone.
- **Outfield** = the receipt's StatsBomb position is not Goalkeeper. Units use periods 1 and 2 only (extra time excluded).
- **Role for players without a Task 32 role** (fewer than 100 eligible passes) is "NONE", used both in p(context) and in the role FE.
- **Placebo outcome:** teammates' change = (the team's outfield receptions in H2 excluding his) mean minus (the same in H1) mean, over every teammate reception in that match.
- **(b) second-half parts:** period-2 minute ≤ 67 ("46-67") and ≥ 68 ("68-90", including stoppage time). Units need ≥5 receptions in the part; the brief sets no floor.
- **(c) season level:** season mean P over all his receptions; season mean PR2_flag_keep over his pressured receptions. Also pooled after demeaning within role.

## 5. Problems and surprises
- **The placebo moves the opposite way:** E1 predicts slightly more second-half pressure on his teammates (p = 0.0007).
- **The effect is concentrated in minutes 46-67** (-0.00529, p = 0.00244); it is not significant in 68-90 (p = 0.31).
- **Deep midfielders show the opposite sign**, not significant (185 players, 1,768 units).
- **Effect size:** the Step 2 coefficient (−0.0037 per SD of E1) is small against the mean first-half value P_H1 (+0.059).
- **Season level:** within every role, players with higher PR2_flag_keep are pressed less overall (pooled within-role r = -0.316, n = 1508). The brief notes a negative correlation would fit opponents avoiding pressing him, and it is also what a common cause would produce. No interpretation is offered.
- **P_H1's own coefficient** is large and negative, the expected regression-to-the-mean term.

## 6. Questions for the research lead
- None.

## 7. Files produced
- `src/engine_v2/task47_deterrence.py`.
- `data/engine_v2_task47.json` (not committed).
- Side effects: none else. No memory writes. JOURNAL.md and AGENTS.md untouched. Reserved data not opened; holdout untouched.
- Commits: brief 105e500 (research lead); this page: recorded in a follow-up commit.

## 8. Confidence
- The model reuses the project's fixed-effects estimator, with player-clustered SE.
- The weakest links:
  - E1 rests on few first-half pressured receptions per unit (mean 8.2).
  - The result is exploratory, with several related tests run.
