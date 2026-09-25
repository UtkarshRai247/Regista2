# Engine Audit — 2026-09-25

Written by the research lead after reading options.py, pass_success.py,
expected_value.py, policy.py, possession_value.py and decompose.py line
by line, prompted by the leaderboards being stable at the bottom across
three different objectives.

Conclusion up front: the objective comparison (plan v3) could never have
worked, because the conservatism is built into the ENGINE, not the value
function. Five defects, in descending order of severity. Defects 2 and 3
are more damaging than the identification bug that started this audit.

---

## DEFECT 1 — Expected value is, algebraically, a risk score

`expected_value.py`:
    EV = p_success * V_success + (1 - p_success) * V_turnover
    V_success  = P(team scores within 10 actions | ball at destination)
    V_turnover = -P(opponent scores within 10 actions | they have it)

Both terms are small probabilities of similar magnitude (roughly 0.03 to
0.08). Rewrite it:
    EV = V_turnover + p_success * (V_success - V_turnover)
V_success - V_turnover is nearly constant across destinations, because
(see Defect 2) V barely varies with destination. p_success varies from
about 0.98 to 0.50. So EV is a monotone increasing function of
p_success with an almost constant slope. **Ranking options by EV is
ranking them by completion probability.**

This is arithmetic, not football, and it explains every leaderboard we
produced: circulators top, line-breakers bottom, unchanged by the
objective, exactly as Amendment v3-2.4 predicted without knowing why.

Two further asymmetries make it worse:
  (a) The success branch counts only upside — it ignores the chance of
      conceding while keeping the ball.
  (b) The turnover branch counts only downside — it ignores that the
      team usually wins the ball back and can still score.
So a turnover is over-penalised on both sides of the ledger.

## DEFECT 2 — The value model cannot see defenders

`possession_value.py` FEATURES = ball_x, ball_y, prev_x, prev_y,
time_remaining_period, score_diff, play_pattern_code.

No freeze-frame information at all. V is a pitch-location surface with a
little game-state context. A pass that puts a runner through on goal and
a sideways pass to the same coordinate with three defenders around the
receiver get the SAME value.

Breaking a defensive line has no value in this engine. It cannot.

This directly violates the Task 01 brief, which said in writing: "Do NOT
use a location-only grid. A location-only value function is the known
flaw we are fixing from the previous project." It was the single
headline fix carried over from Regista 1, and it was not implemented.
Nobody caught it, including me, for thirteen tasks.

## DEFECT 3 — "Execution" measures nothing

`decompose.py`: realized_value = V_success if the pass completed, else
V_turnover; Execution = realized_value - EV(chosen).
Substituting the EV definition:
    complete   -> Execution = (1 - p_success) * (V_success - V_turnover)
    incomplete -> Execution = -p_success * (V_success - V_turnover)

Execution is a deterministic function of p_success and the binary
completion outcome. It contains no information about how well the pass
was struck, weighted or received. It is a completion-rate residual
wearing another name.

This retrospectively explains its unfixable unreliability (0.48, never
reaching 0.70 at any sample size) and invalidates Study C's
choice-versus-execution split, which compared a risk score against a
completion residual.

## DEFECT 4 — The scored option is often not the pass that was played

Measured on 9,648 passes: the displacement between the matched candidate
and the actual `pass_end_location` has a median of 5.05 yards; 50.4%
exceed 5 yards, 29.2% exceed 10, 13.2% exceed 20. By length:

| pass length | median displacement |
|---|---|
| 0-20y | ~4y |
| 20-30y | 5.5y |
| 30-50y | 10.1y |
| 50y+ | 35.1y |

The error grows with pass length, so it is worst for exactly the
progressive, line-breaking and switching passes that distinguish the
players under study. Cause: D-011's angle-matching, which I chose on the
reasoning that `pass_end_location` is post-hoc information. That was
wrong: the destination is the ACTION, not the outcome.

It also corrupts the pass-success model's TRAINING data, which pairs the
features of the matched teammate's location with the outcome of the real
pass (`pass_success.py` trains on chosen rows only).

And 32% of eligible passes are dropped by the matcher, with incomplete
passes dropped at 1.6x the rate of complete ones.

## DEFECT 5 — Feature and option-space defects

  5a. `pass_success.py` uses raw `candidate_x`, `candidate_y` and an
      absolute 0-360 bearing. These are NOT direction-normalised, so the
      same tactical pass has opposite coordinates and bearings depending
      on which way the team is attacking. The value model normalises;
      the success model does not.
  5b. `LANE_WIDTH_M = 1.0` is applied to StatsBomb units, which Task 04
      established are YARDS, not metres. A defender must be within one
      yard of the passing line to count as blocking it, so
      `lane_crosses_opponent` almost never fires and passing-lane
      congestion is effectively unmodelled. `AMBIGUITY_DIST_M = 5.0`
      carries the same unit confusion.
  5c. Offside is never checked, so the "best available option" can be an
      illegal pass to a player in an offside position — and those
      positions look attractive because they are in space.
  5d. Passes into space cannot be represented at all: candidates are
      visible teammates' current positions. The runner who is not there
      yet does not exist in the option set, and a through ball has no
      correct candidate to be matched to.
  5e. The ambiguity rule discards passes where two teammates are close
      together, which systematically discards congested-area passes,
      i.e. the final third.

---

## What survives

- The data pipeline: ingestion, freeze-frame handling, situation
  context, the direction-normalisation utility itself.
- The validation machinery: discovery/confirmation splits, bootstrap,
  cross-fitting harness, reliability estimation, the coverage-tested
  REML estimator, the outcome-validation battery, the MDE audit.
- The win-probability function from Task 13c (validated, strength
  conditioned).
- Every process habit: preregistration, gates, disclosure of refuted
  hypotheses.

## What does not survive

Every player-level and option-level number produced under plan v2 and
plan v3: Decision, Execution, Risk, all three leaderboards, Study A's
blind spots, Study B's variance split, Study C's choice/execution share,
and both referee tests. They are not wrong conclusions from good
measurements; they are measurements of a quantity that is mostly
completion probability.

The results pages stay as the historical record. They are superseded,
not deleted.
