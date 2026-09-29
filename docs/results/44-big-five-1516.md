# Task 44: A fresh, untouched dataset: StatsBomb 2015/16 big-five leagues
Date: 2026-09-28
Status: COMPLETE (every section run; interim pages 5abf571 and f1bf0f3; deviations in Section 4)

## Checklist
| Section | Status |
|---|---|
| Step 0 — brief committed alone | COMPLETE (5b80f43; operational note f89863f, both by the research lead) |
| Memory gate | COMPLETE (57% / 4.88 GB at 17:00 before Step 1; 54% / 4.53 GB at 18:43 before Step 2; 54% / 4.59 GB at 18:45 before Step 3; 49% / 5.55 GB at 19:05 before Steps 4-5) |
| Step 1 — ingest | COMPLETE |
| Step 2 — press-resistance gate (study sample) | COMPLETE (GATE PASS) |
| Step 3 — 2015/16 measures | COMPLETE |
| Step 4 — confirmatory tests, secondary, R1, praised list | COMPLETE |
| Step 5 — DM tables | COMPLETE for PR2_flag_keep; HOLD_VARIATION passes R1 but Task 29's method does not apply to an SD (Section 6, Q1) |

## 1. Headline
On untouched 2015/16 big-five data (1,551 matches, 185 deep midfielders with ≥500 eligible passes), **neither primary lead is confirmed**:
- **P1:** MOVE_ON_SPEED → net xG among deep midfielders is +0.0096 per 100 passes per SD, 95% CI [−0.0076, 0.0268], p = 0.27.
- **P2:** PR2_flag_keep → Y_F3 is +0.775 pp per 100 pressured receptions per SD, CI [−0.013, 1.562], p = 0.054, Holm p = 0.108. Both controls are strongly positive on the same rows.

Stability within deep midfielders (bar 0.60):
- **Pass:** PR2_flag_keep 0.666 (n = 185) and HOLD_VARIATION 0.730.
- **Fail:** MOVE_ON_SPEED 0.475 and PR2_flag_fwd 0.587.

Praised list: PR2_flag_keep is higher, in the pre-declared direction, T = +1.44, p = 0.0011, Holm p = 0.0044 across this task's 4 praised-list tests. This rests on 5 listed players present in 2015/16.

## 2. What I did
- **Decisions asked before Step 3** (2015/16 has no 360 frames; the author chose):
  - eligible pass = the engine's rule minus the frame condition (Pass, not an excluded pass type, non-goalkeeper passer, with an end location);
  - g features = Task 35's feature set minus every 360-derived feature (ball x, y, previous-event x, y, time remaining in the period, score difference, play pattern, under_pressure, period, minute), with the same XGBoost settings and 5 match folds (seed 20260928).
- `.venv/bin/python -W ignore src/engine_v2/task44_build.py` (Step 3):
  - Event-only features follow value_models_v5's non-frame logic.
  - PR2_flag uses Step 2's definition, with the baseline refit on 2015/16.
  - Tempo runs `time_on_ball.main()` and `redesign_metrics.main()` (Task 26 Step 2 patch) unchanged, with the event, time-on-ball, output and competition-lookup paths redirected to new 2015/16 files.
  - Roles use Task 32's rule on 2015/16 eligible-pass positions for players with ≥100 eligible passes. Deep midfielder = ≥50% DM positions AND ≥500 eligible passes.
- `.venv/bin/python -W ignore src/engine_v2/task44_tests.py` (Steps 4-5):
  - Model: `task35_ptest.fe_fit`, with S from Task 39's `s_for_rows` (tempo, ≥100 elsewhere) or `task42_step2.s_loo` (PR2, ≥50 elsewhere).
  - Controls: completion (passes) and Task 43's retention (receptions).
  - R1: Task 38's method (100 random half-splits of a player's matches), players ≥10 matches.
  - Praised list: Task 41's `perm_test` with 2015/16 roles.
  - Step 5: Task 29's method (`task42_step2.dm_table`).
- Reproduce: `task44_ingest.py`, then `task44_gate.py`, `task44_build.py`, `task44_tests.py`, in that order.
- `.venv/bin/python -W ignore src/engine_v2/task44_gate.py` (Step 2, study sample, run before any 2015/16 analysis):
  - Uses Task 43's spell outcomes (`task43_spells.parquet`).
  - PRESSURED_flag = `under_pressure` on the Ball Receipt* OR on the receiver's first on-ball event of the spell (his first Pass, Carry, Dribble, Shot, Miscontrol or Dispossessed after the receipt, same possession).
  - Baseline: Task 42's classifier settings, with event-only context (receipt location x, y, play pattern, period, minute), on Task 35's folds.
- `.venv/bin/python src/engine_v2/task44_ingest.py`:
  - Reads the author's unzipped open-data copy (`data/raw_1516/open-data-master/`). Match lists come from `data/matches/<comp>/27.json`; events from `data/events/<id>.json`.
  - Flattens each events file with statsbombpy's own `entities.events` + `helpers.filter_and_group_events` (what `sb.events` does after fetching).
  - Writes `data/raw_1516/events/<id>.parquet` and `data/raw_1516/matches/<comp>_27.parquet`.
  - Checks row counts against each JSON file's length.

## 3. Numbers

### Step 2 — gate (study sample, 292 matches)
- Completed receipts: 271,830. PRESSURED_flag: 62,006 (flag on the receipt 19,506; on the first spell event only 42,500).
- Units with a spell outcome: 59,911. Of these, 25,136 are also in Task 43's frame-based pressured set.
- keep_spell base rate 0.607, baseline OOF AUC 0.602. fwd_spell base rate 0.225, AUC 0.644.
- **Player mean PR2_flag_keep vs Task 43 PR2_keep: r = 0.840 [0.784, 0.881], n = 148 → GATE PASS (≥ 0.70).**

### Step 3 — 2015/16 measures
- Eligible passes (rule minus frame): 1,286,650. Completed receipts: 1,158,231.
- PRESSURED_flag: 333,082; with a spell outcome: 320,802.
- PR2_flag baselines: keep base rate 0.533, AUC 0.614; fwd base rate 0.214, AUC 0.647.
- Tempo:
  - time_on_ball resolved 813,250 of 1,286,650 open-play passes (63.2%); Carry sanity check passed; 29 excluded by the 0-15 s bound.
  - MOVE_ON_SPEED residuals: 647,581 (within R^2 0.185). HOLD_VARIATION residuals: 813,221 (within R^2 0.057).
- Outcomes (eligible passes): Y_F3 rate 0.685 (x < 80 units only in tests); net xG mean 0.0051.

Players per role (≥100 eligible passes) and deep midfielders (≥50% DM and ≥500 eligible passes), by league:

| League | CB | FB | DM (role) | CM | AM/W | FW | MIXED | deep midfielders |
|---|---|---|---|---|---|---|---|---|
| Premier League | 72 | 80 | 49 | 23 | 99 | 46 | 20 | 40 |
| Ligue 1 | 77 | 85 | 66 | 34 | 100 | 49 | 8 | 48 |
| Bundesliga | 13 | 6 | 9 | 1 | 5 | 2 | 0 | 3 |
| La Liga | 78 | 84 | 63 | 13 | 110 | 49 | 13 | 51 |
| Serie A | 88 | 93 | 57 | 53 | 71 | 55 | 11 | 43 |
| **Total** | 328 | 348 | 244 | 124 | 385 | 201 | 52 | **185** |

### Step 4 — PRIMARY (within deep midfielders; Holm across the two; bars fixed in the brief)

| Test | coef per 100 per SD | 95% CI | p | Holm p | control on same rows | CONFIRMED |
|---|---|---|---|---|---|---|
| dm|move_on_speed|y_net_xg | +0.0096 | [-0.0076, 0.0268] | 0.2744 | 0.2744 | +2.999, p=1.4e-63 | no |
| dm|pr2_flag_keep|y_f3 | +0.7747 | [-0.0129, 1.5624] | 0.05386 | 0.1077 | +3.894, p=1.5e-21 | no |

Neither is confirmed: P1 p = 0.27; P2 Holm p = 0.108.

### Step 4 — all tests (primary and secondary; secondary reported, not claimed)
Units: tempo on eligible passes; PR2 on pressured receptions. Coefficients are pp (Y_F3) or xG (net xG) per 100 units per SD. g OOF R^2 (event-only):
- passes: net xG 0.051, Y_F3 0.153, completion 0.099;
- pressured receptions: net xG 0.023, Y_F3 0.094, keep 0.061.

| Group | S | Y | n | players | coef | 95% CI | p | MDE | control coef [95% CI], p |
|---|---|---|---|---|---|---|---|---|---|
| DM | move_on_speed | net xG | 221,095 | 185 | +0.0096 | [-0.0076, 0.0268] | 0.274 | 0.0246 | +2.999 [2.649, 3.348], 1.4e-63 |
| DM | hold_variation | net xG | 221,095 | 185 | -0.0341 | [-0.0556, -0.0126] | 0.0019 | 0.0307 | +2.999 [2.649, 3.348], 1.4e-63 |
| DM | pr2_flag_keep | net xG | 41,414 | 185 | -0.0273 | [-0.0684, 0.0137] | 0.192 | 0.0586 | +3.692 [2.959, 4.424], 5.1e-23 |
| DM | pr2_flag_fwd | net xG | 41,414 | 185 | +0.0182 | [-0.0208, 0.0571] | 0.361 | 0.0557 | +3.692 [2.959, 4.424], 5.1e-23 |
| DM | move_on_speed | Y_F3 | 191,745 | 185 | -0.1765 | [-0.4190, 0.0659] | 0.154 | 0.3464 | +2.941 [2.558, 3.324], 4e-51 |
| DM | hold_variation | Y_F3 | 191,745 | 185 | +0.4011 | [0.1403, 0.6619] | 0.00257 | 0.3726 | +2.941 [2.558, 3.324], 4e-51 |
| DM | pr2_flag_keep | Y_F3 | 34,822 | 185 | +0.7747 | [-0.0129, 1.5624] | 0.0539 | 1.1252 | +3.894 [3.094, 4.694], 1.5e-21 |
| DM | pr2_flag_fwd | Y_F3 | 34,822 | 185 | +0.7559 | [0.0712, 1.4406] | 0.0305 | 0.9781 | +3.894 [3.094, 4.694], 1.5e-21 |
| all | move_on_speed | net xG | 1,215,039 | 1442 | -0.0008 | [-0.0134, 0.0117] | 0.897 | 0.0179 | +4.541 [4.383, 4.700], 0 |
| all | hold_variation | net xG | 1,235,801 | 1543 | +0.0057 | [-0.0040, 0.0155] | 0.249 | 0.0140 | +4.554 [4.398, 4.711], 0 |
| all | pr2_flag_keep | net xG | 300,404 | 1498 | -0.0457 | [-0.0682, -0.0232] | 7.01e-05 | 0.0322 | +8.396 [7.956, 8.837], 2.9e-305 |
| all | pr2_flag_fwd | net xG | 300,404 | 1498 | +0.0083 | [-0.0112, 0.0278] | 0.404 | 0.0278 | +8.396 [7.956, 8.837], 2.9e-305 |
| all | move_on_speed | Y_F3 | 941,534 | 1442 | -0.3249 | [-0.4770, -0.1728] | 2.83e-05 | 0.2173 | +4.098 [3.919, 4.278], 0 |
| all | hold_variation | Y_F3 | 955,525 | 1543 | +0.1354 | [0.0023, 0.2685] | 0.0461 | 0.1902 | +4.114 [3.936, 4.292], 0 |
| all | pr2_flag_keep | Y_F3 | 203,001 | 1497 | +1.8347 | [1.5037, 2.1656] | 1.71e-27 | 0.4728 | +8.331 [7.804, 8.859], 2.7e-210 |
| all | pr2_flag_fwd | Y_F3 | 203,001 | 1497 | +1.7478 | [1.4332, 2.0624] | 1.31e-27 | 0.4495 | +8.331 [7.804, 8.859], 2.7e-210 |

### Step 4 — R1 stability (Task 38's method; players with ≥10 matches; median [p5, p95] (n))

| Measure | deep midfielders | bar 0.60 | all players |
|---|---|---|---|
| move_on_speed | 0.475 [0.372, 0.537] (185) | FAIL | 0.604 [0.566, 0.637] (1505) |
| hold_variation | 0.730 [0.678, 0.772] (185) | PASS | 0.749 [0.731, 0.767] (1522) |
| pr2_flag_keep | 0.666 [0.610, 0.714] (185) | PASS | 0.755 [0.737, 0.775] (1590) |
| pr2_flag_fwd | 0.587 [0.511, 0.653] (185) | FAIL | 0.652 [0.629, 0.676] (1590) |

### Step 4 — praised list (Task 41's method; 2015/16 Task 32 roles)
- Listed names found in 2015/16: Kroos, Modrić, Verratti, Busquets, De Bruyne, Xhaka.
- "de Jong" matches two different players (Siem de Jong, Nigel de Jong), neither of them Frenkie de Jong, so it was excluded rather than guessed.
- Not in 2015/16 data: Kimmich, Rodri, Pedri, Gündoğan, Grillitsch, Shaparenko.
- Present in each measure after floors (≥100 tempo passes; ≥50 pressured receptions) and roles: Kroos, Modrić, Verratti, Busquets, De Bruyne (5). Xhaka falls below the floors.

| Measure | qualifying | present | T | p (two-sided) | Holm p (4 tests) | pre-declared direction |
|---|---|---|---|---|---|---|
| move_on_speed | 1446 | 5 | +0.141 | 0.7545 | 1 | none (two-sided) |
| hold_variation | 1551 | 5 | -0.022 | 0.9624 | 1 | none (two-sided) |
| pr2_flag_keep | 1442 | 5 | +1.444 | 0.0011 | 0.0044 | higher |
| pr2_flag_fwd | 1442 | 5 | +1.031 | 0.0229 | 0.06869 | none (two-sided) |

z-scores:
- **PR2_flag_keep:** Kevin De Bruyne +0.24, Marco Verratti +2.18, Sergio Busquets i Burgos +1.75, Luka Modrić +1.38, Toni Kroos +1.67.
- **PR2_flag_fwd:** Kevin De Bruyne +1.69, Marco Verratti +1.79, Sergio Busquets i Burgos -0.26, Luka Modrić +1.32, Toni Kroos +0.62.
- **MOVE_ON_SPEED:** Kevin De Bruyne +1.63, Marco Verratti -1.54, Sergio Busquets i Burgos +1.98, Luka Modrić -0.96, Toni Kroos -0.41.
- **HOLD_VARIATION:** Kevin De Bruyne -1.43, Marco Verratti +0.34, Sergio Busquets i Burgos +1.28, Luka Modrić +0.44, Toni Kroos -0.74.

### Step 5 — deep-midfield table: PR2_flag_keep (passes R1; Task 29's method, 185 deep midfielders; output only)
- mu_w = +0.0872, tau^2 = 0.00294, **Q = 703.6 on 184 df, p < 1e-15**.
- Entirely above the mean (27): Thiago Motta, Jorge Luiz Frello Filho, Claudio Marchisio, Sergio Busquets i Burgos, Toni Kroos, Andrew Surman, Gary Alexis Medel Soto, Nampalys Mendy, Matías Vecino Falero, João Filipe Iria Santos Moutinho, Mohamed Naser Elsayed Elneny, Francesco Lodi, John Michael Nchekwube Obinna, Kevin Kampl, James McCarthy, Daniele De Rossi, Rémi Gomis, Bruno Soriano Llido, Jérémy Clément, Gélson da Conceição Tavares Fernandes, Santiago Cazorla González, Maxime Gonalons, Lucas Rodrigo Biglia, Christoph Kramer, Glenn Whelan, Mousa Sidi Yaya Dembélé, Francesco Magnanelli.
- Entirely below (35): Benjamin André, Walid Mesloub, Alfred John Momar N''Diaye, Cheikhou Kouyaté, Daniel García Carrillo, Aaron Ramsey, Seko Fofana, Álvaro Medrán Just, Grzegorz Krychowiak, Sebastián Carlos Cristóforo Pepe, Sergio Álvarez Díaz, José Vicente Gómez Umpiérrez, Víctor Sánchez Mata, Tomás Pina Isla, José Raúl Baena Urdiales, Rio Antonio Zoba Mavuba, Claudio Ariel Yacob, Isaac Cofie, Moustapha Elhadji Diallo, Mirko Gori, Robert Gucher, Yann Bodiger, Pablo Fornals Malla, Andrea Bertolacci, Rubén Salvador Pérez Del Mármol, Omar Mascarell González, Steven N''Kemboanza Mike Christopher Nzonzi, Étienne Didot, Vincent Pajot, Blerim Džemaili, William Jean Rémy, Gonzalo Escalante, Younousse Sankharé, Ignacio Cases Mora, Jan Kirchhoff.
- HOLD_VARIATION also passes R1, but it is a per-player SD of residuals, and Task 29's per-unit-mean method does not apply to it. No table was produced (Q1).

| # | Player | matches | pressured receptions | raw | shrunken | 90% low | 90% high |
|---|---|---|---|---|---|---|---|
| 1 | Thiago Motta | 31 | 568 | +0.2272 | +0.2085 | +0.1759 | +0.2411 |
| 2 | Jorge Luiz Frello Filho | 35 | 663 | +0.2229 | +0.2069 | +0.1764 | +0.2375 |
| 3 | Claudio Marchisio | 23 | 249 | +0.2263 | +0.1924 | +0.1484 | +0.2364 |
| 4 | Sergio Busquets i Burgos | 35 | 427 | +0.1916 | +0.1748 | +0.1391 | +0.2105 |
| 5 | Toni Kroos | 32 | 350 | +0.1865 | +0.1680 | +0.1294 | +0.2065 |
| 6 | Andrew Surman | 38 | 298 | +0.1864 | +0.1660 | +0.1255 | +0.2064 |
| 7 | Gary Alexis Medel Soto | 29 | 203 | +0.1893 | +0.1613 | +0.1147 | +0.2080 |
| 8 | Nampalys Mendy | 38 | 501 | +0.1670 | +0.1557 | +0.1221 | +0.1892 |
| 9 | Matías Vecino Falero | 30 | 426 | +0.1665 | +0.1535 | +0.1174 | +0.1896 |
| 10 | João Filipe Iria Santos Moutinho | 26 | 338 | +0.1679 | +0.1521 | +0.1126 | +0.1915 |
| 11 | Mohamed Naser Elsayed Elneny | 11 | 112 | +0.1925 | +0.1487 | +0.0913 | +0.2062 |
| 12 | Francesco Lodi | 24 | 218 | +0.1708 | +0.1486 | +0.1027 | +0.1945 |
| 13 | John Michael Nchekwube Obinna | 24 | 160 | +0.1772 | +0.1482 | +0.0975 | +0.1988 |
| 14 | Kevin Kampl | 22 | 310 | +0.1635 | +0.1473 | +0.1062 | +0.1884 |
| 15 | James McCarthy | 28 | 181 | +0.1721 | +0.1470 | +0.0985 | +0.1955 |
| 16 | Daniele De Rossi | 20 | 130 | +0.1810 | +0.1464 | +0.0922 | +0.2005 |
| 17 | Rémi Gomis | 16 | 133 | +0.1776 | +0.1442 | +0.0900 | +0.1984 |
| 18 | Bruno Soriano Llido | 30 | 243 | +0.1607 | +0.1429 | +0.0990 | +0.1867 |
| 19 | Jérémy Clément | 25 | 129 | +0.1745 | +0.1425 | +0.0885 | +0.1965 |
| 20 | Gélson da Conceição Tavares Fernandes | 33 | 270 | +0.1580 | +0.1422 | +0.1001 | +0.1844 |
| 21 | Santiago Cazorla González | 15 | 196 | +0.1626 | +0.1403 | +0.0918 | +0.1888 |
| 22 | Maxime Gonalons | 33 | 305 | +0.1526 | +0.1392 | +0.0988 | +0.1796 |
| 23 | Lucas Rodrigo Biglia | 27 | 361 | +0.1496 | +0.1379 | +0.0994 | +0.1764 |
| 24 | Alexander Banor Tettey | 22 | 155 | +0.1581 | +0.1346 | +0.0834 | +0.1859 |
| 25 | Christoph Kramer | 28 | 359 | +0.1412 | +0.1312 | +0.0927 | +0.1697 |
| 26 | Glenn Whelan | 37 | 250 | +0.1439 | +0.1306 | +0.0875 | +0.1737 |
| 27 | Giuseppe Vives | 31 | 222 | +0.1455 | +0.1305 | +0.0853 | +0.1757 |
| 28 | Mousa Sidi Yaya Dembélé | 29 | 405 | +0.1391 | +0.1303 | +0.0934 | +0.1671 |
| 29 | Fernando Francisco Reges | 23 | 117 | +0.1522 | +0.1268 | +0.0712 | +0.1825 |
| 30 | Anderson Hernanes de Carvalho Andrade | 15 | 187 | +0.1427 | +0.1258 | +0.0766 | +0.1750 |
| 31 | Milan Badelj | 27 | 366 | +0.1342 | +0.1255 | +0.0872 | +0.1638 |
| 32 | Francesco Magnanelli | 34 | 436 | +0.1321 | +0.1250 | +0.0895 | +0.1605 |
| 33 | Danilo Cataldi | 18 | 124 | +0.1476 | +0.1245 | +0.0695 | +0.1796 |
| 34 | Augusto Matías Fernández | 27 | 218 | +0.1354 | +0.1227 | +0.0771 | +0.1684 |
| 35 | Leandro Daniel Paredes | 33 | 458 | +0.1283 | +0.1220 | +0.0870 | +0.1569 |
| 36 | Enzo Maresca | 13 | 113 | +0.1447 | +0.1212 | +0.0642 | +0.1782 |
| 37 | Zdravko Kuzmanović | 16 | 107 | +0.1438 | +0.1202 | +0.0627 | +0.1777 |
| 38 | Nemanja Matić | 32 | 294 | +0.1283 | +0.1196 | +0.0787 | +0.1606 |
| 39 | Celso Borges Mora | 24 | 203 | +0.1301 | +0.1182 | +0.0712 | +0.1652 |
| 40 | Ben Watson | 32 | 169 | +0.1305 | +0.1172 | +0.0678 | +0.1666 |
| 41 | Abdoulaye Doucouré | 30 | 304 | +0.1236 | +0.1161 | +0.0755 | +0.1567 |
| 42 | Seydou Kéita | 19 | 131 | +0.1305 | +0.1146 | +0.0604 | +0.1687 |
| 43 | Amadou Diawara | 34 | 313 | +0.1205 | +0.1138 | +0.0738 | +0.1537 |
| 44 | Prince Oniangué | 27 | 231 | +0.1227 | +0.1137 | +0.0689 | +0.1585 |
| 45 | Nicolas Seube | 30 | 132 | +0.1280 | +0.1133 | +0.0599 | +0.1668 |
| 46 | Francis Joseph Coquelin | 24 | 210 | +0.1220 | +0.1126 | +0.0661 | +0.1590 |
| 47 | Ogenyi Eddy Onazi | 15 | 142 | +0.1257 | +0.1119 | +0.0587 | +0.1652 |
| 48 | Mathieu Flamini | 14 | 74 | +0.1351 | +0.1110 | +0.0478 | +0.1742 |
| 49 | Ivan Radovanović | 26 | 245 | +0.1184 | +0.1108 | +0.0668 | +0.1548 |
| 50 | Clément Chantôme | 25 | 234 | +0.1173 | +0.1097 | +0.0650 | +0.1545 |
| 51 | Gabriel Fernández Arenas | 35 | 280 | +0.1156 | +0.1094 | +0.0679 | +0.1510 |
| 52 | Alessandro Gazzi | 14 | 86 | +0.1266 | +0.1082 | +0.0472 | +0.1692 |
| 53 | Gareth Barry | 32 | 263 | +0.1137 | +0.1076 | +0.0650 | +0.1502 |
| 54 | Felipe Melo de Carvalho | 25 | 224 | +0.1139 | +0.1069 | +0.0615 | +0.1524 |
| 55 | Graham Dorrans | 21 | 160 | +0.1162 | +0.1068 | +0.0559 | +0.1576 |
| 56 | Mehdi Mostefa Sbaa | 24 | 173 | +0.1151 | +0.1065 | +0.0571 | +0.1560 |
| 57 | Cheik Ismaël Tioté | 19 | 121 | +0.1174 | +0.1058 | +0.0504 | +0.1611 |
| 58 | Assane Dioussé El Hadji | 15 | 184 | +0.1136 | +0.1055 | +0.0561 | +0.1549 |
| 59 | Carlos Alberto Sánchez Moreno | 18 | 111 | +0.1146 | +0.1035 | +0.0467 | +0.1603 |
| 60 | Michael Carrick | 27 | 221 | +0.1082 | +0.1028 | +0.0573 | +0.1482 |
| 61 | Jordy Clasie | 21 | 110 | +0.1129 | +0.1025 | +0.0458 | +0.1592 |
| 62 | Fernando Lucas Martins | 35 | 407 | +0.1053 | +0.1023 | +0.0660 | +0.1386 |
| 63 | Guillaume Gillet | 19 | 170 | +0.1092 | +0.1023 | +0.0522 | +0.1524 |
| 64 | Morgan Schneiderlin | 27 | 186 | +0.1076 | +0.1017 | +0.0535 | +0.1498 |
| 65 | Oriol Romeu Vidal | 25 | 170 | +0.1080 | +0.1016 | +0.0519 | +0.1512 |
| 66 | François Bellugou | 31 | 217 | +0.1053 | +0.1006 | +0.0551 | +0.1461 |
| 67 | José Luis García del Pozo | 33 | 340 | +0.1027 | +0.0998 | +0.0609 | +0.1386 |
| 68 | Lucas Silva Borges | 18 | 175 | +0.1052 | +0.0996 | +0.0498 | +0.1494 |
| 69 | Ryan Mason | 18 | 80 | +0.1103 | +0.0992 | +0.0374 | +0.1610 |
| 70 | Gilbert Gianelli Imbula Wanga | 14 | 244 | +0.1024 | +0.0984 | +0.0528 | +0.1441 |
| 71 | Javier Fuego Martínez | 24 | 183 | +0.1026 | +0.0980 | +0.0495 | +0.1466 |
| 72 | Papa Kouly Diop | 29 | 199 | +0.1003 | +0.0966 | +0.0497 | +0.1436 |
| 73 | Gnégnéri Yaya Touré | 31 | 425 | +0.0985 | +0.0966 | +0.0606 | +0.1327 |
| 74 | Lassana Diarra | 26 | 282 | +0.0976 | +0.0953 | +0.0534 | +0.1373 |
| 75 | Bastian Schweinsteiger | 18 | 197 | +0.0984 | +0.0951 | +0.0471 | +0.1431 |
| 76 | Jonas Martin | 36 | 574 | +0.0956 | +0.0945 | +0.0624 | +0.1266 |
| 77 | Lars Bender | 11 | 96 | +0.1000 | +0.0943 | +0.0345 | +0.1540 |
| 78 | Alejandro Bergantiños García | 21 | 145 | +0.0969 | +0.0935 | +0.0411 | +0.1459 |
| 79 | Roberto Trashorras Gayoso | 36 | 568 | +0.0928 | +0.0921 | +0.0599 | +0.1242 |
| 80 | Carlos Henrique Casimiro | 23 | 152 | +0.0924 | +0.0907 | +0.0392 | +0.1422 |
| 81 | Rubén Pardo Gutiérrez | 27 | 159 | +0.0907 | +0.0895 | +0.0390 | +0.1401 |
| 82 | Leon Britton | 23 | 183 | +0.0905 | +0.0895 | +0.0409 | +0.1381 |
| 83 | Pedro Mosquera Parada | 36 | 277 | +0.0892 | +0.0888 | +0.0471 | +0.1304 |
| 84 | Benjamin Stambouli | 25 | 198 | +0.0888 | +0.0884 | +0.0411 | +0.1356 |
| 85 | Jacques-Alaixys Romao | 19 | 141 | +0.0890 | +0.0884 | +0.0354 | +0.1413 |
| 86 | Mato Jajalo | 25 | 216 | +0.0887 | +0.0883 | +0.0423 | +0.1342 |
| 87 | Juan Antonio Rodríguez Villamuela | 29 | 153 | +0.0884 | +0.0880 | +0.0369 | +0.1391 |
| 88 | Roque Mesa Quevedo | 34 | 467 | +0.0876 | +0.0876 | +0.0529 | +0.1222 |
| 89 | Mario Lemina | 14 | 114 | +0.0877 | +0.0875 | +0.0307 | +0.1442 |
| 90 | Nemanja Radoja | 22 | 124 | +0.0868 | +0.0869 | +0.0322 | +0.1417 |
| 91 | Fabien Lemoine | 32 | 349 | +0.0864 | +0.0866 | +0.0480 | +0.1251 |
| 92 | José Antonio García Rabasco | 27 | 191 | +0.0859 | +0.0863 | +0.0386 | +0.1340 |
| 93 | Mauricio Aníbal Isla Isla | 24 | 180 | +0.0841 | +0.0850 | +0.0362 | +0.1338 |
| 94 | Mikel San José Domínguez | 31 | 176 | +0.0831 | +0.0843 | +0.0356 | +0.1331 |
| 95 | Riccardo Montolivo | 31 | 358 | +0.0831 | +0.0838 | +0.0456 | +0.1221 |
| 96 | Leandro Greco | 26 | 271 | +0.0822 | +0.0834 | +0.0408 | +0.1259 |
| 97 | Romain Saïss | 35 | 201 | +0.0817 | +0.0832 | +0.0367 | +0.1298 |
| 98 | Federico Viviani | 19 | 233 | +0.0810 | +0.0826 | +0.0372 | +0.1280 |
| 99 | Antoine Devaux | 33 | 331 | +0.0812 | +0.0824 | +0.0432 | +0.1216 |
| 100 | Lionel Mathis | 19 | 147 | +0.0786 | +0.0816 | +0.0292 | +0.1339 |
| 101 | Yann Gérard M''Vila | 37 | 248 | +0.0787 | +0.0807 | +0.0374 | +0.1239 |
| 102 | James McArthur | 27 | 217 | +0.0781 | +0.0805 | +0.0347 | +0.1262 |
| 103 | Henri Saivet | 21 | 205 | +0.0773 | +0.0801 | +0.0330 | +0.1271 |
| 104 | Manuel Trigueros Muñoz | 29 | 251 | +0.0770 | +0.0794 | +0.0360 | +0.1229 |
| 105 | Yohan Cabaye | 33 | 238 | +0.0767 | +0.0792 | +0.0352 | +0.1233 |
| 106 | Yannick Cahuzac | 29 | 266 | +0.0766 | +0.0790 | +0.0365 | +0.1216 |
| 107 | Tiago Cardoso Mendes | 14 | 97 | +0.0678 | +0.0763 | +0.0171 | +0.1355 |
| 108 | Jaba Kankava | 27 | 250 | +0.0722 | +0.0758 | +0.0322 | +0.1195 |
| 109 | Luca Marrone | 21 | 173 | +0.0698 | +0.0752 | +0.0256 | +0.1249 |
| 110 | Didier Ndong Ibrahim | 34 | 428 | +0.0725 | +0.0748 | +0.0391 | +0.1106 |
| 111 | Francisco Manuel Rico Castro | 27 | 178 | +0.0695 | +0.0748 | +0.0260 | +0.1236 |
| 112 | Eric Dier | 37 | 249 | +0.0701 | +0.0741 | +0.0309 | +0.1173 |
| 113 | Lucas Pezzini Leiva | 25 | 124 | +0.0662 | +0.0741 | +0.0195 | +0.1287 |
| 114 | Mehdi Lacen | 31 | 264 | +0.0691 | +0.0733 | +0.0307 | +0.1158 |
| 115 | Marten de Roon | 35 | 292 | +0.0695 | +0.0732 | +0.0323 | +0.1142 |
| 116 | Marcelo Alfonso Díaz Rojas | 14 | 100 | +0.0622 | +0.0730 | +0.0143 | +0.1318 |
| 117 | Mario Suárez Mata | 22 | 148 | +0.0645 | +0.0722 | +0.0202 | +0.1242 |
| 118 | Fernando Damián Tissone | 12 | 105 | +0.0595 | +0.0713 | +0.0131 | +0.1296 |
| 119 | Alexis Blin | 21 | 114 | +0.0598 | +0.0707 | +0.0145 | +0.1268 |
| 120 | Alberto Facundo Costa | 19 | 213 | +0.0640 | +0.0704 | +0.0237 | +0.1171 |
| 121 | Rene Krhin | 19 | 63 | +0.0494 | +0.0697 | +0.0044 | +0.1350 |
| 122 | Yacouba Sylla | 20 | 205 | +0.0606 | +0.0681 | +0.0209 | +0.1152 |
| 123 | Asier Illarramendi Andonegi | 33 | 282 | +0.0626 | +0.0680 | +0.0265 | +0.1095 |
| 124 | Jérôme Le Moigne | 28 | 167 | +0.0583 | +0.0673 | +0.0176 | +0.1171 |
| 125 | Jérémy Toulalan | 25 | 210 | +0.0581 | +0.0660 | +0.0196 | +0.1123 |
| 126 | Gastón Brugman | 13 | 124 | +0.0518 | +0.0656 | +0.0100 | +0.1212 |
| 127 | Thomas Ayasse | 14 | 128 | +0.0511 | +0.0649 | +0.0099 | +0.1199 |
| 128 | Ignacio Camacho Barnola | 23 | 186 | +0.0536 | +0.0635 | +0.0151 | +0.1118 |
| 129 | Petros Matheus dos Santos Araújo | 30 | 213 | +0.0532 | +0.0622 | +0.0163 | +0.1080 |
| 130 | Hernán Daniel Santana Trujillo | 18 | 96 | +0.0422 | +0.0620 | +0.0029 | +0.1210 |
| 131 | Tomás Eduardo Rincón Hernández | 33 | 416 | +0.0569 | +0.0619 | +0.0257 | +0.0981 |
| 132 | Lucas Deaux | 14 | 82 | +0.0348 | +0.0599 | -0.0018 | +0.1216 |
| 133 | Beñat Etxebarria Urkiaga | 35 | 380 | +0.0540 | +0.0598 | +0.0226 | +0.0970 |
| 134 | Mile Jedinak | 22 | 113 | +0.0408 | +0.0593 | +0.0030 | +0.1155 |
| 135 | Raffaele Bianco | 26 | 188 | +0.0465 | +0.0583 | +0.0103 | +0.1063 |
| 136 | Paolo Sammarco | 27 | 186 | +0.0459 | +0.0580 | +0.0098 | +0.1061 |
| 137 | Jessy Pi | 36 | 338 | +0.0493 | +0.0565 | +0.0177 | +0.0953 |
| 138 | Gary O''Neil | 22 | 151 | +0.0307 | +0.0497 | -0.0020 | +0.1013 |
| 139 | Jack Colback | 28 | 152 | +0.0304 | +0.0492 | -0.0020 | +0.1005 |
| 140 | Simão Mate | 29 | 152 | +0.0285 | +0.0479 | -0.0033 | +0.0991 |
| 141 | Birama Touré | 22 | 169 | +0.0297 | +0.0478 | -0.0022 | +0.0977 |
| 142 | Tiemoué Bakayoko | 18 | 151 | +0.0262 | +0.0470 | -0.0050 | +0.0990 |
| 143 | Victor Wanyama | 30 | 226 | +0.0319 | +0.0460 | +0.0010 | +0.0909 |
| 144 | Ibrahim Amadou | 19 | 150 | +0.0246 | +0.0459 | -0.0061 | +0.0979 |
| 145 | Benjamin André | 32 | 612 | +0.0388 | +0.0449 | +0.0133 | +0.0766 |
| 146 | Fernando Luiz Rosa | 33 | 255 | +0.0320 | +0.0448 | +0.0018 | +0.0878 |
| 147 | Manuel Rolando Iturra Urrutia | 21 | 115 | +0.0166 | +0.0445 | -0.0115 | +0.1005 |
| 148 | Nicola Rigoni | 24 | 169 | +0.0243 | +0.0439 | -0.0059 | +0.0937 |
| 149 | Walid Mesloub | 29 | 400 | +0.0340 | +0.0432 | +0.0062 | +0.0802 |
| 150 | Alfred John Momar N''Diaye | 34 | 298 | +0.0272 | +0.0397 | -0.0010 | +0.0804 |
| 151 | Jordan Adéoti | 26 | 94 | -0.0010 | +0.0377 | -0.0213 | +0.0967 |
| 152 | Enzo Nicolás Pérez | 20 | 152 | +0.0115 | +0.0370 | -0.0147 | +0.0887 |
| 153 | Cheikhou Kouyaté | 34 | 221 | +0.0191 | +0.0365 | -0.0086 | +0.0816 |
| 154 | Daniel García Carrillo | 35 | 243 | +0.0197 | +0.0359 | -0.0077 | +0.0795 |
| 155 | Aaron Ramsey | 31 | 484 | +0.0268 | +0.0358 | +0.0013 | +0.0702 |
| 156 | Seko Fofana | 31 | 347 | +0.0233 | +0.0353 | -0.0034 | +0.0740 |
| 157 | Álvaro Medrán Just | 19 | 193 | +0.0120 | +0.0340 | -0.0142 | +0.0822 |
| 158 | Grzegorz Krychowiak | 25 | 149 | +0.0054 | +0.0330 | -0.0187 | +0.0847 |
| 159 | Markel Bergara Larrañaga | 17 | 68 | -0.0266 | +0.0326 | -0.0317 | +0.0969 |
| 160 | Sebastián Carlos Cristóforo Pepe | 21 | 163 | +0.0062 | +0.0323 | -0.0183 | +0.0828 |
| 161 | Sergio Álvarez Díaz | 27 | 243 | +0.0136 | +0.0316 | -0.0125 | +0.0756 |
| 162 | José Vicente Gómez Umpiérrez | 21 | 196 | +0.0089 | +0.0313 | -0.0164 | +0.0791 |
| 163 | Víctor Sánchez Mata | 28 | 205 | +0.0047 | +0.0272 | -0.0194 | +0.0737 |
| 164 | Tomás Pina Isla | 24 | 155 | -0.0032 | +0.0266 | -0.0246 | +0.0777 |
| 165 | José Raúl Baena Urdiales | 24 | 142 | -0.0091 | +0.0243 | -0.0282 | +0.0769 |
| 166 | Rio Antonio Zoba Mavuba | 32 | 252 | +0.0032 | +0.0229 | -0.0203 | +0.0661 |
| 167 | Claudio Ariel Yacob | 33 | 155 | -0.0126 | +0.0197 | -0.0310 | +0.0705 |
| 168 | Isaac Cofie | 28 | 149 | -0.0174 | +0.0176 | -0.0339 | +0.0692 |
| 169 | Moustapha Elhadji Diallo | 27 | 167 | -0.0151 | +0.0169 | -0.0329 | +0.0667 |
| 170 | Mirko Gori | 26 | 203 | -0.0112 | +0.0160 | -0.0309 | +0.0628 |
| 171 | Robert Gucher | 23 | 97 | -0.0423 | +0.0137 | -0.0449 | +0.0723 |
| 172 | Yann Bodiger | 19 | 106 | -0.0391 | +0.0133 | -0.0441 | +0.0707 |
| 173 | Pablo Fornals Malla | 27 | 162 | -0.0243 | +0.0112 | -0.0391 | +0.0615 |
| 174 | Andrea Bertolacci | 27 | 266 | -0.0120 | +0.0108 | -0.0319 | +0.0536 |
| 175 | Rubén Salvador Pérez Del Mármol | 31 | 229 | -0.0158 | +0.0101 | -0.0346 | +0.0548 |
| 176 | Omar Mascarell González | 23 | 112 | -0.0431 | +0.0089 | -0.0474 | +0.0653 |
| 177 | Steven N''Kemboanza Mike Christopher Nzonzi | 27 | 140 | -0.0358 | +0.0070 | -0.0456 | +0.0596 |
| 178 | Étienne Didot | 23 | 235 | -0.0225 | +0.0053 | -0.0396 | +0.0502 |
| 179 | Vincent Pajot | 26 | 177 | -0.0381 | -0.0003 | -0.0493 | +0.0486 |
| 180 | Blerim Džemaili | 26 | 219 | -0.0326 | -0.0011 | -0.0468 | +0.0445 |
| 181 | William Jean Rémy | 27 | 174 | -0.0412 | -0.0022 | -0.0513 | +0.0470 |
| 182 | Gonzalo Escalante | 34 | 235 | -0.0363 | -0.0060 | -0.0502 | +0.0382 |
| 183 | Younousse Sankharé | 32 | 293 | -0.0384 | -0.0118 | -0.0528 | +0.0292 |
| 184 | Ignacio Cases Mora | 23 | 159 | -0.0637 | -0.0147 | -0.0655 | +0.0361 |
| 185 | Jan Kirchhoff | 15 | 110 | -0.0861 | -0.0148 | -0.0720 | +0.0424 |

### Fixed claim rules, applied mechanically
- **PRIMARY:** P1 and P2 are NOT CONFIRMED (Holm p 0.274 and 0.108; both controls positive with p < 1e-20).
- **Stability:** PR2_flag_keep (0.666) and HOLD_VARIATION (0.730) meet the 0.60 bar within deep midfielders. MOVE_ON_SPEED (0.475) and PR2_flag_fwd (0.587) do not.
- **Praised list:** PR2_flag_keep, in the pre-declared direction (higher), has Holm p = 0.0044 < 0.05, which meets the brief's condition for a statement. PR2_flag_fwd (Holm 0.069, no declared direction), MOVE_ON_SPEED and HOLD_VARIATION (Holm 1.0) do not.

### Step 1 — ingest
| Competition | matches listed | ingested | events |
|---|---|---|---|
| Premier League (2) | 380 | 380 | 1,313,773 |
| Ligue 1 (7) | 377 | 377 | 1,358,593 |
| 1. Bundesliga (9) | 34 | 34 | 115,240 |
| La Liga (11) | 380 | 380 | 1,295,354 |
| Serie A (12) | 380 | 380 | 1,353,739 |

Coordinate check: 6,155 team-periods with shots, and a share of 1.0000 have mean shot x > 60.

## 4. Deviations from the brief
- **Coordinate check:** only task24_evidence.py's part (i) was run. Its parts (ii) and (iii) need 360 frames, which 2015/16 does not have.
- **Author's decisions for the missing 360 data** (Section 2): eligible pass = the engine rule minus the frame condition; g = Task 35's features minus the 360-derived ones.
- **Role population:** the Task 32 rule is applied to players with ≥100 eligible passes (Task 32's own population floor). The brief's ≥500 applies to the deep-midfield group.
- **2015/16 match folds:** a seeded (20260928) permutation of the 1,551 match ids into 5 folds.
- **R1 for HOLD_VARIATION** uses each half's residual SD (ddof = 1), because the metric is an SD. The other measures use half-means.
- **Praised list:** "de Jong" was excluded as ambiguous. Holm covers the 4 praised-list tests of this task.
- **Tempo competition lookup:** redirected to the 2015/16 match files so the unchanged code can attach competition/season.

## 5. Problems and surprises
- **P2 is close but not confirmed.** Raw p = 0.054 and the estimate (+0.77) is below its MDE (1.13). For all players, PR2_flag_keep → Y_F3 is +1.83 (p = 2e-27), but that is secondary.
- **Secondary within deep midfielders:**
  - HOLD_VARIATION → net xG is negative (−0.034, p = 0.0019).
  - HOLD_VARIATION → Y_F3 is positive (+0.401, p = 0.0026).
  - PR2_flag_fwd → Y_F3 is +0.756 (p = 0.030).
  - None of these is a primary test.
- **Secondary for all players:**
  - MOVE_ON_SPEED → Y_F3 is negative (−0.325, p = 3e-5).
  - PR2_flag_keep → net xG is negative (−0.046, p = 7e-5).
- **MOVE_ON_SPEED fails R1 within deep midfielders** (0.475) on 2015/16, while it passed its original reliability bar on the study sample (Task 26 Step 2). The two use different methods and units, so they are not directly comparable.
- **The praised-list result rests on 5 players** (Kroos, Modrić, Verratti, Busquets, De Bruyne).
- **The Bundesliga has only 34 matches,** so its players are sparse (9 in the DM role, 3 deep midfielders).
- The Bundesliga has 34 matches, not a full season, and Ligue 1 has 377 matches, not 380. These are the files in StatsBomb's lists; nothing listed is missing.

## 6. Questions for the research lead
- Q1: HOLD_VARIATION passes R1 within deep midfielders, but Task 29's table method needs a per-unit mean. Should a table be built for it, for example on squared residual deviations, or is none wanted?

## 7. Files produced
- `src/engine_v2/task44_ingest.py`, `task44_gate.py`, `task44_build.py`, `task44_tests.py`.
- `data/processed/engine_v2/task44_{passes,receptions,roles}.parquet`, `data/processed/tempo_task44_*`, `data/tempo_task44_*.json`, and `data/engine_v2_task44_{step2,step3,steps4_5}.json` (none committed).
- `data/raw_1516/events/` (1,551 parquet), `data/raw_1516/matches/`, `data/engine_v2_task44_step1.json` (not committed).
- Side effects: none else. No memory writes. JOURNAL.md and AGENTS.md untouched. Study and holdout data untouched.
- Commits: brief 5b80f43 and note f89863f (research lead); Step 1 5abf571; Step 2 f1bf0f3; final: recorded in a follow-up commit.

## 8. Confidence
Ingest is verified by row counts, the press-resistance flag version passed its gate (r = 0.84), and the confirmatory bars were fixed before any 2015/16 result.
The weakest links:
- The event-only g, which omits the 360 features the study's g used (pass net-xG OOF R^2 0.051 here, 0.045 on the study with different features and data).
- The 5-player praised-list result.
