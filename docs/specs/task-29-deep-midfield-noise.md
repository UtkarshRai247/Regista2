# Task 29 — Deep midfielders: estimate their noise from their own passes

Written 2026-09-28 by the research lead after reading
docs/results/28-shrinkage-variance-fix.md.

## Why (two specification problems in the research lead's own formulas)
Task 28 found tau^2 = 0 within the 111 deep midfielders. Two parts of
the specification bias that toward zero, independent of any ranking:
1. sigma2_w and rho were pooled over all 537 players. Forwards'
   per-pass Decision is likely more variable than deep midfielders', so
   the pooled value can overstate deep midfielders' sampling noise.
2. The method-of-moments tau^2 is unweighted, so ~60 players with
   100-250 passes dominate it and the precise estimates of players with
   800-3,500 passes (Busquets, Verratti, Xhaka, Vitinha...) barely count.
The fix below is fixed before any new number exists. Whatever it shows,
including another null, is the result; the abstract rule at the bottom
is decided now.

## Step 0 — Commit this brief alone. Record the hash.

## Step 1 — Within-group noise
Re-estimate sigma2_w and rho exactly as Task 28 Step 1 does, but using
ONLY the 111 deep midfielders' passes. Report both beside Task 28's
pooled values. Recompute each deep midfielder's v_i with Task 28's
design-effect formula and these within-group values.

## Step 2 — Precision-weighted between-player variance
PRIMARY: DerSimonian-Laird. w_i = 1/v_i; mu_w = sum(w m)/sum(w);
Q = sum(w (m - mu_w)^2); k = 111;
tau^2 = max(0, (Q - (k - 1)) / (sum(w) - sum(w^2)/sum(w))).
Report Q, its chi-square p-value on k - 1 df (a direct test of whether
deep midfielders differ at all), and tau^2.
SECONDARY: REML tau^2 for the same data, reported alongside.
Shrink toward mu_w with the PRIMARY tau^2: shrunken_i = mu_w +
tau^2/(tau^2+v_i)(m_i - mu_w); posterior SD and 90% interval as in
Task 27. Also report the same with Task 28's pooled v_i (so the effect
of each change is visible separately).

## Step 3 — An independent check that does not use the shrinkage model
Deep midfielders with >= 500 eligible passes: for each of 100 random
splits of each player's MATCHES into two halves, correlate the two
half-means across players; Spearman-Brown to full length. Report the
median and 5th-95th percentile of full-length reliability, and n.

## Step 4 — Tables
(a) All 111 deep midfielders with Step 2 shrinkage (PRIMARY): n, G, raw,
    shrunken, 90% interval; count of intervals entirely above / below
    mu_w.
(b) The >= 500-pass subset from Step 3, same columns.
(c) The six named players in the group (Kroos, Verratti, Busquets,
    Xhaka, Gundogan, Grillitsch): values and intervals. Output only.

## Abstract rule (decided now, before Steps 1-3 run)
- If the Q test rejects at p < 0.05 AND Step 3's median reliability is
  >= 0.70: the abstract may present a deep-midfield ranking, restricted
  to the >= 500-pass subset, with intervals.
- If exactly one of the two holds: the abstract reports that deep
  midfielders differ but only a few separations are reliable, naming
  only players whose intervals exclude mu_w.
- If neither holds: the abstract states that the measure does not
  reliably separate deep midfielders at available sample sizes, and no
  ranking of them is shown.

## HARD RULES
- Only Steps 1-2's changes, applied to the deep-midfield group only.
  The overall table stays as Task 28 produced it.
- No engine, group, threshold or Study B change.
- Named-player values are output, never input.
- No memory writes. Don't edit docs/JOURNAL.md. No interpretation.
- When finished, reply only that the task is done plus commit hashes.

## Output
docs/results/29-deep-midfield-noise.md (template). Commit per rule 9.
