# Task 14b: Leaderboards and Referee 2
Date: 2026-09-25
Status: COMPLETE

## 1. Headline
Leaderboards were built for all three objectives (160 qualifying players each, >=200 eligible passes pooled across contexts). O1 and O2 rank players very similarly (Spearman rho=0.906); O3 diverges more from both (rho=0.793 vs O1, 0.731 vs O2). Referee 2 could match only 23 of 77 expert-selected players to a qualifying (player, competition-season) unit — most Team of the Season picks, especially goalkeepers and forwards, do not reach 200 eligible passes within a single competition-season even though many qualify in the pooled leaderboard; MLS 2023 has **zero** qualifying units at all (the sample only covers 6 MLS matches). The pre-registered power check (run and reported before any AUC, per Amendment v3-4.2) finds a minimum detectable AUC improvement of 0.267 at 80% power against a 0.10 threshold — **Referee 2 is UNDERPOWERED** for all three objectives, and its result is indicative only, as the plan requires. The AUC test itself (run anyway, as instructed) shows every CI spanning zero for all three objectives, both including and excluding World Cup 2022. Combined with Task 14a's Referee 1 result (all three NOT WIN), plan v3 section 5's rule leaves **no objective describable as BETTER**.

## 2. What I did
Governing spec: `docs/specs/analysis-plan-v3.md` (Amendments v3-1 to v3-5) + `docs/specs/task-14b-leaderboards-referee2.md`, plan v3 sections 4 and 5. Reproducing command: `python src/decision_engine/task14b_leaderboards_referee2.py`.

- **Step 0**: replaced the Bundesliga 2023/24 rows in `data/expert_lists/selections.csv` with the VDV XI from Amendment v3-5.2 (source_org "VDV", the given URL, publication_date 2024-09-10), leaving every other row untouched. Committed Amendment v3-5 and the corrected CSV together (commit `a4f62a7`, SHA-256 of `analysis-plan-v3.md` recorded at commit time: `fcce962ebcdea53471e6dd49cc12d845a607f862870d92ab55e31e5ca066fde0`).
- **Step 1 (leaderboards)**: built per-pass Decision for O1 (`decompose.build_per_pass_table`, unchanged), O2 and O3 (reusing Task 14a's `build_per_pass_o2`/`build_per_pass_o3`, which already handle O2's positional alignment and O3's team-strength-bin coverage gap). A new `build_leaderboard` reuses Task 12's exact `step2_leaderboard` construction (>=200-pass floor, shrinkage at reliability 0.744) but returns the FULL ranked table, not just top/bottom 20, written to `data/processed/leaderboards_o1_o2_o3.parquet`. Looked up the plan v3 section 5 fixed player list by name (see Section 4 for the matching method and a bug it caught) and computed pairwise Spearman correlations between the three objectives' shrunken-Decision rankings.
- **Step 2 (match + power, in that order, per the user's explicit instruction and Amendment v3-4.2)**: built (player, competition, season) units with their own >=200-pass floor (a stricter, separate qualification from the pooled leaderboard), restricted to the 7 competition-seasons with a compiled selection (La Liga has none). Matched each expert-list row to a qualifying unit by normalized name within that row's own competition-season. Reported every unmatched row with its reason. Computed the minimum AUC improvement detectable at 80% power (Hanley-McNeil-based, see Section 4) from the resulting positive/negative counts, BEFORE running any AUC comparison, exactly as instructed.
- **Step 3 (Referee 2 AUC test)**: built each matched unit's team-strength baseline from real final standings / tournament results (external research, see Section 4), z-scored within its own competition-season, and fit `selection ~ team_strength_z` (model i) vs `selection ~ team_strength_z + decision_z` (model ii), comparing AUC with a 1,000-draw competition-season-clustered bootstrap CI on the difference. Reported both the full population and the v3-5.4-required sensitivity excluding World Cup 2022 rows, for all three objectives.
- **Step 4**: restated Task 14a's Referee 1 verdicts (all NOT WIN) alongside Referee 2's PASS/FAIL, and applied plan v3 section 5's rule mechanically.

## 3. Numbers

### Leaderboards
n qualifying players: O1=160, O2=160, O3=160 (of the same underlying eligible-pass population; the count is identical across objectives here because the >=200 pooled-pass floor doesn't depend on which objective's Decision is being averaged, only on how many eligible passes a player has).

**O1 top 20** (rank, name, position, competitions n/a here — shown in the parquet — passes, raw Decision/100, shrunken Decision/100):

| rank | player | position | n passes | raw | shrunken |
|---|---|---|---|---|---|
| 1 | Florian Grillitsch | Midfielder | 219 | 0.4711 | 0.4003 |
| 2 | Mykola Shaparenko | Midfielder | 207 | 0.4054 | 0.3515 |
| 3 | Moriba Kourouma Kourouma | Midfielder | 201 | 0.3946 | 0.3434 |
| 4 | Philippe Coutinho Correia | Midfielder | 295 | 0.3685 | 0.3240 |
| 5 | İlkay Gündoğan | Midfielder | 320 | 0.3599 | 0.3176 |
| 6 | Joshua Kimmich | Defender | 564 | 0.3497 | 0.3100 |
| 7 | Pedro González López (Pedri) | Midfielder | 1567 | 0.3472 | 0.3081 |
| 8 | Ronald Federico Araújo da Silva | Defender | 513 | 0.3256 | 0.2920 |
| 9 | Rodrigo Hernández Cascante (Rodri) | Defender | 887 | 0.3148 | 0.2841 |
| 10 | William Saliba | Defender | 369 | 0.3136 | 0.2831 |
| 11 | Hakan Çalhanoğlu | Midfielder | 227 | 0.3120 | 0.2819 |
| 12 | Warren Zaire Emery | Defender | 265 | 0.3095 | 0.2801 |
| 13 | Eric García Martret | Defender | 215 | 0.3069 | 0.2782 |
| 14 | Georginio Wijnaldum | Midfielder | 274 | 0.3019 | 0.2744 |
| 15 | Bernardo Mota Veiga de Carvalho e Silva | Midfielder | 363 | 0.3005 | 0.2734 |
| 16 | Nicolò Barella | Midfielder | 290 | 0.2996 | 0.2727 |
| 17 | Illia Zabarnyi | Defender | 341 | 0.2960 | 0.2700 |
| 18 | Sergino Dest | Defender | 775 | 0.2926 | 0.2675 |
| 19 | Sergi Roberto Carnicer | Defender | 523 | 0.2908 | 0.2662 |
| 20 | Pau Francisco Torres | Defender | 522 | 0.2882 | 0.2642 |

**O1 bottom 20** (worst first):

| rank | player | position | n passes | raw | shrunken |
|---|---|---|---|---|---|
| 160 | Ivan Perišić | Forward | 205 | -0.1213 | -0.0404 |
| 159 | Kevin De Bruyne | Midfielder | 265 | -0.1150 | -0.0357 |
| 158 | Denzel Dumfries | Defender | 257 | -0.0832 | -0.0121 |
| 157 | Amine Adli | Midfielder | 227 | -0.0267 | 0.0300 |
| 156 | Daley Blind | Defender | 362 | 0.0005 | 0.0502 |
| 155 | Daniel Olmo Carvajal | Forward | 341 | 0.0104 | 0.0575 |
| 154 | Luke Shaw | Defender | 409 | 0.0242 | 0.0678 |
| 153 | Ángel Fabián Di María Hernández | Forward | 633 | 0.0267 | 0.0697 |
| 152 | Bukayo Saka | Forward | 251 | 0.0280 | 0.0707 |
| 151 | Abdou Diallo | Defender | 277 | 0.0429 | 0.0818 |
| 150 | Neymar da Silva Santos Junior | Forward | 1197 | 0.0494 | 0.0866 |
| 149 | Joakim Mæhle | Defender | 271 | 0.0591 | 0.0938 |
| 148 | Cristian Gabriel Romero | Defender | 246 | 0.0749 | 0.1055 |
| 147 | Kylian Mbappé Lottin | Forward | 1366 | 0.0769 | 0.1071 |
| 146 | Piotr Zieliński | Midfielder | 226 | 0.0777 | 0.1076 |
| 145 | Martin Braithwaite Christensen | Forward | 224 | 0.0805 | 0.1097 |
| 144 | Giovanni Di Lorenzo | Defender | 337 | 0.0842 | 0.1125 |
| 143 | Carlos Henrique Casimiro | Midfielder | 222 | 0.0848 | 0.1129 |
| 142 | Christian Dannemann Eriksen | Midfielder | 227 | 0.0932 | 0.1191 |
| 141 | Nordi Mukiele Mulere | Defender | 278 | 0.0935 | 0.1194 |

**O2 top 20**:

| rank | player | position | n passes | raw | shrunken |
|---|---|---|---|---|---|
| 1 | Marc Guehi | Defender | 314 | 0.3196 | 0.2829 |
| 2 | Ronald Federico Araújo da Silva | Defender | 513 | 0.3140 | 0.2788 |
| 3 | El Chadaille Bitshiabu | Defender | 233 | 0.3068 | 0.2734 |
| 4 | Mykola Shaparenko | Midfielder | 207 | 0.2950 | 0.2646 |
| 5 | Bernardo Mota Veiga de Carvalho e Silva | Midfielder | 363 | 0.2907 | 0.2614 |
| 6 | Gerard Piqué Bernabéu | Defender | 946 | 0.2899 | 0.2608 |
| 7 | Thilo Kehrer | Defender | 410 | 0.2828 | 0.2555 |
| 8 | Moriba Kourouma Kourouma | Midfielder | 201 | 0.2827 | 0.2555 |
| 9 | Hakan Çalhanoğlu | Midfielder | 227 | 0.2768 | 0.2510 |
| 10 | Georginio Wijnaldum | Midfielder | 274 | 0.2751 | 0.2498 |
| 11 | William Saliba | Defender | 369 | 0.2691 | 0.2453 |
| 12 | Florian Grillitsch | Midfielder | 219 | 0.2680 | 0.2445 |
| 13 | Sergi Roberto Carnicer | Defender | 523 | 0.2634 | 0.2411 |
| 14 | Pedro González López (Pedri) | Midfielder | 1567 | 0.2626 | 0.2405 |
| 15 | Jurriën David Norman Timber | Defender | 256 | 0.2611 | 0.2394 |
| 16 | Joshua Kimmich | Defender | 564 | 0.2608 | 0.2392 |
| 17 | Nicolás Hernán Otamendi | Defender | 376 | 0.2600 | 0.2386 |
| 18 | Eric García Martret | Defender | 215 | 0.2596 | 0.2382 |
| 19 | Axel Witsel | Midfielder | 246 | 0.2589 | 0.2377 |
| 20 | Stefan de Vrij | Defender | 355 | 0.2566 | 0.2360 |

**O2 bottom 20**:

| rank | player | position | n passes | raw | shrunken |
|---|---|---|---|---|---|
| 160 | Ivan Perišić | Forward | 205 | -0.1270 | -0.0494 |
| 159 | Denzel Dumfries | Defender | 257 | -0.0575 | 0.0023 |
| 158 | Kevin De Bruyne | Midfielder | 265 | -0.0402 | 0.0152 |
| 157 | Amine Adli | Midfielder | 227 | -0.0132 | 0.0353 |
| 156 | Daley Blind | Defender | 362 | 0.0006 | 0.0455 |
| 155 | Luke Shaw | Defender | 409 | 0.0319 | 0.0689 |
| 154 | Ángel Fabián Di María Hernández | Forward | 633 | 0.0387 | 0.0739 |
| 153 | Josip Juranović | Defender | 248 | 0.0582 | 0.0884 |
| 152 | Neymar da Silva Santos Junior | Forward | 1197 | 0.0641 | 0.0928 |
| 151 | Joakim Mæhle | Defender | 271 | 0.0676 | 0.0954 |
| 150 | Daniel Olmo Carvajal | Forward | 341 | 0.0692 | 0.0966 |
| 149 | Kylian Mbappé Lottin | Forward | 1366 | 0.0703 | 0.0974 |
| 148 | Abdou Diallo | Defender | 277 | 0.0800 | 0.1046 |
| 147 | Martin Braithwaite Christensen | Forward | 224 | 0.0813 | 0.1056 |
| 146 | Carlos Henrique Casimiro | Midfielder | 222 | 0.0861 | 0.1092 |
| 145 | Bruno Miguel Borges Fernandes | Midfielder | 312 | 0.0882 | 0.1108 |
| 144 | Bukayo Saka | Forward | 251 | 0.0892 | 0.1115 |
| 143 | Lionel Andrés Messi Cuccittini | Forward | 3536 | 0.0908 | 0.1126 |
| 142 | Jules Koundé | Defender | 425 | 0.0913 | 0.1130 |
| 141 | Giovanni Di Lorenzo | Defender | 337 | 0.0955 | 0.1162 |

**O3 top 20**:

| rank | player | position | n passes | raw | shrunken |
|---|---|---|---|---|---|
| 1 | Moriba Kourouma Kourouma | Midfielder | 201 | 0.0995 | 0.0843 |
| 2 | Philippe Coutinho Correia | Midfielder | 295 | 0.0771 | 0.0676 |
| 3 | Pedro González López (Pedri) | Midfielder | 1567 | 0.0762 | 0.0669 |
| 4 | Sergino Dest | Defender | 775 | 0.0717 | 0.0636 |
| 5 | Marcos Llorente Moreno | Defender | 217 | 0.0711 | 0.0631 |
| 6 | William Saliba | Defender | 369 | 0.0708 | 0.0630 |
| 7 | Eric García Martret | Defender | 215 | 0.0698 | 0.0622 |
| 8 | Axel Witsel | Midfielder | 246 | 0.0690 | 0.0616 |
| 9 | Rodrigo Hernández Cascante (Rodri) | Defender | 887 | 0.0670 | 0.0601 |
| 10 | Kyle Walker | Defender | 592 | 0.0669 | 0.0600 |
| 11 | Ricard Puig Martí | Midfielder | 202 | 0.0666 | 0.0598 |
| 12 | Sergi Roberto Carnicer | Defender | 523 | 0.0663 | 0.0596 |
| 13 | Gerard Piqué Bernabéu | Defender | 946 | 0.0660 | 0.0594 |
| 14 | Bernardo Mota Veiga de Carvalho e Silva | Midfielder | 363 | 0.0657 | 0.0591 |
| 15 | Phil Foden | Forward | 337 | 0.0655 | 0.0590 |
| 16 | Marc Guehi | Defender | 314 | 0.0650 | 0.0586 |
| 17 | Warren Zaire Emery | Defender | 265 | 0.0645 | 0.0582 |
| 18 | Stefan de Vrij | Defender | 355 | 0.0636 | 0.0576 |
| 19 | Jorge Luiz Frello Filho (Jorginho) | Midfielder | 513 | 0.0633 | 0.0573 |
| 20 | Clément Lenglet | Defender | 1542 | 0.0626 | 0.0568 |

**O3 bottom 20**:

| rank | player | position | n passes | raw | shrunken |
|---|---|---|---|---|---|
| 160 | Kevin De Bruyne | Midfielder | 265 | -0.0188 | -0.0037 |
| 159 | Ivan Perišić | Forward | 205 | -0.0172 | -0.0025 |
| 158 | Ángel Fabián Di María Hernández | Forward | 633 | -0.0057 | 0.0060 |
| 157 | Denzel Dumfries | Defender | 257 | -0.0021 | 0.0087 |
| 156 | Joakim Mæhle | Defender | 271 | -0.0006 | 0.0098 |
| 155 | Amine Adli | Midfielder | 227 | -0.0005 | 0.0099 |
| 154 | Piotr Zieliński | Midfielder | 226 | 0.0032 | 0.0127 |
| 153 | Daley Blind | Defender | 362 | 0.0062 | 0.0149 |
| 152 | Bukayo Saka | Forward | 251 | 0.0068 | 0.0153 |
| 151 | Neymar da Silva Santos Junior | Forward | 1162 | 0.0101 | 0.0178 |
| 150 | Raphaël Adelino José Guerreiro | Defender | 212 | 0.0109 | 0.0184 |
| 149 | Min Jae Kim | Defender | 235 | 0.0113 | 0.0186 |
| 148 | Cristian Gabriel Romero | Defender | 246 | 0.0136 | 0.0204 |
| 147 | Daniel Olmo Carvajal | Forward | 341 | 0.0138 | 0.0205 |
| 146 | Lionel Andrés Messi Cuccittini | Forward | 3514 | 0.0145 | 0.0210 |
| 145 | Abdou Diallo | Defender | 277 | 0.0163 | 0.0224 |
| 144 | Luke Shaw | Defender | 409 | 0.0169 | 0.0228 |
| 143 | Giovanni Di Lorenzo | Defender | 337 | 0.0173 | 0.0231 |
| 142 | Carlos Henrique Casimiro | Midfielder | 222 | 0.0174 | 0.0232 |
| 141 | Jannik Vestergaard | Defender | 364 | 0.0184 | 0.0240 |

### Fixed player list (plan v3 section 5), rank of N under each objective (of 160 qualifying)

| name | O1 rank | O2 rank | O3 rank | n passes |
|---|---|---|---|---|
| Kroos | 112 | 131 | 123 | 643 |
| Modric | 129 | 140 | 128 | 619 |
| Verratti | 117 | 124 | 103 | 2,677 (O3: 2,633) |
| Busquets | 39 | 103 | 31 | 2,146 |
| De Bruyne | 159 | 158 | 160 | 265 |
| Xhaka | 40 | 83 | 26 | 2,580 |
| de Jong | 47 | 75 | 38 | 2,139 |
| Kimmich | 6 | 16 | 39 | 564 |
| Rodri | 9 | 37 | 9 | 887 |
| Pedri | 7 | 14 | 3 | 1,567 |
| Gundogan | 5 | 26 | 51 | 320 |
| Grillitsch | 1 | 12 | 64 | 219 |
| Shaparenko | 2 | 4 | 110 | 207 |

(Rodri and Pedri required the nickname-alias fix in Section 4 to be found at all — see Section 5.)

### Spearman rank correlations (n=160)

| | O1 | O2 | O3 |
|---|---|---|---|
| O1 | 1.000 | 0.906 | 0.793 |
| O2 | 0.906 | 1.000 | 0.731 |
| O3 | 0.793 | 0.731 | 1.000 |

### Referee 2: matching, power, AUC

- Qualifying (player, competition, season) units (>=200 passes in that single context, restricted to the 7 covered competition-seasons): 119 for every objective (the count doesn't depend on which objective's Decision is averaged).
- Expert-list rows matched to a qualifying unit: **23/77**, identical for O1/O2/O3 (matching is about who qualifies at all, not about Decision values). 54 unmatched, all for the stated reason "name not found among this competition-season's qualifying units" (i.e., that player did not reach 200 eligible passes within that single competition-season) — see Section 5 for the full breakdown, including that **MLS 2023 contributes zero qualifying units of any kind**.
- **Power (computed and reported before any AUC, per Amendment v3-4.2)**: n_qualifying=119, n_pos=23, n_neg=96. Minimum AUC improvement detectable at 80% power (two-sided alpha=0.05): **0.267**. Since this exceeds 0.10, **Referee 2 is declared UNDERPOWERED** for all three objectives; its AUC result below cannot decide between objectives in either direction, including in O1's favour, per v3-4.2.
- **AUC test** (reported anyway, as instructed), team_strength_z (within-competition-season standardized) vs team_strength_z + decision_z, 1,000 competition-season-clustered bootstrap draws:

| objective | population | n | n_pos | n_neg | AUC(i) | AUC(ii) | diff | 95% CI | PASS? |
|---|---|---|---|---|---|---|---|---|---|
| O1 | full | 71 | 11 | 60 | 0.7068 | 0.7121 | +0.0053 | [0.000, 0.250] | FAIL |
| O1 | excl. World Cup | 48 | 9 | 39 | 0.7806 | 0.7749 | -0.0057 | [-0.0057, 0.0250] | FAIL |
| O2 | full | 71 | 11 | 60 | 0.7068 | 0.7152 | +0.0083 | [-0.025, 0.083] | FAIL |
| O2 | excl. World Cup | 48 | 9 | 39 | 0.7806 | 0.7863 | +0.0057 | [-0.025, 0.017] | FAIL |
| O3 | full | 71 | 11 | 60 | 0.7068 | 0.7318 | +0.0250 | [-0.017, 0.250] | FAIL |
| O3 | excl. World Cup | 48 | 9 | 39 | 0.7806 | 0.7521 | -0.0285 | [-0.0285, 0.0167] | FAIL |

All six CIs include zero. No objective passes Referee 2 under either variant.

### Section 4 (plan v3 section 5) verdict

| objective | Referee 1 (Task 14a) | Referee 2 (full) | Referee 2 (excl. WC) |
|---|---|---|---|
| O1 | NOT WIN | FAIL | FAIL |
| O2 | NOT WIN | FAIL | FAIL |
| O3 | NOT WIN | FAIL | FAIL |

**Objectives eligible to be described as BETTER (won Referee 1 and did not lose Referee 2): NONE.**

## 4. Deviations from the brief
1. **Team-strength construction.** The brief specifies "the team's final league position, or the tournament round it reached" but not how to make these comparable across four different competition formats pooled into one regression. Tournament round was coded as an ordinal scale (1=group stage ... 6=champion); league position was coded as `n_teams + 1 - position` (so a title also scores highest); both were then z-scored **within each competition-season** before pooling, so the model compares a team's standing relative to others in the *same* competition, not raw cross-competition magnitudes. All team-strength data was fetched from Wikipedia's own final-table/knockout-stage pages (Bundesliga 2023/24, Ligue 1 2021/22 and 2022/23 final tables; WC2022, Euro 2020, Euro 2024 knockout brackets; MLS 2023 regular-season standings) — see Section 5 for one correction caught mid-research (a hallucinated Euro 2024 final result).
2. **Power formula.** The brief requires a minimum-detectable-effect calculation at 80% power but doesn't name an estimator. Used the standard Hanley-McNeil (1982) nonparametric AUC-variance formula, evaluated at the conservative null AUC=0.5, treating the two nested models' AUC difference as independent (no prior estimate of their correlation exists in this project) — a conservative, worst-case simplification that only makes the "UNDERPOWERED" call more likely, never less.
3. **Name matching.** Expert-list names were matched to our own player names by normalizing (stripping diacritics/nicknames-in-quotes, case-folding) and requiring the expert name's tokens to be a subset of our full name's tokens — e.g. "Kroos" matches "Toni Kroos". A small, explicitly verified alias table (Section 5) was added for four footballing nicknames that are not token-subsets of the player's registered name at all.

## 5. Problems and surprises
1. **A name-matching bug was caught and fixed mid-task.** Plain token-subset matching initially reported "Rodri" and "Pedri" as absent from our own data entirely (fixed-list lookup) and from several competition-seasons' qualifying units (expert-list matching) — investigated because both are unambiguously present in the underlying data as major, heavily-passing players. The cause: "Rodri", "Pedri", "Jorginho" and "Marquinhos" are footballing nicknames that are not morphological substrings of the players' own registered names ("Rodrigo Hernández Cascante", "Pedro González López", "Jorge Luiz Frello Filho", "Marcos Aoás Corrêa" respectively) — unlike e.g. "Kroos", which is literally a token inside "Toni Kroos". Verified each of the four against this project's own player-name lookup before adding a small, disclosed alias table (Section 4.3). This raised the expert-list match count from 19/77 to 23/77 and changed the Referee 2 AUC test's n_pos from 8 to 11 (full population). No other unmatched name showed the same pattern on inspection (each remaining unmatched player's full candidate pool for that specific competition-season was printed and checked; none contained a plausible nickname match).
2. **MLS 2023 contributes zero qualifying (player, competition, season) units.** The study sample covers only 6 MLS matches; no player reaches 200 eligible passes within that alone (even though some MLS players do qualify in the pooled, all-contexts leaderboard). All 11 MLS Best XI rows are therefore unmatched for a real, reported reason, not a name-matching failure.
3. **Referee 2's actual AUC test population (n=71) excludes all three league competition-seasons, not just MLS.** Team-strength was z-scored *within* each competition-season for cross-competition comparability (Section 4.1) — but for Bundesliga 2023/24, Ligue 1 2021/22, and Ligue 1 2022/23, **every player who reaches the 200-pass floor happens to come from the same single team** (this sample's own focal-team construction, already noted in this project's journal: a handful of possession-dominant clubs are the ones whose full seasons were tracked). A single team per competition-season means zero within-group variance in team strength, so `team_strength_z` is undefined for those units and they are dropped from the AUC fit entirely. The result: Referee 2's AUC test, as constructed here, is **effectively a test on the three tournament competition-seasons only** (World Cup 2022, Euro 2020, Euro 2024 — 23+29+19=71 units), not the full 7-competition coverage Amendment v3-5.3 describes. This is a material limitation of this specific construction, disclosed here rather than smoothed over; a different (non-z-scored, or differently-normalized) team-strength construction might recover the league competition-seasons, but changing it now would be a methodology change I'm not authorized to make.
4. **A hallucinated fact was caught during team-strength research.** An initial fetch of Euro 2024's knockout results claimed Belgium was the runner-up; this was independently checked against multiple sources (UEFA.com, ESPN, NBC) and found wrong — the actual final was Spain 2-1 England. The corrected result is what's used in `EURO2024_ROUND`. Flagged here since it's exactly the kind of error this project's "verify, don't just fetch" discipline exists to catch.
5. **The leaderboards themselves reproduce Task 12's own known face-validity pattern for O1** (circulators near the top, recognized creators like Kroos/Modric/De Bruyne mid-to-low) and extend it descriptively to O2/O3 without new interpretation, as instructed.

## 6. Questions for the research lead
1. Given Referee 2's actual AUC test population is effectively the three tournament competition-seasons only (Section 5.3), should Task 14b be considered to have delivered a genuine (if underpowered) 7-competition Referee 2, or does the league competition-seasons' structural exclusion need its own disclosure in the paper beyond what's in this results page?
2. The four nickname aliases (Section 5.1) were found by manually inspecting every unmatched name's full candidate pool once. Should this alias table be extended pre-emptively for other known footballing nicknames not yet encountered (e.g., for a future task using more of the corpus), or is the current "verify what's actually unmatched" approach sufficient?

## 7. Files produced
- `src/decision_engine/task14b_leaderboards_referee2.py` — this task's full implementation. Committed together with the results page.
- `docs/specs/analysis-plan-v3.md` (Amendment v3-5) and the corrected `data/expert_lists/selections.csv` — committed together at Step 0, commit `a4f62a7`.
- `docs/specs/task-14b-leaderboards-referee2.md` — committed with the script and results page.
- `docs/results/14b-leaderboards-referee2.md` — this page.
- `data/processed/leaderboards_o1_o2_o3.parquet` — full ranked leaderboards for all three objectives (480 rows = 160 x 3). Not committed (data/).
- `data/task14b_leaderboards_referee2.json` — full machine-readable summary. Not committed.

## 8. Confidence
The leaderboard construction is a direct, unmodified reuse of Task 12's own code, so those numbers are as trustworthy as that precedent. The Referee 1 restatement is a direct read of Task 14a's own committed result. Referee 2 is the weakest part of this task by construction, not by execution error: it was explicitly pre-registered as likely underpowered (confirmed: MDE=0.267 against a 0.10 threshold), and this task's own team-strength design further narrows its real test population to three national-team tournaments (Section 5.3) — a limitation worth the research lead's attention independent of anything found here going wrong. The one genuine bug found (nickname matching) was caught by noticing an implausible "not found" result for players known to be major, active participants, then verified against the underlying data before being fixed — the same discipline that caught the hallucinated Euro 2024 result — rather than trusting either the first automated pass or the first fetched page.
