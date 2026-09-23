# Task 10: Interval validity, outcome validation, detectable-effect audit
Date: 2026-09-22
Status: COMPLETE

## Per-section checklist (per brief docs/specs/task-10-validation.md)
- Step 0 (confirm plan SHA-256 unchanged from ceafdcd): COMPLETE
- Part A (Study B interval method by simulated coverage, v2-6.1): COMPLETE
- Part B (outcome validation, v2-6.3): COMPLETE
- Part C (detectable-effect audit, v2-7.1): COMPLETE
- Hard rules (no changed definitions, full tables, no interpretation for
  the paper, no memory writes, JOURNAL.md untouched): COMPLETE for the
  work done so far.

## 1. Headline
**Part A**: the previously-used cluster-bootstrap interval method
severely undercovers (10% of 100 simulations contained the true S),
confirming Amendment v2-6.1's diagnosis that it was invalid. Parametric
bootstrap and profile-likelihood both reached 93% coverage — below the
95% target — and tied exactly, a tie the code resolved by list order
rather than a specified rule (Section 6). Under either candidate, Study
B's Tier 1 verdict changes from NOT ALLOWED (Task 08, invalid interval)
to ALLOWED; Tier 2 remains NOT ALLOWED under both.
**Part B**: mean per-pass Decision is **significantly NEGATIVELY**
associated with both team xG and team goals in the same match, in both
H-O1 and H-O2 specifications (n=583 of 598 team-matches; all four
coefficients p<0.001) — the opposite sign from what H-O1/H-O2
hypothesized. Taken at face value this contradicts the premise that
higher mean Decision (as currently defined) reflects choices that help
a team score more within that match; see Section 5/6.
**Part C**: across all 107 analyzable pairs (not just the 10 candidates),
median minimum detectable effect on the confirmation half is **0.365 L**
— under the preregistered 0.5 practical floor for a "trivial-but-real"
effect. 91.6% of pairs (98/107) could detect a 1.0 L effect at 80% power;
65.4% (70/107) could detect a 0.5 L effect. The 9 pairs with MDE above
1.0 L are all `under_pressure=no` and mostly `backward_*` option types
(Section 3 full table); this is a descriptive pattern in the data, not
an interpretation of why.

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
Reproduce with: `.venv/bin/python src/decision_engine/task10_partC_mde_audit.py`.

- Independently rebuilt the discovery-half analyzable-pairs list (Task
  05's own `build_available_types_table`/`analyzable_pairs`, >=100-chosen
  rule) as a consistency check: got 107, matching Task 05 exactly.
- Loaded the confirmation half (Task 06's `confirmation_match_ids`/
  `load_and_prepare`) and built the g_table (`g = ev_star - ev_star_j`)
  for **all 107** pairs, not just the 10 candidates Task 06's own hard
  rule scoped it to — the brief explicitly supersedes that scope for this
  one audit.
- Wrote `bootstrap_g_stats_se`, a local variant of Task 06's
  `bootstrap_g_stats` that additionally returns the match-level bootstrap
  draws' own standard deviation (SE of G) — same resampling, one extra
  return value, not a change to the shared function.
- MDE in G units: `2.802 * SE` (two-sided alpha=0.05, 80% power). MDE in
  L units: MDE_G x (that pair's own qualifying-passes-per-team-match) x
  38, the same conversion Amendment v2-1 already defines for G itself.
- **Hit and fixed a bug before trusting the output**: `bootstrap_g_stats_se`
  needs a `team` column, but the confirmation-half `cell_info` I built
  only carried zone/pressure/game_state, so the first run crashed with
  `KeyError: "['team'] not in index"`. Fixed by adding `team` to
  `cell_info_c` (matching how Task 06's own `cell_info` is built) and
  reran cleanly.

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

### Part C — join diagnostics
Discovery-half rebuild: 616,038/616,038 typed rows matched (100.0%),
2 key collisions (matches Task 05's own finding exactly). Confirmation
half: 621,573/621,573 matched (100.0%), 16 key collisions, 0 group-size
mismatches. 107/107 analyzable pairs had at least one confirmation-half
pass (0 pairs with zero passes).

### Part C — summary statistics (n=107 pairs)
Median MDE in L units: **0.3651**. Share with MDE <= 1.0 L: **0.9159**
(98/107). Share with MDE <= 0.5 L: **0.6542** (70/107).

### Part C — full 107-row table (sorted by zone, pressure, game state, type — NOT by effect size)
G, SE(G), and MDE(G) are per-pass EV-gap units; L and MDE(L) are the
Amendment v2-1 goal-equivalent-per-season units (G x qualifying-passes-
per-team-match x 38).

| zone | pressure | state | type | G | SE(G) | MDE(G) | L | MDE(L) | n_passes | n_matches |
|---|---|---|---|---|---|---|---|---|---|---|
| defensive | no | leading | backward_medium | -0.010082 | 0.002474 | 0.006933 | -2.0054 | 1.3791 | 670 | 120 |
| defensive | no | leading | backward_short | -0.007810 | 0.001392 | 0.003902 | -2.7931 | 1.3954 | 1280 | 129 |
| defensive | no | leading | forward_medium | -0.003469 | 0.000375 | 0.001050 | -1.6832 | 0.5094 | 1724 | 126 |
| defensive | no | leading | forward_short | -0.002170 | 0.000539 | 0.001511 | -0.9142 | 0.6367 | 1497 | 127 |
| defensive | no | leading | lateral_long | -0.001953 | 0.000217 | 0.000607 | -1.3243 | 0.4119 | 2552 | 136 |
| defensive | no | leading | lateral_medium | -0.000564 | 0.000327 | 0.000917 | -0.4083 | 0.6645 | 2764 | 136 |
| defensive | no | leading | lateral_short | 0.000203 | 0.000346 | 0.000970 | 0.1095 | 0.5235 | 2088 | 137 |
| defensive | no | level | backward_medium | -0.013999 | 0.001138 | 0.003188 | -2.3858 | 0.5433 | 1036 | 134 |
| defensive | no | level | backward_short | -0.008770 | 0.000562 | 0.001574 | -2.5232 | 0.4529 | 2014 | 145 |
| defensive | no | level | forward_long | -0.003902 | 0.000192 | 0.000537 | -1.0117 | 0.1393 | 1153 | 133 |
| defensive | no | level | forward_medium | -0.002829 | 0.000260 | 0.000730 | -1.2034 | 0.3104 | 2955 | 145 |
| defensive | no | level | forward_short | -0.001675 | 0.000287 | 0.000804 | -0.5780 | 0.2775 | 2507 | 148 |
| defensive | no | level | lateral_long | -0.002381 | 0.000196 | 0.000550 | -1.4031 | 0.3243 | 4389 | 147 |
| defensive | no | level | lateral_medium | -0.000659 | 0.000216 | 0.000605 | -0.3977 | 0.3651 | 4530 | 148 |
| defensive | no | level | lateral_short | 0.000181 | 0.000239 | 0.000670 | 0.0840 | 0.3106 | 3441 | 148 |
| defensive | no | trailing | backward_medium | -0.027050 | 0.002975 | 0.008335 | -5.2315 | 1.6120 | 682 | 126 |
| defensive | no | trailing | backward_short | -0.016075 | 0.001270 | 0.003558 | -5.2868 | 1.1702 | 1229 | 129 |
| defensive | no | trailing | forward_medium | -0.002290 | 0.000682 | 0.001911 | -0.8709 | 0.7265 | 1411 | 128 |
| defensive | no | trailing | forward_short | -0.000792 | 0.000857 | 0.002401 | -0.2652 | 0.8038 | 1286 | 134 |
| defensive | no | trailing | lateral_long | -0.002521 | 0.000439 | 0.001231 | -1.5647 | 0.7640 | 2434 | 135 |
| defensive | no | trailing | lateral_medium | -0.001728 | 0.000556 | 0.001558 | -1.0773 | 0.9716 | 2494 | 137 |
| defensive | no | trailing | lateral_short | 0.000689 | 0.000413 | 0.001159 | 0.3276 | 0.5512 | 1903 | 138 |
| defensive | yes | leading | forward_short | -0.001761 | 0.001137 | 0.003185 | -0.1903 | 0.3442 | 273 | 93 |
| defensive | yes | leading | lateral_medium | -0.000246 | 0.000627 | 0.001757 | -0.0370 | 0.2638 | 498 | 119 |
| defensive | yes | leading | lateral_short | 0.000416 | 0.000730 | 0.002045 | 0.0478 | 0.2352 | 342 | 108 |
| defensive | yes | level | backward_short | -0.009578 | 0.001260 | 0.003529 | -0.7966 | 0.2935 | 383 | 118 |
| defensive | yes | level | forward_medium | -0.001492 | 0.000495 | 0.001387 | -0.1396 | 0.1298 | 458 | 121 |
| defensive | yes | level | forward_short | -0.001559 | 0.000629 | 0.001763 | -0.1513 | 0.1710 | 503 | 127 |
| defensive | yes | level | lateral_medium | 0.000041 | 0.000400 | 0.001121 | 0.0057 | 0.1549 | 858 | 135 |
| defensive | yes | level | lateral_short | -0.000274 | 0.000519 | 0.001453 | -0.0325 | 0.1721 | 676 | 130 |
| defensive | yes | trailing | forward_short | -0.001354 | 0.001424 | 0.003989 | -0.1187 | 0.3498 | 240 | 98 |
| defensive | yes | trailing | lateral_medium | -0.001011 | 0.001175 | 0.003292 | -0.1377 | 0.4487 | 434 | 115 |
| defensive | yes | trailing | lateral_short | 0.001057 | 0.001148 | 0.003216 | 0.1163 | 0.3538 | 304 | 100 |
| final | no | leading | backward_medium | -0.009462 | 0.000810 | 0.002271 | -4.1456 | 0.9948 | 1545 | 125 |
| final | no | leading | backward_short | -0.006217 | 0.000770 | 0.002157 | -2.6746 | 0.9281 | 1517 | 126 |
| final | no | leading | forward_short | -0.001377 | 0.000802 | 0.002246 | -0.5125 | 0.8358 | 1322 | 126 |
| final | no | leading | lateral_long | -0.003091 | 0.000349 | 0.000979 | -2.1919 | 0.6943 | 2650 | 131 |
| final | no | leading | lateral_medium | 0.002508 | 0.000471 | 0.001319 | 1.9691 | 1.0358 | 2913 | 131 |
| final | no | leading | lateral_short | 0.001592 | 0.000442 | 0.001240 | 0.8827 | 0.6874 | 2087 | 131 |
| final | no | level | backward_long | -0.007457 | 0.000294 | 0.000825 | -2.1480 | 0.2375 | 1228 | 123 |
| final | no | level | backward_medium | -0.006682 | 0.000295 | 0.000825 | -2.7587 | 0.3408 | 2977 | 147 |
| final | no | level | backward_short | -0.004366 | 0.000305 | 0.000855 | -1.6125 | 0.3156 | 2624 | 146 |
| final | no | level | forward_medium | -0.004255 | 0.000889 | 0.002491 | -0.7862 | 0.4603 | 1128 | 136 |
| final | no | level | forward_short | -0.003041 | 0.000474 | 0.001327 | -0.9938 | 0.4338 | 2279 | 140 |
| final | no | level | lateral_long | -0.002524 | 0.000187 | 0.000524 | -1.6482 | 0.3421 | 4794 | 147 |
| final | no | level | lateral_medium | 0.000807 | 0.000209 | 0.000587 | 0.5241 | 0.3809 | 4801 | 145 |
| final | no | level | lateral_short | 0.000828 | 0.000225 | 0.000630 | 0.4051 | 0.3080 | 3605 | 145 |
| final | no | trailing | backward_medium | -0.008069 | 0.000618 | 0.001731 | -3.5063 | 0.7522 | 1681 | 133 |
| final | no | trailing | backward_short | -0.005853 | 0.000691 | 0.001937 | -2.1359 | 0.7067 | 1402 | 134 |
| final | no | trailing | forward_medium | -0.005483 | 0.001742 | 0.004881 | -1.0919 | 0.9720 | 697 | 125 |
| final | no | trailing | forward_short | -0.004100 | 0.000789 | 0.002212 | -1.3072 | 0.7053 | 1225 | 134 |
| final | no | trailing | lateral_long | -0.002050 | 0.000358 | 0.001002 | -1.3187 | 0.6445 | 2590 | 140 |
| final | no | trailing | lateral_medium | 0.001126 | 0.000366 | 0.001025 | 0.7329 | 0.6670 | 2603 | 137 |
| final | no | trailing | lateral_short | 0.000908 | 0.000337 | 0.000945 | 0.4458 | 0.4638 | 2003 | 139 |
| final | yes | leading | backward_short | -0.007310 | 0.001324 | 0.003710 | -0.8308 | 0.4217 | 329 | 104 |
| final | yes | leading | lateral_medium | 0.002570 | 0.000832 | 0.002332 | 0.4148 | 0.3764 | 531 | 120 |
| final | yes | leading | lateral_short | 0.000782 | 0.000890 | 0.002493 | 0.0995 | 0.3175 | 392 | 112 |
| final | yes | level | backward_medium | -0.004817 | 0.000642 | 0.001799 | -0.4747 | 0.1772 | 516 | 123 |
| final | yes | level | backward_short | -0.002931 | 0.000702 | 0.001966 | -0.3110 | 0.2086 | 564 | 128 |
| final | yes | level | forward_short | -0.004343 | 0.000659 | 0.001845 | -0.4185 | 0.1778 | 464 | 118 |
| final | yes | level | lateral_medium | 0.001156 | 0.000423 | 0.001184 | 0.1754 | 0.1796 | 926 | 131 |
| final | yes | level | lateral_short | 0.000594 | 0.000469 | 0.001314 | 0.0730 | 0.1616 | 715 | 131 |
| final | yes | trailing | backward_short | -0.005684 | 0.001396 | 0.003913 | -0.5896 | 0.4059 | 303 | 106 |
| final | yes | trailing | lateral_medium | 0.001563 | 0.000721 | 0.002020 | 0.2344 | 0.3029 | 509 | 123 |
| final | yes | trailing | lateral_short | 0.001244 | 0.000809 | 0.002267 | 0.1475 | 0.2687 | 365 | 113 |
| middle | no | leading | backward_medium | -0.006139 | 0.000406 | 0.001139 | -6.2107 | 1.1519 | 3727 | 130 |
| middle | no | leading | backward_short | -0.003287 | 0.000238 | 0.000668 | -3.7223 | 0.7565 | 4292 | 134 |
| middle | no | leading | forward_medium | -0.002280 | 0.000218 | 0.000611 | -2.7688 | 0.7415 | 4633 | 134 |
| middle | no | leading | forward_short | -0.002377 | 0.000231 | 0.000649 | -2.8212 | 0.7697 | 4685 | 137 |
| middle | no | leading | lateral_long | -0.000293 | 0.000068 | 0.000190 | -0.6295 | 0.4093 | 8431 | 137 |
| middle | no | leading | lateral_medium | 0.000678 | 0.000056 | 0.000157 | 1.3454 | 0.3124 | 7941 | 137 |
| middle | no | leading | lateral_short | -0.000158 | 0.000085 | 0.000238 | -0.2600 | 0.3920 | 6453 | 136 |
| middle | no | level | backward_long | -0.008879 | 0.000358 | 0.001002 | -2.6622 | 0.3004 | 1515 | 132 |
| middle | no | level | backward_medium | -0.007414 | 0.000191 | 0.000535 | -6.7525 | 0.4869 | 6879 | 148 |
| middle | no | level | backward_short | -0.003739 | 0.000144 | 0.000402 | -3.4831 | 0.3746 | 7109 | 148 |
| middle | no | level | forward_long | -0.003615 | 0.000223 | 0.000625 | -1.1584 | 0.2004 | 1712 | 134 |
| middle | no | level | forward_medium | -0.003513 | 0.000124 | 0.000348 | -3.2582 | 0.3231 | 6835 | 146 |
| middle | no | level | forward_short | -0.002400 | 0.000127 | 0.000355 | -2.2463 | 0.3321 | 7043 | 147 |
| middle | no | level | lateral_long | -0.000269 | 0.000046 | 0.000128 | -0.4741 | 0.2246 | 13620 | 148 |
| middle | no | level | lateral_medium | 0.000788 | 0.000048 | 0.000134 | 1.2498 | 0.2125 | 12320 | 148 |
| middle | no | level | lateral_short | 0.000136 | 0.000062 | 0.000172 | 0.1768 | 0.2234 | 10098 | 148 |
| middle | no | trailing | backward_medium | -0.012964 | 0.000709 | 0.001987 | -12.4795 | 1.9124 | 3876 | 136 |
| middle | no | trailing | backward_short | -0.006453 | 0.000521 | 0.001459 | -6.0353 | 1.3642 | 3864 | 140 |
| middle | no | trailing | forward_medium | -0.005713 | 0.000374 | 0.001047 | -5.2001 | 0.9529 | 3617 | 137 |
| middle | no | trailing | forward_short | -0.003394 | 0.000433 | 0.001212 | -3.1302 | 1.1176 | 3786 | 139 |
| middle | no | trailing | lateral_long | -0.000014 | 0.000113 | 0.000317 | -0.0237 | 0.5488 | 7285 | 141 |
| middle | no | trailing | lateral_medium | 0.001232 | 0.000133 | 0.000374 | 1.9328 | 0.5863 | 6608 | 141 |
| middle | no | trailing | lateral_short | 0.000467 | 0.000146 | 0.000408 | 0.5970 | 0.5220 | 5348 | 140 |
| middle | yes | leading | backward_medium | -0.005194 | 0.000591 | 0.001655 | -0.9014 | 0.2872 | 548 | 115 |
| middle | yes | leading | backward_short | -0.002959 | 0.000383 | 0.001074 | -0.5699 | 0.2069 | 664 | 126 |
| middle | yes | leading | forward_short | -0.002272 | 0.000314 | 0.000880 | -0.4678 | 0.1811 | 688 | 122 |
| middle | yes | leading | lateral_long | -0.000209 | 0.000141 | 0.000394 | -0.0620 | 0.1168 | 1060 | 129 |
| middle | yes | leading | lateral_medium | 0.000760 | 0.000132 | 0.000371 | 0.2489 | 0.1216 | 1181 | 129 |
| middle | yes | leading | lateral_short | -0.000184 | 0.000160 | 0.000448 | -0.0454 | 0.1107 | 903 | 131 |
| middle | yes | level | backward_medium | -0.006227 | 0.000387 | 0.001085 | -0.9394 | 0.1638 | 933 | 139 |
| middle | yes | level | backward_short | -0.003171 | 0.000270 | 0.000756 | -0.5683 | 0.1354 | 1198 | 144 |
| middle | yes | level | forward_medium | -0.002483 | 0.000280 | 0.000783 | -0.3646 | 0.1150 | 966 | 144 |
| middle | yes | level | forward_short | -0.001808 | 0.000275 | 0.000769 | -0.3086 | 0.1313 | 1181 | 139 |
| middle | yes | level | lateral_long | 0.000071 | 0.000137 | 0.000383 | 0.0181 | 0.0982 | 1820 | 145 |
| middle | yes | level | lateral_medium | 0.000931 | 0.000135 | 0.000378 | 0.2581 | 0.1049 | 2029 | 146 |
| middle | yes | level | lateral_short | 0.000379 | 0.000185 | 0.000517 | 0.0830 | 0.1132 | 1548 | 145 |
| middle | yes | trailing | backward_medium | -0.011322 | 0.001127 | 0.003159 | -1.6329 | 0.4555 | 482 | 120 |
| middle | yes | trailing | backward_short | -0.005891 | 0.000887 | 0.002484 | -0.9850 | 0.4153 | 594 | 127 |
| middle | yes | trailing | forward_short | -0.001698 | 0.000559 | 0.001565 | -0.2893 | 0.2667 | 574 | 121 |
| middle | yes | trailing | lateral_long | 0.000338 | 0.000274 | 0.000767 | 0.0766 | 0.1736 | 864 | 134 |
| middle | yes | trailing | lateral_medium | 0.001582 | 0.000295 | 0.000828 | 0.3975 | 0.2080 | 992 | 136 |
| middle | yes | trailing | lateral_short | -0.000046 | 0.000439 | 0.001229 | -0.0097 | 0.2610 | 771 | 129 |

Full table also saved to `data/processed/task10_partC_mde_table.csv`
(not committed, per the project rule that nothing under `data/` is ever
committed — the table above is the full, authoritative copy).

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
- **None for Part C.** Ran on all 107 analyzable pairs as the brief
  explicitly authorizes (superseding Task 06's own confirmation-half
  scope restriction for this one audit), same bootstrap seed/draw count
  as every prior task's G/CI computation, same MDE formula and L
  conversion the brief specifies.

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
- Part C: no zero-pass pairs (all 107 had confirmation-half data), so
  nothing needed to be dropped or flagged as unmeasurable. The 9 pairs
  with MDE above the 1.0 L threshold are all `under_pressure=no` and
  mostly (7/9) `backward_*` types, spanning both small (n_passes=670)
  and large (n_passes=3,876) samples — high MDE isn't simply a small-n
  artifact here, since some of the largest-n pairs in the whole table
  (e.g. `middle|no|trailing|backward_medium`, n=3,876) are also among
  the least powered in L units. Reported as a pattern in the data, with
  no attempt to explain the mechanism.

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
- `src/decision_engine/task10_partC_mde_audit.py` — Part C's script
  (rebuilds all 107 analyzable pairs on the confirmation half, computes
  SE/MDE for each).
- `data/task10_partC_mde_audit.json` — Part C run summary (join
  diagnostics, median/share statistics). Gitignored.
- `data/processed/task10_partC_mde_table.csv` — the full 107-row table
  (also reproduced in full in Section 3 above). Gitignored.
- Git commits made this task: `746ac3c` (docs/JOURNAL.md, research
  lead's own Task 09b entry, committed separately per the established
  pattern); `4116455` (Part A: `reml_crossed.py`,
  `task10_partA_interval.py`, `task10_partA_tiebreak.py`, this results
  page, and `docs/specs/task-10-validation.md`); `229565e` (Part A hash-
  recording follow-up); `9167a4d` (Part B: `task10_partB_outcome.py` and
  this results page); `c46dae9` (Part C: `task10_partC_mde_audit.py` and
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
6, item 3).

Part C: high confidence. The analyzable-pairs count (107) and the
discovery-half join statistics reproduced Task 05's own numbers exactly
as an internal consistency check, the confirmation-half join matched
100.0%, and the one candidate pair cross-checked against Task 09b's
independently-computed frozen-horizon numbers (`middle|no|trailing|
lateral_medium`: G=0.001232, n_passes=6,608, both match exactly) landed
within expected sampling variation on SE/CI. The bug hit during
development (missing `team` column) was caught by the script crashing
immediately, not by a silently wrong number, and the fix was a one-line,
mechanical addition matching an existing pattern (Task 06's own
`cell_info`) rather than a judgment call.
