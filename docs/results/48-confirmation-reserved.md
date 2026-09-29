# Task 48: Confirmation on the untouched (RESERVED) data
Date: 2026-09-28
Status: COMPLETE (every section run; deviations in Section 4)

**This is the single use of the reserved data.** Every definition and test was fixed in the brief before any reserved file was opened.

## Checklist
| Section | Status |
|---|---|
| Step 0 — brief committed alone | COMPLETE (2161d66, by the research lead) |
| Data — ingest, counts, club vs national team, coordinate check | COMPLETE |
| Memory gate | COMPLETE (49% / 4.14 GB at 20:25 before ingest; 52% / 4.39 GB at 20:28 before build; 53% / 6.43 GB at 20:42 before tests) |
| Step 1 — measures, roles, DM list, baselines | COMPLETE |
| Step 2 — confirmatory family C1, C2, C3, C4, C6 (Holm) | COMPLETE (C4 ran: 127 movers ≥ 15) |
| Step 3 — report only | COMPLETE |

## 1. Headline
Two of five confirmatory tests are **CONFIRMED** on the reserved data:
- **C4:** press resistance travels between club and national team. 127 movers; r_true = +0.650, 95% CI [0.500, 0.797]; Holm p < 0.002.
- **C6:** team-adjusted press resistance predicts reaching the final third, all players. +1.281 pp per 100 pressured receptions per SD, 95% CI [0.988, 1.573]; Holm p = 4e-17; control positive.

Three are **not confirmed**, all with Holm p ≥ 0.24:
- **C1** (deep midfielders, PR2_flag_keep → Y_F3): +0.57, p = 0.30.
- **C2** (deep midfielders, W → Y_F3): −0.31, p = 0.28.
- **C3** (pressure deterrence): −0.0024 per SD, p = 0.080.

## 2. What I did
- `.venv/bin/python -W ignore src/engine_v2/task48_ingest.py` (data):
  - Takes the 64 reserved (competition, season) pairs from Task 46's saved listing.
  - Flattens their events with Task 44's `flatten` (statsbombpy's own functions) into `data/raw_reserved/`, and writes match tables.
  - Takes club vs national team from `competitions.json` `competition_international`.
  - Runs the coordinate check, task24_evidence part (i).
- `.venv/bin/python -W ignore src/engine_v2/task48_build.py` (Step 1):
  - Runs Task 44's builders with the event and match directories redirected: event-only g features, eligible passes (rule minus frame), receipt flags, Task 43 spells, Y_F3, net xG window 10.
  - Uses seeded 5 match folds (20260928).
  - Refits the PR2_flag baseline (`task44_gate.fit_baseline`) and the W baseline (`task46_part_b.fit_w`).
  - Assigns roles by Task 32's rule (≥100 eligible passes). Deep midfielder = ≥50% DM AND ≥300 eligible passes.
- `.venv/bin/python -W ignore src/engine_v2/task48_tests.py` (Steps 2-3):
  - **C1, C2, C6:** `task35_ptest.fe_fit` with event-only g (`task44_tests.crossfit_ev`) and the retention control (row keep_spell; S = other-match keep over all completed receptions, ≥100).
  - **C3:** Task 47's model, with p(context) refit (features incl. role code) and `fit_multi`.
  - **C4:** the Task 46 A-ii recipe on club vs international contexts (≥30 pressured receptions each), with p = 2 × share of bootstrap r_true ≤ 0.
  - **C6 A1:** each unit minus the team × competition-season mean.
  - **Holm** across the 5 tests.
  - **Report only:** stability (Task 44's `r1`), praised list (Task 41's `perm_test`) and DM tables (Task 29's method).
- Reproduce: the three commands above, in order.

## 3. Numbers

### Data — 64 reserved competition-seasons, 1,985 matches, 6,893,308 events
Coordinate check: 7,920 team-periods with shots; share with mean shot x > 60 = **0.9999**. Ingest problems: none.

| id | competition season | gender | type | matches | events |
|---|---|---|---|---|---|
| 2/44 | Premier League 2003/2004 | male | club | 38 | 129,401 |
| 11/1 | La Liga 2017/2018 | male | club | 36 | 136,538 |
| 11/2 | La Liga 2016/2017 | male | club | 34 | 124,813 |
| 11/21 | La Liga 2009/2010 | male | club | 35 | 128,395 |
| 11/22 | La Liga 2010/2011 | male | club | 33 | 130,899 |
| 11/23 | La Liga 2011/2012 | male | club | 37 | 145,993 |
| 11/24 | La Liga 2012/2013 | male | club | 32 | 130,457 |
| 11/25 | La Liga 2013/2014 | male | club | 31 | 118,016 |
| 11/26 | La Liga 2014/2015 | male | club | 38 | 142,957 |
| 11/278 | La Liga 1973/1974 | male | club | 1 | 2,974 |
| 11/37 | La Liga 2004/2005 | male | club | 7 | 22,204 |
| 11/38 | La Liga 2005/2006 | male | club | 17 | 57,668 |
| 11/39 | La Liga 2006/2007 | male | club | 26 | 92,656 |
| 11/4 | La Liga 2018/2019 | male | club | 34 | 131,702 |
| 11/40 | La Liga 2007/2008 | male | club | 27 | 96,913 |
| 11/41 | La Liga 2008/2009 | male | club | 31 | 107,089 |
| 11/42 | La Liga 2019/2020 | male | club | 33 | 129,058 |
| 12/86 | Serie A 1986/1987 | male | club | 1 | 3,005 |
| 16/1 | Champions League 2017/2018 | male | club | 1 | 3,497 |
| 16/2 | Champions League 2016/2017 | male | club | 1 | 3,400 |
| 16/21 | Champions League 2009/2010 | male | club | 1 | 3,410 |
| 16/22 | Champions League 2010/2011 | male | club | 1 | 4,326 |
| 16/23 | Champions League 2011/2012 | male | club | 1 | 4,695 |
| 16/24 | Champions League 2012/2013 | male | club | 1 | 3,338 |
| 16/25 | Champions League 2013/2014 | male | club | 1 | 4,263 |
| 16/26 | Champions League 2014/2015 | male | club | 1 | 3,433 |
| 16/27 | Champions League 2015/2016 | male | club | 1 | 4,708 |
| 16/276 | Champions League 1970/1971 | male | club | 1 | 3,529 |
| 16/277 | Champions League 1972/1973 | male | club | 1 | 3,195 |
| 16/37 | Champions League 2004/2005 | male | club | 1 | 4,648 |
| 16/39 | Champions League 2006/2007 | male | club | 1 | 3,064 |
| 16/4 | Champions League 2018/2019 | male | club | 1 | 3,165 |
| 16/41 | Champions League 2008/2009 | male | club | 1 | 3,329 |
| 16/44 | Champions League 2003/2004 | male | club | 1 | 3,223 |
| 16/71 | Champions League 1971/1972 | male | club | 1 | 3,027 |
| 16/76 | Champions League 1999/2000 | male | club | 1 | 3,384 |
| 35/75 | UEFA Europa League 1988/1989 | male | club | 3 | 10,086 |
| 37/281 | FA Women's Super League 2023/2024 | female | club | 132 | 495,189 |
| 37/4 | FA Women's Super League 2018/2019 | female | club | 107 | 356,568 |
| 37/42 | FA Women's Super League 2019/2020 | female | club | 87 | 292,253 |
| 37/90 | FA Women's Super League 2020/2021 | female | club | 131 | 443,295 |
| 43/269 | FIFA World Cup 1958 | male | national team | 2 | 7,341 |
| 43/270 | FIFA World Cup 1962 | male | national team | 1 | 3,754 |
| 43/272 | FIFA World Cup 1970 | male | national team | 6 | 20,030 |
| 43/3 | FIFA World Cup 2018 | male | national team | 64 | 227,825 |
| 43/51 | FIFA World Cup 1974 | male | national team | 6 | 19,259 |
| 43/54 | FIFA World Cup 1986 | male | national team | 3 | 8,471 |
| 43/55 | FIFA World Cup 1990 | male | national team | 1 | 3,140 |
| 49/107 | NWSL 2023 | female | club | 137 | 462,436 |
| 49/3 | NWSL 2018 | female | club | 36 | 114,163 |
| 72/30 | Women's World Cup 2019 | female | national team | 52 | 176,442 |
| 81/275 | Liga Profesional 1981 | male | club | 1 | 3,086 |
| 81/48 | Liga Profesional 1997/1998 | male | club | 1 | 3,572 |
| 87/268 | Copa del Rey 1982/1983 | male | club | 1 | 2,557 |
| 87/279 | Copa del Rey 1977/1978 | male | club | 1 | 2,917 |
| 87/84 | Copa del Rey 1983/1984 | male | club | 1 | 2,596 |
| 116/68 | North American League 1977 | male | club | 1 | 3,205 |
| 131/281 | Serie A Women 2023/2024 | female | club | 130 | 432,487 |
| 135/281 | Frauen Bundesliga 2023/2024 | female | club | 132 | 459,696 |
| 182/281 | Liga F 2023/2024 | female | club | 240 | 835,429 |
| 223/282 | Copa America 2024 | male | national team | 32 | 100,324 |
| 1238/108 | Indian Super league 2021/2022 | male | club | 115 | 344,667 |
| 1267/107 | African Cup of Nations 2023 | male | national team | 52 | 162,903 |
| 1470/274 | FIFA U20 World Cup 1979 | male | national team | 1 | 3,245 |

### Step 1 — measures
- Eligible passes: 1,574,936. Completed receptions: 1,446,829. PRESSURED_flag: 446,015; with a spell outcome: 430,573.
- Baseline AUCs:
  - PR2_flag_keep 0.612 (keep base rate 0.566);
  - PR2_flag_fwd 0.654;
  - W 0.619 (PRESSURED rate 0.308);
  - C3's p(context) 0.664.
- g OOF R^2:
  - pressured receptions: Y_F3 0.120, net xG 0.028, keep 0.063;
  - completed receptions: Y_F3 0.143, net xG 0.201, keep 0.125.
- Roles (≥100 eligible passes): CB 550, AM/W 519, FB 518, DM 369, FW 227, CM 208, MIXED 176. **Deep midfielders: 193.**

### Step 2 — the confirmatory family (Holm across all five)

| Test | n (units / players) | coefficient | 95% CI | raw p | Holm p | MDE (80%) | control on same rows / placebo | result |
|---|---|---|---|---|---|---|---|---|
| C1 DM: PR2_flag_keep → Y_F3 | 33,178 / 189 | +0.572 per 100 per SD | [-0.502, 1.645] | 0.297 | 0.567 | 1.534 | +5.208 [3.834, 6.582], p=1.1e-13 | not confirmed |
| C2 DM: W → Y_F3 | 119,340 / 193 | -0.310 per 100 per SD | [-0.878, 0.257] | 0.284 | 0.567 | 0.811 | +3.972 [3.206, 4.738], p=2.9e-24 | not confirmed |
| C3 ALL: E1 → second-half pressure change (< 0) | 13,779 player-matches / 2,773 | -0.00241 per SD | [-0.00512, +0.00029] | 0.0803 | 0.241 | 0.00386 | placebo +0.00030, p=0.062 | not confirmed |
| C4 ALL: press resistance travels (club vs national team) | 127 movers | r_true +0.650 | [0.500, 0.797] | < 0.002 (0 of 1,000 draws ≤ 0) | 0 | — | — | **CONFIRMED** |
| C6 ALL: team-adjusted PR2_flag_keep (A1) → Y_F3 | 246,255 / 1817 | +1.281 per 100 per SD | [0.988, 1.573] | 9.21e-18 | 3.68e-17 | 0.418 | +8.586 [7.975, 9.196], p=1.7e-167 | **CONFIRMED** |

C4 details: club reliability 0.857, national-team reliability 0.762, r_obs 0.525.

### Step 3 — report only (no claim)

| Test | n (units / players) | coef per 100 per SD | 95% CI | p | MDE | control |
|---|---|---|---|---|---|---|
| C1 with Y = net xG (DM) | 40,073 / 189 | -0.0825 | [-0.1532, -0.0117] | 0.0223 | 0.1010 | +5.214, p=2.1e-21 |
| C2 with Y = net xG (DM) | 141,851 / 193 | +0.0126 | [-0.0344, 0.0596] | 0.599 | 0.0671 | +4.128, p=2.5e-35 |

Stability (Task 38's method, players ≥10 matches):

| Measure | group | n | median [p5, p95] | bar 0.60 |
|---|---|---|---|---|
| pr2_flag_keep | DM | 182 | 0.696 [0.626, 0.750] | PASS |
| pr2_flag_keep | all | 1665 | 0.786 [0.770, 0.802] | PASS |
| w | DM | 182 | 0.781 [0.752, 0.833] | PASS |
| w | all | 1749 | 0.895 [0.888, 0.902] | PASS |

Praised list (Task 41's method; reserved-data Task 32 roles):
- Present: 8 of 13 (Verratti, Pedri, Grillitsch and Shaparenko are not in the reserved data).
- PR2_flag_keep (≥50 pressured receptions; direction higher): T = **+1.581**, p = 9.999e-05. z: Kevin De Bruyne +1.94, Granit Xhaka +2.26, Sergio Busquets i Burgos +1.20, Luka Modrić +0.95, Toni Kroos +1.23, Joshua Kimmich +1.77, Rodrigo Hernández Cascante +1.97, Frenkie de Jong +1.33.
- W (≥100 receptions): T = +0.100, p = 0.777. z: Kevin De Bruyne +0.75, Granit Xhaka +1.20, Sergio Busquets i Burgos -0.99, Luka Modrić -0.57, Toni Kroos -1.20, Joshua Kimmich +2.03, Rodrigo Hernández Cascante -0.01, Frenkie de Jong -0.40.

Deep-midfield tables (Task 29's method, 193 deep midfielders):
- **PR2_flag_keep:** Q = 1057.1 on 192 df, p < 1e-15.
  - 31 above: Yui Hasegawa, Patricia Guijarro Gutiérrez, N'Golo Kanté, Asier Illarramendi Andonegi, Sherida Spitse, Kyra Lillee Cooney-Cross, Julia Angela Grosso, Marcelo Brozović, Desiree Rose Marie Scott, Steven N'Kemboanza Mike Christopher Nzonzi, Gnégnéri Yaya Touré, Alexandre Dimitri Song-Billong, Sophie Louise Ingle, Allie Long, William Silva de Carvalho, Narumi Miura, Sergio Busquets i Burgos, Ariel Borysiuk, Saki Kumagai, Leire Baños Indakoetxea, Keira Walsh, Morgan Paige Gautrat, Sandie Toletti, Teresa Abelleira Dueñas, Sarah Zadrazil, Lisa Fjeldstad Naalsund, Samantha Coffey, Claudia  Zornoza Sánchez, Maite Zubieta Aranbarri, Vilde Bøe Risa, Katie Zelem.
  - 52 below: Emma Severini, Amy Rodgers, Elisa Senß, Sophie Schmidt, Eduardo César Daude Gaspar, Dani Weatherholt, Lalengmawia Ralte, Princeton Rebello, Katharina Piljić, Clare Wheeler, Katrina Gorry, Lena Oberdorf, Young-Ju Lee, Yasmin Katie Mrabet, Gema Soliveres Cholbi, Rubén Salvador Pérez Del Mármol, Alice Parisi, Lalthathanga Khawlhring, Irene Oguiza, Jitendra Singh, Laura Vogt, Marisa Marie DiGrande, Honoka Yonei, Christy Grimshaw, María Pérez, Kerry Abello, Hitesh Sharma, Marisa Ewers, Maisie Symonds, Mariana Cerro, Kassandra Ndoutou Eboa Missipo, Henrietta Csiszár, Júlia Bianchi, Glan Martins, Dominika Čonč, Karen Araya, Meret Günster, Jenny Hipp, Gilberto Aparecido da Silva, Sandra Castelló Oliver, Patrick Vieira, Jade Moore, Julia Zigiotti-Olme, Marta Carro Nolasco, Moirangthem Thoiba Singh, Papa Kouly Diop, Isaac Vanmalsawma Chhakchhuak, Natalie Rose Muth, Rachel Furness, Annalena Rieke, Emily Simpkins, Bernadette Amani Kakounan.
- **W:** Q = 1382.0 on 192 df, p < 1e-15.
  - 54 above: Annalena Rieke, Rachel Furness, Bernadette Amani Kakounan, Kerry Abello, Olivia Van der Jagt, Raquel Rodriguez, Laura Vogt, Samantha Tierney, Lisa Fjeldstad Naalsund, Amy Rodgers, Sophie Schmidt, Denise O'Sullivan, Chloe Peplow, Victoria Pelova, Valentina Gallazzi, Liucija Vaitukaitytė, Elisa Senß, Mikayla Cluff, Morgan Paige Gautrat, Katrina Gorry, Andi Sullivan, Vanessa DiBernardo, Irene Oguiza, Viviana Villacorta, Tessel Middag, Desiree Rose Marie Scott, Katharina Piljić, Emily Ann Sonnett, Narumi Miura, Allie Long, Klára Cahynová, Yasmin Katie Mrabet, Karen Araya, Alexandre Monteiro de Lima, Lo’eau LaBonta, Saori Takarada, Maisie Symonds, Sofie Zdebel, Rebecca Quinn, Lindsey Michelle Horan, Nealy Martin, Kyra Lillee Cooney-Cross, Honoka Hayashi, Cari Roccaro, Dominika Čonč, Sandra Castelló Oliver, María Victoria Losada Gómez, Hayley Ladd, Jade Moore, Leire Baños Indakoetxea, Gabriela Antonia García Segura, Juliane Wirtz, Gema Soliveres Cholbi, Abbey-Leigh Stringer.
  - 35 below: Gnégnéri Yaya Touré, Alexandre Dimitri Song-Billong, María Pérez, Ahmed Jahouh, José Paulo Bezzera Maciel Júnior, Samantha Kerr, Paola Soldevila de la Pisa, Clodoaldo Tavares de Santana, Deepak Tangri, Vinit Rai Chamling, Amandine Henry, Eduardo César Daude Gaspar, Lalengmawia Ralte, Princeton Rebello, Sophie Louise Ingle, Sourav Das, Daniel García Carrillo, Sergio Busquets i Burgos, Steven N'Kemboanza Mike Christopher Nzonzi, Keira Walsh, Wahengbam Angousana Luwang, Jitendra Singh, Carl Gerard McHugh, João Victor de Albuquerque Bruno, Sandie Toletti, Eduardo Bedia Peláez, Melanie Leupolz, Gilberto Aparecido da Silva, Pronay Halder, Patricia Guijarro Gutiérrez, Glan Martins, Saki Kumagai, Ariel Borysiuk, Bruno Edgar Silva Almeida, Lenny Rodrigues.

**The spatial-vs-physical trade-off cannot be tested here:** the reserved data has no positional (360 or tracking) data.

Deep-midfielder list (≥50% DM and ≥300 eligible passes):

| Player | matches | eligible passes | pressured receptions |
|---|---|---|---|
| Sergio Busquets i Burgos | 325 | 21,871 | 3,921 |
| Keira Walsh | 81 | 5,310 | 986 |
| Lia Wälti | 57 | 3,255 | 698 |
| Gnégnéri Yaya Touré | 60 | 3,133 | 633 |
| Sophie Louise Ingle | 61 | 2,852 | 457 |
| Katie Zelem | 54 | 2,831 | 697 |
| Patricia Guijarro Gutiérrez | 26 | 2,207 | 384 |
| Hayley Ladd | 61 | 1,969 | 507 |
| Patrick Vieira | 29 | 1,841 | 487 |
| Denise O'Sullivan | 41 | 1,816 | 585 |
| Alexandre Dimitri Song-Billong | 29 | 1,577 | 299 |
| Gilberto Aparecido da Silva | 32 | 1,566 | 272 |
| Vilde Bøe Risa | 35 | 1,545 | 399 |
| Saki Kumagai | 29 | 1,535 | 187 |
| Teresa Abelleira Dueñas | 27 | 1,533 | 368 |
| Alicia Redondo González | 30 | 1,521 | 414 |
| Leire Baños Indakoetxea | 25 | 1,505 | 426 |
| Paula Fernández Jiménez | 29 | 1,473 | 412 |
| Yui Hasegawa | 25 | 1,463 | 398 |
| Melanie Leupolz | 34 | 1,458 | 243 |
| José Edmílson Gomes de Moraes | 41 | 1,456 | 288 |
| Ana González Rosa | 26 | 1,453 | 343 |
| Rachel Furness | 42 | 1,430 | 505 |
| Abbey-Leigh Stringer | 47 | 1,335 | 339 |
| José Paulo Bezzera Maciel Júnior | 38 | 1,307 | 317 |
| Maite Zubieta Aranbarri | 27 | 1,297 | 290 |
| Narumi Miura | 27 | 1,244 | 398 |
| Karen Araya | 33 | 1,240 | 451 |
| Claudia  Zornoza Sánchez | 28 | 1,216 | 365 |
| Sandie Toletti | 24 | 1,166 | 223 |
| Eduardo Bedia Peláez | 17 | 1,149 | 196 |
| Emily Ann Sonnett | 28 | 1,138 | 296 |
| Paola Soldevila de la Pisa | 30 | 1,117 | 168 |
| Emma Severini | 25 | 1,094 | 249 |
| Eveliina Summanen | 20 | 1,090 | 217 |
| Gema Soliveres Cholbi | 30 | 1,082 | 268 |
| Arianna Caruso | 25 | 1,065 | 335 |
| Jade Moore | 31 | 1,052 | 297 |
| Sarah Zadrazil | 19 | 1,045 | 213 |
| Samantha Coffey | 23 | 1,044 | 215 |
| Sophie Schmidt | 24 | 1,006 | 297 |
| Lalengmawia Ralte | 20 | 991 | 172 |
| Eduardo César Daude Gaspar | 32 | 988 | 188 |
| Alice Benoit | 25 | 988 | 182 |
| Danielle Colaprico | 30 | 975 | 200 |
| Sandra Castelló Oliver | 30 | 973 | 211 |
| Lisanne Gräwe | 22 | 972 | 232 |
| Andi Sullivan | 28 | 967 | 261 |
| Julia Angela Grosso | 21 | 961 | 267 |
| Klára Cahynová | 28 | 952 | 293 |
| Amy Rodgers | 35 | 944 | 238 |
| Ahmed Jahouh | 15 | 942 | 160 |
| Julia Zigiotti-Olme | 23 | 941 | 224 |
| Young-Ju Lee | 29 | 936 | 243 |
| Annabel Schasching | 22 | 935 | 269 |
| Iris Arnaiz Gil | 25 | 928 | 184 |
| Gabriela Antonia García Segura | 26 | 928 | 247 |
| Lo’eau LaBonta | 24 | 921 | 295 |
| João Victor de Albuquerque Bruno | 24 | 911 | 136 |
| Yasmin Katie Mrabet | 27 | 909 | 244 |
| Samantha Tierney | 22 | 897 | 324 |
| Allie Long | 24 | 896 | 215 |
| Chloe Peplow | 31 | 889 | 256 |
| Bruno Edgar Silva Almeida | 20 | 878 | 97 |
| Clare Wheeler | 22 | 871 | 215 |
| Cari Roccaro | 23 | 844 | 245 |
| Juliane Wirtz | 21 | 840 | 203 |
| María Victoria Losada Gómez | 23 | 837 | 241 |
| Victoria Pelova | 22 | 837 | 308 |
| Elisa Senß | 21 | 829 | 244 |
| Fuka Nagano | 21 | 822 | 155 |
| Carl Gerard McHugh | 18 | 821 | 117 |
| Gabriel Fernández Arenas | 20 | 810 | 176 |
| Mariana Cerro | 29 | 802 | 228 |
| Itxaso Uriarte Santamaría | 21 | 789 | 178 |
| Katharina Piljić | 22 | 788 | 201 |
| Zhanna Ferrario | 24 | 783 | 192 |
| Henrietta Csiszár | 23 | 777 | 201 |
| Rebecca Quinn | 29 | 761 | 204 |
| Dani Weatherholt | 29 | 752 | 207 |
| Hernán Daniel Santana Trujillo | 19 | 749 | 200 |
| Maéva Clemaron | 21 | 720 | 164 |
| Lena Oberdorf | 21 | 709 | 175 |
| Natalia Ramos Álvarez | 23 | 704 | 140 |
| Ariadna Mingueza García | 27 | 702 | 149 |
| Kassandra Ndoutou Eboa Missipo | 24 | 701 | 155 |
| Carlos Henrique Casimiro | 14 | 700 | 136 |
| Christy Grimshaw | 20 | 690 | 189 |
| Marisa Ewers | 26 | 688 | 174 |
| Katrina Gorry | 17 | 687 | 248 |
| Pamela Cinthia González Medina | 27 | 685 | 189 |
| Valentina Gallazzi | 25 | 684 | 173 |
| Lalthathanga Khawlhring | 20 | 680 | 134 |
| Laura Vogt | 21 | 679 | 210 |
| Jeakson Singh Thaunaojam | 19 | 675 | 133 |
| Vanessa DiBernardo | 16 | 670 | 211 |
| Olga Ahtinen | 16 | 663 | 142 |
| Júlia Bianchi | 19 | 660 | 183 |
| María Pérez | 25 | 657 | 110 |
| Liucija Vaitukaitytė | 24 | 652 | 195 |
| Princeton Rebello | 17 | 648 | 120 |
| Jenny Hipp | 20 | 647 | 153 |
| Sofie Zdebel | 19 | 642 | 181 |
| Julie Beth Ertz | 18 | 641 | 135 |
| Honoka Hayashi | 21 | 635 | 190 |
| Marta Mascarello | 20 | 626 | 126 |
| Isaac Vanmalsawma Chhakchhuak | 20 | 612 | 148 |
| Alma Hila | 25 | 598 | 141 |
| Marta Carro Nolasco | 20 | 596 | 122 |
| Jaelin Marie Howell | 16 | 595 | 132 |
| Nealy Martin | 18 | 586 | 142 |
| María de los Ángeles Carrión Egido | 23 | 583 | 129 |
| Lindsey Michelle Horan | 12 | 580 | 162 |
| Marisa Marie DiGrande | 20 | 580 | 145 |
| Mikayla Cluff | 22 | 577 | 180 |
| Ariel Borysiuk | 14 | 535 | 67 |
| Vanessa Diehm | 22 | 517 | 104 |
| Sourav Das | 18 | 513 | 65 |
| Olivia Van der Jagt | 19 | 510 | 176 |
| Madison Hammond | 20 | 510 | 117 |
| Bruno Soriano Llido | 12 | 499 | 101 |
| Lena Lattwein | 13 | 498 | 136 |
| Lenny Rodrigues | 19 | 493 | 50 |
| Elli Pikkujämsä | 17 | 492 | 106 |
| Glan Martins | 11 | 486 | 74 |
| Amandine Henry | 11 | 477 | 80 |
| Desiree Rose Marie Scott | 11 | 476 | 121 |
| Annalena Rieke | 21 | 474 | 163 |
| Meret Günster | 16 | 474 | 114 |
| Aimee Palmer | 22 | 469 | 112 |
| Lisa Fjeldstad Naalsund | 16 | 464 | 180 |
| Thiago Motta | 17 | 458 | 99 |
| Xabier Alonso Olano | 10 | 457 | 84 |
| Bernadette Amani Kakounan | 23 | 451 | 131 |
| Saori Takarada | 15 | 450 | 127 |
| Sofie Junge Pedersen | 13 | 448 | 91 |
| Anna Torroda Ricart | 11 | 447 | 100 |
| Maisie Symonds | 22 | 446 | 138 |
| Kerry Abello | 20 | 445 | 183 |
| Deepak Tangri | 18 | 443 | 72 |
| Ander Iturraspe Derteano | 12 | 437 | 91 |
| Jitendra Singh | 19 | 435 | 65 |
| Tanja Pawollek | 10 | 433 | 81 |
| Papa Kouly Diop | 15 | 433 | 100 |
| Alexis Loera | 10 | 431 | 116 |
| Sherida Spitse | 7 | 430 | 102 |
| Khassa Camara | 14 | 430 | 101 |
| Vinit Rai Chamling | 17 | 425 | 69 |
| Alexandre Monteiro de Lima | 22 | 424 | 123 |
| Fabienne Dongus | 16 | 418 | 80 |
| Viviana Villacorta | 16 | 410 | 124 |
| Luca Maria Graf | 16 | 409 | 95 |
| Asier Illarramendi Andonegi | 10 | 404 | 90 |
| Emily Simpkins | 28 | 403 | 104 |
| Natalie Rose Muth | 19 | 402 | 88 |
| Francisco Puñal Martínez | 14 | 396 | 62 |
| Steven N'Kemboanza Mike Christopher Nzonzi | 8 | 395 | 62 |
| William Silva de Carvalho | 7 | 395 | 106 |
| Tiago Cardoso Mendes | 11 | 392 | 98 |
| Teboho Mokoena | 7 | 387 | 103 |
| Raquel Rodriguez | 18 | 386 | 148 |
| Lucía Martínez González | 12 | 384 | 67 |
| Ana Marija Milinković | 11 | 382 | 107 |
| Moirangthem Thoiba Singh | 18 | 380 | 86 |
| Javier Fuego Martínez | 12 | 377 | 70 |
| Luisa Guttenberger | 17 | 377 | 57 |
| Dominika Čonč | 25 | 372 | 91 |
| Franziska Harsch | 15 | 372 | 92 |
| Souvik Chakrabarti | 16 | 370 | 74 |
| Alexandra Jóhannsdóttir | 19 | 367 | 86 |
| Marcelo Brozović | 6 | 367 | 83 |
| Kyra Lillee Cooney-Cross | 14 | 365 | 117 |
| Jordan Brian Henderson | 7 | 363 | 93 |
| Morgan Paige Gautrat | 11 | 360 | 124 |
| Pronay Halder | 14 | 358 | 46 |
| Lucia Pastrenge | 18 | 353 | 73 |
| N'Golo Kanté | 7 | 353 | 82 |
| Alice Parisi | 19 | 350 | 73 |
| Clodoaldo Tavares de Santana | 6 | 346 | 55 |
| Irene Oguiza | 13 | 344 | 112 |
| Ella Jade Mastrantonio | 14 | 336 | 69 |
| Rubén Salvador Pérez Del Mármol | 10 | 333 | 88 |
| Jefferson Andrés Lerma Solís | 10 | 330 | 74 |
| Samantha Kerr | 13 | 327 | 57 |
| Sarah Killion | 7 | 324 | 63 |
| Mehdi Lacen | 11 | 321 | 80 |
| Daniel García Carrillo | 8 | 319 | 50 |
| Sphephelo S''Miso Sithole | 7 | 319 | 98 |
| Germanpreet Singh | 15 | 318 | 76 |
| Honoka Yonei | 22 | 315 | 79 |
| Hitesh Sharma | 10 | 312 | 63 |
| Wahengbam Angousana Luwang | 16 | 306 | 50 |
| Tessel Middag | 12 | 301 | 80 |

## 4. Deviations from the brief
- **C4 sides:** each mover's club side and national-team side are the pooled pressured receptions of his qualifying contexts (each ≥30) on that side, as in Task 46 A-ii.
- **C4 p-value:** 2 × the share of bootstrap r_true ≤ 0. None of the 1,000 draws were ≤ 0, so the reported p is < 0.002 (computed as 0).
- **C3 units and outfield rule** are exactly as in Task 47: outfield = the receipt's position is not Goalkeeper; periods 1-2.
- **Confirmation of C1, C2 and C6** requires the control on the same rows to be positive with p < 0.05. All three controls were positive with p < 1e-13.

## 5. Problems and surprises
- **Most of the reserved matches are women's football**, and all are pooled as the brief lists them:
  - FA WSL, NWSL, Liga F, Frauen Bundesliga, Serie A Women and the Women's World Cup 2019;
  - 1,184 of 1,985 matches.
  Many of the deep midfielders and the table names are women players. The men's club data is mostly one team (Barcelona) across La Liga seasons.
- **Several reserved competition-seasons contain only 1-7 matches** (historic single matches).
- **C1 with Y = net xG is negative** within deep midfielders (−0.083, p = 0.022). Report only.
- **Stability passes** within deep midfielders for PR2_flag_keep (0.696) and W (0.781).
- **The praised list's PR2_flag_keep T is +1.58** (p = 0.0001). This is report only in this task.

## 6. Questions for the research lead
- None.

## 7. Files produced
- `src/engine_v2/task48_ingest.py`, `task48_build.py`, `task48_tests.py`.
- `data/raw_reserved/` (events and matches, derived from the open-data copy), `data/processed/engine_v2/task48_*.parquet`, `data/engine_v2_task48_ingest.json`, `data/engine_v2_task48_build.json`, `data/engine_v2_task48.json` (none committed).
- Side effects: none else. No memory writes. JOURNAL.md and AGENTS.md untouched. Holdout untouched. Nothing beyond the brief was run on the reserved data.
- Commits: brief 2161d66 (research lead); this page 21dd601.

## 8. Confidence
- Every estimator and definition was reused unchanged and fixed before opening the data.
- The weakest links:
  - The reserved sample's composition (a mix of women's and men's football; historic single matches).
  - The C4 movers (127) are the only cross-team evidence.
