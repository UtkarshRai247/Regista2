# BENCHMARK v6 — the baseline for the second improvement round

Frozen 2026-09-28 by the research lead, after Tasks 32-39. BENCHMARK-v5
stays in force for the engine itself; this file adds everything learned
since. Never edited after the fact; a later benchmark is a new file.
Git tag: `benchmark-v6` (Task 40). Checksums: docs/benchmark/manifest-v6.txt.

## What is frozen
- Engine: v5 unchanged (BENCHMARK-v5). v6 Decision (Task 33) kept as a
  variant, not a replacement.
- Tests: Task 35's pass-level out-of-match test (P-test) is the primary
  results test from here on. Team-match tests are kept but are known to
  be underpowered (Task 35 Step 1: MDE 0.12-0.52 xG per match per SD)
  and, when measured in the same match, partly mechanical (Task 32).
- Data: StatsBomb 360 study sample (292 matches with EV); PFF WC2022
  tracking and events (64 matches, Task 36); women's holdout (126
  matches) is SPENT (used in Tasks 26 and 37).

## Headline numbers

### P-test, all passers (coefficient = net xG per 100 passes per SD of the player's other-match score)
| Measure | Sample | n passes / players | coef | 95% CI | p (Holm) |
|---|---|---|---|---|---|
| Positive control (completion, pp) | study | 168,855 / 440 | +2.201 | [1.798, 2.604] | 9.5e-27 |
| v5 Decision | study | 168,855 / 440 | +0.0747 | [0.0269, 0.1224] | 0.0022 (0.0087) |
| v6 Decision | study | 153,279 / 402 | +0.0468 | [0.0163, 0.0773] | 0.0027 (0.0087) |
| v5 ev_chosen | study | 168,855 / 440 | +0.0589 | [-0.0013, 0.1191] | 0.055 (0.11) |
| Reception RQ_rel (per 100 receptions) | study | 166,087 / 446 | +0.0238 | [-0.0410, 0.0887] | 0.47 (0.47) |
| MOVE_ON_SPEED | study | 154,116 / 328 | -0.0076 | [-0.0322, 0.0171] | 0.548 (0.601) |
| HOLD_VARIATION | study | 161,657 / 381 | +0.0154 | [-0.0138, 0.0446] | 0.300 (0.601) |
| Positive control (completion, pp) | holdout | 58,000 / 227 | +2.814 | [2.188, 3.441] | 1.3e-18 |
| **v5 Decision** | **holdout** | 58,000 / 227 | **+0.0780** | **[0.0237, 0.1322]** | **0.0048** |

### P-test, deep midfielders only
| Measure | Sample | n players | coef | 95% CI | p (Holm) |
|---|---|---|---|---|---|
| v5 Decision | study | 88 | +0.0087 | [-0.0297, 0.0471] | 0.657 (1.0) |
| v6 Decision | study | 80 | +0.0147 | [-0.0228, 0.0523] | 0.441 (1.0) |
| Reception RQ_rel | study | 79 | +0.0555 | [0.0158, 0.0952] | 0.0062 (0.0248) |
| MOVE_ON_SPEED | study | 61 | +0.0587 | [0.0063, 0.1111] | 0.028 (0.056) |
| HOLD_VARIATION | study | 72 | +0.0315 | [-0.0078, 0.0709] | 0.116 (0.116) |
| v5 Decision | holdout | 44 | +0.0075 | [-0.0550, 0.0699] | 0.81 |

### Availability (PFF WC2022, Task 38)
| Quantity | Value |
|---|---|
| Moments / players | 584,874 / 639 |
| Base rate AVAILABLE | 0.334 |
| Stability, deep midfielders (n = 28, >= 4 matches) | 0.740 [0.647, 0.814] |
| Stability, all outfield (n = 183) | 0.620 |
| P-test (per 100 receptions per SD), all outfield | -0.0692 [-0.1146, -0.0238], p = 0.0028 |
| P-test, deep midfielders (59) | -0.1749 [-0.3509, 0.0012], p = 0.0515 |
| Deep-midfield heterogeneity | Q = 277.94 on 58 df, p < 1e-15 |
| Above / below group mean | 12 / 14 (Busquets, de Jong, Bellingham below) |
| AV vs RQ_rel (deep midfielders) | r = +0.361 |
AV_vis (camera-visible only) agrees on every test.

### Other reference numbers
Reception quality (Task 34) and tempo (Tasks 26, 39): see those results
pages. v5 deep-midfield table (Task 29): Vitinha and Busquets above the
mean; v6 table (Task 33): none above or below.

## Rules for this round
1. Every change is specified in a brief before it runs, with what it
   must beat on this page.
2. The holdout is spent. No new result can be externally confirmed
   before Oct 1; anything found in this round is labelled "study sample
   only" unless it is a robustness check of an already-confirmed result.
3. The P-test is the primary results test. Team-match tests are
   reported, not relied on.
4. Worse numbers are reported, not hidden; the author decides trades.
5. If this round produces nothing clearly better, v6 is what gets
   written up.
