# Engine v2 — Rebuild Specification

Governing document for the rebuild. Written 2026-09-25 in response to
docs/ENGINE_AUDIT.md. Supersedes the engine built under plan v2; the
validation machinery and data pipeline are reused.

Principle: an engine claim is not usable until the engine passes the
falsification battery in section 6. No player is ranked, and no study is
re-run, before those tests pass.

---

## 1. The option space (fixes Defects 4, 5c, 5d, 5e)

An option is a DESTINATION, not a teammate.

  - Candidate destinations: a 4-yard grid over the pitch, restricted to
    cells within 60 yards of the passer and inside the pitch.
  - Plus every visible teammate's exact position, as its own candidate.
  - The CHOSEN option is the grid cell containing the actual
    `pass_end_location`. No matching, no bearing, no ambiguity rule, no
    dropped passes. Displacement between scored and actual destination
    becomes zero by construction for the grid resolution.
  - Offside: a candidate is flagged `offside_destination` when it lies
    beyond the second-rearmost visible opponent and beyond the ball, in
    the attacking direction. Offside candidates are excluded from the
    best-option and policy-baseline sets, and the exclusion count is
    reported. (With partial visibility this is approximate; the
    approximation is reported, not hidden.)

Incomplete passes: `pass_end_location` is where the ball ENDED, not
where it was aimed. Two treatments, both reported:
  - PRIMARY: use the recorded end location for all passes.
  - SENSITIVITY: complete passes only.
The difference between them is reported for every headline number.

## 2. Features, shared by every candidate (fixes Defect 5a, 5b)

All geometry in direction-normalised coordinates. All distances in
StatsBomb units, named `_u` to end the metres/yards confusion.

  - distance_u from passer to destination
  - forward_progress_u (gain in normalised x)
  - lateral_shift_u (absolute change in normalised y)
  - relative_bearing_deg to the attacking goal (NOT absolute bearing)
  - opponents_within_3u / 5u / 10u of the destination
  - distance_to_nearest_opponent_u at the destination
  - teammates_within_5u of the destination
  - lane congestion: number of opponents within a 3-yard half-width
    corridor of the passing line, and the minimum perpendicular distance
    from that line to any opponent (replaces the 1-yard boolean)
  - opponents_between_ball_and_destination
  - passer_pressure: opponents within 3u/5u of the passer
  - is_teammate_destination (1 for exact teammate positions, else 0)
  - n_visible_players in the frame

## 3. The value model (fixes Defect 2)

V must see the defence. Target and horizon unchanged (P(team scores
within 10 actions)), trained on the study sample's full event stream,
but the feature set gains freeze-frame context at the state being
valued:

  - ball_x, ball_y, prev_x, prev_y, time_remaining_period, score_diff,
    play_pattern_code (retained)
  - opponents_ahead_of_ball (between ball and the opponent goal line)
  - teammates_ahead_of_ball
  - numerical_advantage_ahead = teammates_ahead - opponents_ahead
  - distance_to_nearest_opponent_u
  - opponents_within_5u / 10u
  - defensive_line_x: normalised x of the second-rearmost opponent
  - ball_beyond_defensive_line (boolean)
  - n_visible_players

Second model, same features, target P(OPPONENT scores within 10
actions), for the net value in section 4. (Task 13's concede model is a
precedent; rebuild it on these features.)

REQUIRED TEST before use: hold ball location fixed and vary defensive
context; V must respond. Report V for the same coordinate at the 10th
and 90th percentile of `numerical_advantage_ahead`. If the difference is
not materially larger than zero, the model is still a location surface
and the rebuild has failed at this step — STOP.

## 4. Net value and expected value (fixes Defects 1, 3)

Net value of a state, from the possessing team's view:
    V_net(s) = P(team scores in 10) - P(opponent scores in 10)
evaluated with the SAME pair of models for both branches, so success and
turnover are symmetric. No negation trick, no pattern forcing.

    EV(option) = p_success * V_net(state after arrival at destination)
               + (1 - p_success) * V_net(state after turnover there)

The turnover state is the opponent in possession at the destination,
scored by the same two models from their perspective; the team's
recovery chances are therefore inside the model rather than assumed
away.

REQUIRED TEST: across all options, report the Spearman correlation
between EV and p_success. Under the old engine this is expected to be
near 1. If the rebuilt EV still exceeds 0.90, the engine remains a risk
score and the rebuild has failed — STOP and report.

## 5. Decision, Execution, Risk (fixes Defect 3)

  - Decision = EV(chosen) - sum over legal options of
    policy_probability * EV(option). Unchanged in form.
  - Execution is REDEFINED. It must measure what happened, not what the
    model expected at a destination:
        Execution = V_net(state actually observed 3 actions later)
                    - EV(chosen)
    computed from the real subsequent events, not from the destination's
    modelled value. If this cannot be computed reliably, Execution is
    DROPPED from the framework and Study C is abandoned. It is not
    reported in its old algebraic form under any circumstances.
  - Risk = variance of V_net across the success and turnover branches of
    the chosen option, i.e. p(1-p)(V_success - V_turnover)^2. Reported
    as a style descriptor, never summed into a composite.

## 6. Falsification battery — the engine must pass BEFORE any study

Each test has a pass condition fixed here, in advance.

  T1 Destination fidelity: median displacement between the scored chosen
     destination and `pass_end_location` <= 2 yards (grid half-width).
  T2 Value model sees the defence: section 3's test passes.
  T3 EV is not a risk score: section 4's test passes (Spearman < 0.90).
  T4 Synthetic scenarios, hand-built frames with known right answers:
     (a) an unmarked runner beyond the defensive line must have higher
         EV than a marked sideways option at equal p_success;
     (b) a sideways pass into a 3-opponent cluster must have lower EV
         than the same pass into open space;
     (c) with the defence square and a teammate beyond the line, the
         through ball must be in the top decile of EV.
     All three must hold. These are unit tests, committed as code.
  T5 Pass-success calibration on the REBUILT chosen rows, by pass-length
     bucket (0-20, 20-30, 30-50, 50+). No bucket may be off by more than
     5 percentage points. The old model was trained on mismatched pairs;
     this proves the new one is not.
  T6 Reliability: split-half reliability of Decision, 100 splits, at
     >=200 passes, must be >= 0.60. Below that, no player-level claim is
     made at all.
  T7 Off-policy support: report the share of chosen destinations falling
     outside the convex hull of the training destinations, per length
     bucket.

Reported but explicitly NOT a pass condition, to prevent fitting to
priors: the ranks of the plan v3 section 5 named players. They are
recorded for the reader, and no engine parameter may be changed on the
basis of them. If the engine passes T1-T7 and Kroos still ranks 120th,
that is the result.

## 7. What gets re-run afterwards, and in what order

  1. Reliability and separation gates (as plan v2's Gate A and Gate B).
  2. Outcome validation (the v2-6.3 / v2-8.3 battery, unchanged
     specifications) — this is the external referee, and it is the test
     the old engine failed.
  3. Only if outcome validation is positive: Study A, Study B, the
     leaderboards.
Study C runs only if Execution survives section 5.

## 8. Honest scope statement

This is a rebuild of the measurement instrument, not a tuning pass. It
does not fix: hidden information the freeze frame cannot show (body
orientation, off-camera runners), the absence of time and tempo, or the
fact that option value is estimated off-policy. Those are stated
limitations of any freeze-frame method and belong in the paper.
