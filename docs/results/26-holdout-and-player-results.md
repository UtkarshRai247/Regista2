# Task 26: Holdout replication, then the player results
Date: 2026-09-28
Status: COMPLETE (Steps 0-5; Step 6 to follow in a separate commit per the brief's own allowance)

## Section checklist
- Step 0 (commit brief alone): COMPLETE
- Step 1 (holdout replication, gate): COMPLETE -- GATE PASSES
- Step 2 (tempo rerun on corrected coordinates): COMPLETE
- Step 3 (player-level threshold): COMPLETE
- Step 4 (leaderboard): COMPLETE
- Step 5 (dimension correlations): COMPLETE
- Step 6 (Study B rebuild): reported separately, see Section 12 / follow-up commit

## 1. Headline
The holdout gate passes: on 126 never-touched women's international
matches (Women's Euro 2022/2025, Women's World Cup 2023), scored with
the FROZEN engine v5 (no retraining, no refitting), xg H-O1's
decision_z coefficient is +0.2611 with p=6.7e-06 -- positive and well
under the 0.05 bar. All 8 computable team-match specifications show a
positive coefficient (7 of 8 significant at p<0.05; xg H-O2 is not,
p=0.326, the same weakest-link pattern as the study sample). Tempo's
MOVE_ON_SPEED/HOLD_VARIATION, re-run on corrected coordinates, remain
USABLE with materially unchanged reliability. The player-level
reliability threshold, chosen by the brief's own fixed rule with no
look at any ranking, is the LOWEST threshold tested (100 passes) --
median reliability there is already 0.7252, above the 0.70 bar --
reflecting the scale of Task 24/25's reliability improvement (T6 at
200 passes rose from 0.615 to 0.819). 537 players qualify for the
pooled leaderboard. The only correlation pair exceeding |0.7| in
Section 7 is Decision vs. Risk itself (0.80 overall, 0.75 within the
DEEP/DEFENSIVE MIDFIELD group) -- expected given both share the same
underlying construction, not a new empirical finding. Decision vs. xA
per 90 is +0.57 overall in this task's fully-pooled construction, a
different number from Task 25's own +0.71 (different threshold and
pooling method, both disclosed in Section 7 -- not a contradiction).
Study B (Step 6) is reported separately, per the brief's own
allowance.

## 2. What I did
1. Committed `task-26-holdout-and-player-results.md` alone (Step 0).
2. Step 1(a): `task26_holdout_evidence.py` -- coordinate evidence on
   all 126 holdout matches.
3. Step 1(b): scored the holdout with the FROZEN engine v5 end to end
   -- `grid_holdout.py` (candidate generation), `pass_success_score_holdout.py`
   (frozen pass_success_model_v3.json), `ev_compute_holdout.py` (frozen
   value_model_for_v5/against_v5), `policy_and_decision_holdout.py`
   (frozen policy_model.json, offside_v4/R1_K10, T=0.1562). No `.fit()`
   call anywhere in this chain.
4. Step 1(c): `outcome_validation_holdout.py` -- outcome-validation
   battery on the 126 holdout matches' team-match units, decision_z
   standardized within the holdout. Checked the gate.
5. Step 2: `redesign_metrics_v2.py` / `redesign_reliability_v2.py` --
   MOVE_ON_SPEED/HOLD_VARIATION re-run with `redesign_metrics.py`'s
   local direction function monkeypatched to the corrected (+1
   everywhere) convention, spec otherwise unchanged.
6. Step 3: `task26_step3_threshold.py` -- reused `step8_regate.py`'s
   own `reliability_sweep` on `pass_der_v8.parquet`'s `decision_new`.
7. Step 4: `task26_step4_leaderboard.py` -- pooled leaderboard,
   shrinkage at the measured reliability, DEEP/DEFENSIVE MIDFIELD
   group, fixed-list ranks (name matching ported from
   `task14b_leaderboards_referee2.py`'s diacritic-normalizing,
   nickname-aware `name_matches`).
8. Step 5: `task26_step5_correlations.py` -- correlation matrix at the
   Step 3 threshold, overall and within DEEP/DEFENSIVE MIDFIELD.

Reproduce with (from `src/engine_v2/`, `.venv` activated, in order):
`python task26_holdout_evidence.py && python grid_holdout.py && python
pass_success_score_holdout.py && python ev_compute_holdout.py && python
policy_and_decision_holdout.py && python outcome_validation_holdout.py
&& python task26_step3_threshold.py && python
task26_step4_leaderboard.py && python task26_step5_correlations.py`,
plus (from `src/tempo/`) `python redesign_metrics_v2.py && python
redesign_reliability_v2.py`.

## 3. Step 1 -- holdout replication

### 1(a) Coordinate evidence on the holdout (126 matches)
| quantity | holdout | study sample (Task 24, 299 matches) |
|---|---|---|
| team-periods with a shot | 540 | 1260 |
| share with mean shot x > 60 | 100.00% | 99.84% |
| opponent-keeper x, median | 117.61 | 117.50 |
| opponent-keeper x, share beyond x=100 | 100.00% | 99.93% |
| matches skipped for the keeper check (no frames file) | 1 | 0 |

The same team-relative coordinate convention holds on the holdout.

### 1(b) Scoring the holdout with the frozen engine v5
| stage | quantity |
|---|---|
| candidate generation (`grid_holdout.py`) | 126 matches (1 skipped, no frames file), 89459 eligible passes, 37167409 candidate rows |
| T1 (median displacement) | 1.6125, PASS (True) |
| pass-success scoring | frozen `pass_success_model_v3.json`, no retrain |
| EV computation | frozen `value_model_for_v5`/`against_v5`, no retrain |
| policy scoring | frozen `policy_model.json`, offside_v4 (R1_K10), T=0.1562 (engine v5's own value, no refit) |
| Decision/Risk | 89459 of 89459 passes (0 had zero surviving restricted candidates) |

### 1(c) Outcome validation on holdout team-matches
252 team-match units from 126 matches (2 missing Decision); decision_z standardized within the holdout's own 250 scored units; 3 competition-season levels (3 holdout competition-seasons).

| spec | n | decision_z coef | p |
|---|---|---|---|
| xg_H-O1 | n=250 | 0.2611 | 6.715e-06 |
| xg_H-O2 | n=250 | 0.0664 | 0.3262 |
| xg_PH-O1 | n=250 | 0.1764 | 0.03668 |
| xg_PH-O4 | n=250 | 0.3762 | 5.573e-07 |
| goals_H-O1 | n=250 | 0.3358 | 1.263e-06 |
| goals_H-O2 | n=250 | 0.2797 | 0.0002096 |
| goals_PH-O1 | n=250 | 0.3702 | 2.991e-07 |
| goals_PH-O4 | n=250 | 0.4652 | 5.739e-11 |

**NOT COMPUTED**: PH-O2 and PH-O3 -- not computed: requires team-context (team x competition-season) fixed effects; the holdout has only 3 competition-seasons and most teams appear in only 1-2 matches, so team-context dummies would be at or near the row count (singular design) not computed: the possession-level specification clusters by team-context; the same near-singular-design concern as PH-O2 applies, and the holdout's possession count at this task's minimum-pass floor is small

**GATE (xg H-O1 decision_z positive, p<0.05): PASS.** Steps 2-6 proceed.

Holdout population note, per the brief: this is women's international football (Women's Euro 2022/2025, Women's World Cup 2023); the study sample (Section 4 onward) is mostly men's club/international football (8 competition-seasons, 299 matches). The gate passing on a different population and competition level is a stronger replication than a held-out slice of the same population would have been, and also means the two populations are not directly comparable beyond the gate itself.
## 4. Step 2 -- tempo re-run on corrected coordinates
| quantity | before (Task 16b) | after (this task) |
|---|---|---|
| move_on_speed within R^2 | 0.1851 | 0.1866 |
| move_on_speed median reliability @200 | 0.7832 | 0.7682 |
| move_on_speed verdict (0.70 bar) | USABLE | USABLE |
| hold_variation within R^2 | 0.0421 | 0.0425 |
| hold_variation median reliability @200 | 0.8805 | 0.8801 |
| hold_variation verdict (0.70 bar) | USABLE | USABLE |
| corr(move_on_speed, hold_variation) | -0.0617 | -0.0579 |

Both metrics remain USABLE; reliability and the cross-metric correlation move only slightly. This is expected, not a null result to explain away: tempo's own within-(match,team) demeaning already absorbs a same-match, same-team 180-degree flip almost entirely (a flip applied consistently to every one of a team's passes in one match cancels out in a team-match fixed effect), unlike engine v5's per-event, cross-team-combination-sensitive quantities (T6 at 200 passes, by contrast, rose from 0.615 to 0.819).

## 5. Step 3 -- player-level threshold by reliability
| threshold | n units | median reliability |
|---|---|---|
| 100 | 607 | 0.7252 |
| 150 | 364 | 0.7850 |
| 200 | 252 | 0.8191 |
| 250 | 166 | 0.8660 |
| 300 | 117 | 0.8977 |
| 400 | 77 | 0.9319 |
| 500 | 54 | 0.9489 |

**RULE**: lowest threshold with median reliability >= 0.70. Result: **100** passes (median reliability 0.7252), the lowest threshold tested -- not PROVISIONAL. Chosen from this table alone, before building any ranking, per the hard rule.

## 6. Step 4 -- leaderboard
Qualifying players (>= 100 pooled eligible passes across all competitions): **537**. Overall mean Decision per 100: 0.27984. Shrinkage: `shrunken = overall_mean + 0.7252 * (raw - overall_mean)`.

### Top 20 (overall, by shrunken Decision per 100)
| rank | player | position group | competitions | n | raw | shrunken |
|---|---|---|---|---|---|---|
| 1 | Raphael Dias Belloli | Forward | 1 | 109 | 1.3036 | 1.0223 |
| 2 | Dušan Tadić | Midfielder | 2 | 165 | 1.2173 | 0.9597 |
| 3 | Vinícius José Paixão de Oliveira Júnior | Forward | 2 | 130 | 1.0365 | 0.8286 |
| 4 | Cody Mathès Gakpo | Forward | 3 | 232 | 0.9324 | 0.7531 |
| 5 | Pablo Sarabia García | Forward | 3 | 201 | 0.9065 | 0.7343 |
| 6 | Nicholas Williams Arthuer | Forward | 2 | 212 | 0.8903 | 0.7225 |
| 7 | Otávio Edmilson da Silva Monteiro | Midfielder | 1 | 111 | 0.8879 | 0.7208 |
| 8 | Gerard Moreno Balaguero | Forward | 2 | 176 | 0.8513 | 0.6942 |
| 9 | Serge Gnabry | Forward | 3 | 198 | 0.8193 | 0.6711 |
| 10 | Jeremy Doku | Forward | 4 | 172 | 0.8019 | 0.6584 |
| 11 | Lamine Yamal Nasraoui Ebana | Forward | 1 | 163 | 0.7906 | 0.6502 |
| 12 | Kevin De Bruyne | Midfielder | 3 | 442 | 0.7598 | 0.6279 |
| 13 | Romelu Lukaku Menama | Forward | 3 | 119 | 0.7528 | 0.6228 |
| 14 | Victor Okoh Boniface | Forward | 1 | 318 | 0.7488 | 0.6200 |
| 15 | Daniel Olmo Carvajal | Forward | 4 | 556 | 0.7294 | 0.6058 |
| 16 | Christian Pulisic | Forward | 1 | 108 | 0.7294 | 0.6058 |
| 17 | Alphonso Davies | Defender | 2 | 123 | 0.7232 | 0.6014 |
| 18 | Nathan Tella | Defender | 1 | 224 | 0.7141 | 0.5948 |
| 19 | Lionel Andrés Messi Cuccittini | Forward | 5 | 5570 | 0.7114 | 0.5928 |
| 20 | Xherdan Shaqiri | Midfielder | 4 | 256 | 0.6937 | 0.5800 |

### Bottom 20 (overall)
| rank | player | position group | competitions | n | raw | shrunken |
|---|---|---|---|---|---|---|
| 518 | Tyrone Mings | Defender | 1 | 117 | 0.0597 | 0.1202 |
| 519 | Kieran Tierney | Defender | 2 | 153 | 0.0575 | 0.1186 |
| 520 | Jan Bednarek | Defender | 3 | 205 | 0.0551 | 0.1168 |
| 521 | Domagoj Vida | Defender | 1 | 150 | 0.0540 | 0.1161 |
| 522 | Felix Eduardo Torres Caicedo | Defender | 1 | 181 | 0.0457 | 0.1100 |
| 523 | Nahuel Molina Lucero | Defender | 1 | 241 | 0.0456 | 0.1100 |
| 524 | Josip Šutalo | Defender | 2 | 225 | 0.0428 | 0.1080 |
| 525 | Kalvin Phillips | Midfielder | 2 | 328 | 0.0399 | 0.1059 |
| 526 | Andrei Burcă Andonie | Defender | 1 | 129 | 0.0351 | 0.1023 |
| 527 | Marcus Andreas Danielsson | Defender | 1 | 124 | 0.0320 | 0.1001 |
| 528 | Taras Stepanenko | Midfielder | 2 | 159 | 0.0302 | 0.0988 |
| 529 | Victor Nilsson Lindelöf | Defender | 1 | 163 | 0.0273 | 0.0967 |
| 530 | Duje Ćaleta-Car | Defender | 2 | 175 | 0.0266 | 0.0962 |
| 531 | Jack Hendry | Defender | 2 | 127 | 0.0184 | 0.0902 |
| 532 | Mario Mitaj | Defender | 1 | 106 | 0.0133 | 0.0866 |
| 533 | Yassine Meriah | Defender | 1 | 150 | 0.0075 | 0.0823 |
| 534 | Leonardo Spinazzola | Defender | 1 | 153 | 0.0064 | 0.0816 |
| 535 | Ľubomír Šatka | Defender | 1 | 155 | -0.0034 | 0.0744 |
| 536 | Petr Ševčík | Forward | 2 | 120 | -0.0168 | 0.0647 |
| 537 | Óscar Esau Duarte Gaitán | Defender | 2 | 112 | -0.0260 | 0.0580 |

Top 20 skews attacking (Forwards/creative Midfielders); bottom 20 skews Defenders -- reported descriptively, not interpreted, per the hard rule.

### Fixed 13-name list (output only, never a criterion)
| name | overall rank | within-position rank | position group | n qualifying (position) | n eligible passes |
|---|---|---|---|---|---|
| Kroos (Toni Kroos) | 213 | 79 | Midfielder | 193 | 855 |
| Modric (Luka Modrić) | 290 | 120 | Midfielder | 193 | 954 |
| Verratti (Marco Verratti) | 240 | 91 | Midfielder | 193 | 3518 |
| Busquets (Sergio Busquets i Burgos) | 201 | 74 | Midfielder | 193 | 2994 |
| De Bruyne (Kevin De Bruyne) | 12 | 3 | Midfielder | 193 | 442 |
| Xhaka (Granit Xhaka) | 260 | 101 | Midfielder | 193 | 3510 |
| de Jong (Frenkie de Jong) | 230 | 87 | Midfielder | 193 | 3012 |
| Kimmich (Joshua Kimmich) | 79 | 15 | Defender | 262 | 844 |
| Rodri (Rodrigo Hernández Cascante) | 398 | 158 | Defender | 262 | 1191 |
| Pedri (Pedro González López) | 118 | 32 | Midfielder | 193 | 2413 |
| Gundogan (İlkay Gündoğan) | 218 | 82 | Midfielder | 193 | 469 |
| Grillitsch (Florian Grillitsch) | 272 | 109 | Midfielder | 193 | 320 |
| Shaparenko (Mykola Shaparenko) | 315 | 131 | Midfielder | 193 | 312 |

Name matching used `task14b_leaderboards_referee2.py`'s own diacritic-normalizing, nickname-aware `name_matches` (ported unchanged) -- a plain lowercase-substring match, tried first, mismatched Modrić (diacritic) and Rodri (ambiguous substring of 4 different 'Rodrigo's) until this fix was applied; disclosed here since it changed 3 of 13 rows from the first pass.

### DEEP / DEFENSIVE MIDFIELD group -- full table (200 qualifying players, ranked by within-group z)
Definition (disclosed assumption, not specified anywhere in the plan/codebase, same status as `position_group()`'s own documented assumption): raw StatsBomb `position` containing "Defensive Midfield" (Center/Left/Right Defensive Midfield).

| rank | player | n | raw | shrunken | z (within Midfielder/Defender group) |
|---|---|---|---|---|---|
| 1 | Otávio Edmilson da Silva Monteiro | 111 | 0.8879 | 0.7208 | 4.061 |
| 2 | Kevin De Bruyne | 442 | 0.7598 | 0.6279 | 3.207 |
| 3 | Steven Berghuis | 127 | 0.6837 | 0.5727 | 2.700 |
| 4 | Sergej Milinković-Savić | 171 | 0.5890 | 0.5040 | 2.069 |
| 5 | Cody Mathès Gakpo | 232 | 0.9324 | 0.7531 | 1.878 |
| 6 | Joshua Kimmich | 844 | 0.4329 | 0.3909 | 1.802 |
| 7 | Bruno Miguel Borges Fernandes | 496 | 0.5464 | 0.4731 | 1.785 |
| 8 | Pablo Sarabia García | 201 | 0.9065 | 0.7343 | 1.765 |
| 9 | Alejandro Grimaldo García | 1384 | 0.4139 | 0.3770 | 1.648 |
| 10 | Daniel Wass | 210 | 0.4138 | 0.3770 | 1.647 |
| 11 | Philippe Coutinho Correia | 465 | 0.5004 | 0.4398 | 1.479 |
| 12 | Bruno Guimarães Rodriguez Moura | 102 | 0.4863 | 0.4296 | 1.385 |
| 13 | Thomas Müller | 271 | 0.4838 | 0.4277 | 1.368 |
| 14 | Ludovic Blas | 126 | 0.4515 | 0.4043 | 1.153 |
| 15 | Marcel Sabitzer | 347 | 0.4334 | 0.3912 | 1.033 |
| 16 | Adam Hložek | 179 | 0.4325 | 0.3906 | 1.027 |
| 17 | Mikel Merino Zazón | 208 | 0.4321 | 0.3903 | 1.024 |
| 18 | Pape Gueye | 113 | 0.4320 | 0.3902 | 1.024 |
| 19 | Tomáš Souček | 266 | 0.4264 | 0.3861 | 0.986 |
| 20 | Tomáš Holeš | 186 | 0.3154 | 0.3056 | 0.849 |
| 21 | Georgiy Sudakov | 106 | 0.4045 | 0.3703 | 0.840 |
| 22 | Lucas Tolentino Coelho de Lima | 215 | 0.3953 | 0.3636 | 0.779 |
| 23 | Eduardo Camavinga | 161 | 0.3054 | 0.2983 | 0.767 |
| 24 | Hugo Ekitike | 242 | 0.6776 | 0.5683 | 0.762 |
| 25 | Mikkel Damsgaard | 186 | 0.6726 | 0.5647 | 0.740 |
| 26 | Aleksandr Golovin | 146 | 0.3894 | 0.3593 | 0.740 |
| 27 | Warren Zaire Emery | 396 | 0.2949 | 0.2907 | 0.682 |
| 28 | Jamal Musiala | 323 | 0.6509 | 0.5490 | 0.645 |
| 29 | Luis Gerardo Chávez Magallón | 103 | 0.3752 | 0.3490 | 0.645 |
| 30 | Pedro González López | 2413 | 0.3699 | 0.3452 | 0.610 |
| 31 | Xavi Simons | 250 | 0.6423 | 0.5427 | 0.608 |
| 32 | Azor Matusiwa | 102 | 0.3691 | 0.3446 | 0.605 |
| 33 | Kaan Ayhan | 267 | 0.2846 | 0.2833 | 0.598 |
| 34 | Tijjani Reijnders | 247 | 0.3679 | 0.3437 | 0.596 |
| 35 | Xaver Schlager | 207 | 0.3659 | 0.3423 | 0.583 |
| 36 | Ruslan Malinovskiy | 153 | 0.6329 | 0.5359 | 0.566 |
| 37 | Carlos Soler Barragán | 565 | 0.3621 | 0.3395 | 0.558 |
| 38 | Piotr Zieliński | 339 | 0.3616 | 0.3391 | 0.554 |
| 39 | Aaron Ramsey | 336 | 0.3608 | 0.3385 | 0.549 |
| 40 | Jakub Moder | 124 | 0.3604 | 0.3382 | 0.546 |
| 41 | Konrad Laimer | 267 | 0.3589 | 0.3372 | 0.537 |
| 42 | Hidemasa Morita | 152 | 0.3578 | 0.3364 | 0.529 |
| 43 | Christian Dannemann Eriksen | 373 | 0.3553 | 0.3346 | 0.513 |
| 44 | Weston McKennie | 118 | 0.3482 | 0.3294 | 0.465 |
| 45 | Enis Bardhi | 126 | 0.3474 | 0.3288 | 0.460 |
| 46 | In-Beom Hwang | 216 | 0.3456 | 0.3275 | 0.448 |
| 47 | Mathias Jensen | 146 | 0.3441 | 0.3264 | 0.438 |
| 48 | Valentin Rongier | 217 | 0.2646 | 0.2688 | 0.436 |
| 49 | Marcos Llorente Moreno | 374 | 0.2546 | 0.2615 | 0.354 |
| 50 | Thomas Teye Partey | 165 | 0.3290 | 0.3155 | 0.337 |
| 51 | Khéphren Thuram-Ulien | 119 | 0.3280 | 0.3148 | 0.331 |
| 52 | Noussair Mazraoui | 140 | 0.2498 | 0.2581 | 0.316 |
| 53 | Georginio Wijnaldum | 466 | 0.3239 | 0.3118 | 0.304 |
| 54 | Adrien Rabiot | 621 | 0.3220 | 0.3104 | 0.291 |
| 55 | Jordan Ferri | 115 | 0.3192 | 0.3084 | 0.272 |
| 56 | Alex Král | 102 | 0.3178 | 0.3074 | 0.263 |
| 57 | Seko Fofana | 158 | 0.3138 | 0.3045 | 0.236 |
| 58 | Kobbie Mainoo | 179 | 0.3097 | 0.3015 | 0.209 |
| 59 | Celso Borges Mora | 100 | 0.3087 | 0.3008 | 0.202 |
| 60 | Carlos Henrique Casimiro | 320 | 0.3081 | 0.3004 | 0.198 |
| 61 | Jackson Irvine | 112 | 0.3038 | 0.2972 | 0.170 |
| 62 | Grzegorz Krychowiak | 187 | 0.3030 | 0.2967 | 0.164 |
| 63 | Mateo Kovačić | 720 | 0.3025 | 0.2963 | 0.161 |
| 64 | Vitor Machado Ferreira | 1764 | 0.3003 | 0.2947 | 0.146 |
| 65 | Maxence Caqueret | 115 | 0.3000 | 0.2945 | 0.144 |
| 66 | Saša Lukić | 290 | 0.2996 | 0.2942 | 0.142 |
| 67 | Rodrigo Javier De Paul | 458 | 0.2957 | 0.2914 | 0.116 |
| 68 | Arda Güler | 149 | 0.5286 | 0.4602 | 0.109 |
| 69 | Sergi Roberto Carnicer | 777 | 0.2243 | 0.2396 | 0.109 |
| 70 | Fabián Ruiz Peña | 1715 | 0.2919 | 0.2886 | 0.090 |
| 71 | Ousmane Dembélé | 1126 | 0.5094 | 0.4463 | 0.025 |
| 72 | André-Frank Zambo Anguissa | 118 | 0.2821 | 0.2815 | 0.025 |
| 73 | Youssouf Fofana | 208 | 0.2819 | 0.2813 | 0.024 |
| 74 | Sergio Busquets i Burgos | 2994 | 0.2817 | 0.2812 | 0.022 |
| 75 | Jude Bellingham | 599 | 0.2776 | 0.2782 | -0.005 |
| 76 | Enzo Le Fée | 111 | 0.2764 | 0.2773 | -0.013 |
| 77 | Scott McTominay | 151 | 0.2089 | 0.2284 | -0.016 |
| 78 | Jerdy Schouten | 288 | 0.2758 | 0.2769 | -0.017 |
| 79 | Toni Kroos | 855 | 0.2756 | 0.2768 | -0.018 |
| 80 | Kristoffer Olsson | 138 | 0.2756 | 0.2767 | -0.019 |
| 81 | Mohammed Kanoo | 125 | 0.2734 | 0.2752 | -0.033 |
| 82 | İlkay Gündoğan | 469 | 0.2726 | 0.2746 | -0.038 |
| 83 | Salis Abdul Samed | 136 | 0.2721 | 0.2742 | -0.042 |
| 84 | Ethan Ampadu | 153 | 0.2672 | 0.2707 | -0.074 |
| 85 | Joey Veerman | 136 | 0.2654 | 0.2693 | -0.087 |
| 86 | Himad Abdelli | 121 | 0.2631 | 0.2677 | -0.102 |
| 87 | Frenkie de Jong | 3012 | 0.2610 | 0.2662 | -0.116 |
| 88 | Pierre-Emile Højbjerg | 826 | 0.2596 | 0.2652 | -0.125 |
| 89 | Atakan Karazor | 111 | 0.2574 | 0.2636 | -0.140 |
| 90 | Marcos Aoás Corrêa | 3109 | 0.1937 | 0.2174 | -0.140 |
| 91 | Juraj Kucka | 204 | 0.2566 | 0.2630 | -0.145 |
| 92 | Marco Verratti | 3518 | 0.2550 | 0.2618 | -0.156 |
| 93 | Johan Gastien | 211 | 0.2543 | 0.2613 | -0.160 |
| 94 | Romano Schmid | 152 | 0.2538 | 0.2610 | -0.163 |
| 95 | Yunus Dimoara Musah | 175 | 0.2523 | 0.2599 | -0.173 |
| 96 | Moriba Kourouma Kourouma | 309 | 0.2518 | 0.2595 | -0.177 |
| 97 | Miralem Pjanić | 620 | 0.2479 | 0.2566 | -0.203 |
| 98 | Remo Freuler | 552 | 0.2446 | 0.2543 | -0.225 |
| 99 | Niklas Süle | 222 | 0.1830 | 0.2096 | -0.226 |
| 100 | Rafael Alexandre Conceição Leão | 125 | 0.4514 | 0.4043 | -0.229 |
| 101 | Julian Draxler | 109 | 0.4467 | 0.4008 | -0.249 |
| 102 | Jordan Brian Henderson | 250 | 0.2408 | 0.2515 | -0.250 |
| 103 | Nicolas Seiwald | 258 | 0.2407 | 0.2515 | -0.251 |
| 104 | Granit Xhaka | 3510 | 0.2387 | 0.2500 | -0.264 |
| 105 | Samuel Moutoussamy | 130 | 0.2361 | 0.2481 | -0.282 |
| 106 | Nicolò Barella | 454 | 0.2359 | 0.2480 | -0.283 |
| 107 | Jonas Martin | 116 | 0.2352 | 0.2474 | -0.288 |
| 108 | Pedro Chirivella Burgos | 193 | 0.2326 | 0.2456 | -0.305 |
| 109 | Benjamin Bourigeaud | 109 | 0.2325 | 0.2455 | -0.305 |
| 110 | Matthijs de Ligt | 150 | 0.1715 | 0.2012 | -0.320 |
| 111 | Andrei Girotto | 132 | 0.1714 | 0.2012 | -0.321 |
| 112 | Bernardo Mota Veiga de Carvalho e Silva | 542 | 0.2294 | 0.2432 | -0.326 |
| 113 | Florian Grillitsch | 320 | 0.2291 | 0.2430 | -0.328 |
| 114 | Enzo Fernandez | 406 | 0.2289 | 0.2429 | -0.330 |
| 115 | Kristjan Asllani | 159 | 0.2269 | 0.2414 | -0.343 |
| 116 | Amadou Onana | 316 | 0.2264 | 0.2411 | -0.346 |
| 117 | Leon Goretzka | 217 | 0.2264 | 0.2411 | -0.346 |
| 118 | Rodrigo Hernández Cascante | 1191 | 0.1661 | 0.1974 | -0.364 |
| 119 | Youri Tielemans | 349 | 0.2234 | 0.2389 | -0.366 |
| 120 | Teun Koopmeiners | 101 | 0.2219 | 0.2379 | -0.376 |
| 121 | Benjamin André | 153 | 0.2218 | 0.2378 | -0.377 |
| 122 | Bryan Cristante | 177 | 0.2215 | 0.2375 | -0.379 |
| 123 | Mario Götze | 110 | 0.2177 | 0.2348 | -0.404 |
| 124 | Luka Modrić | 954 | 0.2168 | 0.2341 | -0.410 |
| 125 | Jorge Luiz Frello Filho | 694 | 0.2167 | 0.2341 | -0.411 |
| 126 | Idrissa Gana Gueye | 1086 | 0.2139 | 0.2320 | -0.429 |
| 127 | Jorge Resurrección Merodio | 562 | 0.2136 | 0.2318 | -0.432 |
| 128 | Orkun Kökçü | 109 | 0.2129 | 0.2313 | -0.436 |
| 129 | Albin Ekdal | 113 | 0.2125 | 0.2310 | -0.438 |
| 130 | Danilo Luís Hélio Pereira | 2494 | 0.1561 | 0.1901 | -0.445 |
| 131 | Robert Andrich | 1533 | 0.2107 | 0.2297 | -0.451 |
| 132 | Joseff Morrell | 115 | 0.2098 | 0.2290 | -0.457 |
| 133 | Morten Hjulmand | 202 | 0.2094 | 0.2288 | -0.459 |
| 134 | Nadiem Amiri | 135 | 0.2074 | 0.2273 | -0.472 |
| 135 | Wataru Endo | 171 | 0.2071 | 0.2271 | -0.475 |
| 136 | Mykola Shaparenko | 312 | 0.2061 | 0.2264 | -0.481 |
| 137 | Hakan Çalhanoğlu | 348 | 0.2035 | 0.2245 | -0.498 |
| 138 | Rodrigo Bentancur Colmán | 137 | 0.2020 | 0.2234 | -0.509 |
| 139 | Ellyes Joris Skhiri | 168 | 0.2000 | 0.2220 | -0.522 |
| 140 | Exequiel Alejandro Palacios | 1634 | 0.2000 | 0.2219 | -0.522 |
| 141 | Mario Lemina | 105 | 0.1999 | 0.2219 | -0.523 |
| 142 | Marten de Roon | 251 | 0.1990 | 0.2213 | -0.528 |
| 143 | Boubacar Kamara | 130 | 0.1990 | 0.2212 | -0.529 |
| 144 | Aurélien Djani Tchouaméni | 812 | 0.1978 | 0.2204 | -0.536 |
| 145 | Azzedine Ounahi | 248 | 0.1947 | 0.2181 | -0.557 |
| 146 | El Chadaille Bitshiabu | 282 | 0.1419 | 0.1798 | -0.560 |
| 147 | N'Golo Kanté | 521 | 0.1933 | 0.2171 | -0.566 |
| 148 | Christian Nørgaard | 137 | 0.1923 | 0.2164 | -0.573 |
| 149 | Lovro Majer | 236 | 0.3707 | 0.3457 | -0.582 |
| 150 | Axel Witsel | 332 | 0.1887 | 0.2137 | -0.598 |
| 151 | Stanislav Lobotka | 244 | 0.1881 | 0.2133 | -0.601 |
| 152 | Mattéo Guendouzi Olié | 206 | 0.1844 | 0.2106 | -0.626 |
| 153 | João Maria Lobo Alves Palhinha Gonçalves | 245 | 0.1834 | 0.2099 | -0.633 |
| 154 | Leandro Daniel Paredes | 858 | 0.1824 | 0.2092 | -0.639 |
| 155 | Paul Pogba | 250 | 0.1813 | 0.2084 | -0.647 |
| 156 | Woo-Young Jung | 181 | 0.1808 | 0.2080 | -0.650 |
| 157 | Renato Júnior Luz Sanches | 783 | 0.1782 | 0.2061 | -0.667 |
| 158 | Aaron Mooy | 188 | 0.1759 | 0.2044 | -0.683 |
| 159 | Moisés Isaac Caicedo Corozo | 134 | 0.1749 | 0.2038 | -0.689 |
| 160 | Laurent Abergel | 144 | 0.1742 | 0.2032 | -0.694 |
| 161 | Thomas Delaney | 288 | 0.1724 | 0.2019 | -0.706 |
| 162 | Timi Elšnik | 110 | 0.1720 | 0.2017 | -0.708 |
| 163 | András Schäfer | 190 | 0.1714 | 0.2012 | -0.712 |
| 164 | Trent Alexander-Arnold | 112 | 0.1663 | 0.1975 | -0.746 |
| 165 | Batista Mendy | 101 | 0.1643 | 0.1960 | -0.760 |
| 166 | Rúben Diogo Da Silva Neves | 332 | 0.1627 | 0.1949 | -0.770 |
| 167 | Marcelo Brozović | 833 | 0.1616 | 0.1941 | -0.778 |
| 168 | Sergio Ramos García | 2193 | 0.1129 | 0.1588 | -0.796 |
| 169 | Ivan Ilić | 152 | 0.1549 | 0.1893 | -0.822 |
| 170 | Declan Rice | 1050 | 0.1531 | 0.1879 | -0.835 |
| 171 | Federico Santiago Valverde Dipetta | 221 | 0.1470 | 0.1835 | -0.875 |
| 172 | William Silva de Carvalho | 264 | 0.1454 | 0.1823 | -0.886 |
| 173 | Joan Jordán Moreno | 119 | 0.1402 | 0.1786 | -0.920 |
| 174 | Giorgi Kochorashvili | 156 | 0.1393 | 0.1779 | -0.926 |
| 175 | Ádám Nagy | 161 | 0.1391 | 0.1778 | -0.928 |
| 176 | Andreas Christensen | 669 | 0.0925 | 0.1440 | -0.961 |
| 177 | Joe Allen | 144 | 0.1336 | 0.1738 | -0.964 |
| 178 | Callum McGregor | 191 | 0.1306 | 0.1716 | -0.984 |
| 179 | Corentin Tolisso | 114 | 0.1289 | 0.1704 | -0.995 |
| 180 | Martín Zubimendi Ibáñez | 186 | 0.1285 | 0.1701 | -0.999 |
| 181 | Angel Gomes | 120 | 0.1257 | 0.1681 | -1.017 |
| 182 | Nampalys Mendy | 140 | 0.1206 | 0.1644 | -1.051 |
| 183 | Jordan Veretout | 148 | 0.1205 | 0.1643 | -1.052 |
| 184 | Leander Dendoncker | 171 | 0.1200 | 0.1639 | -1.055 |
| 185 | Serhii Sydorchuk | 184 | 0.1171 | 0.1618 | -1.074 |
| 186 | Kieffer Roberto Francisco Moore | 103 | 0.2474 | 0.2563 | -1.122 |
| 187 | Sofyan Amrabat | 276 | 0.1073 | 0.1547 | -1.139 |
| 188 | Ander Herrera Agüera | 281 | 0.1072 | 0.1547 | -1.140 |
| 189 | Adam Gnezda Čerin | 134 | 0.1052 | 0.1532 | -1.153 |
| 190 | Jhegson Sebastián Méndez Carabalí | 130 | 0.1017 | 0.1506 | -1.177 |
| 191 | Tyler Adams | 235 | 0.1001 | 0.1495 | -1.187 |
| 192 | Billy Gilmour | 145 | 0.0964 | 0.1468 | -1.212 |
| 193 | Aïssa Bilal Laïdouni | 163 | 0.0882 | 0.1409 | -1.267 |
| 194 | Nemanja Gudelj | 114 | 0.0877 | 0.1405 | -1.270 |
| 195 | Phil Foden | 479 | 0.2110 | 0.2299 | -1.282 |
| 196 | Dixon Jair Arroyo Espinoza | 105 | 0.0743 | 0.1308 | -1.359 |
| 197 | Emre Can | 111 | 0.0707 | 0.1282 | -1.383 |
| 198 | Kalvin Phillips | 328 | 0.0399 | 0.1059 | -1.588 |
| 199 | Taras Stepanenko | 159 | 0.0302 | 0.0988 | -1.653 |
| 200 | Petr Ševčík | 120 | -0.0168 | 0.0647 | -2.279 |
## 7. Step 5 -- how the dimensions relate
At the Step 3 threshold (100 passes), pooled fully per player across contexts (Decision/Risk/move_on_speed/hold_variation/median_time_on_ball from raw per-observation files; completion_pct/progressive_passes_per_90/xa_per_90 as an eligible-passes-weighted average across a player's `player_season_metrics.parquet` rows -- the one place a second aggregation layer was unavoidable, disclosed in the script's own docstring).

### Overall (n=537)
| metric | decision_per_100 | risk_per_100 | move_on_speed | hold_variation | median_time_on_ball | completion_pct | progressive_passes_per_90 | xa_per_90 |
|---|---|---|---|---|---|---|---|---|
| decision_per_100 | 1.00 | 0.80 | -0.02 | 0.07 | -0.20 | -0.54 | -0.39 | 0.57 |
| risk_per_100 | 0.80 | 1.00 | 0.02 | 0.08 | -0.08 | -0.50 | -0.29 | 0.56 |
| move_on_speed | -0.02 | 0.02 | 1.00 | -0.13 | -0.08 | -0.13 | -0.02 | -0.07 |
| hold_variation | 0.07 | 0.08 | -0.13 | 1.00 | 0.54 | 0.06 | 0.00 | 0.05 |
| median_time_on_ball | -0.20 | -0.08 | -0.08 | 0.54 | 1.00 | 0.31 | 0.30 | -0.06 |
| completion_pct | -0.54 | -0.50 | -0.13 | 0.06 | 0.31 | 1.00 | 0.48 | -0.31 |
| progressive_passes_per_90 | -0.39 | -0.29 | -0.02 | 0.00 | 0.30 | 0.48 | 1.00 | -0.13 |
| xa_per_90 | 0.57 | 0.56 | -0.07 | 0.05 | -0.06 | -0.31 | -0.13 | 1.00 |

Pairs with |r| > 0.7: decision_per_100 / risk_per_100 (r=0.8048)
Decision vs. xA per 90: r=0.5651.

### DEEP / DEFENSIVE MIDFIELD only (n=200)
| metric | decision_per_100 | risk_per_100 | move_on_speed | hold_variation | median_time_on_ball | completion_pct | progressive_passes_per_90 | xa_per_90 |
|---|---|---|---|---|---|---|---|---|
| decision_per_100 | 1.00 | 0.75 | 0.16 | 0.14 | -0.06 | -0.46 | -0.26 | 0.56 |
| risk_per_100 | 0.75 | 1.00 | 0.18 | 0.14 | 0.02 | -0.45 | -0.14 | 0.57 |
| move_on_speed | 0.16 | 0.18 | 1.00 | -0.14 | -0.24 | -0.21 | -0.01 | 0.08 |
| hold_variation | 0.14 | 0.14 | -0.14 | 1.00 | 0.44 | -0.04 | -0.04 | 0.13 |
| median_time_on_ball | -0.06 | 0.02 | -0.24 | 0.44 | 1.00 | 0.26 | 0.25 | 0.04 |
| completion_pct | -0.46 | -0.45 | -0.21 | -0.04 | 0.26 | 1.00 | 0.46 | -0.26 |
| progressive_passes_per_90 | -0.26 | -0.14 | -0.01 | -0.04 | 0.25 | 0.46 | 1.00 | 0.03 |
| xa_per_90 | 0.56 | 0.57 | 0.08 | 0.13 | 0.04 | -0.26 | 0.03 | 1.00 |

Pairs with |r| > 0.7: decision_per_100 / risk_per_100 (r=0.7506)
Decision vs. xA per 90 (within position): r=0.5572.

**Discrepancy with Task 25, disclosed**: Task 25's own separation check reported Decision vs. xA per 90 at r=+0.71 (overall), computed on per-(player, competition, season) units at a >=200-pass floor, not pooled across a player's contexts. This task's Section 7 number (r=0.5651 overall, r=0.5572 within position) uses the Step 3 threshold (100, not 200) and pools each player's Decision and reference rates fully across all their contexts, per the brief's own Step 4/5 construction. The two numbers are not computed the same way and should not be read as a replication or a contradiction of each other; both are reported as computed.

The only pair exceeding |0.7| in both tables is Decision vs. Risk itself (0.80 overall, 0.75 within position) -- both quantities share the same "chosen minus policy-weighted alternative" construction (EV and variance respectively), so a large share of this correlation is structural, not a new empirical finding. Reported plainly, not interpreted further.

## 8. Deviations from the brief
None from the hard rules. Disclosed adaptations, all necessary and none
silent:
- One holdout match (3845506) has an events file but no frames file
  (Task 23's own recorded 360-data parse failure). Every Step 1(b)
  script that reads frames unconditionally (`task26_holdout_evidence.py`,
  `grid_holdout.py`) was adapted with an explicit skip-and-count guard
  rather than crashing or silently modifying `grid.py`/`task24_evidence.py`
  themselves.
- PH-O2/PH-O3 (Step 1(c)) are reported as NOT COMPUTED with reasons
  (near-singular team-context design on only 3 holdout competition-seasons),
  per the brief's own explicit instruction to say which specifications
  cannot be computed and why.
- Step 5's correlation pooling required one second-aggregation-layer
  choice (an eligible-passes-weighted average of `player_season_metrics.parquet`'s
  own per-season rates, since no lower-level per-pass file exists for
  completion/progressive/xA) -- disclosed in the script's own docstring
  and Section 7 above.

## 9. Problems and surprises
- The player-level threshold (Step 3) came out at 100 passes -- the
  LOWEST value tested, not a value in the middle of the sweep -- with
  median reliability already at 0.7252, comfortably above the 0.70 bar.
  This is a direct, visible consequence of Task 24/25's coordinate fix:
  the same reliability sweep at 200 passes was 0.615 as recently as
  Task 19d and is now 0.8191 (Task 25's own T6).
- The naive (lowercase-substring) name matcher first tried for the
  fixed 13-name list mismatched 3 of 13 players (Modric's diacritic,
  Rodri's ambiguous substring match against 4 different "Rodrigo"s,
  and consequently missed matches for Pedri/Gundogan/Modric) before
  `task14b_leaderboards_referee2.py`'s own established fix
  (`normalize_name` + `NICKNAME_ALIASES`) was ported in -- exactly the
  same failure mode that project's own results page already documented
  once. Caught and fixed before this page was written, not left in.
- Kimmich and Rodri are classified as "Defender" by the coarse
  `position_group()` split (their own MODAL raw StatsBomb position in
  this sample apparently falls under a "Back" label in enough events to
  win the mode), even though both are commonly discussed as deep-lying
  midfielders. This is a known limitation of the existing coarse
  grouping, not something this task's DEEP/DEFENSIVE MIDFIELD
  definition can fix (it operates on the same underlying position
  field) -- disclosed, not corrected unilaterally.

## 10. Questions for the research lead
1. Section 7 reports a real numerical discrepancy with Task 25's own
   Decision-vs-xA-per-90 figure (0.71 there vs. 0.57/0.56 here), driven
   by a different threshold (200 vs. 100) and a different pooling
   method (per-unit vs. fully pooled per player). Is the fully-pooled,
   Step-3-threshold version the one that should be treated as
   authoritative going forward, or should Task 25's per-unit,
   200-threshold version remain the reference figure for this
   relationship specifically?
2. The DEEP/DEFENSIVE MIDFIELD definition (raw position string
   containing "Defensive Midfield") is a disclosed assumption with no
   prior specification anywhere in this codebase. Should this become a
   standing definition (e.g., added to a shared position-grouping
   module) for future tasks, or is it scoped to this task's own output
   only?
3. Kimmich/Rodri's "Defender" classification under the existing coarse
   `position_group()` (Section 9) sits oddly next to how both are
   discussed footballing-wise. Should the coarse grouping be revisited
   in a future task, or is it left as-is since it is descriptive
   context, not a criterion?

## 11. Files produced
- `src/engine_v2/task26_holdout_evidence.py`, `grid_holdout.py`,
  `pass_success_score_holdout.py`, `ev_compute_holdout.py`,
  `policy_and_decision_holdout.py`, `outcome_validation_holdout.py` --
  new. Step 1's holdout-replication pipeline (frozen engine v5, no
  retraining anywhere).
- `src/tempo/redesign_metrics_v2.py`, `redesign_reliability_v2.py` --
  new. Step 2's corrected-coordinate tempo re-run (`redesign_metrics.py`
  itself untouched, per the established "new file, not an in-place
  edit" convention for reusing a frozen script's other functions).
- `src/engine_v2/task26_step3_threshold.py`,
  `task26_step4_leaderboard.py`, `task26_step5_correlations.py` -- new.
  Steps 3-5.
- New data artifacts under `data/processed/engine_v2/` (`options_parts_holdout/`,
  `options_scored_holdout/`, `options_ev_holdout/`,
  `pass_policy_summary_holdout.parquet`, `pass_der_holdout.parquet`)
  and `data/processed/` (`tempo_redesign_metrics_v2.parquet`,
  `tempo_redesign_move_residuals_v2.parquet`,
  `tempo_redesign_hold_residuals_v2.parquet`, `leaderboard_v5.parquet`)
  and new summary JSONs under `data/` -- not committed, `data/` is
  never committed. `data/raw_holdout/` itself was never modified.
- `docs/results/26-holdout-and-player-results.md` -- this file.
- Commit hashes: `110a620` (Step 0, brief alone), `bc43c81` (this
  results page + Steps 1-5 code). Step 6 will be committed separately
  per the brief's own instruction.

## 12. Confidence
High confidence in Step 1's gate: it is a genuine out-of-sample test
(126 matches from a different competition tier and gender never seen
by any part of the pipeline), scored with literally frozen model
artifacts (verified: no `.fit()`/`.train()` call anywhere in the Step
1(b) chain), and it passes with a wide margin (p=6.7e-06). High
confidence in Steps 2-5's numbers, since every one reuses an
already-validated function via direct import or monkeypatch, with the
one new piece of logic (DEEP/DEFENSIVE MIDFIELD) disclosed as an
assumption in the same spirit as the codebase's own existing
`position_group()`. The weakest links: (a) Section 7's discrepancy with
Task 25's own correlation figure, not yet reconciled with the research
lead (Section 10, Q1); (b) the holdout's PH-O2/PH-O3 gaps (Section 3),
which mean this replication is weaker evidence for the
team-context-sensitive specifications than for H-O1/H-O2/PH-O1/PH-O4;
(c) Step 6 (Study B) is not yet in this page -- reported separately per
the brief's own explicit allowance.
