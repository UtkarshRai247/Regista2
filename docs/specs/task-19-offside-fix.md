# Task 19 — Fix the offside heuristic, then re-run

Governing documents: docs/specs/engine-v2-rebuild.md section 1,
docs/results/18-policy-and-crossfit.md Section 5.
Last engine fix. Bounded: one calibration against ground truth, then
re-run what the change affects. No other engine change.

## Step 0 — Commit this brief. Record hash.

## Step 1 — Quantify the defect against ground truth
StatsBomb labels genuinely offside passes: pass outcome "Pass Offside".
Build the labelled set from the 299 matches and report its size.
For the CURRENT heuristic report, on real chosen destinations:
  - false-positive rate: share of COMPLETED passes flagged offside
    (expected ~43.6%);
  - recall: share of truly-offside passes flagged;
  - both broken down by number of visible opponents in the frame and by
    whether the destination is in the attacking half.
This tells us whether partial visibility is the cause, as suspected.

## Step 2 — Calibrate, once, on ground truth only
Candidate rules, all variants of "destination beyond the second-rearmost
visible opponent and beyond the ball":
  R0 current rule (baseline for comparison);
  R1 R0 plus: apply only when at least K visible opponents are in the
     frame, for K in {6, 8, 10, 12};
  R2 R0 plus: apply only when the destination is in the attacking half;
  R3 R1 and R2 combined, at the best K from R1;
  R4 R3 plus a tolerance margin of M yards beyond the second-rearmost
     visible opponent, for M in {0, 1, 2, 3}.
SELECTION RULE, fixed now: choose the rule that MAXIMISES recall on
truly-offside passes subject to a false-positive rate on completed
passes below 5%. If no rule meets that constraint, choose the rule with
the lowest false-positive rate and report that offside cannot be
detected reliably from freeze frames; in that case the engine stops
excluding offside destinations altogether and that becomes a stated
limitation.
Judged on the StatsBomb labels alone. No Decision value, no coefficient,
no player may be consulted.

## Step 3 — Re-run what the change affects
Rebuild the candidate legality flags corpus-wide with the chosen rule.
Report the new chosen-destination coverage under the restricted policy
(the 54.5% figure should rise).
Recompute the policy baseline (restriction + the SAME temperature
procedure, refit), Decision, Risk, Execution.
Re-run T6 reliability, thresholds 100-500, and the separation check.
Report old versus new for every quantity.
If Decision reliability at 200 drops below 0.60, STOP and report.

## Step 4 — Re-run outcome validation, cross-fitted
Re-run the full battery on cross-fitted Decision using the existing
5-fold harness, specifications unchanged. Report three columns side by
side: engine v1 published, Task 18 cross-fitted, and this task's
cross-fitted figures.

## HARD RULES
- One calibration, judged on StatsBomb offside labels only.
- No other engine change. Do not touch the value models, the
  pass-success model, the feature set or the grid.
- Report old versus new everywhere, including any regression.
- No leaderboards, no player identity.
- No memory writes. Don't edit docs/JOURNAL.md. No interpretation.
- When finished, reply only that the task is done plus commit hashes.

## Output
docs/results/19-offside-fix.md (template). Commit per rule 9.
