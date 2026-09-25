# Task 17 — Engine v2: direction check, policy sharpness, Decision, T6, outcome validation

Governing documents: docs/specs/engine-v2-rebuild.md sections 5-7 and
docs/results/15-engine-v2-build.md. Steps 1 and 2 are pre-specified
checks on the built instrument; Step 5 runs only if Step 4 passes.

## Step 0 — Commit this brief. Record hash.

## Step 1 — T2 direction check (bounded: this, and nothing more)
Task 15's probe varied numerical_advantage_ahead at ONE location and
found the sign inverted. A single ceteris-paribus probe can land off the
training manifold, so test it properly and stop.
  (a) Partial dependence of M_for on numerical_advantage_ahead at FIVE
      locations: normalised x = 30, 50, 70, 90, 110 at y = 40. Report
      predicted probability at that feature's 10th, 25th, 50th, 75th and
      90th percentiles.
  (b) The same, computed separately for play_pattern = Regular Play and
      play_pattern = From Counter, to test whether the inversion is
      counter-attack states leaking into the feature.
  (c) EMPIRICAL benchmark, not model output: among real training rows,
      bin by numerical_advantage_ahead quintile within each of the five
      x-bands and report the OBSERVED rate of scoring within 10 actions.
Pre-specified reading, fixed now: if the model's partial dependence
tracks the empirical rates in (c), the model is right and the intuition
is wrong — report it as such. If the model inverts where the empirical
rates do not, the value model is misbehaving and Step 3 does NOT run;
stop and report. Do not retrain or tune in this task either way.

## Step 2 — Policy sharpness
Decision is EV(chosen) minus the policy-weighted mean EV. With ~423
candidates and 6.8% top-1 accuracy, the baseline could be diffuse enough
to reduce Decision to "destination quality versus the average pitch
cell", which would be positional, not behavioural.
Report, per pass and summarised: Shannon entropy of the policy
distribution and the effective number of options, exp(entropy); the
share of probability mass on the top 10 and top 50 candidates; and the
correlation between the policy-weighted mean EV and the unweighted mean
EV across all candidates.
Pre-specified reading: if the median effective number of options exceeds
100, or the policy-weighted and unweighted baselines correlate above
0.95, the baseline is too diffuse to be behavioural. Report that plainly
alongside Decision rather than suppressing Decision — but it becomes a
stated limitation of every downstream number.

## Step 3 — Decision, Execution, Risk (rebuild spec section 5)
Compute per pass. Execution must use V_net of the state actually
observed three actions later, from real subsequent events — not the
destination's modelled value. Report how many passes have three
subsequent events available and the share dropped. If Execution cannot
be computed this way for at least 80% of passes, drop Execution
entirely, say so, and continue with Decision and Risk.
Aggregate per player x competition-season as a mean per 100 passes,
reporting units at the 200-pass floor.

## Step 4 — T6, the reliability gate
100 random split-halves, Spearman-Brown corrected, thresholds 100, 150,
200, 250, 300, 400, 500, for Decision (and Execution if it survives).
Pass condition, fixed in the rebuild spec: Decision reliability >= 0.60
at the 200 threshold. Report the full curve.
Also report the separation check: correlations of Decision with
completion rate, progressive passes per 90, xA per 90, and with the two
usable tempo metrics (move_on_speed, hold_variation).
If T6 fails, STOP. No leaderboard, no studies, no outcome validation.

## Step 5 — Outcome validation. ONLY if T6 passes.
Run the preregistered battery from plan v2 sections v2-6.3, v2-8.3 and
v2-9.2, specifications UNCHANGED, on engine v2's Decision:
  (a) team-match xG and goals, with and without possession share,
      clustered by team context;
  (b) possession level: ends-in-shot and possession xG, with starting
      zone, pass count and team-context fixed effects, clustered by
      match.
Report every coefficient standardized with CI, p and n, beside engine
v1's published figures for the same specifications.
This is the test engine v1 failed. Report it exactly as it comes out.

## HARD RULES
- No leaderboards. No player identity anywhere in Steps 1-4. Step 5 uses
  team and possession aggregates only.
- No retraining, no feature changes, no threshold changes.
- If a pre-specified reading says stop, stop.
- No memory writes. Don't edit docs/JOURNAL.md. No interpretation for
  the paper.
- When finished, reply only that the task is done plus commit hashes.

## Output
docs/results/17-engine-v2-validation.md (template). Commit per rule 9.
