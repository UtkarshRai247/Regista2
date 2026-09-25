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

---

## AMENDMENT v3-2 — 2026-09-23

Made after Task 13, before any leaderboard or referee test exists.

### v3-2.1 O2 negative predictions
1.75% of held-out O2 predictions are negative, which is impossible for
accumulated xG. PRIMARY fix: clip predicted values at 0. This is a
property of the target, not a tuning choice, and it is applied
identically everywhere O2 is used. Report the share clipped in the
option table and confirm the calibration deciles after clipping.
A Tweedie-objective refit is permitted as a reported robustness check
only; if run, it is selected over clipping ONLY on held-out MAE and
calibration, never on any leaderboard or referee result.

### v3-2.2 Why WP-299 failed, and what follows
The gate failed in 2 of 100 buckets, both the same state: a one-goal
lead about five minutes into the match (predicted 77.7% vs observed
62.6%). The estimated rates explain it — in this sample the LEADING
team scores faster (0.0192 goals/team-minute) than the trailing team
(0.0132), because the club competitions are built around four
possession-dominant focal teams that both lead often and keep scoring.
An early lead is therefore over-rewarded.
This is a sample-composition problem, which is exactly what Task 13b's
corpus estimation addresses. O3 remains UNVALIDATED and unbuilt until a
WP function passes the gate. Task 13b is now required, not optional.

### v3-2.3 One refinement to the gate, disclosed as post-hoc
The gate counted each (team, minute) state as independent. States within
a match are almost perfectly correlated, so a bucket of 234 states may
represent roughly 30 matches; a fixed 10-point threshold on ~30
independent observations fails often by chance alone.
Refined gate, applied identically to WP-299 and WP-corpus: a bucket
fails only if the deviation exceeds 10 percentage points AND is
significant at 95% using standard errors clustered by MATCH. Report
both the original and refined verdicts for both functions.
If WP-corpus passes the ORIGINAL gate, the refinement is not used for
selection and is reported as a footnote only. This refinement was
adopted after WP-299 failed and is disclosed as such; it is a
statistical correction to an underpowered test, not a lowered bar.

### v3-2.4 A finding that may pre-empt the comparison
Decision_O1 and Decision_O2 correlate r=0.824 at pass level and r=0.856
at player level, while disagreeing on the best option in 28.9% of
passes. If the O2 leaderboard closely resembles O1's, the conclusion is
NOT that the objective does not matter — it is that both objectives are
dominated by completion probability, which is the deeper cause of the
conservatism. That possibility is recorded here, before the leaderboards
exist, so it cannot be presented later as a prediction made in hindsight.

---

## AMENDMENT v3-3 — 2026-09-24

Made after Task 13b. No leaderboard or referee result exists yet.

### v3-3.1 The v3-2.2 diagnosis was wrong
I attributed WP-299's failure to the study sample's composition. A
corpus seven times larger, spanning 35 different competition-seasons,
produces near-identical rates (leading 0.0187 vs 0.0192, level 0.0133 vs
0.0137, trailing 0.0133 vs 0.0132) and the SAME bucket fails by the same
margin. The explanation is refuted and is reported as refuted.

### v3-3.2 Diagnostic BEFORE any further fix
Two competing explanations remain, and they are distinguishable:
  (i) the construction is too coarse — a memoryless three-state
      (leading/level/trailing) Markov model cannot represent an early
      one-goal lead;
  (ii) the failing bucket is dominated by cases where the WEAKER side
      leads early against a possession-dominant focal team and does not
      hold on, so observed WP is low for reasons of team strength, not
      of game state.
Required diagnostic, run first: within the failing bucket (d=+-1,
m_bin=85, 62 matches), split by whether the leading team is the
stronger side, using each team's goals-scored-minus-conceded per match
across the corpus and study data as the strength proxy. Report n,
predicted and observed WP for each half, with match-clustered errors.
Also report the same split at m_bin=80 and 60 for context.
If the two halves differ sharply, explanation (ii) is supported and a
strength-conditioned WP is warranted. If they do not, explanation (i)
stands and no further WP work is done.

### v3-3.3 One time-boxed attempt, and only if the diagnostic supports it
If and only if (ii) is supported: estimate scoring rates as a function
of game state AND relative team strength, rebuild WP, and revalidate
under the ORIGINAL gate. One attempt. No further iterations.
If it passes, O3 is built as specified in plan v3 section 1.
If it fails, or if the diagnostic supports (i), O3 is ABANDONED for this
submission and the paper reports plainly: a win-probability objective
could not be validated on open data under a tractable construction, and
the comparison runs on O1 and O2 alone. That is a reportable result
about what open data supports, not a gap to be papered over.
Either way, Task 14 (leaderboards and both referees) proceeds on
schedule with whatever objectives are validated.

### v3-3.4 Standing team-rename mapping
The following are documented 1:1 renames or short forms, and are mapped
rather than excluded in any future corpus work:
  Marseille -> Olympique de Marseille; Caen -> Stade Malherbe Caen;
  Hyderabad -> Hyderabad FC; ATK Mohun Bagan -> Mohun Bagan Super Giant.
Any name not on this list is excluded, never guessed. The 41 matches
excluded in Task 13b are recovered only if a WP rebuild happens under
v3-3.3; otherwise the exclusion stands and is reported.

### v3-3.5 Superseded numbers
docs/results/13-objectives.md keeps its unclipped O1/O2 correlations as
the historical record. The clipped figures in 13b supersede them. The
journal carries the pointer; results pages are never retro-edited.

---

## AMENDMENT v3-4 — 2026-09-24

Made after Task 13c (O3 built and validated), before any leaderboard or
referee result exists.

### v3-4.1 Task 14 is split
Referee 1 (plan v3 section 3) requires no leaderboard, no player names
and no expert lists. It runs first, as Task 14a.
Referee 2 (section 4) and the leaderboards run afterwards as Task 14b,
and only after the expert lists are committed, per section 4. The
constraint that lists precede leaderboards is unchanged.

### v3-4.2 Referee 2 is expected to be underpowered; power is reported
Each Team of the Tournament or Season is 11 players, many of them
goalkeepers and forwards who never reach the 200-pass floor. The
expected number of selected players among the 138 qualifying units is
roughly 15-25.
Task 14b must therefore report, BEFORE its AUC comparison: the number
of qualifying units, the number selected, and the minimum AUC
improvement detectable at 80% power given those counts. If that
minimum exceeds 0.10 AUC, Referee 2 is declared UNDERPOWERED and its
result is reported as indicative only — it cannot decide between
objectives in either direction, including in O1's favour.

### v3-4.3 Coverage rule for the lists
A competition-season is included in Referee 2 only if a published,
dated, externally authored selection exists for it. Competitions
without one are excluded and named. The lists are committed as a CSV
with a source URL per row before Task 14b runs, and are never edited
afterwards.

---

## AMENDMENT v3-5 — 2026-09-25

Made after Task 14b-prep compiled the expert lists, before any
leaderboard or Referee 2 computation.

### v3-5.1 Verification of the compiled lists
Euro 2024 was verified independently by the research lead against the
UEFA source before the task ran, and matches exactly. Euro 2020, MLS
2023 and both Ligue 1 XIs also check out.

### v3-5.2 Bundesliga 2023/24 source rejected and replaced
The compiled source (bundesliga.com "Team of the Season presented by
EA FC 24") weights FAN votes at 40%, clubs 30% and experts 30%. The
brief excluded fan-voted XIs, so it is disqualified.
Replacement: the VDV (Vereinigung der Vertragsfußballspieler, the
German players' union) Bundesliga Team of the Season 2023/24 — the
direct counterpart of UNFP, and preference level 2 in the brief.
The eleven: Gregor Kobel (GK); Jeremie Frimpong, Jonathan Tah,
Waldemar Anton, Alejandro Grimaldo (DF); Granit Xhaka, Florian Wirtz,
Jamal Musiala, Xavi Simons (MF); Serhou Guirassy, Harry Kane (FW).
Source: https://fcbayern.com/en/news/2024/09/bundesliga-team-of-the-season-2023-24-kane-and-musiala-receive-vdv-awards
Noted: this URL is a secondary report of the union's selection, the
same situation as the Ligue 1 rows, where UNFP's selections are cited
via culturepsg.com and footmercato.net. Recorded, not hidden.

### v3-5.3 Benchmark heterogeneity is a stated limitation
The selections come from four different kinds of body: UEFA technical
observers (Euro 2020, Euro 2024), players' unions (Ligue 1 x2,
Bundesliga), a league office (MLS 2023) and a single newspaper's
journalist XI (World Cup 2022, Sky Sports — FIFA publishes no official
team of the tournament). La Liga 2020/21 has no qualifying selection
and is excluded.
Coverage: 7 of 8 competition-seasons, 77 selected players.
This heterogeneity is reported in the paper as a limitation of
Referee 2. It is not corrected for, since any weighting would be our
judgement substituted for the sources'.

### v3-5.4 World Cup 2022's weaker provenance is reported inline
Wherever the Referee 2 result is stated, the World Cup row must be
identifiable, and a sensitivity excluding it must be reported, since a
journalist XI is the weakest source in the set and the World Cup
contributes the largest share of qualifying units.
