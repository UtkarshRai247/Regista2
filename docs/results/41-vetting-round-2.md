# Task 41: Vetting round 2 (measurement only), CRITIQUE-v6 items 1a-1f, 2a, 2c, 2d, 3b
Date: 2026-09-28
Status: PARTIAL (Steps 0-6 run; Steps 7-10 NOT RUN yet — interim commit required by the brief)

## Checklist
| Section | Status |
|---|---|
| Step 0 — commit brief alone | COMPLETE (7c678c9) |
| Memory gate | COMPLETE (56% free, ~4.71 GB, 15:19 PDT) |
| Task 35 reproduction assert | COMPLETE (coef 0.0007469384836865591, SE 0.00024360166295770252, identical) |
| Step 1 (1a) — where he usually plays | COMPLETE |
| Step 2 (1b) — roles | COMPLETE |
| Step 3 (1c) — outcome definition | COMPLETE |
| Step 4 (1d) — inference | COMPLETE |
| Step 5 (1e) — size | COMPLETE |
| Step 6 (1f) — DM bounds | COMPLETE |
| Steps 7-10 | NOT RUN |

## 1. Headline
Steps 0-6 only. The base v5 Decision P-test coefficient (+0.0747 xG per 100 passes per SD, n = 168,855 / 440) stays positive with p < 0.01 under every variant tried:
- controls for location and ev_chosen: +0.080 to +0.163;
- position-label fixed effects: +0.153;
- three outcome definitions: +0.045 to +0.094;
- two-way clustering: p = 0.0088;
- passer bootstrap: 95% CI [0.024, 0.127].

By role, only forwards show it significantly (21 players, +0.612 per 100, p = 2.5e-12). Each of the other five roles is non-significant (p 0.08-0.79).

## 2. What I did
- Step 0: committed the brief alone (7c678c9).
- `.venv/bin/python src/engine_v2/task41_ptest_vetting.py`:
  - Regenerates Task 35's inputs with its own functions and asserts the (a) coefficient/SE reproduce.
  - `fit_multi()` is `task35_ptest.fe_fit`'s estimator generalised to several standardised covariates and any fixed-effect label. It is asserted equal to `fe_fit` on the base model.
  - S_x, S_y and S_ev are leave-one-match-out passer means (≥100 elsewhere, `task32_step5.leave_one_match_out`).
  - The Step 3 Y variants use one generalised net-xG function, asserted equal to Task 35's `net_xg_after` for the base window. g is refit for each variant with `task35_ptest.crossfit_g`.
  - Step 4 uses statsmodels two-way clustering (passer, match) and a 1,000-resample passer bootstrap (seed 20260928).

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

## 4. Deviations from the brief
- **"Normalised starting x and y"** = the value-model origin features `ball_x`/`ball_y` for each pass (team-relative, attacking toward x = 120).
- **Model D fixed effect:** each pass's StatsBomb `position` label from the event (23 labels in the rows).
- **Bootstrap:** S is standardised once on the full sample and held fixed across resamples. Duplicated passers count as distinct draws, and team-match fixed effects are re-absorbed in each resample.
- **Step 5:** the size uses the SD of S across all passes. A within-role SD would change the per-role numbers; see Q1.

## 5. Problems and surprises
- **The role split has one driver.** Forwards (21 players) carry a coefficient eight times the overall one; the five other roles are each non-significant. Taken at face value, the overall P-test result is driven by forwards, and it does not show that Decision predicts results within any non-forward role at this sample size (MDEs 0.036-0.246).
- **The Decision coefficient rises when S_ev is added** (+0.075 → +0.112 → +0.163 with location), and S_ev's own coefficient is negative (−0.177 in C).
- Excluding the passer's own shots (Step 3a) leaves the coefficient at +0.078. The overall result is therefore not produced by passers' own shots, but this was not checked within forwards.

## 6. Questions for the research lead
- Q1 (Step 5): should "one SD above his role's average" use a within-role SD of S?

## 7. Files produced (so far)
- `src/engine_v2/task41_ptest_vetting.py`, `data/engine_v2_task41_steps1_6.json` (not committed).
- Commits: brief 7c678c9; this interim page: recorded in the final version.

## 8. Confidence
Steps 1-6 reuse Task 35's estimator, and its reproduction is asserted exactly. The weakest link is the role split: there are only 21 forwards, and the whole-sample effect rests on them.
