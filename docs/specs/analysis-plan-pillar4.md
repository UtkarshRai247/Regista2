# Analysis Plan — Pillar 4 (PREREGISTRATION)

Written 2026-09-19, BEFORE any market value data has been loaded.
This file is frozen once committed. Any change after the market data is
joined must be added as a dated amendment at the bottom, never by
editing the text above it.

## Plain-language terms
- Execution: did the action come off better or worse than expected,
  given what the player chose to do.
- Decision: was the chosen action better or worse than what a typical
  player chooses in that same situation.
- Market value: a published estimate of what a player is worth, from
  the CC0 transfermarkt-datasets snapshot.
- Reliability: how much of a measurement is real signal rather than
  noise, estimated by checking whether a player scores similarly on two
  independent halves of their own data.
- Attenuation: the effect where a noisy predictor's regression
  coefficient is dragged toward zero even when the true effect is real.

## Core question
Does the transfer market pay for decision quality, once execution and
outcome production are held constant?

## Hypotheses
- H1: Execution is positively associated with market value.
- H2: Decision has no meaningful association with market value, after
  controls. (This is the hypothesis of interest.)
- H3: Decision predicts FUTURE market value growth, i.e. the market
  later corrects toward what decision quality already indicated.

H3 matters: it converts a null in H2 into a positive finding. H2 alone
says the market ignores something. H2 plus H3 says the market ignores
something that turns out to be real.

## Unit of analysis
One row per player per competition-season. Standard errors clustered by
player, since players appear in several competitions.

## Sample rules (fixed now)
- Men's competition-seasons with StatsBomb 360 coverage only.
- Minimum 200 eligible on-ball actions with freeze frames per row.
- Player must have a market valuation record within 90 days after the
  competition-season ends.
- Goalkeepers excluded.
- Every exclusion must be counted and reported as a sample flow table.

## Primary specification (ONE model, declared now)
Outcome: log(market value shortly after the competition-season)
Predictors of interest: Decision, Execution
Controls: outcome production (goals+assists per 90, xG+xA per 90),
minutes played, age and age squared, position group, competition-season
fixed effects, and club strength at the time of observation.
If contract length is present in the CC0 dataset, include it.

Everything else is SECONDARY and must be labeled as such in the write-up.

## Secondary specification (H3)
Outcome: change in log market value from just after the
competition-season to 12 months later.
Same predictors and controls, plus the starting value as a control.

## The reliability gate — RUN THIS FIRST
Before any market data is loaded:
1. Split each player's actions into two independent halves.
2. Compute Decision and Execution on each half.
3. Report split-half correlation, corrected for the halving.

Thresholds, fixed in advance:
- Reliability >= 0.70: proceed as planned.
- 0.50 to 0.70: proceed, but the primary model MUST report both raw and
  attenuation-corrected coefficients, and the paper must state that the
  correction is doing real work.
- Below 0.50: STOP. We cannot distinguish "the market ignores decision
  quality" from "we measured decision quality badly". The honest
  reported result becomes the reliability finding itself.

## Separation check — ALSO BEFORE MARKET DATA
If Decision correlates with Execution, or with any existing public
metric (progressive passes, xA, VAEP, xT), at |r| > 0.7, the
decomposition is not separating anything. That is a failure of Pillar 1,
reported as such, and the market test does not run.

## What counts as failure
1. Reliability below 0.50 → stop, report the reliability result.
2. Decision and Execution not separable → stop, report that.
3. Decision coefficient significantly POSITIVE in the primary model →
   H2 refuted. The market does price decision quality. Report it. This
   is a real result and must not be reframed as anything else.
4. H2 supported but H3 also null → weaker paper: the market ignores
   something we cannot show matters. Must be reported honestly, with
   that limitation stated in the abstract, not buried.

## Researcher degrees of freedom — closed off in advance
- The primary specification above is the result. It does not change
  based on what it produces.
- Alternative specifications are robustness checks and must be reported
  as a full set, not selectively.
- No adding, dropping, or transforming controls after seeing the
  outcome.
- No changing the minimum-actions threshold after seeing the outcome.

## Known confounds we cannot fully solve
- Popularity and media exposure inflate market value independently of
  performance (Franck and Nuesch). We have no good proxy. State as a
  limitation.
- Market values are crowd-sourced estimates, not transaction prices.
  Transfer fees would be better but are far sparser. State as a
  limitation.
- Club and league prestige drive value. Controlled via club strength and
  competition fixed effects, imperfectly.
- The sample is elite players in major competitions. Do not generalize
  beyond that.

---

## AMENDMENT 1 — 2026-09-20

Made AFTER Gate A and Gate B, BEFORE any market value data was loaded,
downloaded, or joined. No outcome data has been observed.

### A1.1 Minimum threshold set to 200 eligible passes
Unit remains player per competition-season. Decision reliability is
0.703 [0.585, 0.789] at this threshold and does not improve
monotonically above it. Higher thresholds cost sample without buying
reliability.

### A1.2 Execution removed from the primary specification
Execution reliability ranges 0.41-0.73 across thresholds with no trend
and near-zero-crossing CIs. We cannot measure it well enough to support
a claim, and attenuation correction requires a reliability estimate we
do not have.

H1 is restated: observable output measures (pass completion rate,
progressive passes per 90, goals+assists per 90) are positively
associated with market value.

H2 is unchanged and remains the hypothesis of interest.

The headline contrast is now: the market prices observable output and
does not price decision quality. Execution may appear as a secondary,
clearly labeled exploratory result with its reliability stated inline.

### A1.3 Risk dropped
Risk correlates -0.776 with Decision, indicating redundancy arising from
its construction. It is removed from all analyses.

### A1.4 Primary specification control set trimmed for power
At ~138 units the original control set is overparameterized. Revised:
  log(market value) ~ Decision + completion% + progressive passes/90
    + goals+assists/90 + minutes + age + position group
    + tournament-vs-league indicator + club strength
Age-squared is dropped. Competition fixed effects are replaced by a
single tournament-vs-league indicator. Clustered by player.
If the final joined sample is below 100 units, the primary model is
reported as exploratory and the paper says so in the abstract.

### A1.5 Reliability re-estimation method
Split-half reliability must use 100 repeated random splits with the
median and interval reported, not a single split. The 0.864 vs 0.793
discrepancy on identical data shows single-split estimates are unstable.

### A1.6 Failure conditions unchanged
All failure conditions in the original plan remain in force, including
that a significantly positive Decision coefficient refutes H2 and is
reported as such.

---

## AMENDMENT 2 — 2026-09-20

Made after Gate C descriptives and the valuation-window diagnostic,
BEFORE any model was fit and BEFORE any Decision-to-value relationship
was examined.

### A2.1 Valuation window widened to 180 days
Rule unchanged otherwise: take the EARLIEST valuation record within the
window. The 79 units already matched at 90 days therefore keep their
existing valuation unchanged; widening is purely additive.

Mechanism: the valuation source updates on a roughly semi-annual cycle.
36 of 47 recoverable tournament units fall in a 150-180 day band. This
is a property of the data source's update schedule, not of the players.
Nothing is recovered beyond 180 days.

### A2.2 Valuation lag added as a control
Because tournament units are now measured at a longer lag than league
units, days_to_valuation enters the primary model as a control.

Revised primary specification:
  log(market value) ~ Decision + completion% + progressive passes/90
    + goals+assists/90 + minutes + age + position group
    + tournament-vs-league indicator + club strength
    + days_to_valuation
Clustered by player.

### A2.3 Crosswalk resolutions
Resolved by date of birth and club, recorded as manual_review:
- Idrissa Gana Gueye -> transfermarkt id 126665 (b.1989-09-26, Everton)
- Dayotchanculle Upamecano -> id 344695 (b.1998-10-27, Bayern Munich)
- Jonas Hofmann -> id 7161 (b.1992-07-14, Bayer Leverkusen)

### A2.4 Collinearity accepted
Completion%/goals+assists (r=-0.75) and forward/goals+assists (r=0.72)
are retained. These are controls, not predictors of interest.
VIF for Decision must be reported alongside the primary model.

### A2.5 Units that never recover
8 units (5 tournament, 3 league) have no valuation at any horizon and
are permanently excluded. Reported in the sample flow.

### A2.6 Everything else unchanged
All failure conditions remain in force, including that a significantly
positive Decision coefficient refutes H2 and is reported as such.
