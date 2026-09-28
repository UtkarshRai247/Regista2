# Task 28 — Fix the sampling variance in the player shrinkage

Written 2026-09-28 by the research lead after reading
docs/results/27-player-results-hardened.md.

## The problem (the research lead's own formula error, Task 27 Step 2)
Task 27's v_i is a match-clustered variance. With few matches it
collapses: with one match it is exactly zero (the residuals sum to
zero), so that player gets no shrinkage and a near-zero interval.
Visible symptoms: Bentancur (n=137) has a 90% interval of +/-0.013,
narrower than Busquets (n=2,994, +/-0.031); Mings (n=117) +/-0.017;
several ~100-pass players sit at the top of the deep-midfield table.

## Step 0 — Commit this brief alone. Record the hash.

## Step 1 — Replace v_i with a design-effect variance (fixed now)
Estimate ONCE, pooling all 537 qualifying players:
  - sigma2_w = pooled within-player per-pass variance of Decision
    (deviations from each player's own mean).
  - rho = pooled intra-match correlation of those deviations within a
    player (one-way ANOVA estimator, with matches nested in players;
    floor at 0).
Then for each player i with n_i passes over G_i matches,
  m_i = n_i / G_i,
  v_i = sigma2_w * (1 + (m_i - 1) * rho) / n_i.
Everything else in Task 27 Step 2 is unchanged (group-specific mu and
tau^2 by method of moments, shrinkage factor, posterior SD, 90%
interval). Report sigma2_w, rho, and for each group mu, tau^2 and the
range of shrinkage factors.

## Step 2 — Rebuild Task 27's Step 4 tables (a), (b), (c)
Same groups (Task 27's 537 overall, Task 27's 111 deep midfielders),
same columns, plus G_i (matches) for every row. Report how many deep
midfielders' intervals lie entirely above / below the group mean.
Also report, for each table, the Spearman correlation between this
task's ranking and Task 27's.
Write data/processed/leaderboard_v5c.parquet.

## HARD RULES
- Only v_i changes. Nothing else: no group, threshold, engine or
  Study B change.
- Named-player ranks are output, never input.
- No memory writes. Don't edit docs/JOURNAL.md. No interpretation.
- When finished, reply only that the task is done plus commit hashes.

## Output
docs/results/28-shrinkage-variance-fix.md (template). Commit per rule 9.
