# Task 08 — Study B corrections, Study C, reliability audit

Governing document: docs/specs/analysis-plan-v2.md including Amendments
v2-1 to v2-5. Read all of them first. v2-5 fixes a bootstrap bug and
adds post-hoc Study B checks with claim rules fixed in advance.

## Step 0 — Commit Amendment v2-5 alone. Record hash and new SHA-256.

## PART 1 — Study B corrections (v2-5)
1. Fix bootstrap_by_player: each drawn copy of a player gets a fresh
   id (e.g. original id plus draw index) before fitting. Keep team
   context ids unchanged. Add a unit test showing a player drawn twice
   is treated as two players.
2. Recompute the corrected 95% intervals for S: primary fit (B4) and
   position-matched refit (B5a). Report the Task 07 interval next to
   each corrected one.
3. PH-B1, PH-B2, PH-B3 exactly as v2-5.3 specifies.
4. Apply the v2-5.4 claim rules. Report Tier 1 and Tier 2 as ALLOWED
   or NOT ALLOWED. The rules are fixed; do not adjust them.
5. If Tier 2 is NOT ALLOWED, compute the v2-5.5 design calculation and
   report it. If Tier 2 is ALLOWED, skip it and say so.

## PART 2 — Study C (plan section 5)
Units: the 138 player x competition-season units with >= 200 eligible
passes. For each of 100 random split-halves (seed 20260920):
true var(Decision), true var(Execution), true covariance, via
cross-half covariances exactly as plan 5.2 defines. Choice share =
true var(Decision) / [true var(Decision) + true var(Execution)].
Report the median and 5th-95th percentiles across splits, plus a 95%
bootstrap interval resampling units (1,000 draws; 20 splits per draw,
disclosed). Also report the RAW (uncorrected) share. Apply plan 5.3's
failure condition if triggered.

## PART 3 — Reliability audit (plan 6a, descriptive)
For completion rate, progressive-pass rate, xA per pass, Decision and
Execution: 100-split reliability (Spearman-Brown, median and
5th-95th) at minimum-pass thresholds 100, 150, 200, 250, 300, 400, 500.
Unit: player x competition-season. Report units surviving at each
threshold and the lowest threshold where the median reaches 0.70 for
each metric (or "not reached").
If per-pass progressive or xA flags do not exist, STOP and ask — do not
approximate from season totals.

## HARD RULES
- No changes to definitions, thresholds or claim rules.
- Full tables, no sorting by effect size, no interpretation for the paper.
- No memory writes. Don't edit docs/JOURNAL.md. Don't run cross-fitting.
- When finished, reply only that the task is done plus commit hashes.

## Output
docs/results/08-studies-b-c.md (template). Commit per rule 9.
