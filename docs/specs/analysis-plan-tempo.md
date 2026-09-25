# Analysis Plan — Tempo Module (PREREGISTRATION)

Written 2026-09-25 by the research lead, before any tempo quantity has
been computed. Frozen once committed; amendments appended below.

## 0. Why this is independent
Tempo is computed from StatsBomb event timestamps (millisecond
resolution) and ball-receipt events. It uses no option set, no
pass-success model, no value model and no expected value. It is
therefore unaffected by docs/ENGINE_AUDIT.md and survives the engine
rebuild whatever that produces. It is also the one dimension of the
"eye test" — setting and varying the rhythm of a game — that no part of
this project has measured.

## 1. Unit and sample
Player x competition-season, restricted to the 299-match study sample.
Primary threshold 200 eligible on-ball involvements, matching the
existing convention; the reliability curve (section 5) reports
thresholds from 100 to 500 so the threshold is justified by measurement
rather than by habit.
Open play only, consistent with the rest of the project: set pieces,
throw-ins, corners, free kicks, kick-offs and goalkeeper distributions
excluded.

## 2. Time on ball (the core quantity)
For each open-play pass, time_on_ball = pass timestamp minus the
timestamp of that player's immediately preceding Ball Receipt* in the
same possession.
  - A Carry event between receipt and pass does not break the chain.
  - Passes with no preceding receipt in the possession (won by tackle or
    interception, headers from clearances, etc.) are EXCLUDED and the
    excluded share is reported, overall and per player.
  - Values below 0 or above 15 seconds are excluded as data errors; the
    excluded share is reported. No other trimming.
Reported per player: median, interquartile range, and the share of
passes released in under 0.4 seconds ("one-touch share").

## 3. Composure: does time on ball change under pressure?
Using StatsBomb's under_pressure flag on the pass:
  pressure_delta = median time_on_ball under pressure
                 - median time_on_ball not under pressure
Reported per player with a bootstrap interval (1,000 draws, clustered by
match). Negative means the player releases faster when pressed.
No claim is attached to the sign in advance. This is a descriptive
profile, not a quality measure: releasing faster under pressure can be
composure or panic, and this metric cannot distinguish them.

## 4. Rhythm: does the player change the team's pace?
Possession sequences are the open-play possessions already built for
Task 11 (at least 3 eligible passes), reused unchanged.
  sequence_pace = passes per second within the sequence.
  pace_delta(player) = mean pace of sequences containing at least one of
  his passes, minus the mean pace of sequences by the same team in the
  same match containing none.
Within-match, within-team by construction, so team style and match state
are differenced out. Bootstrap interval clustered by match.
Also reported: tempo_variation = the within-player standard deviation of
sequence_pace across his sequences, and the standard deviation of his
own time_on_ball. Stated plainly in the write-up: variation is not
evidence of control — a player who is inconsistent and a player who
deliberately changes gears look identical here, and this module cannot
separate them.

## 5. GATE — is tempo measurable at all?
Before any tempo number is interpreted or related to anything else, run
the existing reliability machinery: 100 random split-halves, Spearman-
Brown corrected, median and 5th-95th percentiles, at thresholds 100,
150, 200, 250, 300, 400, 500, for each of: median time_on_ball,
one-touch share, pressure_delta, pace_delta, tempo_variation.
  - A metric with median reliability >= 0.70 at the 200 threshold is
    USABLE and may be reported and related to other quantities.
  - Between 0.50 and 0.70 it is reported as PROVISIONAL, always with its
    reliability stated inline.
  - Below 0.50 it is reported as NOT MEASURABLE and is not related to
    anything else, not ranked, and not used in the paper's argument.
This gate applies to each metric separately and is fixed here.

## 6. Relationships (only for USABLE or PROVISIONAL metrics)
  a. Correlation matrix among the tempo metrics.
  b. Correlation with the public metrics already computed: completion
     rate, progressive-pass rate, xA per pass.
  c. NOT correlated with engine v1's Decision, Execution or Risk, which
     are withdrawn as measurements per D-015. If engine v2 passes its
     falsification battery, the correlation with its Decision is
     computed then, not now.
  d. Descriptive leaderboards: top and bottom 20 by each usable metric,
     with position group, competitions and involvement counts.

## 7. What this module does not claim
It does not measure whether changing tempo is good. It has no outcome
test and no value model behind it. It is a description of how players
handle time on the ball, offered because the eye test's vocabulary for
registas is largely temporal and nothing in this project has measured
time at all.
An outcome test for tempo — whether pace changes predict chance
creation — is explicitly deferred; it would need the rebuilt value
model, and running it on engine v1 would be building on a withdrawn
measurement.

---

## AMENDMENT T-1 — 2026-09-25 (written before the task runs)

Purpose: prevent this module from becoming an iteration loop. The engine
rebuild is the priority; tempo gets one build and one repair pass, then
it ships or it is dropped.

### T-1.1 One repair pass, then stop
If the task reports a mechanical failure, exactly ONE repair attempt is
permitted, using the pre-specified remedies in T-1.2. If the repair does
not work, the affected metric is dropped from the module and the module
ships without it. No third attempt, no new diagnostic task, no
amendment chain.

### T-1.2 Pre-specified remedies for the two likely mechanical failures
These are decided NOW so no diagnosis is needed later.

(a) Carry sanity check fails (median time_on_ball for passes preceded by
a Carry is NOT greater than for passes without one).
Cause, in order of likelihood: the receipt lookup is picking a receipt
from the wrong possession, or a Carry by a DIFFERENT player is being
allowed to bridge the chain.
Remedy, applied once: restrict the chain to events by the SAME player,
contiguous in the event index, within the same possession, and recompute.
If the check still fails, time_on_ball is unreliable at source and the
WHOLE module is dropped. Report and stop.

(b) More than 40% of open-play passes have no resolvable receipt.
Remedy, applied once: widen the chain to allow one intervening event by
the same player of any type (Carry, Dribble, Ball Receipt*), still
within the same possession, and recompute the coverage.
If coverage is still below 60%, the module ships with the coverage
figure stated prominently as a bound on every number in it. It is NOT
dropped for this reason alone — low coverage is a limitation, not a
defect.

### T-1.3 Failed metrics are not investigated
A metric classified NOT MEASURABLE by the section 5 gate is reported
with its reliability number and dropped. No diagnostic, no attempt to
improve it, no follow-up task. The gate exists precisely so that a bad
number costs nothing further.
This applies even if all five metrics fail: in that case the module's
result is "tempo, as measurable from event timestamps at these sample
sizes, is not reliable", which is reported in one paragraph and closed.

### T-1.4 No scope growth
No new tempo metrics may be added to this module. Not receipt-to-carry
splits, not scanning proxies, not acceleration of circulation, not
anything suggested by what the first results look like. The five metrics
in section 2-4 are the module.

### T-1.5 Time box
If the task exceeds 3 hours of wall clock, it stops and reports whatever
is complete. The engine rebuild takes precedence over module
completeness.

---

## AMENDMENT T-2 — 2026-09-26

The author has lifted T-1.3's no-diagnosis rule for this one pass. Scope
is fixed here: ONE diagnostic task and ONE redesign, decided by the
existing gate. After that the module ships as-is, whatever the verdicts.

### T-2.1 What is wrong with pace_delta and tempo_variation
Found by reading src/tempo/possessions.py and src/tempo/metrics.py.

(a) CONTAMINATION BY THE WITHDRAWN ENGINE. possessions.py builds
sequences from passes_situation.parquet — the 171,618 angle-MATCHED
passes, not the 289,001 open-play passes. So the rhythm metrics inherit
engine v1's matcher, which dropped 32% of passes non-randomly (incomplete
passes at 1.6x the rate, congested-area passes via the ambiguity rule).
The module is therefore NOT independent of the audited engine, contrary
to what the tempo plan asserts. time_on_ball is unaffected — it was
built from raw events.

(b) A RATIO WITH A TINY DENOMINATOR. pace = n_passes / (time from first
to last pass in the sequence). For a 3-pass sequence the denominator can
be under a second, so pace has a heavy right tail and a handful of
sequences dominate every average built on it. It should also be
intervals, not passes, over duration: (n-1)/duration.

(c) NO ON-PITCH FILTER. The "without him" comparison set includes
sequences played while the player was substituted off or not yet on.
For a 60-minute player, a third of the match's sequences enter the
comparison as if he had chosen not to be involved.

(d) SPLIT GRANULARITY vs SAMPLE. pace reliability splits at MATCH level.
Tournament units have 3-7 matches, so each half is 2-3 matches. Much of
the measured unreliability may be the split, not the metric.
tempo_variation compounds everything above: it is the standard deviation
OF the ratio in (b), a second moment of a heavy-tailed quantity.

### T-2.2 Diagnostic, run once, four checks
  D1 Contamination: rebuild sequences from ALL open-play passes and
     report how pace and n_passes change against the current version.
  D2 Ratio noise: distribution of pace; share of sequences under 3
     seconds; the same figures using (n-1)/duration.
  D3 On-pitch: share of "without" sequences occurring while the player
     was off the pitch, from substitution events.
  D4 Split granularity: recompute pace_delta reliability splitting at
     SEQUENCE level, everything else unchanged, to isolate (d).
No interpretation, no further branching. These four, then stop.

### T-2.3 Redesign, one attempt, pre-specified now
pace_delta and tempo_variation are replaced, not patched:

  MOVE-ON SPEED. For each of the player's open-play passes, the interval
  to his team's NEXT open-play pass in the same possession. Model
  log(interval) with fixed effects for match x team, passer zone,
  under_pressure and pass distance; take the player's mean residual.
  Negative means the ball moves on faster after him than context
  predicts. Unit of observation is a PASS, not a match, so a tournament
  player contributes hundreds of observations instead of four.

  HOLD VARIATION. Standard deviation of the player's residual
  time_on_ball, residualised on the same fixed effects. Replaces
  tempo_variation's second moment of a noisy ratio with a second moment
  of a quantity already shown reliable at 0.94.

Both are built from ALL open-play passes, never the matched subset.
Both are split at PASS level, consistent with the usable metrics.

### T-2.4 The gate is unchanged and final
Section 5's thresholds apply as written: USABLE >= 0.70 at 200,
PROVISIONAL 0.50-0.70, NOT MEASURABLE below 0.50. If the redesigned
metrics fail, the module ships with median_time_on_ball, one_touch_share
and pressure_delta, plus one paragraph stating that rhythm effects were
not measurable at these sample sizes. No third attempt.

### T-2.5 Role confound in the usable metrics
The ten longest holders are all centre-backs and the fastest releasers
are all forwards, so the usable metrics substantially encode position.
Every tempo metric is therefore ALSO reported as a within-position-group
z-score, alongside the raw value. This is presentation, not a new metric.

### T-2.6 pressure_delta is described honestly, not fixed
It correlates -0.858 with median_time_on_ball, close to arithmetic: a
player who holds the ball longer has more room to drop, and nobody drops
below zero. It stays PROVISIONAL and is described as a restatement of
baseline hold time rather than as composure. No attempt to repair it.
