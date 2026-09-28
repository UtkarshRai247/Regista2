# Task 43: Press resistance, done properly (a disclosed second attempt)
Date: 2026-09-28
Status: PARTIAL (Steps 0-2 run; Steps 3-6 NOT RUN yet — interim commit required by the brief)

Study sample and PFF WC2022 only. **This is a second attempt, made after seeing Task 42's results.** Task 42's numbers are reported beside this task's.

## Checklist
| Section | Status |
|---|---|
| Step 0 — brief committed alone | COMPLETE (0eed693, by the research lead) |
| Memory gate | COMPLETE (62% free, ~5.22 GB, 16:33 PDT) |
| Step 1 — corrected measure (spell) | COMPLETE |
| Step 2 — player-level stability | COMPLETE |
| Steps 3-6 | NOT RUN |

## 1. Headline
Steps 1-2 only. With keep judged at the end of the receiver's spell, the measure fails the stability bar within deep midfielders:
- PR2_keep: median split-half reliability 0.387 [p5 0.072, p95 0.585], n = 28 players with ≥4 matches and ≥40 pressured receptions;
- PR2_fwd: 0.283.
Across all players (n = 199) the medians are 0.543 (PR2_keep) and 0.353 (PR2_fwd).
Player PR2_keep correlates r = 0.72 with Task 42's PR_keep (149 players).

## 2. What I did
- Step 0: the brief was committed alone by the research lead (0eed693).
- `.venv/bin/python -W ignore src/engine_v2/task43_spells.py`:
  - Computes each completed receipt's spell outcome (definition below).
  - Rebuilds Task 42's pressured receptions with `task42_step2.match_receipts` and the same PRESSURED rule.
  - Fits Task 42's classifier (`CLF_KWARGS`, `BASE_FEATURES`), cross-fitted on Task 35's folds and refit per outcome.
  - Runs Task 38's R1 (`availability_tests.r1`: 100 random half-splits of a player's matches, seed 20260928, Spearman-Brown) on players with ≥4 matches and ≥40 pressured receptions.
- Spell definition: for a completed Ball Receipt* by P, scan later events. The spell ends at the first of:
  - the possession ending → keep 0;
  - P's Pass → keep 1 if completed, else 0;
  - P's Shot → excluded;
  - P's Miscontrol, Dispossessed or failed Dribble → 0;
  - an opponent's Ball Recovery, Interception, Block, Clearance or won Tackle duel → 0;
  - an on-ball event by a teammate other than P, or P's Clearance → excluded as "other" (not in the brief's list).
  - fwd = keep AND the completed pass's end x − reception x ≥ 5.

## 3. Numbers

### Step 1 — the measure
- Completed receipts (all 292 matches): 271,830. Pressured (Task 42 rule): 42,301.
- How pressured spells end:

| End | n |
|---|---|
| completed pass | 23,561 |
| incomplete pass | 7,814 |
| own miscontrol | 3,059 |
| **shot (excluded)** | **2,368** |
| own dispossessed | 2,294 |
| possession ended | 1,797 |
| own failed dribble | 1,073 |
| opponent block | 204 |
| opponent interception | 66 |
| **other (excluded)** | **26** |
| opponent clearance | 19 |
| opponent ball recovery | 17 |
| **no end found (excluded)** | **3** |
| opponent won duel | 0 |

- Spells with an outcome: **39,904**.

| Outcome | base rate | baseline OOF AUC | Task 42 equivalent |
|---|---|---|---|
| keep_spell (PR2_keep) | 0.590 | 0.638 | keep 0.776, AUC 0.716 |
| fwd_spell (PR2_fwd) | 0.166 | 0.631 | fwd 0.110, AUC 0.587 |

- Correlation of player mean PR2_keep with Task 42's player mean PR_keep (players with ≥50 pressured receptions in both): **r = 0.720, n = 149**.

### Step 2 — player-level stability (Task 38's R1; players with ≥4 matches and ≥40 pressured receptions)

| Measure | Group | n players | median | p5 | p95 | PASS (DM ≥ 0.60) |
|---|---|---|---|---|---|---|
| PR2_keep | **deep midfielders** | 28 | **0.387** | 0.072 | 0.585 | **FAIL** |
| PR2_keep | all | 199 | 0.543 | 0.468 | 0.611 | — |
| PR2_fwd | **deep midfielders** | 28 | **0.283** | −0.076 | 0.556 | **FAIL** |
| PR2_fwd | all | 199 | 0.353 | 0.224 | 0.461 | — |

Task 42 (player-season units, `step8_regate` reliability at 100 pressured receptions, 7 units): PR_keep 0.249, PR_fwd 0.268, FAIL.

## 4. Deviations from the brief
- **Spell end "other" (26) and "no end found" (3) are excluded.** The brief's list does not cover a teammate's on-ball event or P's own Clearance before the spell ends.
- **Duel won:** an opponent's Tackle duel with outcome Won, Success In Play or Success Out. No pressured spell ended this way (0), because the possession id changes first.

## 5. Problems and surprises
- **R1 within deep midfielders fails for both measures** (0.39 and 0.28, n = 28). The all-player medians are also below 0.60.
- **The keep base rate falls from 0.776 (Task 42's first action) to 0.590** when judged at the end of the spell.

## 6. Questions for the research lead
- None yet.

## 7. Files produced (so far)
- `src/engine_v2/task43_spells.py`.
- `data/processed/engine_v2/task43_spells.parquet`, `task43_pressured_spells.parquet`, `data/engine_v2_task43_steps1_2.json` (not committed).
- Commits: brief 0eed693; this interim page: recorded in the final version.

## 8. Confidence
The spell definition follows the brief, with the two disclosed exclusions. Stability rests on 28 deep midfielders.
