# Task 13c — WP diagnostic, and one conditional attempt

Governing document: docs/specs/analysis-plan-v3.md, Amendments v3-1 to
v3-3. Read v3-3 carefully: Step 2 runs ONLY if Step 1 supports it.

## Step 0 — Commit Amendment v3-3 alone. Record hash and SHA-256.

## Step 1 — The diagnostic (v3-3.2). Always run.
Strength proxy: for every team, goals scored minus conceded per match,
computed across the corpus extract plus the 299 study matches. Report
how many teams get a proxy and the distribution.
Within the failing bucket (d = +/-1, m_bin = 85), split the 62 matches
by whether the LEADING team is the stronger side. For each half report:
n matches, n states, mean predicted WP, mean observed WP, difference in
percentage points, and a match-clustered t-statistic.
Repeat the split at m_bin = 80 and m_bin = 60 for context.
State plainly which explanation the diagnostic supports:
  (i) construction too coarse — halves behave similarly; or
  (ii) team strength — halves differ sharply.

## Step 2 — ONLY if the diagnostic supports (ii)
Apply the v3-3.4 rename mapping, recovering the 41 excluded matches.
Estimate scoring rates as a function of game state AND relative team
strength (leading team's proxy minus trailing team's, or the equivalent
for level states). Rebuild WP. Revalidate under the ORIGINAL gate from
plan v3 section 2 on the 299 study matches' states; report per-bucket
results and the Brier score against WP-299 and WP-corpus.
ONE attempt. If it fails the original gate, stop and report — do not
iterate, do not loosen the gate, do not try a third construction.
If it passes, build O3 for all 1,237,611 options per plan v3 section 1,
write data/processed/options_o3.parquet, and report the pass- and
player-level correlations between Decision_O1, O2 and O3 plus the
argmax disagreement rates.

## Step 3 — Verdict
State clearly: O3 BUILT or O3 ABANDONED, and on which evidence.

## HARD RULES
- Step 2 runs only on a supported diagnostic. If (i) is supported, skip
  it entirely and say so.
- One attempt only. No gate changes.
- No leaderboards, no player names, no referee tests.
- No memory writes. Don't edit docs/JOURNAL.md.
- When finished, reply only that the task is done plus commit hashes.

## Output
docs/results/13c-wp-diagnostic.md (template). Commit per rule 9.
