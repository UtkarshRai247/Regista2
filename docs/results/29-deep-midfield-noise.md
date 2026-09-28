# Task 29: Deep midfielders -- estimate their noise from their own passes
Date: 2026-09-28
Status: COMPLETE

## Section checklist
- Step 0 (commit brief alone): COMPLETE
- Step 1 (within-group noise): COMPLETE
- Step 2 (precision-weighted between-player variance): COMPLETE
- Step 3 (independent match-split check): COMPLETE
- Step 4 (tables): COMPLETE
- Abstract rule: applied, see Section 6

## 1. Headline
Both specification problems the brief named were real. Re-estimating
sigma2_w/rho WITHIN the 111 deep midfielders (sigma2_w=1.0869e-04,
rho=0.004394) instead of pooling across all 537 players
(sigma2_w=1.8689e-04, rho=0.007984) gives
smaller, more accurate per-pass variance for this group. Combined with a
precision-weighted (DerSimonian-Laird) between-player variance instead
of Task 28's unweighted method-of-moments estimator, the Q-test for
heterogeneity now **REJECTS** homogeneity (Q=140.53 on
110 df, p=0.0263) -- using Task 28's pooled v_i
instead, Q does NOT reject (p=0.9975), confirming
the pooling choice alone was suppressing the signal. tau^2 is no longer
exactly zero (1.0430e-07, REML agrees: 1.1848e-07), and
2 of 111 players' 90% intervals now lie entirely above the group mean:
**Vitinha** (Vitor Machado Ferreira, 1,764 passes) and **Busquets**
(2,994 passes) -- both among the highest-volume players in the group,
exactly the ones the brief's precision-weighting fix was meant to let
speak.

**But Step 3's fully independent check (no shrinkage model at all) does
NOT corroborate this at a usable level**: median full-length reliability
from 100 match-based split-half correlations, among the 16 deep
midfielders with >=500 passes, is **0.1846**
(5th-95th percentile [-0.5666, 0.5669]) --
far below the 0.70 bar, and the interval is wide enough to include
strongly negative values.

**Abstract rule outcome: EXACTLY ONE of the two conditions holds**
(Q rejects at p<0.05; Step 3's median reliability does not reach 0.70).
Per the rule decided before these numbers existed: the abstract reports
that deep midfielders differ, but only names players whose intervals
exclude the group mean -- Vitinha and Busquets, and no one else.

## 2. What I did
1. Committed `task-29-deep-midfield-noise.md` alone (Step 0).
2. `task29_step1_2.py`: re-ran Task 28's own one-way-ANOVA
   sigma2_w/rho estimator (`estimate_sigma2w_rho`, imported unchanged)
   restricted to the 111 deep midfielders' own passes only; recomputed
   each player's v_i with Task 28's design-effect formula and these
   within-group values; computed DerSimonian-Laird tau^2 (PRIMARY, with
   within-group v_i, and again with Task 28's pooled v_i for
   comparison) and REML tau^2 (SECONDARY); shrank toward the
   precision-weighted mean mu_w using Task 27's shrinkage/interval
   formulas.
3. `task29_step3.py`: for the 16 deep midfielders with >=500 eligible
   passes, 100 random splits of each player's own MATCHES into two
   halves, correlated half-means across players, Spearman-Brown
   corrected, reported median and 5th-95th percentile.

Reproduce with (from `src/engine_v2/`, `.venv` activated):
`python task29_step1_2.py && python task29_step3.py`.

## 3. Step 1 -- within-group noise
| quantity | Task 28 (pooled, 537 players) | Task 29 (within-group, 111 deep midfielders) |
|---|---|---|
| sigma2_w | 1.868879e-04 | 1.086852e-04 |
| rho | 0.007984 | 0.004394 |

Both sigma2_w and rho are smaller within the deep-midfield group than pooled across all 537 players -- consistent with the brief's hypothesis that forwards' more variable per-pass Decision was inflating the pooled estimate used to compute deep midfielders' own v_i in Task 28.

## 4. Step 2 -- precision-weighted between-player variance
| quantity | PRIMARY: DL, within-group v_i | comparison: DL, Task 28 pooled v_i | SECONDARY: REML, within-group v_i |
|---|---|---|---|
| mu_w (per pass) | 2.284729e-03 | 2.280579e-03 | 2.225475e-03 |
| Q | 140.5346 | 72.8718 | -- |
| df | 110 | 110 | -- |
| p-value (chi2) | **0.0263** | 0.9975 | -- |
| tau^2 | 1.042983e-07 | 0.000000e+00 | 1.184786e-07 |

**The Q-test rejects homogeneity at p<0.05 with within-group v_i
(p=0.0263) but not with Task 28's pooled v_i (p=0.9975)** --
isolating that the pooling choice (Step 1), not the precision-weighting
alone, was the larger driver of Task 28's tau^2=0 null: DL's tau^2 is
already 0 even with the pooled v_i under precision-weighting, whereas
switching to within-group v_i alone (holding the tau^2 estimator fixed)
is what pushes Q past the rejection threshold. REML, run on the same
within-group v_i, gives a tau^2 of the same order of magnitude as DL's
(1.1848e-07 vs 1.0430e-07) -- the two estimators agree.

2 of 111 players' 90% intervals lie
entirely ABOVE mu_w (0.2285 per 100 passes); 0 entirely BELOW.

## 5. Step 3 -- independent check (no shrinkage model)
16 deep midfielders have >=500 eligible passes. For each of
100 random splits of each player's own matches into two halves,
correlated the two half-means across the 16 players, Spearman-Brown
corrected to full length (100/100 splits gave a valid,
non-degenerate correlation).

| quantity | value |
|---|---|
| n (qualifying players) | 16 |
| median full-length reliability | **0.1846** |
| 5th percentile | -0.5666 |
| 95th percentile | 0.5669 |

This is far below the 0.70 bar, and the wide, sign-crossing interval
means a given split can easily produce a strongly negative correlation
by chance at this sample size (n=16 players per split) -- this
independent check does not corroborate Step 2's rejection of
homogeneity at a level anyone could act on with confidence.

## 6. Abstract rule -- applied
- Q test: p=0.0263 < 0.05 -> **REJECTS** homogeneity.
- Step 3 median reliability: 0.1846 < 0.70 -> does **NOT** clear the bar.

**Exactly one of the two holds.** Per the rule fixed before these
numbers existed: *"the abstract reports that deep midfielders differ
but only a few separations are reliable, naming only players whose
intervals exclude mu_w."* That is Vitinha and Busquets (Section 4/7) --
no broader ranking of the 111 deep midfielders is supported by this
task's own pre-declared rule.

## 7. Step 4 -- tables

### (a) All 111 deep midfielders, Step 2 shrinkage (PRIMARY: DL, within-group v_i)
Group mean mu_w = 0.2285 per 100 passes. 2 intervals entirely above, 0 entirely below.

| rank | player | n | G | raw | shrunken | 90% interval |
|---|---|---|---|---|---|---|
| 1 | Vitor Machado Ferreira | 1764 | 36 | 0.3003 | 0.2704 | [0.2360, 0.3047] |
| 2 | Sergio Busquets i Burgos | 2994 | 44 | 0.2817 | 0.2651 | [0.2355, 0.2948] |
| 3 | Tomáš Souček | 266 | 8 | 0.4264 | 0.2646 | [0.2166, 0.3127] |
| 4 | Mikel Merino Zazón | 208 | 7 | 0.4321 | 0.2591 | [0.2102, 0.3081] |
| 5 | Lucas Tolentino Coelho de Lima | 215 | 5 | 0.3953 | 0.2532 | [0.2042, 0.3023] |
| 6 | Tijjani Reijnders | 247 | 6 | 0.3679 | 0.2518 | [0.2034, 0.3003] |
| 7 | Bruno Guimarães Rodriguez Moura | 102 | 3 | 0.4863 | 0.2488 | [0.1978, 0.2998] |
| 8 | Xaver Schlager | 207 | 6 | 0.3659 | 0.2488 | [0.1997, 0.2978] |
| 9 | Marco Verratti | 3518 | 47 | 0.2550 | 0.2475 | [0.2193, 0.2757] |
| 10 | Toni Kroos | 855 | 11 | 0.2756 | 0.2464 | [0.2046, 0.2882] |
| 11 | In-Beom Hwang | 216 | 4 | 0.3456 | 0.2453 | [0.1962, 0.2945] |
| 12 | Carlos Henrique Casimiro | 320 | 6 | 0.3081 | 0.2444 | [0.1969, 0.2919] |
| 13 | Hidemasa Morita | 152 | 3 | 0.3578 | 0.2423 | [0.1921, 0.2925] |
| 14 | Saša Lukić | 290 | 6 | 0.2996 | 0.2418 | [0.1939, 0.2897] |
| 15 | Jakub Moder | 124 | 5 | 0.3604 | 0.2413 | [0.1908, 0.2918] |
| 16 | İlkay Gündoğan | 469 | 11 | 0.2726 | 0.2406 | [0.1954, 0.2859] |
| 17 | Pierre-Emile Højbjerg | 826 | 13 | 0.2596 | 0.2404 | [0.1987, 0.2821] |
| 18 | Thomas Teye Partey | 165 | 3 | 0.3290 | 0.2399 | [0.1899, 0.2899] |
| 19 | Kobbie Mainoo | 179 | 6 | 0.3097 | 0.2392 | [0.1897, 0.2887] |
| 20 | Azor Matusiwa | 102 | 2 | 0.3691 | 0.2389 | [0.1878, 0.2900] |
| 21 | Kaan Ayhan | 267 | 8 | 0.2846 | 0.2388 | [0.1907, 0.2868] |
| 22 | Grzegorz Krychowiak | 187 | 6 | 0.3030 | 0.2387 | [0.1893, 0.2880] |
| 23 | Seko Fofana | 158 | 3 | 0.3138 | 0.2379 | [0.1877, 0.2880] |
| 24 | Jerdy Schouten | 288 | 6 | 0.2758 | 0.2373 | [0.1894, 0.2852] |
| 25 | Youssouf Fofana | 208 | 11 | 0.2819 | 0.2368 | [0.1880, 0.2856] |
| 26 | Alex Král | 102 | 6 | 0.3178 | 0.2360 | [0.1851, 0.2868] |
| 27 | Granit Xhaka | 3510 | 43 | 0.2387 | 0.2358 | [0.2073, 0.2642] |
| 28 | Jackson Irvine | 112 | 4 | 0.3038 | 0.2351 | [0.1843, 0.2858] |
| 29 | Miralem Pjanić | 620 | 17 | 0.2479 | 0.2351 | [0.1919, 0.2782] |
| 30 | Celso Borges Mora | 100 | 3 | 0.3087 | 0.2347 | [0.1837, 0.2857] |
| 31 | Maxence Caqueret | 115 | 3 | 0.3000 | 0.2347 | [0.1839, 0.2854] |
| 32 | Remo Freuler | 552 | 14 | 0.2446 | 0.2335 | [0.1894, 0.2776] |
| 33 | Kristoffer Olsson | 138 | 4 | 0.2756 | 0.2333 | [0.1830, 0.2836] |
| 34 | Salis Abdul Samed | 136 | 4 | 0.2721 | 0.2329 | [0.1826, 0.2833] |
| 35 | Ethan Ampadu | 153 | 5 | 0.2672 | 0.2329 | [0.1829, 0.2829] |
| 36 | Mohammed Kanoo | 125 | 3 | 0.2734 | 0.2326 | [0.1820, 0.2832] |
| 37 | Joey Veerman | 136 | 6 | 0.2654 | 0.2324 | [0.1822, 0.2826] |
| 38 | Johan Gastien | 211 | 3 | 0.2543 | 0.2319 | [0.1825, 0.2814] |
| 39 | Atakan Karazor | 111 | 2 | 0.2574 | 0.2308 | [0.1798, 0.2817] |
| 40 | Nicolas Seiwald | 258 | 6 | 0.2407 | 0.2306 | [0.1823, 0.2789] |
| 41 | Samuel Moutoussamy | 130 | 3 | 0.2361 | 0.2292 | [0.1787, 0.2797] |
| 42 | Jonas Martin | 116 | 3 | 0.2352 | 0.2291 | [0.1783, 0.2798] |
| 43 | Pedro Chirivella Burgos | 193 | 3 | 0.2326 | 0.2290 | [0.1793, 0.2786] |
| 44 | Benjamin Bourigeaud | 109 | 3 | 0.2325 | 0.2288 | [0.1779, 0.2797] |
| 45 | Florian Grillitsch | 320 | 8 | 0.2291 | 0.2286 | [0.1813, 0.2759] |
| 46 | Enzo Fernandez | 406 | 7 | 0.2289 | 0.2286 | [0.1822, 0.2750] |
| 47 | Kristjan Asllani | 159 | 3 | 0.2269 | 0.2283 | [0.1782, 0.2784] |
| 48 | Leon Goretzka | 217 | 8 | 0.2264 | 0.2281 | [0.1794, 0.2769] |
| 49 | Amadou Onana | 316 | 8 | 0.2264 | 0.2280 | [0.1807, 0.2754] |
| 50 | Teun Koopmeiners | 101 | 5 | 0.2219 | 0.2279 | [0.1770, 0.2788] |
| 51 | Benjamin André | 153 | 3 | 0.2218 | 0.2278 | [0.1776, 0.2779] |
| 52 | Mario Götze | 110 | 4 | 0.2177 | 0.2275 | [0.1768, 0.2783] |
| 53 | Youri Tielemans | 349 | 10 | 0.2234 | 0.2273 | [0.1806, 0.2741] |
| 54 | Albin Ekdal | 113 | 4 | 0.2125 | 0.2271 | [0.1763, 0.2778] |
| 55 | Nadiem Amiri | 135 | 8 | 0.2074 | 0.2262 | [0.1760, 0.2764] |
| 56 | Mario Lemina | 105 | 3 | 0.1999 | 0.2262 | [0.1752, 0.2771] |
| 57 | Morten Hjulmand | 202 | 3 | 0.2094 | 0.2260 | [0.1765, 0.2755] |
| 58 | Wataru Endo | 171 | 4 | 0.2071 | 0.2259 | [0.1761, 0.2757] |
| 59 | Boubacar Kamara | 130 | 2 | 0.1990 | 0.2259 | [0.1751, 0.2766] |
| 60 | Rodrigo Bentancur Colmán | 137 | 3 | 0.2020 | 0.2258 | [0.1754, 0.2763] |
| 61 | Ellyes Joris Skhiri | 168 | 5 | 0.2000 | 0.2250 | [0.1752, 0.2747] |
| 62 | Christian Nørgaard | 137 | 9 | 0.1923 | 0.2245 | [0.1744, 0.2746] |
| 63 | Jorge Luiz Frello Filho | 694 | 10 | 0.2167 | 0.2245 | [0.1813, 0.2677] |
| 64 | Batista Mendy | 101 | 2 | 0.1643 | 0.2237 | [0.1726, 0.2749] |
| 65 | Timi Elšnik | 110 | 4 | 0.1720 | 0.2236 | [0.1728, 0.2744] |
| 66 | Marten de Roon | 251 | 8 | 0.1990 | 0.2233 | [0.1751, 0.2716] |
| 67 | Moisés Isaac Caicedo Corozo | 134 | 3 | 0.1749 | 0.2233 | [0.1728, 0.2737] |
| 68 | Hakan Çalhanoğlu | 348 | 7 | 0.2035 | 0.2231 | [0.1760, 0.2701] |
| 69 | Trent Alexander-Arnold | 112 | 5 | 0.1663 | 0.2229 | [0.1722, 0.2736] |
| 70 | Laurent Abergel | 144 | 3 | 0.1742 | 0.2229 | [0.1726, 0.2732] |
| 71 | Woo-Young Jung | 181 | 4 | 0.1808 | 0.2224 | [0.1728, 0.2721] |
| 72 | Stanislav Lobotka | 244 | 5 | 0.1881 | 0.2219 | [0.1733, 0.2706] |
| 73 | Aaron Mooy | 188 | 4 | 0.1759 | 0.2216 | [0.1721, 0.2711] |
| 74 | Joan Jordán Moreno | 119 | 2 | 0.1402 | 0.2211 | [0.1703, 0.2720] |
| 75 | Paul Pogba | 250 | 4 | 0.1813 | 0.2210 | [0.1723, 0.2697] |
| 76 | João Maria Lobo Alves Palhinha Gonçalves | 245 | 9 | 0.1834 | 0.2206 | [0.1723, 0.2689] |
| 77 | András Schäfer | 190 | 7 | 0.1714 | 0.2205 | [0.1712, 0.2697] |
| 78 | Ivan Ilić | 152 | 4 | 0.1549 | 0.2203 | [0.1702, 0.2704] |
| 79 | Axel Witsel | 332 | 7 | 0.1887 | 0.2201 | [0.1729, 0.2674] |
| 80 | Corentin Tolisso | 114 | 4 | 0.1289 | 0.2196 | [0.1689, 0.2703] |
| 81 | Angel Gomes | 120 | 3 | 0.1257 | 0.2193 | [0.1686, 0.2700] |
| 82 | Robert Andrich | 1533 | 31 | 0.2107 | 0.2187 | [0.1830, 0.2544] |
| 83 | N'Golo Kanté | 521 | 10 | 0.1933 | 0.2183 | [0.1735, 0.2630] |
| 84 | Giorgi Kochorashvili | 156 | 5 | 0.1393 | 0.2181 | [0.1681, 0.2680] |
| 85 | Joe Allen | 144 | 6 | 0.1336 | 0.2179 | [0.1678, 0.2680] |
| 86 | Ádám Nagy | 161 | 6 | 0.1391 | 0.2176 | [0.1678, 0.2674] |
| 87 | Thomas Delaney | 288 | 10 | 0.1724 | 0.2174 | [0.1698, 0.2650] |
| 88 | Jhegson Sebastián Méndez Carabalí | 130 | 2 | 0.1017 | 0.2172 | [0.1665, 0.2679] |
| 89 | Nampalys Mendy | 140 | 4 | 0.1206 | 0.2172 | [0.1669, 0.2675] |
| 90 | Jordan Veretout | 148 | 3 | 0.1205 | 0.2171 | [0.1669, 0.2674] |
| 91 | Aurélien Djani Tchouaméni | 812 | 13 | 0.1978 | 0.2168 | [0.1750, 0.2586] |
| 92 | Dixon Jair Arroyo Espinoza | 105 | 3 | 0.0743 | 0.2160 | [0.1651, 0.2670] |
| 93 | Adam Gnezda Čerin | 134 | 4 | 0.1052 | 0.2160 | [0.1656, 0.2664] |
| 94 | Nemanja Gudelj | 114 | 5 | 0.0877 | 0.2157 | [0.1650, 0.2664] |
| 95 | Leander Dendoncker | 171 | 4 | 0.1200 | 0.2153 | [0.1655, 0.2651] |
| 96 | Callum McGregor | 191 | 6 | 0.1306 | 0.2149 | [0.1656, 0.2642] |
| 97 | Martín Zubimendi Ibáñez | 186 | 6 | 0.1285 | 0.2148 | [0.1655, 0.2642] |
| 98 | Billy Gilmour | 145 | 4 | 0.0964 | 0.2143 | [0.1641, 0.2645] |
| 99 | Emre Can | 111 | 7 | 0.0707 | 0.2141 | [0.1635, 0.2648] |
| 100 | Rúben Diogo Da Silva Neves | 332 | 10 | 0.1627 | 0.2141 | [0.1672, 0.2611] |
| 101 | Serhii Sydorchuk | 184 | 6 | 0.1171 | 0.2134 | [0.1640, 0.2628] |
| 102 | Exequiel Alejandro Palacios | 1634 | 25 | 0.2000 | 0.2128 | [0.1772, 0.2484] |
| 103 | Aïssa Bilal Laïdouni | 163 | 5 | 0.0882 | 0.2115 | [0.1617, 0.2613] |
| 104 | Leandro Daniel Paredes | 858 | 19 | 0.1824 | 0.2097 | [0.1688, 0.2506] |
| 105 | Tyler Adams | 235 | 4 | 0.1001 | 0.2089 | [0.1600, 0.2578] |
| 106 | Sofyan Amrabat | 276 | 7 | 0.1073 | 0.2061 | [0.1581, 0.2541] |
| 107 | Taras Stepanenko | 159 | 4 | 0.0302 | 0.2056 | [0.1556, 0.2556] |
| 108 | Ander Herrera Agüera | 281 | 8 | 0.1072 | 0.2054 | [0.1576, 0.2533] |
| 109 | Marcelo Brozović | 833 | 13 | 0.1616 | 0.2027 | [0.1611, 0.2444] |
| 110 | Declan Rice | 1050 | 19 | 0.1531 | 0.1946 | [0.1552, 0.2341] |
| 111 | Kalvin Phillips | 328 | 9 | 0.0399 | 0.1881 | [0.1410, 0.2352] |

### (b) The >=500-pass subset (16 players), same columns
| rank (within full group) | player | n | G | raw | shrunken | 90% interval |
|---|---|---|---|---|---|---|
| 1 | Vitor Machado Ferreira | 1764 | 36 | 0.3003 | 0.2704 | [0.2360, 0.3047] |
| 2 | Sergio Busquets i Burgos | 2994 | 44 | 0.2817 | 0.2651 | [0.2355, 0.2948] |
| 9 | Marco Verratti | 3518 | 47 | 0.2550 | 0.2475 | [0.2193, 0.2757] |
| 10 | Toni Kroos | 855 | 11 | 0.2756 | 0.2464 | [0.2046, 0.2882] |
| 17 | Pierre-Emile Højbjerg | 826 | 13 | 0.2596 | 0.2404 | [0.1987, 0.2821] |
| 27 | Granit Xhaka | 3510 | 43 | 0.2387 | 0.2358 | [0.2073, 0.2642] |
| 29 | Miralem Pjanić | 620 | 17 | 0.2479 | 0.2351 | [0.1919, 0.2782] |
| 32 | Remo Freuler | 552 | 14 | 0.2446 | 0.2335 | [0.1894, 0.2776] |
| 63 | Jorge Luiz Frello Filho | 694 | 10 | 0.2167 | 0.2245 | [0.1813, 0.2677] |
| 82 | Robert Andrich | 1533 | 31 | 0.2107 | 0.2187 | [0.1830, 0.2544] |
| 83 | N'Golo Kanté | 521 | 10 | 0.1933 | 0.2183 | [0.1735, 0.2630] |
| 91 | Aurélien Djani Tchouaméni | 812 | 13 | 0.1978 | 0.2168 | [0.1750, 0.2586] |
| 102 | Exequiel Alejandro Palacios | 1634 | 25 | 0.2000 | 0.2128 | [0.1772, 0.2484] |
| 104 | Leandro Daniel Paredes | 858 | 19 | 0.1824 | 0.2097 | [0.1688, 0.2506] |
| 109 | Marcelo Brozović | 833 | 13 | 0.1616 | 0.2027 | [0.1611, 0.2444] |
| 110 | Declan Rice | 1050 | 19 | 0.1531 | 0.1946 | [0.1552, 0.2341] |

### (c) The six named players in the group -- output only, never a criterion
| name | rank | n | G | raw | shrunken | 90% interval |
|---|---|---|---|---|---|---|
| Kroos (Toni Kroos) | 10 | 855 | 11 | 0.2756 | 0.2464 | [0.2046, 0.2882] |
| Verratti (Marco Verratti) | 9 | 3518 | 47 | 0.2550 | 0.2475 | [0.2193, 0.2757] |
| Busquets (Sergio Busquets i Burgos) | 2 | 2994 | 44 | 0.2817 | 0.2651 | [0.2355, 0.2948] |
| Xhaka (Granit Xhaka) | 27 | 3510 | 43 | 0.2387 | 0.2358 | [0.2073, 0.2642] |
| Gundogan (İlkay Gündoğan) | 16 | 469 | 11 | 0.2726 | 0.2406 | [0.1954, 0.2859] |
| Grillitsch (Florian Grillitsch) | 45 | 320 | 8 | 0.2291 | 0.2286 | [0.1813, 0.2759] |

None of the six named players' intervals exclude mu_w -- per Section 6's abstract rule, none of them may be individually named as reliably above or below the group mean in the abstract; only Vitinha and Busquets (neither on this fixed list) qualify.

## 8. `git diff --stat`
No pre-existing tracked file was modified. Two new files only:
```
 src/engine_v2/task29_step1_2.py | new
 src/engine_v2/task29_step3.py   | new
```
`docs/JOURNAL.md` shows as modified in `git status` from before this
task and was not touched here. Task 28's own overall-group table
(`leaderboard_v5c.parquet`) is untouched; this task only reads it (for
the deep-midfield flag) and never rewrites it, per the hard rule that
the overall table stays as Task 28 produced it.

## 9. Deviations from the brief
None. Both Step 1 and Step 2 changes were applied to the deep-midfield
group only, exactly as scoped; the overall 537-player table was not
touched.

## 10. Problems and surprises
- The comparison in Section 4 (DL tau^2 with Task 28's pooled v_i still
  gives tau^2=0) shows that precision-weighting ALONE, without also
  fixing the pooled-vs-within-group variance estimate, would NOT have
  fixed Task 28's null. Both of the brief's named specification
  problems needed fixing together; neither alone was sufficient on this
  data.
- Step 2's shrinkage-model rejection (p=0.026) and Step 3's fully
  independent, model-free check (median reliability 0.18) point in
  different directions on how much confidence to place in the result.
  This is exactly the kind of disagreement the brief's own abstract
  rule anticipated and pre-resolved -- it is reported here as designed,
  not adjudicated further.
- Vitinha and Busquets, the two players whose intervals clear the bar,
  are both cited BY NAME in the brief's own "Why" section as examples
  of high-volume players the precision-weighting fix was meant to let
  speak (Busquets explicitly; Vitinha implicitly via "Vitinha..."). This
  is disclosed as a striking but expected consistency check, not
  evidence used to select or tune anything -- the brief named them
  before this task ran any number.

## 11. Questions for the research lead
1. Section 6 applies the pre-declared abstract rule mechanically: report
   that deep midfielders differ, naming only Vitinha and Busquets. Is
   this the final framing for the abstract, or does Step 3's much lower
   independent reliability estimate warrant softening the claim further
   (e.g. describing it as suggestive rather than established)?
2. The >=500-pass subset (Step 3, Step 4b) has only 16 players -- is
   this considered a large enough base for Step 3's own reliability
   estimate to be trusted at all, or does it need a larger qualifying
   pool (which would require relaxing the 500-pass floor, out of this
   task's scope) before it can inform the abstract rule's second
   condition in a future cycle?

## 12. Files produced
- `src/engine_v2/task29_step1_2.py` -- new. Within-group sigma2_w/rho,
  DerSimonian-Laird tau^2 (primary + pooled-v_i comparison), REML tau^2
  (secondary), shrinkage.
- `src/engine_v2/task29_step3.py` -- new. Match-based split-half
  reliability check, independent of the shrinkage model.
- `data/processed/engine_v2/task29_dm_shrunk.parquet` -- new data
  artifact (not committed, `data/` is never committed).
- `data/engine_v2_task29_step1_2.json`, `engine_v2_task29_step3.json`
  -- new summary JSONs backing this page (also under `data/`, not
  committed).
- `docs/results/29-deep-midfield-noise.md` -- this file.
- Commit hashes: `b197846` (Step 0, brief alone), `<pending>` (this
  results page + code) -- to be filled in a follow-up commit per
  CLAUDE.md rule 9.

## 13. Confidence
High confidence in Steps 1-2's mechanics: both are direct, literal
implementations of the brief's own formulas, and the DL-vs-pooled-v_i
comparison (Section 4) directly demonstrates which of the two named
specification problems drove the original null, exactly as the brief
asked. Confidence in what to DO with the result is lower and
deliberately left to the pre-declared abstract rule rather than this
page's own judgment: Step 2 (model-based) and Step 3 (model-free) point
in different directions, and the abstract rule's "exactly one holds"
branch is the mechanism that was designed in advance to handle exactly
this disagreement. The weakest link is Step 3's own small sample (16
players, wide 5th-95th percentile band crossing zero) -- it is a real,
informative caution, not a sign of a computational error, but it means
this task's own independent check has limited power to detect
reliability even if it exists.
