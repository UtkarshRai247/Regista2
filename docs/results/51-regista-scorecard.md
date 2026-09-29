# Task 51: The regista scorecard
Date: 2026-09-29
Status: COMPLETE (every step run; deviations in Section 4. HOLD_VARIATION has no interval and no label, and Card C has one player)

**Licence flag, read first (Section 5 / Q1).** `docs/scorecard/index.html` and `docs/scorecard/figure_praised.png` contain PFF-derived numbers (AV) and are committed under `docs/`. `docs/DATA_LICENSES.md` says an explicit answer from PFF is needed before any PFF-derived number goes into a public SSAC artifact. The repo has no git remote, and I did not publish anything.

Descriptive product; no new measures, no claims. Datasets and uses:
- Card A: 2015/16, further use after Tasks 44-47 and 50.
- Card B: study sample, as usual. AV comes from PFF WC2022, as in Tasks 38 and 41.
- Card C: reserved data, second use after Task 48 (Task 50 was also a second-use analysis of the same data).

The holdout was not touched.

## Checklist
| Section | Status |
|---|---|
| Step 0: brief committed alone | COMPLETE (27b90f0, by the research lead) |
| Step 1: Card A (185 DMs, 5 dimensions) | COMPLETE |
| Step 1: Card B (111 DMs, 6 dimensions + AV) | COMPLETE (several dimensions have most players below the floor, see Section 3) |
| Step 1: Card C (>= 5 La Liga seasons, >= 50 pressured receptions each) | COMPLETE (1 player meets the rule) |
| Step 2: per player per dimension (n, raw, shrunk + 90% interval, percentile, label) | PARTIAL. HOLD_VARIATION has n, raw SD and percentile only: no shrinkage, interval or label (Section 4) |
| Step 3: tiers + within-DM reliability per dimension; RQ_rel reliability on Card B | COMPLETE (RQ_rel 0.419 < 0.60, so it moved to Tier 3 as the brief specifies) |
| Step 4: parquets, `docs/scorecard/index.html`, `figure_praised.png`, `figure_career.png` | COMPLETE (the praised figure covers Cards A and B, see Section 4) |
| Memory gate (Task 25) | COMPLETE (card A 65% / 5.5 GB; card B 60% / 4.7 GB; card B tempo 64% / 5.3 GB; card C 63% / 5.2 GB) |

## 1. Headline
- Card C rests on n = 1 player: Sergio Busquets, 11 La Liga seasons. No other reserved-data deep midfielder has more than 3 qualifying seasons.
- Card B's group is 111, but only 29-46 players meet the floor for PR2_flag_keep (37), HOLD_VARIATION (35), MOVE_ON_SPEED (29) and AV (46).
- RQ_rel's within-DM reliability on Card B is 0.419 (82 players, Task 38's method), so it ends in Tier 3.
- Tiers as ended:
  - Tier 1: PR2_flag_keep and A1.
  - Tier 2: W, HOLD_VARIATION and AV.
  - Tier 3: Decision, MOVE_ON_SPEED and RQ_rel.

## 2. What I did
Reproduce with:
- `.venv/bin/python -W ignore src/engine_v2/task51_scorecard.py` writes `data/processed/scorecard_card_{a,b,c}.parquet` and `data/engine_v2_task51.json`.
- `.venv/bin/python -W ignore src/engine_v2/task51_outputs.py` writes `docs/scorecard/index.html`, `figure_praised.png` and `figure_career.png`.

**Method, per player x dimension (Task 29's method, as in `task42_step2.dm_table`):**
1. Estimate within-group noise with `estimate_sigma2w_rho`, using (player, match) groups, on the card's DMs who meet the floor.
2. Compute v_i with the design effect.
3. Pool with DerSimonian-Laird.
4. Apply `shrink` for a 90% interval.
5. Take the percentile of the shrunk value within those players.
6. Label: CLEARLY ABOVE / BELOW when the 90% interval excludes the DL group mean; otherwise CAN'T TELL. Players below the floor get "not enough data".

**Floors:** PR / A1 >= 50 pressured receptions; W and RQ_rel >= 100 receptions; Decision >= 100 eligible (cross-fitted) passes; AV >= 300 moments; tempo >= 200 tempo passes (see Section 4).

**Card A (group: `task44_roles.is_dm`, 185):**
- PR2_flag_keep = `task44_receptions.pr2_flag_keep`.
- A1 = unit minus team mean (Task 45).
- W is rebuilt with `task46_part_b.fit_w` on Task 44's seeded folds, because Task 46 never saved it.
- HOLD_VARIATION (SD of residuals) and MOVE_ON_SPEED (mean) come from `tempo_task44_{hold,move}_residuals_ids`.

**Card B (group: `leaderboard_v5c.is_deep_midfield`, 111):**
- Decision = `pass_der_crossfit_v5.decision`.
- PR2_flag_keep = `task46_study_pr_flag` (Task 46's version).
- W is rebuilt with Task 46's code.
- RQ_rel = `task34_receptions.rq_rel`.
- Tempo: Task 26's corrected-coordinate residuals, regenerated with match ids by Task 39's `tempo_residuals_with_ids` recipe. Output goes to new `tempo_task51_*` files and is asserted equal to `tempo_redesign_*_residuals_v2`.
- AV = `pff/availability_moments.av`, mapped to StatsBomb ids with `availability_tests.player_map`, with (player, PFF game) as the match unit.

**Card C (reserved data):**
- Deep midfielders (`task48_roles.is_dm`) with at least 5 La Liga (competition_id 11) seasons that each have >= 50 pressured receptions.
- Per qualifying season: the raw mean PR2_flag_keep and a 90% interval. The interval uses Task 29's within-group noise (`estimate_sigma2w_rho` with the player-season as the group), not shrunk.

**Reliabilities:**
- Cited from existing pages for all dimensions except RQ_rel.
- RQ_rel on Card B uses Task 38's R1 (`availability_tests.r1`): Card B DMs with >= 4 matches, 100 random match half-splits, Spearman-Brown, median.

**Praised list:** Task 41's `LIST_L`, matched with Task 27's `name_matches`. Names are output only.

**Page check.** The page was served from 127.0.0.1 and checked in Chrome:
- Sort, search and row click-through work, and Tier 3 rows are greyed.
- Card B shows the PFF credit.
- No console errors. The only resource loaded is the page itself (no external requests).

**Reproduction checks:**
- Rebuilt W, 2015/16: n 1,158,231, AUC 0.6289478647, identical to Task 46.
- Rebuilt W, study: n 271,830, AUC 0.6134970381, identical to Task 46.
- Card A PR2_flag_keep: group mean +0.08721, Q 703.6 (184 df), 27 above / 35 below, identical to Task 44 Step 5.
- Card A A1: Q 433.5, 9 / 13, identical to Task 45.
- Card B Decision: DL Q 143.8 (110 df), matching Task 32's Q(110) = 143.81.

## 3. Numbers
Counts per dimension (players):

**Card A — 2015/16 big five (2015/16 data, further use; group = Task 44's 185 DMs).** Group size 185.

| Dimension | Tier | within-DM reliability (source) | floor | players meeting floor | CLEARLY ABOVE | CLEARLY BELOW | CAN'T TELL | no interval | not enough data | DL: group mean, tau^2, Q (df) |
|---|---|---|---|---|---|---|---|---|---|---|
| PR2_flag_keep | TIER 1 | 0.666 (docs/results/44-big-five-1516.md:120 (2015/16 DMs, 185)) | 50 | 185 | 27 | 35 | 123 | 0 | 0 | +0.08721, 0.00294, 703.6 (184) |
| A1 | TIER 1 | 0.487 (docs/results/45-press-resistance-vetting.md:48 (2015/16 DMs, 185)) | 50 | 185 | 9 | 13 | 163 | 0 | 0 | +0.08822, 0.00141, 433.5 (184) |
| W | TIER 2 | 0.802 (docs/results/46-movers-and-spatial-physical.md:73 (2015/16 DMs, 185)) | 100 | 185 | 47 | 43 | 95 | 0 | 0 | -0.02244, 0.00204, 1137.0 (184) |
| HOLD_VARIATION | TIER 2 | 0.730 (docs/results/44-big-five-1516.md:119 (2015/16 DMs, 185)) | 200 | 185 | 0 | 0 | 0 | 185 | 0 | not applicable (SD measure) |
| MOVE_ON_SPEED | TIER 3 | 0.475 (docs/results/44-big-five-1516.md:118 (2015/16 DMs, 185)) | 200 | 183 | 5 | 14 | 164 | 0 | 2 | -0.041, 0.00052, 381.0 (182) |

Praised-list players present (Task 41's list, matched by name): Kroos (player_id 5574); Busquets (player_id 5203). Not present: Modric, Verratti, De Bruyne, Xhaka, de Jong, Kimmich, Rodri, Pedri, Gundogan, Grillitsch, Shaparenko.

**Card B — 360 era (study sample, as usual; group = Task 27's 111 DMs).** Group size 111.

| Dimension | Tier | within-DM reliability (source) | floor | players meeting floor | CLEARLY ABOVE | CLEARLY BELOW | CAN'T TELL | no interval | not enough data | DL: group mean, tau^2, Q (df) |
|---|---|---|---|---|---|---|---|---|---|---|
| Decision | TIER 3 | 0.451 (docs/results/32-critique-diagnostics.md:265 (study DMs at 200 passes, 51 player-seasons)) | 100 | 111 | 2 | 0 | 109 | 0 | 0 | +0.002013, 1.11e-07, 143.8 (110) |
| PR2_flag_keep | TIER 1 | 0.666 (docs/results/44-big-five-1516.md:120 (2015/16 DMs, 185)) | 50 | 37 | 2 | 3 | 32 | 0 | 74 | +0.113, 0.00206, 89.5 (36) |
| W | TIER 2 | 0.802 (docs/results/46-movers-and-spatial-physical.md:73 (2015/16 DMs, 185)) | 100 | 106 | 12 | 8 | 86 | 0 | 5 | -0.008778, 0.00189, 298.9 (105) |
| RQ_rel | TIER 3 | 0.419 (computed in Task 51 (Card B DMs, Task 38's R1)) | 100 | 98 | 6 | 8 | 84 | 0 | 13 | -1.051, 0.182, 235.6 (97) |
| HOLD_VARIATION | TIER 2 | 0.730 (docs/results/44-big-five-1516.md:119 (2015/16 DMs, 185)) | 200 | 35 | 0 | 0 | 0 | 35 | 76 | not applicable (SD measure) |
| MOVE_ON_SPEED | TIER 3 | 0.475 (docs/results/44-big-five-1516.md:118 (2015/16 DMs, 185)) | 200 | 29 | 3 | 4 | 22 | 0 | 82 | -0.04107, 0.000925, 86.9 (28) |
| AV | TIER 2 | 0.740 (docs/results/38-availability.md:122 (WC2022 DMs, 28)) | 300 | 46 | 7 | 6 | 33 | 0 | 65 | +0.02978, 0.00162, 179.8 (45) |

Praised-list players present (Task 41's list, matched by name): Kroos (player_id 5574); Verratti (player_id 3166); Busquets (player_id 5203); Xhaka (player_id 3500); Gundogan (player_id 10287); Grillitsch (player_id 11396). Not present: Modric, De Bruyne, de Jong, Kimmich, Rodri, Pedri, Shaparenko.

**Card C (reserved data, second use; descriptive; TIER 1, reliability 0.666 cited from docs/results/44-big-five-1516.md:120).** 1 player meets the rule. Qualifying La Liga seasons per reserved DM: Busquets 11, Yaya Touré 3, Edmílson 2, Alex Song 2, Thiago Motta 1, Paulinho 1.

| Season | pressured receptions | matches | PR2_flag_keep (raw mean) | 90% interval |
|---|---|---|---|---|
| 2008/2009 | 204 | 21 | -0.0338 | [-0.0853, +0.0177] |
| 2009/2010 | 337 | 28 | +0.1006 | [+0.0596, +0.1415] |
| 2010/2011 | 375 | 24 | +0.1283 | [+0.0883, +0.1684] |
| 2011/2012 | 398 | 30 | +0.1087 | [+0.0706, +0.1467] |
| 2012/2013 | 315 | 28 | +0.1312 | [+0.0891, +0.1732] |
| 2013/2014 | 322 | 27 | +0.1857 | [+0.1439, +0.2276] |
| 2014/2015 | 360 | 33 | +0.1859 | [+0.1467, +0.2251] |
| 2016/2017 | 328 | 28 | +0.2041 | [+0.1627, +0.2455] |
| 2017/2018 | 366 | 29 | +0.1523 | [+0.1129, +0.1918] |
| 2018/2019 | 406 | 33 | +0.1638 | [+0.1264, +0.2012] |
| 2019/2020 | 403 | 29 | +0.1523 | [+0.1143, +0.1904] |

2015/16 is not among the reserved La Liga seasons: it is the separate 2015/16 dataset.

**Tier each dimension ended in:**
- Tier 1: PR2_flag_keep and A1. A1's within-DM reliability is 0.487, below 0.60, but the brief places A1 in Tier 1 beside PR2_flag_keep.
- Tier 2: W, HOLD_VARIATION, AV (with the brief's note).
- Tier 3: Decision, MOVE_ON_SPEED, RQ_rel. RQ_rel moved by the brief's rule: 0.419 < 0.60.

**RQ_rel within-DM reliability, Card B (Task 38's method):** 82 players with >= 4 matches; median 0.419; p5 0.311; p95 0.530.

## 4. Deviations from the brief
- **HOLD_VARIATION has no shrunk value, interval or label.** It is a per-player SD of residuals, and Task 29's method is a per-unit-mean method. Task 44 already recorded that the method does not apply (docs/results/44-big-five-1516.md:147, its Q1), and I found no decision resolving it. The page shows n, the raw SD and the percentile of the raw SD, marked "no interval". Its CLEARLY ABOVE / BELOW / CAN'T TELL counts are therefore missing on both cards.
- **Tempo floor = 200 tempo passes on both cards.** "Tempo per its preregistered floor": I used the preregistered tempo gate threshold (`src/tempo/reliability.py:46`, `GATE_THRESHOLD = 200`). Task 44's tests used >= 100 as the S floor. At 200, Card A MOVE_ON_SPEED loses 2 of 185 players. On Card B only 35 (HOLD) and 29 (MOVE) of 111 meet it.
- **The DL group is the players meeting the floor.** Task 29's method was run on the DMs at or above each floor, not on all DMs. On Card A this changes nothing for PR2_flag_keep, A1 or W, where all 185 meet the floor.
- **W was rebuilt, never read from disk.** Task 46 did not save it. The rebuild reproduces Task 46's baselines exactly.
- **Card B tempo residuals were regenerated** with match ids (needed for Task 29's within-group noise) into new files `data/processed/tempo_task51_{metrics,move_residuals,hold_residuals}.parquet` and `data/tempo_task51_redesign_rerun.json`. Nothing earlier was overwritten. The residuals are asserted identical (to 1e-12) to `tempo_redesign_*_residuals_v2`.
- **Card B reliabilities for PR2_flag_keep, W, HOLD_VARIATION and MOVE_ON_SPEED are cited from 2015/16 pages.** No existing page reports a study-sample within-DM value for these, and each citation says "2015/16 DMs". Decision's 0.451 (docs/results/32-critique-diagnostics.md:265) was measured on in-sample v5 `decision_new` by player-season at 200 passes, not on the cross-fitted v5 shown on the card.
- **Card C interval:** raw per-season mean with a 90% interval from Task 29's within-group noise (player-season as the group), not shrunk. The brief says "per season with 90% intervals" without saying whether to shrink across seasons.
- **figure_praised.png covers Cards A and B.** Card C's only player is shown in figure_career.png.
- **RQ_rel reliability sample:** Card B DMs with >= 4 matches (82), with no reception floor. The brief names only the >= 4 matches rule.
- **New dependency:** matplotlib 3.11.2, plus contourpy 1.4.0, cycler 0.12.1, fonttools 4.66.1, kiwisolver 1.5.1, pillow 12.3.0, pyparsing 3.3.3, installed into `.venv` because the brief requires PNG figures and matplotlib was not installed. There is no requirements file in the repo to record it in.

## 5. Problems and surprises
- **PFF licence (see the top of this page).** AV and the PFF credit appear in committed files under `docs/`. What this would invalidate if the licence is refused: publishing `index.html` and `figure_praised.png` as they are. They would need AV removed.
- **Card C = one player.** The career line is Busquets alone, because the reserved men's club data is mostly Barcelona (Task 48 page). Taken at face value, Card C describes one player, not deep midfielders.
- **Most Card B players lack data for several dimensions.** PR2_flag_keep: 74 of 111 are below 50 pressured receptions. Tempo: 76 / 82 below 200. AV: 65 of 111 without 300 moments, and only 55 have any WC2022 moments.
- **Decision on Card B has tau^2 = 1.1e-7:** almost all between-player spread is noise, so shrunk values sit near the group mean. 2 players are CLEARLY ABOVE and none below. Taken at face value, Decision cannot separate these 111 deep midfielders, consistent with its Tier 3 placement.
- **RQ_rel reliability 0.419 here vs 0.933 on Task 34's page** (docs/results/34-reception-quality.md:73: player x competition-season units, at 200, 37 DM player-seasons). This task's value uses Task 38's match-split method within Card B's DMs. Taken at face value, the Task 34 value does not hold within deep midfielders under the brief's method.
- **A1 is Tier 1 with reliability 0.487 < 0.60.** The brief fixes this ("A1 shown beside it"). I report it without changing it.

## 6. Questions for the research lead
1. **PFF licence:** should AV (and the PFF credit) stay in the committed `docs/scorecard/` files before PFF answers, or be removed from the public version?
2. **HOLD_VARIATION:** which interval method (if any) should an SD measure get, so it can have a label? This is Task 44's Q1, still open. Until answered, HOLD has no CLEARLY ABOVE / BELOW counts.
3. **Tempo floor:** is 200 (the preregistered gate threshold) the intended "preregistered floor", or should it be Task 44's 100?
4. **Card C:** with one qualifying player, should Card C stay as specified, or should its rule change? Is an unshrunk per-season interval what was intended?
5. **Card B reliabilities:** is citing 2015/16 within-DM reliabilities for PR2_flag_keep, W and tempo acceptable, or should they be computed on the study sample (as was done for RQ_rel)?
6. **Praised figure:** should Card C (Busquets only) also get a row in `figure_praised.png`?

## 7. Files produced
- `src/engine_v2/task51_scorecard.py`: builds the three cards (reuses Task 28/29, 38, 39, 44, 45, 46, 48 code).
- `src/engine_v2/task51_outputs.py`: HTML page and figures.
- `docs/scorecard/index.html`: 829 KB, self-contained, data embedded.
- `docs/scorecard/figure_praised.png`, `docs/scorecard/figure_career.png`.
- `data/processed/scorecard_card_a.parquet`, `scorecard_card_b.parquet`, `scorecard_card_c.parquet` (not committed). Long format: card, player, dimension, n, raw, shrunk, 90% interval, percentile, label, tier, reliability + source, note.
- `data/engine_v2_task51.json`: counts, DL summaries, reproduction checks, RQ_rel R1, memory log (not committed).
- `data/processed/tempo_task51_{metrics,move_residuals,hold_residuals}.parquet`, `data/tempo_task51_redesign_rerun.json`: regenerated study tempo (side effect of the tempo regeneration; not committed).
- Side effects:
  - Python packages installed into `.venv` (Section 4).
  - The matplotlib font cache was built in the user cache directory.
  - A temporary local web server (127.0.0.1:8751) served the page for the check. It is stopped.
- Commits: 5af9e43 (Task 51).
- Not mine and not committed: pre-existing uncommitted changes to `docs/JOURNAL.md` and the untracked `AGENTS.md`.

## 8. Confidence
- The reproduction checks tie Cards A and B to the earlier tasks' numbers exactly.
- The weakest links:
  - Card C (n = 1 player).
  - Card B dimensions with 29-46 players above the floor.
  - HOLD_VARIATION without an interval.
  - Card B reliabilities borrowed from 2015/16.
