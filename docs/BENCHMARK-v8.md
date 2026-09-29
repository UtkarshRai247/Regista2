# BENCHMARK v8 — adds the one-time confirmation on the reserved data

Frozen 2026-09-29 by the research lead after Task 48. BENCHMARK-v5, v6
and v7 stay in force. Never edited after the fact.
Git tag: `benchmark-v8` (Task 50). Checksums: docs/benchmark/manifest-v8.txt.

## Data status
- Study sample: 292 matches with EV (299 on disk). Used throughout.
- Women's holdout (126 matches): SPENT (Tasks 26, 37).
- 2015/16 big five (1,551 matches): used in Tasks 44-47.
- Reserved (64 competition-seasons, 1,985 matches, 1,184 women's):
  SPENT (Task 48). No untouched StatsBomb data is known to remain.

## Confirmed results (pre-registered, on data untouched by design)
| Claim | Evidence |
|---|---|
| Decision quality is an individual skill that shows up in other matches' passes (pass-level test) | study +0.0747 per 100 passes per SD [0.0269, 0.1224], Holm 0.0087; holdout +0.0780 [0.0237, 0.1322], p 0.0048 (Tasks 35, 37). Carried by forwards in the study sample (Task 41). |
| Press resistance travels with the player between club and country | reserved: r_true +0.650 [0.500, 0.797], 127 movers, Holm p < 0.002 (Task 48 C4); study 0.924 [0.735, 1.0], 24 movers; 2015/16 club vs later national team 0.740 [0.579, 0.888], 91 players (Task 46) |
| Team-adjusted press resistance predicts the team reaching the final third (all players) | reserved: +1.281 pp per 100 pressured receptions per SD [0.988, 1.573], Holm 3.7e-17, control positive (Task 48 C6); 2015/16 +1.60, p 1.4e-27 (Task 45) |

## Not confirmed
| Test | Result |
|---|---|
| DM press resistance -> final third | 2015/16 +0.775 [-0.013, 1.562] p 0.054; A1 +0.64 p 0.041; reserved +0.572 [-0.502, 1.645] p 0.297 |
| DM willingness W -> final third | 2015/16 +0.333 p 0.037; reserved -0.310 p 0.284 |
| Pressure deterrence (all) | 2015/16 -0.00371 p 0.0068; reserved -0.00241 p 0.080 |
| Decision within DMs | study +0.0087 p 0.657; holdout +0.0075 p 0.81 |

## Open puzzle
Press resistance goes with reaching the final third but with LOWER net
xG over the next 10 events: 2015/16 all players -0.046 p 7e-5; reserved
DMs -0.0825 p 0.022.

## Rules
As BENCHMARK-v6. All further analyses of any dataset are labelled with
which use of that dataset they are, and none can be called confirmed.
