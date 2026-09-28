# Task 34: Reception quality (space at reception, context-adjusted)
Date: 2026-09-28
Status: COMPLETE (every section run; deviations and operationalizations in Section 4, questions in Section 6)

## Checklist
| Section | Status |
|---|---|
| Step 0 — brief committed alone | COMPLETE (5ac7246, committed by the research lead; brief not modified) |
| Memory gate (before Step 1, before Step 2) | COMPLETE (see Section 4 for how the second reading was taken) |
| Step 1 — the measure | COMPLETE |
| Step 2 R1 — stability | COMPLETE |
| Step 2 R2 — follows the player | COMPLETE |
| Step 2 R3 — predicts other matches | COMPLETE |
| Step 2 R4 — distinct from what we have | COMPLETE |
| Step 3 — deep-midfield table | COMPLETE |
| Interim commit after Step 1; final commit | COMPLETE |

## 1. Headline
R3 FAILS: out-of-match receiver RQ does not predict xG (H-O1 coef +0.025, 95% CI [−0.124, 0.173], p=0.74, n=373 of 584 team-matches), and under PH-O2 both coefficients are negative (goals −0.330, p=0.014).
R1 PASSES (deep-midfield reliability at 200 = 0.93, but only n=37 player-seasons), while R2 within deep midfielders is r_true 0.25, 95% CI [−0.01, 0.57], n=42; the all-player R2 (0.87, n=252) passes.
Under the brief's fixed rules this is "a stable trait, no evidence it affects results", and because PH-O2 is not positive the paper must say the R3 result cannot be separated from team quality.

## 2. What I did
- Step 0: brief `docs/specs/task-34-reception-quality.md` committed alone in 5ac7246 by the research lead, before Task 33 was read. Not modified.
- Memory gate readings: 2026-09-28 10:33 PDT, 72% free, ~6.09 GB available (before Step 1); 10:35 PDT, 71% free, ~5.99 GB (before Step 2). Both above 40% / 3 GB. Available = free+inactive+speculative pages from vm_stat.
- Step 1: `src/engine_v2/task34_step1_rq.py`. Step 2 and 3: `src/engine_v2/task34_step2_3.py`.
- Reproduce: `.venv/bin/python src/engine_v2/task34_step1_rq.py && .venv/bin/python src/engine_v2/task34_step2_3.py`
- Reused unchanged: `task32_step4.assign_roles`, `step8_regate.reliability_sweep`, `task26_step6_study_b.split_half_reliability` (and the PH-B2 recipe), `task32_step5.leave_one_match_out` / `standardize_and_join` / `fit_both`, `outcome_validation` unit builders, the `task26_step5_correlations` metric sources, `task28_step1_2.estimate_sigma2w_rho`, `task29_step1_2.dersimonian_laird` / `shrink` / `FIXED_LIST`.
- Checks: DM group n = 111 (asserted). Role counts equal Task 32's JSON exactly (asserted): CB 159, DM 111, FB 99, AM/W 87, CM 35, FW 27, MIXED 19. Folds are from `data/splits/cv_folds.csv`, restricted to the 292 options_ev_v4 matches. No existing file was changed.

## 3. Numbers

### Step 1 — the measure
- Matches: 292. Successful Ball Receipt* events: 271,830. With a 360 frame and an actor: **245,163 (90.19%)**. The brief expected about 93%.
- Players: 2,279. Team-contexts: 159. Frames with zero visible opponents: 165 (space = 15). Receptions at the 15 cap: 10.19%.
- f(context) pooled out-of-fold R^2: **0.2367** (n=245,163). Mean RQ overall: +0.032 (SD 3.77).

Mean RQ by zone (receiver x; defensive <40, middle 40-80, final ≥80):

| Zone | n | mean space | mean RQ | SE |
|---|---|---|---|---|
| defensive | 55,919 | 9.848 | −0.018 | 0.017 |
| middle | 128,196 | 7.838 | +0.041 | 0.011 |
| final | 61,048 | 5.565 | +0.061 | 0.012 |

Distributions:

| | mean | sd | q01 | q05 | q25 | q50 | q75 | q95 | q99 |
|---|---|---|---|---|---|---|---|---|---|
| space | 7.731 | 4.316 | 0.637 | 1.437 | 4.148 | 7.192 | 11.151 | 15.0 | 15.0 |
| f_oof | 7.698 | 2.162 | 2.406 | 4.067 | 6.529 | 7.534 | 8.820 | 11.678 | 13.311 |
| RQ | 0.032 | 3.771 | −7.667 | −5.913 | −2.776 | −0.143 | 2.815 | 6.468 | 7.982 |
| RQ_rel | 0.010 | 3.804 | −7.730 | −5.954 | −2.829 | −0.188 | 2.828 | 6.516 | 8.058 |

Visible opponents per frame: mean 8.37, median 9, q01 2.

### R1 — stability (reliability_sweep on RQ_rel, units = player × competition-season; median of 100 split-halves [p5, p95] not shown here; they are in the JSON)
The deep midfielders have receptions in all 111 cases (35,963 receptions).

| Group | n players | @100 (n units) | @200 (n units) | @300 (n units) |
|---|---|---|---|---|
| **Deep midfield (111)** | 111 | 0.878 (99) | **0.933 (37)** | 0.948 (20) |
| CB | 159 | 0.880 (174) | 0.921 (82) | 0.966 (38) |
| FB | 99 | 0.844 (106) | 0.890 (36) | 0.898 (15) |
| DM (role) | 111 | 0.878 (99) | 0.933 (37) | 0.948 (20) |
| CM | 35 | 0.768 (40) | 0.875 (19) | 0.895 (13) |
| AM/W | 87 | 0.789 (90) | 0.868 (23) | 0.953 (11) |
| FW | 27 | 0.856 (32) | 0.930 (10) | 0.960 (7) |
| MIXED | 19 | 0.878 (19) | 0.952 (8) | 0.985 (4) |
| All 537 with a role | 537 | 0.978 (560) | 0.987 (215) | 0.991 (108) |
| All receivers | 2,279 | 0.977 (580) | 0.987 (218) | 0.991 (111) |

**R1: PASS** (0.933 ≥ 0.60), but at 200 it rests on only 37 deep-midfield player-seasons. The DM role group and the 111 are the same players, so their rows are identical.

### R2 — follows the player across teams (PH-B2 recipe; sides = each player's two largest team-contexts with ≥50 receptions)

| Population | n players | rel side A | rel side B | r_obs [Fisher 95%] | r_true | 95% bootstrap CI |
|---|---|---|---|---|---|---|
| **All players (brief's population)** | 252 (80 have ≥3 contexts) | 0.973 | 0.961 | 0.842 [0.802, 0.875] | **0.871** | **[0.827, 0.909]** |
| Deep midfielders only | 42 (12 have ≥3) | 0.856 | 0.861 | 0.217 [−0.093, 0.489] | 0.253 | [−0.010, 0.571] |

No bootstrap draw was NaN, and none hit the ±1 cap.
**R2 (all players): PASS**, lower bound 0.827 > 0. Within deep midfielders the lower bound is −0.010, so it does not clear 0.

### R3 — predicts other matches (LINEUP over receptions, receiver's mean **RQ** from his other matches, ≥50 receptions elsewhere, units ≥70% coverage)
Units kept: 373 of 584 team-matches. Coverage quantiles over all 584: p10 0.17, p25 0.54, median 0.90, p75 0.997.

| Outcome | Spec | n | coef (per SD) | 95% CI | p |
|---|---|---|---|---|---|
| **xG** | **H-O1** | 373 | **+0.0249** | [−0.124, 0.173] | **0.743** |
| xG | PH-O2 (team-context FE) | 373 | −0.1514 | [−0.397, 0.094] | 0.227 |
| goals | H-O1 | 373 | −0.0153 | [−0.151, 0.120] | 0.825 |
| goals | PH-O2 | 373 | −0.3299 | [−0.594, −0.066] | 0.014 |

**R3: FAIL** (xG H-O1 p = 0.74). PH-O2 is not positive for either outcome.

### R4 — correlations with player mean RQ_rel within deep midfielders (report only; Pearson, Fisher 95% CI)

| Metric | n | r | 95% CI |
|---|---|---|---|
| Decision (v5 cross-fitted, player mean) | 111 | −0.187 | [−0.361, −0.001] |
| move_on_speed | 111 | −0.158 | [−0.334, 0.030] |
| median_time_on_ball | 111 | +0.541 | [0.394, 0.661] |
| completion rate | 111 | +0.196 | [0.010, 0.369] |
| receptions per team pass on pitch | 111 | +0.283 | [0.102, 0.446] |

### Step 3 — deep-midfield table (Task 29 method on RQ_rel per reception, units: yards)
- Within-group noise: sigma2_w = 11.79, rho = 0.0612.
- DerSimonian-Laird: mu_w = −1.044, tau^2 = 0.1824, **Q = 258.40 on 110 df, p = 5.8e-14** (rejects homogeneity).
- Intervals entirely **above** mu_w (6): Aurélien Tchouaméni, Kaan Ayhan, Leandro Paredes, Toni Kroos, Trent Alexander-Arnold, Robert Andrich.
- Intervals entirely **below** mu_w (8): Sergio Busquets, Vitor Machado Ferreira (Vitinha), Marco Verratti, Youri Tielemans, Casemiro, Amadou Onana, Mikel Merino, Moisés Caicedo.

The six named deep midfielders:

| Player | n receptions | rank /111 | raw | shrunken | 90% interval |
|---|---|---|---|---|---|
| Toni Kroos | 803 | 4 | −0.199 | −0.455 | [−0.842, −0.068] |
| Florian Grillitsch | 279 | 43 | −0.903 | −0.961 | [−1.415, −0.508] |
| Granit Xhaka | 3,214 | 61 | −1.066 | −1.064 | [−1.286, −0.842] |
| İlkay Gündoğan | 436 | 75 | −1.243 | −1.177 | [−1.582, −0.771] |
| Sergio Busquets | 2,669 | 97 | −1.390 | −1.355 | [−1.579, −1.131] |
| Marco Verratti | 3,324 | 101 | −1.441 | −1.404 | [−1.619, −1.190] |

Full table (rank, name, n, raw, shrunken, 90% interval), all 111:

| # | Player | n | raw | shrunk | lo90 | hi90 |
|---|---|---|---|---|---|---|
| 1 | Aurélien Djani Tchouaméni | 745 | 0.214 | −0.137 | −0.507 | 0.234 |
| 2 | Kaan Ayhan | 236 | 0.394 | −0.224 | −0.684 | 0.237 |
| 3 | Leandro Daniel Paredes | 776 | −0.168 | −0.363 | −0.695 | −0.032 |
| 4 | Toni Kroos | 803 | −0.199 | −0.455 | −0.842 | −0.068 |
| 5 | Trent Alexander-Arnold | 104 | 0.304 | −0.476 | −1.011 | 0.058 |
| 6 | Nemanja Gudelj | 102 | 0.147 | −0.545 | −1.081 | −0.010 |
| 7 | Robert Andrich | 1297 | −0.465 | −0.553 | −0.827 | −0.279 |
| 8 | Dixon Jair Arroyo Espinoza | 93 | 0.331 | −0.581 | −1.154 | −0.009 |
| 9 | Marten de Roon | 197 | −0.196 | −0.591 | −1.071 | −0.112 |
| 10 | Martín Zubimendi Ibáñez | 149 | −0.125 | −0.600 | −1.104 | −0.095 |
| 11 | Rúben Diogo Da Silva Neves | 304 | −0.372 | −0.623 | −1.052 | −0.194 |
| 12 | Leander Dendoncker | 160 | −0.065 | −0.631 | −1.165 | −0.097 |
| 13 | Samuel Moutoussamy | 115 | 0.117 | −0.636 | −1.202 | −0.070 |
| 14 | Jordan Veretout | 125 | 0.060 | −0.651 | −1.214 | −0.087 |
| 15 | Kristjan Asllani | 149 | 0.023 | −0.653 | −1.212 | −0.094 |
| 16 | Jhegson Sebastián Méndez Carabalí | 110 | 0.314 | −0.659 | −1.254 | −0.065 |
| 17 | Jonas Martin | 107 | 0.042 | −0.668 | −1.236 | −0.100 |
| 18 | Mario Götze | 93 | −0.106 | −0.689 | −1.243 | −0.135 |
| 19 | Woo-Young Jung | 148 | −0.207 | −0.695 | −1.232 | −0.159 |
| 20 | Benjamin Bourigeaud | 109 | −0.116 | −0.721 | −1.289 | −0.154 |
| 21 | Johan Gastien | 199 | −0.226 | −0.732 | −1.285 | −0.180 |
| 22 | Nampalys Mendy | 118 | −0.274 | −0.736 | −1.281 | −0.192 |
| 23 | Batista Mendy | 98 | −0.096 | −0.781 | −1.377 | −0.184 |
| 24 | Benjamin André | 138 | −0.357 | −0.795 | −1.356 | −0.234 |
| 25 | Saša Lukić | 240 | −0.571 | −0.797 | −1.282 | −0.312 |
| 26 | Mario Lemina | 102 | −0.410 | −0.827 | −1.396 | −0.257 |
| 27 | Nicolas Seiwald | 217 | −0.629 | −0.830 | −1.319 | −0.341 |
| 28 | Wataru Endo | 141 | −0.476 | −0.837 | −1.398 | −0.277 |
| 29 | Emre Can | 99 | −0.639 | −0.858 | −1.375 | −0.341 |
| 30 | Enzo Fernandez | 391 | −0.729 | −0.861 | −1.316 | −0.406 |
| 31 | Pedro Chirivella Burgos | 183 | −0.570 | −0.865 | −1.420 | −0.311 |
| 32 | Timi Elšnik | 70 | −0.595 | −0.887 | −1.453 | −0.321 |
| 33 | Azor Matusiwa | 89 | −0.502 | −0.896 | −1.495 | −0.297 |
| 34 | Nadiem Amiri | 127 | −0.757 | −0.899 | −1.392 | −0.405 |
| 35 | Rodrigo Bentancur Colmán | 112 | −0.641 | −0.903 | −1.470 | −0.337 |
| 36 | Pierre-Emile Højbjerg | 704 | −0.852 | −0.906 | −1.278 | −0.534 |
| 37 | Teun Koopmeiners | 88 | −0.714 | −0.911 | −1.454 | −0.368 |
| 38 | Ádám Nagy | 119 | −0.761 | −0.914 | −1.429 | −0.398 |
| 39 | Ivan Ilić | 130 | −0.739 | −0.920 | −1.461 | −0.379 |
| 40 | Celso Borges Mora | 75 | −0.688 | −0.930 | −1.510 | −0.351 |
| 41 | Tomáš Souček | 218 | −0.851 | −0.935 | −1.399 | −0.471 |
| 42 | Axel Witsel | 293 | −0.865 | −0.943 | −1.407 | −0.479 |
| 43 | Florian Grillitsch | 279 | −0.903 | −0.961 | −1.415 | −0.508 |
| 44 | Adam Gnezda Čerin | 106 | −0.849 | −0.968 | −1.516 | −0.419 |
| 45 | Tijjani Reijnders | 244 | −0.906 | −0.972 | −1.456 | −0.487 |
| 46 | Ander Herrera Agüera | 257 | −0.921 | −0.973 | −1.430 | −0.517 |
| 47 | Sofyan Amrabat | 219 | −0.925 | −0.979 | −1.455 | −0.504 |
| 48 | Declan Rice | 916 | −0.981 | −0.994 | −1.320 | −0.668 |
| 49 | Bruno Guimarães Rodriguez Moura | 102 | −0.931 | −1.005 | −1.575 | −0.436 |
| 50 | Joey Veerman | 124 | −1.009 | −1.028 | −1.542 | −0.514 |
| 51 | Youssouf Fofana | 191 | −1.019 | −1.029 | −1.476 | −0.583 |
| 52 | Tyler Adams | 181 | −1.012 | −1.030 | −1.561 | −0.500 |
| 53 | Mohammed Kanoo | 104 | −1.009 | −1.032 | −1.601 | −0.463 |
| 54 | Seko Fofana | 163 | −1.026 | −1.037 | −1.594 | −0.480 |
| 55 | Giorgi Kochorashvili | 149 | −1.040 | −1.042 | −1.561 | −0.523 |
| 56 | Ellyes Joris Skhiri | 133 | −1.042 | −1.043 | −1.567 | −0.520 |
| 57 | Marcelo Brozović | 745 | −1.047 | −1.046 | −1.417 | −0.675 |
| 58 | Jorge Luiz Frello Filho | 634 | −1.054 | −1.050 | −1.454 | −0.647 |
| 59 | Salis Abdul Samed | 123 | −1.067 | −1.053 | −1.596 | −0.510 |
| 60 | Corentin Tolisso | 106 | −1.094 | −1.064 | −1.612 | −0.515 |
| 61 | Granit Xhaka | 3214 | −1.066 | −1.064 | −1.286 | −0.842 |
| 62 | Maxence Caqueret | 100 | −1.108 | −1.066 | −1.636 | −0.496 |
| 63 | Angel Gomes | 120 | −1.117 | −1.070 | −1.635 | −0.505 |
| 64 | Exequiel Alejandro Palacios | 1509 | −1.081 | −1.075 | −1.361 | −0.789 |
| 65 | Aaron Mooy | 142 | −1.155 | −1.090 | −1.628 | −0.552 |
| 66 | Grzegorz Krychowiak | 149 | −1.188 | −1.114 | −1.618 | −0.609 |
| 67 | Remo Freuler | 480 | −1.156 | −1.123 | −1.502 | −0.745 |
| 68 | In-Beom Hwang | 184 | −1.246 | −1.131 | −1.661 | −0.601 |
| 69 | Callum McGregor | 172 | −1.222 | −1.133 | −1.631 | −0.634 |
| 70 | Boubacar Kamara | 124 | −1.381 | −1.141 | −1.734 | −0.548 |
| 71 | Laurent Abergel | 135 | −1.319 | −1.143 | −1.705 | −0.582 |
| 72 | Hakan Çalhanoğlu | 322 | −1.221 | −1.145 | −1.605 | −0.684 |
| 73 | Atakan Karazor | 90 | −1.473 | −1.161 | −1.760 | −0.563 |
| 74 | Kristoffer Olsson | 109 | −1.370 | −1.172 | −1.719 | −0.624 |
| 75 | İlkay Gündoğan | 436 | −1.243 | −1.177 | −1.582 | −0.771 |
| 76 | András Schäfer | 159 | −1.330 | −1.191 | −1.681 | −0.701 |
| 77 | Jackson Irvine | 94 | −1.455 | −1.200 | −1.753 | −0.646 |
| 78 | Jerdy Schouten | 250 | −1.350 | −1.205 | −1.689 | −0.721 |
| 79 | Jakub Moder | 98 | −1.444 | −1.210 | −1.747 | −0.673 |
| 80 | Hidemasa Morita | 126 | −1.519 | −1.213 | −1.777 | −0.650 |
| 81 | Thomas Teye Partey | 142 | −1.515 | −1.216 | −1.776 | −0.655 |
| 82 | João Palhinha | 216 | −1.371 | −1.234 | −1.689 | −0.779 |
| 83 | Aïssa Bilal Laïdouni | 134 | −1.511 | −1.252 | −1.775 | −0.729 |
| 84 | Xaver Schlager | 168 | −1.484 | −1.262 | −1.761 | −0.762 |
| 85 | Kalvin Phillips | 280 | −1.421 | −1.272 | −1.714 | −0.830 |
| 86 | Stanislav Lobotka | 215 | −1.525 | −1.276 | −1.782 | −0.771 |
| 87 | Miralem Pjanić | 579 | −1.356 | −1.277 | −1.630 | −0.924 |
| 88 | Christian Nørgaard | 110 | −1.510 | −1.278 | −1.774 | −0.783 |
| 89 | Joan Jordán Moreno | 109 | −1.883 | −1.281 | −1.876 | −0.686 |
| 90 | Albin Ekdal | 91 | −1.678 | −1.283 | −1.837 | −0.728 |
| 91 | Paul Pogba | 242 | −1.597 | −1.291 | −1.814 | −0.768 |
| 92 | Serhii Sydorchuk | 145 | −1.560 | −1.292 | −1.798 | −0.786 |
| 93 | Ethan Ampadu | 119 | −1.639 | −1.303 | −1.831 | −0.774 |
| 94 | Taras Stepanenko | 124 | −1.710 | −1.312 | −1.855 | −0.770 |
| 95 | Kobbie Mainoo | 178 | −1.597 | −1.320 | −1.817 | −0.824 |
| 96 | Billy Gilmour | 127 | −1.785 | −1.344 | −1.886 | −0.803 |
| 97 | Sergio Busquets i Burgos | 2669 | −1.390 | −1.355 | −1.579 | −1.131 |
| 98 | Lucas Tolentino Coelho de Lima | 206 | −1.718 | −1.367 | −1.874 | −0.860 |
| 99 | Joe Allen | 106 | −1.772 | −1.370 | −1.892 | −0.848 |
| 100 | Vitor Machado Ferreira | 1691 | −1.432 | −1.383 | −1.633 | −1.132 |
| 101 | Marco Verratti | 3324 | −1.441 | −1.404 | −1.619 | −1.190 |
| 102 | Leon Goretzka | 194 | −1.741 | −1.430 | −1.899 | −0.960 |
| 103 | Thomas Delaney | 231 | −1.685 | −1.430 | −1.873 | −0.988 |
| 104 | N'Golo Kanté | 468 | −1.639 | −1.434 | −1.847 | −1.022 |
| 105 | Morten Hjulmand | 187 | −2.103 | −1.445 | −1.998 | −0.891 |
| 106 | Alex Král | 77 | −2.120 | −1.484 | −2.024 | −0.943 |
| 107 | Youri Tielemans | 321 | −1.785 | −1.511 | −1.938 | −1.085 |
| 108 | Carlos Henrique Casimiro | 263 | −2.028 | −1.564 | −2.047 | −1.082 |
| 109 | Amadou Onana | 285 | −2.024 | −1.595 | −2.060 | −1.130 |
| 110 | Mikel Merino Zazón | 189 | −2.156 | −1.633 | −2.115 | −1.152 |
| 111 | Moisés Isaac Caicedo Corozo | 111 | −2.875 | −1.683 | −2.250 | −1.116 |

### Fixed claim rules (brief), applied mechanically
- R1 passes and R3 fails, so the claim allowed is: "a stable trait, no evidence it affects results."
- R2 (all players) r_true 0.871 [0.827, 0.909]. Deep midfielders only: 0.253 [−0.010, 0.571].
- PH-O2 is not positive (xG −0.151, goals −0.330), so the paper must say the R3 result cannot be separated from team quality.

## 4. Deviations from the brief
- **R2 context pairing.** PH-B2 compares a club side with an international side. The brief says "correlation between contexts" for players with ≥2 contexts. I used each player's two largest ≥50-reception team-contexts (ties broken by context key). Contexts beyond the second were not used (80 players have ≥3). See Q1.
- **R2 extra population.** The brief's population is all players. I also ran R2 on the deep-midfield subset (n=42). This was not requested; it was reported because the other tests are within deep midfielders. The PASS call uses the all-player result only.
- **R1 extra rows.** "All roles" was run two ways: the 537 role-assigned players and all 2,279 receivers. MIXED was also reported. None of these affects the PASS call, which uses the 111.
- **R3 uses RQ, not RQ_rel**, because the brief's R3 text says "mean RQ" while every other test uses RQ_rel. Taken literally; see Q2.
- **Zero-visible-opponent frames** (165) set to space = 15. See Q3.
- **opp_ctx_mean_space** is missing for 11,605 receptions: 22 opponent contexts appear in only one match. Left missing; XGBoost's native missing handling was used. See Q5.
- **XGBoost parameters** the brief does not name were left at library defaults.
- **Opponents** = frame rows with teammate == False, including the goalkeeper.
- **R4 "receptions per team pass on the pitch":** numerator = the player's Step 1 sample receptions (360 frame present). Denominator = his team's Pass events with event index between his first and last event in each match, summed over matches. See Q4.
- **R4 inputs** move_on_speed, median_time_on_ball and completion rate are built exactly as in `task26_step5_correlations.py` (player-level pooling from its source files). I did not check which matches those source files cover.
- **Memory gate before Step 2:** the reading was taken in the same shell command that launched Step 2, so it was recorded but could not block the run. It read 71% / ~5.99 GB, above the floor, so no step ran below the gate.

## 5. Problems and surprises
- **Frame coverage is 90.19%, not ~93%.**
- **Mean RQ by zone is not zero:** final +0.061 (≈5 SE), middle +0.041 (≈3.7 SE), defensive −0.018 (≈1 SE). This is small against SD 3.77. Cross-fitting does not force per-zone means to zero.
- **R1's high reliability may be role or sub-role, not a player trait.** RQ_rel is measured against all teammates in the context, so a player's systematic position (for example a deeper holding 6 against a more advanced 8 in the "DM" label) moves his RQ_rel for every reception. All-roles reliability is 0.98, above every within-role value (0.87-0.93 at 200), which shows how much role alone contributes. Within deep midfielders, R2 falls to 0.25 [−0.01, 0.57]. Taken at face value, R1's pass would suggest a player trait. The R2 drop from 0.87 (all) to 0.25 (DM) says most of the cross-team persistence in the all-player R2 is role persistence, the same pattern Task 27 Step 3 found for Decision.
- **The deep-midfield group mean RQ_rel is −1.04 yards**, meaning deep midfielders receive in less space than their teammates. The players whose intervals sit above the mean, and so receive in the most space, include Kroos and Alexander-Arnold. The players whose intervals sit below include Busquets and Vitinha, the only two players whose Decision intervals cleared the group mean in Task 29 (docs/results/29-deep-midfield-noise.md, 2026-09-27). At face value this contradicts the brief's premise ("elite deep midfielders are always free") for those two players.
- **R4:** RQ_rel correlates −0.19 [−0.36, −0.001] with Decision and +0.54 [0.39, 0.66] with median time on ball. A player who receives in more space holds the ball longer, so the two may partly measure the same thing.
- **R3 PH-O2 goals coefficient is negative and significant** (−0.330, p=0.014). Taken at face value, within a team-context, lineups with higher out-of-match RQ score fewer goals. The unit count is 373, and 211 of 584 team-matches were dropped by the 70% coverage rule.
- **R1 at 200 uses 37 deep-midfield player-seasons**, and at 300 only 20.
- 10.2% of receptions sit at the 15 cap, so space is censored at the top.
- 360 frames show only the camera's visible area, so "nearest visible opponent" overstates space whenever the true nearest opponent is off-camera.

## 6. Questions for the research lead
- **Q1 (R2):** Which two contexts should be compared for a player with ≥3? I used the two largest. Alternatives: every pair, club versus international (as PH-B2), or chronological order. The PASS/FAIL could change for the DM subset; the all-player lower bound is far from 0.
- **Q2 (R3):** The brief says "mean RQ" in R3 and RQ_rel everywhere else. Is RQ intended? RQ_rel was not run for R3.
- **Q3:** Zero-visible-opponent frames (165): keep at 15 or drop?
- **Q4 (R4):** Should the receptions-per-team-pass numerator be all successful receptions rather than only 360-present ones?
- **Q5:** 22 single-match opponent contexts: is leaving opp_ctx_mean_space missing acceptable?
- **Q6:** Given the role and sub-role concern in Section 5, should R1 and R2 be read as they stand, or is a within-sub-role check wanted? I have not run one.

## 7. Files produced
- `src/engine_v2/task34_step1_rq.py`: Step 1 (receptions, f(context), RQ, RQ_rel).
- `src/engine_v2/task34_step2_3.py`: R1-R4 and the Step 3 table.
- `data/processed/engine_v2/task34_receptions.parquet`: per-reception table (not committed).
- `data/engine_v2_task34_step1.json`, `data/engine_v2_task34_step2_3.json`: summaries (not committed).
- `data/processed/engine_v2/task34_dm_shrunk.parquet`: Step 3 table (not committed).
- This page.
- Commits: brief 5ac7246 (research lead); Step 1 interim bcec9c8; final commit recorded in a follow-up commit.
- Side effects: none beyond the files above. No memory writes. docs/JOURNAL.md and AGENTS.md had uncommitted changes before this task; they were left untouched and not committed.

## 8. Confidence
The code path is mechanical reuse of existing functions, and role counts and the DM group match earlier tasks exactly. The weakest link is interpretation of R1: its pass rests on 37 player-seasons at 200, and R2 within deep midfielders does not clear zero. R1's stability therefore cannot be separated from positional or sub-role effects with the tests the brief specified. R3 fails outright.
