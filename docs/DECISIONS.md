# Decisions Log

Append-only. Newest at the bottom. Never edit or delete past entries —
if a decision is reversed, add a new entry that says so and links back.

Only record decisions handed down by the research lead. Questions and
proposed changes go in the relevant results page instead.

Format:

## D-000 — <short title>
Date:
Decision:
Reason:
Alternatives rejected:
Reversible? (yes/no — and what it would cost to reverse)

---

## D-001 — New repo for Regista 2
Date: 2026-09-18
Decision: Regista 2 lives in a new repo, private until Sep 28, then
public for the SSAC submission. Regista 1 is kept untouched and used
as a reference implementation to import from.
Reason: The SSAC repo will be judged. Regista 1's exploratory history
would weaken it.
Alternatives rejected: Continuing in the Regista 1 repo.
Reversible? Yes, cheaply, before publication.

## D-002 — Scope cut for SSAC
Date: 2026-09-18
Decision: Pillar 5 (role discovery) and the off-ball availability
extension are cut from the SSAC work. Pillars 1-4 only.
Reason: 13 days to abstract, 9 weeks to full paper, solo author.
Alternatives rejected: Attempting all five pillars.
Reversible? Yes — they return only if Phase 3 finishes early.

## D-003 — Modeling constrained to local hardware
Date: 2026-09-18
Decision: All models must train on an M4 MacBook Pro with 16GB RAM.
No large transformer training.
Reason: No GPU cluster or cloud budget.
Alternatives rejected: Transformer-based credit assignment as in
Regista 1.
Reversible? Only with compute funding.

## D-004 — Results page convention
Date: 2026-09-18
Decision: The results template lives at docs/results/TEMPLATE.md.
Results pages are docs/results/NN-name.md. docs/RESULTS_TEMPLATE.md
is deleted.
Reason: Matches the standing routine already in CLAUDE.md.
Alternatives rejected: A separate top-level template file.
Reversible? Yes.

## D-005 — PFF data dropped from SSAC scope
Date: 2026-09-19
Decision: PFF FC World Cup 2022 tracking is dropped from all SSAC work.
No PFF-derived number appears in the abstract, paper, or repo.
Reason: Pillar 2 is cut (57% of PFF player-positions are ESTIMATED, so
PFF is not ground truth; plus prior art). PFF's license is unresolved.
Alternatives rejected: Waiting on a licensing answer from PFF.
Reversible? Yes, but only with an explicit written license from PFF.

## D-006 — Repo ships code, not raw data
Date: 2026-09-19
Decision: The public SSAC repo contains source code, download scripts,
and derived metric outputs. No raw third-party data is redistributed.
Reason: StatsBomb's full terms beyond the README were not verified.
Derived outputs plus scripts satisfy SSAC's open-source requirement.
Alternatives rejected: Redistributing raw StatsBomb data.
Reversible? Yes, if StatsBomb's terms are confirmed permissive.

## D-007 — Sample definition
Date: 2026-09-19
Decision: Men's competition-seasons with StatsBomb 360 coverage only.
Women's competitions are excluded from the market analysis because
market valuation coverage is too sparse to support a pricing test.
Reason: ~280 matches, wide club/league variation for the pricing model.
Alternatives rejected: All 426 360-matches; single-league sample.
Reversible? Yes — women's competitions may return for non-market
analyses in the full paper.

## D-008 — Metric frozen before market join
Date: 2026-09-19
Decision: The decision-quality metric is finalized, committed, and
hashed BEFORE any market valuation data is loaded or joined.
Reason: Prevents tuning the metric until the market result looks good.
Alternatives rejected: Building both in parallel.
Reversible? No. Once the join happens, this protection is spent.

## D-009 — Pillar 4 is the SSAC headline
Date: 2026-09-19
Decision: Headline claim is whether the transfer market prices decision
quality separately from execution. Pillar 2 is cut.
Reason: Literature check found off-screen imputation and its downstream
effects already published; the decision-vs-execution pricing test
appears open.
Alternatives rejected: Pillar 2 (visibility calibration).
Reversible? No, not before Oct 1.

## D-010 — Possession-value model training scope
Date: 2026-09-19
Decision: The Task 01 possession-value model trains on the full event
stream (all action types) of the 299-match, 8-competition-season study
sample only. Training on the same matches later used for player
evaluation is intentional, not leakage — the model estimates a
game-state property, not a player-level target. The match-level
held-out split required elsewhere applies only to the pass-success
model (Step 2), where leakage would actually matter.
Reason: All 3,961 StatsBomb open-data matches would add era and
competition heterogeneity (matches back to 1973) far outside the
study's own sample, and would require chunked/on-disk training instead
of an in-memory pipeline, for a training-volume gain that doesn't serve
the study's scope.
Alternatives rejected: Training on all 3,961 StatsBomb matches.
Reversible? Yes, as a robustness check.

## D-011 — Chosen-candidate identification via angle-matching
Date: 2026-09-19
Decision: StatsBomb 360 freeze frames carry no player identity, so the
actual pass recipient cannot be read directly off a freeze-frame row.
The chosen candidate is identified by matching: compute the bearing
from passer to pass_end_location and the bearing from passer to each
visible teammate; the teammate with the smallest bearing difference is
the match, accepted only if that difference is <= 15 degrees; rejected
as AMBIGUOUS if a second teammate is within 10 degrees of the best
match's bearing AND within 5m of its position. Unmatched and ambiguous
passes are dropped from the decision analysis, with both rates reported
as a share of eligible passes, and separately for completed vs
incomplete passes. Once matched, the chosen candidate's features are
computed from its own freeze-frame location exactly like every unchosen
candidate — pass_end_location is used only for this matching step and
for computing Execution in Step 6, never as a feature in Steps 1, 2, or
5.
Reason: A synthetic chosen-candidate built directly from
pass_end_location was rejected because pass_end_location is post-hoc
information (only known once the pass has already happened) and would
make the chosen and unchosen candidates non-comparable — the model
could learn to distinguish them without learning anything about
decision quality.
Alternatives rejected: Synthetic chosen candidate built directly from
pass_end_location, with unchosen candidates drawn from the freeze frame.
Reversible? Yes, as a robustness check.

## D-012 — Research question pivot
Date: 2026-09-20
Decision: The headline moves from market pricing to decision-making
itself: Study A (sport-wide blind spots), Study B (player vs system),
Study C (choice vs execution). The market test becomes a scoping note.
Reason: The market test was powered only for ~22% effects per SD (n=125
player-seasons). The original research question was about measuring
registas, not their market price. The new studies use pass-level data
where sample size is not the binding constraint.
Alternatives rejected: More market work; women's replication (cut for
time); lowering the pass threshold (buys power with noise).
Reversible? No, not before Oct 1.

## D-013 — Preregistration v2
Date: 2026-09-20
Decision: docs/specs/analysis-plan-v2.md governs all new analysis. It
was written before any situation-level data was joined.
Reversible? Only by dated amendment.

## D-014 — Discovery / confirmation split
Date: 2026-09-20
Decision: Study A is run on a match-level 50/50 split, seed 20260920,
committed before any Study A statistic exists.
Reversible? No.
