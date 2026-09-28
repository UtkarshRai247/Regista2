# Task 32: Critique diagnostics (CRITIQUE-v5 problems A1-A5, B1)
Date: 2026-09-28
Status: PARTIAL (Steps 0-3 complete; Steps 4-6 not yet run — this page
will be replaced by a full version, per the brief's own two-commit rule:
"Commit the results page after Steps 1-3, then again at the end.")

## Section checklist
- Step 0 (commit brief alone): COMPLETE (done in a prior turn, hash `a62af14`)
- Step 1 / A2 (typical-choice baseline bias): COMPLETE
- Step 2 / A3 (execution contamination): COMPLETE
- Step 3 / A4 (cross-fitted vs in-sample player tables): COMPLETE
- Step 4 / A5 (role-based reliability): NOT RUN (this checkpoint)
- Step 5 / A1 (out-of-match prediction): NOT RUN (this checkpoint)
- Step 6 / B1 (baseline comparison): NOT RUN (this checkpoint)

## 1. Headline
Both of the brief's own pre-declared fix-trigger conditions fire on
this data. A2: `ev_chosen` exceeds `policy_weighted_ev` in 10 of 10
calibration deciles (rule: ≥8/10), and the final-zone vs
defensive-zone spread in `policy_weighted_ev` (0.01415) is ~5.3x the
overall mean Decision (0.00267). A3: within the 111 deep midfielders,
Decision recomputed on completed-only passes correlates with the
all-passes version at Spearman rho=0.734 (n=111, p=4.8e-20) — below
the rule's 0.80 bar — and incomplete passes alone account for 39.6% of
total between-player variance in mean Decision (rule: >30%). Per the
brief's own rule this means an A2 fix AND an A3 fix are both
prioritised; this task does not act on either — no engine change was
made, per the hard rules.

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
5. Memory checked as free (well above the 40%/3GB gate) before each
   corpus-scale step; none came close to the limit (this task reads
   the 292-match corpus repeatedly, not the full 299-match raw corpus
   or the multi-GB EV directory in one pass).
6. Wrote this results page covering Steps 0-3 and committed it, per the
   brief's hard rule to commit after Steps 1-3 before continuing.

Reproduce with (from `src/engine_v2/`, `.venv` activated):
`python task32_step1.py && python task32_step2.py && python task32_step3.py`

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

## 7. Decision-rule summary (reported, not acted on — no engine change was made)
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

## 8. Deviations from the brief (Steps 0-3 only)
None from the hard rules or the numbered steps' own specification.
Two disclosed operationalizations:
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

## 9. Problems and surprises
- Two bugs were caught and fixed while writing `task32_step1.py` and
  `task32_step3.py` before their final runs (missing `passer_y`/
  `candidate_x`/`candidate_y` columns in a `read_parquet` call; a wrong
  column name `rank_overall` instead of the actual
  `rank_overall_v5c`, and a missing `player_name` merge onto the
  deep-midfield cross-fitted table) — both were code bugs in this
  task's own new scripts, caught by the scripts crashing on first run,
  not silent errors. Fixed and reran; final numbers above are from the
  corrected runs.
- 43.4% of incomplete passes in Step 2(c) have no teammate within 15°
  of the pass line at all — the angle-restricted geometry diagnostic is
  undefined for nearly half of incomplete passes. This narrows how much
  Step 2(c)'s within-15° distribution alone can inform a future fix.
- Both A2 and A3 fix-trigger conditions independently fire, and A3's
  fires by a wide margin on the variance-share test (39.56% vs a 30%
  bar) — this is not a marginal call.

## 10. Questions for the research lead
None yet from Steps 0-3 — the decision rules resolved cleanly (both
fire) and no ambiguity in the brief's own text required a judgment
call beyond the two disclosed operationalizations in Section 8.
Section 6 of the final version of this page (after Steps 4-6) may add
more.

## 11. Files produced (Steps 0-3)
- `src/engine_v2/task32_step1.py` — new. Step 1/A2 diagnostics.
- `src/engine_v2/task32_step2.py` — new. Step 2/A3 diagnostics.
- `src/engine_v2/task32_step3.py` — new. Step 3/A4 cross-fitted table
  rebuild.
- `data/engine_v2_task32_step1.json`, `data/engine_v2_task32_step2.json`,
  `data/engine_v2_task32_step3.json` — new summary JSONs (under `data/`,
  not committed).
- `docs/results/32-critique-diagnostics.md` — this file (checkpoint
  version; will be overwritten with the full Steps 0-6 version before
  the final commit).
- No engine artifact, table, or config file was modified or overwritten.

## 12. Confidence
High confidence in the Steps 1-3 numbers themselves: every custom
statistic reuses Task 28's/Task 29's own already-validated functions
unchanged, both bugs hit while writing new code were caught by crashes
(not silent), and Step 3's cross-fitted deep-midfield finding (2 players
above the mean, same identities) independently reproduces Task 29's
result under a different Decision estimate. The weakest link is Step
2(c)'s incomplete-pass geometry: the within-15° distance is undefined
for 43.4% of incomplete passes, so it characterizes a majority-but-not-
all subset, and — per the brief's own framing — informs a future fix
rather than settling anything on its own.
