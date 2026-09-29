# BENCHMARK v7 — adds the 2015/16 big-five results

Frozen 2026-09-28 by the research lead after Task 44. BENCHMARK-v5 and
v6 stay in force; this adds Tasks 42-44. Never edited after the fact.

## New data
StatsBomb 2015/16 big-five leagues (1,551 matches, event data only),
untouched before Task 44; definitions fixed before download.

## Headline numbers (Task 44 unless noted)
| Quantity | Value |
|---|---|
| PR2_flag vs frame-based PR2 (study sample, player level) | r = 0.840 [0.784, 0.881], n = 148 |
| PR2 PFF vs StatsBomb (WC2022, Task 43) | r = 0.778 [0.648, 0.864], n = 55 |
| Stability within deep midfielders, PR2_flag_keep | 0.666 [0.610, 0.714], n = 185 (PASS) |
| Stability within deep midfielders, HOLD_VARIATION | 0.730, n = 185 (PASS) |
| Stability within deep midfielders, MOVE_ON_SPEED | 0.475 (FAIL) |
| Stability within deep midfielders, PR2_flag_fwd | 0.587 (FAIL) |
| Deep-midfield heterogeneity, PR2_flag_keep | Q = 703.6 on 184 df, p < 1e-15; 27 above, 35 below |
| Praised list, PR2_flag_keep (pre-declared higher) | T = +1.444, p = 0.0011, Holm (4) 0.0044; 5 players |
| P1 MOVE_ON_SPEED -> net xG (DM) | +0.0096 [-0.0076, 0.0268], p = 0.27 — not confirmed |
| P2 PR2_flag_keep -> reach final third (DM) | +0.775 pp [-0.013, 1.562], p = 0.054, Holm 0.108 — not confirmed |
| PR2_flag_keep -> reach final third (all, secondary) | +1.835 pp [1.504, 2.166], p = 1.7e-27 |
| PR2_flag_keep -> net xG (all, secondary) | -0.046 [-0.068, -0.023], p = 7.0e-5 |

## Known open attacks (to vet in Task 45)
Team style (top-team deep midfielders dominate the table), "just safe
passing" (keep = spell ends in a completed pass), league differences,
and the praised list's small n.

## Rules
As BENCHMARK-v6. 2015/16 has now been used once for confirmation; any
further use is labelled "second use of 2015/16".
