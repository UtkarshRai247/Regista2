# Task 18 — Sharpen the policy baseline, then re-validate without circularity

Governing documents: docs/specs/engine-v2-rebuild.md,
docs/results/17-engine-v2-validation.md. Two defects in the VALIDATION,
not the engine. Both are bounded and use machinery that already exists.

## Step 0 — Commit this brief. Record hash.

## Step 1 — The policy baseline is not behavioural (Task 17 Step 2)
Median effective options 420.6 of ~423 candidates; policy-weighted and
unweighted mean EV correlate 0.9986. The policy is nearly uniform, so
Decision currently means "better than the average reachable cell", not
"better than what players typically choose". Fix the policy, not
Decision.

Two changes, both judged ONLY on held-out policy accuracy — an external
criterion that has nothing to do with any Decision value or outcome:
  (a) RESTRICTED CANDIDATE SET for the policy baseline: drop candidates
      with p_success < 0.05, offside destinations (already flagged), and
      destinations beyond 45 yards. Report the resulting candidate count
      per pass.
  (b) TEMPERATURE CALIBRATION: fit a single softmax temperature on the
      training matches by maximising held-out log-likelihood of the
      actual chosen destination. Report the fitted temperature.
Report, on held-out matches, before and after: top-1 accuracy, top-3
accuracy, median effective options, top-10 and top-50 probability mass,
and the correlation between policy-weighted and unweighted mean EV.
PRE-SPECIFIED READING: the baseline counts as behavioural if median
effective options falls below 100 AND the weighted/unweighted
correlation falls below 0.95. If it does not, report that plainly and
carry the limitation forward — do not iterate further, and do not tune
anything on a Decision or outcome number.

## Step 2 — Recompute and re-gate
Recompute Decision (and Execution, Risk) with the calibrated policy.
Re-run T6: 100-split reliability, thresholds 100-500. Re-run the
separation correlations with completion rate, progressive passes, xA,
move_on_speed, hold_variation.
Report old and new side by side. If reliability at 200 falls below 0.60,
STOP and report.

## Step 3 — The circularity problem in outcome validation
Task 17's possession-level result (p = 4.8e-111) is partly mechanical:
EV is built from a value model trained to predict scoring within 10
actions on THESE events, then tested against whether the possession ends
in a shot. The model is being asked to predict what it was fitted on.
Fix with the cross-fitting harness built in Task 09 (Amendment v2-4):
  - 5 match-level folds, seed 20260920, the same fold file if it still
    applies to the v2 sample; otherwise rebuild it the same way.
  - Retrain the two value models and the pass-success model per fold on
    the other four, score each held-out fold, recompute EV and Decision
    from out-of-fold values only.
  - Re-run the FULL outcome battery on cross-fitted Decision, with the
    specifications unchanged, and report beside the Task 17 in-sample
    figures.
Report out-of-fold versus in-sample AUC for each model, as Task 09 did.
This is the honest version of the test. If the coefficients survive
cross-fitting, the validation is real; if they collapse, Task 17's
result was the value model predicting itself, and that is reported as
the finding.

## Step 4 — Time box and order
Steps 1 and 2 first; they are cheap. Step 3 is the expensive one. If
Step 3 cannot finish, report Steps 1 and 2 with Task 17's in-sample
outcome numbers clearly labelled AS in-sample and circular-risk, and
say Step 3 is outstanding. Do not skip it silently.

## HARD RULES
- Nothing in this task may be tuned on a Decision value, a coefficient,
  or any outcome. Step 1's changes are judged on policy accuracy alone.
- No leaderboards, no player identity.
- Report old-versus-new for every quantity, including regressions.
- No memory writes. Don't edit docs/JOURNAL.md. No interpretation.
- When finished, reply only that the task is done plus commit hashes.

## Output
docs/results/18-policy-and-crossfit.md (template). Commit per rule 9.
