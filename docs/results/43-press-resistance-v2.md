# Task 43: Press resistance, done properly (a disclosed second attempt)
Date: 2026-09-28
Status: COMPLETE (every section run; interim page after Step 2 committed in c5cc7d9; deviations in Section 4)

Study sample and PFF WC2022 only. **This is a second attempt, made after seeing Task 42's results.** Task 42's numbers are reported beside this task's.

## Checklist
| Section | Status |
|---|---|
| Step 0 — brief committed alone | COMPLETE (0eed693, by the research lead) |
| Memory gate | COMPLETE (62% / 5.22 GB at 16:33 before Steps 1-2; 59% / 5.27 GB at 16:34 before Steps 3-6; 58% at 16:35 before Step 5) |
| Step 1 — corrected measure (spell) | COMPLETE |
| Step 2 — player-level stability | COMPLETE |
| Step 3 — results (P-test) with retention control | COMPLETE |
| Step 4 — praised list, Holm across all directional tests | COMPLETE |
| Step 5 — PFF convergent check | COMPLETE |
| Step 6 — deep-midfield tables | COMPLETE |
| Commits after Step 2 and at the end | COMPLETE |

## 1. Headline
Second attempt, study sample only.
- **Stability:** the corrected press-resistance measure fails the bar within deep midfielders (PR2_keep 0.387, PR2_fwd 0.283; n = 28).
- **Within-DM results:** no claim is allowed. The one strong result, deep midfielders' PR2_keep → Y_F3 (+4.13 pp per 100 pressured receptions per SD, p = 1.4e-6, Holm 5.5e-6, only 20 players), has a retention control on the same rows that is not positive (+0.05, p = 0.97).
- **Praised list:** PR2_keep T = +0.49 (p = 0.073). Across all 7 directional praised-list tests the smallest Holm p is 0.099 (Task 42's PR_keep), so no statement about the list is allowed.
- **Convergent check:** PFF and StatsBomb press resistance on WC2022 correlate r = 0.78, 95% CI [0.64, 0.86], n = 55 players.

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
- `.venv/bin/python -W ignore src/engine_v2/task43_steps3_6.py`:
  - Step 3: Task 42 Step 2 R2's design on the spell units (`task35_ptest.reception_features`, `crossfit_g`, `fe_fit`, S = other-match PR2 with ≥50 elsewhere). The retention control is redefined as below.
  - Step 4: Task 41's `perm_test`, plus Holm across all 7 directional praised-list tests.
  - Step 6: Task 29's method via `task42_step2.dm_table`.
- `.venv/bin/python -W ignore src/pff/task43_pff_check.py` runs Step 5.
- Reproduce: `task43_spells.py`, then `task43_steps3_6.py`, then `src/pff/task43_pff_check.py`.

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

### Step 3 — results (unit = pressured reception with value-model features: 38,428 of 39,904 spells)
The retention control on the same rows uses Y = the row's keep_spell and S = the receiver's keep_spell rate over ALL his completed receptions in other matches (≥100 elsewhere). Coefficients are pp (Y_F3) or xG (net xG) per 100 pressured receptions per SD.

| Group | S | Y | n | players | coef | 95% CI | p | MDE | retention control coef [95% CI], p |
|---|---|---|---|---|---|---|---|---|---|
| all | PR2_KEEP | Y_F3 | 10,755 | 141 | +0.400 | [-0.720, 1.519] | 0.484 | 1.599 | +6.267 [4.335, 8.198], 2.03e-10 |
| DM | PR2_KEEP | Y_F3 | 2,379 | 20 | +4.132 | [2.455, 5.810] | 1.38e-06 | 2.397 | +0.047 [-2.309, 2.403], 0.969 |
| all | PR2_KEEP | net xG | 18,149 | 141 | +0.025 | [-0.089, 0.139] | 0.665 | 0.162 | +4.520 [2.307, 6.732], 6.23e-05 |
| DM | PR2_KEEP | net xG | 3,025 | 20 | -0.078 | [-0.185, 0.030] | 0.158 | 0.154 | +0.124 [-2.242, 2.489], 0.918 |
| all | PR2_FWD | Y_F3 | 10,755 | 141 | +0.088 | [-0.985, 1.161] | 0.872 | 1.533 | +6.267 [4.335, 8.198], 2.03e-10 |
| DM | PR2_FWD | Y_F3 | 2,379 | 20 | +0.449 | [-3.225, 4.123] | 0.811 | 5.249 | +0.047 [-2.309, 2.403], 0.969 |
| all | PR2_FWD | net xG | 18,149 | 141 | +0.032 | [-0.053, 0.116] | 0.462 | 0.121 | +4.520 [2.307, 6.732], 6.23e-05 |
| DM | PR2_FWD | net xG | 3,025 | 20 | -0.183 | [-0.317, -0.048] | 0.00766 | 0.192 | +0.124 [-2.242, 2.489], 0.918 |

Claim family: Holm across this task's 4 within-DM results tests.

| Test | coef per 100 per SD | raw p | Holm | control on same rows | claim allowed |
|---|---|---|---|---|---|
| dm|pr2_keep|y_f3 | +4.132 | 1.38e-06 | 5.52e-06 | +0.047, p=0.969 | no |
| dm|pr2_keep|y_net_xg | -0.078 | 0.158 | 0.315 | +0.124, p=0.918 | no |
| dm|pr2_fwd|y_f3 | +0.449 | 0.811 | 0.811 | +0.047, p=0.969 | no |
| dm|pr2_fwd|y_net_xg | -0.183 | 0.00766 | 0.023 | +0.124, p=0.918 | no |

Task 42 (first attempt), for comparison: DM PR_keep → Y_F3 +2.911 (p = 0.017, Holm 0.19, control not positive); all-player PR_keep → Y_F3 +1.497 (p = 0.0014).

### Step 4 — praised list (Task 41's method; ≥50 pressured receptions; 141 qualifying; 11 of 13 present, Grillitsch and Shaparenko absent)

| Measure | T | p (two-sided) | pre-declared direction |
|---|---|---|---|
| PR2_keep | +0.493 | 0.07329 | higher (direction matches, p ≥ 0.05) |
| PR2_fwd | +0.269 | 0.3385 | higher (direction matches, p ≥ 0.05) |

z-scores:
- **PR2_keep:** Kevin De Bruyne -0.84, Marco Verratti +0.39, Granit Xhaka +0.87, Sergio Busquets i Burgos +0.04, Luka Modrić +0.06, Toni Kroos -0.29, Joshua Kimmich +1.38, Rodrigo Hernández Cascante +1.42, Frenkie de Jong +1.59, İlkay Gündoğan +0.37, Pedro González López +0.43.
- **PR2_fwd:** Kevin De Bruyne +1.59, Marco Verratti +0.41, Granit Xhaka -0.49, Sergio Busquets i Burgos +0.77, Luka Modrić +0.77, Toni Kroos +0.39, Joshua Kimmich +1.31, Rodrigo Hernández Cascante -1.44, Frenkie de Jong +0.60, İlkay Gündoğan -0.39, Pedro González López -0.55.

Holm across every directional praised-list test so far (7):

| Test | T | p | Holm p |
|---|---|---|---|
| Task 41 AV (lower) | +0.293 | 0.3651 | 1 |
| Task 41 AV_vis (lower) | +0.108 | 0.7382 | 1 |
| Task 41 RQ_rel (lower) | -0.267 | 0.3254 | 1 |
| Task 42 PR_keep (higher) | +0.687 | 0.0142 | 0.0994 |
| Task 42 PR_fwd (higher) | -0.224 | 0.4256 | 1 |
| Task 43 PR2_keep (higher) | +0.493 | 0.07329 | 0.44 |
| Task 43 PR2_fwd (higher) | +0.269 | 0.3385 | 1 |

### Step 5 — PFF convergent check (WC2022; report only)
- PFF pressured receptions (Task 38 rec_pressure = 1): 12,127.
- How the spells end: 10,074 passes; 1,226 opponent events (keep 0); 506 teammate events (excluded); 318 shots (excluded); 3 with no end (excluded).
- Units: 11,300. keep_pff base rate: 0.656. Baseline OOF AUC: 0.634.
- Players with ≥30 pressured receptions: PFF 116; StatsBomb restricted to WC2022 60; **both 55**.
- **Pearson r (player PFF score vs player StatsBomb PR2_keep, WC2022) = 0.776, 95% CI [0.644, 0.864]**.

### Step 6 — deep-midfield tables (Task 29's method, within the 111; output only)
- **PR2_keep:** mu_w = +0.0870, tau^2 = 0.00380, **Q = 219.9 on 110 df, p = 2.5e-09**.
  - Above: Leandro Daniel Paredes, Vitor Machado Ferreira, Granit Xhaka, Marco Verratti.
  - Below: Pierre-Emile Højbjerg, Alex Král.
- **PR2_fwd:** mu_w = +0.0260, tau^2 = 0.00070, Q = 132.1 on 110 df, p = 0.075.
  - Above: none.
  - Below: Vitor Machado Ferreira.

PR2_keep (all 111):

| # | Player | matches | pressured receptions | raw | shrunken | 90% low | 90% high |
|---|---|---|---|---|---|---|---|
| 1 | Leandro Daniel Paredes | 15 | 73 | +0.2271 | +0.1721 | +0.1086 | +0.2357 |
| 2 | Ander Herrera Agüera | 8 | 48 | +0.2248 | +0.1565 | +0.0851 | +0.2279 |
| 3 | Vitor Machado Ferreira | 35 | 276 | +0.1569 | +0.1467 | +0.1080 | +0.1854 |
| 4 | Granit Xhaka | 43 | 501 | +0.1513 | +0.1458 | +0.1161 | +0.1755 |
| 5 | Morten Hjulmand | 3 | 37 | +0.2066 | +0.1396 | +0.0637 | +0.2155 |
| 6 | Axel Witsel | 7 | 26 | +0.2307 | +0.1381 | +0.0567 | +0.2195 |
| 7 | Corentin Tolisso | 4 | 12 | +0.3082 | +0.1319 | +0.0413 | +0.2224 |
| 8 | Declan Rice | 19 | 97 | +0.1492 | +0.1289 | +0.0709 | +0.1868 |
| 9 | Amadou Onana | 7 | 37 | +0.1781 | +0.1270 | +0.0511 | +0.2029 |
| 10 | Hakan Çalhanoğlu | 7 | 56 | +0.1562 | +0.1246 | +0.0560 | +0.1932 |
| 11 | Saša Lukić | 6 | 24 | +0.1940 | +0.1231 | +0.0406 | +0.2057 |
| 12 | Dixon Jair Arroyo Espinoza | 3 | 9 | +0.3085 | +0.1225 | +0.0296 | +0.2154 |
| 13 | Marco Verratti | 47 | 550 | +0.1231 | +0.1203 | +0.0918 | +0.1488 |
| 14 | Nadiem Amiri | 5 | 20 | +0.1938 | +0.1188 | +0.0338 | +0.2038 |
| 15 | Tyler Adams | 4 | 20 | +0.1933 | +0.1187 | +0.0337 | +0.2036 |
| 16 | Florian Grillitsch | 7 | 37 | +0.1558 | +0.1173 | +0.0414 | +0.1932 |
| 17 | Leander Dendoncker | 3 | 11 | +0.2317 | +0.1144 | +0.0231 | +0.2057 |
| 18 | Robert Andrich | 28 | 187 | +0.1208 | +0.1140 | +0.0685 | +0.1595 |
| 19 | Nampalys Mendy | 4 | 20 | +0.1725 | +0.1125 | +0.0275 | +0.1974 |
| 20 | Stanislav Lobotka | 5 | 38 | +0.1428 | +0.1119 | +0.0365 | +0.1874 |
| 21 | Lucas Tolentino Coelho de Lima | 5 | 49 | +0.1337 | +0.1108 | +0.0398 | +0.1818 |
| 22 | Exequiel Alejandro Palacios | 25 | 248 | +0.1152 | +0.1107 | +0.0702 | +0.1513 |
| 23 | Jorge Luiz Frello Filho | 10 | 90 | +0.1222 | +0.1101 | +0.0506 | +0.1695 |
| 24 | Joan Jordán Moreno | 2 | 14 | +0.1817 | +0.1087 | +0.0196 | +0.1977 |
| 25 | Tijjani Reijnders | 6 | 29 | +0.1436 | +0.1086 | +0.0288 | +0.1884 |
| 26 | Enzo Fernandez | 7 | 40 | +0.1338 | +0.1085 | +0.0339 | +0.1830 |
| 27 | Boubacar Kamara | 2 | 19 | +0.1599 | +0.1079 | +0.0223 | +0.1935 |
| 28 | Martín Zubimendi Ibáñez | 5 | 20 | +0.1572 | +0.1079 | +0.0229 | +0.1929 |
| 29 | İlkay Gündoğan | 11 | 66 | +0.1221 | +0.1075 | +0.0420 | +0.1730 |
| 30 | Miralem Pjanić | 15 | 92 | +0.1177 | +0.1073 | +0.0483 | +0.1663 |
| 31 | Marten de Roon | 5 | 13 | +0.1584 | +0.1024 | +0.0127 | +0.1922 |
| 32 | João Maria Lobo Alves Palhinha Gonçalves | 9 | 22 | +0.1340 | +0.1019 | +0.0182 | +0.1857 |
| 33 | Sergio Busquets i Burgos | 44 | 423 | +0.1026 | +0.1010 | +0.0689 | +0.1331 |
| 34 | Ellyes Joris Skhiri | 5 | 19 | +0.1356 | +0.1010 | +0.0154 | +0.1866 |
| 35 | Christian Nørgaard | 8 | 20 | +0.1336 | +0.1009 | +0.0159 | +0.1859 |
| 36 | Jerdy Schouten | 6 | 39 | +0.1157 | +0.1000 | +0.0250 | +0.1750 |
| 37 | Jordan Veretout | 3 | 17 | +0.1322 | +0.0990 | +0.0120 | +0.1859 |
| 38 | Mikel Merino Zazón | 7 | 62 | +0.1077 | +0.0987 | +0.0321 | +0.1654 |
| 39 | Nemanja Gudelj | 4 | 6 | +0.1498 | +0.0941 | -0.0014 | +0.1896 |
| 40 | Azor Matusiwa | 2 | 17 | +0.1067 | +0.0922 | +0.0053 | +0.1792 |
| 41 | Angel Gomes | 3 | 21 | +0.1035 | +0.0921 | +0.0077 | +0.1764 |
| 42 | Wataru Endo | 3 | 18 | +0.1022 | +0.0912 | +0.0049 | +0.1774 |
| 43 | Moisés Isaac Caicedo Corozo | 3 | 28 | +0.0969 | +0.0907 | +0.0103 | +0.1710 |
| 44 | Batista Mendy | 2 | 13 | +0.1007 | +0.0900 | +0.0002 | +0.1797 |
| 45 | Pedro Chirivella Burgos | 3 | 24 | +0.0934 | +0.0891 | +0.0066 | +0.1717 |
| 46 | Kalvin Phillips | 9 | 48 | +0.0888 | +0.0879 | +0.0165 | +0.1593 |
| 47 | Carlos Henrique Casimiro | 6 | 57 | +0.0871 | +0.0871 | +0.0188 | +0.1553 |
| 48 | Toni Kroos | 11 | 59 | +0.0834 | +0.0850 | +0.0174 | +0.1526 |
| 49 | Mario Lemina | 3 | 10 | +0.0685 | +0.0838 | -0.0084 | +0.1759 |
| 50 | Bruno Guimarães Rodriguez Moura | 3 | 16 | +0.0733 | +0.0835 | -0.0041 | +0.1711 |
| 51 | Celso Borges Mora | 3 | 19 | +0.0653 | +0.0807 | -0.0049 | +0.1664 |
| 52 | Kaan Ayhan | 6 | 20 | +0.0616 | +0.0794 | -0.0055 | +0.1644 |
| 53 | Aurélien Djani Tchouaméni | 12 | 51 | +0.0704 | +0.0784 | +0.0081 | +0.1486 |
| 54 | Sofyan Amrabat | 6 | 28 | +0.0618 | +0.0776 | -0.0027 | +0.1579 |
| 55 | Samuel Moutoussamy | 3 | 17 | +0.0405 | +0.0747 | -0.0123 | +0.1616 |
| 56 | Timi Elšnik | 4 | 13 | +0.0299 | +0.0747 | -0.0151 | +0.1644 |
| 57 | N'Golo Kanté | 10 | 73 | +0.0661 | +0.0743 | +0.0108 | +0.1378 |
| 58 | Giorgi Kochorashvili | 5 | 31 | +0.0532 | +0.0736 | -0.0052 | +0.1524 |
| 59 | Trent Alexander-Arnold | 4 | 9 | -0.0077 | +0.0718 | -0.0211 | +0.1647 |
| 60 | In-Beom Hwang | 4 | 27 | +0.0450 | +0.0717 | -0.0092 | +0.1526 |
| 61 | Leon Goretzka | 8 | 37 | +0.0495 | +0.0705 | -0.0054 | +0.1464 |
| 62 | Joey Veerman | 6 | 15 | +0.0161 | +0.0699 | -0.0184 | +0.1582 |
| 63 | Youri Tielemans | 10 | 35 | +0.0459 | +0.0695 | -0.0073 | +0.1463 |
| 64 | Johan Gastien | 3 | 21 | +0.0283 | +0.0689 | -0.0154 | +0.1533 |
| 65 | Woo-Young Jung | 3 | 11 | -0.0160 | +0.0675 | -0.0238 | +0.1588 |
| 66 | Salis Abdul Samed | 4 | 17 | +0.0053 | +0.0653 | -0.0216 | +0.1523 |
| 67 | Benjamin Bourigeaud | 3 | 12 | -0.0321 | +0.0628 | -0.0277 | +0.1534 |
| 68 | Rúben Diogo Da Silva Neves | 7 | 19 | +0.0027 | +0.0628 | -0.0229 | +0.1484 |
| 69 | Ethan Ampadu | 5 | 21 | +0.0065 | +0.0622 | -0.0222 | +0.1465 |
| 70 | Emre Can | 5 | 13 | -0.0332 | +0.0610 | -0.0288 | +0.1508 |
| 71 | Maxence Caqueret | 3 | 15 | -0.0237 | +0.0603 | -0.0281 | +0.1486 |
| 72 | Youssouf Fofana | 8 | 29 | +0.0148 | +0.0595 | -0.0203 | +0.1393 |
| 73 | Kobbie Mainoo | 6 | 33 | +0.0192 | +0.0591 | -0.0187 | +0.1368 |
| 74 | Jonas Martin | 3 | 11 | -0.0672 | +0.0578 | -0.0335 | +0.1491 |
| 75 | Seko Fofana | 3 | 34 | +0.0130 | +0.0560 | -0.0213 | +0.1333 |
| 76 | Ádám Nagy | 6 | 26 | -0.0021 | +0.0553 | -0.0261 | +0.1367 |
| 77 | Serhii Sydorchuk | 4 | 33 | +0.0075 | +0.0543 | -0.0235 | +0.1320 |
| 78 | Taras Stepanenko | 3 | 20 | -0.0284 | +0.0526 | -0.0323 | +0.1376 |
| 79 | Marcelo Brozović | 12 | 91 | +0.0337 | +0.0519 | -0.0074 | +0.1111 |
| 80 | Jhegson Sebastián Méndez Carabalí | 2 | 11 | -0.0994 | +0.0517 | -0.0396 | +0.1430 |
| 81 | Laurent Abergel | 3 | 25 | -0.0171 | +0.0509 | -0.0311 | +0.1329 |
| 82 | Jakub Moder | 4 | 19 | -0.0401 | +0.0505 | -0.0352 | +0.1361 |
| 83 | Aïssa Bilal Laïdouni | 5 | 29 | -0.0098 | +0.0501 | -0.0297 | +0.1299 |
| 84 | Callum McGregor | 6 | 33 | -0.0037 | +0.0497 | -0.0281 | +0.1274 |
| 85 | Billy Gilmour | 3 | 27 | -0.0169 | +0.0492 | -0.0317 | +0.1300 |
| 86 | Thomas Delaney | 9 | 60 | +0.0154 | +0.0469 | -0.0204 | +0.1142 |
| 87 | Kristoffer Olsson | 4 | 15 | -0.0864 | +0.0451 | -0.0432 | +0.1334 |
| 88 | András Schäfer | 7 | 40 | -0.0073 | +0.0437 | -0.0309 | +0.1183 |
| 89 | Tomáš Souček | 8 | 49 | -0.0007 | +0.0423 | -0.0287 | +0.1133 |
| 90 | Mohammed Kanoo | 3 | 21 | -0.0598 | +0.0417 | -0.0426 | +0.1261 |
| 91 | Benjamin André | 3 | 21 | -0.0662 | +0.0398 | -0.0446 | +0.1241 |
| 92 | Ivan Ilić | 4 | 11 | -0.1692 | +0.0385 | -0.0528 | +0.1298 |
| 93 | Thomas Teye Partey | 3 | 18 | -0.0895 | +0.0382 | -0.0481 | +0.1245 |
| 94 | Xaver Schlager | 6 | 31 | -0.0424 | +0.0357 | -0.0431 | +0.1144 |
| 95 | Paul Pogba | 4 | 49 | -0.0157 | +0.0347 | -0.0363 | +0.1057 |
| 96 | Aaron Mooy | 4 | 20 | -0.0903 | +0.0342 | -0.0508 | +0.1191 |
| 97 | Hidemasa Morita | 3 | 21 | -0.0872 | +0.0333 | -0.0511 | +0.1176 |
| 98 | Rodrigo Bentancur Colmán | 3 | 13 | -0.1676 | +0.0320 | -0.0578 | +0.1217 |
| 99 | Kristjan Asllani | 3 | 23 | -0.0821 | +0.0315 | -0.0516 | +0.1147 |
| 100 | Remo Freuler | 14 | 104 | +0.0052 | +0.0307 | -0.0259 | +0.0874 |
| 101 | Jackson Irvine | 4 | 22 | -0.0951 | +0.0290 | -0.0547 | +0.1128 |
| 102 | Grzegorz Krychowiak | 5 | 31 | -0.0669 | +0.0259 | -0.0528 | +0.1047 |
| 103 | Atakan Karazor | 2 | 13 | -0.1978 | +0.0254 | -0.0644 | +0.1152 |
| 104 | Albin Ekdal | 4 | 13 | -0.2129 | +0.0221 | -0.0676 | +0.1119 |
| 105 | Nicolas Seiwald | 5 | 17 | -0.1644 | +0.0204 | -0.0666 | +0.1073 |
| 106 | Mario Götze | 3 | 10 | -0.3097 | +0.0175 | -0.0746 | +0.1097 |
| 107 | Teun Koopmeiners | 4 | 11 | -0.2889 | +0.0159 | -0.0755 | +0.1072 |
| 108 | Adam Gnezda Čerin | 4 | 23 | -0.1320 | +0.0152 | -0.0680 | +0.0983 |
| 109 | Joe Allen | 5 | 24 | -0.1262 | +0.0151 | -0.0675 | +0.0976 |
| 110 | Pierre-Emile Højbjerg | 13 | 85 | -0.0283 | +0.0128 | -0.0477 | +0.0734 |
| 111 | Alex Král | 6 | 25 | -0.2066 | -0.0148 | -0.0967 | +0.0672 |

PR2_fwd (all 111):

| # | Player | matches | pressured receptions | raw | shrunken | 90% low | 90% high |
|---|---|---|---|---|---|---|---|
| 1 | N'Golo Kanté | 10 | 73 | +0.1338 | +0.0515 | +0.0136 | +0.0894 |
| 2 | Sergio Busquets i Burgos | 44 | 423 | +0.0648 | +0.0509 | +0.0250 | +0.0769 |
| 3 | Pierre-Emile Højbjerg | 13 | 85 | +0.1124 | +0.0490 | +0.0118 | +0.0861 |
| 4 | András Schäfer | 7 | 40 | +0.1815 | +0.0486 | +0.0085 | +0.0887 |
| 5 | Celso Borges Mora | 3 | 19 | +0.2903 | +0.0458 | +0.0040 | +0.0875 |
| 6 | Ethan Ampadu | 5 | 21 | +0.2378 | +0.0434 | +0.0018 | +0.0849 |
| 7 | Tomáš Souček | 8 | 49 | +0.1185 | +0.0419 | +0.0025 | +0.0814 |
| 8 | Marco Verratti | 47 | 550 | +0.0473 | +0.0409 | +0.0172 | +0.0646 |
| 9 | Mario Lemina | 3 | 10 | +0.3876 | +0.0407 | -0.0018 | +0.0832 |
| 10 | Adam Gnezda Čerin | 4 | 23 | +0.1912 | +0.0407 | -0.0007 | +0.0821 |
| 11 | Mikel Merino Zazón | 7 | 62 | +0.0961 | +0.0406 | +0.0020 | +0.0792 |
| 12 | Tyler Adams | 4 | 20 | +0.1821 | +0.0382 | -0.0034 | +0.0799 |
| 13 | In-Beom Hwang | 4 | 27 | +0.1359 | +0.0373 | -0.0038 | +0.0784 |
| 14 | Jerdy Schouten | 6 | 39 | +0.1008 | +0.0366 | -0.0036 | +0.0768 |
| 15 | Enzo Fernandez | 7 | 40 | +0.0851 | +0.0346 | -0.0055 | +0.0747 |
| 16 | Youri Tielemans | 10 | 35 | +0.0860 | +0.0337 | -0.0067 | +0.0742 |
| 17 | Aïssa Bilal Laïdouni | 5 | 29 | +0.0957 | +0.0336 | -0.0073 | +0.0746 |
| 18 | Xaver Schlager | 6 | 31 | +0.0915 | +0.0336 | -0.0072 | +0.0744 |
| 19 | Marcelo Brozović | 12 | 91 | +0.0527 | +0.0334 | -0.0034 | +0.0703 |
| 20 | Amadou Onana | 7 | 37 | +0.0775 | +0.0330 | -0.0073 | +0.0733 |
| 21 | Joey Veerman | 6 | 15 | +0.1406 | +0.0328 | -0.0092 | +0.0749 |
| 22 | Jordan Veretout | 3 | 17 | +0.1130 | +0.0318 | -0.0101 | +0.0737 |
| 23 | Pedro Chirivella Burgos | 3 | 24 | +0.0814 | +0.0311 | -0.0102 | +0.0724 |
| 24 | Joan Jordán Moreno | 2 | 14 | +0.1172 | +0.0311 | -0.0111 | +0.0733 |
| 25 | Johan Gastien | 3 | 21 | +0.0876 | +0.0310 | -0.0105 | +0.0726 |
| 26 | Benjamin Bourigeaud | 3 | 12 | +0.1295 | +0.0310 | -0.0113 | +0.0733 |
| 27 | João Maria Lobo Alves Palhinha Gonçalves | 9 | 22 | +0.0843 | +0.0310 | -0.0105 | +0.0725 |
| 28 | Batista Mendy | 2 | 13 | +0.1151 | +0.0306 | -0.0116 | +0.0729 |
| 29 | Toni Kroos | 11 | 59 | +0.0462 | +0.0300 | -0.0088 | +0.0688 |
| 30 | Leandro Daniel Paredes | 15 | 73 | +0.0427 | +0.0299 | -0.0080 | +0.0678 |
| 31 | Angel Gomes | 3 | 21 | +0.0744 | +0.0299 | -0.0116 | +0.0715 |
| 32 | Nampalys Mendy | 4 | 20 | +0.0747 | +0.0298 | -0.0119 | +0.0714 |
| 33 | Declan Rice | 19 | 97 | +0.0388 | +0.0297 | -0.0068 | +0.0662 |
| 34 | Christian Nørgaard | 8 | 20 | +0.0723 | +0.0296 | -0.0121 | +0.0713 |
| 35 | Giorgi Kochorashvili | 5 | 31 | +0.0563 | +0.0295 | -0.0113 | +0.0703 |
| 36 | Jakub Moder | 4 | 19 | +0.0723 | +0.0294 | -0.0123 | +0.0712 |
| 37 | Trent Alexander-Arnold | 4 | 9 | +0.1106 | +0.0291 | -0.0135 | +0.0717 |
| 38 | Hidemasa Morita | 3 | 21 | +0.0631 | +0.0290 | -0.0126 | +0.0706 |
| 39 | Ádám Nagy | 6 | 26 | +0.0551 | +0.0289 | -0.0123 | +0.0700 |
| 40 | Nicolas Seiwald | 5 | 17 | +0.0657 | +0.0286 | -0.0133 | +0.0705 |
| 41 | Jhegson Sebastián Méndez Carabalí | 2 | 11 | +0.0844 | +0.0286 | -0.0138 | +0.0710 |
| 42 | Maxence Caqueret | 3 | 15 | +0.0695 | +0.0286 | -0.0135 | +0.0706 |
| 43 | Aaron Mooy | 4 | 20 | +0.0593 | +0.0286 | -0.0131 | +0.0702 |
| 44 | Lucas Tolentino Coelho de Lima | 5 | 49 | +0.0402 | +0.0284 | -0.0110 | +0.0679 |
| 45 | Woo-Young Jung | 3 | 11 | +0.0781 | +0.0283 | -0.0141 | +0.0707 |
| 46 | Seko Fofana | 3 | 34 | +0.0421 | +0.0280 | -0.0126 | +0.0686 |
| 47 | Youssouf Fofana | 8 | 29 | +0.0444 | +0.0280 | -0.0130 | +0.0689 |
| 48 | Rúben Diogo Da Silva Neves | 7 | 19 | +0.0509 | +0.0278 | -0.0139 | +0.0696 |
| 49 | Martín Zubimendi Ibáñez | 5 | 20 | +0.0491 | +0.0278 | -0.0139 | +0.0694 |
| 50 | Stanislav Lobotka | 5 | 38 | +0.0386 | +0.0277 | -0.0125 | +0.0680 |
| 51 | Marten de Roon | 5 | 13 | +0.0557 | +0.0275 | -0.0147 | +0.0698 |
| 52 | Mario Götze | 3 | 10 | +0.0507 | +0.0270 | -0.0155 | +0.0695 |
| 53 | Corentin Tolisso | 4 | 12 | +0.0433 | +0.0268 | -0.0155 | +0.0691 |
| 54 | Samuel Moutoussamy | 3 | 17 | +0.0290 | +0.0262 | -0.0157 | +0.0681 |
| 55 | Grzegorz Krychowiak | 5 | 31 | +0.0263 | +0.0260 | -0.0148 | +0.0668 |
| 56 | Taras Stepanenko | 3 | 20 | +0.0260 | +0.0260 | -0.0157 | +0.0676 |
| 57 | Thomas Delaney | 9 | 60 | +0.0253 | +0.0258 | -0.0129 | +0.0646 |
| 58 | Jonas Martin | 3 | 11 | +0.0230 | +0.0258 | -0.0166 | +0.0682 |
| 59 | Timi Elšnik | 4 | 13 | +0.0227 | +0.0258 | -0.0165 | +0.0680 |
| 60 | Morten Hjulmand | 3 | 37 | +0.0233 | +0.0256 | -0.0147 | +0.0659 |
| 61 | Exequiel Alejandro Palacios | 25 | 248 | +0.0252 | +0.0256 | -0.0047 | +0.0558 |
| 62 | Azor Matusiwa | 2 | 17 | +0.0197 | +0.0255 | -0.0164 | +0.0674 |
| 63 | Kaan Ayhan | 6 | 20 | +0.0161 | +0.0252 | -0.0165 | +0.0668 |
| 64 | Remo Freuler | 14 | 104 | +0.0232 | +0.0251 | -0.0110 | +0.0612 |
| 65 | Nemanja Gudelj | 4 | 6 | -0.0234 | +0.0247 | -0.0181 | +0.0676 |
| 66 | Tijjani Reijnders | 6 | 29 | +0.0125 | +0.0245 | -0.0165 | +0.0654 |
| 67 | Nadiem Amiri | 5 | 20 | -0.0033 | +0.0237 | -0.0180 | +0.0653 |
| 68 | Bruno Guimarães Rodriguez Moura | 3 | 16 | -0.0114 | +0.0236 | -0.0184 | +0.0656 |
| 69 | Leander Dendoncker | 3 | 11 | -0.0284 | +0.0235 | -0.0189 | +0.0659 |
| 70 | Moisés Isaac Caicedo Corozo | 3 | 28 | +0.0003 | +0.0232 | -0.0178 | +0.0642 |
| 71 | Jackson Irvine | 4 | 22 | -0.0069 | +0.0231 | -0.0183 | +0.0646 |
| 72 | Benjamin André | 3 | 21 | -0.0112 | +0.0229 | -0.0187 | +0.0645 |
| 73 | Miralem Pjanić | 15 | 92 | +0.0127 | +0.0222 | -0.0145 | +0.0590 |
| 74 | İlkay Gündoğan | 11 | 66 | +0.0081 | +0.0220 | -0.0163 | +0.0604 |
| 75 | Rodrigo Bentancur Colmán | 3 | 13 | -0.0592 | +0.0215 | -0.0208 | +0.0637 |
| 76 | Aurélien Djani Tchouaméni | 12 | 51 | +0.0000 | +0.0213 | -0.0180 | +0.0607 |
| 77 | Boubacar Kamara | 2 | 19 | -0.0364 | +0.0213 | -0.0205 | +0.0630 |
| 78 | Kristjan Asllani | 3 | 23 | -0.0279 | +0.0212 | -0.0203 | +0.0626 |
| 79 | Dixon Jair Arroyo Espinoza | 3 | 9 | -0.1070 | +0.0210 | -0.0215 | +0.0636 |
| 80 | Carlos Henrique Casimiro | 6 | 57 | -0.0006 | +0.0208 | -0.0182 | +0.0597 |
| 81 | Sofyan Amrabat | 6 | 28 | -0.0240 | +0.0206 | -0.0204 | +0.0616 |
| 82 | Leon Goretzka | 8 | 37 | -0.0170 | +0.0201 | -0.0202 | +0.0604 |
| 83 | Albin Ekdal | 4 | 13 | -0.0868 | +0.0200 | -0.0222 | +0.0623 |
| 84 | Axel Witsel | 7 | 26 | -0.0356 | +0.0198 | -0.0214 | +0.0610 |
| 85 | Kristoffer Olsson | 4 | 15 | -0.0821 | +0.0195 | -0.0226 | +0.0615 |
| 86 | Salis Abdul Samed | 4 | 17 | -0.0736 | +0.0192 | -0.0227 | +0.0611 |
| 87 | Atakan Karazor | 2 | 13 | -0.1046 | +0.0191 | -0.0231 | +0.0613 |
| 88 | Ander Herrera Agüera | 8 | 48 | -0.0157 | +0.0189 | -0.0207 | +0.0584 |
| 89 | Kobbie Mainoo | 6 | 33 | -0.0315 | +0.0189 | -0.0218 | +0.0595 |
| 90 | Thomas Teye Partey | 3 | 18 | -0.0739 | +0.0188 | -0.0230 | +0.0607 |
| 91 | Alex Král | 6 | 25 | -0.0507 | +0.0186 | -0.0227 | +0.0598 |
| 92 | Kalvin Phillips | 9 | 48 | -0.0179 | +0.0185 | -0.0210 | +0.0581 |
| 93 | Florian Grillitsch | 7 | 37 | -0.0298 | +0.0184 | -0.0220 | +0.0587 |
| 94 | Mohammed Kanoo | 3 | 21 | -0.0703 | +0.0181 | -0.0235 | +0.0596 |
| 95 | Emre Can | 5 | 13 | -0.1291 | +0.0178 | -0.0244 | +0.0601 |
| 96 | Ivan Ilić | 4 | 11 | -0.1572 | +0.0178 | -0.0247 | +0.0602 |
| 97 | Saša Lukić | 6 | 24 | -0.0686 | +0.0172 | -0.0241 | +0.0585 |
| 98 | Billy Gilmour | 3 | 27 | -0.0609 | +0.0170 | -0.0241 | +0.0581 |
| 99 | Ellyes Joris Skhiri | 5 | 19 | -0.0963 | +0.0168 | -0.0249 | +0.0585 |
| 100 | Teun Koopmeiners | 4 | 11 | -0.1856 | +0.0165 | -0.0259 | +0.0589 |
| 101 | Wataru Endo | 3 | 18 | -0.1224 | +0.0154 | -0.0264 | +0.0572 |
| 102 | Paul Pogba | 4 | 49 | -0.0382 | +0.0149 | -0.0246 | +0.0543 |
| 103 | Laurent Abergel | 3 | 25 | -0.1039 | +0.0135 | -0.0278 | +0.0547 |
| 104 | Jorge Luiz Frello Filho | 10 | 90 | -0.0207 | +0.0130 | -0.0239 | +0.0499 |
| 105 | Joe Allen | 5 | 24 | -0.1379 | +0.0108 | -0.0306 | +0.0521 |
| 106 | Serhii Sydorchuk | 4 | 33 | -0.0977 | +0.0107 | -0.0299 | +0.0513 |
| 107 | Granit Xhaka | 43 | 501 | +0.0034 | +0.0106 | -0.0139 | +0.0351 |
| 108 | Hakan Çalhanoğlu | 7 | 56 | -0.0573 | +0.0099 | -0.0291 | +0.0489 |
| 109 | Callum McGregor | 6 | 33 | -0.1050 | +0.0098 | -0.0308 | +0.0504 |
| 110 | Robert Andrich | 28 | 187 | -0.0386 | -0.0027 | -0.0350 | +0.0297 |
| 111 | Vitor Machado Ferreira | 35 | 276 | -0.0415 | -0.0105 | -0.0399 | +0.0189 |

### Fixed claim rules, applied mechanically
- **Within-DM results:** no test meets both conditions. Two tests have Holm p < 0.05, PR2_keep → Y_F3 (5.5e-6) and PR2_fwd → net xG (0.023, negative), but the retention control on those rows is not positive (p = 0.97 and 0.92). No claim.
- **Praised list:** the smallest Holm-adjusted p across the 7 directional tests is 0.099, so no statement is allowed.
- **Stability:** PR2_keep and PR2_fwd fail the bar within deep midfielders (0.387 and 0.283 < 0.60).
- Task 42's first-attempt numbers are reported beside these (Sections 3 and 5).

## 4. Deviations from the brief
- **Spell end "other" (26) and "no end found" (3) are excluded.** The brief's list does not cover a teammate's on-ball event or P's own Clearance before the spell ends.
- **Step 3 retention control:** the brief says "Y = keep_spell over ALL his completed receptions". I applied it as in Task 42's corrected control: Y = each test row's keep_spell (so the control is on the same rows, as the claim rule requires), and S = the receiver's keep_spell rate over ALL his completed receptions in other matches (≥100 elsewhere).
- **Step 4:** Holm uses each test's reported two-sided p.
- **Step 5:** PFF "pressured" = Task 38's rec_pressure (the receiver's next event pressureType, or its initial-touch pressure, ≠ 'N'). A spell is ended by a teammate's possession event (excluded, 506) or an opposing possession event (keep 0). Nearest-opponent distance and the within-5 count are in metres (PFF units), not StatsBomb units. The setpieceType of the pass event stands in for play pattern.
- **Duel won:** an opponent's Tackle duel with outcome Won, Success In Play or Success Out. No pressured spell ended this way (0), because the possession id changes first.

## 5. Problems and surprises
- **R1 within deep midfielders fails for both measures** (0.39 and 0.28, n = 28). The all-player medians are also below 0.60.
- **The keep base rate falls from 0.776 (Task 42's first action) to 0.590** when judged at the end of the spell.
- **The deep-midfielder Step 3 rows have only 20 players.** On those rows, both retention controls are null (p = 0.97 and 0.92) while the all-player controls are strongly positive. Taken at face value, the DM rows cannot detect a known reception-level skill. The large PR2_keep → Y_F3 coefficient there (+4.13, above its MDE of 2.40) comes from rows where the design's sensitivity is not shown.
- **PR2_fwd → net xG within deep midfielders is negative** (−0.183, Holm p = 0.023).
- **Across all players, neither PR2 measure predicts Y_F3 or net xG** (p 0.46-0.87). Task 42's first-action PR_keep did predict Y_F3 across all players (p = 0.0014).
- **The two data sources agree at player level on WC2022** (r = 0.78, n = 55). The measure is not source-specific noise, but its within-DM stability across matches fails.

## 6. Questions for the research lead
- None yet.

## 7. Files produced
- `src/engine_v2/task43_spells.py`, `src/engine_v2/task43_steps3_6.py`, `src/pff/task43_pff_check.py`.
- `data/engine_v2_task43_steps3_6.json`, `data/pff_task43_step5.json` (not committed).
- `data/processed/engine_v2/task43_spells.parquet`, `task43_pressured_spells.parquet`, `data/engine_v2_task43_steps1_2.json` (not committed).
- Side effects: none else. No memory writes. JOURNAL.md and AGENTS.md untouched. Holdout untouched.
- Commits: brief 0eed693; interim page after Step 2 c5cc7d9; final ed3b7b5.

## 8. Confidence
The spell definition follows the brief, with the disclosed exclusions.
The weakest links:
- Stability rests on 28 deep midfielders.
- The within-DM results rows cover 20 players, on which the positive control is null.
