# BENCHMARK v5 — the baseline every improvement is measured against

Frozen 2026-09-28 by the research lead, after Task 29. This is the
rollback point. Nothing here is changed after the fact; a later
benchmark gets a new file (BENCHMARK-v6.md), never an edit to this one.

## What "engine v5" is
Task 25's artifacts (corrected coordinates, in-possession value rows,
own-event labels, rotated cross-team prev location):
value_model_for_v5.json, value_model_against_v5.json,
pass_success_model_v3.json, offside rule R1_K10, softmax temperature
0.1562, policy scored by policy_score_v8.py, Decision/Risk from
step8_regate.py. Player tables: leaderboard_v5c.parquet (overall, Task
28) and task29_dm_shrunk.parquet (deep midfield, Task 29). Exact file
checksums: docs/benchmark/manifest-v5.txt (Task 31). Git tag:
`benchmark-v5`.

## Headline numbers

### Falsification battery (results/25)
| Test | Bar | v5 |
|---|---|---|
| T1 median snap displacement | <= 2u | 1.6125 |
| T2 numerical-advantage effect | >= 10% IQR; sign reported | +0.01272 (positive) |
| T3 Spearman(EV, p_success) | < 0.90 | -0.2396 |
| T4a unmarked vs marked | unmarked higher | 0.01853 vs -0.00883 |
| T4b open space vs cluster | open higher | 0.00536 vs -0.04014 |
| T4c through ball vs corpus p90 | >= p90 | 0.02378 vs 0.01169 |
| T5 pass-success calibration | <= 5pp every bucket | 2.18pp max |
| T6 reliability at 200 passes | >= 0.60 | 0.8191 |

### Outcome validation: decision_z coefficient (p)
| Spec | Study, cross-fitted (583 team-matches; results/25) | Holdout, frozen (250; results/26) |
|---|---|---|
| xG H-O1 | +0.2486 (2.4e-10) | +0.2611 (6.7e-6) |
| xG H-O2 (with completion, progressive, xA) | +0.0917 (0.069) | +0.0664 (0.326) |
| xG PH-O1 | +0.2404 (1.1e-7) | +0.1764 (0.037) |
| xG PH-O2 (team-context FE) | +0.2683 (2.5e-5) | not computable |
| xG PH-O4 | +0.2753 (6.2e-9) | +0.3762 (5.6e-7) |
| Goals H-O1 | +0.2147 (2.3e-4) | +0.3358 (1.3e-6) |
| Goals H-O2 | +0.2641 (3.9e-4) | +0.2797 (2.1e-4) |
| Goals PH-O1 | +0.2412 (8.4e-6) | +0.3702 (3.0e-7) |
| Goals PH-O2 | +0.2758 (2.1e-5) | not computable |
| Goals PH-O4 | +0.2416 (1.6e-4) | +0.4652 (5.7e-11) |
Uncorrected engine (v1), xG H-O1: -0.1381 (1.8e-4).

### Player level
| Quantity | v5 | Source |
|---|---|---|
| Median reliability at 100 passes | 0.7252 | results/26 |
| Qualifying players (>= 100 passes) | 537 | results/26 |
| Decision vs Risk (overall) | r = 0.80 | results/26 |
| Decision vs xA per 90 (pooled) | r = 0.57 | results/26 |
| Study B S (B4, parametric bootstrap) | 0.7939 [0.7086, 0.8866] | results/26 |
| PH-B1 (position FE) | 0.7683 [0.6793, 0.8774] | results/26 |
| PH-B3 (players with 2+ units) | 0.8589 [0.7545, 0.9474] | results/26 |
| PH-B2 mover r_true | 0.6234 [0.2586, 1.0] | results/26 |
| PH-B2 residualised on zone/pressure | 0.2716 [-0.1372, 0.6626] | results/27 |
| Deep midfielders (>= 50% DM passes) | 111 | results/27 |
| Within-DM: Decision vs xA / completion / progressive | 0.18 / -0.19 / -0.06 | results/27 |
| Within-DM heterogeneity (DL Q, 110 df) | 140.53, p = 0.0263 | results/29 |
| Within-DM intervals entirely above / below mean | 2 (Vitinha, Busquets) / 0 | results/29 |
| Within-DM match-split reliability (>= 500 passes, n = 16) | 0.1846 [-0.567, 0.567] | results/29 |

## Known defects carried by v5 (see docs/CRITIQUE-v5.md)
Execution not computed (cross-team defect); Decision's zero point
(mean Decision > 0 for every group); chosen option = where the ball
ended, not where it was aimed; player tables built from in-sample
(full-corpus) models; outcome tests measure Decision and outcomes in
the same match.

## Rules for any improvement
1. Every change is specified in a brief BEFORE it runs, with what it
   must beat on this page.
2. Any engine change re-runs the full falsification battery and the
   cross-fitted outcome validation, reported beside the v5 column.
3. The women's holdout has been used once (Task 26). It is used ONE more
   time only, on the final candidate engine, with the gate declared in
   advance. Improvements are never checked against it along the way.
4. A change that makes any v5 number worse is reported, not hidden, and
   the author decides whether the trade is worth it.
5. If the improvement cycle does not produce a clearly better,
   re-validated engine by the submission deadline, v5 is what gets
   submitted.
