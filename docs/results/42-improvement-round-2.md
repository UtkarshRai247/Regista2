# Task 42: Improvement round 2: role-appropriate outcomes and press resistance (study sample only)
Date: 2026-09-28
Status: COMPLETE (every section run; interim page after Step 1 committed in 99a4b82; deviations in Section 4)

## Checklist
| Section | Status |
|---|---|
| Step 0 — brief committed alone | COMPLETE (107bed0, by the research lead) |
| Memory gate | COMPLETE (54% / 4.52 GB at 16:01 before Step 1; 47% / 4.38 GB at 16:03 before Step 2; 51% / 4.33 GB at 16:04 before Step 3) |
| Step 1 (A) — Y_F3 / Y_SHOT P-tests | COMPLETE |
| Step 2 (B) — press resistance: measure, R1, R2, R3, table | COMPLETE |
| Step 3 (C) — progressive availability: R1, R2, praised list | COMPLETE |
| Claim family (Holm, 11 tests; plus Task 41's 12) | COMPLETE |
| Commits after Step 1 and at the end | COMPLETE |

## 1. Headline
Study sample only. **No within-deep-midfielder results claim is allowed under the fixed rule.** Across the 11 within-DM tests, the smallest Holm p is 0.19 (Step 2, PR_keep → Y_F3, raw p = 0.017, 22 players), and that test's positive control on the same rows is not positive (−0.54 pp, p = 0.67).
- **Stability:** press resistance fails R1 within deep midfielders (median 0.25 at 100 pressured receptions, only 7 player-seasons). Progressive availability passes R1 (0.67, 28 players).
- **Across all players:** PR_keep predicts Y_F3 (+1.50 pp per 100 pressured receptions per SD, p = 0.0014, 150 players, control positive).
- **Praised list:** on PR_keep, T = +0.69 with two-sided p = 0.014, in the pre-declared direction (higher), from 11 of the 13 players present.

## 2. What I did
- Step 0: the brief was committed alone by the research lead in 107bed0.
- **Reception-unit control:** before running, I asked which positive control reception-unit tests should use. The author chose a retention control. The research lead then fixed it in a correction to the brief (4d6405a, 15:59 PDT):
  - Y = the receiver's next on-ball action keeps the ball (PR_keep's definition);
  - S = his raw retention rate over ALL his completed receptions in his OTHER matches, ≥100 elsewhere;
  - g refit on the same reception features;
  - for PFF (Step 3), retention comes from PFF's next possession event by the receiver.
- **Superseded control run:** the correction landed before the Step 1 run (16:01), but I did not re-read the brief. The first run of Steps 1-2 used S = retention over Task 34's frame-present receptions (Step 1) and over pressured receptions only with a ≥50 floor (Step 2), and had no PFF control. That version is in the interim commit 99a4b82 and the first final commit c8ec94d. All three steps were then re-run with the corrected control (16:07 PDT; memory gate 56% / 4.94 GB). The numbers on this page are from that re-run. The test coefficients did not change; only the control columns did.
- `.venv/bin/python src/engine_v2/task42_step1.py`:
  1. Builds Y_F3 / Y_SHOT and receipt next-action outcomes per match (`src/engine_v2/task42_outcomes.py`).
  2. Rebuilds Task 35's pass table and asserts Task 35 (a) reproduces exactly.
  3. Re-runs Task 26 Step 2's tempo computation with outputs redirected to new Task 42 files. Its residuals are asserted identical to the stored v2 files.
  4. Takes S from `task35_ptest.add_s` (Decision, RQ_rel, completion, retention) and Task 39's `s_for_rows` (MOVE_ON_SPEED).
  5. Refits g per outcome with `task35_ptest.crossfit_g`, and fits with `task35_ptest.fe_fit`.
- `.venv/bin/python -W ignore src/engine_v2/task42_step2.py`:
  - Pressured receptions are completed receipts with a 360 frame and actor, where the nearest visible opponent (recomputed, uncapped) is ≤ 3 units OR `under_pressure` is set. keep/fwd come from Step 1's receipt-action table.
  - Baseline: cross-fitted XGBoost classifier on Task 35's folds with the brief's settings and context features.
  - R1: `step8_regate.reliability_sweep`.
  - R2: `task35_ptest.fe_fit`, with S = other-match mean PR (≥50 elsewhere) and g refit on Task 35 (d)'s reception features, plus the retention control.
  - R3: Task 41's `perm_test`.
  - Table: Task 29's method.
- `.venv/bin/python -W ignore src/pff/task42_av_prog.py`:
  - Re-derives each Task 38 moment's teammate and ball x in the attacking frame. d_ball is recomputed and asserted equal to Task 38's.
  - Refits the baseline with `availability.fit_oof`, then runs `availability_tests.r1`/`r2` and Task 41's `perm_test`.
- `.venv/bin/python src/engine_v2/task42_family.py` applies the claim rule.
- Reproduce: Step 1, Step 2, Step 3, then family, in that order.

## 3. Numbers

### Step 1 — base rates (Y_F3 only on units starting at x < 80)

| Units | n | units eligible for Y_F3 | Y_F3 rate | Y_SHOT rate |
|---|---|---|---|---|
| Passes, all | 239,588 | 179,021 | 0.677 | 0.161 |
| Passes, deep midfielders | 38,677 | 31,275 | 0.724 | 0.166 |
| Receptions, all | 241,222 | 180,683 | 0.664 | 0.169 |
| Receptions, deep midfielders | 35,536 | 29,002 | 0.726 | 0.171 |

- Receipt next-action outcomes: 271,830 completed receipts. Next action: Carry 228,878; Pass 37,856; Shot 2,672; Miscontrol 1,473; Dispossessed 141; Dribble 150; none found 660.
- Retention (keep) rate on Task 34 receptions: 0.938 (n = 240,776).
- Reception g out-of-fold R^2: Y_F3 0.169, Y_SHOT 0.078, keep 0.236.

### Step 1 — P-tests (coefficient = percentage points of the outcome per 100 units per SD of S; team-match FE, role FE, SE by player)

| Group | S (unit) | Y | n units | players | coef per 100 per SD | 95% CI | p | MDE | control on same rows: coef, 95% CI, p |
|---|---|---|---|---|---|---|---|---|---|
| all | v5 Decision (passes) | Y_F3 | 126,936 | 440 | +0.232 | [−0.208, 0.672] | 0.30 | 0.628 | completion +1.768 [1.434, 2.102], 3e-25 |
| all | MOVE_ON_SPEED (passes) | Y_F3 | 116,536 | 327 | −0.174 | [−0.479, 0.131] | 0.26 | 0.436 | completion +1.766 [1.425, 2.107], 3e-24 |
| all | RQ_rel (receptions) | Y_F3 | 124,095 | 445 | +0.500 | [−0.269, 1.269] | 0.20 | 1.098 | retention +0.792 [0.539, 1.045], 9e-10 |
| all | v5 Decision (passes) | Y_SHOT | 168,855 | 440 | +0.014 | [−0.317, 0.345] | 0.93 | 0.473 | completion +2.201 [1.798, 2.604], 9e-27 |
| all | MOVE_ON_SPEED (passes) | Y_SHOT | 154,116 | 328 | −0.011 | [−0.231, 0.210] | 0.93 | 0.315 | completion +2.190 [1.740, 2.640], 1e-21 |
| all | RQ_rel (receptions) | Y_SHOT | 166,087 | 446 | +0.390 | [−0.145, 0.925] | 0.15 | 0.764 | retention +0.496 [0.285, 0.707], 4e-6 |
| DM | v5 Decision (passes) | Y_F3 | 27,388 | 88 | +0.454 | [−0.407, 1.315] | 0.30 | 1.230 | completion +0.760 [0.375, 1.145], 1e-4 |
| DM | MOVE_ON_SPEED (passes) | Y_F3 | 24,711 | 60 | +0.455 | [−0.553, 1.462] | 0.38 | 1.440 | completion +0.796 [0.504, 1.088], 9e-8 |
| DM | RQ_rel (receptions) | Y_F3 | 24,360 | 78 | −0.108 | [−0.601, 0.385] | 0.67 | 0.704 | retention −0.035 [−0.244, 0.175], 0.75 |
| DM | v5 Decision (passes) | Y_SHOT | 33,889 | 88 | −0.393 | [−0.970, 0.184] | 0.18 | 0.825 | completion +0.626 [0.115, 1.137], 0.016 |
| DM | MOVE_ON_SPEED (passes) | Y_SHOT | 30,680 | 61 | +0.110 | [−0.417, 0.638] | 0.68 | 0.754 | completion +0.545 [0.105, 0.985], 0.015 |
| DM | RQ_rel (receptions) | Y_SHOT | 29,940 | 79 | +0.264 | [−0.214, 0.742] | 0.28 | 0.683 | retention −0.259 [−0.600, 0.082], 0.14 |

### Step 2 (B) — press resistance: the measure
- Completed receipts with frame and actor: 245,163.
- Pressured: 42,301. By distance ≤ 3: 37,928. By the under_pressure flag: 18,140.
- No next action: 93, excluded, leaving 42,208 for the baseline and R1.
- 40,732 of these have value-model origin features, which R2's g needs.
- Base rates: PR_keep outcome (keep) 0.776; PR_fwd outcome (fwd) 0.110.
- Baseline out-of-fold AUC: keep 0.716; fwd 0.587.

### Step 2 — R1 (deep midfielders; units = player × competition-season; median [p5, p95])

| Measure | @50 (units) | @100 (units) | @150 (units) | PASS (≥ 0.60 at 100) |
|---|---|---|---|---|
| PR_keep | 0.413 [−0.141, 0.747] (15) | **0.249** [−0.546, 0.711] (7) | 0.249 (7) | FAIL |
| PR_fwd | 0.299 [−0.598, 0.726] (15) | **0.268** [−0.968, 0.751] (7) | 0.268 (7) | FAIL |

### Step 2 — R2 (unit = pressured reception; S = other-match mean PR, ≥50 pressured receptions elsewhere; retention control on the same rows)
Coefficients are in percentage points (Y_F3) or xG (net xG) per 100 pressured receptions per SD.

| Group | S | Y | n | players | team-matches | coef | 95% CI | p | MDE | control coef [95% CI], p |
|---|---|---|---|---|---|---|---|---|---|---|
| all | PR_keep | Y_F3 | 11,110 | 150 | 406 | **+1.497** | [0.578, 2.415] | **0.0014** | 1.313 | +2.835 [1.799, 3.871], 8e-8 |
| all | PR_keep | net xG | 19,833 | 150 | 409 | +0.095 | [−0.023, 0.213] | 0.115 | 0.169 | +0.960 [0.118, 1.803], 0.026 |
| all | PR_fwd | Y_F3 | 11,110 | 150 | 406 | −0.038 | [−0.967, 0.890] | 0.94 | 1.326 | +2.835 [1.799, 3.871], 8e-8 |
| all | PR_fwd | net xG | 19,833 | 150 | 409 | −0.011 | [−0.116, 0.094] | 0.84 | 0.150 | +0.960 [0.118, 1.803], 0.026 |
| DM | PR_keep | Y_F3 | 2,440 | 22 | 250 | +2.911 | [0.517, 5.306] | 0.017 | 3.421 | −0.538 [−2.969, 1.894], 0.67 |
| DM | PR_keep | net xG | 3,160 | 22 | 254 | +0.032 | [−0.043, 0.107] | 0.40 | 0.107 | +0.004 [−2.766, 2.774], 1.00 |
| DM | PR_fwd | Y_F3 | 2,440 | 22 | 250 | +1.124 | [−3.146, 5.395] | 0.61 | 6.101 | −0.538 [−2.969, 1.894], 0.67 |
| DM | PR_fwd | net xG | 3,160 | 22 | 254 | −0.119 | [−0.395, 0.157] | 0.40 | 0.394 | +0.004 [−2.766, 2.774], 1.00 |

### Step 2 — R3 (praised list, Task 41's method; ≥50 pressured receptions; 147 qualifying players; 11 of 13 present)
Kroos and Verratti are present, as are 9 of the other 11 names; Grillitsch and Shaparenko are absent.

| Measure | T | p (two-sided) | Pre-declared direction |
|---|---|---|---|
| PR_keep | **+0.687** | **0.014** | higher, met |
| PR_fwd | −0.224 | 0.43 | higher, not met |

z-scores:
- **PR_keep:** De Bruyne +0.16, Verratti +0.73, Xhaka +0.05, Busquets +0.42, Modrić +0.09, Kroos +0.69, Kimmich +1.48, Rodri +1.53, de Jong +1.46, Gündoğan +0.52, Pedri +0.43.
- **PR_fwd:** De Bruyne +2.32, Verratti −0.23, Xhaka −0.55, Busquets −0.16, Modrić −0.36, Kroos −1.35, Kimmich +1.08, Rodri −2.56, de Jong −0.61, Gündoğan +0.38, Pedri −0.42.

### Step 2 — tables (Task 29's method, within the 111; output only)
- **PR_keep:** mu_w = +0.0576, tau^2 = 0.00129, **Q = 186.6 on 110 df, p = 7e-6**.
  - Above: Ander Herrera Agüera, Exequiel Alejandro Palacios, Marco Verratti.
  - Below: Aurélien Djani Tchouaméni, Pierre-Emile Højbjerg, Remo Freuler.
- **PR_fwd:** mu_w = −0.0014, tau^2 = 0.00006, Q = 112.9 on 110 df, p = 0.41. None above or below.

PR_keep (all 111):

| # | Player | matches | pressured receptions | raw | shrunken | 90% low | 90% high |
|---|---|---|---|---|---|---|---|
| 1 | Ander Herrera Agüera | 8 | 47 | +0.1770 | +0.1068 | +0.0616 | +0.1521 |
| 2 | Aïssa Bilal Laïdouni | 5 | 29 | +0.1912 | +0.0980 | +0.0487 | +0.1473 |
| 3 | Leandro Daniel Paredes | 15 | 72 | +0.1265 | +0.0933 | +0.0523 | +0.1343 |
| 4 | Exequiel Alejandro Palacios | 25 | 244 | +0.0960 | +0.0877 | +0.0603 | +0.1151 |
| 5 | Marco Verratti | 47 | 539 | +0.0903 | +0.0867 | +0.0671 | +0.1063 |
| 6 | Christian Nørgaard | 8 | 20 | +0.1730 | +0.0841 | +0.0323 | +0.1359 |
| 7 | Miralem Pjanić | 15 | 90 | +0.0986 | +0.0811 | +0.0426 | +0.1197 |
| 8 | Morten Hjulmand | 3 | 39 | +0.1199 | +0.0805 | +0.0336 | +0.1275 |
| 9 | Seko Fofana | 3 | 33 | +0.1234 | +0.0793 | +0.0310 | +0.1277 |
| 10 | Boubacar Kamara | 2 | 19 | +0.1523 | +0.0785 | +0.0264 | +0.1306 |
| 11 | Giorgi Kochorashvili | 5 | 32 | +0.1220 | +0.0784 | +0.0299 | +0.1270 |
| 12 | Wataru Endo | 3 | 16 | +0.1596 | +0.0773 | +0.0242 | +0.1303 |
| 13 | Nadiem Amiri | 6 | 21 | +0.1381 | +0.0768 | +0.0253 | +0.1283 |
| 14 | Vitor Machado Ferreira | 35 | 275 | +0.0813 | +0.0767 | +0.0506 | +0.1028 |
| 15 | Saša Lukić | 6 | 24 | +0.1177 | +0.0735 | +0.0228 | +0.1241 |
| 16 | Jakub Moder | 4 | 21 | +0.1214 | +0.0728 | +0.0213 | +0.1243 |
| 17 | Sergio Busquets i Burgos | 44 | 419 | +0.0752 | +0.0728 | +0.0509 | +0.0947 |
| 18 | Toni Kroos | 11 | 59 | +0.0883 | +0.0720 | +0.0289 | +0.1150 |
| 19 | Corentin Tolisso | 4 | 13 | +0.1443 | +0.0717 | +0.0177 | +0.1257 |
| 20 | Tyler Adams | 4 | 20 | +0.1182 | +0.0715 | +0.0197 | +0.1234 |
| 21 | Jorge Luiz Frello Filho | 10 | 86 | +0.0815 | +0.0711 | +0.0320 | +0.1101 |
| 22 | Axel Witsel | 7 | 26 | +0.1041 | +0.0706 | +0.0205 | +0.1207 |
| 23 | Jerdy Schouten | 6 | 36 | +0.0947 | +0.0706 | +0.0230 | +0.1182 |
| 24 | Lucas Tolentino Coelho de Lima | 5 | 52 | +0.0861 | +0.0701 | +0.0258 | +0.1144 |
| 25 | Kalvin Phillips | 9 | 48 | +0.0871 | +0.0699 | +0.0249 | +0.1150 |
| 26 | Pedro Chirivella Burgos | 3 | 22 | +0.1055 | +0.0694 | +0.0182 | +0.1207 |
| 27 | İlkay Gündoğan | 11 | 67 | +0.0800 | +0.0688 | +0.0271 | +0.1105 |
| 28 | Ellyes Joris Skhiri | 5 | 19 | +0.1081 | +0.0688 | +0.0167 | +0.1209 |
| 29 | Dixon Jair Arroyo Espinoza | 3 | 9 | +0.1419 | +0.0676 | +0.0122 | +0.1230 |
| 30 | Stanislav Lobotka | 5 | 36 | +0.0855 | +0.0674 | +0.0198 | +0.1150 |
| 31 | Leander Dendoncker | 4 | 11 | +0.1095 | +0.0649 | +0.0102 | +0.1196 |
| 32 | Thomas Teye Partey | 3 | 17 | +0.0903 | +0.0642 | +0.0115 | +0.1170 |
| 33 | Declan Rice | 19 | 99 | +0.0682 | +0.0639 | +0.0264 | +0.1014 |
| 34 | Moisés Isaac Caicedo Corozo | 3 | 26 | +0.0789 | +0.0636 | +0.0135 | +0.1137 |
| 35 | Carlos Henrique Casimiro | 6 | 54 | +0.0697 | +0.0630 | +0.0191 | +0.1069 |
| 36 | Azor Matusiwa | 2 | 17 | +0.0831 | +0.0628 | +0.0100 | +0.1155 |
| 37 | Martín Zubimendi Ibáñez | 5 | 20 | +0.0794 | +0.0626 | +0.0108 | +0.1144 |
| 38 | Kristjan Asllani | 3 | 23 | +0.0762 | +0.0623 | +0.0114 | +0.1133 |
| 39 | Robert Andrich | 28 | 185 | +0.0639 | +0.0622 | +0.0318 | +0.0927 |
| 40 | Timi Elšnik | 4 | 14 | +0.0812 | +0.0617 | +0.0080 | +0.1154 |
| 41 | Thomas Delaney | 8 | 61 | +0.0661 | +0.0616 | +0.0189 | +0.1044 |
| 42 | Serhii Sydorchuk | 4 | 26 | +0.0701 | +0.0611 | +0.0110 | +0.1112 |
| 43 | Batista Mendy | 2 | 14 | +0.0777 | +0.0611 | +0.0074 | +0.1148 |
| 44 | Sofyan Amrabat | 6 | 26 | +0.0697 | +0.0610 | +0.0109 | +0.1111 |
| 45 | Salis Abdul Samed | 4 | 17 | +0.0675 | +0.0596 | +0.0069 | +0.1123 |
| 46 | Nampalys Mendy | 4 | 20 | +0.0653 | +0.0594 | +0.0076 | +0.1112 |
| 47 | Atakan Karazor | 2 | 12 | +0.0686 | +0.0593 | +0.0049 | +0.1136 |
| 48 | Florian Grillitsch | 7 | 35 | +0.0615 | +0.0589 | +0.0111 | +0.1068 |
| 49 | Tijjani Reijnders | 6 | 30 | +0.0613 | +0.0587 | +0.0097 | +0.1078 |
| 50 | Rúben Diogo Da Silva Neves | 7 | 19 | +0.0621 | +0.0586 | +0.0065 | +0.1107 |
| 51 | Kristoffer Olsson | 4 | 15 | +0.0607 | +0.0582 | +0.0048 | +0.1115 |
| 52 | Mario Lemina | 3 | 10 | +0.0596 | +0.0579 | +0.0028 | +0.1129 |
| 53 | Granit Xhaka | 43 | 503 | +0.0575 | +0.0575 | +0.0373 | +0.0778 |
| 54 | Joan Jordán Moreno | 2 | 14 | +0.0561 | +0.0573 | +0.0037 | +0.1110 |
| 55 | Marcelo Brozović | 12 | 85 | +0.0562 | +0.0568 | +0.0176 | +0.0960 |
| 56 | Amadou Onana | 7 | 41 | +0.0546 | +0.0565 | +0.0100 | +0.1030 |
| 57 | In-Beom Hwang | 4 | 27 | +0.0536 | +0.0564 | +0.0066 | +0.1063 |
| 58 | Joe Allen | 5 | 23 | +0.0516 | +0.0561 | +0.0051 | +0.1070 |
| 59 | Xaver Schlager | 6 | 30 | +0.0484 | +0.0547 | +0.0057 | +0.1038 |
| 60 | Bruno Guimarães Rodriguez Moura | 3 | 18 | +0.0403 | +0.0539 | +0.0015 | +0.1064 |
| 61 | João Maria Lobo Alves Palhinha Gonçalves | 9 | 25 | +0.0437 | +0.0538 | +0.0035 | +0.1042 |
| 62 | Maxence Caqueret | 3 | 15 | +0.0369 | +0.0538 | +0.0005 | +0.1072 |
| 63 | Celso Borges Mora | 3 | 16 | +0.0379 | +0.0538 | +0.0008 | +0.1068 |
| 64 | Jordan Veretout | 3 | 17 | +0.0371 | +0.0535 | +0.0007 | +0.1062 |
| 65 | Aaron Mooy | 4 | 18 | +0.0375 | +0.0534 | +0.0009 | +0.1058 |
| 66 | Albin Ekdal | 4 | 11 | +0.0271 | +0.0533 | -0.0014 | +0.1080 |
| 67 | Trent Alexander-Arnold | 4 | 9 | +0.0200 | +0.0532 | -0.0023 | +0.1086 |
| 68 | Angel Gomes | 3 | 21 | +0.0365 | +0.0526 | +0.0011 | +0.1041 |
| 69 | Tomáš Souček | 8 | 57 | +0.0464 | +0.0525 | +0.0091 | +0.0959 |
| 70 | Kaan Ayhan | 6 | 21 | +0.0336 | +0.0519 | +0.0004 | +0.1034 |
| 71 | Hakan Çalhanoğlu | 7 | 59 | +0.0453 | +0.0518 | +0.0088 | +0.0949 |
| 72 | Laurent Abergel | 3 | 24 | +0.0307 | +0.0505 | -0.0001 | +0.1012 |
| 73 | Ivan Ilić | 3 | 10 | -0.0013 | +0.0499 | -0.0051 | +0.1050 |
| 74 | András Schäfer | 7 | 38 | +0.0364 | +0.0499 | +0.0028 | +0.0971 |
| 75 | Kobbie Mainoo | 6 | 32 | +0.0325 | +0.0495 | +0.0009 | +0.0980 |
| 76 | Johan Gastien | 3 | 21 | +0.0235 | +0.0495 | -0.0021 | +0.1010 |
| 77 | Samuel Moutoussamy | 3 | 16 | +0.0130 | +0.0490 | -0.0040 | +0.1020 |
| 78 | Taras Stepanenko | 4 | 19 | +0.0176 | +0.0488 | -0.0033 | +0.1009 |
| 79 | Benjamin André | 3 | 20 | +0.0120 | +0.0471 | -0.0047 | +0.0989 |
| 80 | Nemanja Gudelj | 4 | 6 | -0.0870 | +0.0457 | -0.0108 | +0.1023 |
| 81 | Jhegson Sebastián Méndez Carabalí | 2 | 11 | -0.0275 | +0.0456 | -0.0091 | +0.1003 |
| 82 | Hidemasa Morita | 3 | 19 | +0.0019 | +0.0453 | -0.0068 | +0.0974 |
| 83 | Ethan Ampadu | 5 | 20 | +0.0007 | +0.0445 | -0.0073 | +0.0963 |
| 84 | Woo-Young Jung | 3 | 11 | -0.0364 | +0.0443 | -0.0104 | +0.0991 |
| 85 | Mikel Merino Zazón | 7 | 64 | +0.0285 | +0.0434 | +0.0012 | +0.0856 |
| 86 | Youri Tielemans | 10 | 34 | +0.0129 | +0.0425 | -0.0055 | +0.0906 |
| 87 | Billy Gilmour | 3 | 26 | +0.0026 | +0.0422 | -0.0079 | +0.0923 |
| 88 | Marten de Roon | 5 | 13 | -0.0383 | +0.0420 | -0.0120 | +0.0960 |
| 89 | Jackson Irvine | 4 | 20 | -0.0131 | +0.0414 | -0.0104 | +0.0932 |
| 90 | Grzegorz Krychowiak | 5 | 28 | -0.0011 | +0.0403 | -0.0093 | +0.0899 |
| 91 | Jonas Martin | 3 | 11 | -0.0704 | +0.0395 | -0.0152 | +0.0943 |
| 92 | Rodrigo Bentancur Colmán | 3 | 14 | -0.0507 | +0.0389 | -0.0148 | +0.0926 |
| 93 | Callum McGregor | 6 | 32 | -0.0051 | +0.0373 | -0.0112 | +0.0859 |
| 94 | N'Golo Kanté | 10 | 74 | +0.0135 | +0.0345 | -0.0062 | +0.0752 |
| 95 | Joey Veerman | 5 | 14 | -0.0774 | +0.0343 | -0.0194 | +0.0880 |
| 96 | Enzo Fernandez | 7 | 41 | -0.0045 | +0.0340 | -0.0125 | +0.0805 |
| 97 | Nicolas Seiwald | 5 | 15 | -0.0918 | +0.0303 | -0.0231 | +0.0836 |
| 98 | Paul Pogba | 4 | 44 | -0.0119 | +0.0300 | -0.0158 | +0.0759 |
| 99 | Emre Can | 5 | 13 | -0.1281 | +0.0274 | -0.0266 | +0.0814 |
| 100 | Alex Král | 6 | 24 | -0.0575 | +0.0272 | -0.0234 | +0.0779 |
| 101 | Youssouf Fofana | 8 | 28 | -0.0480 | +0.0265 | -0.0231 | +0.0760 |
| 102 | Mario Götze | 3 | 10 | -0.1945 | +0.0249 | -0.0302 | +0.0799 |
| 103 | Leon Goretzka | 8 | 40 | -0.0310 | +0.0245 | -0.0222 | +0.0712 |
| 104 | Mohammed Kanoo | 3 | 21 | -0.0969 | +0.0207 | -0.0308 | +0.0722 |
| 105 | Ádám Nagy | 5 | 23 | -0.0869 | +0.0207 | -0.0303 | +0.0716 |
| 106 | Teun Koopmeiners | 4 | 11 | -0.2127 | +0.0195 | -0.0352 | +0.0742 |
| 107 | Adam Gnezda Čerin | 4 | 23 | -0.0929 | +0.0191 | -0.0318 | +0.0701 |
| 108 | Benjamin Bourigeaud | 3 | 14 | -0.1995 | +0.0132 | -0.0405 | +0.0668 |
| 109 | Aurélien Djani Tchouaméni | 13 | 56 | -0.0510 | +0.0081 | -0.0354 | +0.0517 |
| 110 | Pierre-Emile Højbjerg | 13 | 84 | -0.0508 | -0.0027 | -0.0420 | +0.0366 |
| 111 | Remo Freuler | 14 | 103 | -0.0534 | -0.0096 | -0.0467 | +0.0274 |

PR_fwd (all 111):

| # | Player | matches | pressured receptions | raw | shrunken | 90% low | 90% high |
|---|---|---|---|---|---|---|---|
| 1 | Tomáš Souček | 8 | 57 | +0.0895 | +0.0014 | -0.0106 | +0.0135 |
| 2 | N'Golo Kanté | 10 | 74 | +0.0686 | +0.0014 | -0.0106 | +0.0134 |
| 3 | András Schäfer | 7 | 38 | +0.1284 | +0.0013 | -0.0108 | +0.0135 |
| 4 | Declan Rice | 19 | 99 | +0.0459 | +0.0011 | -0.0108 | +0.0130 |
| 5 | Enzo Fernandez | 7 | 41 | +0.1028 | +0.0009 | -0.0112 | +0.0131 |
| 6 | Marcelo Brozović | 12 | 85 | +0.0400 | +0.0005 | -0.0115 | +0.0125 |
| 7 | Celso Borges Mora | 3 | 16 | +0.2002 | +0.0004 | -0.0118 | +0.0126 |
| 8 | Aïssa Bilal Laïdouni | 5 | 29 | +0.0938 | +0.0001 | -0.0121 | +0.0123 |
| 9 | Tyler Adams | 4 | 20 | +0.1352 | +0.0001 | -0.0121 | +0.0123 |
| 10 | Ethan Ampadu | 5 | 20 | +0.1325 | +0.0001 | -0.0121 | +0.0123 |
| 11 | Adam Gnezda Čerin | 4 | 23 | +0.1128 | +0.0000 | -0.0122 | +0.0122 |
| 12 | Angel Gomes | 3 | 21 | +0.1158 | -0.0001 | -0.0122 | +0.0121 |
| 13 | Youri Tielemans | 10 | 34 | +0.0702 | -0.0001 | -0.0122 | +0.0121 |
| 14 | Benjamin Bourigeaud | 3 | 14 | +0.1606 | -0.0002 | -0.0124 | +0.0121 |
| 15 | Jerdy Schouten | 6 | 36 | +0.0571 | -0.0003 | -0.0124 | +0.0119 |
| 16 | Remo Freuler | 14 | 103 | +0.0197 | -0.0003 | -0.0122 | +0.0117 |
| 17 | Maxence Caqueret | 3 | 15 | +0.1326 | -0.0003 | -0.0125 | +0.0119 |
| 18 | Paul Pogba | 4 | 44 | +0.0405 | -0.0004 | -0.0125 | +0.0117 |
| 19 | Jackson Irvine | 4 | 20 | +0.0894 | -0.0004 | -0.0126 | +0.0118 |
| 20 | Youssouf Fofana | 8 | 28 | +0.0618 | -0.0004 | -0.0126 | +0.0117 |
| 21 | João Maria Lobo Alves Palhinha Gonçalves | 9 | 25 | +0.0604 | -0.0006 | -0.0128 | +0.0116 |
| 22 | Alex Král | 6 | 24 | +0.0592 | -0.0006 | -0.0128 | +0.0116 |
| 23 | Ádám Nagy | 5 | 23 | +0.0595 | -0.0006 | -0.0128 | +0.0115 |
| 24 | Kobbie Mainoo | 6 | 32 | +0.0418 | -0.0007 | -0.0128 | +0.0115 |
| 25 | Mikel Merino Zazón | 7 | 64 | +0.0204 | -0.0007 | -0.0127 | +0.0114 |
| 26 | Billy Gilmour | 3 | 26 | +0.0461 | -0.0007 | -0.0129 | +0.0114 |
| 27 | Seko Fofana | 3 | 33 | +0.0331 | -0.0008 | -0.0130 | +0.0114 |
| 28 | Mario Lemina | 3 | 10 | +0.1041 | -0.0008 | -0.0131 | +0.0114 |
| 29 | Moisés Isaac Caicedo Corozo | 3 | 26 | +0.0379 | -0.0009 | -0.0130 | +0.0113 |
| 30 | İlkay Gündoğan | 11 | 67 | +0.0137 | -0.0009 | -0.0129 | +0.0112 |
| 31 | Kaan Ayhan | 6 | 21 | +0.0442 | -0.0009 | -0.0131 | +0.0113 |
| 32 | Aurélien Djani Tchouaméni | 13 | 56 | +0.0159 | -0.0009 | -0.0130 | +0.0112 |
| 33 | Martín Zubimendi Ibáñez | 5 | 20 | +0.0424 | -0.0009 | -0.0131 | +0.0113 |
| 34 | Jonas Martin | 3 | 11 | +0.0708 | -0.0010 | -0.0132 | +0.0112 |
| 35 | Sofyan Amrabat | 6 | 26 | +0.0287 | -0.0010 | -0.0132 | +0.0112 |
| 36 | Woo-Young Jung | 3 | 11 | +0.0674 | -0.0010 | -0.0132 | +0.0112 |
| 37 | Timi Elšnik | 4 | 14 | +0.0459 | -0.0011 | -0.0133 | +0.0112 |
| 38 | Joe Allen | 5 | 23 | +0.0274 | -0.0011 | -0.0133 | +0.0111 |
| 39 | Jhegson Sebastián Méndez Carabalí | 2 | 11 | +0.0551 | -0.0011 | -0.0133 | +0.0111 |
| 40 | Rúben Diogo Da Silva Neves | 7 | 19 | +0.0301 | -0.0011 | -0.0133 | +0.0111 |
| 41 | Jorge Luiz Frello Filho | 10 | 86 | +0.0051 | -0.0011 | -0.0131 | +0.0108 |
| 42 | Jakub Moder | 4 | 21 | +0.0242 | -0.0011 | -0.0133 | +0.0111 |
| 43 | Marten de Roon | 5 | 13 | +0.0380 | -0.0011 | -0.0134 | +0.0111 |
| 44 | Nampalys Mendy | 4 | 20 | +0.0224 | -0.0012 | -0.0134 | +0.0110 |
| 45 | Johan Gastien | 3 | 21 | +0.0172 | -0.0012 | -0.0134 | +0.0110 |
| 46 | Corentin Tolisso | 4 | 13 | +0.0278 | -0.0012 | -0.0135 | +0.0110 |
| 47 | Miralem Pjanić | 15 | 90 | +0.0029 | -0.0012 | -0.0132 | +0.0107 |
| 48 | Batista Mendy | 2 | 14 | +0.0249 | -0.0012 | -0.0135 | +0.0110 |
| 49 | Joan Jordán Moreno | 2 | 14 | +0.0247 | -0.0012 | -0.0135 | +0.0110 |
| 50 | Samuel Moutoussamy | 3 | 16 | +0.0171 | -0.0013 | -0.0135 | +0.0109 |
| 51 | Rodrigo Bentancur Colmán | 3 | 14 | +0.0194 | -0.0013 | -0.0135 | +0.0109 |
| 52 | Joey Veerman | 5 | 14 | +0.0188 | -0.0013 | -0.0135 | +0.0109 |
| 53 | Jordan Veretout | 3 | 17 | +0.0086 | -0.0013 | -0.0136 | +0.0109 |
| 54 | Thomas Teye Partey | 3 | 17 | +0.0038 | -0.0014 | -0.0136 | +0.0108 |
| 55 | Leander Dendoncker | 4 | 11 | +0.0047 | -0.0014 | -0.0136 | +0.0108 |
| 56 | Hidemasa Morita | 3 | 19 | +0.0014 | -0.0014 | -0.0136 | +0.0108 |
| 57 | Stanislav Lobotka | 5 | 36 | -0.0027 | -0.0015 | -0.0136 | +0.0107 |
| 58 | Aaron Mooy | 4 | 18 | -0.0041 | -0.0015 | -0.0137 | +0.0107 |
| 59 | Mohammed Kanoo | 3 | 21 | -0.0040 | -0.0015 | -0.0137 | +0.0107 |
| 60 | Xaver Schlager | 6 | 30 | -0.0034 | -0.0015 | -0.0136 | +0.0107 |
| 61 | Ivan Ilić | 3 | 10 | -0.0163 | -0.0015 | -0.0138 | +0.0107 |
| 62 | Mario Götze | 3 | 10 | -0.0187 | -0.0015 | -0.0138 | +0.0107 |
| 63 | Amadou Onana | 7 | 41 | -0.0063 | -0.0015 | -0.0137 | +0.0106 |
| 64 | Boubacar Kamara | 2 | 19 | -0.0119 | -0.0016 | -0.0138 | +0.0107 |
| 65 | Albin Ekdal | 4 | 11 | -0.0229 | -0.0016 | -0.0138 | +0.0107 |
| 66 | Lucas Tolentino Coelho de Lima | 5 | 52 | -0.0068 | -0.0016 | -0.0137 | +0.0105 |
| 67 | Carlos Henrique Casimiro | 6 | 54 | -0.0071 | -0.0016 | -0.0137 | +0.0105 |
| 68 | Atakan Karazor | 2 | 12 | -0.0273 | -0.0016 | -0.0138 | +0.0106 |
| 69 | Kalvin Phillips | 9 | 48 | -0.0102 | -0.0017 | -0.0138 | +0.0104 |
| 70 | Leon Goretzka | 8 | 40 | -0.0128 | -0.0017 | -0.0138 | +0.0104 |
| 71 | Benjamin André | 3 | 20 | -0.0259 | -0.0017 | -0.0139 | +0.0105 |
| 72 | Pedro Chirivella Burgos | 3 | 22 | -0.0244 | -0.0017 | -0.0139 | +0.0105 |
| 73 | Kristjan Asllani | 3 | 23 | -0.0251 | -0.0017 | -0.0139 | +0.0104 |
| 74 | Morten Hjulmand | 3 | 39 | -0.0158 | -0.0018 | -0.0139 | +0.0104 |
| 75 | Nadiem Amiri | 6 | 21 | -0.0279 | -0.0018 | -0.0140 | +0.0104 |
| 76 | Nemanja Gudelj | 4 | 6 | -0.1072 | -0.0018 | -0.0141 | +0.0105 |
| 77 | Nicolas Seiwald | 5 | 15 | -0.0473 | -0.0018 | -0.0140 | +0.0104 |
| 78 | Serhii Sydorchuk | 4 | 26 | -0.0291 | -0.0018 | -0.0140 | +0.0103 |
| 79 | Axel Witsel | 7 | 26 | -0.0304 | -0.0019 | -0.0140 | +0.0103 |
| 80 | Leandro Daniel Paredes | 15 | 72 | -0.0122 | -0.0019 | -0.0139 | +0.0102 |
| 81 | Taras Stepanenko | 4 | 19 | -0.0443 | -0.0019 | -0.0141 | +0.0103 |
| 82 | Saša Lukić | 6 | 24 | -0.0370 | -0.0019 | -0.0141 | +0.0103 |
| 83 | Kristoffer Olsson | 4 | 15 | -0.0619 | -0.0020 | -0.0142 | +0.0103 |
| 84 | Salis Abdul Samed | 4 | 17 | -0.0592 | -0.0020 | -0.0142 | +0.0102 |
| 85 | Wataru Endo | 3 | 16 | -0.0633 | -0.0020 | -0.0142 | +0.0102 |
| 86 | Dixon Jair Arroyo Espinoza | 3 | 9 | -0.1117 | -0.0020 | -0.0142 | +0.0102 |
| 87 | Trent Alexander-Arnold | 4 | 9 | -0.1126 | -0.0020 | -0.0142 | +0.0102 |
| 88 | Exequiel Alejandro Palacios | 25 | 244 | -0.0061 | -0.0020 | -0.0135 | +0.0095 |
| 89 | Tijjani Reijnders | 6 | 30 | -0.0399 | -0.0021 | -0.0143 | +0.0101 |
| 90 | Teun Koopmeiners | 4 | 11 | -0.1076 | -0.0021 | -0.0143 | +0.0101 |
| 91 | Bruno Guimarães Rodriguez Moura | 3 | 18 | -0.0673 | -0.0021 | -0.0143 | +0.0101 |
| 92 | Thomas Delaney | 8 | 61 | -0.0218 | -0.0021 | -0.0142 | +0.0099 |
| 93 | Emre Can | 5 | 13 | -0.0959 | -0.0021 | -0.0144 | +0.0101 |
| 94 | Grzegorz Krychowiak | 5 | 28 | -0.0461 | -0.0021 | -0.0143 | +0.0100 |
| 95 | In-Beom Hwang | 4 | 27 | -0.0479 | -0.0021 | -0.0143 | +0.0100 |
| 96 | Giorgi Kochorashvili | 5 | 32 | -0.0424 | -0.0022 | -0.0143 | +0.0100 |
| 97 | Christian Nørgaard | 8 | 20 | -0.0672 | -0.0022 | -0.0144 | +0.0100 |
| 98 | Laurent Abergel | 3 | 24 | -0.0677 | -0.0023 | -0.0145 | +0.0099 |
| 99 | Sergio Busquets i Burgos | 44 | 419 | -0.0062 | -0.0023 | -0.0134 | +0.0087 |
| 100 | Callum McGregor | 6 | 32 | -0.0584 | -0.0025 | -0.0146 | +0.0097 |
| 101 | Azor Matusiwa | 2 | 17 | -0.1331 | -0.0027 | -0.0149 | +0.0095 |
| 102 | Ellyes Joris Skhiri | 5 | 19 | -0.1294 | -0.0028 | -0.0150 | +0.0094 |
| 103 | Florian Grillitsch | 7 | 35 | -0.0767 | -0.0029 | -0.0151 | +0.0092 |
| 104 | Hakan Çalhanoğlu | 7 | 59 | -0.0494 | -0.0030 | -0.0151 | +0.0091 |
| 105 | Toni Kroos | 11 | 59 | -0.0503 | -0.0030 | -0.0151 | +0.0090 |
| 106 | Marco Verratti | 47 | 539 | -0.0086 | -0.0031 | -0.0139 | +0.0076 |
| 107 | Ander Herrera Agüera | 8 | 47 | -0.0722 | -0.0033 | -0.0154 | +0.0088 |
| 108 | Pierre-Emile Højbjerg | 13 | 84 | -0.0512 | -0.0037 | -0.0157 | +0.0083 |
| 109 | Robert Andrich | 28 | 185 | -0.0439 | -0.0055 | -0.0172 | +0.0062 |
| 110 | Granit Xhaka | 43 | 503 | -0.0205 | -0.0057 | -0.0165 | +0.0051 |
| 111 | Vitor Machado Ferreira | 35 | 275 | -0.0420 | -0.0069 | -0.0183 | +0.0045 |

### Step 3 (C) — progressive availability (PFF WC2022)
- Moments: 584,874. The teammate is ≥5 m nearer the opponent goal than the ball in 50.2% of them.
- AV_prog base rate: 0.143 (Task 38 AV: 0.334). Baseline out-of-fold AUC: 0.814.
- P(target | AV_prog) = 0.148; P(target | not) = 0.099.

| Test | Result |
|---|---|
| R1, deep midfielders (≥4 matches) | median 0.671 [0.544, 0.802], n = 28: **PASS** |
| R1, all outfield | 0.466 [0.389, 0.525], n = 183 |
| R2, all outfield | −0.0126 per 100 receptions per SD [−0.0655, 0.0403], p = 0.64, MDE 0.0755 (43,815 / 381) |
| R2, deep midfielders | +0.0852 [−0.0880, 0.2583], p = 0.33, MDE 0.2474 (8,053 / 59) |
| Praised list (≥300 moments; 273 qualifying; 9 present) | T = −0.167, p = 0.60 (no pre-declared direction) |

Praised-list z-scores: Rodri −0.56, Gündoğan −0.21, De Bruyne +1.59, Xhaka +0.48, Busquets +0.09, de Jong −1.71, Pedri −0.43, Modrić −1.54, Kimmich +0.78.

### Claim family — every within-DM results test in Steps 1-3 (Holm across 11; also with Task 41's 12 added = 23)

| Test | coef per 100 per SD | raw p | Holm (11) | Holm (23) | control on same rows | claim allowed |
|---|---|---|---|---|---|---|
| Step 1 dm|v5_decision|y_f3 | +0.4538 | 0.3015 | 1 | 1 | +0.760, p=0.000109 | no |
| Step 1 dm|move_on_speed|y_f3 | +0.4546 | 0.3766 | 1 | 1 | +0.796, p=9.47e-08 | no |
| Step 1 dm|rq_rel|y_f3 | -0.1080 | 0.6675 | 1 | 1 | -0.035, p=0.745 | no |
| Step 1 dm|v5_decision|y_shot | -0.3931 | 0.182 | 1 | 1 | +0.626, p=0.0163 | no |
| Step 1 dm|move_on_speed|y_shot | +0.1103 | 0.6821 | 1 | 1 | +0.545, p=0.0152 | no |
| Step 1 dm|rq_rel|y_shot | +0.2643 | 0.2785 | 1 | 1 | -0.259, p=0.137 | no |
| Step 2 R2 dm|pr_keep|y_f3 | +2.9114 | 0.01716 | 0.189 | 0.378 | -0.538, p=0.665 | no |
| Step 2 R2 dm|pr_keep|y_net_xg | +0.0320 | 0.4017 | 1 | 1 | +0.004, p=0.998 | no |
| Step 2 R2 dm|pr_fwd|y_f3 | +1.1243 | 0.6059 | 1 | 1 | -0.538, p=0.665 | no |
| Step 2 R2 dm|pr_fwd|y_net_xg | -0.1186 | 0.3997 | 1 | 1 | +0.004, p=0.998 | no |
| Step 3 R2 dm|av_prog|y_net_xg | +0.0852 | 0.3349 | 1 | 1 | +1.856, p=0.00955 | no |

### Fixed claim rules, applied mechanically
- **Within-DM results:** no test meets both conditions (Holm p < 0.05 and a positive control with p < 0.05). No within-deep-midfielder results claim is made.
- **Stability:**
  - PR_keep and PR_fwd fail R1 (0.249 and 0.268 at 100).
  - AV_prog passes R1 within deep midfielders (0.671 ≥ 0.60, n = 28 players).
- **Praised list:** PR_keep has p = 0.014 in the pre-declared direction (higher). This meets the brief's stated condition for any statement about the list. PR_fwd (p = 0.43) and AV_prog (p = 0.60, no declared direction) do not.

## 4. Deviations from the brief
- **Reception-unit control** is the retention control chosen by the author (above). The brief says "positive control (completion)", which does not exist for receptions.
- **Operational definitions:**
  - "Normalised x" = StatsBomb's team-relative x (the acting team attacks toward 120).
  - Y_F3 / Y_SHOT count only LATER events of the unit's own team in the same `possession`.
  - The unit's start x is the pass origin (value-model `ball_x`) or the receiver's 360 location (`recv_x`).
- **Next action and keep** (used by the retention control and Step 2):
  - Scan later events of the same possession. The receiver's Miscontrol or Dispossessed first gives keep = 0.
  - Otherwise the first receiver event in {Pass, Carry, Dribble, Shot} is the action.
  - keep = the action did not fail (a Pass with any pass_outcome, a Dribble 'Incomplete', or any Shot counts as failed) AND the event right after it is in the same possession and is not the receiver's Miscontrol or Dispossessed.
  - Receipts with no action found (660) are excluded.
  - Under this rule, a carry followed by the team keeping possession counts as keep = 1 even if the next pass fails. The receiver's own next action is the carry in 84% of receipts.
- **PRESSURED distance:** the nearest visible opponent was recomputed from the frame without Task 34's 15-unit cap.
- **R3 floor:** qualifying players have ≥50 pressured receptions, the brief's R2 floor (the brief states none for R3).
- **Step 2 R2 units:** 1,476 of 42,208 pressured receptions have no value-model origin row, so they have no g and were dropped from R2. R1 used all 42,208.
- **Step 3 control (PFF, per the correction):**
  - The receiver's next PFF possession event after the reception (skipping his initial touch, IT) is his action. An opposing possession event first gives keep = 0.
  - keep = the action did not fail (PA/CR not 'C', or any SH) AND the next possession event is by the same team.
  - The PFF retention rate is 0.818 (n = 52,411 receptions).
  - Control: all outfield +3.435 pp [2.606, 4.264], p = 5e-16 (22,425 receptions, 131 players). Deep midfielders +1.856 [0.452, 3.260], p = 0.0096 (4,671 receptions, 28 players).
  - These control rows are the test rows whose receivers also have ≥100 PFF receptions elsewhere, so they are fewer than the test's.
- **Overlap with PR_keep (as the correction asks to note):** in Step 2 the retention control overlaps in content with PR_keep. It still shows whether the design can detect a known reception-level skill on those rows.
- **Claim rule:** "positive control ... p < 0.05" is applied as a control coefficient > 0 with p < 0.05.
- **Tempo residuals** were regenerated with ids (as in Task 39) to new Task 42 files, asserted identical to the stored v2 files.

## 5. Problems and surprises
- **The retention control fails on the deep-midfielder RQ_rel rows** (Y_F3 −0.035, p = 0.75; Y_SHOT −0.259, p = 0.14). Under the brief's claim rule, those two deep-midfielder tests could not support a claim even if their Holm p were < 0.05.
- **MDEs on Y_F3 / Y_SHOT for deep midfielders are 0.68-1.44 pp per SD per 100 units.** That is larger than any coefficient observed.
- **keep's base rate is 0.94**, so the retention outcome varies little.

- **R1 for press resistance rests on 7 player-seasons at 100** (15 at 50). With the ≥50-elsewhere floor, R2 covers only 150 players overall and 22 deep midfielders.
- **The one within-DM test with raw p < 0.05** (PR_keep → Y_F3, p = 0.017) has a retention control that is not positive on the same rows (−0.54 pp, p = 0.67). Its MDE (3.4 pp) exceeds its estimate (2.9 pp).
- **On the 22-player press-resistance deep-midfielder rows, the retention control is not positive for either outcome** (p = 0.67 and 1.00). Taken at face value, those rows could not detect a known reception-level skill.
- **The PR_fwd baseline AUC is 0.587.** The fwd outcome is rare (11%), and its DM table shows no heterogeneity (Q p = 0.41).
- **The praised list scores higher on PR_keep** (p = 0.014, pre-declared direction), while PR_keep fails R1 within deep midfielders (0.25). Taken at face value, the list differs from random within-role draws on a measure whose player-level differences are not shown to be stable among deep midfielders.
- **AV_prog passes R1** among deep midfielders, but its R2 is null for all players and for deep midfielders.

## 6. Questions for the research lead
- Q1: The keep definition evaluates the receiver's first action, which is usually a carry. Should it instead evaluate his first pass or shot (the end of his possession spell)?

## 7. Files produced
- `src/engine_v2/task42_outcomes.py`, `task42_step1.py`, `task42_step2.py`, `task42_family.py`, and `src/pff/task42_av_prog.py`.
- `data/engine_v2_task42_step2.json`, `data/pff_task42_step3.json`, `data/engine_v2_task42_family.json`, and `data/processed/engine_v2/task42_pressured_receptions.parquet` (none committed).
- `data/engine_v2_task42_step1.json`, `data/processed/engine_v2/task42_event_outcomes.parquet`, `task42_receipt_actions.parquet`, and the redirected tempo re-run outputs `data/processed/tempo_task42_*` and `data/tempo_task42_redesign_rerun.json` (none committed).
- Side effects: none else. No memory writes. JOURNAL.md and AGENTS.md untouched. Holdout untouched.
- Commits: brief 107bed0; interim page after Step 1 99a4b82; first final c8ec94d (hash recorded in 3d97f4e); corrected-control version c2aed3b.

## 8. Confidence
The estimator and inputs are the verified Task 35 pipeline.
The weakest links:
- The new keep definition, which lies behind both PR_keep and the retention control.
- The small press-resistance samples (7 player-seasons for R1 at 100; 22 deep midfielders for R2).
