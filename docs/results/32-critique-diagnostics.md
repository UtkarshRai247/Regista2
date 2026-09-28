# Task 32: Critique diagnostics (CRITIQUE-v5 problems A1-A5, B1)
Date: 2026-09-28
Status: COMPLETE

## Section checklist
- Step 0 (commit brief alone): COMPLETE (done in a prior turn, hash `a62af14`)
- Step 1 / A2 (typical-choice baseline bias): COMPLETE
- Step 2 / A3 (execution contamination): COMPLETE
- Step 3 / A4 (cross-fitted vs in-sample player tables): COMPLETE
- Step 4 / A5 (role-based reliability): COMPLETE
- Step 5 / A1 (out-of-match prediction): COMPLETE
- Step 6 / B1 (baseline comparison): COMPLETE

## 1. Headline
Both of the brief's pre-declared fix-trigger conditions fire (A2:
10/10 calibration deciles + zone spread 5.3x the overall mean Decision;
A3: deep-midfield completed-only Spearman 0.734<0.80 and incomplete
passes are 39.6% of between-player variance) — reported, not acted on.
Three further findings weaken claims the paper might otherwise make:
(1) role alone explains **63.9%** of between-player variance in mean
Decision, and within-role reliability is far below the all-roles 0.8191
figure for every role tested (e.g. CB=0.464, DM=0.451 at 200 passes) —
cross-role player comparisons rest on a confound this large; (2) the
LINEUP out-of-match test — a player's OWN mean Decision from his other
matches predicting this match's xG — is far weaker than the same-match
result and not significant for xG (coef=0.082, p=0.174, vs the
same-match cross-fitted H-O1 xg coef=+0.249, p=2.4e-10); (3) the raw
chosen-option EV (`ev_chosen`) alone predicts match xG/goals as well or
better than Decision in every specification tested, and when both are
fit together for goals, Decision's own coefficient turns **negative**
(-0.32 to -0.44, p<0.01) while raw EV stays strongly positive — Decision
does not demonstrably add predictive value over the naive baseline it
was built to beat, in-sample.

## 2. What I did
1. Confirmed Step 0 (brief-alone commit, `a62af14`) was already done in
   a prior turn of this same task; not repeated.
2. `task32_step1.py` (Step 1/A2): joined `pass_der_crossfit_v5.parquet`
   (292 matches) to each match's `options_ev_v4` chosen-candidate rows
   for zone/length/outcome/restriction metadata and re-ran
   `offside_v4.add_offside_v4_column` per match to get `offside_v4` on
   the chosen row. Computed (a)-(e) exactly as specified.
3. `task32_step2.py` (Step 2/A3): built full-corpus per-pass Decision
   (`pass_der_v8.parquet`, 292 matches) joined to
   `options_ev_v4`'s `pass_complete` flag. Computed the incomplete-pass
   share and variance decomposition (a); reused Task 28's
   `estimate_sigma2w_rho`/`empirical_bayes_shrink` (overall group) and
   Task 29's `estimate_sigma2w_rho`/`dersimonian_laird`/`shrink`
   (deep-midfield group) UNCHANGED, applied to completed-passes-only
   subsets (b); iterated every match with at least one incomplete pass,
   reading raw events + frames, to compute nearest-teammate distances
   for incomplete-pass end locations (c).
4. `task32_step3.py` (Step 3/A4): rebuilt the overall and deep-midfield
   tables from cross-fitted Decision using the identical Task 28 /
   Task 29 estimation methods, then compared to the existing v5 tables
   (`leaderboard_v5c.parquet`, `task29_dm_shrunk.parquet`).
5. Memory checked as free before each corpus-scale step; none came
   close to exhaustion (this task reads the 292-match corpus repeatedly,
   not the full 299-match raw corpus or the multi-GB EV directory in one
   pass).
6. Wrote and committed the Steps-0-3 checkpoint version of this page,
   per the brief's hard rule to commit after Steps 1-3 before continuing
   (hashes in Section 14).
7. `task32_step4.py` (Step 4/A5): assigned each of the 537 qualifying
   players a role by re-using Task 27 Step 1's exact per-pass-position
   technique (per-pass StatsBomb `position`, not modal), extended to the
   brief's 6-way group list at the same ≥50%-of-eligible-passes
   threshold. Ran `step8_regate.py`'s own `reliability_sweep` unchanged,
   filtered to each role's players (a); computed a passes-weighted
   one-way ANOVA of player-level mean Decision on role (b); refit Study
   B's PH-B1 by reusing the ALREADY-BUILT `study_b_units_v5.parquet`
   (Task 26 Step 6, not rebuilt) and `reml_crossed.fit_reml` plus
   `task26_step6_study_b.py`'s own `method_ii_parametric_bootstrap`
   (the already-selected PRIMARY interval method from Task 26, not a
   fresh coverage-selection run), replacing the position-group dummies
   with role dummies (c). Wall clock for (c): 12.3 seconds, well inside
   the 45-minute budget.
8. `task32_step5.py` (Step 5/A1): built LINEUP (leave-one-match-out per
   passer, ≥50-pass floor in the complement, ≥70% pass coverage per
   unit) and TEAM (leave-one-match-out per team-context, no floor
   stated in the brief, none added) versions of out-of-match Decision
   from the cross-fit corpus, standardised each, and fit H-O1 (both) and
   PH-O2 (LINEUP only) via `outcome_validation.py`'s unchanged builders
   (`build_team_match_units`, `add_possession_share`,
   `add_zone_pressure_shares`, `add_xg`, the dummy builders, `fit_ols`).
9. `task32_step6.py` (Step 6/B1): built b1 (`ev_chosen`), b2
   (`ev_chosen` minus the mean EV of all candidates for that pass), b3
   (`decision_new`, the standard Decision) per pass from `options_ev_v4`
   and `pass_der_v8.parquet` (full corpus, in-sample), took team-match
   means, standardised each, and fit H-O1/PH-O2 for xG and goals: each
   baseline alone, then b3+b1 and b3+b2 together. Also computed
   player-level b1/b2/b3 correlations within the 111 deep midfielders.
10. Wrote this final version of the results page and made the closing
    commit, per the brief's hard rule.

Reproduce with (from `src/engine_v2/`, `.venv` activated):
`python task32_step1.py && python task32_step2.py && python task32_step3.py && python task32_step4.py && python task32_step5.py && python task32_step6.py`

## 3. Why 292 matches, not 299 (required by the brief)
`data/raw/events/` has 299 match files. Every downstream v5 artifact
used in this task (`options_ev_v4`, `pass_der_v8.parquet`,
`pass_der_crossfit_v5.parquet`, `pass_policy_summary_v8.parquet`) has
exactly 292 matches — the same 292 in every case. The 7 matches dropped
are `3837706, 3877115, 3877170, 3877194, 3895158, 3895266, 3895309`.
Each of these 7 has a large raw events file (900-1,240 `Pass` events)
and a non-trivial frames file (~1-1.3MB) on disk — the data is not
simply missing. Directly invoking `grid.process_match(3837706)`
confirms the mechanism: `{'eligible': 0, 'no_frame': 1037, ...}` — for
this match, every single pass candidate fails
`frames_by_event.get(event_id)` even though the frames file exists and
is substantial. This means the frames file's own event IDs do not
correspond to this match's event IDs — a raw-data event-ID/frame-ID
misalignment specific to these 7 matches, not a bug in `grid.py` or any
downstream pipeline code. 292, not 299, is therefore the correct
population for every analysis in this task, since it is the population
every named input file already uses; this is disclosed rather than
silently assumed.

## 4. Step 1 (A2) — is the "typical choice" baseline unbiased?
Cross-fit corpus: 250,850 passes, 292 matches, 537 qualifying players.

**(a) Overall.** Mean Decision = 0.0026745 (n=250,850). 535/537
(99.63%) qualifying players have a positive mean cross-fitted Decision.

**(b) By zone / length / outcome** (mean Decision, mean `ev_chosen`,
mean `policy_weighted_ev`):

| zone | n | mean Decision | mean ev_chosen | mean policy_weighted_ev |
|---|---|---|---|---|
| defensive (x<40) | 54,065 | 0.001445 | -0.001506 | -0.002951 |
| middle (40≤x<80) | 135,225 | 0.001151 | 0.001941 | 0.000790 |
| final (x≥80) | 61,560 | 0.007100 | 0.018298 | 0.011198 |

| length (yd) | n | mean Decision | mean ev_chosen | mean policy_weighted_ev |
|---|---|---|---|---|
| 0-10 | 55,545 | **-0.000746** | 0.003223 | 0.003969 |
| 10-20 | 110,257 | 0.003366 | 0.006026 | 0.002661 |
| 20-30 | 52,214 | 0.004047 | 0.005714 | 0.001667 |
| 30+ | 32,834 | 0.003957 | 0.005044 | 0.001088 |

| outcome | n | mean Decision | mean ev_chosen | mean policy_weighted_ev |
|---|---|---|---|---|
| complete | 214,513 | 0.002244 | 0.004329 | 0.002085 |
| incomplete | 36,337 | 0.005216 | 0.010429 | 0.005213 |

Short passes (0-10y) are the only length bucket with negative mean
Decision. Incomplete passes have HIGHER mean Decision than complete
ones (0.005216 vs 0.002244) — the same direction problem A3 targets.

**(c) Calibration by decile of `policy_weighted_ev`** (n=25,085/decile):
mean `ev_chosen` exceeds mean `policy_weighted_ev` in **10 of 10**
deciles, from decile 0 (-0.00402 vs -0.00685) to decile 9 (0.03430 vs
0.02215). The rule's bar is ≥8/10 — met.

**(d) Restriction.** 18,707/250,850 passes (7.457%) have a chosen
option outside the policy's restricted candidate set
(p_success≥0.05, distance_u≤45, not offside). Mean Decision outside =
0.010859 vs inside = 0.002015 — a 5.39x asymmetry.

**(e) Policy accuracy** (cited from the crossfit summary,
`engine_v2_step6_crossfit_v5.json`'s `oof_policy` key, not recomputed):
top-1 = 8.07%, top-3 = 21.39%, n_covered = 232,099.

**A2 trigger check:** zone-mean spread in `policy_weighted_ev`
(final − defensive = 0.011198 − (−0.002951) = 0.014149) vs overall mean
Decision (0.002674): ratio ≈ 5.29x — spread exceeds overall mean
Decision. Combined with 10/10 deciles above, **both conditions of the
A2 rule are met.**

## 5. Step 2 (A3) — how much of Decision is execution?
Full corpus: 250,850 eligible passes, 292 matches (same population as
Step 1 and every other v5 artifact).

**(a)** 36,337/250,850 passes (14.486%) are incomplete. Mean Decision:
complete = 0.002458, incomplete = 0.005775. Between-player variance in
mean Decision: all-passes = 3.3321e-06, completed-only = 2.0138e-06 —
incomplete passes account for **39.56%** of the total (rule bar: >30%
— met).

**(b) Shrinkage on completed-only passes, same methods:**

| group | n players | sigma2_w | rho | mu (per-pass) | Spearman vs all-passes | p | n |
|---|---|---|---|---|---|---|---|
| overall (Task 28 method-of-moments) | 537 | 1.0934e-04 | 0.013681 | 0.002391 | **0.8554** | 5.7e-155 | 537 |
| deep midfield (Task 29 DerSimonian-Laird) | 111 | 6.3978e-05 | 0.005192 | 0.002131 (DL mu_w) | **0.7342** | 4.8e-20 | 111 |

Deep-midfield DL Q(110 df) = 139.65, p=0.0296 (still rejects
homogeneity on completed-only passes, as it did on all passes in Task
29: Q=140.53, p=0.0263 — essentially unchanged).

**A3 trigger check:** deep-midfield Spearman (0.7342) < 0.80 — met.
Incomplete-pass variance share (39.56%) > 30% — met. **Both conditions
of the A3 rule are independently met** (either alone would have been
sufficient).

**(c) Incomplete-pass geometry** (36,337 incomplete passes across 292
matches; 0 passes had missing location/frame data):

| measure | n | median | Q25 | Q75 |
|---|---|---|---|---|
| distance to nearest visible teammate (any angle) | 36,336 | 8.955 | 5.145 | 16.315 |
| distance to nearest visible teammate within 15° of the pass line | 20,569 | 8.435 | 4.328 | 16.790 |

Only 20,569/36,337 (56.6%) of incomplete passes have ANY visible
teammate within 15° of the pass line at all — for the other 43.4%, no
angle-restricted nearest-teammate distance exists. This is reported as
measured, per the brief ("informs a later fix; no fix here").

## 6. Step 3 (A4) — in-sample vs cross-fitted player tables
Cross-fit corpus: 250,850 passes, 292 matches. Re-deriving the
qualifying set from the cross-fit corpus's own ≥100-pass threshold
gives the same 537 players as the full-corpus v5 leaderboard (all 537
have ≥100 cross-fitted passes; no player fell under the bar due to the
7 missing matches).

**Per-pass correlation** (in-sample `decision_new` vs cross-fitted
`decision`, same match_id/event_id): r=0.9187, n=250,850.

| table | Spearman (rank_crossfit vs rank_v5) | p | n | top-20 overlap |
|---|---|---|---|---|
| overall | 0.9625 | 2.9e-305 | 537 | 16/20 |
| deep midfield | 0.9326 | 4.7e-50 | 111 | — |

Deep-midfield DerSimonian-Laird on cross-fitted Decision: Q(110 df) =
143.81, p=0.0168 (rejects homogeneity, consistent with Task 29's
p=0.0263 and Step 2(b)'s p=0.0296 above). Intervals entirely above the
group mean: **2** — the same two players as Task 29 and
`BENCHMARK-v5.md`:

| player | n_i (cross-fit) | shrunken_i_per100 |
|---|---|---|
| Vitor Machado Ferreira (Vitinha) | 1,764 | 0.2384 |
| Sergio Busquets i Burgos | 2,994 | 0.2367 |

Intervals entirely below the mean: 0 (unchanged from Task 29).

Per the brief's own instruction ("Decided now: cross-fitted tables
become the standard from here on, whatever this shows"), this is
reported as a directive already in force, not a decision made in this
task.

## 7. Step 4 (A5) — is Decision stable WITHIN a role?
Role assignment (≥50% of a qualifying player's 292-match-corpus eligible
passes at positions within one group, else MIXED), 537 qualifying
players:

| role | n players |
|---|---|
| CB | 159 |
| DM | 111 |
| FB | 99 |
| AM/W | 87 |
| CM | 35 |
| FW | 27 |
| MIXED | 19 |

**(a) Within-role reliability** (`step8_regate.py`'s `reliability_sweep`,
unchanged, median split-half Spearman-Brown; `n_units` = player ×
competition-season groups meeting the threshold):

| role | n players | median @100 (n_units) | @200 (n_units) | @300 (n_units) | @500 (n_units) |
|---|---|---|---|---|---|
| CB | 159 | 0.242 (201) | 0.464 (97) | 0.607 (43) | 0.774 (18) |
| FB | 99 | 0.449 (114) | 0.707 (48) | 0.778 (18) | 0.777 (10) |
| DM | 111 | 0.375 (123) | 0.451 (51) | 0.598 (21) | 0.498 (9) |
| CM | 35 | 0.493 (44) | 0.084 (19) | 0.354 (13) | 0.980 (3) |
| AM/W | 87 | 0.578 (80) | 0.605 (21) | 0.738 (11) | 0.661 (7) |
| FW | 27 | 0.432 (24) | -8.28 (7) | -7.50 (6) | -4.90 (5) |
| MIXED | 19 | 0.614 (21) | -0.269 (9) | -0.232 (5) | n/a (2) |
| **all roles (BENCHMARK-v5.md)** | 537 | — | **0.8191** | — | — |

Every role's within-role reliability at 200 passes is well below the
all-roles 0.8191 figure — CB (0.464) and DM (0.451) are roughly half;
CM, FW and MIXED go negative once `n_units` drops below ~20 (FW: -8.28
at 200 on only 7 units; MIXED: undefined at 500 with only 2 units).
These small-`n_units` negative values are noise from too few
player-seasons, not a real negative reliability, and are reported as
such rather than interpreted.

**(b) Variance explained by role.** Passes-weighted one-way ANOVA of
player-level mean Decision on role (7 groups): role explains
**63.87%** of the between-player variance.

**(c) PH-B1 refit with roles.** Reusing Task 26 Step 6's own
`study_b_units_v5.parquet` (1,041 of its 2,099 units have a player_id
that maps to one of the 537 qualifying players' roles; the rest lack a
role and were excluded) and its primary parametric-bootstrap interval
method:

| spec | S | 95% CI | n units | wall clock |
|---|---|---|---|---|
| PH-B1, engine-v5 position groups (BENCHMARK-v5.md) | 0.7683 | [0.6793, 0.8774] | 2,099 | — |
| PH-B1, roles (this step) | 0.7587 | [0.6057, 0.9072] | 1,041 | 12.3s |

S is similar (0.759 vs 0.768), but the role-based CI is wider (span
0.301 vs 0.098) on roughly half the units — a smaller, differently
composed sample, not a directly comparable refit of the same units.

## 8. Step 5 (A1) — does Decision predict matches it was not measured in?
Cross-fit corpus: 250,850 passes, 292 matches; 584 team-match units.

| version | units kept | note |
|---|---|---|
| LINEUP | 400/584 (68.5%) | ≥70% pass coverage by passers with ≥50 complement passes |
| TEAM | 562/584 (96.2%) | non-empty leave-one-match-out complement; no floor stated in the brief |

| outcome | spec | version | n | coef | p | same-match v5 (BENCHMARK-v5.md) |
|---|---|---|---|---|---|---|
| xg | H-O1 | LINEUP | 400 | 0.0816 | 0.174 | +0.2486 (p=2.4e-10) |
| xg | PH-O2 | LINEUP | 400 | -0.1082 | 0.406 | +0.2683 (p=2.5e-5) |
| goals | H-O1 | LINEUP | 400 | 0.1322 | 0.0497 | +0.2147 (p=2.3e-4) |
| goals | PH-O2 | LINEUP | 400 | 0.0308 | 0.831 | +0.2758 (p=2.1e-5) |
| xg | H-O1 | TEAM | 562 | 0.0255 | 0.553 | +0.2486 (p=2.4e-10) |
| goals | H-O1 | TEAM | 562 | 0.0118 | 0.796 | +0.2147 (p=2.3e-4) |

Every out-of-match coefficient is smaller than its same-match
counterpart; three of six are not significant at p<0.05, and LINEUP's
PH-O2 for xG is the wrong sign. Only LINEUP-goals-H-O1 clears p<0.05,
barely (p=0.0497), and its point estimate (0.132) is little more than
half the same-match value (0.215). No outcome threshold was set by the
brief, so none of this is scored pass/fail; reported as measured.

## 9. Step 6 (B1) — does the typical-choice model earn its place?
In-sample, full corpus: 250,850 passes, 583 team-match units (matches
with a `chosen` EV row and a `decision_new` value in both `pass_der_v8`
and `options_ev_v4`).

| outcome | spec | version | coef | p | R² |
|---|---|---|---|---|---|
| xg | H-O1 | b1 (`ev_chosen` alone) | 0.3946 | 1.7e-17 | 0.2639 |
| xg | H-O1 | b2 (uniform-baseline-adjusted) | 0.2723 | 1.3e-12 | 0.2180 |
| xg | H-O1 | b3 (Decision, standard) | 0.2751 | 8.5e-12 | 0.2172 |
| xg | PH-O2 | b1 | 0.4188 | 3.1e-8 | 0.4566 |
| xg | PH-O2 | b2 | 0.3303 | 1.4e-7 | 0.4480 |
| xg | PH-O2 | b3 | 0.3083 | 6.9e-7 | 0.4410 |
| goals | H-O1 | b1 | 0.6193 | 5.6e-20 | 0.3020 |
| goals | H-O1 | b2 | 0.2519 | 4.0e-5 | 0.1630 |
| goals | H-O1 | b3 | 0.2905 | 1.5e-6 | 0.1728 |
| goals | PH-O2 | b1 | 0.8916 | 2.6e-22 | 0.5217 |
| goals | PH-O2 | b2 | 0.3826 | 2.9e-9 | 0.3875 |
| goals | PH-O2 | b3 | 0.3778 | 7.5e-8 | 0.3860 |

Raw `ev_chosen` (b1) alone has the highest coefficient and R² of the
three baselines in **every one of the 8 specifications** (xg/goals x
H-O1/PH-O2). Decision (b3) does not out-perform either simpler baseline
in-sample.

**Joint fits (b3 together with b1, and b3 together with b2):**

| outcome | spec | pair | b3 coef (p) | other coef (p) | R² |
|---|---|---|---|---|---|
| xg | H-O1 | b3+b1 | -0.0000 (1.00) | b1: 0.3946 (5.3e-9) | 0.2639 |
| xg | PH-O2 | b3+b1 | 0.0907 (0.315) | b1: 0.3392 (0.0031) | 0.4583 |
| xg | H-O1 | b3+b2 | 0.1325 (0.201) | b2: 0.1524 (0.139) | 0.2201 |
| xg | PH-O2 | b3+b2 | 0.0195 (0.895) | b2: 0.3124 (0.0492) | 0.4480 |
| goals | H-O1 | b3+b1 | **-0.3222 (3.6e-6)** | b1: 0.8788 (1.1e-21) | 0.3258 |
| goals | PH-O2 | b3+b1 | **-0.4432 (3.2e-5)** | b1: 1.2803 (4.2e-17) | 0.5483 |
| goals | H-O1 | b3+b2 | 0.3552 (0.0020) | b2: -0.0693 (0.570) | 0.1732 |
| goals | PH-O2 | b3+b2 | 0.1591 (0.373) | b2: 0.2366 (0.173) | 0.3887 |

When Decision (b3) and raw `ev_chosen` (b1) are fit together for goals,
b3's own coefficient is **negative and significant** (-0.32 to -0.44,
p<0.01) while b1 stays strongly positive — Decision's information is
redundant with, and in this joint specification partially working
against, the raw candidate value it is built from. Against b2 (the
uniform baseline), the two trade off which one is significant by
outcome/spec, with neither dominating.

**Within the 111 deep midfielders, player-level correlations**
(pooled b1/b2/b3 per player, full corpus):

| pair | r |
|---|---|
| b1 vs b2 | 0.841 |
| b2 vs b3 | 0.920 |
| b1 vs b3 | 0.780 |

All three are strongly positively correlated (they share the same
underlying EV values), but b1 (raw EV) is noticeably less correlated
with b3 (Decision) than with b2 (the uniform-baseline version) —
consistent with b3 (subtracting a policy-weighted, not uniform,
baseline) reordering players relative to a simple EV ranking more than
b2 does.

## 10. Decision-rule summary (reported, not acted on — no engine change was made)
- **A2 fix (recalibrate the typical-choice baseline): PRIORITISED**
  per the brief's rule — both conditions in Section 4 are met.
- **A3 fix (infer the intended target for incomplete passes):
  PRIORITISED** per the brief's rule — both conditions in Section 5 are
  met (either alone would suffice).
- The brief caps this at "at most two fixes go forward" — both
  qualifying fixes are A2 and A3, so both, per the brief's own rule.
  No fix was implemented in this task; the hard rules for Task 32
  explicitly forbid any engine change, retraining, or new EV corpus.
  Which fix (if either) is actually built, and in what order, is a
  question for the research lead, not a choice made here.
- **A1, A5, B1 do not trigger fixes** (per the brief), but all three
  inform what the paper may claim: A5 (Section 7) shows role explains
  63.9% of between-player Decision variance and within-role reliability
  is well below the all-roles figure at every threshold tested; A1
  (Section 8) shows the out-of-match signal is much weaker than the
  same-match signal and mostly not significant; B1 (Section 9) shows
  raw `ev_chosen` matches or beats Decision on every in-sample outcome
  spec tested, and Decision's marginal coefficient on goals is negative
  once raw EV is included.

## 11. Deviations from the brief
None from the hard rules or the numbered steps' own specification.
Disclosed operationalizations:
- Step 3's "same methods" was read as reusing Task 28's and Task 29's
  functions completely unchanged (not re-derived), including
  re-deriving the ≥100-pass qualifying set from the cross-fit corpus
  itself rather than reusing the full-corpus 537 IDs verbatim — since
  the cross-fit corpus has 7 fewer matches, a player could in principle
  fall under the threshold there even after clearing it on the full
  corpus. In this data no player did (537 both ways), disclosed here
  rather than assumed identical without checking.
- Step 2(c)'s "nearest visible teammate" was read as StatsBomb's own
  360 freeze-frame teammate locations (`teammate=True` in the frame),
  matching how `offside_v4.py` already defines visibility elsewhere in
  this codebase — not re-derived from a different visibility rule.
- Step 4(c)'s "PH-B1 refit with these roles" was read as reusing Task
  26 Step 6's already-built Study B units (`study_b_units_v5.parquet`)
  and its already-selected PRIMARY interval method (parametric
  bootstrap), replacing only the position-group dummies with role
  dummies, rather than rebuilding Study B's per-pass covariates and
  rerunning the full coverage-selection procedure from scratch. This
  means the role-based PH-B1's 1,041 units are not the same 2,099 units
  the original PH-B1 used (players without a mapped role were dropped;
  see Section 7) — a smaller, differently composed sample, not a
  directly comparable refit, disclosed rather than presented as
  equivalent. The reference category for the role dummies is MIXED
  (the residual, no-majority group), parallel to how the original
  PH-B1 left Midfielder as the implicit reference.
- Step 5's TEAM version has no stated minimum-passes floor in the
  brief (unlike LINEUP's explicit ≥50); none was added, so a
  team-context with very few passes in its complement can still
  produce a TEAM score. This is the brief's own asymmetry, not an
  omission introduced here.

## 12. Problems and surprises
- Two bugs were caught and fixed while writing `task32_step1.py` and
  `task32_step3.py` before their final runs (missing `passer_y`/
  `candidate_x`/`candidate_y` columns in a `read_parquet` call; a wrong
  column name `rank_overall` instead of the actual `rank_overall_v5c`,
  and a missing `player_name` merge onto the deep-midfield cross-fitted
  table) — both were code bugs in this task's own new scripts, caught
  by the scripts crashing on first run, not silent errors. Fixed and
  reran; final numbers above are from the corrected runs.
- 43.4% of incomplete passes in Step 2(c) have no teammate within 15°
  of the pass line at all — the angle-restricted geometry diagnostic is
  undefined for nearly half of incomplete passes.
- Both A2 and A3 fix-trigger conditions independently fire, and A3's
  fires by a wide margin on the variance-share test (39.56% vs a 30%
  bar) — this is not a marginal call.
- Step 4(a)'s within-role reliability at 200/300/500 passes goes sharply
  negative for FW and MIXED once `n_units` drops below ~10 — these are
  small-sample artifacts of the split-half procedure, not evidence of
  genuinely negative reliability, and are reported as measured rather
  than smoothed over or excluded.
- Step 5's LINEUP and TEAM out-of-match tests both collapse relative to
  the same-match figures in `BENCHMARK-v5.md` — LINEUP's PH-O2 for xG is
  even the wrong sign. This directly bears on A1's concern that the
  outcome test "may be mechanical": a large share of the same-match
  relationship does not survive moving the Decision measurement out of
  the match being predicted.
- Step 6's finding that raw `ev_chosen` (b1) beats Decision (b3) on
  every in-sample spec, and that b3's coefficient flips negative when
  fit jointly with b1 for goals, is the most direct evidence in this
  task that the "typical-choice" baseline subtraction (Decision's whole
  reason for existing over a raw-EV ranking) is not earning its keep,
  at least under this in-sample, team-match-level test.

## 13. Questions for the research lead
None. Every decision rule resolved cleanly from the brief's own fixed
thresholds (Section 10), and every judgment call required to execute
an otherwise-unambiguous step is disclosed in Section 11 rather than
raised here as a blocking question.

## 14. Files produced
- `src/engine_v2/task32_step1.py` — new. Step 1/A2 diagnostics.
- `src/engine_v2/task32_step2.py` — new. Step 2/A3 diagnostics.
- `src/engine_v2/task32_step3.py` — new. Step 3/A4 cross-fitted table
  rebuild.
- `src/engine_v2/task32_step4.py` — new. Step 4/A5 role-based
  reliability, variance decomposition, and PH-B1 role refit.
- `src/engine_v2/task32_step5.py` — new. Step 5/A1 out-of-match
  LINEUP/TEAM prediction.
- `src/engine_v2/task32_step6.py` — new. Step 6/B1 baseline comparison.
- `data/engine_v2_task32_step1.json` through
  `data/engine_v2_task32_step6.json` — new summary JSONs (under `data/`,
  not committed).
- `docs/results/32-critique-diagnostics.md` — this file.
- No engine artifact, table, or config file was modified or overwritten;
  `study_b_units_v5.parquet` was read, not rewritten.
- Commit hashes: `a62af14` (Step 0, brief alone, prior turn), `cb9c592`
  (Steps 1-3 checkpoint code + page), `067e783` (Steps 1-3 hash-record
  follow-up), `<pending>` (this final commit: Steps 4-6 code + full
  page), `<pending>` (final hash-record follow-up).

## 15. Confidence
High confidence in Steps 1-4's numbers: every custom statistic reuses
Task 28's/Task 29's/Task 26's own already-validated functions unchanged,
the two bugs hit while writing new code were caught by crashes (not
silent), and Step 3's cross-fitted deep-midfield finding (2 players
above the mean, same identities) independently reproduces Task 29's
result under a different Decision estimate. Steps 5 and 6 are more
consequential findings than measurement exercises: the LINEUP/TEAM
out-of-match collapse (Step 5) and the raw-EV-beats-Decision result
(Step 6) both bear directly on whether Decision, as currently built, is
earning the claims made for it — these are reported plainly as measured,
not softened, per the reporting discipline's "weakest evidence" rule.
The weakest link technically is Step 2(c)'s incomplete-pass geometry
(undefined for 43.4% of incomplete passes) and Step 4(c)'s smaller,
differently-composed role-refit sample (1,041 vs 2,099 units) — both
already flagged as partial rather than fully comparable measurements.
