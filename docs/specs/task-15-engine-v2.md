# Task 15 — Build engine v2, Part 1: option space, features, models

Governing documents: docs/ENGINE_AUDIT.md and
docs/specs/engine-v2-rebuild.md. Read both fully before writing code.

This task BUILDS and TESTS the instrument. It computes no player
metrics, no leaderboards and no studies. Those come only after the
falsification battery passes.

## Step 0 — Commit the audit and the rebuild spec together. Record the
hash and each file's SHA-256. Append to docs/DECISIONS.md:

## D-015 — Engine v1 superseded
Date: 2026-09-25
Decision: The engine built in Task 01 is superseded. All option-level
and player-level results under plans v2 and v3 are withdrawn as
measurements, per docs/ENGINE_AUDIT.md (five defects). Results pages
remain as the historical record and are not edited.
Reason: EV was algebraically a risk score; the value model could not see
defenders; Execution was a completion residual; the scored destination
was often not the pass played; several feature and option-space defects.
Alternatives rejected: patching the identification bug alone.
Reversible? No.

## Step 1 — New module, do not edit v1 files
Write to src/engine_v2/. Leave src/decision_engine/ untouched so the
superseded results stay reproducible.

## Step 2 — Option space (spec section 1)
Build destinations per pass: 4-yard grid within 60 yards of the passer,
inside the pitch, plus each visible teammate's exact position. Chosen =
the cell containing pass_end_location. Flag offside destinations per the
spec and exclude them from best-option and policy sets, reporting counts.
Report: options per pass (mean, median, p90), passes retained (should be
essentially all eligible passes — report the number and compare with
v1's 171,618), and the T1 displacement statistic.

## Step 3 — Features (spec section 2)
Implement the full shared feature set, direction-normalised, in
StatsBomb units with _u naming. Unit-test the lane-congestion
calculation against three hand-built cases and commit those tests.

## Step 4 — Pass-success model
Same algorithm family as v1 (gradient boosting), trained on chosen
destinations only, held out by MATCH. Report AUC, calibration overall,
and T5's calibration by length bucket. Report T7's support statistics.

## Step 5 — Value models (spec section 3)
Train BOTH P(team scores in 10) and P(opponent scores in 10) on the
299-match sample's full event stream with the freeze-frame feature set.
Report held-out AUC and calibration for each. Run T2 and report it.

## Step 6 — EV and the policy (spec sections 4, 5)
Compute V_net, EV for every option, then train the behavior policy on
the new features and softmax within each pass's legal option set.
Report policy top-1 and top-3 accuracy. Run T3 and report it.

## Step 7 — The falsification battery (spec section 6)
Run T1 through T5 and T7 and report each with its pass condition and
verdict. Write T4's synthetic scenarios as committed unit tests.
STOP after this step. Do not compute Decision per player, do not build
leaderboards, do not run any study, whatever the verdicts are.

## HARD RULES
- If T2 or T3 fails, STOP and report. Do not tune features to make them
  pass; report the failure and wait for the research lead.
- Never use the named-player ranks, or any player identity, as a check
  on the engine. Player identity must not enter this task at all.
- Report every test verdict, including failures, in Section 3.
- No memory writes. Don't edit docs/JOURNAL.md.
- When finished, reply only that the task is done plus commit hashes.

## Output
docs/results/15-engine-v2-build.md (template). Commit per rule 9.
