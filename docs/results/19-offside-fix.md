# Task 19: Fix the offside heuristic, then re-run
Date: 2026-09-25
Status: COMPLETE

## Section checklist
- Step 0 (commit brief): COMPLETE
- Step 1 (quantify the defect against StatsBomb ground truth): COMPLETE
- Step 2 (calibrate, once, on ground truth only): COMPLETE — verdict: no candidate rule reliably detects offside at FP<5%; offside filtering is DROPPED ENTIRELY
- Step 3 (re-run what the change affects: coverage, policy baseline, Decision/Risk/Execution, T6, separation): COMPLETE — T6 PASS (0.623 at 200, above 0.60)
- Step 4 (re-run outcome validation, cross-fitted, three-way comparison): COMPLETE

Overall: COMPLETE. No leaderboards, no player identity anywhere. One calibration, judged on StatsBomb's own "Pass Offside" labels alone — no Decision value, coefficient, or player was consulted in Step 2's rule selection.

## 1. Headline
The current offside heuristic (R0) has a 43.1% false-positive rate on real completed passes (confirming Task 18's estimate) and only 50.5% recall on the 790 genuinely offside passes in the eligible population — and no calibrated variant tested (gated by minimum visible-opponent count, attacking-half-only, or a tolerance margin, all fixed candidate families from the brief) gets the false-positive rate below 10.7% while detecting any meaningful share of true offsides; every rule that clears the 5% false-positive bar does so only by never firing at all (a K=12 gate is a structurally impossible threshold — a team fields at most 11 players). **No rule meets the pre-specified constraint. Per the brief's own contingency, offside filtering is dropped entirely** — engine v2 no longer excludes any destination as offside. Restricted-policy coverage of real chosen destinations rose from 54.5% (Task 18) to 96.3%. Decision's reliability at 200 passes fell further, from 0.780 (Task 17) to 0.704 (Task 18) to **0.623 (Task 19)** — still above the 0.60 gate, but the margin is now thin. The cross-fitted outcome-validation battery remains positive and significant almost everywhere, with most coefficients larger than Task 18's (offside-restricted) cross-fitted figures and closer to Task 17's original in-sample magnitudes.

## 2. What I did
- Read `docs/specs/task-19-offside-fix.md` and committed it alone (`8641c5e`).
- Step 1 (`src/engine_v2/offside_diagnostic.py`): built a ground-truth diagnostic table from StatsBomb's `pass_outcome == "Pass Offside"` label across all 299 raw match files, joined to engine v2's existing eligible-pass population; reported false-positive rate and recall for the current rule, broken down by visible-opponent count and by attacking half.
- Step 2 (same script): evaluated R0-R4 (11 total configurations: R0; R1 at K∈{6,8,10,12}; R2; R3 at the best R1 K; R4 at that K for M∈{0,1,2,3}) against ground truth only, applied the fixed selection rule, and reported the verdict.
- Step 3 (`src/engine_v2/policy_baseline_fix_v2.py`, `policy_score_v4.py`, `step4_regate.py`): rebuilt the restriction filter without the offside term, refit the temperature (same procedure as Task 18), recomputed Decision/Risk corpus-wide (Execution unaffected, reused), re-ran T6 and the separation check, reported old (Task 17/18) vs new.
- Step 4 (`src/engine_v2/crossfit_v2.py`, `outcome_validation_crossfit_v2.py`): re-ran Task 09's 5-fold cross-fitting harness with the offside-free restriction and Task 19's own fitted temperature, then reran the full outcome-validation battery on the resulting cross-fitted Decision.
- No file under `src/decision_engine/` or any prior Task 15/17/18 `src/engine_v2/` file was modified — confirmed via `git diff --stat` at the end. The value models, pass-success model, feature set, and grid were never touched; only the offside flag's role in the RESTRICTION FILTER was changed (to "always false" / not applied).
- Reproduce with (from repo root, `.venv` active, run in order from `src/engine_v2/`):
  `python offside_diagnostic.py && python policy_baseline_fix_v2.py && python policy_score_v4.py && python step4_regate.py && python crossfit_v2.py && python outcome_validation_crossfit_v2.py`
- Total wall clock: ~41 minutes.

## 3. Numbers

### Step 1 — ground truth and current-rule (R0) diagnostic
- Genuinely offside passes (`pass_outcome == "Pass Offside"`) across all 299 matches: **998**. Of these, **790** fall within engine v2's eligible population (208 excluded — e.g. offside free kicks, which `EXCLUDED_PASS_TYPES` already excludes from the eligible pass set for unrelated reasons).
- R0 on the eligible population (n=214,513 completed passes; 790 truly-offside passes):
  - **False-positive rate: 43.11%** (consistent with Task 18's ~43.6% estimate, computed slightly differently — restricted to completed passes only here, per this task's exact definition).
  - **Recall: 50.51%.**
- By number of visible opponents (false-positive rate barely varies; recall drifts down slightly as more opponents are visible):

| opponents visible | n completed | FP rate | n truly offside | recall |
|---|---|---|---|---|
| 0-6 | 20,169 | 36.96% | 24 | 58.33% |
| 6-8 | 39,916 | 42.85% | 126 | 52.38% |
| 8-10 | 65,296 | 44.16% | 298 | 52.35% |
| 10-12 | 89,129 | 43.86% | 342 | 47.66% |
| 12+ | 3 | 33.33% | 0 | — |

- By attacking half — **this is the whole story**:

| location | n completed | FP rate | n truly offside | recall |
|---|---|---|---|---|
| own half | 106,856 | 32.08% | 388 | **0.77%** |
| attacking half | 107,657 | 54.07% | 402 | **98.51%** |

Nearly all real recall comes from the attacking half (98.5%); the current rule essentially never correctly identifies offside in a team's own half (0.77%, as it should be — offside cannot occur there under the Laws of the Game) but still generates a 32.08% false-positive rate there, purely from geometric noise.

### Step 2 — calibration against ground truth only

| rule | K | M | attacking-half-only | FP rate | recall |
|---|---|---|---|---|---|
| R0 (current) | — | — | no | 43.11% | 50.51% |
| R1_K6 | 6 | — | no | 39.64% | 48.73% |
| R1_K8 | 8 | — | no | 31.67% | 40.38% |
| R1_K10 | 10 | — | no | 18.22% | 20.63% |
| R1_K12 | 12 | — | no | ~0.0005%* | 0%* |
| R2 | — | — | yes | 27.13% | 50.13% |
| R3 (K=10 + attacking half) | 10 | 0 | yes | 11.57% | 20.38% |
| R4_M0 | 10 | 0 | yes | 11.57% | 20.38% |
| R4_M1 | 10 | 1 | yes | 11.32% | 20.38% |
| R4_M2 | 10 | 2 | yes | 11.04% | 20.38% |
| R4_M3 | 10 | 3 | yes | **10.74%** | 20.38% |

*R1_K12 requires >=12 visible opponents, which occurs in only 3 of 250,850 rows (a team fields at most 11 players) — a structurally impossible operating point, not a real rule. It (and R3/R4 built on "best K from R1" before this check) are excluded from selection as degenerate (gated population < 100), per a disclosed refinement of the selection procedure (Section 4). The genuine best K from R1 is **10**.

**SELECTION: no rule (excluding the degenerate K=12 branch) achieves the required false-positive rate below 5%.** The best functioning candidate, R4 at K=10, M=3, still has an 11.57%→10.74% false-positive rate — more than double the ceiling — while recall collapses to ~20%. **Per the brief's contingency: offside cannot be detected reliably from freeze frames at an acceptable false-positive cost, and the engine STOPS excluding offside destinations altogether.**

### Step 3 — re-run: coverage, policy baseline, Decision/Risk, T6, separation

**Restricted-policy coverage** (held-out test matches, same 233/59 split as Task 18): **54.5% → 96.3%.**

**Policy baseline metrics**, offside-included (Task 18) vs offside-free (Task 19):

| metric (held-out test) | Task 18 (restricted incl. offside) | Task 19 (restricted, no offside) |
|---|---|---|
| coverage | 54.5% | **96.3%** |
| restricted candidates/pass (mean/median) | 152.5 / 155 | 287.5 / 288 |
| fitted temperature | 0.1579 | 0.1556 |
| top-1 accuracy (covered) | 10.24% | 6.93% |
| top-3 accuracy (covered) | 26.69% | 19.31% |
| median effective options | 56.3 | **95.1** |
| corr(policy-weighted, unweighted mean EV) | 0.855 | 0.863 |

**Pre-specified reading (Task 18's, reapplied): BEHAVIORAL** (95.1 < 100, 0.863 < 0.95) — but median effective options is now within 5 units of the 100 threshold, and top-1/top-3 accuracy dropped as the candidate pool nearly doubled. This is a real trade-off, not a pure improvement: coverage rose sharply but the policy itself is somewhat less sharp on a larger, less-filtered candidate set.

**Reliability of Decision** (100-split, Spearman-Brown), Task 17 (original) vs Task 18 (offside-restricted) vs Task 19 (offside dropped):

| threshold | n_units | Task 17 | Task 18 | Task 19 |
|---|---|---|---|---|
| 100 | 607 | 0.685 | 0.614 | 0.541 |
| 150 | 364 | 0.764 | 0.705 | 0.620 |
| **200** | **252** | **0.780** | **0.704** | **0.623** |
| 250 | 166 | 0.845 | 0.784 | 0.698 |
| 300 | 117 | 0.884 | 0.828 | 0.725 |
| 400 | 77 | 0.922 | 0.872 | 0.813 |
| 500 | 54 | 0.936 | 0.888 | 0.837 |

**T6 (Task 19): Decision reliability @200 = 0.623. Pass condition (>=0.60): PASS**, but with a narrowing margin across all three tasks (0.780 → 0.704 → 0.623).

**Separation check** (n=252 qualifying units), old vs new:

| metric | Task 17 | Task 18 | Task 19 |
|---|---|---|---|
| completion_pct | −0.299 | −0.178 | −0.066 |
| progressive_passes_per_90 | −0.420 | −0.300 | −0.212 |
| xa_per_90 | +0.547 | +0.530 | +0.463 |
| move_on_speed (tempo) | −0.097 | −0.255 | −0.177 |
| hold_variation (tempo) | −0.107 | −0.220 | −0.149 |

Every correlation weakened in magnitude from Task 18 to Task 19 while keeping its sign; xA/90 remains the strongest, most stable relationship across all three versions of Decision.

### Step 4 — cross-fitted outcome validation, three-way comparison

Out-of-fold AUC (unchanged from Task 18, as expected — the pass-success and value models were never touched by this task): pass_success 0.9043, M_for 0.8240, M_against 0.8789. Policy OOF top-1/top-3: 7.21%/19.41% (down from Task 18's 10.41%/26.72%, mirroring Step 3's held-out finding — the larger, offside-free candidate set is evaluated as a whole, harder per-pass but far more complete).

**Outcome = xG:**

| Spec | v1 published | Task 18 cross-fitted | Task 19 cross-fitted |
|---|---|---|---|
| H-O1 | −0.1381 [−0.210,−0.066] p=1.8e-4 | +0.1684 [0.094,0.243] p=9.9e-6 | **+0.2321** [0.150,0.315] p=3.4e-8 |
| H-O2 | −0.1241 [−0.193,−0.056] p=3.9e-4 | +0.0453 [−0.032,0.123] p=0.251 (n.s.) | **+0.0933** [−0.014,0.201] p=0.088 (n.s.) |
| PH-O1 | −0.1532 [−0.229,−0.077] p=7.0e-5 | +0.1744 [0.098,0.251] p=7.0e-6 | **+0.2293** [0.146,0.312] p=5.9e-8 |
| PH-O2 | −0.1759 [−0.275,−0.077] p=5.2e-4 | +0.1721 [0.067,0.277] p=1.3e-3 | **+0.2221** [0.107,0.337] p=1.6e-4 |
| PH-O4 | +0.0271 [−0.058,0.112] p=0.532 | +0.2208 [0.144,0.298] p=2.1e-8 | **+0.3620** [0.283,0.441] p=1.9e-19 |

**Outcome = goals:**

| Spec | v1 published | Task 18 cross-fitted | Task 19 cross-fitted |
|---|---|---|---|
| H-O1 | −0.4031 [−0.512,−0.294] p<1e-12 | +0.2182 [0.089,0.347] p=9.2e-4 | **+0.2568** [0.117,0.397] p=3.2e-4 |
| H-O2 | −0.4587 [−0.576,−0.341] p<1e-13 | +0.1477 [0.018,0.277] p=0.026 | **+0.1854** [0.041,0.330] p=0.012 |
| PH-O1 | −0.4101 [−0.522,−0.298] p<1e-15 | +0.2123 [0.083,0.341] p=1.3e-3 | **+0.2587** [0.120,0.397] p=2.5e-4 |
| PH-O2 | −0.4229 [−0.581,−0.265] p<1e-6 | +0.2755 [0.120,0.431] p=5.1e-4 | **+0.3109** [0.137,0.485] p=4.7e-4 |
| PH-O4 | −0.2088 [−0.309,−0.109] p<1e-4 | +0.2698 [0.141,0.398] p=4.0e-5 | **+0.3832** [0.252,0.514] p=1.0e-8 |

**Possession level** (n=26,647, same as Task 17's original — the offside fix restored full Decision coverage, so no possessions are excluded for missing Decision anymore):

| Outcome | v1 published | Task 18 cross-fitted | Task 19 cross-fitted |
|---|---|---|---|
| (a) ends_in_shot (avg. marg. effect) | +0.0119 [0.0055,0.0184] p=3.0e-4 | +0.0374 [0.032,0.043] p=7.7e-47 | **+0.0439** [0.038,0.049] p=1.0e-56 |
| (b) possession_xg (OLS) | −0.00059 [−0.00157,0.00039] p=0.236 (n.s.) | +0.0091 [0.008,0.010] p=4.4e-37 | **+0.0099** [0.008,0.011] p=2.2e-37 |

**Every Task 19 cross-fitted coefficient keeps the sign of Task 18's, and every one is at least as large in magnitude** (PH-O3(a) +18% larger, PH-O3(b) +9% larger, xG H-O1 +38% larger, goals PH-O4 +42% larger) — the offside fix, despite lowering Decision's reliability, moved the outcome-validation effect sizes CLOSER to Task 17's original in-sample magnitudes, not further away. The one persistently non-significant spec (xG, H-O2, the richest control set) remains non-significant (p=0.088, versus Task 18's p=0.251 — closer to significance but still short of it).

## 4. Deviations from the brief
None from `task-19-offside-fix.md`'s Steps 0-4 or hard rules. One disclosed refinement to the selection procedure:
- **Step 2's selection rule excludes candidates whose K-gate applies to fewer than 100 rows** (`n_opponents_visible >= K` satisfied by under 100 of 250,850 eligible passes). Without this, K=12 — which only 3 rows in the entire corpus ever satisfy, since a team fields at most 11 players — trivially achieves FP≈0%/recall=0% by never firing, and the brief's own selection rule ("maximizes recall subject to FP<5%") would mechanically select it as if it were a real, functioning detector. This is the plainly intended reading of "meets that constraint" (a rule that actually operates on the population), not a new criterion invented to reach a preferred answer — and it does not change the ultimate outcome, since the corrected fallback (R4 at K=10, M=3, FP=10.74%) still fails the 5% ceiling by more than double, so offside filtering is dropped entirely either way. This is disclosed here in case the research lead wants to review the raw, unfiltered candidate table (`data/processed/engine_v2/offside_diagnostic_table.parquet`) directly.

## 5. Problems and surprises
- **No calibrated rule variant in the brief's own candidate families gets anywhere close to the 5% false-positive ceiling** once the degenerate K=12 branch is set aside — the best functioning rule (R4, K=10, M=3) still has FP=10.74%, more than double the bar, while catching only ~20% of true offsides (down from R0's 50.5%). The attacking-half restriction alone (R2) is the single most effective lever tested (FP 43.11%→27.13% with almost no recall loss, 50.51%→50.13%) but was never going to clear 5% on its own; combining it with opponent-count gating trades away most of the recall it preserved. This suggests StatsBomb's freeze-frame visibility (partial camera coverage, no player identity, no offside-line marking) may not carry enough geometric signal to detect offside reliably at all, at least via this family of heuristics — consistent with the brief's own anticipated fallback.
- **Dropping offside filtering did not simply "fix" the policy — it traded one problem for a smaller one.** Coverage rose dramatically (54.5%→96.3%), but median effective options (95.1) sits right at the edge of the 100-threshold "behavioral" cutoff, and Decision's reliability at 200 fell further (0.704→0.623), continuing a monotonic decline across Tasks 17→18→19. The gate still passes, but a fourth consecutive real-data change of similar magnitude would put T6 at meaningful risk of failing.
- **The outcome-validation coefficients got LARGER, not smaller, after dropping offside filtering** — a genuine, if modest, surprise, since restoring the offside-affected ~45% of candidates could plausibly have gone either way (diluting the signal with noisier candidates, or, as happened, sharpening it by removing a mechanically-biased FP-heavy subset of the option space from the policy baseline). This is reported as observed; no explanation is asserted, per the hard rule against interpretation.
- 208 of the 998 ground-truth "Pass Offside" passes (20.8%) fall outside engine v2's eligible population entirely (mostly excluded pass types, e.g. free kicks) — these can never contribute to recall as measured in this task, since engine v2 has no `offside_destination` flag (or now, no flag at all) for a pass it never generates candidates for in the first place. Not a defect of this task's measurement, just a boundary of what "recall on the eligible population" can mean.

## 6. Questions for the research lead
1. Given no tested rule family gets close to an acceptable false-positive rate (Section 5), is offside-aware option-space construction worth revisiting with a fundamentally different approach (e.g. using the full visible-area polygon rather than just visible-player counts, or accepting a coarser "likely offside" probability rather than a hard flag) in a future task, or is "engine v2 does not model offside" an acceptable permanent limitation for this paper?
2. T6's reliability has now fallen in a straight line across three tasks (0.780→0.704→0.623) as the option space and policy construction have been refined. Is this trend itself worth a dedicated diagnostic, given the gate could plausibly fail under a future, similarly-scoped correction?
3. Section 3's finding that dropping offside filtering INCREASED outcome-validation effect sizes, despite lowering Decision's own reliability, is counter to a naive expectation that a more reliable metric would show a cleaner outcome relationship. Is this worth flagging for the paper as its own finding, or treated purely as incidental to the calibration work in this task?

## 7. Files produced
- `src/engine_v2/offside_diagnostic.py` — Steps 1-2. Committed, commit `9974140`.
- `src/engine_v2/policy_baseline_fix_v2.py`, `policy_score_v4.py`, `step4_regate.py` — Step 3. Committed, commit `9974140`.
- `src/engine_v2/crossfit_v2.py`, `outcome_validation_crossfit_v2.py` — Step 4. Committed, commit `9974140`.
- `data/engine_v2_step1_offside_diagnostic.json`, `engine_v2_step2_offside_calibration.json`, `engine_v2_step3_policy_baseline_fix_v2.json`, `engine_v2_step3_recompute.json`, `engine_v2_step3_regate.json`, `engine_v2_step4_crossfit.json`, `engine_v2_step4_outcome_validation_crossfit.json` — step summaries (all numbers in Section 3 come from these). Not committed (data/).
- `data/processed/engine_v2/offside_diagnostic_table.parquet`, `pass_policy_summary_v4.parquet`, `pass_der_v4.parquet`, `pass_der_crossfit_v2.parquet` — intermediate/final per-pass tables for this task's re-run. Not committed (data/).
- `docs/specs/task-19-offside-fix.md` — the executed task spec, committed alone, commit `8641c5e`.
- `docs/results/19-offside-fix.md` — this page. Committed, commit `9974140`.

## 8. Confidence
High for Step 1/2 (deterministic ground-truth comparison, the degenerate-K refinement is disclosed and verified not to change the ultimate outcome, the attacking-half/own-half split is a clean and unambiguous confirmation of the diagnosed cause). High for Step 3's mechanical execution (coverage rose exactly as predicted; T6 still clears its gate). Moderate for what this means going forward: T6's margin over the 0.60 gate is now much thinner than in Task 17 (0.780→0.623), and median effective options (95.1) is close enough to the 100 "behavioral" cutoff that a small change in a future task could flip the diffuseness verdict. The outcome-validation battery's continued positive, mostly-significant result across three independent robustness checks (Task 18's restriction fix, this task's offside fix, both under cross-fitting) is the strongest evidence yet that engine v2's reversal of engine v1's finding is not an artifact of any single construction choice — but the reliability trend (Section 5, question 2) is a real, unresolved risk for whatever comes after this "last engine fix."
