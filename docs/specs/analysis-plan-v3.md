# Analysis Plan v3 — What should a decision metric maximise?

Written 2026-09-23 by the research lead. Frozen once committed.
Amendments appended at the bottom, never edits above.
Plan v2 and every result under it remain valid and are NOT superseded;
its objective becomes O1, the baseline in this comparison.

## 0. Motivation and disclosures
Under plan v2 the Decision metric proved reliable (0.744 at >=200
passes) and orthogonal to public metrics, but the preregistered outcome
test failed: team mean Decision does not predict chance creation and is
negatively associated with xG holding possession fixed, while at
possession level it produces more shots but not better ones. The
leaderboard shows the same thing from another angle — circulators rank
top (Gundogan 5th, Kimmich 6th, Rodri 9th) while Kroos (112th),
Verratti (117th), Modric (129th) and De Bruyne (159th of 160) rank low.

Diagnosis to be TESTED, not assumed: expected value under a
retention-based value function is dominated by completion probability,
so maximising it is structurally risk-averse. If so, the metric measures
safety, not judgement.

Disclosed: this plan was written after seeing those results, and the
authors expect the alternative objectives to rank differently. That
expectation is why both referees below are external to the authors and
fixed in advance, and why all objectives are reported in full whatever
they show.

## 1. The three objectives
All share the SAME option sets, the SAME pass-success model, the SAME
behavior policy, and the SAME 10-action horizon. Only the value of a
state changes. Each is computed symmetrically for both teams, so a
turnover is valued by what the opponent gains.

  O1 RETENTION (existing): V = P(possessing team scores within the next
     10 actions).
  O2 CHANCE CREATION: V = expected xG accumulated by the possessing team
     within the next 10 actions (sum of StatsBomb shot xG).
  O3 WINNING: V = expected change in the possessing team's win
     probability within the next 10 actions, i.e.
       P(team scores in 10) x dWP(goal for)
     + P(opponent scores in 10) x dWP(goal against)
     where dWP is taken from a win-probability function of (goal
     difference, minutes remaining). O3 therefore reuses O1's model plus
     a concede-within-10 model plus WP.

For each objective and each option:
  EV_obj = p_success x V_obj(state after a completed pass)
         + (1 - p_success) x V_obj(state after a turnover)
  Decision_obj = EV_obj(chosen) - sum over options of
                 policy_probability x EV_obj(option)
Decision_obj is expressed in that objective's own units and is never
compared across objectives on raw magnitude, only on rank and on the
validation tests below.

## 2. The win-probability function (O3)
Built WITHOUT downloading the full open-data event corpus.
Goals are modelled as a Poisson process. Scoring rates per minute for
the leading, level and trailing team are estimated from the 299-match
sample's own goal times. Win probability at (goal difference d,
minutes remaining m) follows from the distribution of remaining goals
for each side. dWP(goal for) = WP(d+1, m) - WP(d, m); dWP(goal against)
= WP(d-1, m) - WP(d, m).
Validation, required before O3 is used: bucket all match states in the
sample by (d, m) and compare predicted WP against observed win rate;
report calibration and the Brier score. If calibration fails visibly
(any bucket with n >= 100 off by more than 10 percentage points), O3 is
reported as unvalidated and excluded from the referee tests.
Draws count as half a win throughout; this is stated, not adjustable.

## 3. REFEREE 1 (primary): real outcomes
Run the v2-6.3 / v2-8.3 / v2-9.2 outcome battery IDENTICALLY for each of
O1, O2, O3, with no specification changes:
  (a) team-match xG and goals, with possession share (PRIMARY as
      preregistered in v2) and without it (PH-O4, descriptive);
  (b) possession level: probability the possession ends in a shot, and
      the possession's xG, with team-context fixed effects.
Pre-specified comparison statistic: the standardized coefficient on
Decision_obj in possession-level xG (b), and in team-match xG without
possession share (a, PH-O4 form). An objective WINS Referee 1 if both
are positive with CIs excluding zero. Report all objectives' full
tables regardless of outcome.

## 4. REFEREE 2 (secondary): external expert selection
Benchmark list: published Team of the Tournament / Team of the Season
selections covering the sample's competition-seasons, assembled by the
research lead from public sources and COMMITTED BEFORE any O2 or O3
leaderboard is computed. Coverage and sources recorded; competitions
without a usable published list are excluded and that is reported.
Test: for players meeting the 200-pass floor in a covered
competition-season, predict selection from (i) team strength alone —
the team's final league position or tournament round reached — and
(ii) team strength plus Decision_obj. Compare AUC.
An objective PASSES Referee 2 only if adding Decision_obj improves AUC
over the team-strength baseline with a bootstrap CI excluding zero.
Failing Referee 2 is not fatal; it is reported.

## 5. Decision rule (fixed now)
No objective is declared "correct". The paper reports:
  - all three leaderboards side by side, top and bottom 20;
  - all three objectives' Referee 1 and Referee 2 results in full;
  - the rank of a fixed, pre-named set of players under each objective:
    Kroos, Modric, Verratti, Busquets, De Bruyne, Xhaka, de Jong,
    Kimmich, Rodri, Pedri, Gundogan, Grillitsch, Shaparenko. This list
    is fixed here, before O2 and O3 exist, and is descriptive context
    for the reader, NOT a criterion.
An objective may be described as BETTER only if it wins Referee 1 and
does not lose Referee 2 relative to O1. If no objective wins Referee 1,
the reported finding is that the choice of value function changes who
is called a good decision-maker while none of them predicts outcomes —
a stronger caution about the whole metric class.

## 6. Tempo module (descriptive, separate from Decision)
StatsBomb timestamps are millisecond-resolution and ball receipts are
separate events, so time-on-ball is computable.
Per player (>=200 eligible passes): median time from receipt to release;
share of one-touch passes (under 0.4s); and the change in the team's
pass rate per minute in the 60 seconds after his involvements versus the
team's own match baseline.
No hypotheses attached. Reported as descriptive, and correlated with
Decision_obj under each objective purely to show what it does and does
not capture.

## 7. Closed degrees of freedom
- Objective definitions, the horizon, the WP construction and both
  referees are fixed here.
- No objective is tuned. No thresholds move. The named-player list is
  never used to select an objective.
- Every objective built is reported, including any that embarrasses the
  authors' expectations.

---

## AMENDMENT v3-1 — 2026-09-23

Made before any O2 or O3 value was computed.

### v3-1.1 Win probability may be estimated from the full open-data corpus
Section 2 builds WP from the 299-match sample (~800 goals). The full
StatsBomb open-data corpus is available and disk is not a constraint, so
a second WP function is built from it and the better one is selected by
CALIBRATION, decided in advance.

Corpus scope, fixed now to avoid the era heterogeneity that D-010
rejected for the value model: MEN's competitions only, matches from the
2010-11 season onward. The 299 study matches are EXCLUDED from corpus
estimation so the comparison below is out-of-sample for the corpus
version. Report the qualifying match count and total goals.

### v3-1.2 Selection rule between WP-299 and WP-corpus
Both are validated identically on the 299-match sample's own states:
bucket by (goal difference, minutes remaining), compare predicted WP
with observed win rate, report per-bucket n, predicted, observed, and
the Brier score.
PRIMARY = whichever has the lower Brier score on those states, provided
it also passes the section 2 gate (no bucket with n >= 100 off by more
than 10 percentage points). If only one passes the gate, it is primary.
If neither passes, O3 is UNVALIDATED and excluded from both referees.
The selection is made on calibration alone. It is never made on, and
never revisited after, any leaderboard or referee result.

### v3-1.3 Scope discipline
The corpus download is a SEPARATE task and must not delay or block the
O2 build, the concede model, or the WP-299 build, all of which proceed
on the 299-match sample as planned. If the corpus task fails or runs
long, O3 uses WP-299 provided it passes the gate, and the paper reports
that the corpus version was attempted and why it was not used.
