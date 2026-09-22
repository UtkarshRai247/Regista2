# Task 08: Study B corrections, Study C, reliability audit

Date: 2026-09-22
Status: COMPLETE

## Per-section checklist (per brief docs/specs/task-08-studies-b-c.md)
- Step 0 (commit Amendment v2-5 alone): COMPLETE
- Part 1.1 (bootstrap_by_player fix + unit test): COMPLETE
- Part 1.2 (corrected B4/B5a intervals vs. Task 07's superseded ones): COMPLETE
- Part 1.3 (PH-B1, PH-B2, PH-B3): COMPLETE
- Part 1.4 (v2-5.4 claim-rule verdicts): COMPLETE
- Part 1.5 (v2-5.5 design calculation): COMPLETE (Tier 2 NOT ALLOWED, so computed)
- Part 2 (Study C): COMPLETE
- Part 3 (reliability audit): COMPLETE
- Hard rules (fixed definitions/thresholds/claim rules, full unsorted
  tables, no interpretation, no memory writes, JOURNAL.md untouched, no
  cross-fitting): COMPLETE

## 1. Headline
The Amendment v2-5.1 bootstrap fix materially changes Study B's
conclusion: the corrected 95% CI for S (primary fit) is **[0.363,
0.573]**, versus Task 07's superseded (buggy) **[0.626, 0.785]** — the
corrected lower bound no longer clears 0.5, so **Tier 1 is NOT ALLOWED**
(and Tier 2 therefore isn't either). Study C finds a choice-share median
of **0.498** (95% CI [0.362, 0.688]) — decision and execution contribute
roughly equally to the real spread in value added, not decisively either
way. The reliability audit shows Decision needs >=200 eligible passes to
reach 0.70 median split-half reliability; Execution never reaches 0.70
at any threshold up to 500.

## 2. What I did
Reproduce with: `.venv/bin/python src/decision_engine/task08_studyb_corrections.py`,
then `.venv/bin/python src/decision_engine/task08_study_c.py`, then
`.venv/bin/python src/decision_engine/task08_reliability_audit.py`
(after Step 0's commit, done separately — see Section 7).

- **Step 0**: committed `docs/specs/analysis-plan-v2.md` (Amendment v2-5
  alone, 67 lines, already present on disk) in commit `0943000`
  (`sha256 = c846afc02666ee44a32b4c43f77f01ec7605600186ad6e45a283e1fbce345b9e`).
- **Part 1.1**: added a corrected `bootstrap_by_player` to
  `src/decision_engine/reml_crossed.py` (not edited into Task 07's
  historical `task07_study_b.py` — v2-5.1 says that script's intervals
  are *superseded*, not deleted). The bug: Task 07's version kept a
  resampled unit's real `player_id`, so `_factorize` pooled two draws of
  the same player into one inflated group instead of two independent
  draws of the player-level random effect. Fix: each of the P drawn
  *slots* gets a synthetic id (`f"{player_id}__{slot}"`); team-context
  ids are untouched. Added a unit test (in `reml_crossed.py`'s
  `__main__` self-check) that forces a specific player to be drawn twice
  and asserts the buggy grouping collapses to 2 distinct "players" while
  the fixed grouping correctly keeps 3 — verified passing before this
  function was used anywhere else (Section 8).
- **Part 1.2**: reused `data/processed/study_b_units.parquet` (Task 07's
  exact stage-1 unit table, unchanged) so the corrected CIs are an
  apples-to-apples comparison against the same point estimates. Refit
  B4 (primary, 1,701 units) and B5a (position-matched refit, 1,668 units,
  same exclusion rule as Task 07) with the corrected bootstrap, 1,000
  draws each.
- **PH-B1**: added position-group dummy fixed effects
  (`position_group`'s mode per unit; Midfielder is the reference).
  Discovered zero GK units exist in this data (goalkeepers were excluded
  from eligible passes all the way back in Task 01's `options.py`
  eligibility filter, `position != "Goalkeeper"`) — an all-zero `is_GK`
  dummy makes the design matrix exactly singular, so it was dropped
  (unidentifiable, not a discretionary choice) and only `is_Defender`/
  `is_Forward` were fit; see Section 5.
- **PH-B2**: rebuilt pass-level Decision (reusing Task 07's
  `compute_decision_per_pass` + `decompose.match_competition_lookup`,
  without redoing the position-lookup pass, which this check doesn't
  need). For each side (club, international) separately: pooled a
  mover's passes on that side across all their qualifying contexts on
  that side, ran 100 random half-splits, Spearman-Brown-corrected the
  across-mover half-mean correlation, took the median as that side's
  reliability. `r_true = r_obs / sqrt(rel_club * rel_intl)`, `r_obs`
  recomputed the same pass-count-weighted way as Task 07's B5b. 1,000-draw
  bootstrap resampling movers, 20 splits per draw (disclosed, for
  speed), both reliabilities and `r_obs` recomputed fresh inside each
  draw; capped `r_true` to [-1, 1] and tracked the capped share.
- **PH-B3**: refit restricted to the 345 players with 2+ units (all
  their units, 814 units total), same corrected bootstrap.
- **Part 1.4**: applied the v2-5.4 tier rules exactly as written, using
  the numbers above — no adjustment.
- **Part 1.5**: since Tier 2 is NOT ALLOWED, computed the v2-5.5 design
  calculation: required mover count for 80% power (two-sided alpha 0.05)
  to detect true correlations of 0.3 and 0.5 at the *observed*
  attenuation (Fisher z power formula), and international passes per
  mover needed to raise `rel_intl` to 0.5 and 0.7 (Spearman-Brown
  projection from the observed mean international passes per mover).
- **Part 2 (Study C)**: ran `decompose.build_per_pass_table` in full
  (all 299 matches) to get per-pass Decision AND Execution — Task 07
  deliberately avoided this (it only needed Decision), but Study C needs
  both. Restricted to the 138 player x competition-season units with
  >=200 eligible passes (verified this count against
  `player_season_metrics.parquet` — exact match). 100 random split-halves
  (seed 20260920): per split, cross-half covariances across the 138
  units give true var(Decision), true var(Execution), and the averaged
  cross-covariance (plan 5.2's exact formulas); choice share = true
  var(Decision) / [true var(Decision) + true var(Execution)]. Also
  computed the raw (uncorrected, non-split) share directly from each
  unit's own overall mean. Bootstrap: 1,000 draws resampling the 138
  units (ordinary bootstrap — no crossed-effects identity issue here,
  unlike Study B), 20 splits per draw (disclosed), median choice share
  per draw, then the 1,000 draws' 95% percentile interval. Checked plan
  5.3's failure condition against the 100 primary splits' distribution
  of true var(Execution).
- **Part 3 (reliability audit)**: extracted per-pass completion,
  progressive, and xA flags for all 299 matches by reusing
  `decompose.compute_reference_metrics`'s exact per-pass formula and
  `PROGRESSIVE_THRESHOLD_M` constant (its logic already computes these
  per pass before aggregating to match sums — confirming the brief's
  STOP condition, "if flags do not exist," does not apply here), then
  restricted to the 171,618 eligible passes (exact match). Joined
  Decision/Execution (same `build_per_pass_table` call, shared with
  Part 2's need for it — computed once). All 5 metrics computed on the
  same population (eligible passes) for internal consistency, since
  Decision/Execution only exist there and the unit's pass-count
  thresholds are "eligible passes" throughout this project (see Section
  4). For each of 5 metrics x 7 thresholds (100/150/200/250/300/400/500):
  100 random splits, Spearman-Brown-corrected across-unit correlation,
  median and 5th-95th percentile, generalizing
  `task01b_diagnostics.repeated_split_reliability`'s pattern (which did
  the same thing for one metric at one threshold).

## 3. Numbers

### Part 1 — Study B corrections

**B4/B5a: corrected vs. Task 07 (superseded) intervals**

| Fit | n units | n players | var_player | var_team | S (point, unaffected by the bug) | Corrected 95% CI | Task 07 superseded 95% CI |
|---|---|---|---|---|---|---|---|
| B4 (primary) | 1,701 | 1,232 | 4.9024e-7 | 2.5967e-7 | 0.6537 | **[0.3631, 0.5727]** | [0.6263, 0.7846] |
| B5a (position-matched refit, 33 units excluded) | 1,668 | 1,219 | 4.8315e-7 | 2.5807e-7 | 0.6518 | **[0.3540, 0.5686]** | [0.6305, 0.7854] |

**PH-B1** (position-group fixed effects; GK dropped, 0 units — see
Section 5): var_player=4.6293e-7, var_team=2.6273e-7, S=0.6379, 95% CI
**[0.3513, 0.5560]**. Position-group counts among the 1,701 units:
Defender 804, Midfielder 614, Forward 283, GK 0.

**PH-B2** (disattenuated mover correlation, n=132 movers):
rel_club=0.5007, rel_intl=0.5522 (both from 100 primary splits, median
Spearman-Brown-corrected), r_obs=0.0534 (same value as Task 07's B5b,
recomputed fresh here), r_true (disattenuated) = **0.1015**, 95% CI
**[-0.2476, 0.5263]** (1,000-draw bootstrap, 20 splits/draw, 0% of draws
capped). Mean international passes per mover: 148.25.

**PH-B3** (players with 2+ units only, all their units): n=814 units,
345 players. var_player=4.0545e-7, var_team=2.9449e-7, S=0.5793, 95% CI
**[0.2432, 0.5175]**.

**v2-5.4 claim-rule verdicts** (fixed rule, applied mechanically):

| Tier | Conditions | Result |
|---|---|---|
| Tier 1 | corrected B4 CI lower bound > 0.5 (0.3631 — **fails**) AND PH-B1 CI lower bound > 0.5 (0.3513 — **fails**) | **NOT ALLOWED** |
| Tier 2 | Tier 1 (fails) AND PH-B2 positive with CI excluding zero (r_true=0.1015 > 0 but CI includes zero — **fails**) AND PH-B3 CI lower bound > 0.5 (0.2432 — **fails**) | **NOT ALLOWED** |

**v2-5.5 design calculation** (computed because Tier 2 is NOT ALLOWED),
using PH-B2's rel_club=0.5007, rel_intl=0.5522, mean international
passes/mover=148.25:

| True correlation | Effective (attenuated) correlation | Movers needed for 80% power (two-sided, alpha=0.05) |
|---|---|---|
| 0.3 | 0.1577 | 314 |
| 0.5 | 0.2629 | 112 |

| Target rel_intl | Spearman-Brown k (relative to current) | International passes/mover required |
|---|---|---|
| 0.5 | 0.811 | 121 |
| 0.7 | 1.892 | 281 |

(rel_intl is already 0.5522, above 0.5, hence k<1 for that target — the
current average pass count already exceeds what 0.5 alone would need;
0.7 requires roughly 1.9x the current average.)

### Part 2 — Study C (n=138 units, 100 primary splits, seed 20260920)

| Quantity | Value |
|---|---|
| True var(Decision), median | 5.1885e-7 |
| True var(Execution), median [5th-95th pct] | 5.1773e-7 [3.4087e-7, 6.5534e-7] |
| True covariance, median | 1.2759e-7 |
| **Choice share, median [5th-95th pct]** | **0.4984 [0.4384, 0.6063]** |
| Choice share, 95% bootstrap CI (1,000 draws, 20 splits/draw, resampling units) | **[0.3621, 0.6883]** |
| Raw (uncorrected) share | 0.3927 (raw var(Decision)=6.9225e-7, raw var(Execution)=1.0706e-6) |
| Plan 5.3 failure condition (true var(Execution) negative, or interval spans zero widely) | **Not triggered** (median and both the 5th/95th split percentiles and the primary distribution stay positive) |

The raw share (0.393) is lower than the noise-corrected median (0.498),
consistent with the plan's expectation that measurement noise alone
inflates execution's apparent importance.

### Part 3 — Reliability audit (5 metrics x 7 thresholds, 100 splits each, unit = player x competition-season, population = eligible passes)

| Threshold | n units | Completion | Progressive | xA/pass | Decision | Execution |
|---|---|---|---|---|---|---|
| 100 | 364 | 0.737 [0.695, 0.770] | 0.751 [0.712, 0.775] | 0.513 [0.405, 0.590] | 0.649 [0.594, 0.692] | 0.392 [0.301, 0.484] |
| 150 | 226 | 0.771 [0.727, 0.811] | 0.793 [0.746, 0.826] | 0.580 [0.490, 0.648] | 0.668 [0.605, 0.714] | 0.402 [0.257, 0.529] |
| 200 | 138 | 0.830 [0.775, 0.857] | 0.855 [0.820, 0.892] | 0.726 [0.635, 0.788] | 0.750 [0.670, 0.804] | 0.472 [0.356, 0.580] |
| 250 | 95 | 0.881 [0.836, 0.910] | 0.863 [0.829, 0.897] | 0.768 [0.675, 0.841] | 0.778 [0.715, 0.839] | 0.582 [0.466, 0.677] |
| 300 | 75 | 0.910 [0.884, 0.937] | 0.896 [0.858, 0.925] | 0.799 [0.709, 0.857] | 0.793 [0.738, 0.853] | 0.646 [0.512, 0.737] |
| 400 | 55 | 0.937 [0.909, 0.958] | 0.906 [0.862, 0.938] | 0.775 [0.665, 0.860] | 0.843 [0.789, 0.896] | 0.589 [0.408, 0.732] |
| 500 | 45 | 0.948 [0.922, 0.965] | 0.874 [0.822, 0.914] | 0.817 [0.712, 0.887] | 0.878 [0.813, 0.926] | 0.637 [0.432, 0.760] |

(Cells are median [5th, 95th percentile] of the Spearman-Brown-corrected
split-half correlation across the 100 splits.)

**Lowest threshold reaching median >= 0.70:**

| Metric | Lowest threshold |
|---|---|
| Completion rate | 100 |
| Progressive-pass rate | 100 |
| xA per pass | 200 |
| Decision | 200 |
| Execution | **not reached** (highest observed median: 0.646 at threshold 300) |

Progressive's median at threshold 500 (0.874) is slightly below its
values at 300 (0.896) and 400 (0.906) — non-monotonic, most likely
sampling noise from the smaller unit count (45) at that threshold;
reported exactly as computed, not smoothed.

## 4. Deviations from the brief

1. **PH-B1's `is_GK` dummy was dropped**, not fit alongside
   `is_Defender`/`is_Forward` as a literal reading of "position-group
   fixed effects" might suggest. This is not a discretionary deviation:
   zero units have `position_group == "GK"` (goalkeepers are excluded
   from eligible passes since Task 01), so an all-zero dummy column
   makes the design matrix exactly singular — no fixed effect can be
   estimated for a group with zero observations. Confirmed via
   `np.linalg.matrix_rank`.
2. **All 5 reliability-audit metrics were computed on the eligible-pass
   population**, not each player's full raw passing activity (which is
   what `decompose.compute_reference_metrics` normally aggregates for
   `player_season_metrics.parquet`'s reference columns). The plan doesn't
   explicitly state this population choice for completion/progressive/xA;
   I used the eligible-pass population for internal consistency, since
   Decision/Execution only exist there and the audit's own pass-count
   thresholds are "eligible passes" everywhere else in this project.
3. Both bootstrap procedures added in this task (PH-B2's mover
   resampling, Study C's unit resampling) use 20 splits per draw instead
   of the primary analysis's 100, exactly as the brief itself specifies
   ("20 splits per draw, disclosed") — not a deviation, restated here for
   visibility since it affects precision of those particular intervals.

No other deviations. Every threshold, formula, and the v2-5.4 claim
rules were applied exactly as specified.

## 5. Problems and surprises

- **Zero goalkeeper units** (Section 4.1) — a real, notable fact about
  the sample: no player ever appears in Study B's 1,701 units as a
  goalkeeper, because Task 01's eligibility filter excludes goalkeeper
  passes entirely. This has been true since Task 01 but only became
  operationally visible here, when PH-B1 tried to fit a fixed effect for
  a group that doesn't exist in this data.
- **What the Tier-1-NOT-ALLOWED finding invalidates, and what it
  doesn't** (per CLAUDE.md item 6): Task 07's results page (2026-09-21)
  reported Gate E as PASS and implied Study B "could lead the paper."
  That characterization is now superseded specifically on the *claim*
  question — the corrected CI [0.3631, 0.5727] straddles 0.5, so the
  plain-language claim "most systematic variation in decision quality
  sits with players" cannot be made under the v2-5.4 rule, in either the
  primary fit or PH-B1. This does NOT mean the point estimate (S≈0.65)
  is wrong or that players contribute *less* than teams — the point
  estimate is unaffected by the bug and still sits above 0.5 in every
  variant computed (B4, B5a, PH-B1, PH-B3 all give S in [0.579, 0.654]).
  What it invalidates is the *confidence* behind that number: at this
  sample's precision, the data cannot rule out team-context variance
  being as large as, or larger than, player variance. This is a
  precision problem, not a sign-reversal, and the paper should say so
  plainly rather than either asserting the Tier-1 claim or discarding
  the point estimate.
- **PH-B2's disattenuated correlation (0.1015) has a very wide CI
  ([-0.2476, 0.5263])** that includes both Task 07's raw observed value
  (0.0534) and values several times larger — at n=132 movers with
  side-reliabilities near 0.5, this check cannot distinguish "no real
  travel of decision quality between systems" from "a moderate real
  effect obscured by noise." The v2-5.5 design calculation quantifies
  this directly: detecting a true correlation of 0.3 at the observed
  reliabilities would need roughly 314 movers (this sample has 132).
- Nothing else was missing, broken, or malformed.

## 6. Questions for the research lead
None. Every definition, threshold, and claim rule in Amendments v2-3
through v2-5 and plan sections 4-6 was implementable exactly as written.

## 7. Files produced
- `src/decision_engine/reml_crossed.py` — extended with the corrected
  `bootstrap_by_player` and its unit test (existing file, not new).
- `src/decision_engine/task08_studyb_corrections.py` — Part 1 script.
- `src/decision_engine/task08_study_c.py` — Part 2 script.
- `src/decision_engine/task08_reliability_audit.py` — Part 3 script.
- `data/task08_studyb_corrections.json`, `data/task08_study_c.json`,
  `data/task08_reliability_audit.json` — run summaries. Gitignored.
- Git commits made this task: `0943000` (Amendment v2-5). Per CLAUDE.md
  item 9, the remaining new/changed files under `src/`/`docs/` from this
  task (the three new scripts, the `reml_crossed.py` extension, this
  results page, and `docs/JOURNAL.md`, which changed on disk
  independently of this task, same pattern as Tasks 05-07) are committed
  immediately after this page is written; those hashes are reported to
  the user directly, per their explicit instruction not to paste this
  page's contents in the reply.

## 8. Confidence
High on Part 1.1's fix: a direct, mechanical unit test (not an indirect
numeric check) confirms the exact bug mechanism and its correction,
verified passing before the corrected function was used anywhere else.
High on the corrected intervals' direction and magnitude being real
(every corrected CI is both shifted down and wider than its Task 07
counterpart, consistent with a one-directional upward bias from the
bug, not a coincidence). Medium on Study C: the choice-share estimate
is imprecise (CI spans roughly 0.36-0.69) at n=138 units, so "roughly
equal" is a fair summary but not a precise split. High on the
reliability audit's mechanics (it directly generalizes an existing,
already-used pattern from Task 01b) — the substantive finding that
Execution never reaches 0.70 reliability even at 500 passes is itself
informative for how Study C's own noise-correction should be read: Execution
is the noisier of the two ingredients feeding Study C's choice-share
estimate, which is consistent with that estimate's own wide interval.
