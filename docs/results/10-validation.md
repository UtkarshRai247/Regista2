# Task 10: Interval validity, outcome validation, detectable-effect audit
Date: 2026-09-22
Status: PARTIAL (Parts A and B complete; Part C in progress)

## Per-section checklist (per brief docs/specs/task-10-validation.md)
- Step 0 (confirm plan SHA-256 unchanged from ceafdcd): COMPLETE
- Part A (Study B interval method by simulated coverage, v2-6.1): COMPLETE
- Part B (outcome validation, v2-6.3): COMPLETE
- Part C (detectable-effect audit, v2-7.1): NOT RUN
- Hard rules (no changed definitions, full tables, no interpretation for
  the paper, no memory writes, JOURNAL.md untouched): COMPLETE for the
  work done so far.

## 1. Headline
[Placeholder — finalized once Part C is run. Part A: the previously-used
cluster-bootstrap interval method severely undercovers (10% of 100
simulations contained the true S), confirming Amendment v2-6.1's
diagnosis that it was invalid. Parametric bootstrap and profile-likelihood
both reached 93% coverage — below the 95% target — and tied exactly, a
tie the code resolved by list order rather than a specified rule
(Section 6). Under either candidate, Study B's Tier 1 verdict changes
from NOT ALLOWED (Task 08, invalid interval) to ALLOWED; Tier 2 remains
NOT ALLOWED under both.
Part B: **mean per-pass Decision is significantly NEGATIVELY associated
with both team xG and team goals in the same match**, in both H-O1 and
H-O2 specifications (n=583 of 598 team-matches; all four coefficients
p<0.001) — the opposite sign from what H-O1/H-O2 hypothesized. Taken at
face value this contradicts the premise that higher mean Decision (as
currently defined) reflects choices that help a team score more within
that match; see Section 5/6.]

## 2. What I did

### Part A
Reproduce with: `.venv/bin/python src/decision_engine/task10_partA_interval.py`
(then, for the tie-break addendum below, `.venv/bin/python
src/decision_engine/task10_partA_tiebreak.py`).

- Added `profile_likelihood_ci_S` to `src/decision_engine/reml_crossed.py`:
  reparametrizes `(var_player, var_team)` as `(S, total_var)`, profiles
  out `total_var` by bounded 1-D search over `log(total_var)` at each
  candidate `S` (reusing the module's existing sparse REML objective),
  then solves for the two `S` values where the profile deviance crosses
  `chi2(1, 0.95)` above the MLE deviance.
- Implemented all three candidate methods in
  `src/decision_engine/task10_partA_interval.py`: (i) cluster bootstrap
  with fresh ids (Task 08's fix, `reml_crossed.bootstrap_by_player`),
  (ii) parametric bootstrap (`reml_crossed.simulate_units` from the
  fitted variances, refit, percentile), (iii) profile likelihood.
- Ran the coverage test: 100 simulated datasets on the real 1,701-unit
  design at the fitted variances (var_player=4.9024e-7,
  var_team=2.5967e-7, true S=0.653732), B=200 bootstrap draws per
  simulation for methods (i) and (ii), per the task brief. Checkpointed
  at sim 25 (elapsed 1,782s, projected total 7,128s = 1.98h) — under the
  2-hour budget, so continued to the full 100 (did not cut to 50).
  Actual total: 7,039s (~1.96h).
- Selected PRIMARY = method with coverage closest to 0.95 among those
  >=0.90. Built all three intervals on the real `study_b_units.parquet`,
  then re-applied the fixed v2-5.4 Tier 1/Tier 2 rules using PRIMARY.
- **Found a tie**: methods (ii) and (iii) both reached exactly 0.93
  coverage (both 0.02 from 0.95). The brief specifies the selection rule
  but not a tie-break; the code's `select_primary()` resolves ties via
  `min()` over a fixed `("i","ii","iii")` iteration order, which returns
  (ii) — an implementation-order artifact, not a considered rule. Wrote
  `src/decision_engine/task10_partA_tiebreak.py` to compute PH-B1/PH-B3/
  tier verdicts under the untied alternate, (iii), reusing the same real
  fit and unit subsets, so this is disclosed with full information
  rather than silently resolved (Section 6).

### Part B
Reproduce with: `.venv/bin/python src/decision_engine/task10_partB_outcome.py`.

- Built 598 team-match units (299 matches x 2 teams) from
  `task04_situation_context.load_matches_meta` (home/away teams, scores,
  competition_id, season_id — home/away IS derivable, per the brief's
  request to report this).
- Decision: `decompose.build_per_pass_table` (frozen, non-cross-fitted
  per-pass table, the same one Tasks 08/09 reuse), mean per (match_id,
  team). 15/598 rows came back with no Decision at all — investigated
  before dropping anything silently; see Section 5.
- Possession share: eligible-pass count per (match_id, team) from
  `passes_situation.parquet`, divided by that match's total.
  Completion/progressive/xA rates: `task08_reliability_audit.
  per_pass_reference_flags` (Task 08's own per-pass formulas, unchanged),
  aggregated by team instead of player, merged to team via
  `passes_situation.parquet`'s own team column.
- xG: summed `shot_statsbomb_xg` over each team's `Shot` events in that
  match. Goals: `home_score`/`away_score` from the match-metadata file
  directly (not reconstructed from events).
- Standardized Decision to a z-score (mean=0.001590, sd=0.001140,
  n=598) so coefficients are in outcome-per-SD-of-Decision.
- Fit H-O1 (Decision_z + possession_share + is_home + competition-season
  fixed effects, reference = comp_id=11/season_id=90) and H-O2 (H-O1 +
  completion_rate + progressive_rate + xa_per_pass), clustered by team
  context (team x competition x season), for both xG (primary) and
  goals (secondary) — 4 regressions total, via `statsmodels`
  `sm.OLS(...).fit(cov_type="cluster", ...)`, the same idiom
  `src/market_join/fit_model.py` already uses.

### Part C
Not yet run.

## 3. Numbers

### Part A — coverage test (100 simulations, B=200 bootstrap draws each)

| Method | Coverage (target 0.95) | Mean CI width |
|---|---|---|
| (i) cluster bootstrap, fresh ids | **0.10** | 0.1606 |
| (ii) parametric bootstrap | 0.93 | 0.1813 |
| (iii) profile likelihood | 0.93 | 0.1857 |

PRIMARY selected by code: **(ii)**, via the tie-break described in
Section 2/6.

### Part A — real-data fit and intervals (study_b_units.parquet, n=1,701 units, 1,232 players, 157 team-contexts)
Point estimate: S = 0.653731 (var_player=4.9024e-7, var_team=2.5967e-7).

| Method | 95% CI for S | Contains point estimate? |
|---|---|---|
| (i) cluster bootstrap | [0.3789, 0.5657] | No |
| (ii) parametric bootstrap (PRIMARY) | [0.5662, 0.7550] | Yes |
| (iii) profile likelihood (tied alternate) | [0.5444, 0.7515] | Yes |

Method (i)'s real-data interval reproduces the exact pathology Amendment
v2-6.1 diagnosed: it excludes the point estimate it was built from.

### Part A — post-hoc checks and v2-5.4 tier verdict, using PRIMARY = (ii)

| Check | Fit S | 95% CI | n units |
|---|---|---|---|
| PH-B1 (+ position-group FE) | 0.6379 | [0.5473, 0.7427] | 1,701 |
| PH-B3 (movers with >=2 units only) | 0.5793 | [0.4656, 0.6970] | 814 |

PH-B2 (disattenuated mover correlation, unaffected by interval method):
r_obs=0.0534, split-half reliabilities club=0.5007/intl=0.5522,
r_true=0.1015, 95% CI=[-0.2476, 0.5263] (includes zero).

| Tier | Condition | Verdict under PRIMARY=(ii) |
|---|---|---|
| Tier 1 | B4 CI lower bound > 0.5 (0.5662 — passes) AND PH-B1 CI lower bound > 0.5 (0.5473 — passes) | **ALLOWED** |
| Tier 2 | Tier 1 (passes) AND PH-B2 positive w/ CI excl. zero (r_true=0.1015>0 but CI includes zero — fails) AND PH-B3 CI lower bound > 0.5 (0.4656 — fails) | **NOT ALLOWED** |

### Part A — tie-break addendum: same tier verdict under the untied alternate, (iii)

| Check | 95% CI (method iii) |
|---|---|
| B4 (real data) | [0.5444, 0.7515] |
| PH-B1 | [0.5274, 0.7381] |
| PH-B3 | [0.4344, 0.7160] |

| Tier | Verdict under (iii) |
|---|---|
| Tier 1 | **ALLOWED** (both lower bounds > 0.5) |
| Tier 2 | **NOT ALLOWED** (same two failures: PH-B2 CI includes zero, PH-B3 CI lower bound < 0.5) |

The tier verdicts are identical under both tied candidates. The tie is
disclosed in full (Section 6) but does not change Part A's substantive
conclusion.

### For comparison — Task 08's verdict under the now-invalid interval method
Tier 1: NOT ALLOWED (corrected B4 CI lower bound 0.3631, PH-B1 CI lower
bound 0.3513, both failed). Tier 2: NOT ALLOWED. Source:
`docs/results/08-studies-b-c.md`.

### Part B — unit count
598 team-match units built as expected (299 matches x 2). Decision
available for 583/598 (see Section 5 for the 15 missing); all four
regressions therefore use **n=583**, not 598.

### Part B — H-O1 and H-O2, outcome = xG (primary), clustered by team context

| Spec | n | R² | Decision_z coef (xG per SD) | 95% CI | p |
|---|---|---|---|---|---|
| H-O1 | 583 | 0.1665 | **-0.1381** | [-0.2104, -0.0659] | 0.00018 |
| H-O2 | 583 | 0.2176 | **-0.1241** | [-0.1926, -0.0555] | 0.00039 |

H-O1 other coefficients: possession_share +2.6745 [2.1726, 3.1765]
(p<1e-24), is_home -0.0257 [-0.1814, 0.1301] (p=0.747, not significant).
H-O2 adds: completion_rate +1.1485 [-1.0071, 3.3041] (p=0.296, not
significant), progressive_rate +2.9090 [1.4657, 4.3523] (p<0.001),
xa_per_pass +213.30 [109.24, 317.37] (p<0.001). Competition-season fixed
effects: 6 of 7 not significant at alpha=0.05; cs_44_107 (MLS 2023)
-0.3503 [-0.6970, -0.0036], p=0.048.

### Part B — H-O1 and H-O2, outcome = goals (secondary), clustered by team context

| Spec | n | R² | Decision_z coef (goals per SD) | 95% CI | p |
|---|---|---|---|---|---|
| H-O1 | 583 | 0.1979 | **-0.4031** | [-0.5124, -0.2939] | <1e-12 |
| H-O2 | 583 | 0.2287 | **-0.4587** | [-0.5761, -0.3414] | <1e-13 |

H-O1 other coefficients: possession_share +3.1441 [2.5401, 3.7482]
(p<1e-30), is_home +0.0388 [-0.1503, 0.2280] (p=0.687, not significant).
H-O2 adds: completion_rate +5.3961 [2.7259, 8.0663] (p<0.001),
progressive_rate +1.6744 [-0.6720, 4.0208] (p=0.162, not significant),
xa_per_pass +71.20 [-29.79, 172.18] (p=0.167, not significant).

In every one of the 4 regressions, Decision_z is **significantly
negative** — the opposite sign from H-O1/H-O2's hypothesized direction
— and remains negative and significant after adding the completion/
progressive/xA controls (H-O2), so the sign is not an artifact of
omitting those controls.

## 4. Deviations from the brief
- **None in method or scope for Part A.** All three candidate methods,
  the 100-simulation coverage test with the brief's own checkpoint-and-
  disclose contingency, and the fixed v2-5.4 tier re-application were
  run exactly as specified.
- **Ambiguity encountered, not resolved by me**: the coverage tie between
  methods (ii) and (iii) (Section 2/6) — the brief's selection rule
  ("PRIMARY = coverage closest to 0.95 among methods with coverage
  >= 0.90") does not define a tie-break, and the code I wrote resolved
  it via Python `min()`'s first-match behavior on an unordered tie
  without my having previously flagged that this was a live possibility.
  I am disclosing this as a question (Section 6) rather than asserting
  (ii) is correctly primary, and have computed the untied alternate's
  full downstream consequences so nothing is hidden by the choice.
- The task brief (`docs/specs/task-10-validation.md`) specifies **100**
  coverage-test simulations; Amendment v2-6.1's original text specifies
  **200**. I followed the task brief's explicit number, since it is the
  document that governs this task's execution and was given after the
  amendment — noted here as a discrepancy between the two governing
  documents, not a decision I made myself.
- **Part B: sample size is 583, not 598.** 15 of the 598 built
  team-match units had no computable Decision and were dropped by
  `dropna()` before fitting (same 15 rows are also missing
  possession_share/completion/progressive/xA, since those come from the
  same team-name join). Not a choice I made to shrink the sample — see
  Section 5 for exactly which rows and why.

## 5. Problems and surprises
- Neither method that reached the >=0.90 coverage floor actually reached
  0.95 — both (ii) and (iii) sit at 0.93. This is not itself a failure
  under the brief's stated rule, but it means Study B's validated
  interval is still not exactly nominal; a table this small (100
  simulations) can't distinguish "true coverage is 0.93" from "true
  coverage is 0.95 and this is Monte Carlo noise" — the 95% CI on a
  binomial proportion of 93/100 is roughly [0.863, 0.972].
- Method (i)'s catastrophic 10% coverage is a strong, direct confirmation
  of Amendment v2-6.1's mechanism argument (crossed-design resampling
  damages the un-resampled factor) — not a surprise given the amendment,
  but worth stating plainly since it is the paper's justification for
  discarding Task 07/08's original interval entirely.
- If taken at face value, Part A's Tier 1 "ALLOWED" result would
  invalidate the Task 08 conclusion that Study B's player-vs-context
  finding was descriptive only — that conclusion rested entirely on the
  now-demonstrated-invalid interval method's lower bound (0.3631) failing
  the 0.5 threshold. The corrected lower bound (0.5662/0.5444 depending
  on method) clears it. This is exactly the kind of correction v2-6.1
  anticipated, not a new finding independent of the interval-method fix.
- **Part B's 15 missing team-match rows have two distinct causes, and one
  of them is a new finding.** 14 of the 15 (7 matches x 2 teams) come
  from matches with zero eligible passes at all: 3 MLS matches involving
  Inter Miami (match_ids 3877115, 3877170, 3877194), 1 Ligue 1 match
  (3837706), and 3 Bundesliga matches (3895158, 3895266, 3895309) — this
  is the same "7 matches with zero eligible passes" property Task 04
  already documented, not new.
  The 15th is new: match 3837747 (Paris Saint-Germain vs. Olympique de
  Marseille, Ligue 1) has PSG's row intact but **Marseille's row is
  silently unjoinable**, because that one match's raw event file
  (`data/raw/events/3837747.parquet`) records the team as `"Marseille"`,
  while the match-metadata file (`data/raw/matches/*.parquet`) and every
  other Marseille match's event file both use `"Olympique de Marseille"`.
  Verified by checking the other 3 PSG-vs-Marseille meetings
  (3802983, 3802902, 3837885): all 3 use `"Olympique de Marseille"`
  consistently in both files, so this is an isolated single-match naming
  anomaly in the raw StatsBomb data (unedited, per repo rules), not a
  systemic Ligue 1 or Marseille naming convention. It silently drops one
  otherwise-valid, computable team-match observation from every merge
  keyed on team name (Decision, possession share, completion/progressive/
  xA), rather than one with genuinely no underlying data. This is a
  data-quality finding, not something I patched — the row is currently
  just missing, and I have not added a name-alias fix (that would be a
  methodology choice I'm not authorized to make silently). See Section 6.
- **If taken at face value, the sign of H-O1/H-O2's Decision coefficient
  would invalidate the assumption that this project's central metric,
  mean per-pass Decision, measures something that helps a team produce
  more shots/goals within the same match.** All 4 regressions (xG and
  goals, both specs) find Decision significantly negative, holding up
  after adding completion/progressive/xA controls. This is the first
  time any task in this project has tested Decision against an outcome
  outside the possession-value model that defines it, and the result
  runs opposite to what both hypotheses expected. I have not attempted
  to explain the sign (that is a modeling/interpretation decision, not
  mine to make) — flagging it as the single most consequential finding
  in this task and asking about it directly in Section 6.

## 6. Questions for the research lead
1. **Tie-break rule for PRIMARY selection.** Methods (ii) and (iii) tied
   exactly at 0.93 coverage in the 100-simulation test. The brief does
   not specify how to break a tie. My code resolved it via Python's
   `min()` iteration order (returns (ii)), which is an implementation
   detail I introduced, not a rule from the brief or the amendment. I
   have NOT chosen a tie-break rule myself, and computed the untied
   alternate's PH-B1/PH-B3/tier verdicts for comparison
   (`data/task10_partA_tiebreak.json`, Section 3 above) — under this
   audit, both alternates give the SAME tier verdict, so nothing hinges
   on the answer here for this task, but I did not want to silently rely
   on Python dict-iteration order as if it were a methodology decision,
   and a future re-run with different bootstrap draws could plausibly
   land on a tie the two methods' tier verdicts do NOT agree on. Please
   specify a tie-break rule (e.g. narrower mean width, or a preference
   order) for the preregistration record.
2. **100 vs. 200 simulations.** Amendment v2-6.1 specifies 200 simulated
   datasets for the coverage test; the task-10 brief specifies 100 (with
   B=200 bootstrap draws inside each simulation). I ran 100, following
   the task brief. Flagging the discrepancy between the two documents in
   case it was not an intentional narrowing.
3. **Decision is significantly negatively associated with both xG and
   goals, in both H-O1 and H-O2, at n=583.** This is the opposite sign
   from both hypotheses and survives adding completion/progressive/xA
   controls. I am not proposing a mechanism (that is a research-design
   decision) or deciding what this means for the project's central
   Decision metric — reporting it exactly as it came out, per the hard
   rule against interpretation. This seems like the kind of result that
   needs the research lead's judgment on whether/how to proceed with
   Study A/B's framing, since it is the first outcome-level test this
   project has run.
4. **Should the Olympique de Marseille / Marseille naming mismatch
   (Section 5) be corrected in a future task?** It currently causes one
   otherwise-valid team-match observation (match 3837747) to be dropped
   from every team-level merge in this project that keys on team name,
   not just this task's regressions. I have not attempted a fix (e.g. a
   name-alias map) since that would be a data-cleaning decision outside
   this task's scope, and did not want to silently patch it inside a
   validation task.

## 7. Files produced
- `src/decision_engine/reml_crossed.py` — added `profile_likelihood_ci_S`
  (method iii)'s CI construction), plus a self-check in `__main__`. No
  existing function in this file was changed.
- `src/decision_engine/task10_partA_interval.py` — Part A's main script
  (coverage test, real-data intervals, PH-B1/PH-B2/PH-B3, tier
  application).
- `src/decision_engine/task10_partA_tiebreak.py` — addendum computing the
  tied alternate's downstream PH-B1/PH-B3/tier verdict (Section 6, item 1).
- `data/task10_partA_interval.json` — full Part A run summary. Gitignored.
- `data/task10_partA_tiebreak.json` — tie-break addendum summary.
  Gitignored.
- `src/decision_engine/task10_partB_outcome.py` — Part B's script (team-
  match unit construction, 4 clustered-OLS regressions).
- `data/task10_partB_outcome.json` — full Part B run summary, all 4
  regressions' coefficients. Gitignored.
- Git commits made so far this task: `746ac3c` (docs/JOURNAL.md,
  research lead's own Task 09b entry, committed separately per the
  established pattern); `4116455` (Part A: `reml_crossed.py`,
  `task10_partA_interval.py`, `task10_partA_tiebreak.py`, this results
  page, and `docs/specs/task-10-validation.md`); `229565e` (Part A hash-
  recording follow-up); `9167a4d` (Part B: `task10_partB_outcome.py` and
  this results page).

## 8. Confidence
Part A: moderate-high. The coverage test ran to completion at the full
100 simulations without needing the runtime-cut contingency, method (i)'s
failure is a clean, large-margin confirmation of the amendment's
diagnosis, and the tier verdict is identical under both tied primary
candidates so the one real ambiguity found (Section 6, item 1) turns out
not to be load-bearing for this task's conclusion. The soft spots are:
neither validated method reaches the nominal 95% coverage target (both at
93%, within Monte Carlo noise of 95% but not confirming it), and the
tie-break itself remains an open methodology question for future reruns
where it might not be inconsequential.

Part B: high confidence in the arithmetic (n, clustering, and the two
outcome variables were each independently spot-checked — xG matched
299/299 with zero missing shot xG, and the 15-row shortfall was traced to
two specific, named causes rather than accepted as unexplained noise).
Low confidence in what the negative Decision coefficient MEANS for the
project, deliberately — that is not a call for me to make. The weakest
link is construct validity: this is a team-match-level, same-match
association, not a causal test, and the direction is exactly opposite
what was hypothesized, which is important enough that it should not be
read past this results page without the research lead's input (Section
6, item 3). Part C not yet assessed.
