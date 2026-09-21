# Task 07 — Study A post-hoc checks, then Study B

Governing document: docs/specs/analysis-plan-v2.md including Amendments
v2-1, v2-2, v2-3 and v2-4. Read all of them first.

## Step 0 — Commit Amendments v2-3 and v2-4 together in one commit.
Record the hash and the new SHA-256 of analysis-plan-v2.md. v2-4
(cross-fitting) is NOT executed in this task; it is Task 09.

## PART 1 — Study A post-hoc checks (v2-3.1), confirmation half
For each of the 7 CONFIRMED candidates:
- PH-1: mean-EV G with 95% CI (1,000 match draws, seed 20260920).
- PH-2: count-matched max-vs-max G, restricted to passes where the
  number of type-k options equals the number of chosen-type-j options.
  Report G, 95% CI, P, n passes, and the share of the candidate's
  passes that survive the restriction.
- Apply the v2-3.1 interpretation rule and report ROBUST / NOT ROBUST
  per candidate. The rule is fixed; do not adjust it.

## PART 2 — Study B (plan section 4)

### Step B1 — Per-pass Decision and stage-1 units
Per-pass Decision = EV(chosen) - sum(policy_probability * EV) over the
pass's options (options_policy.parquet). Verify that averaging it per
player x competition-season reproduces decision_per_100 in
player_season_metrics.parquet (allowing for the per-100 scaling). STOP
if it does not.
Stage-1 unit = player x team context (from passes_situation.parquet),
>= 20 eligible passes. Per unit: mean Decision, SE = SD / sqrt(n),
n passes, share of passes in each zone, share under pressure, and the
player's position group.

### Step B2 — Gate E counts
Players contributing 2+ units; club-plus-international movers; movers
with the same position group in both. Number of units and team contexts.

### Step B3 — Estimator and recovery test (v2-3.2)
Build the REML estimator as specified. Run the recovery test on the REAL
design. Report every scenario's numbers. If any scenario fails, STOP and
report — do not fit the real data.

### Step B4 — Fit
Fixed effects: intercept, zone shares (defensive, final; middle is the
reference), pressure share. Report var_player, var_team, S, fixed
effects. 95% interval for S from 1,000 bootstrap draws resampling
PLAYERS (a resampled player brings all their units). Seed 20260920.
Apply Gate E (plan 4.4) and report PASS or DESCRIPTIVE ONLY.

### Step B5 — Secondary (plan 4.5)
a. Refit on movers whose club and international position groups match
   (plus all non-movers). Report S and interval.
b. For movers, correlation between their club-context and
   international-context stage-1 means (pooling contexts within each
   side, weighted by n). Report r, n, and a bootstrap CI.

## HARD RULES
- No changes to definitions, thresholds or the interpretation rule.
- Everything reported, including failures. No sorting by effect size.
- No interpretation for the paper. No memory writes. Don't edit
  docs/JOURNAL.md.
- When finished, reply only that the task is done plus commit hashes.

## Output
docs/results/07-study-b.md (template). Commit per rule 9.
