# Task 24 — Root cause: the direction "fix" flips half the teams. Correct it and rebuild.

Written 2026-09-27 by the research lead, after checking the data
directly. Nothing in this brief was chosen by looking at T4.

## What was found (reproduce it in Step 1)
StatsBomb event AND 360 freeze-frame coordinates are already
team-relative: every team attacks toward x = 120 in its own events.
Evidence, first 40 match files:
  - 156 of 156 team-periods have mean shot x > 60 (range ~100-111).
  - The opponent goalkeeper in shot freeze frames sits at median
    x = 117.4; 99.9% are beyond x = 100.
`geometry.team_period_directions` assumes the opposite (pitch-fixed
coordinates, teams attacking opposite ends). In each period it sorts the
two teams by mean shot x and assigns direction = -1 to the lower one. So
in almost every period ONE team's events are rotated 180 degrees, chosen
by whichever side happened to shoot from slightly further out (80 of 156
team-periods got +1, 76 got -1). About half of all events have been
valued with the attack pointing the wrong way.

This is consistent with everything that has looked wrong since engine
v2: 30,255 in-possession rows in the OWN third flagged "beyond the
defensive line" (geometrically near-impossible); own-third possessions
scoring ~4x more often than midfield ones; the top EV decile holding
31% own-third destinations; T2's backwards sign; the offside rule's
23.7% false-positive rate; and "beyond the line" looking bad everywhere.
The same function was ported from engine v1's `pitch_direction`, and
`src/tempo/redesign_metrics.py` also uses it.

## Disclosure
Written after scenario_c failed (Tasks 19d, 21, 22, 23). The fix is
justified by the coordinate evidence above, which does not involve T4.
All history is disclosed in the results page and any paper.

## Step 0 — Commit this brief alone. Record the hash.

## Step 1 — Evidence and audit, before changing code
(a) Commit a script reproducing the evidence above on ALL 299 matches:
    share of team-periods with mean shot x > 60; opponent-keeper x in
    shot frames; current direction assignment counts.
(b) List every place in `src/engine_v2/` where an attack direction is
    INFERRED or APPLIED (`team_period_directions`, `normalize_xy`,
    `normalize_xy_arr`, any `direction` argument). Classify each as:
    INFERRED (comes from team_period_directions — to be fixed), or
    PERSPECTIVE FLIP (deliberately rotates into the OTHER team's view,
    e.g. the EV turnover branch's `direction=-1` — CORRECT, keep).
(c) List every place that compares or combines locations from events
    by DIFFERENT teams (e.g. value model `prev_x/prev_y`, which takes
    the previous event of any team). Under team-relative coordinates, a
    location from the other team's event must be rotated 180 degrees
    (x -> 120 - x, y -> 80 - y) before use.
    Also list (do not change) uses in `src/decision_engine/` and
    `src/tempo/`.
Write this section of the results page before changing any code.

## Step 2 — The fix
- `team_period_directions` returns +1 for every (team, period), with a
  docstring stating why and pointing to Step 1's evidence script.
- Every cross-team location found in Step 1(c) inside `src/engine_v2/`
  is rotated into the acting team's frame.
- PERSPECTIVE FLIPS are left exactly as they are.
- Keep Task 22's fixes A (in-possession rows only) and B (label counts
  its own event), and Task 21's features stay out of STATE_FEATURES.
Print a worked example: one real event from a previously flipped
team-period, showing ball_x, defensive_line_x and
ball_beyond_defensive_line before and after.

## Step 3 — Geometry checkpoint (checks the coordinates, not the engine)
From rebuilt value-model rows (in-possession, Task 22 labels):
  G1. Share of rows in band 0-40 with ball beyond the defensive line:
      must be under 1% (currently 14.8%).
  G2. P(score in 10) by band must satisfy 0-40 < 80-100 < 100-120.
  G3 (report only). The ORIGINAL simple offside rule (second-rearmost
      visible opponent, no restrictions) on real completed passes:
      false-positive rate and recall, vs Task 19c's 23.69% / 46.58%.
  G4 (report only). Task 22's premise table and Task 23's central
      channel table, recomputed.
If G1 or G2 fails, the coordinates are still wrong somewhere: stop,
report, and list what you checked. Do not build models on them.

## Step 4 — Rebuild the engine on corrected coordinates
Same features, same hyperparameters, same seeds, new `_vN` paths:
pass-success model (retrain), M_for and M_against (retrain), EV corpus
(recompute all ~106M rows), offside: re-run Task 19c's calibration
procedure EXACTLY (same candidate rules, same 5% false-positive bar,
same selection criterion) and report which rule it now selects; policy
model (retrain), softmax temperature (refit); Decision and Risk.
Keep the policy restriction thresholds unchanged (disclose that they
were set on the old coordinates). Execution: not computed.

## Step 5 — Falsification battery, definitions unchanged
T1, T2 (magnitude verdict AND sign), T3, T4 (a, b, c), T5, T6, plus the
separation check. For T4 report the p90 from BOTH Task 23's seeded
sample and the committed test's sampling, both on THIS task's corpus.
Columns: Task 15, 19d, this task.

## Step 6 — Cross-fitted outcome validation
Run it whatever Step 5 shows. Per-fold models trained on the corrected
rows; this task's temperature and offside rule. Specifications
unchanged. Columns: engine v1 published, Task 19d, this task.

## HARD RULES
- Changes allowed: Step 2 only. No new features, hyperparameters,
  thresholds or test definitions.
- Do not touch `data/raw_holdout/`.
- Single machine. Memory gate: proceed at >= 40% free and >= 3 GB
  available; one match in memory at a time.
- No leaderboards, no player identity, no interpretation.
- No memory writes. Don't edit docs/JOURNAL.md.
- When finished, reply only that the task is done plus commit hashes.

## Output
docs/results/24-direction-fix.md (template). Commit per rule 9.
