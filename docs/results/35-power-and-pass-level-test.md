# Task 35: Power check and pass-level out-of-match test (P-test)
Date: 2026-09-28
Status: COMPLETE (every section run; operational choices and one smaller-than-specified sample in Section 4)

## Checklist
| Section | Status |
|---|---|
| Step 0 — commit brief alone | COMPLETE (61b576f) |
| Step 1 — MDEs of Tasks 32 / 33 / 34 out-of-match tests + scale | COMPLETE |
| Step 2 — P-test (a)-(d), positive control, Holm | COMPLETE (pass sample 239,588 of 250,850, see Section 4) |
| Step 3 — same within the 111 deep midfielders | COMPLETE |

## 1. Headline
Within the 111 deep midfielders (Step 3; 79-88 players, about 30-34k rows), v5 Decision, v6 Decision and v5 ev_chosen are not detected (Holm p = 1.0 for each; MDEs 0.054-0.062 xG per 100 passes per SD). Reception RQ_rel is detected (+0.056 per 100 receptions per SD, Holm p = 0.025, n = 79 receivers).
Across all passers (Step 2, 440 passers, 168,855 passes), v5 and v6 Decision are positive after Holm (both p_holm = 0.0087). ev_chosen (p_holm = 0.11) and RQ_rel (p_holm = 0.47) are not.
The positive control (other-match completion rate predicts completion) is clearly positive in Step 2 (p = 9e-27) and weaker in Step 3 (p = 0.016, n = 88 passers). Step 1: the earlier team-match tests had MDEs of 0.12-0.52 xG per match per SD, against a between-team-context SD of team mean xG of 0.646.

## 2. What I did
- Step 0: committed the brief alone (61b576f).
- Step 1: `src/engine_v2/task35_step1_mde.py` reads each `decision_z` SE from `data/engine_v2_task32_step5.json`, `data/engine_v2_task33_step4a.json` and `data/engine_v2_task34_step2_3.json`, and computes MDE = 2.8 × SE. Scale comes from `outcome_validation.build_team_match_units` + `add_xg` on the 292 matches.
- Steps 2-3: `src/engine_v2/task35_ptest.py`.
  - Y = net shot xG over events i+1..i+10 (events sorted by `index`), from the pass's or reception's own team perspective.
  - g = cross-fitted XGBoost using `task33_step3_f_state.F_STATE_FEATURES`, `XGB_REGRESSOR_KWARGS` and the `crossfit.FOLDS_PATH` folds. Three g fits: pass net xG, pass completion (for the control), and reception net xG.
  - S = `task32_step5.leave_one_match_out` with ≥100 elsewhere, standardised across the analysis rows.
  - Roles = `task32_step4.assign_roles`.
  - Team-match fixed effects absorbed by within-demeaning. Frisch-Waugh was checked against a full-dummy OLS on 40 team-matches: 0.00052445 in both.
  - OLS with SE clustered by player. Holm (statsmodels `multipletests`) across (a)-(d), separately for Step 2 and Step 3.
- Reproduce: `.venv/bin/python src/engine_v2/task35_step1_mde.py && .venv/bin/python src/engine_v2/task35_ptest.py`

## 3. Numbers

### Step 1 — MDE of the team-match tests (80% power, alpha 0.05, MDE = 2.8 × SE; units: xG or goals per match per SD)

| Task | Test | Spec | n | coef | SE | MDE |
|---|---|---|---|---|---|---|
| 32 Step 5 | LINEUP Decision v5 | xG H-O1 | 400 | +0.082 | 0.060 | 0.168 |
| 32 Step 5 | LINEUP Decision v5 | xG PH-O2 | 400 | −0.108 | 0.130 | 0.364 |
| 32 Step 5 | LINEUP Decision v5 | goals H-O1 | 400 | +0.132 | 0.067 | 0.189 |
| 32 Step 5 | LINEUP Decision v5 | goals PH-O2 | 400 | +0.031 | 0.144 | 0.404 |
| 32 Step 5 | TEAM Decision v5 | xG H-O1 | 562 | +0.026 | 0.043 | 0.120 |
| 32 Step 5 | TEAM Decision v5 | goals H-O1 | 562 | +0.012 | 0.046 | 0.128 |
| 33 Step 4a | LINEUP Decision v6 | xG H-O1 | 382 | −0.078 | 0.068 | 0.191 |
| 33 Step 4a | LINEUP Decision v6 | xG PH-O2 | 382 | −0.141 | 0.145 | 0.407 |
| 33 Step 4a | LINEUP Decision v6 | goals H-O1 | 382 | +0.030 | 0.064 | 0.179 |
| 33 Step 4a | LINEUP Decision v6 | goals PH-O2 | 382 | +0.016 | 0.184 | 0.516 |
| 33 Step 4a | LINEUP ev_chosen v6 | xG H-O1 | 382 | +0.261 | 0.065 | 0.181 |
| 33 Step 4a | LINEUP ev_chosen v6 | xG PH-O2 | 382 | −0.098 | 0.156 | 0.438 |
| 33 Step 4a | LINEUP ev_chosen v6 | goals H-O1 | 382 | +0.236 | 0.078 | 0.218 |
| 33 Step 4a | LINEUP ev_chosen v6 | goals PH-O2 | 382 | −0.030 | 0.174 | 0.486 |
| 33 Step 4a | LINEUP f(state) alone | xG H-O1 | 382 | +0.300 | 0.057 | 0.160 |
| 33 Step 4a | LINEUP f(state) alone | xG PH-O2 | 382 | −0.057 | 0.156 | 0.436 |
| 33 Step 4a | LINEUP f(state) alone | goals H-O1 | 382 | +0.229 | 0.080 | 0.224 |
| 33 Step 4a | LINEUP f(state) alone | goals PH-O2 | 382 | −0.040 | 0.185 | 0.518 |
| 33 Step 4a | LINEUP Decision_policy v6 | xG H-O1 | 382 | +0.067 | 0.068 | 0.190 |
| 33 Step 4a | LINEUP Decision_policy v6 | xG PH-O2 | 382 | −0.054 | 0.150 | 0.421 |
| 33 Step 4a | LINEUP Decision_policy v6 | goals H-O1 | 382 | +0.148 | 0.071 | 0.199 |
| 33 Step 4a | LINEUP Decision_policy v6 | goals PH-O2 | 382 | +0.089 | 0.168 | 0.469 |
| 34 R3 | LINEUP RQ | xG H-O1 | 373 | +0.025 | 0.076 | 0.212 |
| 34 R3 | LINEUP RQ | xG PH-O2 | 373 | −0.151 | 0.125 | 0.351 |
| 34 R3 | LINEUP RQ | goals H-O1 | 373 | −0.015 | 0.069 | 0.194 |
| 34 R3 | LINEUP RQ | goals PH-O2 | 373 | −0.330 | 0.135 | 0.377 |

Scale over the 292 matches: 584 team-matches in 158 team-contexts (mean 3.70 matches per context, median 3).
- SD across contexts of context mean xG per match: **0.646**.
- The same SD for goals: 0.724.
- The same xG SD restricted to the 28 contexts with ≥5 matches: 0.643.
- SD of team-match xG: 1.102.

### Step 2 — P-test, all passers (team-match FE, role FE, g_oof; SE clustered by player)

| Measure | n rows | n players | n team-matches | coef per SD (xG per pass) | per 100 | 95% CI (per 100) | p | p Holm | MDE (per 100) |
|---|---|---|---|---|---|---|---|---|---|
| **Positive control** (completion ~ other-match completion rate; Y 0/1) | 168,855 | 440 | 506 | +0.02201 (prob.) | +2.201 pp | [1.798, 2.604] | 9.5e-27 | — | 0.576 |
| (a) v5 Decision | 168,855 | 440 | 506 | +0.000747 | +0.0747 | [0.0269, 0.1224] | 0.0022 | 0.0087 | 0.0682 |
| (b) v6 Decision | 153,279 | 402 | 494 | +0.000468 | +0.0468 | [0.0163, 0.0773] | 0.0027 | 0.0087 | 0.0436 |
| (c) v5 ev_chosen | 168,855 | 440 | 506 | +0.000589 | +0.0589 | [−0.0013, 0.1191] | 0.0550 | 0.1100 | 0.0860 |
| (d) reception RQ_rel (unit = reception) | 166,087 | 446 | 499 | +0.000238 | +0.0238 | [−0.0410, 0.0887] | 0.4714 | 0.4714 | 0.0926 |

Positive control: POSITIVE, so the brief's condition for interpreting (a)-(d) is met.

### Step 3 — same, rows restricted to the 111 deep midfielders

| Measure | n rows | n players | n team-matches | coef per SD | per 100 | 95% CI (per 100) | p | p Holm | MDE (per 100) |
|---|---|---|---|---|---|---|---|---|---|
| Positive control | 33,889 | 88 | 418 | +0.00626 (prob.) | +0.626 pp | [0.115, 1.137] | 0.0163 | — | 0.730 |
| (a) v5 Decision | 33,889 | 88 | 418 | +0.000087 | +0.0087 | [−0.0297, 0.0471] | 0.657 | 1.0 | 0.0548 |
| (b) v6 Decision | 31,563 | 80 | 408 | +0.000147 | +0.0147 | [−0.0228, 0.0523] | 0.441 | 1.0 | 0.0536 |
| (c) v5 ev_chosen | 33,889 | 88 | 418 | −0.000011 | −0.0011 | [−0.0443, 0.0420] | 0.958 | 1.0 | 0.0616 |
| (d) reception RQ_rel | 29,940 | 79 | 398 | +0.000555 | +0.0555 | [0.0158, 0.0952] | 0.0062 | 0.0248 | 0.0568 |

### Supporting numbers
- g out-of-fold R^2: pass net xG 0.0448; pass completion 0.1282; reception net xG 0.1921.
- Y (pass net xG over i+1..i+10): mean 0.0056, SD 0.0431.
- SD of S before standardising (Step 2): Decision v5 0.00165, Decision v6 0.00083, ev_chosen 0.00413, RQ_rel 1.618, completion rate 0.057.
- Rows in singleton team-matches (dropped by the fixed effect): 0 in Step 2 and 1-2 in Step 3.
- Role "NONE" rows (player outside the 537): 0 for passes and 4,454 for receptions (Step 2).

## 4. Deviations from the brief
- **Pass sample is smaller than the brief's corpus.** The brief says "eligible pass (engine v5 corpus)", which is 250,850 passes in `pass_der_crossfit_v5.parquet`. Only 239,588 have origin features in `value_model_rows_v5.parquet`, so the 11,262 passes without a value-model row have no g and were dropped. `task33_step3_f_state.build_feature_table` has the same coverage (Task 33's f(state) population). After the ≥100-elsewhere filter, Step 2's pass models use 168,855 rows.
- **Window.** The brief says events i+1..i+10 and "same window convention as the value model". `value_models_v5` trains on events i..i+9 ("label counts its own event"). I used the brief's explicit i+1..i+10. For Pass and Ball Receipt* events, event i is never a shot, so the only difference is whether event i+10 is included.
- **One pass-level g** (net xG) was fitted on all 239,588 passes and used for (a), (b) and (c). The positive control got its own g, fitted with target = completion (0/1), using the brief's `reg:squarederror` hyperparameters unchanged.
- **Reception g features:** the same 18 F_STATE_FEATURES, taken from `value_model_rows_v5`'s Ball Receipt* rows, plus the receipt event's `under_pressure`, and `period`/`minute`. Of Task 34's 245,163 receptions, 241,222 have a value-model row; the other 3,941 were dropped.
- **(b) v6 Decision** uses non-excluded v6 passes, as in Task 33 Step 4a.
- **(d) threshold:** ≥100 receptions elsewhere. The brief's "≥100" is stated for passes.
- **Role FE:** players outside Task 32's 537 get role "NONE" (receptions only: 4,454 rows). Role dummies with no within-team-match variation are dropped.
- **Standardisation of S:** done across each analysis's own rows, so Step 3 is standardised within deep-midfield rows. "Per SD" in Step 3 therefore means per deep-midfield SD.
- **Step 3 reuses Step 2's g_oof** rather than refitting g on deep-midfield rows.
- **FE estimation:** within-transformation, which gives identical point estimates to dummies (checked). The cluster-robust SE small-sample factor does not count the absorbed team-match levels, which makes SEs very slightly smaller than a full-dummy fit would.
- **Holm families:** Step 2 (a)-(d) and Step 3 (a)-(d) were corrected separately. The control is not in either family.
- **Step 1 extras** not asked for: the SD for contexts with ≥5 matches, and the team-match xG SD. They are reported for scale only.
- **Context counts:** Step 1 counts 158 team-contexts from match metadata team names, while Task 34 counted 159 from event team names. I did not investigate the difference.

## 5. Problems and surprises
- **(d) differs between populations:** not detected across all receivers (p = 0.47) but detected within deep midfielders (p_holm = 0.025). Taken at face value, reception quality relates to next-10-event xG only for deep midfielders. The Step 3 control is also much weaker than Step 2's (p = 0.016, with an MDE of 0.73 pp against Step 2's 0.58 pp), so Step 3's power to detect a real skill is lower.
- **(a) and (b) are positive across all passers but not within deep midfielders.** Taken at face value, the all-passer result does not establish that Decision separates deep midfielders.
- **Step 1:** 21 of 26 earlier specs have MDE ≥ 0.18 xG per match per SD. The PH-O2 MDEs (0.35-0.52) are more than half the 0.646 between-context SD. If taken at face value, earlier "not detected" results from these specs (Tasks 32, 33 and 34) do not show absence of an effect of that size.
- **g for pass net xG explains only 4.5%** of Y's variance. Y is dominated by rare shots (SD 0.043, mean 0.0056).
- The Step 2 effect sizes are small in absolute terms. For (a), +0.075 xG per 100 passes per SD compares to a Y mean of 0.56 xG per 100 passes. No interpretation is offered here.

## 6. Questions for the research lead
- Q1: Should the 11,262 passes without a value-model row be scored with an alternative origin-feature source, or is Task 33's f(state) population the intended corpus?
- Q2: Window i+1..i+10 (used) or value-model i..i+9?
- Q3: Should Step 3's S be standardised on the all-passer SD instead, so Step 2 and Step 3 coefficients are on the same scale?
- Q4: Should the Holm family span Steps 2 and 3 together (8 tests) rather than separately?

## 7. Files produced
- `src/engine_v2/task35_step1_mde.py`, `src/engine_v2/task35_ptest.py`.
- `data/engine_v2_task35_step1.json`, `data/engine_v2_task35_ptest.json` (not committed; data/).
- This page.
- Commits: brief 61b576f; final commit recorded in a follow-up commit.
- Side effects: none beyond these files. No memory writes. JOURNAL.md, AGENTS.md and task-36 spec left untouched and uncommitted.

## 8. Confidence
The mechanics are verified: Frisch-Waugh matches the dummy fit exactly, the positive control is detected, and fold, g and feature reuse are unchanged from Task 33.
The weakest links are three:
- The Step 3 conclusions rest on 79-88 players, with a positive control of only p = 0.016.
- The 11,262-pass drop.
- The within-transformation SE caveat, which is small at 506 team-matches with 440 clusters.
