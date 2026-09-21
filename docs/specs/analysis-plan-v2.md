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

---

## AMENDMENT v2-1 — 2026-09-20

Made after Task 04 (situation join, option typing, counts only), BEFORE
any Study A, B or C value quantity was computed. No EV, gap, Decision,
Execution or realized value has been examined by cell, type, team,
competition or player.

### v2-1.1 Normalization of L(c,k)
"Per team-season" in 3.3 is ambiguous because tournament teams play 3-7
matches and club sides 30+. L(c,k) is defined as:
  G(c,k) x (qualifying passes per team-match) x 38
i.e. goal-equivalents per standardized 38-match season, upper bound.

### v2-1.2 Additional sensitivity check 3.6d: tournaments only
Task 04 showed every club competition-season is built around one focal
team (PSG x2, Leverkusen, Barcelona, Inter Miami). A club-derived blind
spot could be one elite side's habit. Every blind spot is also reported
using World Cup 2022, Euro 2020 and Euro 2024 matches only (no focal
team). Reported in full; not a gate.

### v2-1.3 High visibility defined
Median visible players per frame is 17. "High visibility" in 3.6b
means at least 18 visible players (strictly above the median).

### v2-1.4 Descriptive field definitions confirmed
Channel = equal thirds of normalized width. Position group =
GK/Defender/Midfielder/Forward from StatsBomb position names. Both are
descriptive only and never define a primary cell.

### v2-1.5 MLS 2023 retained
Three matches, all Inter Miami. Retained as-is in all studies. In Study
B it is one team context, shrunk by the model. Excluding it would be an
unregistered sample change.

### v2-1.6 Interpretive note on option types (no change to definitions)
Under the 45/135 degree rule, "lateral" spans half the compass (64% of
options). Findings about lateral types are to be described as broad
categories in the write-up, not as precise passing patterns.

---

## AMENDMENT v2-2 — 2026-09-20

Made AFTER the discovery-half results (docs/results/05-study-a-discovery.md)
and BEFORE any confirmation-half data was loaded. Disclosed as such.
This amendment makes Gate D STRICTER. No discovery criterion is changed
and no candidate is added or removed.

### v2-2.1 The flaw
Plan 3.5 compares type k's calibration to "the modal chosen type in the
same cell". All 10 discovery candidates are lateral_short or
lateral_medium, which are themselves the most frequently chosen types
(s around 0.30-0.35). In most candidate cells the modal chosen type IS
type k, so the gate would compare a type's calibration to itself and
pass automatically. As written, Gate D cannot fail for these candidates.

### v2-2.2 Replacement reference group
Reference = chosen passes in cell c whose chosen type is NOT k — the
alternatives players actually chose instead, which is exactly what g_k
compares against.
  Bias_k   = mean(realized value - EV) over chosen passes of type k in c
  Bias_ref = mean(realized value - EV) over chosen passes of type != k in c
  Delta    = Bias_ref - Bias_k
Positive Delta means the model overvalues type k relative to the
alternatives. Realized value is defined exactly as for Execution.

### v2-2.3 Replacement pass criterion
Computed on the CONFIRMATION half, bootstrap by match (1,000 draws).
PASS only if the upper bound of Delta's 95% CI is below the candidate's
confirmation-half G(c,k). Reason: "the CI includes zero" is too weak —
a model bias as large as the gap itself would explain the whole gap.
Completion calibration (p_success vs actual, relative in the same way)
is reported in percentage points, descriptive only.

### v2-2.4 Pooled type-level diagnostic (descriptive, not a gate)
All candidates share two option types and none are under pressure. A
real sport-wide blind spot is plausibly situation-specific; a model
calibration error is type-specific and appears in every cell. So Delta
is also reported for lateral_short and lateral_medium pooled across all
18 cells, and for every other option type pooled likewise, for
comparison.

### v2-2.5 Disclosure carried to the write-up
The pass-success and possession-value models were trained on data that
includes confirmation-half matches. Gate D is therefore an in-sample
calibration check for the models, even though it is out-of-sample for
candidate selection. Stated as a limitation.

---

## AMENDMENT v2-3 — 2026-09-20

Made AFTER Study A confirmation (docs/results/06-study-a-confirmation.md)
and BEFORE any Study B quantity was computed.

### v2-3.1 Study A post-hoc robustness checks (LABELED POST HOC)
Sensitivity 3.6a showed the max-vs-max gap shrinks sharply, and flips
sign in two final-third cells, when mean EV is used instead of max.
lateral_medium has more candidates per pass (2.1-2.2) than the chosen
type (1.9-2.0). The max of more noisy estimates is inflated (winner's
curse on model noise), so part of G may be an artefact of counting.
Two post-hoc checks for the 7 confirmed candidates, confirmation half:
  PH-1: G using mean EV (as in 3.6a), now WITH a 95% bootstrap CI.
  PH-2: count-matched G — max-vs-max gap restricted to passes where the
        number of type-k options equals the number of chosen-type-j
        options, so both maxima are taken over equally many candidates.
        With 95% bootstrap CI and n.
Interpretation rule, fixed now before these are computed: a candidate
may be described in the paper as a ROBUST blind spot only if it passed
confirmation and Gate D AND both PH-1 and PH-2 are positive with CIs
excluding zero. Otherwise it is described as not robust to the counting
artefact. These checks are reported as post hoc in the paper.

### v2-3.2 Study B software (no change to the model)
R is not available. Stage 2 of plan 4.3 is implemented directly in
Python: restricted maximum likelihood for y = Xb + u_player + v_team + e,
with e having known unit-specific variance (stage-1 SE squared) and
u, v independent normal random effects with variances var_player and
var_team, optimized over log-variances with scipy.
Because this is hand-built, it must first pass a PARAMETER RECOVERY
TEST on simulated data with the real design (same players, teams and
SEs): simulate from known variance pairs including (a) both variances
equal to the observed stage-1 variance / 3, (b) var_team = 0,
(c) var_player = 0. 100 simulations per scenario. PASS requires:
in (a), the mean estimate of each variance within 10% of truth and the
mean absolute error of S below 0.05; in (b) and (c), the mean estimate
of the zero variance below 5% of the non-zero one, and S recovered
within 0.05 of 1 or 0 respectively. If any scenario fails, STOP — no
Study B result is reported from an unvalidated estimator.

---

## AMENDMENT v2-4 — 2026-09-20

Made after Study A confirmation, BEFORE any Study B, Study C or
cross-fitted quantity was computed.

### v2-4.1 Why
The pass-success, possession-value and behavior-policy models were
trained on matches that include the confirmation half (v2-2.5). Gate D
is therefore in-sample for the models. Cross-fitting removes this: every
match is scored only by models that never saw it.

### v2-4.2 Procedure
- 5 folds by MATCH, stratified by competition-season, seed 20260920,
  drawn independently of the discovery/confirmation split. Fold file
  committed before any model is retrained.
- For each fold: retrain all three models on the other four folds with
  EXACTLY the frozen code, features and hyperparameters of commit
  9db72ef. Only the training data changes. The possession-value model
  uses the full event stream of the training folds' matches (D-010).
- Score the held-out fold's options: p_success, EV, policy_probability,
  Decision, Execution, realized value.
- Report out-of-fold vs in-sample AUC and calibration for each model.

### v2-4.3 Study A under cross-fitted values (the decision rule)
For the 7 confirmed candidates, on the CONFIRMATION half, recompute G
with CI, P, L, Gate D (v2-2 criterion), PH-1 and PH-2.
A candidate called ROBUST under v2-3.1 stays ROBUST in the paper only
if, under cross-fitted values, ALL of these hold: G > 0 with CI
excluding zero; L >= 0.5; Gate D PASS; PH-1 and PH-2 positive with CIs
excluding zero. Otherwise it is reported as "not robust to out-of-sample
models" and cannot be the paper's headline. Candidates not ROBUST under
v2-3.1 are recomputed and reported for completeness but cannot be
promoted by this check.

### v2-4.4 Studies B and C under cross-fitted values (secondary)
Point estimates of S (Study B) and the choice share (Study C) recomputed
with cross-fitted Decision and Execution, reported next to the primary
estimates. No bootstrap required. Not gates.

### v2-4.5 What this does not fix
Cross-fitting removes in-sample flattery. It does not address hidden
information the freeze frame cannot show, nor the overvaluation of
backward passes (which biases against the Study A finding and is left
in place as the conservative choice).
