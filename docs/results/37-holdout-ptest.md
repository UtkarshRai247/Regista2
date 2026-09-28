# Task 37: Pass-level test (P-test) on the untouched women's holdout (final holdout use)
Date: 2026-09-28
Status: COMPLETE (every section run; deviations in Section 4)

## Checklist
| Section | Status |
|---|---|
| Step 0 — brief committed | COMPLETE, with a deviation: committed by the research lead in 1601bcd **together with the Task 38 brief**, not alone |
| Step 1 — holdout P-test inputs | COMPLETE |
| Step 2 — positive control, then GATE | COMPLETE |
| Step 3 — deep midfielders (report only) | COMPLETE (44 qualify, ≥20) |

## 1. Headline
GATE PASSES: on 58,000 holdout passes by 227 passers in 203 team-matches, v5 Decision from a passer's other holdout matches has coefficient +0.078 xG per 100 passes per SD (95% CI [0.024, 0.132], p = 0.0048). The positive control is positive (p = 1.3e-18).
The holdout MDE at 80% power is 0.077 per 100, essentially equal to the estimate.
Within the 44 qualifying holdout deep midfielders (report only), the coefficient is +0.007 per 100 (95% CI [−0.055, 0.070], p = 0.81). Only 105 of those 185 team-matches contain two or more such players.

## 2. What I did
- Step 0: brief `docs/specs/task-37-holdout-ptest.md`, already committed in 1601bcd, which also contains `task-38-availability.md`.
- Run: `.venv/bin/python src/engine_v2/task37_holdout_ptest.py`
  1. **g models:** trained one XGBoost regression for net xG and one for completion on all 239,588 study-sample passes. These are Task 35's feature table (`task33_step3_f_state.build_feature_table`, 292 matches), Task 35's Y, `F_STATE_FEATURES` and `XGB_REGRESSOR_KWARGS`. They were not cross-fitted, since the brief asks for one model.
  2. **Holdout origin features:** ran engine v5's own `value_models_v5.build_match_rows_v5` on `data/raw_holdout` (module directories redirected, function unchanged). Then `build_feature_table` redirected to the holdout options/events added Task 33's extras (under_pressure, period, minute).
  3. **Holdout g:** applied both g models unchanged to the holdout passes.
  4. **Y:** net shot xG over events i+1..i+10, from `task35_ptest.net_xg_after` on holdout events.
  5. **S:** Task 26's frozen-engine holdout Decision (`pass_der_holdout.parquet`) and completion. `task35_ptest.add_s` takes the leave-one-match-out mean over the other holdout matches, requiring ≥100 elsewhere.
  6. **Roles:** `task32_step4.assign_roles` on holdout pass positions (all holdout passers).
  7. **Deep midfielders:** DM share ≥ 0.50 on holdout positions.
  8. **Model:** `task35_ptest.fe_fit`, the same model and inference as Task 35.

## 3. Numbers

### Step 1 — inputs
- Holdout matches with scored passes: 125 of 126. 3845506 has no frames file, as in Task 26.
- Eligible passes scored by Task 26: 89,459, all with origin features and a passer id.
- Passers: 825. Team-matches: 250.
- Analysis sample (passers with ≥100 eligible passes in other holdout matches): **58,000 passes, 227 passers, 203 team-matches**.
- Of those, 193 team-matches contain ≥2 qualifying passers.
- Qualifying passers per competition (a passer can appear in more than one):

| Competition file | Qualifying passers |
|---|---|
| 53_106 | 145 |
| 53_315 | 139 |
| 72_107 | 179 |

- Holdout roles (players): AM/W 208, FB 153, CB 150, DM 136, FW 112, CM 52, MIXED 14.
- Y on holdout passes: mean 0.0058, SD 0.0450. The study values were mean 0.0056, SD 0.0431.

### Step 2 — positive control, then GATE (beside Task 35's study values)

| Test | Sample | n passes | n passers | team-matches | coef per SD | per 100 | 95% CI (per 100) | p | MDE 80% (per 100) |
|---|---|---|---|---|---|---|---|---|---|
| Positive control (completion) | **holdout** | 58,000 | 227 | 203 | +0.02814 | +2.814 pp | [2.188, 3.441] | 1.3e-18 | 0.895 |
| Positive control (completion) | study (Task 35) | 168,855 | 440 | 506 | +0.02201 | +2.201 pp | [1.798, 2.604] | 9.5e-27 | 0.576 |
| **v5 Decision (PRIMARY)** | **holdout** | 58,000 | 227 | 203 | **+0.000780** | **+0.0780** | **[0.0237, 0.1322]** | **0.0048** | 0.0774 |
| v5 Decision | study (Task 35) | 168,855 | 440 | 506 | +0.000747 | +0.0747 | [0.0269, 0.1224] | 0.0022 | 0.0682 |

- Positive control: POSITIVE (p < 0.05), so the primary may be read.
- **GATE: PASS** (coefficient positive, two-sided p = 0.0048 < 0.05).
- SD of S (raw Decision, holdout): 0.00175. Study: 0.00165.

### Step 3 — holdout deep midfielders (report only)
- DM-share ≥ 0.50 on holdout positions: 136 players. With ≥100 eligible passes elsewhere: **44** (≥20, so the test was run).
- 10,580 passes in 185 team-matches. Only **105 team-matches (7,182 passes) contain ≥2 qualifying deep midfielders**; in the rest, S does not vary within the team-match fixed effect.

| Test | n passes | n players | team-matches | coef per SD | per 100 | 95% CI (per 100) | p | MDE 80% (per 100) |
|---|---|---|---|---|---|---|---|---|
| Positive control | 10,580 | 44 | 185 | +0.03568 | +3.568 pp | [2.104, 5.033] | 1.8e-6 | 2.092 |
| v5 Decision | 10,580 | 44 | 185 | +0.000075 | +0.0075 | [−0.0550, 0.0699] | 0.814 | 0.0892 |

## 4. Deviations from the brief
- **Step 0:** the brief was not committed alone. The research lead committed it in 1601bcd together with `task-38-availability.md`. I did not re-commit it.
- **g trained on "ALL study-sample passes"** means Task 35's 239,588 passes with origin features. The 11,262 passes of the 250,850 v5 corpus that lack a value-model row (Task 35 Section 4) are not included.
- **Holdout origin features** were written to `data/processed/engine_v2/value_model_rows_holdout.parquet`, a new file. `build_match_rows_v5` also computes its goal-in-window labels as part of the unchanged function. Those labels were discarded and not saved.
- **Deep-midfield rule:** ≥50% DM share among holdout eligible passes, with qualifying defined as ≥100 elsewhere, which matches the S requirement. Task 27's original also required ≥100 eligible passes to enter the 537 pool; here the ≥100-elsewhere requirement takes that role.
- **The two "≥2 players per team-match" counts** (193 of 203 and 105 of 185) came from an in-session command using the same inputs. That logic was then added to `task37_holdout_ptest.py` (it writes `team_matches_with_2plus_players_*`). **The script was not re-run afterwards**, to avoid a second pass over the holdout, so the saved JSON does not yet contain these two fields. The test itself was run once.
- S standardised across each analysis's own rows (as in Task 35), so Step 3's "per SD" is per deep-midfield SD.

## 5. Problems and surprises
- **The holdout estimate (+0.078 per 100) sits at its own MDE (0.077).** The test had about 80% power for an effect of the size found, and the 95% CI's lower end (0.024) is close to zero.
- **Holdout Decision is frozen-engine scored, not cross-fitted.** Task 35's study S was cross-fitted, so the S definitions differ in how the engine was fitted. The brief specifies this.
- **Step 3's deep-midfield coefficient is near zero** (+0.007 per 100) with an MDE of 0.089, larger than the all-passer effect. Only 105 of 185 team-matches carry within-game variation in S. Taken at face value, the holdout does not show the pass-level result within deep midfielders, which is also true on the study sample (Task 35 Step 3, p = 0.66).
- **The positive control is larger on the holdout** (+2.8 pp against +2.2 pp).

## 6. Questions for the research lead
- None blocking.
- Q1: Should the script be re-run once so the saved JSON carries the two team-match counts? This would be a second execution of the same holdout test; I did not do it without instruction.

## 7. Files produced
- `src/engine_v2/task37_holdout_ptest.py`.
- `data/processed/engine_v2/value_model_rows_holdout.parquet` (holdout origin features; not committed).
- `data/engine_v2_task37_holdout_ptest.json` (not committed).
- Side effects: none else. No memory writes. JOURNAL.md and AGENTS.md untouched and uncommitted. The holdout is now spent per BENCHMARK-v5 rule 3.
- Commits: brief 1601bcd (research lead); this task: recorded in a follow-up commit.

## 8. Confidence
- The mechanics reuse Task 35 and Task 26 code unchanged, and the positive control works.
- The weakest link is that the gate result sits right at the holdout MDE: the p-value is 0.0048, but the CI lower bound is 0.024 per 100.
