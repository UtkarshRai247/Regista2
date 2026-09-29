# Task 45: Vetting press resistance: is it the team, or just safe passing?
Date: 2026-09-28
Status: COMPLETE (every section run; deviations in Section 4)

**Second use of the 2015/16 data. Steps 3-6 are exploratory.** Measurement only; PR2_flag is unchanged.

## Checklist
| Section | Status |
|---|---|
| Step 0 — brief | COMPLETE, with a deviation: committed by the research lead in 999cf5f **together with docs/BENCHMARK-v7.md**, not alone; amended before any run in ca9362f and 51c29d1 |
| Memory gate | COMPLETE (53% free, ~4.48 GB, 19:47 PDT) |
| Step 1 — A1 team-adjusted | COMPLETE |
| Step 2 — A2 team- and style-adjusted, correlations, descriptive | COMPLETE |
| Step 3 — league | COMPLETE |
| Step 4 — praised-list leave-one-out | COMPLETE |
| Step 5 — adjusted results link | COMPLETE |
| Step 6 — every role (exploratory) | COMPLETE |

## 1. Headline
**A1 (team style removed) fails both conditions.**
- Deep-midfield stability falls from 0.666 (unadjusted) to **0.487** (bar 0.60; n = 185).
- The praised-list T falls from +1.44 (p = 0.0007) to **+0.27 (p = 0.54, Holm across A1/A2 0.54)**.
- A2 also fails (stability 0.518; T = −0.51, p = 0.25).

Under the fixed rule, no statement is made beyond Task 44's unadjusted result, and that result is described as **possibly team style**.
Team fixed effects explain only 0.85% of unit-level variance, but they remove most of the player-level stability and all of the praised-list separation.

## 2. What I did
- Step 0: the brief was committed by the research lead (999cf5f, with BENCHMARK-v7) and amended before any run (ca9362f, 51c29d1).
- `.venv/bin/python -W ignore src/engine_v2/task45_vetting.py` does all steps. It reads Task 44's 2015/16 artifacts (read-only) and the 2015/16 events for pass geometry.
- **A1:** each pressured reception's PR2_flag_keep minus its team's mean (OLS on team × season fixed effects, equal unit weights; one season). Player score = mean.
- **A2:** the A1 player score residualised by WLS (weight = pressured receptions) on three measures from his UNPRESSURED eligible passes:
  - completion rate;
  - share of passes < 15 units;
  - share with end x − start x < 0.
  - The fit uses 1414 players with ≥50 pressured receptions and ≥100 unpressured eligible passes.
  - Unit A2 = unit A1 − the player's fitted value, so player means equal the WLS residuals (asserted).
  - WLS: R^2 = 0.493; completion +0.557 (p = 5e-123), short share -0.168 (p = 2e-11), backward/sideways share -0.131 (p = 3e-07).
- **Methods reused:** Task 44's `r1` (Task 38's method, 100 half-splits of matches, players ≥10 matches), `task42_step2.dm_table` (Task 29's method), Task 41's `perm_test` (≥50 pressured receptions, 2015/16 roles, the same five listed players as Task 44), and Task 44's P-test (event-only g, `fe_fit`, retention control).

## 3. Numbers

### Steps 1-2 — within the 185 deep midfielders

| Measure | R1 median [p5, p95] | bar 0.60 | Q | above / below mean | praised T | p (two-sided) | Holm (A1, A2) |
|---|---|---|---|---|---|---|---|
| unadjusted | 0.666 [0.610, 0.714] | PASS | 703.6 (184 df) | 27 / 35 | +1.444 | 0.0006999 | — |
| A1 | 0.487 [0.404, 0.567] | FAIL | 433.5 (184 df) | 9 / 13 | +0.274 | 0.5401 | 0.5401 |
| A2 | 0.518 [0.436, 0.590] | FAIL | 460.2 (184 df) | 15 / 14 | -0.514 | 0.2497 | 0.4994 |

- Team fixed-effect share of unit-level PR2_flag_keep variance: **0.0085**.
- Spearman correlation with unadjusted (185 deep midfielders): A1 **0.773**; A2 **0.490**.
- Praised-list z-scores:
  - unadjusted: Kevin De Bruyne +0.24, Marco Verratti +2.18, Sergio Busquets i Burgos +1.75, Luka Modrić +1.38, Toni Kroos +1.67;
  - A1: Kevin De Bruyne -0.49, Marco Verratti +0.93, Sergio Busquets i Burgos -0.53, Luka Modrić +0.80, Toni Kroos +0.65;
  - A2: Kevin De Bruyne -0.80, Marco Verratti +0.10, Sergio Busquets i Burgos -1.20, Luka Modrić -0.07, Toni Kroos -0.60.
- Players entirely above / below the mean:
  - A1 above: Francesco Lodi, João Filipe Iria Santos Moutinho, Bruno Soriano Llido, Andrew Surman, Claudio Marchisio, Jérémy Clément, Ben Watson, Kevin Kampl, Roberto Trashorras Gayoso.
  - A1 below: Walid Mesloub, Younousse Sankharé, Jessy Pi, José Vicente Gómez Umpiérrez, Vincent Pajot, Jan Kirchhoff, Benjamin André, William Jean Rémy, Benjamin Stambouli, Fernando Luiz Rosa, Blerim Džemaili, Andrea Bertolacci, Aaron Ramsey.
  - A2 above: Francesco Lodi, Ben Watson, João Filipe Iria Santos Moutinho, Kevin Kampl, Bruno Soriano Llido, Nicolas Seube, Jérémy Clément, Celso Borges Mora, Mehdi Mostefa Sbaa, Alexander Banor Tettey, Abdoulaye Doucouré, Giuseppe Vives, José Luis García del Pozo, Christoph Kramer, Andrew Surman.
  - A2 below: Tomás Eduardo Rincón Hernández, Maxime Gonalons, Jessy Pi, Benjamin André, Rio Antonio Zoba Mavuba, Sergio Busquets i Burgos, Vincent Pajot, José Vicente Gómez Umpiérrez, William Jean Rémy, Blerim Džemaili, Andrea Bertolacci, Benjamin Stambouli, Aaron Ramsey, Fernando Luiz Rosa.
  - Unadjusted lists: as in Task 44 (27 above, 35 below).

Raw correlations (deep midfielders, n = 185) of unadjusted player PR2_flag_keep with unpressured passing style:

| Style variable | r |
|---|---|
| completion rate | +0.573 |
| share < 15 units | +0.020 |
| share backward/sideways | +0.137 |

Descriptive: spells ending in a completed pass under pressure. The ending pass's dx = end x − start x: forward ≥ 5, backward ≤ −5, else sideways. Top and bottom 20 use the unadjusted deep-midfield ranking.

| Group | n spells | forward | sideways | backward | median length |
|---|---|---|---|---|---|
| top20 | 4646 | 0.326 | 0.300 | 0.374 | 15.2 |
| bottom20 | 2010 | 0.405 | 0.277 | 0.318 | 15.8 |
| Toni Kroos | 279 | 0.362 | 0.351 | 0.287 | 16.2 |
| Luka Modrić | 290 | 0.397 | 0.297 | 0.307 | 14.3 |
| Marco Verratti | 278 | 0.381 | 0.317 | 0.302 | 14.6 |
| Sergio Busquets i Burgos | 341 | 0.343 | 0.302 | 0.355 | 15.6 |
| Kevin De Bruyne | 157 | 0.376 | 0.325 | 0.299 | 14.2 |
| Granit Xhaka | 34 | 0.500 | 0.176 | 0.324 | 16.9 |

### Step 3 — by league (deep-midfield R1; praised list within the league's players; no claim)

| League | unadjusted | A1 | A2 |
|---|---|---|---|
| Premier League | 0.581 (n=40); T 0.062, p 0.928, present 1 | 0.453 (n=40); T -0.515, p 0.633, present 1 | 0.486 (n=40); T -0.706, p 0.548, present 1 |
| Ligue 1 | 0.670 (n=48); T 2.021, p 0.030, present 1 | 0.593 (n=48); T 0.956, p 0.303, present 1 | 0.587 (n=48); T 0.127, p 0.866, present 1 |
| Bundesliga | 0.558 (n=3); T —, p —, present 0 | 0.558 (n=3); T —, p —, present 0 | -0.367 (n=3); T —, p —, present 0 |
| La Liga | 0.567 (n=51); T 1.915, p 0.001, present 3 | 0.348 (n=51); T 0.472, p 0.417, present 3 | 0.429 (n=51); T -0.492, p 0.396, present 3 |
| Serie A | 0.711 (n=43); T —, p —, present 0 | 0.521 (n=43); T —, p —, present 0 | 0.519 (n=43); T —, p —, present 0 |

A1 with league fixed effects added is identical to A1: league is nested in team, and A1's league means are 0 (asserted).

### Step 4 — praised list, leave one out (T, p after dropping each present player)

| Dropped | unadjusted | A1 | A2 |
|---|---|---|---|
| Kevin De Bruyne | +1.745, p=0.0003 | +0.465, p=0.3547 | -0.443, p=0.3702 |
| Marco Verratti | +1.261, p=0.009299 | +0.109, p=0.8253 | -0.668, p=0.1825 |
| Sergio Busquets i Burgos | +1.368, p=0.006799 | +0.476, p=0.3411 | -0.342, p=0.4994 |
| Luka Modrić | +1.459, p=0.0016 | +0.141, p=0.778 | -0.626, p=0.2129 |
| Toni Kroos | +1.387, p=0.005999 | +0.180, p=0.7192 | -0.492, p=0.3254 |

### Step 5 — adjusted results link (Task 44's P-test; S = other-match A1 / A2, ≥50 elsewhere; retention control on the same rows; report only)

| Measure | group | Y | n | players | coef per 100 per SD | 95% CI | p | MDE | control |
|---|---|---|---|---|---|---|---|---|---|
| A1 | DM | Y_F3 | 34,822 | 185 | +0.6417 | [0.0277, 1.2557] | 0.0405 | 0.8772 | +3.894, p=1.5e-21 |
| A1 | DM | net xG | 41,414 | 185 | -0.0213 | [-0.0536, 0.0111] | 0.198 | 0.0462 | +3.692, p=5.1e-23 |
| A1 | all | Y_F3 | 203,001 | 1497 | +1.6039 | [1.3150, 1.8927] | 1.38e-27 | 0.4126 | +8.331, p=2.7e-210 |
| A1 | all | net xG | 300,404 | 1498 | -0.0400 | [-0.0598, -0.0203] | 6.92e-05 | 0.0282 | +8.396, p=2.9e-305 |
| A2 | DM | Y_F3 | 34,822 | 185 | +0.4134 | [-0.2390, 1.0658] | 0.214 | 0.9320 | +3.894, p=1.5e-21 |
| A2 | DM | net xG | 41,414 | 185 | -0.0230 | [-0.0576, 0.0117] | 0.194 | 0.0495 | +3.692, p=5.1e-23 |
| A2 | all | Y_F3 | 198,605 | 1443 | +1.0692 | [0.8181, 1.3204] | 7.22e-17 | 0.3588 | +8.390, p=4.8e-203 |
| A2 | all | net xG | 296,008 | 1444 | -0.0254 | [-0.0415, -0.0092] | 0.00208 | 0.0231 | +8.453, p=1.8e-296 |

Task 44 (unadjusted) for comparison: DM Y_F3 +0.775 (p = 0.054); all Y_F3 +1.835 (p = 2e-27); all net xG −0.046 (p = 7e-5).

### Step 6 — every Task 32 role (second use of 2015/16; exploratory; report only)

| Role | measure | R1 median (players ≥10 matches) | P-test Y_F3 per 100 per SD [95% CI], p; control p | P-test net xG [95% CI], p; control p | Q (df), p |
|---|---|---|---|---|---|
| CB | unadjusted | 0.543 (261) | -1.010 [-2.019, 0.000], p=0.05; ctrl p=5.5e-11 | +0.0041 [-0.0576, 0.0657], p=0.898; ctrl p=5.4e-12 | 904.7 (327), p=0 |
| CB | A1 | 0.402 (261) | -0.815 [-1.629, -0.002], p=0.0495; ctrl p=5.5e-11 | +0.0033 [-0.0464, 0.0530], p=0.896; ctrl p=5.4e-12 | 640.3 (327), p=0 |
| FB | unadjusted | 0.644 (284) | +1.163 [0.376, 1.950], p=0.00378; ctrl p=4.6e-21 | +0.0067 [-0.0427, 0.0562], p=0.79; ctrl p=1.9e-28 | 1248.9 (347), p=0 |
| FB | A1 | 0.531 (284) | +1.004 [0.363, 1.646], p=0.00213; ctrl p=4.6e-21 | +0.0058 [-0.0344, 0.0460], p=0.777; ctrl p=1.9e-28 | 854.1 (347), p=0 |
| DM | unadjusted | 0.601 (213) | +0.727 [-0.019, 1.474], p=0.0563; ctrl p=8.2e-26 | -0.0247 [-0.0622, 0.0128], p=0.197; ctrl p=5.2e-27 | 796.1 (243), p=0 |
| DM | A1 | 0.432 (213) | +0.598 [0.012, 1.184], p=0.0455; ctrl p=8.2e-26 | -0.0196 [-0.0494, 0.0102], p=0.197; ctrl p=5.2e-27 | 513.1 (243), p=0 |
| CM | unadjusted | 0.729 (111) | +2.079 [1.024, 3.135], p=0.000113; ctrl p=3.6e-17 | -0.0007 [-0.0696, 0.0682], p=0.984; ctrl p=4.7e-19 | 619.5 (123), p=0 |
| CM | A1 | 0.626 (111) | +1.819 [0.926, 2.712], p=6.57e-05; ctrl p=3.6e-17 | -0.0003 [-0.0592, 0.0586], p=0.993; ctrl p=4.7e-19 | 458.3 (123), p=0 |
| AM/W | unadjusted | 0.796 (361) | +2.407 [1.920, 2.895], p=3.77e-22; ctrl p=5.9e-133 | -0.0698 [-0.1044, -0.0352], p=7.81e-05; ctrl p=9.3e-217 | 2595.0 (384), p=0 |
| AM/W | A1 | 0.737 (361) | +2.056 [1.635, 2.478], p=1.18e-21; ctrl p=5.9e-133 | -0.0599 [-0.0894, -0.0304], p=7.01e-05; ctrl p=9.3e-217 | 1878.6 (384), p=0 |
| FW | unadjusted | 0.626 (198) | +1.885 [0.827, 2.942], p=0.000477; ctrl p=1.2e-07 | +0.0510 [-0.0220, 0.1240], p=0.171; ctrl p=5.3e-19 | 712.3 (200), p=0 |
| FW | A1 | 0.579 (198) | +1.799 [0.809, 2.789], p=0.000368; ctrl p=1.2e-07 | +0.0396 [-0.0282, 0.1075], p=0.252; ctrl p=5.3e-19 | 608.0 (200), p=0 |

| Role | players in role | PR2_flag_fwd R1 (n) | completed-pass-under-pressure spells | forward | sideways | backward | median length |
|---|---|---|---|---|---|---|---|
| CB | 328 | 0.389 (261) | 14,698 | 0.529 | 0.199 | 0.271 | 20.7 |
| FB | 348 | 0.355 (284) | 24,563 | 0.363 | 0.229 | 0.408 | 14.9 |
| DM | 244 | 0.526 (213) | 30,205 | 0.368 | 0.281 | 0.351 | 15.8 |
| CM | 124 | 0.480 (111) | 17,756 | 0.343 | 0.289 | 0.368 | 14.4 |
| AM/W | 385 | 0.535 (361) | 48,042 | 0.293 | 0.297 | 0.410 | 13.3 |
| FW | 201 | 0.408 (198) | 22,448 | 0.258 | 0.346 | 0.396 | 12.2 |

Top 10 by shrunken score within each role (Task 29's method; output only):
- **CB.** Unadjusted: Javier Alejandro Mascherano (+0.243), Thiago Emiliano da Silva (+0.215), Gerard Piqué Bernabéu (+0.197), Martín Gastón Demichelis (+0.195), Marcos Aoás Corrêa (+0.189), Davide Astori (+0.186), Konstantinos Manolas (+0.178), José Martín Cáceres Silva (+0.175), Francesco Acerbi (+0.168), Jérémy Mathieu (+0.165).
  A1: Luis Hernández Rodríguez (+0.167), Damien Da Silva (+0.154), Francesco Acerbi (+0.149), Adil Rami (+0.146), Martín Gastón Demichelis (+0.138), Jonathan Grant Evans (+0.135), Emiliano Moretti (+0.135), Alex Rodrigo Dias da Costa (+0.130), Bakary Adama Soumaoro (+0.126), Konstantinos Manolas (+0.124).
- **FB.** Unadjusted: Daniel Alves da Silva (+0.194), Christophe Jallet (+0.173), Maxwell Scherrer Cabelino Andrade (+0.172), Gregory van der Wiel (+0.159), Adriano Correia Claro (+0.156), Jordi Alba Ramos (+0.146), Javier Garrido Behovide (+0.126), Mattia Cassani (+0.120), Vincent Le Goff (+0.116), Àngel Rangel Zaragoza (+0.115).
  A1: Christophe Jallet (+0.111), Vincent Le Goff (+0.101), Massimo Gobbi (+0.101), Chaker Alhadhur (+0.099), Javier Garrido Behovide (+0.093), Eneko Bóveda Altube (+0.092), Mattia Cassani (+0.090), Yoann Andreu (+0.087), Danny Simpson (+0.086), Patrick van Aanholt (+0.081).
- **DM.** Unadjusted: Thiago Motta (+0.208), Jorge Luiz Frello Filho (+0.207), Claudio Marchisio (+0.192), Sergio Busquets i Burgos (+0.174), Toni Kroos (+0.167), Andrew Surman (+0.165), Gary Alexis Medel Soto (+0.161), Nampalys Mendy (+0.155), Matías Vecino Falero (+0.153), João Filipe Iria Santos Moutinho (+0.152).
  A1: Francesco Lodi (+0.152), João Filipe Iria Santos Moutinho (+0.149), Bruno Soriano Llido (+0.147), Claudio Marchisio (+0.142), Andrew Surman (+0.142), Jérémy Clément (+0.139), Ben Watson (+0.133), Nicolas Seube (+0.131), Kevin Kampl (+0.131), Augusto Matías Fernández (+0.128).
- **CM.** Unadjusted: Marco Verratti (+0.187), Arda Turan (+0.183), Andrés Iniesta Luján (+0.148), David López Silva (+0.148), Luka Modrić (+0.139), Ivan Rakitić (+0.136), Rémi Walter (+0.128), Marek Hamšík (+0.126), Mahamane El-Hadj Traoré (+0.123), Mounir Obbadi (+0.121).
  A1: Mounir Obbadi (+0.134), N''Golo Kanté (+0.123), Mark Noble (+0.117), Ashley Westwood (+0.107), Jonjo Shelvey (+0.104), Matteo Fedele (+0.096), Alessandro Frara (+0.095), Danny Drinkwater (+0.093), Lee Cattermole (+0.091), Marvin Martin (+0.087).
- **AM/W.** Unadjusted: Juan Manuel Mata García (+0.141), Samir Nasri (+0.130), Tom Cleverley (+0.115), Eden Hazard (+0.112), Steven Davis (+0.111), Adem Ljajić (+0.105), Joan Verdú Fernández (+0.105), Lorenzo Insigne (+0.101), Mathieu Valbuena (+0.101), Moisés Gómez Bordonado (+0.098).
  A1: Joan Verdú Fernández (+0.112), Moisés Gómez Bordonado (+0.111), Michael Krohn-Dehli (+0.108), Juan Manuel Mata García (+0.099), Steven Davis (+0.095), Thibault Giresse (+0.089), Nicolas Maurice-Belay (+0.089), Francisco Portillo Soler (+0.087), Frédéric Bulot (+0.083), Samir Nasri (+0.080).
- **FW.** Unadjusted: Zlatan Ibrahimović (+0.047), Karim Benzema (+0.011), Wilfried Guemiand Bony (+0.003), Manuel Pucciarelli (+0.002), Benik Afobe (+0.002), Bertrand Isidore Traoré (-0.001), Cyril Théréau (-0.002), Gregoire Defrel (-0.003), Luiz Adriano de Souza da Silva (-0.006), Lewis Grabban (-0.006).
  A1: Cyril Théréau (+0.021), Iago Aspas Juncal (+0.008), Víctor Casadesús Castaño (+0.004), Rickie Lambert (-0.000), Marco Borriello (-0.003), Jacques Zoua Daogari (-0.005), Wissam Ben Yedder (-0.005), Gregoire Defrel (-0.008), José Leonardo Ulloa (-0.009), Benik Afobe (-0.011).

### Fixed claim rule, applied mechanically
- **A1** (the essential test) fails both conditions: deep-midfield stability 0.487 < 0.60, and praised-list p = 0.54 (Holm 0.54). No statement is made beyond Task 44's unadjusted result, which is described as **possibly team style**.
- **A2** also fails (0.518; T negative, p = 0.25).

## 4. Deviations from the brief
- **Step 0:** the brief was not committed alone (999cf5f also contains docs/BENCHMARK-v7.md).
- **A2 fit population** (the brief does not state one): all players with ≥50 pressured receptions and ≥100 unpressured eligible passes (1414 players). The same coefficients are applied to every unit.
- **Descriptive dx:** the ending pass's end x − its start x, with ±5 units separating forward / sideways / backward. The brief gives ≥5 for forward only.
- **The spell-ending pass** is the receiver's first Pass after the receipt in the same possession. That pass ends the spell whenever keep_spell = 1, by Task 43's definition.
- **Step 3 league:** a player's league is his modal league (Task 44 roles). Stability is within the league's deep midfielders. The praised list is within the league's qualifying players.
- **Praised-list p values** come from a fresh generator (seed 20260928) per test, so the unadjusted p here (0.0007) differs from Task 44's 0.0011 for the same T (+1.444).

## 5. Problems and surprises
- **Team style is only 0.85% of unit variance, but it carries most of the player-level signal.** Removing it drops deep-midfield stability by 0.18 and the praised-list T from +1.44 to +0.27. Taken at face value, player differences in unadjusted PR2_flag_keep largely track which team the player is on.
- **Leave-one-out:** the unadjusted praised-list result survives dropping any single player (p ≤ 0.009). A1 and A2 do not come close to 0.05 for any subset.
- **Completion rate on unpressured passes correlates +0.57 with unadjusted PR2_flag_keep among deep midfielders.** In the WLS it is the strongest predictor of the A1 score (R^2 0.49 across players).
- **The top-20 deep midfielders' completed pressured spells go backward more often** (0.374) than the bottom 20's (0.318), and forward less often (0.326 against 0.405).
- **In the adjusted results link, A1 → Y_F3 within deep midfielders is +0.64 (p = 0.041).** All-player A1 and A2 → Y_F3 are strongly positive, while → net xG is negative, as in Task 44 unadjusted. None of these is claimed.
- **Across roles (exploratory):** unadjusted R1 ≥ 0.60 for FB, DM (role), CM, AM/W and FW; after A1, only CM (0.626) and AM/W (0.737) stay ≥ 0.60. Y_F3 P-tests are positive (p < 0.05) for FB, CM, AM/W and FW under both versions; negative for CB (p ≈ 0.05).
- **The praised-list statistic rests on 5 players**, and each league contains 0-3 of them.

## 6. Questions for the research lead
- Q1: Is the A2 fit population (all players with ≥50 pressured receptions and ≥100 unpressured passes) the intended one, rather than deep midfielders only?

## 7. Files produced
- `src/engine_v2/task45_vetting.py`.
- `data/engine_v2_task45.json` (not committed).
- Side effects: none else. No memory writes. JOURNAL.md and AGENTS.md untouched. Holdout, study data and Task 44 artifacts untouched.
- Commits: brief 999cf5f (+ ca9362f, 51c29d1, research lead); this page b16283b.

## 8. Confidence
- A1 is an exact team demeaning (asserted), and A2's player means equal its WLS residuals (asserted).
- The weakest links:
  - The praised-list inference, which rests on 5 players.
  - A2's dependence on the three chosen style variables and the fit population.
