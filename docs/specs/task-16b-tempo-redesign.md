# Task 16b — Tempo: diagnostic and one redesign

Governing document: docs/specs/analysis-plan-tempo.md, Amendment T-2.
One diagnostic, one redesign, then the module ships. No third attempt.

## Step 0 — Commit Amendment T-2 alone. Record hash and SHA-256.

## Step 1 — Diagnostic (T-2.2). Four checks, then stop.
D1 CONTAMINATION. Rebuild possession sequences from ALL open-play passes
   in the 299 matches (not passes_situation.parquet's matched subset).
   Report: sequence count, median n_passes and median pace, old vs new,
   and the share of sequences whose n_passes changes by 2 or more.
D2 RATIO NOISE. For the new sequences: distribution of pace
   (p5/25/50/75/95/99), the share with duration under 3 seconds, and the
   same distribution using (n_passes - 1) / duration.
D3 ON-PITCH. Using substitution events, compute for each player-match
   the minutes he was on the pitch, and report the share of his "without
   him" sequences that occurred while he was OFF the pitch.
D4 SPLIT GRANULARITY. Recompute pace_delta reliability at thresholds
   100-500 splitting at SEQUENCE level rather than match level,
   everything else unchanged. Report beside Task 16's match-level
   numbers.
Report all four. Do not act on them beyond Step 2's fixed redesign.

## Step 2 — Redesign (T-2.3). One attempt.
Build both from ALL open-play passes with a resolvable receipt chain.
  MOVE_ON_SPEED: for each of the player's open-play passes, the interval
  in seconds to his team's next open-play pass in the same possession
  (drop the last pass of a possession, report how many). Fit
  log(interval) ~ C(match_team) + C(zone) + under_pressure +
  pass_distance. Player metric = mean residual.
  HOLD_VARIATION: residualise time_on_ball on the same right-hand side;
  player metric = standard deviation of his residuals.
Report n observations per player, and the two metrics' distributions.

## Step 3 — The gate (T-2.4), unchanged
100-split Spearman-Brown reliability at thresholds 100, 150, 200, 250,
300, 400, 500, split at PASS level, for MOVE_ON_SPEED and
HOLD_VARIATION. Classify at 200: USABLE >= 0.70, PROVISIONAL 0.50-0.70,
NOT MEASURABLE < 0.50. Thresholds are fixed; do not adjust them.

## Step 4 — Final tempo table (T-2.5)
For every metric that is USABLE or PROVISIONAL — the three from Task 16
plus any surviving redesigned metric — report per player-season both the
raw value and a within-position-group z-score, with the correlation
matrix among survivors and with completion rate, progressive-pass rate
and xA per pass. Top and bottom 20 by within-position z-score for each.
Do not touch engine v1's Decision, Execution or Risk.

## HARD RULES
- One redesign attempt. If a redesigned metric fails the gate, report
  it and drop it. No diagnosis, no second version, no new metric.
- pace_delta and tempo_variation are NOT rebuilt or rescued; D1-D4 are
  diagnostic evidence only.
- pressure_delta is not modified (T-2.6).
- Stop and report at 3 hours wall clock, however incomplete.
- No memory writes. Don't edit docs/JOURNAL.md. No interpretation for
  the paper.
- When finished, reply only that the task is done plus commit hashes.

## Output
docs/results/16b-tempo-redesign.md (template). Commit per rule 9.
