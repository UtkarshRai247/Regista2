# Task 25: Explain G1's residual, then rebuild the engine (Task 24 Steps 4-6)
Date: 2026-09-27
Status: COMPLETE

## Disclosure (per Task 24, repeated here)
This task continues engine work past Task 22's "no Task 22b" stop rule
and Task 24's own G1 gate failure. The engine has failed its acceptance
battery or a premise check at Tasks 19d, 21, 22, and (partially) 24.
This task's full pass of the falsification battery and its cross-fitted
outcome validation are reported in full below, including every prior
failure that preceded them, per that standing disclosure requirement.

## Section checklist
- Step 0 (commit brief alone): COMPLETE
- Step 1 (visibility vs. remaining coordinate error, fixed decision rule): COMPLETE — decision: VISIBILITY, continue to Step 2
- Step 2 (rebuild the engine — Task 24's Steps 4, 5, 6): COMPLETE — falsification battery ALL PASS; cross-fitted outcome validation run in full
- Memory gate (before Step 2, before EV recompute): COMPLETE — both readings recorded below, both well above the 40%/3GB floor
- Execution: NOT COMPUTED (Task 24 Step 1(c)'s `decision_execution_risk.py` defect stays unfixed and unexercised, per this task's brief) — recorded as a known issue

## 1. Headline
Task 24's residual (2.30% of band-0-40 in-possession rows flagged
"beyond the defensive line") is confirmed as the known 360-visibility
limitation, not a remaining coordinate error: restricted to frames with
≥10 visible opponents, the share falls to 0.04% (well under the
brief's 1% bar), and no team-period with ≥50 band-0-40 rows exceeds
20% beyond-line share (max 9.85%, no sign of a leftover 180-degree
flip). Per the brief's fixed decision rule, this authorized the full
rebuild (Task 24's Steps 4-6), which is now complete: **the falsification
battery passes in full for the first time in this project's history**
(T1-T6 all pass; T2's sign is correctly positive; all three T4
scenarios pass, with scenario_c clearing the corpus p90 by roughly 2x
instead of narrowly failing as in every prior task). The cross-fitted
outcome-validation battery shows a positive `decision_z` coefficient in
all 10 team-match specifications, 9 of 10 significant at p<0.05 (xg
H-O2 is marginal, p=0.069), and both possession-level specifications
(PH-O3a/b) are significant at p<1e-30. Taken at face value, this would
invalidate every finding reported in Tasks 15 through 23, all of which
were computed on a coordinate system now shown to rotate roughly half
of all events 180 degrees; it would NOT, by itself, validate Step 1's
own decision rule (a fixed, pre-declared threshold, not something this
page can independently confirm is the correct cutoff) or rule out a
still-more-subtle defect that this specific battery happens not to
detect.

## 2. What I did
1. Committed `task-25-engine-rebuild-v5.md` alone (Step 0).
2. Wrote and ran `task25_step1.py`: from
   `value_model_rows_diagnostic_v5.parquet`, band 0-40, in-possession
   rows, computed G1 share by visible-opponent-count bin, G1 restricted
   to ≥10 visible opponents, the residual rows' own characteristics,
   and the per-team-period beyond-line share — applying the brief's
   fixed decision rule (Step 1).
3. Memory gate check before Step 2: `memory_pressure`'s "System-wide
   memory free percentage" read 70% (well above 40%), no lingering
   processes.
4. Retrained M_for/M_against on the already-built
   `value_model_rows_v5.parquet` (`value_models_v5_retrain.py`).
5. Rebuilt the full candidate corpus from scratch on the corrected
   geometry (`grid_v2.py`, ~106M rows), retrained the pass-success
   model on it (`pass_success_v3.py`), memory-gate-checked again (67%
   free) before recomputing EV corpus-wide (`ev_recompute_v4.py`).
6. Re-ran Task 19c's exact offside calibration procedure on the
   corrected corpus (`offside_diagnostic_v3.py`) — selected a
   DIFFERENT rule this time (R1_K10, not Task 19c's R4) — applied it
   corpus-wide (`offside_v4.py`), refit the softmax temperature
   (`policy_baseline_fix_v5.py`), re-scored the full corpus
   (`policy_score_v8.py`), recomputed Decision/Risk and ran T6 +
   separation check (`step8_regate.py`, Execution not computed).
7. Ran the full falsification battery (`falsification_v3.py`): T1
   (restated), T2 (magnitude + sign), T3, T4 (all three scenarios,
   `EV_DIR` pointed at `options_ev_v4` from the start), T5, T6.
8. Ran the cross-fitted battery regardless of Step 5's verdict (it
   passed in full anyway), per the brief: `crossfit_v5.py` (5-fold,
   per-fold models on `value_model_rows_v5.parquet`, this task's
   temperature and offside rule, Execution not computed), then
   `outcome_validation_crossfit_v5.py`.

Reproduce with (from `src/engine_v2/`, `.venv` activated, in order):
`python task25_step1.py && python value_models_v5_retrain.py && python
grid_v2.py && python pass_success_v3.py && python ev_recompute_v4.py &&
python offside_diagnostic_v3.py && python policy_baseline_fix_v5.py &&
python policy_score_v8.py && python step8_regate.py && python
falsification_v3.py && python crossfit_v5.py && python
outcome_validation_crossfit_v5.py`.

## 3. Numbers

### Step 1 — visibility vs. remaining coordinate error (band 0-40, in-possession, n=184,727)
| visible opponents | n | n beyond line | share beyond line |
|---|---|---|---|
| 0-3 | 19,981 | 1,149 | 5.7505% |
| 4-6 | 76,103 | 2,160 | 2.8383% |
| 7-9 | 61,173 | 931 | 1.5219% |
| 10-11 | 27,470 | 11 | **0.0400%** |

**(b)** restricted to ≥10 visible opponents: n=27,470, 11 beyond-line,
share=0.0400% — well under 1%.

**(c)** residual (all 4,251 beyond-line rows, any visibility): median
`defensive_line_x`=25.70, **99.74%** have fewer than 10 visible
opponents.

**(d)** top 10 team-periods by band-0-40 beyond-line share: highest is
30.77% (Morocco, period 4, n=13 — below the brief's n≥50 floor);
among team-periods with n≥50 rows, the maximum share is **9.85%**
(Nashville SC, period 2, n=132) — far below the 20% threshold a
leftover 180-degree flip would produce.

**DECISION** (fixed by the brief): (b) 0.0400% < 1% — **TRUE**; no
n≥50 team-period exceeds 20% (max 9.85%) — **TRUE**. **Both hold →
residual attributed to visibility, continue to Step 2.**

### Step 2 — value-model retrain (on already-built `value_model_rows_v5.parquet`, n=828,728)
| quantity | value |
|---|---|
| M_for AUC (held out) | 0.9072 |
| M_against AUC (held out) | 0.9195 |
| T2 diff (p_for at adv p90 − p10) | +0.01272 |
| T2 materiality threshold | 0.000401 |
| T2 sign | **POSITIVE** (more numerical advantage ahead → higher scoring probability — the football-sensible direction, reversing every prior task's backwards sign) |

### Candidate corpus rebuild (`grid_v2.py`)
| quantity | this task | Task 15 original |
|---|---|---|
| eligible passes | 250,850 | 250,850 (unchanged — geometry doesn't change which candidates qualify) |
| total candidate rows | 106,141,669 | 106,141,669 (unchanged) |
| T1 median displacement | 1.6125 | 1.6125 (unchanged — distance-based, direction-invariant) |
| T1 verdict | PASS | PASS |

### Pass-success retrain (`pass_success_v3.py`)
Held-out AUC=0.9140. T5 calibration: all 4 length buckets pass (max
abs diff 2.18pp, bucket 50-50+). T7 off-policy support: share outside
convex hull ≈0 in every bucket.

### Offside recalibration (`offside_diagnostic_v3.py`, Task 19c's exact procedure, corrected corpus)
| quantity | this task | Task 19c (old geometry) |
|---|---|---|
| R0 (current/naive rule) FP rate | 11.84% | 23.69% |
| R0 recall | 91.77% | 46.58% |
| selected rule | **R1_K10** (K≥10 visible opponents, no M tolerance, no attacking-half restriction) | R4 (K=10, M=1, attacking-half-only) |
| selected rule FP rate | 2.91% | 4.83% |
| selected rule recall | **37.72%** | 16.96% |

A different rule composition is selected this time — recalibrating on
the corrected geometry does not merely shift R4's numbers, it changes
which candidate rule wins, with both a lower FP rate and more than
double the recall.

### Policy temperature refit (`policy_baseline_fix_v5.py`, `options_ev_v4`, offside_v4 restriction)
Fitted T=0.1562 (Task 19c's was 0.1572). Coverage=92.50% (up from Task
19c's ~91.7%). Median effective options=86.5, corr(policy-weighted vs
unweighted EV)=0.9035 — pre-specified reading: BEHAVIORAL.

### Decision/Risk regate (`step8_regate.py`, Execution not computed)
| quantity | this task | Task 19d (old geometry) |
|---|---|---|
| Decision reliability @200 (T6) | **0.8191** | 0.6149 |
| T6 verdict | PASS | PASS |

Separation check (n=252 qualifying player-seasons at ≥200 passes):
completion_pct r=−0.592, progressive_passes_per_90 r=−0.343, xa_per_90
r=**+0.714**, move_on_speed r=−0.159, hold_variation r=−0.082 — every
magnitude substantially larger than any prior task's equivalent
(reported, not gated, per the established convention).

### Step 5 — falsification battery
| test | pass condition | this task | Task 15 | Task 19d |
|---|---|---|---|---|
| T1 | median displacement ≤2u | 1.6125, **PASS** | 1.6125, PASS | (unaffected, not rerun) |
| T2 | magnitude ≥10% IQR; sign reported | diff=0.01272 (POSITIVE), **PASS** | — | diff=−0.02072 (NEGATIVE), PASS (magnitude only) |
| T3 | Spearman(EV,p_success)<0.90 | ρ=−0.2396, **PASS** | ρ≈0 range historically | — |
| T4a | unmarked > marked (equal p_success) | EV 0.01853 vs −0.00883, **PASS** | PASS | PASS |
| T4b | open space > cluster | EV 0.00536 vs −0.04014, **PASS** | PASS | PASS |
| T4c | through ball ≥ corpus p90 | EV 0.02378 ≥ p90 0.01169 (≈2x margin), **PASS** | PASS | **FAIL** (0.00232 < 0.00402) |
| T5 | calibration ≤5pp all buckets | max 2.18pp, **PASS** | PASS | (unaffected, not rerun) |
| T6 | reliability@200 ≥0.60 | 0.8191, **PASS** | — | 0.6149, PASS (thinnest margin at the time) |

**ALL SIX TESTS PASS.** This is the first task in this project where
T4's scenario_c is not a narrow pass or an outright failure but clears
its bar by roughly a factor of two.

### Step 6 — cross-fitted outcome validation
OOF AUC: pass_success=0.9116, M_for=0.8745, M_against=0.7222. OOF
policy top1=8.07%, top3=21.39%.

**Team-match specifications** (n=583 each), `decision_z` coefficient:
| spec | v1 published | Task 19d cross-fitted | this task cross-fitted |
|---|---|---|---|
| xg H-O1 | −0.1381, p=1.8e-4 | +0.1342, p=1.6e-3 | **+0.2486**, p=2.4e-10 |
| xg H-O2 | −0.1241, p=3.9e-4 | +0.0261, p=0.583 (n.s.) | **+0.0917**, p=0.069 (marginal) |
| xg PH-O1 | — | — | **+0.2404**, p=1.1e-7 |
| xg PH-O2 | — | — | **+0.2683**, p=2.5e-5 |
| xg PH-O4 | — | — | **+0.2753**, p=6.2e-9 |
| goals H-O1 | −0.4031, p<1e-12 | +0.1646, p=0.015 | **+0.2147**, p=2.3e-4 |
| goals H-O2 | −0.4587, p<1e-13 | +0.0615, p=0.362 (n.s.) | **+0.2641**, p=3.9e-4 |
| goals PH-O1 | — | — | **+0.2412**, p=8.4e-6 |
| goals PH-O2 | — | — | **+0.2758**, p=2.1e-5 |
| goals PH-O4 | — | — | **+0.2416**, p=1.6e-4 |

**Possession-level specifications** (n=26,647 possessions of ≥3 passes):
| spec | v1 published | Task 19d cross-fitted | this task cross-fitted |
|---|---|---|---|
| PH-O3(a) ends_in_shot, avg marg. effect | +0.0119, p=3.0e-4 | +0.0371, p=9.2e-39 | **+0.0572**, p=5.9e-109 |
| PH-O3(b) possession_xg (OLS coef) | −0.00059, p=0.236 (n.s.) | +0.0087, p=1.9e-31 | **+0.0178**, p=1.8e-64 |

Every one of the 10 team-match specifications and both possession-level
specifications now has a positive coefficient; 9 of the 10 team-match
specifications are significant at p<0.05 (xg H-O2 at p=0.069 is the one
exception), and both possession-level specifications are significant
at p<1e-30. Coefficient magnitudes are 1.5-3x larger than Task 19d's
cross-fitted values throughout.

## 4. Deviations from the brief
None from the hard rules. One disclosed methodology point: Step 4's
brief text says "offside: re-run Task 19c's calibration procedure
EXACTLY ... and report which rule it now selects," listed before
"policy model (retrain), softmax temperature (refit)." I read this
ordering as meaning the newly SELECTED rule (this task's R1_K10, not
Task 19c's R4) feeds into the policy restriction's offside component —
not that Task 19c's specific R4 parameters should be reused regardless
of what this task's own recalibration selects. This is the most literal
reading of "report which rule it now selects" as meaningful (a
recalibration that changes the selected rule but is not then acted on
would make that report inert), and is disclosed here rather than
assumed silently.

## 5. Problems and surprises
- Section 3's Step 1 numbers form an unusually clean dose-response
  curve: share beyond-line falls from 5.75% (0-3 visible opponents) to
  2.84% to 1.52% to 0.04% (10-11 visible opponents) — each bin roughly
  halving or better. This is exactly the signature a genuine visibility
  artifact should produce and is hard to explain as a coincidental
  byproduct of a different, unrelated defect.
- The offside recalibration selecting a DIFFERENT rule (R1_K10 instead
  of Task 19c's R4) — not just improved numbers for the same rule — is
  a reminder that "the same procedure, corrected inputs" does not
  guarantee "the same answer, just better": the selection criterion
  (`select_best`, maximize recall subject to FP<5% with a minimum
  gated population) is sensitive to exactly which candidate rules clear
  the bar, and which ones clear it changed here.
- `decision_execution_risk.py`'s cross-team defect (Task 24 Step 1(c))
  remains unfixed and unexercised, as directed — Execution is not part
  of any number in this results page.
- xg H-O2 (the specification adding completion/progressive/xa
  reference-rate controls) is the one team-match specification that
  does not clear p<0.05 (p=0.069). This is disclosed plainly rather
  than rounded into "significant" — it is the weakest link among the
  10 team-match coefficients, all of which point the same direction.

## 6. Questions for the research lead
1. This task's falsification battery and outcome-validation battery
   both pass cleanly, for the first time. Given Task 22's "no Task 22b"
   language and Task 23/24's escalating disclosure requirements, is
   this now the accepted engine for the SSAC27 abstract, and does the
   Task 23 holdout-gate requirement (`data/raw_holdout/`, H-O1 same sign
   and p<0.05) still need to be run before any player-level claim, or
   does this task's own result supersede that requirement?
2. `decision_execution_risk.py`'s defect (Step 1(c), Task 24) has now
   gone unfixed across three tasks (23, 24, 25) because Execution has
   not been in scope. If a future task needs Execution, should that fix
   be scheduled explicitly, or handled reactively when first needed?
3. Section 4 discloses a reading of Step 4's offside-rule ordering
   (recalibrated rule feeds the policy restriction, not Task 19c's
   R4 reused verbatim). Please confirm this reading is correct, since
   every downstream number (policy metrics, Decision, T6, crossfit,
   outcome validation) depends on it.

## 7. Files produced
- `src/engine_v2/task25_step1.py` — new. Step 1's visibility-vs-
  coordinate-error diagnostic.
- `src/engine_v2/value_models_v5_retrain.py` — new. Retrains M_for/
  M_against on `value_model_rows_v5.parquet` (Task 24's rows).
- `src/engine_v2/grid_v2.py` — new. Rebuilds the full candidate corpus
  on corrected geometry (monkeypatches `grid.py`'s output paths).
- `src/engine_v2/pass_success_v3.py` — new. Retrains the pass-success
  model on the corrected candidate features.
- `src/engine_v2/ev_recompute_v4.py` — new. Recomputes EV corpus-wide
  into `options_ev_v4/`.
- `src/engine_v2/offside_diagnostic_v3.py` — new. Re-runs Task 19c's
  exact offside calibration on the corrected corpus.
- `src/engine_v2/offside_v4.py` — new. Applies this task's newly
  selected offside rule (R1_K10) corpus-wide.
- `src/engine_v2/policy_baseline_fix_v5.py` — new. Refits the softmax
  temperature on `options_ev_v4` with the `offside_v4` restriction.
- `src/engine_v2/policy_score_v8.py` — new. Full-corpus policy re-score.
- `src/engine_v2/step8_regate.py` — new. Decision/Risk recompute, T6,
  separation check (Execution not computed).
- `src/engine_v2/falsification_v3.py` — new. Assembles T1-T6.
- `src/engine_v2/crossfit_v5.py` — new. 5-fold cross-fitting harness on
  the corrected geometry (Execution not computed).
- `src/engine_v2/outcome_validation_crossfit_v5.py` — new. Cross-fitted
  outcome-validation battery.
- New data artifacts under `data/processed/engine_v2/` (`options_parts_v2/`,
  `options_scored_v2/`, `options_ev_v4/`, `value_model_for_v5.json`,
  `value_model_against_v5.json`, `pass_success_model_v3.json`,
  `pass_policy_summary_v8.parquet`, `pass_der_v8.parquet`,
  `pass_der_crossfit_v5.parquet`, `offside_diagnostic_table_v3.parquet`)
  and new summary JSONs under `data/` — not committed, `data/` is never
  committed.
- `docs/results/25-engine-rebuild-v5.md` — this file.
- Commit hashes: `5b57c5a` (brief alone, Step 0), `40333e6` (this
  results page + all Step 1/2 code).

## 8. Confidence
High confidence in every number reported: each stage reuses an
already-validated pipeline function (`train_one`, `run_t2`,
`evaluate_rule`/`select_best`, `build_ev_oof_for_match`, the outcome-
validation builders) via direct import or monkeypatched path, with no
new modeling logic introduced anywhere in this task beyond the offside-
rule application (`offside_v4.py`, a direct parameter change to an
already-validated function shape). The full falsification and outcome-
validation batteries passing together, cleanly, for the first time in
ten prior attempts is a strong result, but Section 1 states plainly
what it would and would not prove: it validates that the coordinate fix
(Tasks 24-25) explains the great majority of every prior task's
anomalies, but it does not independently verify Step 1's own fixed
1%/20% visibility thresholds were the objectively correct cutoffs
(they were fixed by the brief before this task ran), and it says
nothing about the untouched holdout data or `decision_execution_risk.py`'s
still-unfixed defect. The weakest single number in the whole page is xg
H-O2's p=0.069 — reported as marginal, not rounded up to "significant."
