# Analysis Plan v2 — Decision-Making in Football (PREREGISTRATION)

Written 2026-09-20 by the research lead. Frozen once committed. Changes
after any Study A, B or C result is observed must be dated amendments
appended at the bottom, never edits above.

## 0. Disclosures (read first)
- This plan was written AFTER the Pillar 4 market test returned an
  underpowered null (docs/results/03-primary-model.md). The questions
  below are new questions, not re-analyses of the market data. The
  market work is closed; it appears in the paper only as a scoping note.
- Task 01 reported the aggregate EV distribution of chosen vs unchosen
  options. No EV has been examined by situation, option type, team or
  player context. No situation features have been joined.
- The engine (pass success, possession value, behavior policy, Decision)
  is unchanged from the frozen commit 9db72ef. Nothing in this plan
  retrains or modifies it.

## 1. Shared definitions
- Pass: an eligible, angle-matched open-play pass from Task 01
  (171,618 passes, 299 matches, 8 men's competition-seasons).
- Options: the visible-teammate candidates for that pass, each with
  p_success, EV and policy_probability, as already computed.
- Coordinates: ALWAYS the attacking-direction-normalized coordinates
  (src/decision_engine/pitch_direction.py). Never raw coordinates.
- Decision (per pass) = EV(chosen) - sum over options of
  policy_probability * EV. Unchanged from Task 01.
- Value units: EV is a probability of scoring within the next 10
  actions. Summed over passes it is reported as "goal-equivalents" and
  always labeled as an upper bound (it ignores downstream adaptation).

## 2. Situation cells and option types (fixed now)
Situation cell = passer zone x pressure x game state = 18 cells.
- Passer zone (normalized x on 120 length): defensive third x<40,
  middle third 40<=x<80, final third x>=80.
- Pressure: StatsBomb under_pressure flag on the pass event (yes/no).
- Game state, from the passing team's view at the moment of the pass:
  leading / level / trailing.
Secondary only (never used to define primary cells): channel
(left/centre/right), play_pattern (counter vs settled), minute band.

Option type = direction x length = 9 types.
- Direction, relative to the attacking goal: forward if the option's
  bearing is within 45 degrees of straight at goal; backward if more
  than 135 degrees away; lateral otherwise.
- Length (passer to option): short < 15m, medium 15-30m, long >= 30m,
  converted into whatever unit the distance column uses (Task 04
  confirms the unit and the conversion before anything is typed).

## 3. STUDY A — Where does the sport systematically choose badly?

### 3.1 Split (created before any Study A statistic exists)
Matches are split 50/50 into DISCOVERY and CONFIRMATION, stratified by
competition-season, seed 20260920. The split file is committed to git
before Study A runs. Confirmation data is not touched until discovery
candidates are written down and committed.

### 3.2 Support
An (option type k, cell c) pair is analyzable only if, in the discovery
half, type k was CHOSEN at least 100 times in cell c. Below that, the
model's values for type k in cell c cannot be checked against reality
(see Gate D) and the pair is reported as "unverifiable", never as a
finding.

### 3.3 Primary statistic
For each pass and each option type available in it, let EV*_k be the
highest EV among options of type k. Let j be the type the player chose.
Type-level gap for the pass: g_k = EV*_k - EV*_j.
(Both sides are maxima, so the comparison is between kinds of pass on
equal footing. This isolates choosing the wrong KIND of pass from
choosing the wrong teammate within the right kind.)

For each analyzable (c, k):
- G(c,k) = mean of g_k over passes in c where k was available and j != k
- P(c,k) = share of those passes with g_k > 0
- s(c,k) = share of passes in c with k available where k was chosen
- L(c,k) = G(c,k) x number of such passes, per team-season
  (goal-equivalents left on the table, upper bound)
Uncertainty by bootstrap resampling of MATCHES (1,000 draws).

### 3.4 What counts as a blind spot (all conditions required)
In DISCOVERY, a (c,k) pair is a CANDIDATE if:
  1. G(c,k) > 0 with bootstrap 95% CI excluding zero,
  2. P(c,k) > 0.5 (the alternative is better more often than not),
  3. L(c,k) >= 0.5 goal-equivalents per team-season (practical floor).
Candidates are written to a committed file BEFORE confirmation runs.
In CONFIRMATION, a candidate is CONFIRMED if G(c,k) > 0 with
Benjamini-Hochberg adjusted significance at q = 0.05 across all
candidates, and conditions 2 and 3 also hold.
A confirmed pair becomes a BLIND SPOT only if it also passes Gate D.

### 3.5 GATE D — is the blind spot the sport's or the model's?
The known threat: the model may overvalue options players rarely
choose, and that error would look like a sport-wide blind spot.
For each confirmed (c,k), among passes where players DID choose type k
in cell c, compare predicted to realized:
  - completion: mean p_success vs actual completion rate
  - value: mean EV vs mean realized value (as defined for Execution)
Because realized value sits systematically below EV everywhere (the
known negative Execution mean), calibration is judged RELATIVE: the
calibration error for type k minus the calibration error for the
modal chosen type in the same cell. The bootstrap CI of that
difference must include zero or be favorable to type k.
Fail -> the pair is reported as a model limitation, not a blind spot.

### 3.6 Sensitivity checks (reported for every blind spot, no selection)
  a. EV*_k replaced by the MEAN EV of type-k options (guards against
     max-over-more-candidates inflation). Also report the average
     number of candidates per type.
  b. High-visibility frames only (top half of frames by number of
     visible players).
  c. Within each competition-season separately (Simpson's paradox
     check). Report sign in every competition with >= 100 available
     passes in that cell.

### 3.7 Study A failure condition
If no pair survives confirmation and Gate D, the result is: "within
what the freeze frame shows, the sport's choices are consistent with
available value; apparent gaps are within model error." This is a
valid finding and is reported as such.

## 4. STUDY B — Does decision quality travel?

### 4.1 Question
What share of systematic variation in Decision belongs to the player,
and what share to the team context (system, coaching, teammates)?

### 4.2 Units
Team context = team x competition-season (e.g. one national team at one
tournament, one club in one season). Stage-1 unit = player x team
context with at least 20 eligible passes.

### 4.3 Model (two stages)
Stage 1: for each player x team context, mean Decision and its standard
error (pass-level SD / sqrt(n)).
Stage 2: random-effects model on the stage-1 means, weighted by their
known sampling variance, with CROSSED random effects for player and for
team context, plus fixed effects for the unit's share of passes in each
passer zone and under pressure (so role and situation mix are not
counted as player or team skill).
Primary estimand: S = var_player / (var_player + var_team), with a 95%
interval (bootstrap by player, 1,000 draws).

### 4.4 GATE E — identifiability
Report the number of players contributing to two or more team contexts
at the 20-pass floor, and separately club-plus-international movers.
If fewer than 100 players have two or more contexts, OR the team
variance estimate sits at the zero boundary, OR the interval for S
spans more than 0.6 of the unit range, Study B is reported as
descriptive only and cannot lead the paper.

### 4.5 Secondary
  a. Movers with the same position group in both contexts only (guards
     against role change between club and country).
  b. Descriptive: for movers, correlation of their context-specific
     estimates across contexts.

## 5. STUDY C — Choice or execution?

### 5.1 Question
Across players, how much of the real (non-noise) spread in value added
per 100 passes comes from what they choose versus how well they execute?

### 5.2 Method
Units: player x competition-season with >= 200 eligible passes (the
138-unit sample). For each of 100 random split-halves:
  - true variance of Decision  = cov(Decision_half1, Decision_half2)
  - true variance of Execution = cov(Execution_half1, Execution_half2)
  - true covariance = mean of cov(Dec_h1, Exe_h2) and cov(Dec_h2, Exe_h1)
Cross-half covariances remove noise because measurement errors in
different halves are independent. This is equivalent to correcting
each variance by its reliability, and uses the same machinery.
Primary estimand: choice share = true var(Decision) /
[true var(Decision) + true var(Execution)], median across splits, with
a bootstrap interval by unit. Covariance reported alongside.
Also report the raw (uncorrected) share, to show how much noise alone
inflates execution's apparent importance.

### 5.3 Failure condition
If the true variance of Execution comes out negative or its interval
spans zero widely, report bounds for the choice share rather than a
point estimate, and say so in the abstract.

## 6. Appendix analyses (descriptive, no hypotheses)
  a. Reliability audit: 100-split reliability curves (thresholds 100 to
     500 passes) for completion rate, progressive-pass rate, xA per pass,
     Decision and Execution. Report the minimum passes for >= 0.70.
  b. Leaderboard: players pooled across contexts with >= 200 passes,
     ranked by Decision shrunk toward the mean by its reliability.
     Face validity only.
  c. Market: two-sentence scoping note citing results page 03. No new
     analysis.

## 7. Closed researcher degrees of freedom
- Cells, option types, thresholds, floors and gates above do not change
  after results are observed.
- No additional cells, types or subgroups are promoted to primary.
- All sensitivity checks are reported in full, including failures.
- If a definition turns out to be impossible to implement, the builder
  STOPS and the research lead issues a dated amendment before any
  result under the changed definition is computed.
