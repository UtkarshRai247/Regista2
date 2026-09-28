# CRITIQUE v5 — an adversarial review of engine v5 and the player results

Research lead, 2026-09-28. Written as a hostile SSAC reviewer would read
the work. Ranked by how much each problem could change a conclusion.
"Checked" = verified in code or results; "Suspected" = needs a test.

## A. Problems that could change the conclusions

A1. The outcome test may be partly mechanical. (Checked)
Team Decision and team xG/goals are measured in the SAME match. A pass
into a dangerous area scores high on Decision and also tends to precede
the shot that produces the xG. Cross-fitting stops the models memorising
a match, but not this mechanical link. PH-O2 (team-context fixed
effects) rules out "good teams do both", not "the same passes do both".
Test: out-of-match prediction. Decision measured in a team's (or its
players') OTHER matches predicting this match's xG/goals. If it
survives, the headline becomes much stronger; if not, the headline
changes.

A2. Decision's zero point is wrong. (Checked)
Decision should average about zero if the "typical choice" model is
right: players cannot all beat the typical player. Instead mean
Decision is +0.28 per 100 passes overall and +0.23 among deep
midfielders; essentially every player is positive. The policy model is
weak (top-1 accuracy about 7-8% on engine v4; not yet reported for v5)
and too flat, so its "typical" choice drags in low-value options.
Consequence: "how much better than the typical choice" is not true as
stated; only differences between players are meaningful, and those may
partly reflect where the policy is worst (for example it may be worse in
some zones than others, which then rewards players who pass from them).
Test: policy calibration by zone and pass length; mean Decision by zone.
Fix candidates: better calibrated policy, or define Decision relative to
a baseline that is unbiased by construction.

A3. The "choice" is where the ball ended, not where it was aimed.
(Checked: grid.py uses the cell containing pass_end_location.)
For an intercepted or overhit pass, the end location is the interception
point or the touchline, so the player is scored as if he CHOSE that
spot. Decision is therefore contaminated with execution: a good choice
badly executed is scored as a bad choice. This is exactly what Decision
is supposed to separate from Execution, and Execution is not computed.
Test: share of Decision variance from incomplete passes; recompute
player tables on completed passes only (biased, but shows sensitivity);
better, infer the intended target for incomplete passes (nearest
teammate to the pass line, with a distance cap), specified in advance.

A4. Player tables use in-sample models. (Checked)
Engine v5's player tables are built from full-corpus models that were
trained on the same passes' outcomes. The outcome tests were
cross-fitted; the player rankings were not. A player whose passes
happened to precede goals gets a small in-sample boost. Test: rebuild
player tables from cross-fitted Decision and report the rank
correlation with v5.

A5. "Player trait" claims are mostly across roles. (Suspected, strong)
T6 reliability (0.82) and Study B's S (0.79) are computed across all
positions. Forwards and centre-backs differ a lot, so much of that
stability is role. Within deep midfielders the match-split reliability
is 0.18 (n = 16), and the mover correlation halves once pitch zones are
adjusted. The abstract-level claim "Decision is a stable player trait"
is not yet shown within a role. Test: T6-style reliability within each
position group; Study B with position-group fixed effects built from
the corrected per-pass DM share rather than the coarse grouping.

## B. Problems that weaken the case but probably do not reverse it

B1. No baseline comparison. We never show that the policy adds anything
over simpler versions: chosen EV alone; chosen EV minus the mean EV of
all options; an xT-style location value added. If a simple version does
as well on the outcome tests, the complexity is not earning its place.

B2. Literature positioning is missing. Closest prior work includes risk
and reward pass models from tracking data (Power et al., KDD 2017),
expected possession value (Fernandez, Bornn and Cervone), action-value
frameworks (xT, VAEP) and StatsBomb's own on-ball value. An SSAC
reviewer will ask what is new. Candidate answers: open 360 data,
decision measured against a learned typical choice, a pre-registered
falsification battery, and an out-of-population holdout. This needs a
real literature check, not memory.

B3. Missing controls in outcome regressions: opponent strength and game
state (score, minute). Leading teams pass differently.

B4. No sensitivity analysis on engine v5: lookahead horizon (5/10/15
actions), grid resolution, softmax temperature, policy restriction
thresholds (set on the OLD coordinates, disclosed but never revisited).

B5. xG H-O2 over-control. xA is built from the same shots that make xG,
so "Decision does not add to xG beyond xA" may partly be controlling for
the outcome itself. Worth one sentence and a version without xA.

B6. Multiple comparisons in naming players. 111 deep midfielders with
90% intervals; the two named players need a statement of how many
separations chance alone would produce under the fitted model.

B7. Visibility. 360 frames show only players in camera view; the
defensive line, offside rule and marking features are all computed on
visible players. Quantified for G1 (Task 25) but not for the player
tables: players in deeper roles may be scored on sparser frames.

## C. Scope gaps (state as limitations; not fixable by Oct 1)
- Only passes. The decision to carry, dribble or shoot instead of
  passing is not scored, and for a regista "keep or release" is central.
- No tracking data: no velocities, body orientation or off-ball runs.
- Sample: 299 matches, mostly tournaments; most players have 100-500
  passes. Deep-midfield separation is limited by this.
- The holdout is women's international football, a different
  population; it is a strong replication but not like-for-like.
- Execution and Study C are not computed.

## D. Product and reproducibility
D1. No single command reproduces engine v5 from raw data; the chain is
spread across versioned scripts (_v2 ... _v8). A from-scratch rerun
reproducing BENCHMARK-v5 exactly has never been done.
D2. No data-invariant tests. A test such as "the opponent keeper sits
near x = 120 in shot frames" would have caught the direction bug in
Task 1. Add a small test suite of such invariants.
D3. Records are behind: JOURNAL, DECISIONS (D-016 onward), CHAT-HANDOFF
do not cover Tasks 22-29.
D4. No worked example figure: one real pass with its option surface,
chosen option and typical choice. This is the single most persuasive
thing a reader can see.
D5. Units are hard to read ("0.27 per 100 passes"). Translate into
net goal probability per match for a typical deep midfielder.

## Suggested order for the 2-3 days (author decides)
1. Freeze the benchmark (Task 31). Done first, cheap.
2. Diagnostics only, no engine change: A2 (zero point by zone), A3
   (incomplete-pass share), A4 (cross-fitted player tables), A5
   (within-role reliability), B1 (baselines), A1 (out-of-match test).
   One task; everything reported against BENCHMARK-v5.
3. From those results, choose at most two engine fixes (likely A3
   and A2), each pre-specified, then one full re-validation.
4. Literature check (B2), worked-example figure (D4), invariant tests
   (D2), records (D3) in parallel.
5. Final holdout use on the final candidate only.

## Addendum 2026-09-28 — B2 checked, and it is serious
A quick literature search found work that already defines our core
metric. KU Leuven's "Creative Decision Rating" (CDR), built on
StatsBomb 360 data (2021/22 Premier League), scores each pass as the
difference between the expected value of the chosen option and the
predicted typical pass, using a destination-likelihood model, a
long-term reward model and a pass-success model -- the same three
components as our Decision. Other 360-based work scores counterfactual
pass options for risk and reward (an Erasmus master's thesis with rDP /
RVE decision parameters; a 37-match Barcelona study with rDP / gDP; an
"Opportunity-Adjusted Risk Taking" metric), and Power et al. (KDD 2017)
did risk and reward from tracking data.
Consequence: "we build a decision model" is NOT the contribution and
must not be presented as new. The candidate contributions are what
surrounds the metric: a pre-registered falsification battery for such
metrics; the finding that team-relative coordinates were silently
double-flipped (and that the broken version reached the opposite
conclusion), which is a warning for anyone building on 360 data;
cross-fitted outcome validation with an out-of-population holdout;
reliability and "does it travel" analysis; and the within-role
(deep midfield) analysis with honest uncertainty. The full literature
check (read CDR in full; what did they validate, and how?) is a
priority item.
