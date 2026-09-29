# BENCHMARK v9 — adds the puzzle, robustness, pooling and the scorecard

Frozen 2026-09-29 by the research lead after Tasks 50-51. BENCHMARK-v5
to v8 stay in force. Never edited after the fact.
Git tag: `benchmark-v9` (Task 52 Step 1). Checksums:
docs/benchmark/manifest-v9.txt.

## New numbers (report only; every dataset previously used)
| Quantity | Value | Source |
|---|---|---|
| Press resistance -> own xG, next 10 events (all players) | 2015/16 -0.0448 p 5.8e-5; reserved -0.0417 p 4.1e-5 | results/50 |
| Press resistance -> own xG, whole possession (all) | 2015/16 +0.0258 p 0.077; reserved +0.0386 p 0.019 | results/50 |
| Press resistance -> possession length (all) | +74.6 / +87.1 events per 100 pressured receptions per SD, p < 1e-50 | results/50 |
| Press resistance -> xG conceded, next 10 / next opponent possession | null in every cell | results/50 |
| Deep midfielders: whole-possession xG | null (p >= 0.53) | results/50 |
| C6 (team-adjusted PR -> final third) by subset | positive, CI excluding 0 in all six (men +1.699, women +1.109, club +1.251, national +2.303, no Barcelona +1.130, no Busquets/Walsh +1.285) | results/50 |
| C4 (travels) by subset | men +0.735 (29), women +0.593 (98), no Barcelona +0.681 (94), no Busquets/Walsh +0.642 (125) | results/50 |
| Pooled DM PR -> final third (3 samples, decided after C1) | +0.677 [0.075, 1.278], p 0.027, I^2 = 0 | results/50 |
| Pooled DM W -> final third | FE +0.162 p 0.23; DL +0.043 p 0.86 | results/50 |
| Scorecard: tiers | T1 PR (+A1); T2 W, HOLD_VARIATION, AV; T3 Decision, MOVE_ON_SPEED, RQ_rel (0.419) | results/51 |
| Busquets La Liga PR2_flag_keep by season | 2008/09 -0.034 -> 2013/14 +0.186, 2016/17 +0.204 | results/51 |

## Tempo as of this benchmark
MOVE_ON_SPEED within-DM stability 0.475 (2015/16, FAIL), HOLD_VARIATION
0.730; no confirmed results link (Tasks 39, 44). Scorecard Tier 3 / 2.

## Rules
As BENCHMARK-v6. New tempo work uses the pre-registered development /
replication split fixed in Task 52.
