# Regista 2 — Project Journal

Running narrative record: what we did, what we found, what changed as a
result, and why. Append a new dated entry after every task, methodology
change, or design decision. Never rewrite past entries — if something
turns out to be wrong, add a new entry saying so.

Companion files:
- `docs/DECISIONS.md` — the decision log (D-xxx), terse
- `docs/specs/analysis-plan-pillar4.md` — the preregistration + amendments
- `docs/results/` — the raw per-task results pages

---

## Background — why Regista 2 exists

Regista 1 ("the Architect Framework") built six metrics for deep-lying
creative midfielders on StatsBomb open data. A systematic review found
limitations serious enough to warrant a rebuild rather than a patch:

- Validation was partly circular: it separated known registas from known
  non-registas, which confirms the labels rather than testing value.
- The composite Architect Score mixed *style* with *quality*, used equal
  z-score weights with no empirical basis, and had no units.
- Decision Surplus used a positional value proxy that systematically
  undervalued deep zones — the exact population being studied.
- Counterfactual pass values were an off-policy extrapolation problem
  that the 0.935 AUC (measured on chosen passes only) did not address.
- Surplus was measured against the *best* option (regret) rather than
  against what a typical player would choose.
- Transformer attention was used as credit assignment; attention is not
  attribution.
- One team-season made player skill and team system unidentifiable.
- No uncertainty quantification anywhere; split-half reliability was
  r=0.47 (p=0.24) on 8 players.

Regista 2 was scoped as five pillars: (1) a rebuilt decision engine with
a learned value function and a behavior-policy baseline, (2) visibility
calibration against full tracking, (3) a hierarchical player model,
(4) outcome and market grounding, (5) unsupervised role discovery.

---

## 2026-09-18 — Project start, SSAC27 target

Target: MIT Sloan Sports Analytics Conference 2027 Research Papers
Competition. Abstract due Oct 1 2026 (11:59pm ET); full paper Dec 4 2026
if selected. Solo author. Open-source repo required by the competition.

Working model: research lead (Claude, chat) makes all methodology and
interpretation decisions; Claude Code builds; the user is the messenger
and reviews raw output.

Decisions taken: D-001 (new repo, public from Sep 28), D-002 (Pillars 5
and off-ball extension cut for SSAC), D-003 (all modeling must run on an
M4 MacBook Pro, 16GB — no large transformer training).

Timeline set: 13-day abstract sprint with two go/no-go checkpoints, then
Pillar 1 during the waiting period, Pillar 3 and the non-headline pillar
for the full paper, writing from Nov 23.

Scaffolding built: CLAUDE.md, ROADMAP.md, DECISIONS.md, results
template. A duplicated-paste incident left three docs files with
identical content; caught by Claude Code, fixed. D-004 recorded the
results-page convention (`docs/results/TEMPLATE.md`, `NN-name.md`).

---

## 2026-09-18 — Task 00: data audit

Full results: `docs/results/00-data-audit.md`

Findings:
- StatsBomb open data: 80 competition-seasons, 3,9xx matches, 426 with
  360 coverage across 12 competition-seasons. **FIFA World Cup 2022 has
  360 on all 64 matches.**
- PFF FC WC2022 tracking obtained (one sample match): 185,746 frames at
  ~30fps, meters/pitch-centre coordinates, ball tracked in 66.8% of
  frames. **57.2% of player-positions are flagged ESTIMATED, not
  directly observed.**
- Match-level crosswalk PFF <-> StatsBomb WC2022: 64/64 unambiguous.
- Event-to-frame alignment tested on two goals: identical +2.0s offset,
  no drift. n=2, and goals are unusually unambiguous events.
- Regista 1's 360 frames are NOT on disk despite the README's claim —
  Regista 2 starts from zero on freeze frames.
- PFF has **no stated license anywhere** (checked, not merely
  unchecked).
- Market values: `dcaribou/transfermarkt-datasets` is **CC0-1.0**, ~650k
  historical valuation records, frozen snapshot (pipeline stopped
  mid-July 2026).

---

## 2026-09-19 — Literature check, and Go/No-Go 1

**Pillar 2's novelty did not survive.** Off-screen player imputation
with a simulated broadcast camera mask is already published: DeepMind's
Graph Imputer (Omidshafiei et al., Sci Rep 2022); Everett et al.
(arXiv 2311.14642), which reports ~7.33m error for non-visible players
and already ships a StatsBomb-360 mode with a visible/estimated flag;
and a 2026 arXiv paper doing training-free off-screen imputation with a
simulated viewport benchmark *and* measuring the downstream effect on a
possession-quality score.

**Pillar 2 died a second time on the data.** Its premise was using full
tracking as ground truth. With 57% of PFF positions themselves
inferred, PFF is not ground truth — it is another imputation model.
Comparing two estimates cannot say which is wrong.

**Pillar 4's general form is also crowded** — market-value modeling,
hedonic pricing, mispricing detection are all well covered. What was
NOT found: a test of whether the market prices *decision quality
separated from execution*. Every existing metric (goals, assists, VAEP,
xT, OBV) bundles choice and outcome.

Decisions: D-005 (PFF dropped entirely — Pillar 2 cut, license
unresolved), D-006 (public repo ships code + download scripts, no raw
third-party data), D-007 (sample = men's competition-seasons with 360),
D-008 (metric frozen before any market join), D-009 (Pillar 4 is the
headline).

The preregistration `docs/specs/analysis-plan-pillar4.md` was written
and frozen before any modeling: hypotheses H1-H3, one primary
specification, a reliability gate with thresholds fixed in advance, a
separation gate, explicit failure conditions, and a list of closed-off
researcher degrees of freedom.

---

## 2026-09-19/20 — Task 01: decision engine

Full results: `docs/results/01-decision-engine.md`

Built on 299 matches across 8 men's competition-seasons. Open-play
passes only. Three components per pass: **Decision** (chosen option's
expected value minus the policy-weighted average of all options),
**Execution** (realized value minus the chosen option's expected value),
**Risk** (variance preference).

Two spec gaps surfaced mid-task and were resolved as decisions:
- D-010: the possession-value model trains on the 299-match sample's
  full event stream, not all 3,961 StatsBomb matches — era and
  competition heterogeneity outweighs raw volume.
- D-011: StatsBomb freeze frames carry **no player identity**. The
  chosen option is identified by **angle-matching** (bearing from passer
  to pass end vs bearing to each visible teammate, <=15 degrees,
  ambiguous cases dropped). The alternative — building a synthetic
  chosen candidate from `pass_end_location` — was rejected because that
  is post-hoc information and would make chosen and unchosen candidates
  non-comparable, biasing both the success model and the policy model.

Model performance: pass success AUC 0.867, possession value AUC 0.799,
behavior policy ~3x random on top-1. A real bug was caught mid-build:
the possession-value model initially ignored attacking direction, which
would have reproduced exactly the flaw Regista 2 exists to fix.

### Gate A — reliability (the turning point)

Pooled across all players, all three metrics failed the preregistered
0.50 floor: Decision 0.227, Execution 0.131, Risk 0.310. The >500-pass
subgroup (63 players) cleared 0.70 for Decision and Risk.

The obvious move — raise the threshold to 500 — was rejected. Not on
preregistration grounds (reliability is measurement, not outcome, and no
market data had been touched) but on **power**: 63 units cannot support
an 11-parameter model. A threshold curve was run instead.

### Gate B — separation

Decision vs Execution r=0.058; Decision vs progressive passes 0.093, vs
xA -0.026, vs completion% 0.338. Clean separation from every public
metric. The one high correlation was Decision vs Risk at -0.776 —
redundancy from the Risk formula's own construction.

### Task 01b — diagnostics

Full results: `docs/results/01b-diagnostics.md`

Sample flow: 1,145,062 events -> 328,892 passes -> 289,001 open play ->
251,229 with freeze frame -> 250,850 with >=6 visible -> 171,618
angle-matched -> 2,901 player-competition-season units -> 138 units at
>=200 passes.

Repeated-split reliability (100 splits): **Decision 0.744
[0.691, 0.792]**, Execution 0.482 [0.300, 0.603].

Pass-success calibration on chosen passes is essentially unbiased
(0.8890 predicted vs 0.8886 actual), which rules out the obvious
explanation for Execution's persistent small negative mean. That mean
remains unexplained; the working hypothesis (not a finding) is that the
success branch of the EV calculation values a completed pass as clean
possession while realized value reflects immediate pressure — a level
shift absorbed by the intercept, not a per-player distortion.

**Amendment 1** followed: threshold set at 200 passes; **Execution
removed from the primary specification** (unreliable at every
threshold, and attenuation correction needs a reliability estimate we
don't have); Risk dropped (redundant with Decision); control set
trimmed for power; reliability must henceforth use 100 repeated splits,
because a single split gave 0.864 and 0.793 on identical data.

The headline contrast changed here. Not "the market pays for our
Execution but not our Decision" — which requires trusting our execution
metric — but **"the market pays for observable output (completion,
progressive passes, goals and assists) and not for decision quality."**
Those observables are measured without our machinery.

---

## 2026-09-20 — Task 02: market join, and Gate C

Full results: `docs/results/02-market-join.md`

Metric frozen first (commit `9db72ef`, SHA-256 recorded) per D-008,
before any market data was downloaded.

Crosswalk: 99/102 players resolved automatically. A real bug was caught:
naive fuzzy matching was not merely low-confidence but *confidently
wrong* (matching Jorginho to "Luiz Felipe"); using StatsBomb's own
nickname field fixed it properly. Three genuine collisions were escalated
and resolved by date of birth and club (Amendment A2.3).

At a 90-day valuation window the sample collapsed to 79 units, and
**94.5% of the losses were tournament units** — non-random attrition
that would have skewed the sample toward domestic-league players, i.e.
away from exactly the players most likely to be mispriced.

Diagnostic: the loss is bimodal, with 36 of 47 recoverable tournament
units landing in a 150-180 day band — a property of the valuation
source's roughly semi-annual update cycle, not of the players. Nothing
is recovered beyond 180 days. Because the rule takes the *earliest*
record in the window, widening is purely additive: the 79 already-matched
units keep identical valuations (later verified byte-identical).

**Amendment 2**: window widened to 180 days; `days_to_valuation` added
as a control (tournament units are now measured at a longer lag);
crosswalk resolutions recorded; collinearity among controls accepted
with VIF to be reported; 8 units that never receive a valuation at any
horizon permanently excluded.

Result: 125 units, 96 players, 61 tournament / 64 league — above
Amendment A1.4's threshold of 100, so the primary model is confirmatory
rather than exploratory.

---

## 2026-09-20 — Task 03: the primary model

Full results: `docs/results/03-primary-model.md`

**Decision coefficient: -0.285, p=0.733, 95% CI [-1.925, 1.355].**
In plain units: -2.40% market value per SD of Decision, CI
[-15.13%, +12.24%]. n=125, 96 clusters, R^2=0.588. VIFs all low
(Decision 1.787, max 3.53).

H3 (does the market correct later?): Decision -0.775, p=0.111, also null
though larger in magnitude and closer to significance.

Robustness, all six reported without selection: two variants (90-day /
79-unit, and league-only) show a *significant negative* coefficient
(p=0.043, p=0.033); the primary, >=250-passes, midfielders-only, and
without-club-strength variants do not reach significance. None show a
significant positive coefficient, so H2's stated failure condition is
not triggered.

### Interpretation (research lead, 2026-09-20)

**The study was underpowered from the start.** With a clustered SE of
0.837, the smallest effect detectable at 80% power is ~2.35 log points,
or roughly **22% market value per SD of Decision**. No plausible
mispricing effect is that large. The null describes our sample size, not
the market.

That also disposes of the two significant negatives: in a study powered
only to ~22%, a subset coefficient clearing p<0.05 is what noise looks
like. Both variants are strict subsets of the primary sample (79 of 125;
64 of 125), and across six checks roughly one false positive is
expected. Reported, not built upon.

**Face validity of Decision, by detailed position** (n per cell in
brackets; several cells are tiny, so the ordering is indicative only):
attacking midfielders highest (~0.32, n=3), central midfielders and
centre backs clustered ~0.21-0.26, full backs ~0.14-0.24, wingers and
forwards lowest (~0.07-0.13). It separates central structured-possession
roles from wide and forward roles — coherent, and *not* simply a
"centre back" metric, which was the fear given the 72/42/11
defender/midfielder/forward composition at a 200-pass floor.

### Consequence: the headline pivots

The mispricing claim is not available. Proposed reframing, to be
confirmed: the paper's contribution becomes **measurement** — decision
quality in passing can be measured from open data via a policy-baseline
decomposition; it is reliable at 0.744 but only above ~200 eligible
passes; it is separable from every public metric; and at the sample
sizes open data permits, market-efficiency tests of it are underpowered
by roughly a factor of two.

Rejected alternative: lowering the pass threshold to recover units. That
buys power with noise — more units, lower reliability, worse
attenuation.

Open question at time of writing: whether the paper's centre of gravity
sits on the metric itself or on the measurement-limits argument. The
lead's view is the latter, with the metric as the vehicle.

### Standing limitations to carry into the write-up

- Passes only; carries, holds and shots are outside the option set.
- Passes into space are not modeled — options are visible teammates.
- A 200-pass floor selects for centre backs and central midfielders.
- Angle-matching drops ambiguous passes, and incomplete passes drop at a
  higher rate than completed ones (~1.6x), which biases Execution.
- Market values are crowd-sourced estimates, not transaction prices.
- Popularity and media exposure inflate valuations with no proxy
  available (Franck & Nuesch).
- Sample is elite players in major competitions; do not generalize.

---

## 2026-09-20 — Stepping back: the pivot away from market value

Prompted by the author, not by a result: the project had drifted. Regista
set out to measure how good registas are relative to one another; by
Task 03 the paper was about Transfermarkt. The market route was chosen at
Go/No-Go 1 because the literature check made it look most novel, but it
answered only the secondary clause of the research question, and it
forced the unit of analysis up to player-seasons, where n=125 made it
structurally underpowered.

Alternatives considered: outcome grounding (does Decision predict team
results — familiar shape); a reliability audit of the public toolkit;
reframing outcome grounding as a choice-vs-execution decomposition; and
two genuinely new questions — where the sport as a whole chooses badly,
and whether decision quality belongs to the player or his system.

**Feasibility check against the data on disk** before committing:
- Naive "does it travel" (same player, reliable score in two systems):
  only **11 players** clear 200 passes in both club and international
  contexts. Dead in that form.
- Pass-level version with crossed player and team effects: **592 players
  with 2+ team contexts, 247 club-plus-international**. Viable.
- Option-level file: 1,237,611 scored options with EV and policy
  probability; situation context (pressure, score, minute, phase) still
  needs joining from events.
- Club competitions appear to be single-focal-team seasons (e.g. 34
  Bundesliga matches = Leverkusen's season); opponents appear in only a
  match or two. To be verified in Task 04.

**Decision (D-012):** three studies on one engine — A (sport-wide blind
spots, headline candidate), B (player vs system, second result), C
(choice vs execution, framing result); reliability audit and
leaderboard as appendix; market test reduced to a scoping note. Women's
replication cut.

**Preregistration v2** (`docs/specs/analysis-plan-v2.md`) written before
any situation-level join. Key protections: 18 fixed situation cells x 9
option types; type-level gaps compared max-to-max so that choosing the
wrong kind of pass is separated from the wrong teammate; a 100-chosen
support floor; discovery/confirmation split by match with BH correction;
Gate D, a RELATIVE tail-calibration check, because the dominant threat is
the model's own blind spot being reported as the sport's; and Gate E for
whether player and team variance are separable at all.

Disclosed openly: the questions changed after the market null. Task 01's
aggregate chosen-vs-unchosen EV distribution had already been seen;
nothing by situation, type, team or player had.

---

## 2026-09-20 — Task 04: situation context joined

Full results: `docs/results/04-situation-context.md`

All 171,618 passes carry situation context. Score reconstruction matched
the recorded final score in **all 299 matches** — the gate that could
have invalidated every game-state cell. StatsBomb units confirmed as
yards empirically (195 penalty spots at a median 12.00 units from goal),
so 15m/30m became 16.404/32.808 units.

Feasibility: **107 of 162** situation x pass-type pairs clear the
100-chosen floor in the discovery half; all 18 situations populated.
Study B: **345 players** with 2+ team contexts at a 20-pass floor, **132**
club-plus-international movers, **119** of them in the same position
group in both. Gate E's count condition (>=100) passes.

Structural finding: every club competition-season is one focal team's
season — PSG (two Ligue 1 seasons), Leverkusen, Barcelona, Inter Miami
(3 usable matches). Tournaments (166 of 299 matches) have none. So
"the sport" in Study A is partly four elite possession sides.

Option typing note: under the 45/135-degree rule, lateral options are
64% of all options; long forward and long backward are each under 2%.

**Amendment v2-1** (before any value quantity was computed): L(c,k)
normalized to a 38-match season; tournaments-only sensitivity added
because of the focal-team structure; high visibility = 18+ visible
players; channel and position group confirmed as descriptive; MLS
retained; lateral findings to be described as broad categories.

Process problem caught: only three commits existed — all of src/ was
untracked. That undermines both reproducibility (SSAC requires it) and
the preregistration's credibility (the code history should show the
analysis followed the plan). Fixed in Task 05 Step 0, with a standing
commit-every-task rule added to CLAUDE.md.

---

## 2026-09-20 — Task 05: Study A discovery

Full results: `docs/results/05-study-a-discovery.md`

Of 107 analyzable pairs, **10 candidates**. All 10 are lateral_short or
lateral_medium; none under pressure; they span all three zones and all
game states. The wider table shows a near-universal type pattern:
backward options negative in every cell, forward options mostly
negative, lateral_long negative, short and medium lateral positive.

Magnitudes are small per pass: G around 0.0006-0.0021 (a tenth of a
percentage point of scoring probability), P only 0.54-0.58 (better
barely more often than not), L 0.7-1.8 goal-equivalents per 38-match
season per cell, upper bound. Candidate cells draw 42-58% of passes from
tournaments, so no candidate is a focal-team artefact at this stage.

Research-lead read: this is one pattern, not ten findings. And the shape
of the pattern is the warning. A genuine sport-wide blind spot would
plausibly depend on the situation; a model calibration error attaches to
a TYPE of pass and shows up in every situation. What we see is
type-specific and nearly situation-invariant. It also runs against
conventional analytics wisdom (which says teams should be more
progressive, not circulate more) — not disqualifying, but a reason for
extra scrutiny. The max-over-more-candidates artefact is at most a
partial explanation: lateral_medium has more candidates than the chosen
type (2.0 vs 1.7), but lateral_short has FEWER (1.5 vs 1.9) and still
shows the effect.

**Flaw found in my own Gate D.** It compared a candidate type's
calibration with the modal chosen type in the same cell — but short and
medium lateral are themselves the modal choices, so the gate would have
compared each candidate to itself and passed automatically. **Amendment
v2-2** (after discovery, before any confirmation data was loaded) fixes
this and makes the gate stricter: the reference is the alternatives
players actually chose; the pass criterion requires the upper bound of
the relative calibration bias to sit below the gap itself; and a pooled
type-level diagnostic is added because that is exactly where a model
error would show. Also disclosed: the models were trained on data that
includes confirmation matches, so Gate D is in-sample for the models.

Process: CLAUDE.md's Reporting discipline list had been truncated at
item 5 since the original paste, so items 6-8 — including the rule
against unrequested memory writes — were never in force. Repaired by
the research lead.

---

## 2026-09-20 — Task 06: Study A confirmation and Gate D

Full results: `docs/results/06-study-a-confirmation.md`

**7 of 10 candidates confirmed** on the untouched half (BH q=0.05, P>0.5,
L>=0.5). Two short-lateral cells failed only the practical floor; one
failed significance. **5 of the 7 pass the (stricter) Gate D — all
lateral_medium.** Every lateral_short candidate failed Gate D, so those
are described as model limitations, not blind spots.

Pooled calibration diagnostic (Gate D logic, all situations): the model
does NOT overvalue lateral_medium relative to the alternatives players
chose (Delta -0.00024 [-0.00047, 0.00004]); if anything it slightly
undervalues it. It DOES overvalue backward passes (backward_medium
+0.00168, backward_short +0.00066) and forward_medium (+0.00068). Since
the gap compares against the best option of the type chosen, an
overvalued chosen type makes the gap smaller, not larger — this cuts in
favour of the lateral_medium finding. The backward-pass overvaluation is
itself a model limitation for the write-up.

Sensitivity: high-visibility frames — all 7 positive with CIs excluding
zero. Per competition — 48 of 49 signs positive; the one reversal is
final third / trailing / lateral_medium in Ligue 1 21/22. Tournaments
only — all 7 positive with CIs excluding zero, so this is not a
focal-team effect.

**But sensitivity 3.6a (mean EV instead of max) cuts deep.** In the
final third, lateral_medium's gap shrinks to near zero (leading) or flips
negative (level, trailing). In midfield it survives at about half size
(0.00025-0.00062). lateral_medium has more candidates per pass (2.1-2.2)
than the chosen type (1.9-2.0), and the maximum of more noisy estimates
is inflated — a winner's curse on model noise.

Research-lead read at this point: the credible survivor is narrow.
**Midfield, not under pressure, lateral_medium, in every game state** —
confirmed, Gate D pass (with the model if anything undervaluing it),
high-visibility pass, 7/7 competitions positive, tournaments-only pass,
and it survives the mean-EV check at roughly half size. The final-third
cells look largely like a counting artefact. Worth noting for the
narrative, carefully: the 15-30m sideways ball across midfield is the
regista's pass.

**Amendment v2-3**, before any Study B quantity: two POST-HOC checks —
PH-1 (mean-EV gap with a CI) and PH-2 (count-matched gap, both maxima
over equally many options, which isolates the winner's curse directly),
with the rule for calling anything "robust" fixed BEFORE those numbers
exist. And because R is not installed, Study B's second stage is
hand-built in Python REML, which must pass a parameter-recovery test on
simulated data with the real design before any real estimate is
reported.

---

## 2026-09-20 — Cross-fitting added (Amendment v2-4)

Question from the author: can the model's deficiencies be fixed? Decision:
not before the abstract, with one exception.

Why not: the engine was frozen before these results existed, and the
freeze is what makes them credible. Retraining now, with the misjudged
pass types and the surviving blind spot in view, would be tuning with
the answer visible. The backward-pass overvaluation is the sharpest case:
fixing it would enlarge the Study A gap, so it is a correction whose
direction is known to favour us — left in place as the conservative
choice and reported as a limitation.

The exception is cross-fitting, because it retrains nothing toward any
result: 5 match-level folds, frozen code and hyperparameters, every match
scored only by models that never saw it. That turns Gate D into a
genuinely out-of-sample check. The rule for what survives was written
before any cross-fitted number exists: a candidate stays ROBUST only if
it passes G, L, Gate D, PH-1 and PH-2 again under cross-fitted values,
and cross-fitting can demote a candidate but never promote one.

Scheduled as Task 09 (Sep 24-25). Go/No-Go 2 moves from Sep 25 to
Sep 26. Deferred to the full paper: type-aware models, out-of-sample
recalibration, and shrinking noisy option values before taking maxima.

---

## 2026-09-21 — Task 07: Study A post-hoc checks, Study B primary fit

Full results: `docs/results/07-study-b.md`

**Study A: 3 of 7 confirmed candidates are ROBUST — middle third, not
under pressure, lateral_medium, in all three game states.** Both the
mean-EV check and the count-matched check stay positive with CIs
excluding zero for all three (count-matched G 0.00032-0.00064, about
30% of passes retained). Every final-third candidate is NOT ROBUST: the
two that passed Gate D collapse under the counting checks. This is the
outcome predicted after Task 06, and the rule deciding it was fixed
before the numbers existed. Cross-fitting (Task 09) is the last test.

**Study B primary fit:** the hand-built REML estimator passed all three
recovery scenarios on the real design (mean |S error| 0.032, 0.002,
0.003), and the real data reproduced decision_per_100 exactly. S = 0.654
from 1,701 units, 1,232 players, 157 team contexts; Gate E passed.
Position-matched refit unchanged (0.652). Fixed effects: middle-third
share has the highest Decision, final and defensive shares lower, and
pressure lowers it — consistent with Study A's midfield result.

**Two problems found by the research lead on reading the page and code:**
1. A bootstrap bug. Resampled duplicate players kept their original id,
   so a player drawn twice looked like one player with perfectly
   replicated units, inflating the player share in every bootstrap
   sample. The reported interval [0.626, 0.785] sits lopsided above the
   point estimate for exactly this reason. Point estimate unaffected;
   intervals superseded.
2. S is not the "does it travel" test it was sold as. Only 345 of 1,232
   players appear in more than one team context, so S is identified
   mostly from spread between players WITHIN one system, which includes
   role (position was not a fixed effect). The one direct test — the
   same player in club and international football — gave r = 0.053
   [-0.126, 0.259]. That may be pure noise from small international
   samples, which is itself unknown.

**Amendment v2-5** (before Study C or cross-fitting): the bug fix; three
post-hoc checks (position fixed effects; a noise-corrected mover
correlation; a fit using only multi-context players); and two claim
tiers fixed in advance. Tier 1 — "most systematic variation sits with
players, within the systems observed" — needs S's corrected lower bound
above 0.5 with and without position controls. Tier 2 — "it travels" —
additionally needs the corrected mover correlation to exclude zero.

---

## 2026-09-22 — Task 08: Study B corrections, Study C, reliability audit

Full results: `docs/results/08-studies-b-c.md`

**Study B's claim fails.** With the bootstrap bug fixed, S's interval
moves from [0.626, 0.785] to [0.363, 0.573]. Tier 1 is NOT ALLOWED: the
data cannot rule out team context mattering as much as the player. The
point estimate is unchanged and sits above 0.5 in every variant (0.579
to 0.654) — this is a precision failure, not a sign reversal. Tier 2
also fails: the noise-corrected mover correlation is 0.10 [-0.25, 0.53].
The design calculation says a decisive test needs about 314 movers at
current reliability; this sample has 132.

**But the new interval is also invalid, and the numbers say so.** The
corrected CI [0.363, 0.573] does not contain the point estimate 0.654.
In a crossed design, resampling one factor damages the other: with
original ids, duplicated players looked like one player replicating
himself (var_player up, S up); with fresh ids, those duplicated
identical units sit in the same team context and look like team-level
replication (var_team up, S down). Both biased, in opposite directions.
**Amendment v2-6.1** replaces the method and — importantly — selects
among cluster bootstrap, parametric bootstrap and profile likelihood by
SIMULATED COVERAGE on the real design, not by which gives a nicer
answer. If no method reaches 90% coverage, Study B reports a point
estimate with no interval.

**Study C:** choice share 0.498, median across splits, 95% CI [0.362,
0.688]; raw uncorrected share 0.393. So what a player chooses and how
well he executes contribute about equally to the real spread between
players — and the naive calculation understates choice, because
execution is measured far less reliably.

**Reliability audit** (median split-half, unit = player-competition-
season): completion and progressive-pass rate reach 0.70 at 100 passes;
xA per pass and Decision at 200; **Execution never reaches 0.70 at any
threshold up to 500** (best 0.646 at 300). This is the appendix table
that makes the measurement argument concrete.

**Two additions preregistered in v2-6 before Task 09:** horizon
sensitivity for Study A (a 10-action value horizon may itself reward
retention over progression — the sharpest technical objection to the
midfield finding, with the rule for surviving fixed in advance), and
outcome validation at team-match level (598 units), which fills the
paper's biggest hole: nothing so far links decision quality to real
results.

---

## 2026-09-22 — Task 09 Part 1: cross-fitting

Full results: `docs/results/09-crossfit-horizon.md`

**The finding survived, narrowed by one cell.** Under models that never
saw the match they score, 2 of the 3 ROBUST candidates stay ROBUST:
middle third, not under pressure, lateral_medium, when LEVEL and when
TRAILING. The leading-state cell fails the count-matched check by a
hair (CI lower bound -0.0000006). Under the fixed rule, FAIL is FAIL;
it is reported as failing, and the razor-thin margin is reported too.

Cross-fitting was a real test, not a formality: possession-value AUC
dropped 0.799 to 0.743 out-of-fold — the largest in-sample flattery of
the three models, exactly where v2-4.1 expected it. Pass-success and
policy were unchanged out-of-fold. Under that stiffer scoring the two
surviving cells cleared every check with room, and G moved barely
(0.000604 to 0.000669; 0.001140 to 0.001026).

Note on a candidate that improved: final third / leading / lateral_medium
looks stronger under cross-fitting (G 0.00269, Gate D PASS, PH-2 CI
excluding zero). Under v2-4.3 cross-fitting can demote but never
promote, so it stays NOT ROBUST. That rule was written before these
numbers existed and it is being honoured.

Secondary cross-fitted estimates: Study B S = 0.641 (vs 0.654);
Study C corrected choice share 0.549 (vs 0.498). Both stable.

**Part 2 (horizon sensitivity) did not run.** Not a bug: the machine hit
2.6 GB of swap on 16 GB, and per-match time degraded 14x on matches that
had just processed quickly. Stopped under the brief's own 4-hour rule
with 197 of 299 matches cached and resumable. Retried as Task 09b, with
a swap check before starting. **Amendment v2-7.2** states that if it
cannot complete, the paper must say the 10-action horizon is an
unvalidated assumption — it may not be quietly dropped.

**Amendment v2-7.1** adds the detectable-effect audit: for all 107
pairs, the smallest gap we had 80% power to find. The paper may only
call collective decision-making "close to optimal" for pairs where a
1.0 goal-equivalent effect would have been detected, and must report
what share of pairs that is. This is what makes the calibration framing
honest rather than rhetorical.

---

## 2026-09-22 — Task 09b: horizon sensitivity

Full results: `docs/results/09b-horizon.md`

**All 3 candidates are horizon-robust under v2-6.2**: G stays positive
with CI excluding zero at a 5-action and a 15-action value horizon. The
sharpest technical objection to Study A — that a short horizon rewards
retention and manufactures a "pass sideways" result — does not hold. The
direction of the finding is not an artefact of the 10-action choice.

**But the magnitude is horizon-dependent, and the paper must say so.**
For middle/leading, L runs 0.47 (h=5), 1.35 (h=10), 1.82 (h=15); for
middle/level, 0.43, 1.25, 1.24; for middle/trailing, 0.84, 1.93, 1.57.
At h=5 two of the three fall BELOW the 0.5 practical floor the
preregistration set for discovery. The rule is stated on G's CI alone,
so the verdicts stand as computed — but honesty requires reporting the
effect as a RANGE across horizons, never as a single number. Also
reported: PH-2's CI for middle/trailing at h=15 includes zero, so the
counting-artefact check is fragile in that cell at that horizon.

Machine note: the run completed with live memory pressure between 61%
and 66% free throughout, never tripping the runtime floor. The earlier
failure was diagnosed by the research lead as a bad gate (swap in use is
never reclaimed by macOS, so it records past pressure, not headroom)
combined with the original script accumulating all 299 matches in
memory; both fixed.

**Final Study A status.** Middle third, not under pressure,
lateral_medium: LEVEL and TRAILING survive everything — confirmation,
Gate D, both counting checks, cross-fitting and both horizons. LEADING
survives everything except the cross-fitted counting check, which it
missed by 0.0000006, and under the fixed rule it is reported as failing.

Next (Task 10): the Study B interval method chosen by simulated
coverage; outcome validation at team-match level; and the
detectable-effect audit that decides whether the calibration framing
can be used.
