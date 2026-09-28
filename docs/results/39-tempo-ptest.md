# Task 39: Does tempo show up in results? (pass-level test, study sample)
Date: 2026-09-28
Status: COMPLETE (every section run; two inputs had to be regenerated, see Section 4)

## Checklist
| Section | Status |
|---|---|
| Step 0 — brief committed alone | COMPLETE (9b2e49f, by the research lead) |
| Step 1 — inputs, n, mapping to Task 35 rows | COMPLETE |
| Step 2 — P-test, all passers, S_move and S_hold, control, Holm | COMPLETE |
| Step 3 — within the 111 deep midfielders | COMPLETE |

## 1. Headline
Neither tempo metric is detected across all passers:
- MOVE_ON_SPEED: −0.008 xG per 100 passes per SD, 95% CI [−0.032, 0.017], Holm p = 0.60, MDE 0.035, n = 154,116 passes / 328 passers.
- HOLD_VARIATION: +0.015 per 100, CI [−0.014, 0.045], Holm p = 0.60, MDE 0.042, n = 161,657 / 381.

The positive control is clearly positive on both sets of rows. Under the brief's fixed rule, tempo is "a stable style measure with no demonstrated link to results in this sample" (MDE 0.035 for MOVE_ON_SPEED and 0.042 for HOLD_VARIATION, xG per 100 passes per SD).
Step 3 (report only, 61 and 72 deep midfielders): MOVE_ON_SPEED +0.059 per 100 (raw p = 0.028, Holm p = 0.056); HOLD_VARIATION +0.032 (p = 0.12).

## 2. What I did
- Step 0: brief committed alone in 9b2e49f by the research lead.
- Run: `.venv/bin/python src/engine_v2/task39_tempo_ptest.py`
  1. **Rebuilt Task 35's pass table exactly:** `task33_step3_f_state.build_feature_table`, `task35_ptest.net_xg_after`, `task35_ptest.crossfit_g` for net xG and completion g, the `pass_der_crossfit_v5` join, and `task32_step4.assign_roles`.
  2. **Asserted that Task 35's own (a) v5-Decision and positive-control coefficient and SE reproduce exactly** from its saved JSON (relative tolerance 1e-9). Both did: coef 0.0007469384836865591 and 0.02201331162937713, identical to Task 35.
  3. **Re-ran `src/tempo/redesign_metrics.main()`** with Task 26 Step 2's patch, applied by importing `redesign_metrics_v2.py` unchanged. All output paths were redirected to new Task 39 files. This returns the per-pass residuals with match_id/event_id.
  4. **Asserted the residuals are identical** in row order, player and value (atol 1e-12) to the stored `tempo_redesign_{move,hold}_residuals_v2.parquet`. Both passed.
  5. **S per (passer, match), leave-one-match-out** over all the passer's other matches, pooled across competitions:
     - S_move = mean of move residuals;
     - S_hold = SD (ddof = 1) of hold residuals.
     These are the preregistered per-player definitions in `redesign_metrics.py`, applied to the complement. ≥100 tempo-eligible passes of that metric elsewhere are required.
  6. **Model:** `task35_ptest.fe_fit`, Task 35's model unchanged: Y ~ S + g_oof + role FE + team-match FE, SE clustered by passer. Holm correction across the two metrics, separately in Step 2 and Step 3.
  7. **Positive control** (completion ~ other-match completion rate, completion g) run on each metric's analysis rows.

## 3. Numbers

### Step 1 — inputs and mapping
- Tempo-eligible passes: move 180,375; hold 209,775. These are Task 26 Step 2's populations, reproduced exactly.
- Mapping onto Task 35's 239,588 pass rows by event_id:
  - move: 156,267 of 180,375 (86.6%) are Task 35 rows;
  - hold: 180,359 of 209,775 (86.0%) are Task 35 rows.
  - Seen from Task 35's side, 156,267 of its rows are move-eligible and 180,359 are hold-eligible.
- The analysis rows are Task 35 pass rows whose passer has S (the pass itself need not be tempo-eligible, because S is the passer's other-match value):
  - S_move: 154,116 rows, 328 passers, 469 team-matches.
  - S_hold: 161,657 rows, 381 passers, 481 team-matches.
- Raw SD of S before standardising: S_move 0.0534; S_hold 0.2247.
- g out-of-fold R^2 (Task 35's, regenerated): net xG 0.0448; completion 0.1282.
- Role "NONE" rows (passer outside Task 32's 537): 87 (S_move) and 147 (S_hold).

### Step 2 — all passers

| Measure | n passes | n passers | team-matches | coef per SD | per 100 | 95% CI (per 100) | p | p Holm | MDE 80% (per 100) |
|---|---|---|---|---|---|---|---|---|---|
| **S_move (MOVE_ON_SPEED)** | 154,116 | 328 | 469 | −0.0000756 | −0.0076 | [−0.0322, 0.0171] | 0.548 | **0.601** | 0.0352 |
| **S_hold (HOLD_VARIATION)** | 161,657 | 381 | 481 | +0.000154 | +0.0154 | [−0.0138, 0.0446] | 0.300 | **0.601** | 0.0417 |

Positive control (completion, on the same rows):

| Rows | n | coef per 100 (pp) | 95% CI | p | MDE |
|---|---|---|---|---|---|
| S_move rows | 153,599 | +2.190 | [1.740, 2.640] | 1.4e-21 | 0.643 |
| S_hold rows | 160,877 | +2.245 | [1.825, 2.666] | 1.3e-25 | 0.601 |
| Task 35 original (all rows) | 168,855 | +2.201 | [1.798, 2.604] | 9.5e-27 | 0.576 |

The control's n is slightly below each metric's n because its S (completion rate) needs ≥100 eligible passes elsewhere.

### Step 3 — the 111 deep midfielders (S standardised within these rows)

| Measure | n passes | n players | team-matches | coef per SD | per 100 | 95% CI (per 100) | p | p Holm | MDE 80% (per 100) |
|---|---|---|---|---|---|---|---|---|---|
| S_move | 30,680 | 61 | 360 | +0.000587 | +0.0587 | [0.0063, 0.1111] | 0.028 | 0.056 | 0.0748 |
| S_hold | 31,914 | 72 | 386 | +0.000315 | +0.0315 | [−0.0078, 0.0709] | 0.116 | 0.116 | 0.0562 |

Positive control on the same rows:
- S_move rows: +0.545 pp, 95% CI [0.105, 0.985], p = 0.015.
- S_hold rows: +0.678 pp, CI [0.174, 1.183], p = 0.008.

### Fixed claim rule, applied mechanically
Step 2 Holm p is 0.601 for both metrics, so neither is < 0.05. For both: "a stable style measure with no demonstrated link to results in this sample". The MDE at 80% power is 0.035 (MOVE_ON_SPEED) and 0.042 (HOLD_VARIATION) xG per 100 passes per SD. Step 3 is reported, not claimed.

## 4. Deviations from the brief
- **The residual files named in the brief could not be used as they are.** `tempo_redesign_{move,hold}_residuals_v2.parquet` have no match_id or event_id, so neither "OTHER matches" nor the event_id mapping is possible from them. I re-ran the unchanged Task 26 Step 2 computation (`redesign_metrics_v2.py`'s patch plus `redesign_metrics.main()`), which returns the residuals with ids, and wrote to new files only. The residuals were asserted identical to the stored v2 files before use. No tempo definition or earlier artifact changed.
- **Task 35's g_oof was not persisted**, so "reuse, do not refit" could not be done by loading it. It was regenerated with Task 35's own function on the identical inputs. Task 35's (a) and control results were asserted to reproduce to 1e-9 before any tempo number was computed. This is a re-execution of Task 35's fit, not a new fit.
- **S pooling:** the leave-one-match-out S pools all of a passer's other matches across competitions. The preregistered tempo metrics were per player × competition-season, while Task 26 Step 5 pooled by player. The brief says "his OTHER matches", and I read that as all of them.
- **Positive control:** "re-report Task 35's on the same rows" was run as Task 35's control specification restricted to each metric's analysis rows. The original Task 35 control is shown beside it.
- **Holm correction** was also applied within Step 3 (two metrics), since the brief says "report the same columns".

## 5. Problems and surprises
- Across all passers, both metrics' 95% CIs exclude effects larger than about +0.017 (move) and +0.045 (hold) per 100 passes per SD. For comparison, Task 35's v5 Decision estimate was +0.075.
- Within deep midfielders, MOVE_ON_SPEED has raw p = 0.028 (Holm 0.056), and the estimate (+0.059) is below its MDE (0.075). The all-passer estimate for the same metric is −0.008. Step 3 is report-only under the brief.
- In `redesign_metrics.py` the move residual is on log(interval to the team's next open-play pass). A higher MOVE_ON_SPEED therefore means a longer interval relative to context; the sign is stated for reading only.

## 6. Questions for the research lead
- None blocking.
- Q1: Should the tempo S instead be per player × competition-season (the preregistered unit) rather than pooled across competitions?

## 7. Files produced
- `src/engine_v2/task39_tempo_ptest.py`.
- `data/engine_v2_task39_tempo_ptest.json`.
- `data/processed/tempo_task39_metrics.parquet`, `tempo_task39_move_residuals.parquet`, `tempo_task39_hold_residuals.parquet`, and `data/tempo_task39_redesign_rerun.json`. These are redirected re-run outputs; the stored v2 files are unchanged.
- None of the data/ files are committed.
- Side effects: none else. No memory writes. JOURNAL.md and AGENTS.md untouched. Holdout untouched.
- Commits: brief 9b2e49f (research lead); this task 689e5fe.

## 8. Confidence
- Inputs are verified identical to the earlier artifacts, the test reproduces Task 35 exactly, and the control works on the same rows.
- The weakest link is the pooling choice for S (Q1).
