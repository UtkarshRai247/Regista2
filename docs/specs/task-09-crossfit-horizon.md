# Task 09 — Cross-fitting (v2-4) and horizon sensitivity (v2-6.2)

Governing document: docs/specs/analysis-plan-v2.md, Amendments v2-1 to
v2-6. Read all of them. This is the longest task so far; expect hours.

## Step 0 — Commit Amendment v2-6 alone. Record hash and new SHA-256.

## PART 1 — Cross-fitting (Amendment v2-4)
1. Build 5 match-level folds, stratified by competition-season, seed
   20260920, drawn independently of the discovery/confirmation split.
   Save data/splits/cv_folds.csv and COMMIT it before retraining.
2. For each fold, retrain pass-success, possession-value and behavior-
   policy models on the other four folds using exactly the frozen code,
   features and hyperparameters (commit 9db72ef). Only training data
   changes. Score the held-out fold: p_success, EV, policy_probability,
   Decision, Execution, realized value.
3. Report out-of-fold vs in-sample AUC and calibration for each model.
4. For the 7 CONFIRMED candidates, on the CONFIRMATION half, recompute
   with cross-fitted values: G + CI, P, L, Gate D (v2-2 criterion),
   PH-1, PH-2. Apply v2-4.3's rule and report which of the 3 ROBUST
   candidates remain ROBUST. The rule is fixed.
5. Secondary (v2-4.4): recompute S (Study B primary fit) and the Study C
   choice share as point estimates on cross-fitted values. No bootstrap.

## PART 2 — Horizon sensitivity (v2-6.2)
Retrain the possession-value model at horizons of 5 and 15 actions
(frozen code otherwise). Using NON-cross-fitted values for comparability
with Task 06/07, recompute for the 3 ROBUST candidates on the
confirmation half: G + CI, P, L, and PH-2, at each horizon. Report the
10-action numbers alongside. Apply v2-6.2's interpretation rule.

## HARD RULES
- Frozen code only. No feature changes, no hyperparameter changes, no
  new model types. Only training data and (Part 2) the horizon differ.
- If a retrain fails or a fold is degenerate, STOP and report.
- Report everything, including results that kill the finding.
- No interpretation for the paper. No memory writes. Don't edit
  docs/JOURNAL.md.
- If runtime looks likely to exceed 4 hours, STOP after Part 1 step 4
  and report — that step is the critical one.
- When finished, reply only that the task is done plus commit hashes.

## Output
docs/results/09-crossfit-horizon.md (template). Commit per rule 9.
