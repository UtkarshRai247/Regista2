# Task 38: "Always available" (PFF WC2022)
Date: 2026-09-28
Status: COMPLETE (every section run; deviations in Section 4)

## Checklist
| Section | Status |
|---|---|
| Step 0 — brief committed | COMPLETE, with a deviation: committed by the research lead in 1601bcd **together with the Task 37 brief**, not alone |
| Memory gate | COMPLETE (55% free, ~4.61 GB, 2026-09-28 14:03 PDT) |
| Step 1 — measure, baseline, AV and AV_vis | COMPLETE |
| Step 2 — DM group | COMPLETE (59) |
| Step 3 R1 — stability | COMPLETE |
| Step 3 R2 — results (pass-level, out-of-match) | COMPLETE |
| Step 3 R3 — distinctness | COMPLETE |
| Step 4 — DM tables (AV and AV_vis) | COMPLETE |

## 1. Headline
R2 FAILS: the out-of-match availability of the receiver has a NEGATIVE coefficient on net xG after the reception (−0.069 xG per 100 receptions per SD, 95% CI [−0.115, −0.024], p = 0.003, MDE 0.065; 43,815 receptions, 381 receivers). AV_vis gives the same (−0.069, p = 0.003).
R1 PASSES within deep midfielders, but on only 28 players with ≥4 matches: median split-half reliability 0.74 [p5 0.65, p95 0.81] (AV_vis 0.71).
Under the brief's fixed rules: "a stable trait; no evidence it shows up in results in this sample (MDE 0.065 xG per 100 receptions per SD)". The observed estimate is negative and significant.

## 2. What I did
- Step 0: the brief was already committed in 1601bcd (with `task-37-holdout-ptest.md`).
- Told decisions appended to `docs/DECISIONS.md` as D-016:
  - under pressure = PFF `pressureType != 'N'`;
  - the Bono → Yassine Bounou override;
  - the top-level Event Data (v2.5).
- Step 1: `.venv/bin/python src/pff/availability.py`
  - Reads each match's PFF events JSON, one match in memory at a time.
  - Moments: PA/CR events with nonEvent false, periods 1-4, every outfield teammate of the passer in the embedded snapshot.
  - Computes d_ball, space and lane in PFF metres; the lane is point-to-segment, checked against `engine_v2/geometry.point_segment_perp_distance`.
  - Ball x/y goes into the passing team's attacking frame via Task 36's `frames.to_sb` / `attack_sign`.
  - Baseline: cross-fitted XGBoost classifier (5 match folds, seed 20260928), AV = AVAILABLE − p_oof.
  - AV_vis: same baseline refit on the visible subset.
  - Also builds R2's reception units.
- Steps 2-4: `.venv/bin/python src/pff/availability_tests.py`
  - Reuses `task35_ptest.fe_fit`, Task 35's regression hyperparameters, `task28_step1_2.estimate_sigma2w_rho`, and `task29_step1_2.dersimonian_laird` / `shrink`.
- Reproduce: the two commands above, after Task 36's pipeline.

## 3. Numbers

### Step 1 — the measure
- Matches: 64. Pass/cross events: 68,567, of which 4,163 (6.1%) had no ball position in the snapshot and were skipped.
- **Moments: 584,874** (639 players). Every moment's player has a StatsBomb id.
- **Base rate AVAILABLE: 0.334.** Component rates: d_ball 5-40 m 0.847; space ≥ 3 m 0.804; lane ≥ 2 m 0.415.
- **Baseline out-of-fold AUC: 0.743.** Mean AV: +0.0008.
- AV_vis subset (teammate and his nearest opponent both VISIBLE): 341,515 moments; base rate 0.360; AUC 0.748; mean AV_vis +0.0005.
- Pass target (`targetPlayerId`):
  - P(target | AVAILABLE) = **0.181** (n = 195,257).
  - P(target | not available) = **0.068** (n = 389,617).
  - 57.1% of the 61,904 target moments were AVAILABLE.

### Step 2 — deep midfielders
Rule: ≥50% of WC2022 StatsBomb eligible passes (cross-fitted v5 corpus) at C/L/R Defensive Midfield, AND ≥3 PFF matches, AND ≥300 moments. 100 players meet the DM-share rule alone; **59** meet all three.

| Player | Team | DM share | WC passes | PFF matches | moments |
|---|---|---|---|---|---|
| Aaron Mooy | Australia | 1.00 | 188 | 4 | 1362 |
| Adrien Rabiot | France | 0.98 | 253 | 6 | 2654 |
| Ahmad Nourollahi | Iran | 0.81 | 52 | 3 | 690 |
| Aissa Laidouni | Tunisia | 0.92 | 107 | 3 | 930 |
| Ali Karimi | Iran | 0.55 | 40 | 3 | 422 |
| Ao Tanaka | Japan | 1.00 | 63 | 3 | 432 |
| Atiba Hutchinson | Canada | 1.00 | 98 | 3 | 716 |
| Aurélien Tchouaméni | France | 0.99 | 412 | 7 | 2904 |
| Axel Witsel | Belgium | 0.95 | 146 | 3 | 1600 |
| Casemiro | Brazil | 1.00 | 235 | 4 | 2173 |
| Celso Borges | Costa Rica | 0.91 | 100 | 3 | 814 |
| Declan Rice | England | 0.99 | 292 | 5 | 2597 |
| Ellyes Skhiri | Tunisia | 1.00 | 113 | 3 | 1109 |
| Enzo Fernandez | Argentina | 0.84 | 406 | 7 | 2898 |
| Ethan Ampadu | Wales | 0.93 | 125 | 3 | 1034 |
| Federico Valverde | Uruguay | 0.66 | 164 | 3 | 1228 |
| Fred | Brazil | 0.88 | 69 | 4 | 825 |
| Frenkie de Jong | Netherlands | 1.00 | 335 | 5 | 2379 |
| Granit Xhaka | Switzerland | 1.00 | 201 | 4 | 1675 |
| Grzegorz Krychowiak | Poland | 1.00 | 114 | 4 | 1167 |
| Hidemasa Morita | Japan | 1.00 | 152 | 3 | 1148 |
| Ilkay Gündogan | Germany | 0.89 | 150 | 3 | 1195 |
| In-beom Hwang | South Korea | 0.78 | 216 | 4 | 1515 |
| Ismael Kone | Canada | 0.77 | 84 | 3 | 566 |
| Jackson Irvine | Australia | 0.53 | 112 | 4 | 1379 |
| Jonathan Osorio | Canada | 0.84 | 51 | 3 | 643 |
| Joshua Kimmich | Germany | 0.80 | 215 | 3 | 1640 |
| Jude Bellingham | England | 0.52 | 250 | 5 | 2605 |
| Jun-ho Son | South Korea | 0.98 | 54 | 3 | 377 |
| Karim Boudiaf | Qatar | 0.68 | 99 | 3 | 813 |
| Krystian Bielik | Poland | 1.00 | 87 | 4 | 758 |
| Leandro Paredes | Argentina | 1.00 | 202 | 5 | 1185 |
| Leon Goretzka | Germany | 1.00 | 54 | 3 | 880 |
| Lucas Paquetá | Brazil | 0.80 | 174 | 4 | 1784 |
| Marcelo Brozovic | Croatia | 0.99 | 473 | 6 | 2962 |
| Marten De Roon | Netherlands | 1.00 | 113 | 5 | 1125 |
| Mohamed Kanno | Saudi Arabia | 0.78 | 125 | 3 | 955 |
| Moises Caicedo | Ecuador | 0.87 | 134 | 3 | 1170 |
| Nampalys Mendy | Senegal | 0.96 | 140 | 4 | 1094 |
| Nemanja Maksimovic | Serbia | 1.00 | 50 | 3 | 692 |
| Pape Gueye | Senegal | 0.57 | 47 | 3 | 526 |
| Pathe Ciss | Senegal | 1.00 | 54 | 3 | 455 |
| Pierre-Emile Höjbjerg | Denmark | 0.77 | 198 | 3 | 1629 |
| Remo Freuler | Switzerland | 0.81 | 124 | 4 | 1543 |
| Rodrigo Bentancur | Uruguay | 1.00 | 137 | 3 | 947 |
| Rúben Neves | Portugal | 1.00 | 222 | 5 | 1669 |
| Saeid Ezatolahi | Iran | 1.00 | 78 | 3 | 814 |
| Salis Abdul Samed | Ghana | 1.00 | 121 | 3 | 883 |
| Saša Lukić | Serbia | 0.93 | 150 | 3 | 1113 |
| Sergio Busquets | Spain | 1.00 | 259 | 4 | 3186 |
| Sofyan Amrabat | Morocco | 0.95 | 276 | 7 | 2371 |
| Teun Koopmeiners | Netherlands | 1.00 | 101 | 5 | 1086 |
| Thomas Partey | Ghana | 0.73 | 165 | 3 | 1003 |
| Tyler Adams | United States | 1.00 | 235 | 4 | 1858 |
| Wataru Endo | Japan | 1.00 | 171 | 4 | 1247 |
| Woo-young Jung | South Korea | 0.97 | 181 | 4 | 1321 |
| Yeltsin Tejeda | Costa Rica | 0.89 | 92 | 3 | 860 |
| Youri Tielemans | Belgium | 1.00 | 51 | 3 | 547 |
| Youssouf Fofana | France | 0.59 | 97 | 6 | 1015 |

### Step 3 R1 — stability (100 random half-splits of each player's matches; Spearman-Brown; players with ≥4 matches)

| Group | measure | n players | median | p5 | p95 |
|---|---|---|---|---|---|
| **DM** | **AV** | 28 | **0.740** | 0.647 | 0.814 |
| DM | AV_vis | 28 | 0.712 | 0.559 | 0.819 |
| all outfield | AV | 183 | 0.620 | 0.561 | 0.672 |
| all outfield | AV_vis | 181 | 0.608 | 0.546 | 0.668 |

**R1: PASS** (AV 0.740 ≥ 0.60; AV_vis 0.712 ≥ 0.60).

### Step 3 R2 — results (pass-level, out-of-match; team-match FE, role FE = PFF positionGroupType, SE clustered by player)
- Units: 52,419 completed PA/CR receptions. In 572 of them the receiver had no PFF event within the next 3 entries, so the reception location and pressure are missing (NaN in g).
- Y: net StatsBomb xG over the next 10 PFF possession events; mean 0.0072, SD 0.0528.
- PFF shots: 1,559, of which 185 have no Task 36 pair and were excluded. That affected Y in 415 receptions.
- g out-of-fold R^2: 0.019.
- S requires ≥2 other matches.

| Measure | Sample | n receptions | n players | team-matches | coef per SD | per 100 | 95% CI (per 100) | p | MDE 80% (per 100) |
|---|---|---|---|---|---|---|---|---|---|
| **AV** | **all outfield (PRIMARY)** | 43,815 | 381 | 128 | −0.000692 | **−0.0692** | [−0.1146, −0.0238] | **0.0028** | 0.0648 |
| AV | DM (report) | 8,053 | 59 | 121 | −0.001749 | −0.1749 | [−0.3509, 0.0012] | 0.0515 | 0.2515 |
| AV_vis | all outfield | 43,706 | 378 | 128 | −0.000690 | −0.0690 | [−0.1152, −0.0228] | 0.0034 | 0.0660 |
| AV_vis | DM (report) | 8,008 | 58 | 121 | −0.001717 | −0.1717 | [−0.3393, −0.0041] | 0.0446 | 0.2394 |

**R2: FAIL** (the coefficient is not > 0).

### Step 3 R3 — distinctness (DM, n = 59, Pearson, Fisher 95% CI)

| Player AV vs | n | r | 95% CI |
|---|---|---|---|
| v5 Decision (cross-fitted, WC2022 passes) | 59 | −0.125 | [−0.369, 0.136] |
| Task 34 RQ_rel (WC2022 receptions) | 59 | +0.361 | [0.115, 0.565] |
| PFF receptions per match | 59 | +0.235 | [−0.022, 0.463] |

### Step 4 — DM tables (Task 29's method on per-moment values; 90% intervals)
- **AV:** sigma2_w = 0.2151, rho = 0.00564; DerSimonian-Laird mu_w = +0.0218, tau^2 = 0.00187; **Q = 277.94 on 58 df, p < 1e-15**.
  - Above the mean (12): Woo-young Jung, Jun-ho Son, Ismael Kone, Sofyan Amrabat, Enzo Fernandez, Aurélien Tchouaméni, Rúben Neves, Rodrigo Bentancur, Leandro Paredes, In-beom Hwang, Salis Abdul Samed, Aaron Mooy.
  - Below the mean (14): Frenkie de Jong, Adrien Rabiot, Teun Koopmeiners, Nemanja Maksimovic, Ali Karimi, Pape Gueye, Fred, Sergio Busquets, Jonathan Osorio, Lucas Paquetá, Marten De Roon, Remo Freuler, Jude Bellingham, Leon Goretzka.
- **AV_vis:** sigma2_w = 0.2137, rho = 0.00604; mu_w = +0.0174, tau^2 = 0.00187; **Q = 243.50 on 58 df, p < 1e-15**.
  - Above the mean (10): Ismael Kone, Woo-young Jung, Leandro Paredes, Rúben Neves, Aaron Mooy, Enzo Fernandez, In-beom Hwang, Rodrigo Bentancur, Sofyan Amrabat, Aurélien Tchouaméni.
  - Below the mean (11): Fred, Frenkie de Jong, Pape Gueye, Lucas Paquetá, Jonathan Osorio, Sergio Busquets, Nemanja Maksimovic, Marten De Roon, Jude Bellingham, Remo Freuler, Leon Goretzka.

AV table (all 59 DMs):

| # | Player | Team | matches | moments | raw AV | shrunken | 90% low | 90% high |
|---|---|---|---|---|---|---|---|---|
| 1 | Woo-young Jung | South Korea | 4 | 1321 | +0.0986 | +0.0833 | +0.0515 | +0.1150 |
| 2 | Jun-ho Son | South Korea | 3 | 377 | +0.1010 | +0.0739 | +0.0323 | +0.1155 |
| 3 | Ismael Kone | Canada | 3 | 566 | +0.0955 | +0.0738 | +0.0351 | +0.1124 |
| 4 | Sofyan Amrabat | Morocco | 7 | 2371 | +0.0760 | +0.0693 | +0.0443 | +0.0943 |
| 5 | Enzo Fernandez | Argentina | 7 | 2898 | +0.0723 | +0.0664 | +0.0421 | +0.0908 |
| 6 | Aurélien Tchouaméni | France | 7 | 2904 | +0.0700 | +0.0644 | +0.0401 | +0.0887 |
| 7 | Rúben Neves | Portugal | 5 | 1669 | +0.0727 | +0.0643 | +0.0354 | +0.0932 |
| 8 | Rodrigo Bentancur | Uruguay | 3 | 947 | +0.0779 | +0.0638 | +0.0281 | +0.0995 |
| 9 | Leandro Paredes | Argentina | 5 | 1185 | +0.0705 | +0.0616 | +0.0310 | +0.0921 |
| 10 | In-beom Hwang | South Korea | 4 | 1515 | +0.0705 | +0.0612 | +0.0300 | +0.0924 |
| 11 | Salis Abdul Samed | Ghana | 3 | 883 | +0.0737 | +0.0604 | +0.0243 | +0.0964 |
| 12 | Aaron Mooy | Australia | 4 | 1362 | +0.0696 | +0.0602 | +0.0285 | +0.0918 |
| 13 | Atiba Hutchinson | Canada | 3 | 716 | +0.0681 | +0.0554 | +0.0182 | +0.0926 |
| 14 | Youri Tielemans | Belgium | 3 | 547 | +0.0638 | +0.0513 | +0.0124 | +0.0901 |
| 15 | Thomas Partey | Ghana | 3 | 1003 | +0.0603 | +0.0508 | +0.0153 | +0.0862 |
| 16 | Mohamed Kanno | Saudi Arabia | 3 | 955 | +0.0600 | +0.0504 | +0.0148 | +0.0861 |
| 17 | Pathe Ciss | Senegal | 3 | 455 | +0.0621 | +0.0493 | +0.0091 | +0.0894 |
| 18 | Axel Witsel | Belgium | 3 | 1600 | +0.0533 | +0.0463 | +0.0127 | +0.0799 |
| 19 | Nampalys Mendy | Senegal | 4 | 1094 | +0.0527 | +0.0462 | +0.0136 | +0.0788 |
| 20 | Saeid Ezatolahi | Iran | 3 | 814 | +0.0530 | +0.0448 | +0.0083 | +0.0813 |
| 21 | Krystian Bielik | Poland | 4 | 758 | +0.0490 | +0.0425 | +0.0078 | +0.0773 |
| 22 | Marcelo Brozovic | Croatia | 6 | 2962 | +0.0435 | +0.0407 | +0.0153 | +0.0662 |
| 23 | Jackson Irvine | Australia | 4 | 1379 | +0.0435 | +0.0392 | +0.0076 | +0.0708 |
| 24 | Youssouf Fofana | France | 6 | 1015 | +0.0401 | +0.0368 | +0.0065 | +0.0670 |
| 25 | Pierre-Emile Höjbjerg | Denmark | 3 | 1629 | +0.0401 | +0.0360 | +0.0024 | +0.0696 |
| 26 | Federico Valverde | Uruguay | 3 | 1228 | +0.0322 | +0.0298 | -0.0048 | +0.0643 |
| 27 | Hidemasa Morita | Japan | 3 | 1148 | +0.0321 | +0.0296 | -0.0052 | +0.0645 |
| 28 | Ellyes Skhiri | Tunisia | 3 | 1109 | +0.0312 | +0.0289 | -0.0061 | +0.0639 |
| 29 | Wataru Endo | Japan | 4 | 1247 | +0.0281 | +0.0269 | -0.0052 | +0.0589 |
| 30 | Ilkay Gündogan | Germany | 3 | 1195 | +0.0280 | +0.0265 | -0.0082 | +0.0612 |
| 31 | Yeltsin Tejeda | Costa Rica | 3 | 860 | +0.0274 | +0.0259 | -0.0103 | +0.0621 |
| 32 | Joshua Kimmich | Germany | 3 | 1640 | +0.0263 | +0.0253 | -0.0083 | +0.0588 |
| 33 | Moises Caicedo | Ecuador | 3 | 1170 | +0.0240 | +0.0235 | -0.0113 | +0.0583 |
| 34 | Ethan Ampadu | Wales | 3 | 1034 | +0.0232 | +0.0228 | -0.0125 | +0.0581 |
| 35 | Tyler Adams | United States | 4 | 1858 | +0.0188 | +0.0194 | -0.0111 | +0.0498 |
| 36 | Granit Xhaka | Switzerland | 4 | 1675 | +0.0153 | +0.0165 | -0.0143 | +0.0473 |
| 37 | Saša Lukić | Serbia | 3 | 1113 | +0.0135 | +0.0155 | -0.0195 | +0.0505 |
| 38 | Casemiro | Brazil | 4 | 2173 | +0.0139 | +0.0153 | -0.0146 | +0.0453 |
| 39 | Karim Boudiaf | Qatar | 3 | 813 | +0.0094 | +0.0127 | -0.0238 | +0.0492 |
| 40 | Celso Borges | Costa Rica | 3 | 814 | +0.0041 | +0.0087 | -0.0277 | +0.0452 |
| 41 | Declan Rice | England | 5 | 2597 | -0.0008 | +0.0026 | -0.0248 | +0.0299 |
| 42 | Ahmad Nourollahi | Iran | 3 | 690 | -0.0065 | +0.0014 | -0.0360 | +0.0388 |
| 43 | Grzegorz Krychowiak | Poland | 4 | 1167 | -0.0047 | +0.0007 | -0.0316 | +0.0331 |
| 44 | Aissa Laidouni | Tunisia | 3 | 930 | -0.0090 | -0.0012 | -0.0370 | +0.0346 |
| 45 | Frenkie de Jong | Netherlands | 5 | 2379 | -0.0156 | -0.0099 | -0.0376 | +0.0177 |
| 46 | Adrien Rabiot | France | 6 | 2654 | -0.0148 | -0.0100 | -0.0358 | +0.0158 |
| 47 | Teun Koopmeiners | Netherlands | 5 | 1086 | -0.0219 | -0.0136 | -0.0446 | +0.0175 |
| 48 | Ao Tanaka | Japan | 3 | 432 | -0.0350 | -0.0166 | -0.0571 | +0.0240 |
| 49 | Nemanja Maksimovic | Serbia | 3 | 692 | -0.0334 | -0.0181 | -0.0555 | +0.0193 |
| 50 | Ali Karimi | Iran | 3 | 422 | -0.0423 | -0.0213 | -0.0620 | +0.0195 |
| 51 | Pape Gueye | Senegal | 3 | 526 | -0.0427 | -0.0232 | -0.0623 | +0.0159 |
| 52 | Fred | Brazil | 4 | 825 | -0.0407 | -0.0263 | -0.0605 | +0.0079 |
| 53 | Sergio Busquets | Spain | 4 | 3186 | -0.0379 | -0.0280 | -0.0569 | +0.0009 |
| 54 | Jonathan Osorio | Canada | 3 | 643 | -0.0491 | -0.0290 | -0.0668 | +0.0088 |
| 55 | Lucas Paquetá | Brazil | 4 | 1784 | -0.0503 | -0.0370 | -0.0675 | -0.0064 |
| 56 | Marten De Roon | Netherlands | 5 | 1125 | -0.0533 | -0.0391 | -0.0700 | -0.0083 |
| 57 | Remo Freuler | Switzerland | 4 | 1543 | -0.0712 | -0.0534 | -0.0845 | -0.0223 |
| 58 | Jude Bellingham | England | 5 | 2605 | -0.0716 | -0.0578 | -0.0851 | -0.0304 |
| 59 | Leon Goretzka | Germany | 3 | 880 | -0.1245 | -0.0869 | -0.1230 | -0.0508 |

AV_vis table (all 59 DMs):

| # | Player | Team | matches | moments | raw AV_vis | shrunken | 90% low | 90% high |
|---|---|---|---|---|---|---|---|---|
| 1 | Ismael Kone | Canada | 3 | 365 | +0.1369 | +0.0949 | +0.0528 | +0.1371 |
| 2 | Woo-young Jung | South Korea | 4 | 833 | +0.0911 | +0.0737 | +0.0391 | +0.1082 |
| 3 | Leandro Paredes | Argentina | 5 | 846 | +0.0808 | +0.0672 | +0.0343 | +0.1001 |
| 4 | Rúben Neves | Portugal | 5 | 1072 | +0.0782 | +0.0663 | +0.0348 | +0.0978 |
| 5 | Aaron Mooy | Australia | 4 | 1021 | +0.0793 | +0.0656 | +0.0322 | +0.0991 |
| 6 | Jun-ho Son | South Korea | 2 | 180 | +0.1086 | +0.0635 | +0.0136 | +0.1135 |
| 7 | Enzo Fernandez | Argentina | 7 | 2109 | +0.0678 | +0.0611 | +0.0352 | +0.0870 |
| 8 | In-beom Hwang | South Korea | 4 | 1005 | +0.0711 | +0.0592 | +0.0256 | +0.0927 |
| 9 | Rodrigo Bentancur | Uruguay | 3 | 604 | +0.0749 | +0.0580 | +0.0193 | +0.0966 |
| 10 | Sofyan Amrabat | Morocco | 7 | 1621 | +0.0643 | +0.0575 | +0.0305 | +0.0846 |
| 11 | Aurélien Tchouaméni | France | 7 | 2103 | +0.0634 | +0.0573 | +0.0314 | +0.0832 |
| 12 | Mohamed Kanno | Saudi Arabia | 3 | 648 | +0.0710 | +0.0555 | +0.0173 | +0.0937 |
| 13 | Salis Abdul Samed | Ghana | 3 | 628 | +0.0704 | +0.0550 | +0.0166 | +0.0934 |
| 14 | Youri Tielemans | Belgium | 3 | 372 | +0.0686 | +0.0508 | +0.0087 | +0.0928 |
| 15 | Thomas Partey | Ghana | 3 | 689 | +0.0589 | +0.0471 | +0.0093 | +0.0850 |
| 16 | Atiba Hutchinson | Canada | 3 | 489 | +0.0583 | +0.0454 | +0.0054 | +0.0854 |
| 17 | Krystian Bielik | Poland | 4 | 566 | +0.0556 | +0.0452 | +0.0082 | +0.0823 |
| 18 | Axel Witsel | Belgium | 3 | 1242 | +0.0507 | +0.0426 | +0.0075 | +0.0777 |
| 19 | Pathe Ciss | Senegal | 3 | 295 | +0.0509 | +0.0381 | -0.0058 | +0.0820 |
| 20 | Federico Valverde | Uruguay | 3 | 790 | +0.0428 | +0.0359 | -0.0012 | +0.0730 |
| 21 | Nampalys Mendy | Senegal | 4 | 798 | +0.0411 | +0.0354 | +0.0006 | +0.0702 |
| 22 | Pierre-Emile Höjbjerg | Denmark | 3 | 1131 | +0.0376 | +0.0326 | -0.0029 | +0.0680 |
| 23 | Youssouf Fofana | France | 6 | 730 | +0.0364 | +0.0323 | -0.0005 | +0.0651 |
| 24 | Marcelo Brozovic | Croatia | 6 | 2175 | +0.0328 | +0.0306 | +0.0037 | +0.0575 |
| 25 | Jackson Irvine | Australia | 4 | 989 | +0.0334 | +0.0298 | -0.0038 | +0.0635 |
| 26 | Ellyes Skhiri | Tunisia | 3 | 794 | +0.0303 | +0.0268 | -0.0103 | +0.0638 |
| 27 | Wataru Endo | Japan | 4 | 947 | +0.0295 | +0.0268 | -0.0071 | +0.0606 |
| 28 | Moises Caicedo | Ecuador | 3 | 891 | +0.0280 | +0.0252 | -0.0113 | +0.0617 |
| 29 | Saeid Ezatolahi | Iran | 3 | 454 | +0.0267 | +0.0237 | -0.0168 | +0.0642 |
| 30 | Hidemasa Morita | Japan | 3 | 900 | +0.0187 | +0.0183 | -0.0181 | +0.0548 |
| 31 | Yeltsin Tejeda | Costa Rica | 3 | 657 | +0.0170 | +0.0171 | -0.0210 | +0.0552 |
| 32 | Ilkay Gündogan | Germany | 3 | 810 | +0.0135 | +0.0145 | -0.0225 | +0.0515 |
| 33 | Ethan Ampadu | Wales | 3 | 792 | +0.0122 | +0.0136 | -0.0235 | +0.0507 |
| 34 | Aissa Laidouni | Tunisia | 3 | 587 | +0.0093 | +0.0117 | -0.0271 | +0.0505 |
| 35 | Joshua Kimmich | Germany | 3 | 1248 | +0.0086 | +0.0107 | -0.0243 | +0.0458 |
| 36 | Granit Xhaka | Switzerland | 4 | 1296 | +0.0085 | +0.0103 | -0.0220 | +0.0427 |
| 37 | Ahmad Nourollahi | Iran | 3 | 420 | +0.0021 | +0.0072 | -0.0339 | +0.0483 |
| 38 | Saša Lukić | Serbia | 3 | 787 | +0.0024 | +0.0065 | -0.0307 | +0.0436 |
| 39 | Tyler Adams | United States | 4 | 1337 | +0.0024 | +0.0054 | -0.0268 | +0.0376 |
| 40 | Casemiro | Brazil | 4 | 1675 | +0.0016 | +0.0047 | -0.0266 | +0.0360 |
| 41 | Karim Boudiaf | Qatar | 3 | 614 | -0.0041 | +0.0022 | -0.0363 | +0.0408 |
| 42 | Declan Rice | England | 5 | 1848 | -0.0070 | -0.0030 | -0.0320 | +0.0260 |
| 43 | Celso Borges | Costa Rica | 3 | 617 | -0.0162 | -0.0063 | -0.0448 | +0.0322 |
| 44 | Ao Tanaka | Japan | 3 | 324 | -0.0224 | -0.0078 | -0.0509 | +0.0353 |
| 45 | Adrien Rabiot | France | 6 | 1947 | -0.0130 | -0.0085 | -0.0358 | +0.0188 |
| 46 | Teun Koopmeiners | Netherlands | 5 | 671 | -0.0226 | -0.0132 | -0.0477 | +0.0213 |
| 47 | Grzegorz Krychowiak | Poland | 4 | 842 | -0.0236 | -0.0140 | -0.0485 | +0.0205 |
| 48 | Ali Karimi | Iran | 3 | 289 | -0.0390 | -0.0174 | -0.0614 | +0.0267 |
| 49 | Fred | Brazil | 4 | 680 | -0.0342 | -0.0211 | -0.0570 | +0.0147 |
| 50 | Frenkie de Jong | Netherlands | 5 | 1833 | -0.0321 | -0.0238 | -0.0529 | +0.0052 |
| 51 | Pape Gueye | Senegal | 3 | 388 | -0.0462 | -0.0244 | -0.0661 | +0.0173 |
| 52 | Lucas Paquetá | Brazil | 4 | 1238 | -0.0362 | -0.0250 | -0.0575 | +0.0076 |
| 53 | Jonathan Osorio | Canada | 3 | 390 | -0.0554 | -0.0304 | -0.0721 | +0.0112 |
| 54 | Sergio Busquets | Spain | 4 | 2725 | -0.0483 | -0.0367 | -0.0666 | -0.0068 |
| 55 | Nemanja Maksimovic | Serbia | 3 | 458 | -0.0670 | -0.0397 | -0.0802 | +0.0007 |
| 56 | Marten De Roon | Netherlands | 5 | 887 | -0.0551 | -0.0399 | -0.0725 | -0.0073 |
| 57 | Jude Bellingham | England | 5 | 1575 | -0.0579 | -0.0448 | -0.0744 | -0.0151 |
| 58 | Remo Freuler | Switzerland | 4 | 1142 | -0.0848 | -0.0629 | -0.0958 | -0.0300 |
| 59 | Leon Goretzka | Germany | 3 | 616 | -0.1246 | -0.0830 | -0.1215 | -0.0445 |

### Fixed claim rules, applied mechanically
- R1 passes (AV and AV_vis) and R2 fails (AV and AV_vis). The claim allowed is: "a stable trait; no evidence it shows up in results in this sample". The MDE is 0.065 xG per 100 receptions per SD (AV_vis: 0.066).
- AV and AV_vis agree on R1 and R2, so the AV_vis limitation clause does not change the claim.

## 4. Deviations from the brief
- **Step 0:** not committed alone. The research lead committed it in 1601bcd with Task 37's brief.
- **Passer under pressure = `pressureType != 'N'`.** The brief says "not null", but pressureType is never null (N/P/L/A). The author chose this when asked, and it is recorded as D-016.
- **Score difference comes from kickoff restarts, not PFF shot outcomes.** A first run counted PFF `shotOutcomeType == 'G'`. It disagreed with StatsBomb's final score in 24 of 64 matches, because 'G' includes disallowed goals and shoot-out kicks and misses own goals. The score is now reconstructed from kickoffs: every kickoff in periods 1-4 other than the first of its period is taken by the team that just conceded. That leaves 4 matches disagreeing with StatsBomb's final score:
  - 10504, France v Poland: 3-0 against 3-1;
  - 10505, England v Senegal: 2-0 against 3-0;
  - 10502, Netherlands v United States: 2-1 against 3-1;
  - 3850, Poland v Argentina: 1-2 against 0-2.
  The first three are consistent with a late goal with no restart after it. Step 1 was re-run with this method; all numbers above are from that run. This is my operational choice (see Q1).
- **AV_vis baseline refit** on the visible subset (same folds and parameters), reading "the same, restricted" as the whole procedure. The alternative would restrict the original AV to the subset.
- **Minute** = PFF `startGameClock` (cumulative seconds) // 60.
- **Opponents** include the goalkeeper for space, lane and the 10 m count. Teammates exclude the goalkeeper and the passer, as specified.
- **DM rule:** no minimum number of WC2022 passes beyond the brief's ≥3 PFF matches and ≥300 moments. Some DMs have 40-60 WC passes behind the ≥50% share.
- **R1 halves:** a player's matches are split floor/ceil when the count is odd.
- **R2 reception features:**
  - Location = the ball at the receiver's next PFF event (within 3 entries), in the receiving team's frame.
  - Pressure = that event's pressureType, or its initialTouch pressure for IT events, coded != 'N'.
  - 572 receptions have these missing; XGBoost handles the NaN.
  - Role FE uses the receiver's positionGroupType at the pass event. Goalkeeper receivers are excluded, and a receiver not found in the snapshot gets role "NONE" (12 rows).
- **R2 Y window:** the next 10 entries with a possessionEventType after the pass.
- **R3 receptions per match** = PFF completed receptions ÷ PFF matches in which the player has moments.

## 5. Problems and surprises
- **R2's coefficient is negative and significant.** Taken at face value: within the same team and game, receptions by players who are more available in their other matches are followed by less net xG. This contradicts the question's premise that being available pays off in results.
- **R1 rests on 28 deep midfielders** (players with ≥4 PFF matches). All-outfield reliability is 0.62, with n = 183.
- **Base rate and target rate:** AVAILABLE covers a third of moments; the lane condition is the binding one (41.5% pass it).
- **g explains ~2% of Y** (R^2 0.019).
- **4,163 of 68,567 pass/cross events (6.1%) have no ball position** in the embedded snapshot, so they contribute no moments.
- **Step 4:** Busquets, de Jong and Bellingham are among the DMs whose intervals sit below the group mean on both AV and AV_vis.
- **Data notes (brief Q5):**
  - The tracking files for PFF 10510 (Croatia v Brazil) and 10511 (Netherlands v Argentina) contain no extra-time frames, though both matches went to extra time (StatsBomb periods 3-5). This task uses only PFF events and snapshots, not the tracking files.
  - 185 PFF shots are unpaired to StatsBomb (Task 36: 58 had no tracking frame; the rest had no StatsBomb shot within 10 s).

## 6. Questions for the research lead
- Q1: Should the kickoff-based score reconstruction be kept (4 mismatches), or should score come from another source?
- Q2: AV_vis: is a baseline refit on the visible subset what was meant, or AV restricted to the subset?
- Q3: Should the DM rule carry a minimum WC2022 pass count? Some DMs rest on 40-60 passes.

## 7. Files produced
- `src/pff/availability.py`, `src/pff/availability_tests.py`.
- `docs/DECISIONS.md` (D-016 appended).
- `data/processed/pff/`: `availability_moments.parquet`, `availability_receptions.parquet`, `availability_dm_table.parquet`.
- `data/pff_task38_step1.json`, `data/pff_task38_tests.json`.
- None of the data/ files are committed.
- Side effects: none else. No memory writes. JOURNAL.md and AGENTS.md untouched.
- Commits: brief 1601bcd (research lead); this task: recorded in a follow-up commit.

## 8. Confidence
- The measure and tests ran end to end with existing, reused inference code.
- The weakest links:
  - R1's n = 28.
  - The embedded PFF snapshots: ESTIMATED positions are ~62% of player-frames (Task 36). AV_vis addresses this and agrees.
  - The score feature's 4 mismatched matches.
