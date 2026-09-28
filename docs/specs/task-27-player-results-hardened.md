# Task 27 — Harden the player results before the abstract

Written 2026-09-28 by the research lead after reading
docs/results/26-holdout-and-player-results.md. The holdout gate passed;
engine v5 is accepted. Three problems in Task 26's player outputs must
be fixed before anything is written about players. Each fix is
specified here in full, before any new number exists. No engine change.

Answers to Task 26's questions:
- Correlations: Task 26's pooled, threshold-100 figures are the
  player-level reference; Task 25's per-unit figure stays as the
  engine's separation check. Label both that way.
- Deep-midfield definition: replaced by Step 1 below; that becomes the
  standing definition.
- Coarse position_group(): left as-is for the overall table; all
  regista analysis uses Step 1's definition.
- Study B: Tier 2 ALLOWED stands as the pre-registered verdict. Step 3
  adds a disclosed sensitivity; it does not change the verdict.

## Step 0 — Commit this brief alone. Record the hash.

## Step 1 — Fix the deep-midfield group
PROBLEM: Task 26's group included anyone ever listed at a defensive
midfield position (De Bruyne, Gakpo, Müller, Foden, Sergio Ramos...),
and ranked them by a z from a different group.
FIX: a player is DEEP MIDFIELD if at least 50% of his eligible passes
(at the 100-pass threshold, pooled) were made while his event
`position` was Center, Left or Right Defensive Midfield. Report group
size and, for the 13 named players, their DM pass share. z-scores are
computed WITHIN this group only.

## Step 2 — Fix the shrinkage
PROBLEM: one reliability (0.7252) was applied to every player, so a
3,000-pass player was shrunk as much as a 100-pass one, pushing
small-sample players to the top.
FIX (empirical Bayes, per player):
  - m_i = player's mean Decision per pass; n_i = eligible passes.
  - v_i = match-clustered sampling variance of m_i:
    v_i = (1/n_i^2) * sum over matches of (sum over that match's passes
    of (d - m_i))^2.
  - Within the group being ranked (all 537 for the overall table; the
    Step 1 group for the deep-midfield table): mu = mean of m_i;
    tau^2 = max(0, var(m_i) - mean(v_i)).
  - shrunken_i = mu + tau^2/(tau^2 + v_i) * (m_i - mu);
    posterior SD_i = sqrt(tau^2 * v_i / (tau^2 + v_i));
    90% interval = shrunken_i +/- 1.645 * SD_i.
Report per 100 passes. Report mu, tau^2 and the range of shrinkage
factors for each group.

## Step 3 — Study B sensitivity: is "travels" just role persisting?
PROBLEM: a player's role usually stays the same between club and
country, and Decision partly tracks role (xA r = 0.56 within
position). PH-B2's mover correlation uses raw unit means, so it could
reflect role persisting rather than decision quality travelling.
SENSITIVITY: residualise the stage-1 unit means on the same fixed
effects Stage 2 uses (zone shares, pressure share) by variance-weighted
least squares across all units; recompute PH-B2 with the identical
procedure and bootstrap on the residualised means. Report r_obs,
reliabilities, r_true and CI beside Task 26's values. The Tier 2
verdict is not recomputed from this; it is reported as a sensitivity.

## Step 4 — Rebuild the tables
(a) Overall top 20 / bottom 20 with Step 2 shrinkage, intervals, n.
(b) Deep-midfield table (Step 1 group, Step 2 shrinkage within the
    group): every player, ranked by shrunken Decision, with n, raw,
    shrunken, 90% interval, within-group z. Report how many players'
    intervals lie entirely above / below the group mean.
(c) The 13 named players: overall rank, deep-midfield rank (or "not in
    group" with DM share), shrunken value and interval. Output only.
(d) Correlation matrix of Task 26 Step 5 recomputed within the Step 1
    group.
Write data/processed/leaderboard_v5b.parquet.

## HARD RULES
- No engine change, retraining, feature or threshold change.
- Only the three fixes above. Report `git diff --stat`.
- Named-player ranks are output, never input. Report whoever is where.
- No memory writes. Don't edit docs/JOURNAL.md. No interpretation.
- When finished, reply only that the task is done plus commit hashes.

## Output
docs/results/27-player-results-hardened.md (template). Commit per rule 9.
