# Task 42: Improvement round 2: role-appropriate outcomes and press resistance (study sample only)
Date: 2026-09-28
Status: PARTIAL (Step 1 run; Steps 2-3 and the claim family NOT RUN yet — interim commit required by the brief)

## Checklist
| Section | Status |
|---|---|
| Step 0 — brief committed alone | COMPLETE (107bed0, by the research lead) |
| Memory gate | COMPLETE (54% free, ~4.52 GB, 16:01 PDT, before Step 1) |
| Step 1 (A) — Y_F3 / Y_SHOT P-tests | COMPLETE |
| Step 2 (B) — press resistance | NOT RUN |
| Step 3 (C) — progressive availability | NOT RUN |
| Claim family (Holm) | NOT RUN |

## 1. Headline
Step 1 only (study sample only). None of the 12 tests has p < 0.05: v5 Decision, MOVE_ON_SPEED and RQ_rel, each against Y_F3 and Y_SHOT, for all players and for deep midfielders. The smallest p is 0.15.
The MDEs are large on these binary outcomes: 0.32-1.44 percentage points per SD per 100 units.
The retention control on deep-midfielder RQ_rel rows is not positive: −0.155 pp (p = 0.16) for Y_F3 and −0.403 pp (p = 0.031) for Y_SHOT.

## 2. What I did
- Step 0: the brief was committed alone by the research lead in 107bed0.
- Asked before running: which positive control should reception-unit tests use? The author chose a **retention control**:
  - Y = the receiver's next action keeps the ball (PR_keep's definition);
  - S = his other-match retention rate (same ≥100 floor);
  - g refit on the same reception features.
- `.venv/bin/python src/engine_v2/task42_step1.py`:
  1. Builds Y_F3 / Y_SHOT and receipt next-action outcomes per match (`src/engine_v2/task42_outcomes.py`).
  2. Rebuilds Task 35's pass table and asserts Task 35 (a) reproduces exactly.
  3. Re-runs Task 26 Step 2's tempo computation with outputs redirected to new Task 42 files. Its residuals are asserted identical to the stored v2 files.
  4. Takes S from `task35_ptest.add_s` (Decision, RQ_rel, completion, retention) and Task 39's `s_for_rows` (MOVE_ON_SPEED).
  5. Refits g per outcome with `task35_ptest.crossfit_g`, and fits with `task35_ptest.fe_fit`.

## 3. Numbers

### Step 1 — base rates (Y_F3 only on units starting at x < 80)

| Units | n | units eligible for Y_F3 | Y_F3 rate | Y_SHOT rate |
|---|---|---|---|---|
| Passes, all | 239,588 | 179,021 | 0.677 | 0.161 |
| Passes, deep midfielders | 38,677 | 31,275 | 0.724 | 0.166 |
| Receptions, all | 241,222 | 180,683 | 0.664 | 0.169 |
| Receptions, deep midfielders | 35,536 | 29,002 | 0.726 | 0.171 |

- Receipt next-action outcomes: 271,830 completed receipts. Next action: Carry 228,878; Pass 37,856; Shot 2,672; Miscontrol 1,473; Dispossessed 141; Dribble 150; none found 660.
- Retention (keep) rate on Task 34 receptions: 0.938 (n = 240,776).
- Reception g out-of-fold R^2: Y_F3 0.169, Y_SHOT 0.078, keep 0.236.

### Step 1 — P-tests (coefficient = percentage points of the outcome per 100 units per SD of S; team-match FE, role FE, SE by player)

| Group | S (unit) | Y | n units | players | coef per 100 per SD | 95% CI | p | MDE | control on same rows: coef, 95% CI, p |
|---|---|---|---|---|---|---|---|---|---|
| all | v5 Decision (passes) | Y_F3 | 126,936 | 440 | +0.232 | [−0.208, 0.672] | 0.30 | 0.628 | completion +1.768 [1.434, 2.102], 3e-25 |
| all | MOVE_ON_SPEED (passes) | Y_F3 | 116,536 | 327 | −0.174 | [−0.479, 0.131] | 0.26 | 0.436 | completion +1.766 [1.425, 2.107], 3e-24 |
| all | RQ_rel (receptions) | Y_F3 | 124,095 | 445 | +0.500 | [−0.269, 1.269] | 0.20 | 1.098 | retention +0.783 [0.531, 1.035], 1e-9 |
| all | v5 Decision (passes) | Y_SHOT | 168,855 | 440 | +0.014 | [−0.317, 0.345] | 0.93 | 0.473 | completion +2.201 [1.798, 2.604], 9e-27 |
| all | MOVE_ON_SPEED (passes) | Y_SHOT | 154,116 | 328 | −0.011 | [−0.231, 0.210] | 0.93 | 0.315 | completion +2.190 [1.740, 2.640], 1e-21 |
| all | RQ_rel (receptions) | Y_SHOT | 166,087 | 446 | +0.390 | [−0.145, 0.925] | 0.15 | 0.764 | retention +0.466 [0.251, 0.681], 2e-5 |
| DM | v5 Decision (passes) | Y_F3 | 27,388 | 88 | +0.454 | [−0.407, 1.315] | 0.30 | 1.230 | completion +0.760 [0.375, 1.145], 1e-4 |
| DM | MOVE_ON_SPEED (passes) | Y_F3 | 24,711 | 60 | +0.455 | [−0.553, 1.462] | 0.38 | 1.440 | completion +0.796 [0.504, 1.088], 9e-8 |
| DM | RQ_rel (receptions) | Y_F3 | 24,360 | 78 | −0.108 | [−0.601, 0.385] | 0.67 | 0.704 | retention −0.155 [−0.372, 0.063], 0.16 |
| DM | v5 Decision (passes) | Y_SHOT | 33,889 | 88 | −0.393 | [−0.970, 0.184] | 0.18 | 0.825 | completion +0.626 [0.115, 1.137], 0.016 |
| DM | MOVE_ON_SPEED (passes) | Y_SHOT | 30,680 | 61 | +0.110 | [−0.417, 0.638] | 0.68 | 0.754 | completion +0.545 [0.105, 0.985], 0.015 |
| DM | RQ_rel (receptions) | Y_SHOT | 29,940 | 79 | +0.264 | [−0.214, 0.742] | 0.28 | 0.683 | retention −0.403 [−0.769, −0.036], 0.031 |

## 4. Deviations from the brief
- **Reception-unit control** is the retention control chosen by the author (above). The brief says "positive control (completion)", which does not exist for receptions.
- **Operational definitions:**
  - "Normalised x" = StatsBomb's team-relative x (the acting team attacks toward 120).
  - Y_F3 / Y_SHOT count only LATER events of the unit's own team in the same `possession`.
  - The unit's start x is the pass origin (value-model `ball_x`) or the receiver's 360 location (`recv_x`).
- **Next action and keep** (used by the retention control and Step 2):
  - Scan later events of the same possession. The receiver's Miscontrol or Dispossessed first gives keep = 0.
  - Otherwise the first receiver event in {Pass, Carry, Dribble, Shot} is the action.
  - keep = the action did not fail (a Pass with any pass_outcome, a Dribble 'Incomplete', or any Shot counts as failed) AND the event right after it is in the same possession and is not the receiver's Miscontrol or Dispossessed.
  - Receipts with no action found (660) are excluded.
  - Under this rule, a carry followed by the team keeping possession counts as keep = 1 even if the next pass fails. The receiver's own next action is the carry in 84% of receipts.
- **Tempo residuals** were regenerated with ids (as in Task 39) to new Task 42 files, asserted identical to the stored v2 files.

## 5. Problems and surprises
- **The retention control fails on the deep-midfielder RQ_rel rows** (Y_F3 p = 0.16; Y_SHOT negative, p = 0.031). Under the brief's claim rule, those two deep-midfielder tests could not support a claim even if their Holm p were < 0.05.
- **MDEs on Y_F3 / Y_SHOT for deep midfielders are 0.68-1.44 pp per SD per 100 units.** That is larger than any coefficient observed.
- **keep's base rate is 0.94**, so the retention outcome varies little.

## 6. Questions for the research lead
- Q1: The keep definition evaluates the receiver's first action, which is usually a carry. Should it instead evaluate his first pass or shot (the end of his possession spell)?

## 7. Files produced (so far)
- `src/engine_v2/task42_outcomes.py`, `src/engine_v2/task42_step1.py`.
- `data/engine_v2_task42_step1.json`, `data/processed/engine_v2/task42_event_outcomes.parquet`, `task42_receipt_actions.parquet`, and the redirected tempo re-run outputs `data/processed/tempo_task42_*` and `data/tempo_task42_redesign_rerun.json` (none committed).
- Commits: brief 107bed0; this interim page: recorded in the final version.

## 8. Confidence
The estimator and inputs are the verified Task 35 pipeline. The weakest link is the new keep definition behind the retention control.
