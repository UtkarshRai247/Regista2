# Task 16 — Tempo module

Governing document: docs/specs/analysis-plan-tempo.md. Read it fully
first. Runs BEFORE the engine rebuild (Task 15) by the author's
decision; it shares no code with the engine and cannot be invalidated
by it.

## Step 0 — Commit the tempo plan alone. Record hash and SHA-256.

## Step 1 — Build time on ball (plan section 2)
Write to src/tempo/. Do not modify src/decision_engine/.
From the 299-match event data: for every open-play pass, find the
player's immediately preceding Ball Receipt* in the same possession,
allowing intervening Carry events by the same player.
Report, before anything else:
  - passes with a resolvable receipt, and the share without one, broken
    down by the reason where determinable (possession won by tackle or
    interception, header, first event of possession);
  - the share excluded by the 0-15 second bound;
  - the distribution of time_on_ball overall (percentiles 5/25/50/75/95)
    and separately for complete and incomplete passes;
  - a sanity check: the median time_on_ball for passes immediately
    preceded by a Carry should exceed that for passes with no Carry.
    Report both. If it does not hold, apply Amendment T-1.2(a)'s
    pre-specified remedy ONCE, then re-report. If it still fails, drop
    the whole module and stop — do not diagnose further.
If more than 40% of open-play passes have no resolvable receipt, apply
T-1.2(b)'s remedy ONCE and re-report coverage. Do not drop the module
for low coverage; report the figure as a bound.

## Step 2 — Per-player quantities (plan sections 2-4)
Compute per player x competition-season: median time_on_ball, IQR,
one-touch share (<0.4s), pressure_delta, pace_delta, tempo_variation,
and the count of involvements behind each.
Reuse Task 11's possession-sequence construction unchanged for
pace_delta; state in the results page that it was reused, not rebuilt.

## Step 3 — THE GATE (plan section 5). Run before anything else is
interpreted.
100-split Spearman-Brown reliability at thresholds 100, 150, 200, 250,
300, 400, 500 for all five metrics, with median and 5th-95th
percentiles and the surviving unit count at each threshold.
Classify each metric at the 200 threshold as USABLE (>=0.70),
PROVISIONAL (0.50-0.70) or NOT MEASURABLE (<0.50). The thresholds are
fixed; do not adjust them.

## Step 4 — Relationships, only for metrics that are USABLE or
PROVISIONAL (plan section 6)
Correlation matrix among tempo metrics; correlations with completion
rate, progressive-pass rate and xA per pass; top and bottom 20 by each
qualifying metric with position group, competitions and counts.
Do NOT correlate anything with engine v1's Decision, Execution or Risk —
those are withdrawn per D-015.

## HARD RULES
- Metrics classified NOT MEASURABLE are reported with their reliability
  and then dropped. They do not appear in leaderboards or correlations.
- No outcome test, no value model, no expected value anywhere in this
  task.
- Report the exclusion shares prominently in Section 3, not buried —
  if a large share of passes have no resolvable receipt, that bounds
  everything else in this module.
- One repair pass only, per Amendment T-1.1. Metrics that fail the gate
  are reported and dropped with NO diagnosis and NO follow-up.
- Do not add any metric beyond the five specified (T-1.4).
- Stop and report at 3 hours wall clock (T-1.5), however incomplete.
- No interpretation for the paper. No memory writes. Don't edit
  docs/JOURNAL.md.
- When finished, reply only that the task is done plus commit hashes.

## Output
docs/results/16-tempo.md (template). Commit per rule 9.
