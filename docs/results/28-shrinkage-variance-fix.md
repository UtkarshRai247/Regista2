# Task 28: Fix the sampling variance in the player shrinkage
Date: 2026-09-28
Status: COMPLETE

## Section checklist
- Step 0 (commit brief alone): COMPLETE
- Step 1 (design-effect variance): COMPLETE
- Step 2 (rebuild tables a/b/c): COMPLETE

## 1. Headline
The design-effect variance fix works as intended on the overall
537-player group: shrinkage factors now range [0.4478, 0.9776] (Task
27's old match-clustered v_i produced [0.1073, 1.0000], including the
zero-shrinkage bug the brief named). Bentancur's 90% interval widens
from Task 27's +/-0.013 to +/-0.163; Mings from +/-0.017 to +/-0.168;
Busquets, with 22x more passes, now correctly has a NARROWER interval
than either (+/-0.050). The overall ranking is highly stable (Spearman
rho=0.9839 vs. Task 27).

**But the deep-midfield group's tau^2 collapses to exactly zero**
(var(m_i)=0.00741 vs. mean(v_i)=0.01328, per-100^2 units, within that
111-player group) -- meaning the empirical Bayes model finds NO
between-player signal distinguishable from sampling noise among deep
midfielders under the corrected variance, and shrinks every one of them
fully to the group mean. The deep-midfield ranking becomes close to
uninformative (Spearman rho vs. Task 27's own DM ranking =
-0.0600, not significant at
p=0.5319) -- a genuine consequence of
fixing the variance formula, not a bug, and reported plainly rather
than as a smaller version of Task 27's table.

## 2. What I did
1. Committed `task-28-shrinkage-variance-fix.md` alone (Step 0).
2. `task28_step1_2.py`: estimated sigma2_w and rho once, pooling all
   537 qualifying players, via a one-way random-effects ANOVA with
   (player, match) as the nested group (grand mean of per-player-
   demeaned deviations is exactly 0 by construction); computed the
   design-effect v_i = sigma2_w * (1 + (m_i-1)*rho) / n_i per player;
   reused Task 27's own empirical-Bayes shrinkage formula (group mu/
   tau^2 by method of moments, shrinkage factor, posterior SD, 90%
   interval) UNCHANGED, only v_i's construction differs; rebuilt tables
   (a)/(b)/(c) with G_i added; wrote `leaderboard_v5c.parquet`.

Reproduce with (from `src/engine_v2/`, `.venv` activated):
`python task28_step1_2.py`.

## 3. Step 1 -- the design-effect variance
One-way random-effects ANOVA, pooled across all 537 players'
per-player-demeaned deviations, grouped by (player, match)
(N=195928 passes, k=5002 player-match groups):
| quantity | value |
|---|---|
| MSB (between player-match groups) | 2.438337e-04 |
| MSW (within player-match groups) | 1.853959e-04 |
| n0 (unbalanced-design adjustment) | 39.1668 |
| sigma2_u (between-match variance) | 1.492024e-06 |
| sigma2_eps (within-match variance) | 1.853959e-04 |
| **sigma2_w** (pooled per-pass variance) | **1.868879e-04** |
| **rho** (intra-match correlation) | **0.007984** |

rho is small (0.008) -- passes within the same match are only weakly
more similar to each other than passes from different matches, for the
same player -- but the design-effect formula still corrects Task 27's
real defect: a player with few matches now has v_i properly bounded
away from zero regardless of how small rho is, because v_i's floor is
set by sigma2_w/n_i, not by the (now near-zero, previously exactly-zero
for one-match players) between-match spread alone.

| group | n | mu (per 100) | tau^2 (per 100^2) | shrinkage factor range |
|---|---|---|---|---|
| Overall | 537 | 0.27984 | 2.093572e-02 | [0.4478, 0.9776] |
| Deep midfield | 111 | 0.21798 | 0.000000e+00 (collapses to exactly 0) | [0.0000, 0.0000] (i.e. full shrinkage, everyone) |

## 4. Step 2 -- rebuilt tables

### (a) Overall top 20 / bottom 20 (fixed v_i)
Spearman rho vs. Task 27's overall ranking: **0.9839** (p=0) -- the ranking is materially stable; the fix changes interval widths and a handful of small-sample players' exact positions, not the overall ordering.

| rank | player | n | G | raw | shrunken | 90% interval |
|---|---|---|---|---|---|---|
| 1 | Dušan Tadić | 165 | 6 | 1.2173 | 0.8461 | [0.6963, 0.9959] |
| 2 | Raphael Dias Belloli | 109 | 5 | 1.3036 | 0.8035 | [0.6372, 0.9699] |
| 3 | Cody Mathès Gakpo | 232 | 12 | 0.9324 | 0.7327 | [0.6010, 0.8644] |
| 4 | Lionel Andrés Messi Cuccittini | 5570 | 102 | 0.7114 | 0.7017 | [0.6661, 0.7373] |
| 5 | Vinícius José Paixão de Oliveira Júnior | 130 | 6 | 1.0365 | 0.7002 | [0.5415, 0.8589] |
| 6 | Pablo Sarabia García | 201 | 14 | 0.9065 | 0.7000 | [0.5634, 0.8366] |
| 7 | Nicholas Williams Arthuer | 212 | 10 | 0.8903 | 0.6898 | [0.5534, 0.8262] |
| 8 | Kevin De Bruyne | 442 | 11 | 0.7598 | 0.6592 | [0.5502, 0.7682] |
| 9 | Daniel Olmo Carvajal | 556 | 17 | 0.7294 | 0.6541 | [0.5567, 0.7515] |
| 10 | Ángel Fabián Di María Hernández | 949 | 26 | 0.6891 | 0.6450 | [0.5669, 0.7231] |
| 11 | Victor Okoh Boniface | 318 | 21 | 0.7488 | 0.6372 | [0.5211, 0.7533] |
| 12 | Gerard Moreno Balaguero | 176 | 7 | 0.8513 | 0.6359 | [0.4898, 0.7820] |
| 13 | Serge Gnabry | 198 | 8 | 0.8193 | 0.6310 | [0.4904, 0.7716] |
| 14 | Kylian Mbappé Lottin | 2183 | 67 | 0.6438 | 0.6261 | [0.5736, 0.6786] |
| 15 | Jeremy Doku | 172 | 8 | 0.8019 | 0.6053 | [0.4592, 0.7514] |
| 16 | Florian Wirtz | 1595 | 34 | 0.6257 | 0.6011 | [0.5377, 0.6645] |
| 17 | Neymar da Silva Santos Junior | 1830 | 36 | 0.6129 | 0.5917 | [0.5315, 0.6518] |
| 18 | Lamine Yamal Nasraoui Ebana | 163 | 7 | 0.7906 | 0.5903 | [0.4413, 0.7394] |
| 19 | Nathan Tella | 224 | 22 | 0.7141 | 0.5840 | [0.4537, 0.7143] |
| 20 | Memphis Depay | 367 | 15 | 0.6678 | 0.5809 | [0.4682, 0.6936] |

| rank | player | n | G | raw | shrunken | 90% interval |
|---|---|---|---|---|---|---|
| 518 | Kléper Laveran Lima Ferreira | 822 | 12 | 0.1069 | 0.1316 | [0.0416, 0.2217] |
| 519 | Yassine Meriah | 150 | 3 | 0.0075 | 0.1308 | [-0.0294, 0.2910] |
| 520 | Duje Ćaleta-Car | 175 | 4 | 0.0266 | 0.1295 | [-0.0222, 0.2812] |
| 521 | Josip Šutalo | 225 | 4 | 0.0428 | 0.1291 | [-0.0145, 0.2726] |
| 522 | Piero Martín Hincapié Reyna | 1205 | 26 | 0.1116 | 0.1270 | [0.0550, 0.1991] |
| 523 | Óscar Esau Duarte Gaitán | 112 | 4 | -0.0260 | 0.1245 | [-0.0425, 0.2914] |
| 524 | Leonardo Spinazzola | 153 | 4 | 0.0064 | 0.1242 | [-0.0320, 0.2805] |
| 525 | Ľubomír Šatka | 155 | 3 | -0.0034 | 0.1232 | [-0.0359, 0.2824] |
| 526 | Gerard Piqué Bernabéu | 1129 | 18 | 0.1047 | 0.1232 | [0.0459, 0.2006] |
| 527 | Sergio Ramos García | 2193 | 37 | 0.1129 | 0.1223 | [0.0658, 0.1787] |
| 528 | Andreas Christensen | 669 | 13 | 0.0925 | 0.1221 | [0.0276, 0.2166] |
| 529 | Nahuel Molina Lucero | 241 | 7 | 0.0456 | 0.1204 | [-0.0141, 0.2549] |
| 530 | Aymeric Laporte | 1401 | 15 | 0.1014 | 0.1192 | [0.0440, 0.1943] |
| 531 | Petr Ševčík | 120 | 7 | -0.0168 | 0.1186 | [-0.0422, 0.2794] |
| 532 | Presnel Kimpembe | 1661 | 33 | 0.1060 | 0.1181 | [0.0553, 0.1809] |
| 533 | Thilo Kehrer | 514 | 19 | 0.0778 | 0.1128 | [0.0137, 0.2120] |
| 534 | John Stones | 1310 | 19 | 0.0919 | 0.1098 | [0.0364, 0.1832] |
| 535 | Jonathan Tah | 1987 | 32 | 0.0983 | 0.1097 | [0.0501, 0.1693] |
| 536 | Rúben Santos Gato Alves Dias | 805 | 12 | 0.0734 | 0.1033 | [0.0127, 0.1939] |
| 537 | Kalvin Phillips | 328 | 9 | 0.0399 | 0.1020 | [-0.0191, 0.2231] |

Note: Tadić (n=165, G=6) and Belloli (n=109, G=5) are now #1/#2 --
still small-sample players, but their intervals are now properly wide
([0.696, 0.996] and [0.637, 0.970] respectively), unlike Task 27's
narrow, overconfident intervals for similar players. The fix bounds
uncertainty correctly; it does not, by itself, remove small-sample
players from the top of the table when their raw mean is genuinely
much higher than the pool mean -- that is a property of ranking by
point estimate at all, not something this task's brief asked to
change.

**Symptom check (the brief's own named cases):**
| player | n | G | Task 27 90% width | Task 28 90% width |
|---|---|---|---|---|
| Bentancur | 137 | 3 | 0.013 | 0.326 |
| Mings | 117 | 3 | 0.017 | 0.336 |
| Busquets | 2,994 | 44 | 0.031 | 0.100 |

Busquets now correctly has a narrower interval than either Bentancur or
Mings despite having far more passes than both combined -- the
inversion the brief reported is fixed.
### (b) Deep-midfield group -- full table (111 players)
**0 players' 90% intervals lie entirely ABOVE the group mean; 0 entirely BELOW.** Both are zero: tau^2 collapsed to exactly 0 for this group (Section 3), so `shrunken_i = mu_dm` for all 111 players EXACTLY, and `posterior_SD_i = sqrt(tau^2 * v_i / (tau^2+v_i)) = 0` for all of them too -- every player's 90% interval is a single point at the group mean (0.217982 per 100 passes). The z-scores this produces are a floating-point artifact of dividing by a standard deviation that is numerically indistinguishable from zero across 111 values that are all equal to the same constant -- **not a real signal** -- and are OMITTED from the table below rather than reported as if meaningful. The rank column is similarly an artifact of how a stable sort breaks ties among numerically identical values, not a real ordering.

Spearman rho vs. Task 27's deep-midfield ranking: **-0.0600** (p=0.5319, not significant) -- as expected, since this task's own DM ranking is tie-broken arbitrarily (see above), it has no reason to correlate with Task 27's ranking.

| player | n | G | raw (per 100) | shrunken (= group mean, per 100) |
|---|---|---|---|---|
| Bruno Guimarães Rodriguez Moura | 102 | 3 | 0.4863 | 0.2180 |
| Mikel Merino Zazón | 208 | 7 | 0.4321 | 0.2180 |
| Tomáš Souček | 266 | 8 | 0.4264 | 0.2180 |
| Lucas Tolentino Coelho de Lima | 215 | 5 | 0.3953 | 0.2180 |
| Azor Matusiwa | 102 | 2 | 0.3691 | 0.2180 |
| Tijjani Reijnders | 247 | 6 | 0.3679 | 0.2180 |
| Xaver Schlager | 207 | 6 | 0.3659 | 0.2180 |
| Jakub Moder | 124 | 5 | 0.3604 | 0.2180 |
| Hidemasa Morita | 152 | 3 | 0.3578 | 0.2180 |
| In-Beom Hwang | 216 | 4 | 0.3456 | 0.2180 |
| Thomas Teye Partey | 165 | 3 | 0.3290 | 0.2180 |
| Alex Král | 102 | 6 | 0.3178 | 0.2180 |
| Seko Fofana | 158 | 3 | 0.3138 | 0.2180 |
| Kobbie Mainoo | 179 | 6 | 0.3097 | 0.2180 |
| Celso Borges Mora | 100 | 3 | 0.3087 | 0.2180 |
| Carlos Henrique Casimiro | 320 | 6 | 0.3081 | 0.2180 |
| Jackson Irvine | 112 | 4 | 0.3038 | 0.2180 |
| Grzegorz Krychowiak | 187 | 6 | 0.3030 | 0.2180 |
| Vitor Machado Ferreira | 1764 | 36 | 0.3003 | 0.2180 |
| Maxence Caqueret | 115 | 3 | 0.3000 | 0.2180 |
| Saša Lukić | 290 | 6 | 0.2996 | 0.2180 |
| Kaan Ayhan | 267 | 8 | 0.2846 | 0.2180 |
| Youssouf Fofana | 208 | 11 | 0.2819 | 0.2180 |
| Sergio Busquets i Burgos | 2994 | 44 | 0.2817 | 0.2180 |
| Jerdy Schouten | 288 | 6 | 0.2758 | 0.2180 |
| Toni Kroos | 855 | 11 | 0.2756 | 0.2180 |
| Kristoffer Olsson | 138 | 4 | 0.2756 | 0.2180 |
| Mohammed Kanoo | 125 | 3 | 0.2734 | 0.2180 |
| İlkay Gündoğan | 469 | 11 | 0.2726 | 0.2180 |
| Salis Abdul Samed | 136 | 4 | 0.2721 | 0.2180 |
| Ethan Ampadu | 153 | 5 | 0.2672 | 0.2180 |
| Joey Veerman | 136 | 6 | 0.2654 | 0.2180 |
| Pierre-Emile Højbjerg | 826 | 13 | 0.2596 | 0.2180 |
| Atakan Karazor | 111 | 2 | 0.2574 | 0.2180 |
| Marco Verratti | 3518 | 47 | 0.2550 | 0.2180 |
| Johan Gastien | 211 | 3 | 0.2543 | 0.2180 |
| Miralem Pjanić | 620 | 17 | 0.2479 | 0.2180 |
| Remo Freuler | 552 | 14 | 0.2446 | 0.2180 |
| Nicolas Seiwald | 258 | 6 | 0.2407 | 0.2180 |
| Granit Xhaka | 3510 | 43 | 0.2387 | 0.2180 |
| Samuel Moutoussamy | 130 | 3 | 0.2361 | 0.2180 |
| Jonas Martin | 116 | 3 | 0.2352 | 0.2180 |
| Pedro Chirivella Burgos | 193 | 3 | 0.2326 | 0.2180 |
| Benjamin Bourigeaud | 109 | 3 | 0.2325 | 0.2180 |
| Florian Grillitsch | 320 | 8 | 0.2291 | 0.2180 |
| Enzo Fernandez | 406 | 7 | 0.2289 | 0.2180 |
| Kristjan Asllani | 159 | 3 | 0.2269 | 0.2180 |
| Amadou Onana | 316 | 8 | 0.2264 | 0.2180 |
| Leon Goretzka | 217 | 8 | 0.2264 | 0.2180 |
| Youri Tielemans | 349 | 10 | 0.2234 | 0.2180 |
| Teun Koopmeiners | 101 | 5 | 0.2219 | 0.2180 |
| Benjamin André | 153 | 3 | 0.2218 | 0.2180 |
| Mario Götze | 110 | 4 | 0.2177 | 0.2180 |
| Jorge Luiz Frello Filho | 694 | 10 | 0.2167 | 0.2180 |
| Albin Ekdal | 113 | 4 | 0.2125 | 0.2180 |
| Robert Andrich | 1533 | 31 | 0.2107 | 0.2180 |
| Morten Hjulmand | 202 | 3 | 0.2094 | 0.2180 |
| Nadiem Amiri | 135 | 8 | 0.2074 | 0.2180 |
| Wataru Endo | 171 | 4 | 0.2071 | 0.2180 |
| Hakan Çalhanoğlu | 348 | 7 | 0.2035 | 0.2180 |
| Rodrigo Bentancur Colmán | 137 | 3 | 0.2020 | 0.2180 |
| Ellyes Joris Skhiri | 168 | 5 | 0.2000 | 0.2180 |
| Exequiel Alejandro Palacios | 1634 | 25 | 0.2000 | 0.2180 |
| Mario Lemina | 105 | 3 | 0.1999 | 0.2180 |
| Marten de Roon | 251 | 8 | 0.1990 | 0.2180 |
| Boubacar Kamara | 130 | 2 | 0.1990 | 0.2180 |
| Aurélien Djani Tchouaméni | 812 | 13 | 0.1978 | 0.2180 |
| N'Golo Kanté | 521 | 10 | 0.1933 | 0.2180 |
| Christian Nørgaard | 137 | 9 | 0.1923 | 0.2180 |
| Axel Witsel | 332 | 7 | 0.1887 | 0.2180 |
| Stanislav Lobotka | 244 | 5 | 0.1881 | 0.2180 |
| João Maria Lobo Alves Palhinha Gonçalves | 245 | 9 | 0.1834 | 0.2180 |
| Leandro Daniel Paredes | 858 | 19 | 0.1824 | 0.2180 |
| Paul Pogba | 250 | 4 | 0.1813 | 0.2180 |
| Woo-Young Jung | 181 | 4 | 0.1808 | 0.2180 |
| Aaron Mooy | 188 | 4 | 0.1759 | 0.2180 |
| Moisés Isaac Caicedo Corozo | 134 | 3 | 0.1749 | 0.2180 |
| Laurent Abergel | 144 | 3 | 0.1742 | 0.2180 |
| Thomas Delaney | 288 | 10 | 0.1724 | 0.2180 |
| Timi Elšnik | 110 | 4 | 0.1720 | 0.2180 |
| András Schäfer | 190 | 7 | 0.1714 | 0.2180 |
| Trent Alexander-Arnold | 112 | 5 | 0.1663 | 0.2180 |
| Batista Mendy | 101 | 2 | 0.1643 | 0.2180 |
| Rúben Diogo Da Silva Neves | 332 | 10 | 0.1627 | 0.2180 |
| Marcelo Brozović | 833 | 13 | 0.1616 | 0.2180 |
| Ivan Ilić | 152 | 4 | 0.1549 | 0.2180 |
| Declan Rice | 1050 | 19 | 0.1531 | 0.2180 |
| Joan Jordán Moreno | 119 | 2 | 0.1402 | 0.2180 |
| Giorgi Kochorashvili | 156 | 5 | 0.1393 | 0.2180 |
| Ádám Nagy | 161 | 6 | 0.1391 | 0.2180 |
| Joe Allen | 144 | 6 | 0.1336 | 0.2180 |
| Callum McGregor | 191 | 6 | 0.1306 | 0.2180 |
| Corentin Tolisso | 114 | 4 | 0.1289 | 0.2180 |
| Martín Zubimendi Ibáñez | 186 | 6 | 0.1285 | 0.2180 |
| Angel Gomes | 120 | 3 | 0.1257 | 0.2180 |
| Nampalys Mendy | 140 | 4 | 0.1206 | 0.2180 |
| Jordan Veretout | 148 | 3 | 0.1205 | 0.2180 |
| Leander Dendoncker | 171 | 4 | 0.1200 | 0.2180 |
| Serhii Sydorchuk | 184 | 6 | 0.1171 | 0.2180 |
| Sofyan Amrabat | 276 | 7 | 0.1073 | 0.2180 |
| Ander Herrera Agüera | 281 | 8 | 0.1072 | 0.2180 |
| Adam Gnezda Čerin | 134 | 4 | 0.1052 | 0.2180 |
| Jhegson Sebastián Méndez Carabalí | 130 | 2 | 0.1017 | 0.2180 |
| Tyler Adams | 235 | 4 | 0.1001 | 0.2180 |
| Billy Gilmour | 145 | 4 | 0.0964 | 0.2180 |
| Aïssa Bilal Laïdouni | 163 | 5 | 0.0882 | 0.2180 |
| Nemanja Gudelj | 114 | 5 | 0.0877 | 0.2180 |
| Dixon Jair Arroyo Espinoza | 105 | 3 | 0.0743 | 0.2180 |
| Emre Can | 111 | 7 | 0.0707 | 0.2180 |
| Kalvin Phillips | 328 | 9 | 0.0399 | 0.2180 |
| Taras Stepanenko | 159 | 4 | 0.0302 | 0.2180 |

(Sorted by raw mean Decision, descending, since the shrunken column carries no ordering information here -- every row's shrunken value is identical.)
### (c) Fixed 13-name list -- output only, never a criterion
| name | overall rank | n | G | shrunken (per 100) | 90% interval | deep-midfield rank |
|---|---|---|---|---|---|---|
| Kroos (Toni Kroos) | 216 | 855 | 11 | 0.2762 | [0.1859, 0.3666] | 109 (artifact -- see 4b) |
| Modric (Luka Modrić) | 338 | 954 | 16 | 0.2244 | [0.1417, 0.3072] | not in group |
| Verratti (Marco Verratti) | 258 | 3518 | 47 | 0.2560 | [0.2091, 0.3028] | 80 (artifact -- see 4b) |
| Busquets (Sergio Busquets i Burgos) | 199 | 2994 | 44 | 0.2816 | [0.2318, 0.3314] | 61 (artifact -- see 4b) |
| De Bruyne (Kevin De Bruyne) | 8 | 442 | 11 | 0.6592 | [0.5502, 0.7682] | not in group |
| Xhaka (Granit Xhaka) | 294 | 3510 | 43 | 0.2404 | [0.1927, 0.2881] | 76 (artifact -- see 4b) |
| de Jong (Frenkie de Jong) | 247 | 3012 | 43 | 0.2618 | [0.2119, 0.3117] | not in group |
| Kimmich (Joshua Kimmich) | 64 | 844 | 14 | 0.4123 | [0.3249, 0.4997] | not in group |
| Rodri (Rodrigo Hernández Cascante) | 460 | 1191 | 15 | 0.1785 | [0.1000, 0.2569] | not in group |
| Pedri (Pedro González López) | 95 | 2413 | 48 | 0.3655 | [0.3128, 0.4182] | not in group |
| Gundogan (İlkay Gündoğan) | 219 | 469 | 11 | 0.2741 | [0.1670, 0.3811] | 22 (artifact -- see 4b) |
| Grillitsch (Florian Grillitsch) | 285 | 320 | 8 | 0.2427 | [0.1195, 0.3658] | 17 (artifact -- see 4b) |
| Shaparenko (Mykola Shaparenko) | 329 | 312 | 8 | 0.2262 | [0.1021, 0.3502] | not in group |

All six deep-midfield-group members of the fixed list share the exact same shrunken value (0.217982, the group mean) and a zero-width interval, per Section 4(b) -- their listed "deep-midfield rank" is a tie-breaking artifact, not a real ordering, and is reported as such rather than presented as a finding.

## 5. `git diff --stat`
No pre-existing tracked file was modified. One new file only:
```
 src/engine_v2/task28_step1_2.py | new
```
`docs/JOURNAL.md` shows as modified in `git status` from before this
task and was not touched here.

## 6. Deviations from the brief
None. Only v_i's construction changed, exactly as the hard rule
requires; the same groups (537 overall, 111 deep midfielders from Task
27 Step 1), same mu/tau^2-by-method-of-moments/shrinkage-factor/
posterior-SD/90%-interval formulas, same fixed 13-name list, are all
reused unchanged.

## 7. Problems and surprises
- The deep-midfield group's tau^2 collapsing to exactly zero (Section
  3-4) was not anticipated by the brief and is the most significant
  finding in this task. It means that, under a correctly-specified
  sampling-variance model, the 111 deep midfielders' RAW mean-Decision
  values do not differ from each other by more than sampling noise
  would produce -- i.e. this task's own corrected statistical model
  finds no reliable within-group signal to rank on. This is a direct,
  mechanical consequence of the brief's own formula (method-of-moments
  tau^2, floored at 0) applied to this specific subgroup's data, not a
  bug: verified directly (var(m_i)=0.00741 vs. mean(v_i)=0.01328, per
  100^2 units, both computed straightforwardly from the group's own
  111 rows).
- Once tau^2=0, several downstream quantities become numerically
  degenerate (posterior_SD=0 exactly, so 90% intervals collapse to a
  point; z-scores divide by a standard deviation that is
  indistinguishable from zero across 111 identical values). Rather than
  report these as if they were meaningful numbers, Section 4(b) states
  plainly that they are artifacts and omits the z-score/rank columns
  from the table.
- The overall group's shrinkage factor range [0.4478, 0.9776] is
  reassuringly bounded compared to Task 27's [0.1073, 1.0000] -- direct
  evidence the design-effect fix removed the zero-variance failure mode
  the brief described, without needing to inspect individual players.

## 8. Questions for the research lead
1. The deep-midfield table (Section 4b) is now, in effect, a null
   result: no player in that group is distinguishable from the group
   mean under the corrected variance model. Should the deep-midfield
   leaderboard be reported at all going forward (e.g. in the abstract),
   or should it be replaced with a statement that this analysis found
   no reliable within-group differentiation among deep midfielders,
   given the sample sizes and match counts available?
2. This task's hard rule forbids changing the group or threshold. Is a
   follow-up task in scope to investigate WHY the deep-midfield
   subgroup specifically shows this pattern (e.g., a genuinely more
   homogeneous population of players, or a group too narrow/correlated
   with role for method-of-moments tau^2 to detect real spread), or is
   the null result itself the reportable finding?

## 9. Files produced
- `src/engine_v2/task28_step1_2.py` -- new. One-way ANOVA
  sigma2_w/rho estimation, design-effect v_i, empirical-Bayes shrinkage
  (Task 27's formula reused unchanged), rebuilt tables (a)/(b)/(c),
  Spearman comparisons with Task 27.
- `data/processed/leaderboard_v5c.parquet` -- new data artifact (the
  overall group's full shrunk table; not committed, `data/` is never
  committed).
- `data/engine_v2_task28_step1_2.json` -- new summary JSON backing this
  page (also under `data/`, not committed).
- `docs/results/28-shrinkage-variance-fix.md` -- this file.
- Commit hashes: `453f3e3` (Step 0, brief alone), `ade53b9` (this
  results page + code).

## 10. Confidence
High confidence in Step 1's ANOVA-based sigma2_w/rho estimate and the
resulting v_i formula: it is a direct, literal implementation of the
brief's own formula, verified against a hand-checked toy example for
the (player, match) grouping mechanics, and its effect on the reported
symptom cases (Bentancur, Mings, Busquets) is exactly the correction
the brief predicted. High confidence the overall group's ranking is
essentially unchanged (Spearman rho=0.98) and its intervals are now
properly bounded. Lower confidence in what to DO with the deep-midfield
group's null result (Section 7/8) -- that is a methodology question
for the research lead, not something resolved in this page. The
weakest link is definitional, not statistical: whether a table of 111
numerically-tied values should be presented as a "ranking" at all is a
judgment call this task's hard rules do not authorize this page to make
on its own.
