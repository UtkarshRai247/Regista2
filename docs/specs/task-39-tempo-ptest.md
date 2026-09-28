# Task 39 — Does tempo show up in results? (pass-level test, study sample)

Written 2026-09-28 by the research lead. Tempo (MOVE_ON_SPEED,
HOLD_VARIATION) was never part of the Decision engine; it is a separate
module that passed its own reliability bar (Task 16b; re-run on
corrected coordinates in Task 26 Step 2: 0.768 and 0.880 at 200 passes)
but was never tested against results. This task applies the same
pass-level out-of-match test (P-test) as Task 35. Study sample only;
holdout untouched.

## Step 0 — Commit this brief alone. Record the hash.

## Step 1 — Inputs
Per-pass tempo residuals from Task 26 Step 2's corrected re-run
(`tempo_redesign_move_residuals_v2.parquet`,
`tempo_redesign_hold_residuals_v2.parquet`), with each metric's
preregistered definition (docs/specs/analysis-plan-tempo.md and Task
16b) applied per player:
  S_move = passer's MOVE_ON_SPEED computed from his OTHER matches only.
  S_hold = passer's HOLD_VARIATION computed from his OTHER matches only.
Passers with >= 100 tempo-eligible passes elsewhere. Standardise each
across its analysis rows. Report n, and how tempo-eligible passes map
onto Task 35's pass rows (match by event_id).

## Step 2 — The test (Task 35 Step 2, unchanged)
Y = realised net xG over events i+1 ... i+10; g = Task 35's pass-level
g_oof (reuse, do not refit); Y ~ S + g_oof + role FE + team-match FE,
SE clustered by passer. Run S_move and S_hold separately. Positive
control: re-report Task 35's on the same rows. Holm across the two.
Report coefficient per SD (per pass, per 100 passes), 95% CI, raw and
Holm p, MDE.

## Step 3 — Within the 111 deep midfielders
Same, rows restricted to Task 27's group; S standardised within those
rows. Report the same columns.

## HARD RULES
- No change to tempo's definitions or any earlier artifact.
- Holdout untouched.
- No memory writes. Don't edit docs/JOURNAL.md. No interpretation.
- When finished, reply only that the task is done plus commit hashes.

## Output
docs/results/39-tempo-ptest.md (template). Commit per rule 9.

## Research lead review (added 2026-09-28, main project chat)
This brief was found uncommitted in docs/specs/ and was not written in
the main research-lead chat. It was reviewed there and adopted as-is,
with the claim rules below added before any result exists.

## What may be claimed (fixed now)
- Holm p < 0.05 in Step 2 for a metric: that tempo metric "shows up in
  the chance value of a player's passes relative to teammates in the
  same game", with its sign stated in plain words (what a higher value
  means).
- Otherwise: a stable style measure with no demonstrated link to
  results in this sample (state the MDE).
- Step 3 is reported, not claimed on its own.
