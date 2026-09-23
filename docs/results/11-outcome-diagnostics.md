# Task 11: Outcome diagnostics (Amendment v2-8)
Date: 2026-09-22
Status: COMPLETE

## Per-section checklist (per brief docs/specs/task-11-outcome-diagnostics.md)
- Step 0 (commit Amendment v2-8 alone, record hash + SHA-256): COMPLETE
- Step 1 (descriptive correlation matrix): COMPLETE
- Step 2 (PH-O1/PH-O2 vs. xG/goals, clustered by team context): COMPLETE
- Step 3 (PH-O3, possession level): COMPLETE
- Step 4 (apply v2-8.4 claim rule): COMPLETE
- Hard rules (H-O1/H-O2 not recomputed or restated as new results, no
  new controls/outcomes, full reporting, no interpretation for the
  paper, no memory writes, JOURNAL.md untouched): COMPLETE

## 1. Headline
The compositional explanation in v2-8.2 is **not supported**: controlling
for zone mix and pressure share (PH-O1), and then for team-context fixed
effects (PH-O2), does not flip or shrink the negative Decision-outcome
association from Task 10 — it stays significantly negative in all 4
regressions (xG and goals, PH-O1 and PH-O2), if anything slightly larger
in magnitude under PH-O2. At the possession level (PH-O3, n=20,030), the
picture is mixed: higher mean Decision is significantly associated with
a HIGHER probability that the possession ends in a shot (+0.0119
percentage points per SD, p<0.001), but has no significant association
with the possession's own xG (p=0.236). Per the fixed v2-8.4 rule, since
PH-O2 is not positive, the claim "decision quality is associated with
chance creation" is **NOT ALLOWED**. The metric's relationship with real
match outcomes is genuinely mixed across levels of aggregation, not
resolved by these diagnostics.

## 2. What I did
Reproduce with: `.venv/bin/python src/decision_engine/task11_outcome_diagnostics.py`.

- **Step 0**: committed `docs/specs/analysis-plan-v2.md` alone (Amendment
  v2-8, 51 new lines) as commit `3232e28`; new file SHA-256 =
  `51f482b6c047e6d585f9aef1a5f7b7bfbd792c70968242f16bc436b80920f39e`.
  Separately committed `docs/JOURNAL.md`'s pending Task 10 retrospective
  entry (research lead's own edit, not touched by me) as `5b31b5a`.
- **Step 1**: extended Task 10 Part B's 598-row team-match frame
  (`task10_partB_outcome.build_team_match_units`/`add_decision`/
  `add_possession_share`/`add_xg`, imported unchanged) with two new
  columns from `passes_situation.parquet`: zone shares (final/middle/
  defensive share of that team's eligible passes) and pressure share
  (share with `under_pressure=True`). Computed the full 7x7 correlation
  matrix on the 583 rows with computable Decision (same 583, same 15
  missing rows/causes as Task 10 Part B — not re-investigated).
- **Step 2**: fit PH-O1 (H-O1's own predictors + final_share +
  defensive_share + pressure_share, middle_share as reference) and PH-O2
  (PH-O1 minus the competition-season dummies, plus team-context fixed
  effects — see the design note below) for xG and goals, clustered by
  team context, reusing `task10_partB_outcome.fit_ols` unchanged. Pulled
  Task 10's own H-O1/H-O2 numbers from `data/task10_partB_outcome.json`
  for the comparison table — did not recompute them.
  **Design note (disclosed, not silently chosen)**: v2-8.3 says PH-O2 is
  "PH-O1 plus team-context fixed effects." A team context (team x
  competition x season) strictly nests competition-season, so literally
  keeping both dummy sets makes the design matrix exactly collinear.
  PH-O2 was fit with the finer team-context FE replacing the coarser
  competition-season FE (every other PH-O1 predictor kept), the only way
  to get a non-degenerate design.
- **Found and fixed a rank-deficiency bug before trusting PH-O2's
  numbers**: building team-context dummy columns on the full 598-row
  frame (before dropping the 15 rows with no Decision) left 4 dummies
  — Toronto FC, Cincinnati, Charlotte (all MLS 2023, matches
  3877115/3877170/3877194), and Borussia Dortmund (Bundesliga, matches
  3895158/3895309) — with **zero remaining observations** after the
  dropna, since every one of those teams' rows in the 598 happened to be
  among the 15 with no computable Decision. An all-zero dummy column
  made the design matrix rank-deficient (verified via SVD: rank 164 of
  168 parameters, condition number 1.8e18) — `statsmodels` still
  produced numbers via its pseudo-inverse fallback, silently, with a
  `SingularMatrixWarning` this script's top-level `warnings.filterwarnings
  ("ignore")` was suppressing. Fixed by building all dummy columns only
  on the 583-row analysis sample (rank now exactly matches the parameter
  count, condition number 281, no warnings). `decision_z`'s coefficient
  barely moved (-0.1759 before the fix vs. -0.1759 after) since the
  degenerate columns weren't collinear with `decision_z` itself, but the
  fit is now numerically sound rather than accidentally close.
- **Step 3**: built open-play possessions from the frozen per-pass table
  (`decompose.build_per_pass_table`) joined to each match's raw events'
  `possession`/`possession_team`/`type`/`shot_statsbomb_xg` fields.
  Grouped eligible passes by `(match_id, possession)`, kept groups with
  >=3 eligible passes. **Verified before trusting**: `possession_team`
  is constant within every possession id (checked on a sample match,
  136/136 groups), but 2.9%-ish of individual eligible passes (6,078 of
  ~171,618 project-wide) belong to a team OTHER than that possession's
  attributed team — a stray opponent touch (e.g. a loose-ball
  interception that gets immediately lost) that StatsBomb still tags
  with the same possession id. These were excluded from that
  possession's own statistics (mean Decision, pass count, starting
  zone), and Shot events were likewise filtered to `team ==
  possession_team`, so a possession's outcome (a)/(b) reflects only its
  attributed team's own passes and shots.
  Fit (a) `sm.Logit` for `ends_in_shot` and (b) `sm.OLS` for
  `possession_xg`, both on Decision_z + n_passes + starting-zone dummies
  (middle as reference) + team-context FE, clustered by match.
- **Found and fixed a second numerical problem**: the logistic fit
  (a) failed to converge on the first attempt (`ConvergenceWarning`).
  Diagnosed as complete separation: Nashville SC's team-context (MLS
  2023) had **zero** of its 12 qualifying possessions end in a shot,
  making that one fixed-effect coefficient want to diverge to
  -infinity. This is the same class of problem, and the same fix, as
  Task 08's PH-B1 all-zero `is_GK` dummy
  (`docs/results/08-studies-b-c.md`): dropped that one degenerate
  team-context (12 of 20,042 possessions, 0.06%) before fitting either
  (a) or (b), and reported exactly which one and how many.
- **Step 4**: applied v2-8.4 mechanically — ALLOWED requires PH-O2(xG)
  AND PH-O3(a) both positive with CI excluding zero.

## 3. Numbers

### Step 1 — correlation matrix (n=583 team-matches with computable Decision)

| | mean_decision | final_share | middle_share | defensive_share | pressure_share | possession_share | xg |
|---|---|---|---|---|---|---|---|
| mean_decision | 1.0000 | -0.1275 | 0.0760 | 0.0488 | -0.2272 | 0.3413 | 0.0213 |
| final_share | -0.1275 | 1.0000 | -0.4651 | -0.5108 | 0.0901 | -0.2946 | -0.1352 |
| middle_share | 0.0760 | -0.4651 | 1.0000 | -0.5235 | -0.1721 | 0.4539 | 0.1555 |
| defensive_share | 0.0488 | -0.5108 | -0.5235 | 1.0000 | 0.0804 | -0.1573 | -0.0210 |
| pressure_share | -0.2272 | 0.0901 | -0.1721 | 0.0804 | 1.0000 | -0.3866 | -0.1700 |
| possession_share | 0.3413 | -0.2946 | 0.4539 | -0.1573 | -0.3866 | 1.0000 | 0.3839 |
| xg | 0.0213 | -0.1352 | 0.1555 | -0.0210 | -0.1700 | 0.3839 | 1.0000 |

Note: mean_decision's raw bivariate correlation with xg is essentially
zero (0.0213) — the significant NEGATIVE relationship in Task 10's H-O1
and this task's PH-O1/PH-O2 only appears after conditioning on
possession_share (r=+0.34 with Decision, r=+0.38 with xG) and other
controls; it is not visible in the simple correlation.

### Step 2 — PH-O1 and PH-O2 vs. Task 10's H-O1/H-O2 (all n=583, clustered by team context)

| Spec | Outcome | n | R² | Decision_z coef | 95% CI | p |
|---|---|---|---|---|---|---|
| H-O1 (Task 10) | xG | 583 | 0.1665 | -0.1381 | [-0.2104, -0.0659] | 0.00018 |
| PH-O1 | xG | 583 | 0.1725 | -0.1532 | [-0.2289, -0.0774] | 0.00007 |
| PH-O2 | xG | 583 | 0.4030 | -0.1759 | [-0.2752, -0.0765] | 0.00052 |
| H-O1 (Task 10) | goals | 583 | 0.1979 | -0.4031 | [-0.5124, -0.2939] | <1e-12 |
| PH-O1 | goals | 583 | 0.2004 | -0.4101 | [-0.5223, -0.2978] | <1e-15 |
| PH-O2 | goals | 583 | 0.3977 | -0.4229 | [-0.5808, -0.2651] | <1e-6 |

(H-O2 is also on record in Task 10 for reference — xG: -0.1241
[-0.1926, -0.0555], p=0.00039; goals: -0.4587 [-0.5761, -0.3414],
p<1e-13 — not repeated in the table above since PH-O1/PH-O2 are the
directly comparable specs here.)

Zone-share and other coefficients (PH-O1 / PH-O2, xG then goals):

| Predictor | PH-O1 xG | PH-O2 xG | PH-O1 goals | PH-O2 goals |
|---|---|---|---|---|
| possession_share | 2.6824 [2.1373, 3.2276] p<1e-20 | 1.1218 [0.1090, 2.1345] p=0.030 | 3.3410 [2.7281, 3.9540] p<1e-25 | 0.9428 [-0.3938, 2.2793] p=0.167 |
| is_home | -0.0293 [-0.1863, 0.1276] p=0.714 | -0.0454 [-0.2221, 0.1313] p=0.615 | 0.0426 [-0.1448, 0.2300] p=0.656 | 0.0313 [-0.1816, 0.2442] p=0.773 |
| final_share | 0.2427 [-0.9869, 1.4722] p=0.699 | 0.6978 [-0.9716, 2.3671] p=0.413 | 1.1326 [-0.8371, 3.1023] p=0.260 | 1.5657 [-1.1881, 4.3196] p=0.265 |
| defensive_share | 1.0816 [-0.1994, 2.3627] p=0.098 | 0.8021 [-0.7702, 2.3744] p=0.317 | 0.9393 [-1.0430, 2.9215] p=0.353 | 0.4890 [-1.8521, 2.8300] p=0.682 |
| pressure_share | -0.9505 [-2.7049, 0.8038] p=0.288 | -1.5305 [-3.8948, 0.8338] p=0.205 | -0.1545 [-1.8754, 1.5665] p=0.860 | -0.3061 [-2.9476, 2.3353] p=0.820 |

None of the zone-share coefficients (final_share, defensive_share)
reach significance at alpha=0.05 in any of the 4 specs — the direct
evidence for v2-8.2's "final-third play mechanically lowers Decision
and raises xG" story is weak-to-absent in this frame, consistent with
Decision_z staying negative and significant regardless.

### Step 3 — PH-O3, possession level (n=20,030 possessions with >=3 eligible passes; 1 degenerate team-context / 12 possessions dropped, see Section 5)

| Outcome | n | Fit stat | Decision_z coefficient | 95% CI | p |
|---|---|---|---|---|---|
| (a) ends_in_shot (logistic, avg. marginal effect) | 20,030 | pseudo-R²=0.0248 | **+0.01194** (probability points per SD) | [0.00546, 0.01842] | 0.00030 |
| (b) possession_xg (OLS) | 20,030 | R²=0.0124 | **-0.00059** (xG per SD) | [-0.00157, 0.00039] | 0.236 |

(a) is positive with CI excluding zero. (b) is not significant (CI
includes zero) and points the same direction as the team-match-level
result.

### Step 4 — v2-8.4 verdict
Rule (fixed): ALLOWED only if PH-O2 (xG) AND PH-O3(a) are both positive
with CIs excluding zero.
- PH-O2 (xG): coefficient -0.1759, CI [-0.2752, -0.0765] — **negative**, condition fails.
- PH-O3(a): marginal effect +0.01194, CI [0.00546, 0.01842] — positive, CI excludes zero, condition holds.

**Verdict: NOT ALLOWED.** Per the rule, the paper states plainly that
the metric does not predict (in fact inversely predicts, at the
team-match level) real chance creation at the levels tested, treating
this as a principal limitation of possession-value-based decision
metrics. Since the compositional diagnostics (Step 2) do not support
the zone-mix explanation, this is not a case of "reports both the
negative result and the compositional explanation" — the compositional
explanation is not supported by these diagnostics, so the negative
team-match-level result stands without that mitigating account, while
the possession-level result (a) shows a positive, significant
association in the opposite direction from the team-match-level one.

## 4. Deviations from the brief
- **None in scope.** H-O1/H-O2 were not recomputed or restated as new
  results (Task 10's own numbers were read from its JSON output only,
  for the comparison table Step 2 explicitly requests). No control or
  outcome beyond v2-8.3's list was added.
- **Disclosed implementation choice, not an invented methodology**:
  PH-O2's team-context FE replaces (rather than supplements) PH-O1's
  competition-season FE, since the two are exactly nested and keeping
  both is not numerically possible (Section 2). This is the only way to
  fit "PH-O1 plus team-context fixed effects" as a well-defined
  regression; flagged in Section 6 in case the research lead intends
  something else by "plus."
- Two possessions-side exclusions, both disclosed and small relative to
  the sample: 6,078 stray opponent passes excluded from possession-level
  statistics (2.9% project-wide across all eligible passes, not 2.9% of
  possessions), and 1 degenerate team-context / 12 possessions (0.06% of
  20,042) dropped for complete separation in the logistic fit. Neither
  changes any reported conclusion (verified: dropping the 12
  possessions moved Decision_z's coefficient by <0.001% in both (a) and
  (b)).

## 5. Problems and surprises
- **The compositional story (v2-8.2) is not supported by these
  diagnostics.** If taken at face value, this invalidates the working
  hypothesis that Task 10's negative Decision-outcome finding was an
  artifact of teams that attack more playing more final-third passes.
  Controlling for zone mix (PH-O1) barely moves the coefficient;
  controlling for team identity itself (PH-O2) makes it slightly MORE
  negative, not less. None of the zone-share coefficients are
  significant. Whatever is driving the negative team-match-level
  association, it does not appear to be simply "where a team played."
- **The result reverses sign at the possession level for one of two
  outcomes.** PH-O3(a) (ends_in_shot) is significantly POSITIVE — the
  opposite direction from the team-match-level H-O1/H-O2/PH-O1/PH-O2
  results. PH-O3(b) (possession_xg) is directionally negative like the
  team-match results but not significant. This is a genuinely mixed
  picture across levels of aggregation (team-match vs. possession), not
  a case where one diagnostic cleanly confirms or refutes the other.
  Taken at face value, this would invalidate any single, simple story
  about the metric's relationship with chance creation — the answer
  appears to depend on the unit of analysis.
- Two numerical failures were caught before trusting any numbers: a
  silently-degenerate design matrix in PH-O2 (Section 2) and a
  non-converging logistic fit in PH-O3(a) (Section 2), both from the
  same underlying cause (a team-context category losing all its
  variation once a filter or exclusion is applied) and both fixed the
  same way Task 08 already established a precedent for. Nothing else
  was missing, broken, or malformed.
- Standard errors for PH-O2 are wider than PH-O1's (e.g. xG: 0.0507 vs.
  0.0387) despite similar point estimates — expected, since clustering
  by team context while ALSO including team-context fixed effects means
  the cluster-robust variance is estimated from residual variation
  within each team's own matches, which is a much smaller quantity of
  information per cluster than PH-O1's coarser competition-season FE
  allows. Reported as-is; not a fit failure, just a real cost of the
  finer fixed-effect structure the brief specifies.

## 6. Questions for the research lead
1. **PH-O2's fixed-effect structure.** v2-8.3 says PH-O2 is "PH-O1 plus
   team-context fixed effects." Team context (team x competition x
   season) exactly nests competition-season, so literally adding both
   dummy sets is not estimable (confirmed via SVD — the design matrix is
   rank-deficient by exactly the number of comp-season categories minus
   the number that survive as genuinely separate from team-context,
   which in this data is effectively all of them). I implemented PH-O2
   as PH-O1's non-FE predictors + team-context FE, dropping the
   competition-season FE entirely, since that is the only way to get a
   non-degenerate fit and it is the standard way to add a finer FE on
   top of a coarser one. If a different resolution was intended (e.g.
   some other combination), please specify.
2. **How to read the possession-level reversal.** PH-O3(a) is
   significantly positive; the team-match-level results and PH-O3(b)
   are negative or null. I am not proposing which level of aggregation
   is more informative, or why they diverge — that is an interpretation
   decision, not mine to make. Flagging that v2-8.4's rule, applied
   mechanically, returns NOT ALLOWED because PH-O2 fails even though
   PH-O3(a) alone would have passed; the rule requires both, and I have
   not second-guessed that requirement.

## 7. Files produced
- `src/decision_engine/task11_outcome_diagnostics.py` — this task's
  full script (team-match diagnostics frame, PH-O1/PH-O2, possession
  builder, PH-O3, v2-8.4 verdict).
- `data/task11_outcome_diagnostics.json` — full run summary (correlation
  matrix, all regression coefficients, possession diagnostics, verdict).
  Gitignored.
- `data/processed/task11_possessions.csv` — the 20,042-possession
  intermediate table (not committed, per the project rule that nothing
  under `data/` is ever committed).
- Git commits made this task: `3232e28` (Amendment v2-8 alone, Step 0);
  `5b31b5a` (docs/JOURNAL.md, research lead's own Task 10 entry,
  committed separately per the established pattern); `9996c90` (this
  task's own script, spec file, and results page).

## 8. Confidence
Moderate-high on the numbers, low on what they mean (deliberately, since
that's not mine to decide). Both numerical failures encountered
(rank-deficient PH-O2, non-converging PH-O3 logit) were root-caused via
direct inspection (SVD null-space contributors; per-team-context
outcome variance) rather than papered over, and both fixes changed the
reported coefficients by a negligible amount — reassuring that the
underlying substantive numbers were already close to right, and that the
fixes were about numerical soundness and honest disclosure, not about
changing the finding. The join between per-pass Decision and raw-event
possession/shot data was verified on a sample match before being trusted
at scale (possession_team constancy, the stray-opponent-pass rate). The
weakest link is exactly the substantive one flagged in Sections 5-6: the
diagnostics do not converge on a single, clean explanation for Task 10's
negative finding, and I have deliberately not tried to make them.
