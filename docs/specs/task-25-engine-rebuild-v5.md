# Task 25 — Explain G1's residual, then rebuild the engine (Task 24 Steps 4-6)

Written 2026-09-27 by the research lead after reading
docs/results/24-direction-fix.md.

## Context
Task 24's direction fix is confirmed on all 299 matches and moved G1
from 14.8% to 2.30%; G2 passes; the premise table now shows
beyond-the-line scoring MORE than not-beyond in every band. The G1 bar
(1%) was set by the research lead without allowing for partial
visibility in 360 frames. Task 24 reports the residual rows are spread
over 286 of 299 matches and have median 13 visible players vs 17 overall
— the signature of the known visibility limitation (handoff section 5,
item 5), not of a remaining direction flip. That is checked, not
assumed, in Step 1 below, with the criterion fixed now.

## Step 0 — Commit this brief alone. Record the hash.

## Step 1 — Is the residual visibility, or a remaining coordinate error?
From `value_model_rows_diagnostic_v5.parquet`, in-possession rows,
band 0-40:
  (a) G1 share (beyond the line) by number of VISIBLE OPPONENTS in the
      frame: bins 0-3, 4-6, 7-9, 10-11. Report n and share per bin.
  (b) G1 share restricted to frames with >= 10 visible opponents
      (the same K the project's offside rule R4 already uses).
  (c) For the residual beyond-line rows: median defensive_line_x, and
      the share of them in which fewer than 10 opponents are visible.
  (d) Per team-period, the share of its band-0-40 rows that are
      beyond-line; report the 10 highest team-periods. A leftover
      direction flip would show whole team-periods near 50%+.
DECISION, fixed now: the residual is attributed to visibility, and the
task continues to Step 2, if (b) is under 1% AND no team-period in (d)
exceeds 20% on at least 50 rows. Otherwise stop after Step 1 and report.
No code changes in this step.

## Step 2 — Rebuild the engine: run Task 24's Steps 4, 5 and 6 exactly
as written in docs/specs/task-24-direction-fix.md, on Task 24's corrected
coordinates and rows (`value_model_rows_v5.parquet`), under all of Task
24's hard rules. Specifically: no visibility filter or new feature is
added to the engine — the value model already has n_visible_players;
the visibility effect is reported as a limitation, not fixed.
Step 6 (cross-fitted outcome validation) runs whatever Step 5 shows.
The per-fold value models in Step 6 must be built from the v5 row
definition (in-possession, own-event label, fixed directions, rotated
prev location).

## Execution
`decision_execution_risk.py`'s cross-team defect (Task 24, Step 1(c))
stays unfixed and unexercised; Execution is not computed. Record it in
the results page's known-issues list.

## Memory gate
Before Step 2 and again before the EV corpus recompute, read the
"System-wide memory free percentage" line from macOS
`memory_pressure`, and available memory. Proceed at >= 40% and >= 3 GB.
If below, wait and re-check (quit other apps if possible); report every
reading. One match in memory at a time.

## HARD RULES
- Code changes: none beyond what Task 24's Step 4 requires to run the
  rebuild on new `_vN` paths.
- Tests unchanged. `data/raw_holdout/` untouched.
- No leaderboards, no player identity, no interpretation.
- No memory writes. Don't edit docs/JOURNAL.md.
- When finished, reply only that the task is done plus commit hashes.

## Output
docs/results/25-engine-rebuild-v5.md (template). Commit per rule 9.
