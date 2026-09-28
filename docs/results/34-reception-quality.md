# Task 34: Reception quality (space at reception, context-adjusted)
Date: 2026-09-28
Status: PARTIAL (Step 1 only; Steps 2-3 NOT RUN yet — interim commit required by the brief)

## Checklist
| Section | Status |
|---|---|
| Step 0 — brief committed alone | COMPLETE (5ac7246, by the research lead) |
| Memory gate before Step 1 | COMPLETE |
| Step 1 — the measure | COMPLETE |
| Step 2 R1-R4 | NOT RUN |
| Step 3 — deep-midfield table | NOT RUN |

## 1. Headline
Step 1 only: 245,163 receptions in 292 matches; f(context) out-of-fold R^2 = 0.237.
Mean RQ by zone is not exactly zero: final third +0.061 (SE 0.012, n=61,048), middle +0.041 (SE 0.011).

## 2. What I did
- Step 0: brief `docs/specs/task-34-reception-quality.md` committed alone in 5ac7246 by the research lead. Not modified.
- Memory gate (2026-09-28 10:33 PDT): memory_pressure free 72%, available ~6.09 GB (free+inactive+speculative pages from vm_stat). Above 40% / 3 GB.
- Step 1: `.venv/bin/python src/engine_v2/task34_step1_rq.py`

## 3. Numbers (Step 1)
- Matches: 292 (options_ev_v4 set ∩ cv_folds.csv).
- Successful Ball Receipt* events: 271,830. With a 360 frame containing an actor: 245,163 (90.19%). The brief said "about 93%".
- Receptions with zero visible opponents: 165 (space set to 15).
- Share of receptions at the 15 cap: 10.19%.
- Players: 2,279. Team-contexts: 159.
- f(context) pooled out-of-fold R^2: 0.2367 (n=245,163).
- Mean RQ overall: +0.032 (SD 3.77).

Mean RQ by zone (receiver x; defensive <40, middle 40-80, final ≥80):

| Zone | n | mean space | mean RQ | SE |
|---|---|---|---|---|
| defensive | 55,919 | 9.848 | −0.018 | 0.017 |
| middle | 128,196 | 7.838 | +0.041 | 0.011 |
| final | 61,048 | 5.565 | +0.061 | 0.012 |

Distributions:

| | mean | sd | q01 | q05 | q25 | q50 | q75 | q95 | q99 |
|---|---|---|---|---|---|---|---|---|---|
| space | 7.731 | 4.316 | 0.637 | 1.437 | 4.148 | 7.192 | 11.151 | 15.0 | 15.0 |
| f_oof | 7.698 | 2.162 | 2.406 | 4.067 | 6.529 | 7.534 | 8.820 | 11.678 | 13.311 |
| RQ | 0.032 | 3.771 | −7.667 | −5.913 | −2.776 | −0.143 | 2.815 | 6.468 | 7.982 |
| RQ_rel | 0.010 | 3.804 | −7.730 | −5.954 | −2.829 | −0.188 | 2.828 | 6.516 | 8.058 |

Visible opponents per frame: mean 8.37, median 9, q01 2.

## 4. Deviations from the brief
- Zero-visible-opponent frames (165) given space = 15 (the cap applied to an infinite distance). The brief does not say. See Q3.
- opp_ctx_mean_space is undefined for 11,605 receptions: 22 opponent team-contexts appear in only one match, so "its OTHER matches" is empty. Left as missing; XGBoost's native missing-value handling used. Not dropped.
- XGBoost parameters not named by the brief (colsample_bytree etc.) left at library defaults, as in Task 33.
- Opponents = every frame row with teammate == False, including the goalkeeper.

## 5. Problems and surprises
- Frame coverage 90.19%, not ~93% as the brief states.
- Mean RQ by zone is not zero: final +0.061 (≈5 SE), middle +0.041 (≈3.7 SE). Small relative to SD 3.77, but not zero "by construction". Cross-fitted f is not guaranteed zero-mean per zone, so this is not by itself a bug; reported as is.
- 10.2% of receptions sit at the 15 cap, so the space distribution is censored at the top.
- If taken at face value, R^2 = 0.24 means context explains about a quarter of space; the remaining 76% goes into RQ, including frame noise (visibility limits of 360 data) as well as any player effect.

## 6. Questions for the research lead
- Q3: zero-visible-opponent frames: 15 (used), or drop them?
- Q5: 22 opponent contexts with only one match: missing feature (used), or other handling?

## 7. Files produced
- `src/engine_v2/task34_step1_rq.py`
- `data/processed/engine_v2/task34_receptions.parquet` (not committed; data/)
- `data/engine_v2_task34_step1.json` (not committed; data/)
- This page. Step 1 commit: recorded in the final version.

## 8. Confidence
Step 1 only. Weakest link: 360 visibility — "nearest visible opponent" is the nearest opponent inside the camera view, so space is overstated wherever the true nearest opponent is off-camera.
