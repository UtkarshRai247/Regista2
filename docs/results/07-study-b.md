# Task 07: Study A post-hoc checks, then Study B

Date: 2026-09-21
Status: COMPLETE

## Per-section checklist (per brief docs/specs/task-07-study-b.md)
- Step 0 (commit Amendments v2-3 + v2-4 together): COMPLETE
- Part 1 (post-hoc PH-1/PH-2, ROBUST/NOT ROBUST): COMPLETE
- Step B1 (per-pass Decision, reproduction check, stage-1 units): COMPLETE
- Step B2 (Gate E counts): COMPLETE
- Step B3 (REML estimator + parameter recovery test): COMPLETE (all 3 scenarios passed)
- Step B4 (fit, Gate E verdict): COMPLETE
- Step B5 (secondary: position-matched refit, mover correlation): COMPLETE
- Hard rules (fixed interpretation rule, full unsorted tables, no
  interpretation, no memory writes, JOURNAL.md untouched, v2-4
  cross-fitting NOT run): COMPLETE

## 1. Headline
Of the 7 CONFIRMED Study A candidates, 3 are ROBUST to the post-hoc
counting-artifact checks (all `middle`-zone `lateral_medium`); the other
4 (including both cells that passed Gate D but not the post-hoc checks)
are NOT ROBUST. Separately, Study B's hand-built REML estimator passed
its parameter-recovery test on all 3 scenarios (the required gate before
touching real data), and the real fit gives S = var_player /
(var_player + var_team) = 0.654 (95% CI [0.626, 0.785], n=1,701 stage-1
units, 1,232 players), passing Gate E (PASS, not descriptive-only). The
club-vs-international correlation for movers (n=132) is r=0.053, 95% CI
[-0.126, 0.259] — indistinguishable from zero at this sample size.

## 2. What I did
Reproduce with: `.venv/bin/python src/decision_engine/task07_posthoc.py`
then `.venv/bin/python src/decision_engine/task07_study_b.py` (after
Step 0's commit, done separately — see Section 7).

- **Step 0**: committed `docs/specs/analysis-plan-v2.md` (Amendments
  v2-3 and v2-4 together, 89 lines, already present on disk) in one
  commit `7f747da`
  (`sha256 = 5b566b426b8a833eeb7924e95b76f9a1afbc77d38c31de9616a279797fa38d3f`).
  Amendment v2-4 (cross-fitting) is not executed in this task, per the
  brief and the user's explicit instruction — that is Task 09.
- **Part 1**: reused Task 06's confirmation-half join pipeline
  (`src/decision_engine/task06_study_a_confirmation.py`, 2026-09-20) to
  rebuild the per-pass available-types table with both max-based
  (`ev_star`) and mean-based (`ev_mean`) EV per type, for the 7 CONFIRMED
  candidates. PH-1 = bootstrap CI (1,000 match draws, seed 20260920) on
  `mean(ev_mean_k - ev_mean_j)`. PH-2 = the same bootstrap on the
  original max-based `g`, restricted to passes where the candidate's
  qualifying-pass subset has `n_options_k == n_options_j` (both maxima
  taken over equally many candidates). ROBUST = CONFIRMED (given) AND
  Gate-D-PASS (from `data/processed/study_a_gate_d.parquet`, Task 06)
  AND PH-1 positive with CI excluding zero AND PH-2 positive with CI
  excluding zero — applied exactly as the (fixed) v2-3.1 rule states, not
  adjusted.
- **Step B1**: Decision per pass computed as `EV(chosen) -
  sum(policy_probability * EV)` from `options_policy.parquet`, using the
  identical arithmetic `decompose.build_per_pass_table`'s `decision`
  column already defines (reimplemented without that function's
  possession-value-model dependency, since Study B needs only Decision,
  not Execution/realized value). Verified: grouping by `(player_id,
  competition_id, season_id)` and taking `mean(decision)*100` reproduces
  `player_season_metrics.parquet`'s `decision_per_100` exactly (max
  absolute difference 0.0 across all 2,901 rows, row counts and per-group
  pass counts also matched exactly) — see Section 3. Built stage-1 units
  on `(player_id, team, competition_id, season_id)` with >=20 passes:
  mean Decision, SE (pass-level SD/sqrt(n)), n, zone shares, pressure
  share, and position-group mode (position recomputed from raw events —
  `passes_situation.parquet` drops this column on write — mapped through
  `task04_situation_context.position_group()`).
- **Step B2**: Gate E descriptive counts using the same
  `CLUB_COMPETITIONS`/`INTL_COMPETITIONS` classification defined in
  `task04_situation_context.py`.
- **Step B3**: built `src/decision_engine/reml_crossed.py`, a sparse
  Woodbury-identity REML estimator for two crossed random effects with
  known per-unit residual variance (R unavailable, per Amendment v2-3.2;
  statsmodels' `MixedLM` doesn't support per-observation known
  variances). Verified the sparse implementation against a brute-force
  dense computation on a small synthetic design before trusting it (see
  Section 8). Ran the 3-scenario x 100-simulation recovery test on the
  REAL design (real players, team contexts, and stage-1 SEs); all 3
  scenarios passed the brief's stated thresholds (Section 3).
- **Step B4**: fit the real 1,701 units (fixed effects: intercept +
  zone shares for defensive/final + pressure share, middle omitted as
  reference). Bootstrapped S's 95% CI by resampling players with
  replacement (1,000 draws, seed 20260920 — a resampled player's units
  all travel together, handled by the estimator's sparse group-index
  construction, which sums duplicate player/context entries correctly).
  Applied Gate E's three conditions.
- **Step B5**: (a) refit excluding only the units of movers whose
  club-context and international-context position-group modes do NOT
  match (all non-movers and position-matched movers retained). (b) For
  the 132 movers, computed each one's pass-count-weighted mean Decision
  pooled across their club-context unit(s) and, separately, their
  international-context unit(s), then the Pearson correlation between
  those two per-mover numbers, with a bootstrap CI (1,000 draws,
  resampling movers).

## 3. Numbers

**Part 1 — post-hoc checks, all 7 CONFIRMED candidates (not sorted by effect size):**

| zone | state | type | Gate D (Task 06) | PH-1 G | PH-1 95% CI | PH-1 n | PH-2 G | PH-2 95% CI | PH-2 n (share retained) | ROBUST |
|---|---|---|---|---|---|---|---|---|---|---|
| final | leading | lateral_medium | PASS | 0.000208 | [-0.00063, 0.00105] | 2913 | 0.000805 | [-0.00035, 0.00203] | 889 (30.5%) | **No** |
| final | leading | lateral_short | FAIL | 0.002823 | [0.00211, 0.00358] | 2087 | 0.001048 | [0.00004, 0.00208] | 798 (38.2%) | **No** (Gate D) |
| final | level | lateral_medium | FAIL | -0.000999 | [-0.00146, -0.00057] | 4801 | -0.000409 | [-0.00102, 0.00022] | 1406 (29.3%) | **No** |
| final | trailing | lateral_medium | PASS | -0.000879 | [-0.00178, 0.00011] | 2603 | -0.000020 | [-0.00093, 0.00085] | 809 (31.1%) | **No** |
| middle | leading | lateral_medium | PASS | 0.000370 | [0.00025, 0.00050] | 7941 | 0.000318 | [0.00014, 0.00050] | 2340 (29.5%) | **Yes** |
| middle | level | lateral_medium | PASS | 0.000565 | [0.00045, 0.00068] | 12320 | 0.000357 | [0.00024, 0.00051] | 3677 (29.8%) | **Yes** |
| middle | trailing | lateral_medium | PASS | 0.000942 | [0.00065, 0.00124] | 6608 | 0.000644 | [0.00020, 0.00110] | 1960 (29.7%) | **Yes** |

3 of 7 ROBUST. Consistent with Amendment v2-3.1's own preview
("sensitivity 3.6a ... flips sign in two final-third cells"):
`final|level|lateral_medium` and `final|trailing|lateral_medium` both
have negative PH-1 G. All under-pressure and defensive-zone candidates
had already been excluded before Part 1 (none of the 7 CONFIRMED
candidates are under pressure or in the defensive zone).

**Step B1 — reproduction check:** 2,901/2,901 player-competition-season
rows matched `player_season_metrics.parquet` exactly (max absolute
difference in `decision_per_100` = 0.0; 0 row-count mismatches; 0
per-group pass-count mismatches). Stage-1 units: **1,701** (player x
team context, >=20 passes), spanning **1,232** distinct players and
**157** distinct team contexts.

**Step B2 — Gate E counts:** 345 players contribute 2+ units; 132 are
club-plus-international movers; 119 of those 132 have the same
position-group mode in at least one club context and one international
context. (These three counts match Task 04's independent descriptive
count exactly, 2026-09-20 — a cross-task consistency check, not a new
computation choice.)

**Step B3 — parameter recovery test** (observed stage-1 variance =
3.8724e-6 [ddof=1 over the 1,701 unit means]; magnitude used for the
non-zero variance in every scenario = that value / 3 = 1.2908e-6; 100
simulations per scenario, seed 20260920):

| scenario | true var_player | true var_team | mean var_player_hat | mean var_team_hat | mean S_hat | mean \|S_hat - true S\| | PASS thresholds met | Result |
|---|---|---|---|---|---|---|---|---|
| (a) both = obs/3 | 1.2908e-6 | 1.2908e-6 | 1.2947e-6 | 1.3097e-6 | 0.4990 | 0.0323 | both within 10%; MAE(S) < 0.05 | **PASS** |
| (b) var_team=0 | 1.2908e-6 | 0 | 1.2843e-6 | 2.858e-9 | 0.9978 | 0.0022 | zero-var < 5% of non-zero; S within 0.05 of 1 | **PASS** |
| (c) var_player=0 | 0 | 1.2908e-6 | 3.762e-9 | 1.2586e-6 | 0.0030 | 0.0030 | zero-var < 5% of non-zero; S within 0.05 of 0 | **PASS** |

All 3 scenarios PASS, so Step B4 proceeded per the hard rule.

**Step B4 — real fit** (n=1,701 units):
- var_player = 4.9024e-7, var_team = 2.5967e-7
- **S = 0.6537**, 95% CI **[0.6263, 0.7846]** (1,000 player-resampling draws)
- Fixed effects: intercept = 0.002873, share_defensive = -0.002240,
  share_final = -0.001850, share_pressure = -0.002237 (middle is the
  reference zone)
- Gate E: fail-fewer-than-100 = No (345 >= 100); fail-zero-boundary = No
  (var_team is 53% of var_player, well above the 1% threshold used —
  see Section 4 for this threshold choice); fail-span-over-0.6 = No
  (span = 0.1583). **Verdict: PASS** (Study B is not restricted to
  descriptive-only).

**Step B5a — position-matched refit** (33 units excluded, belonging to
mover players whose club/international position groups don't match;
n=1,668 units, 1,219 players): var_player=4.8315e-7, var_team=2.5807e-7,
**S=0.6518**, 95% CI **[0.6305, 0.7854]** — materially unchanged from
the primary fit.

**Step B5b — mover club-vs-international correlation** (n=132 movers,
pass-count-weighted pooling within each side): **r = 0.0534**, 95% CI
**[-0.1260, 0.2590]** (1,000 bootstrap draws resampling movers).

## 4. Deviations from the brief

1. **Recovery-test scenario magnitude** (plan doesn't specify the exact
   non-zero variance for scenarios b/c): used `observed stage-1 variance
   / 3` in all three scenarios (same magnitude as scenario a), for
   consistency with (a)'s own stated convention. True fixed effects were
   set to 0 in every simulation (only the variance components are the
   recovery target; GLS profiling for b is exact given V regardless of
   b's true value).
2. **Gate E's "zero boundary" threshold** (not numerically specified):
   operationalized as `var_team < 1% of var_player`. The real fit's
   `var_team` was 53% of `var_player`, far from this threshold either
   way, so this choice was not close to binding.
3. **Step B1's Decision arithmetic reuses `decompose.py`'s formula but
   not its function call** — `build_per_pass_table` also computes
   Execution/realized value via the possession-value model, which Study
   B doesn't need; recomputing just the Decision line avoids an
   unnecessary full model pass over all 299 matches. The formula itself
   is unchanged (verified byte-exact against `player_season_metrics.
   parquet`, Section 3).

No other deviations. Every threshold, gate, and the v2-3.1 interpretation
rule were applied exactly as specified.

## 5. Problems and surprises

- Nothing was missing, broken, or malformed. The REML estimator's
  sparse-vs-dense cross-check (Section 8) matched to better than 1e-4 on
  a synthetic design before being trusted on the real one, and every one
  of the ~2,300 REML fits in this run (300 recovery sims + 1 real fit +
  1,000 bootstrap + 1,000 B5a bootstrap, `scipy.optimize`'s Nelder-Mead)
  reported `converged: true`.
- **What a face-value reading of S=0.65 would assume, and what would
  invalidate it** (per CLAUDE.md item 6): taking "65% of the variation
  in Decision quality is attributable to the player, not the team" at
  face value assumes (a) the crossed random-effects model is correctly
  specified — in particular that player and team-context effects are
  genuinely additive and uncorrelated, which cannot be tested directly
  with this design; (b) the fixed effects included (zone shares,
  pressure share) fully absorb role/situation-mix differences between
  players, so what's left in `var_player` isn't actually a proxy for
  "plays more often in favorable situations" that the model failed to
  capture; (c) the 20-pass floor per unit doesn't itself induce a
  selection effect (e.g., players who only get 20-40 passes in a context
  may be systematically different from those who get 200+, and Gate E
  doesn't test for this). If any of these fails, S's point estimate
  would still be numerically correct under this model but would not
  license the plain-language claim "decision quality is mostly a player
  trait" — that interpretive step is for the paper, not this task
  (CLAUDE.md rule 4).

## 6. Questions for the research lead
None. Every definition in plan section 4, Amendment v2-3, and Amendment
v2-3.2 (excluding v2-4, explicitly out of scope for this task) was
implementable exactly as written, and the recovery test passed, so no
STOP condition was triggered.

## 7. Files produced
- `src/decision_engine/task07_posthoc.py` — Part 1 script.
- `src/decision_engine/reml_crossed.py` — the shared sparse REML
  estimator, with a self-check (`__main__`) comparing it against a
  brute-force dense computation.
- `src/decision_engine/task07_study_b.py` — Part 2 (Steps B1-B5) driver.
- `data/processed/study_a_posthoc.parquet` — Part 1's 7-row table. Gitignored.
- `data/processed/study_b_units.parquet` — the 1,701 stage-1 units. Gitignored.
- `data/task07_posthoc.json`, `data/task07_study_b_recovery.json`,
  `data/task07_study_b.json` — run summaries. Gitignored.
- `docs/specs/analysis-plan-v2.md` — Amendments v2-3 and v2-4 (already
  present on disk before this task; committed here).
- Git commits made this task: `7f747da` (Amendments v2-3 + v2-4). Per
  CLAUDE.md item 9, the remaining new/changed files under `src/`/`docs/`
  from this task (the three scripts above, this results page, and
  `docs/JOURNAL.md`/`docs/ROADMAP.md`, which changed on disk
  independently of this task, same pattern as Tasks 05-06) are committed
  immediately after this page is written; those hashes are reported to
  the user directly, per their explicit instruction not to paste this
  page's contents in the reply.

## 8. Confidence
High on Step B1 (byte-exact reproduction of the frozen metric) and on
the REML estimator's correctness (sparse-vs-dense agreement on a
synthetic design, then a full 3-scenario/100-sim-each recovery test
passing on the real design before touching real data, exactly as the
gate required). Medium-high on the Study B headline itself: Gate E
passes cleanly and S's bootstrap CI is reasonably tight (span 0.158,
well under the 0.6 descriptive-only threshold), but Section 5's face-
value caveats (model specification, residual role/situation confounding,
floor-induced selection) are genuine and untested by anything in this
task. Part 1's ROBUST/NOT ROBUST calls are mechanical applications of an
already-fixed rule to already-computed quantities, so confidence there
tracks Task 06's own (medium-high, per that page's Section 8).
