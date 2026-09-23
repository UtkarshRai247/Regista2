# Task 11 — Outcome diagnostics (Amendment v2-8)

Governing document: docs/specs/analysis-plan-v2.md, Amendments v2-1 to
v2-8. The preregistered H-O1/H-O2 results are final and are not
recomputed or replaced. This task explains the mechanism.

## Step 0 — Commit Amendment v2-8 alone. Record hash and SHA-256.

## Step 1 — Descriptive first (before any new regression)
Using the 583 team-match units: correlation between team mean Decision
and each of final-third pass share, middle-third share, defensive-third
share, pressure share, possession share, and team xG. Report the matrix.
This is the direct evidence for or against the compositional story in
v2-8.2.

## Step 2 — PH-O1 and PH-O2
Exactly as v2-8.3 specifies, outcome xG (primary) and goals (secondary),
clustered by team context. Report the Decision coefficient per SD with
CI and p, alongside the H-O1/H-O2 numbers from Task 10 for comparison.
Report the zone-share coefficients too.

## Step 3 — PH-O3, possession level
Build open-play possessions with at least 3 eligible passes from the
frozen per-pass table and the StatsBomb events. Report how many
possessions and how they were delimited.
Predictor: mean Decision over the possession's eligible passes,
standardized. Outcome (a): possession ends in a shot, logistic. Outcome
(b): possession xG, OLS. Controls: starting zone, number of passes,
team-context fixed effects. Clustered by match.
Report coefficients in interpretable units: for (a) the change in shot
probability per SD of Decision, for (b) xG per SD.

## Step 4 — Apply v2-8.4
Report whether the paper's "associated with chance creation" claim is
ALLOWED or NOT ALLOWED. The rule is fixed; do not adjust it.

## HARD RULES
- Do not recompute, restate or revise H-O1/H-O2. They stand.
- No new controls beyond those listed. No alternative outcomes.
- Report everything, including results that make the metric look bad.
- No interpretation for the paper. No memory writes. Don't edit
  docs/JOURNAL.md.
- When finished, reply only that the task is done plus commit hashes.

## Output
docs/results/11-outcome-diagnostics.md (template). Commit per rule 9.
