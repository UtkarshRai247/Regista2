# SSAC27 abstract — DRAFT v2 (research lead, 2026-09-29)

Supersedes docs/abstract/SSAC27-abstract-draft.md (v1, stale: it used
the same-match outcome link, now known to be partly mechanical, and
said 299 matches). Every number below is traced in the source map.
Limit: 500 words for the body; up to two tables/figures.

---

## The Regista's Trade-off: Measuring Tempo and Press Resistance in Elite Deep Midfielders

Deep-lying playmakers are judged by the eye test: they "dictate the
tempo" and "never lose the ball." We ask which of these qualities can be
measured reliably from free data, whether they belong to the player
rather than his team, and whether they matter for results. Using nearly
4,000 StatsBomb open-data matches (men's and women's, club and
international) plus PFF broadcast tracking of the 2022 World Cup, we
built candidate measures, pre-registered every test, and judged each
only on data held back from its development.

Two traits pass. Press resistance, keeping the ball after receiving it
under pressure relative to what is typical for the situation, is stable
within deep midfielders (split-half reliability 0.67-0.70), travels
with the player between club and national team (disattenuated r = 0.65,
127 players), and predicts his team reaching the final third relative
to teammates in the same match (+1.3 percentage points per SD,
p < 10^-16) on 1,985 matches untouched during development. Tempo
choices, how often a player speeds play up with a forward or through
pass, slows it down by recycling, or switches play, are among the most
stable traits we measured (0.83-0.90 within deep midfielders). On 1,137
held-back matches they predict progression for all players (speeding up
+0.63 points, recycling -0.62, switching +0.37; all Holm-adjusted
p < 10^-5). For deep midfielders, switching adds to press resistance
(+0.74 points, p < 10^-4), and the two trade off: 6s who accelerate more
often are less press-resistant (r = -0.29). Elite registas sit at
different points on this trade-off. Busquets rarely speeds play up
(bottom 6%) but releases quickly and safely under pressure (top 7%);
Kroos is a switcher (top 7%).

Two popular ideas fail. Being "always available", open to receive at a
teammate's pass, is stable but linked to fewer chances (tracking data;
exploratory). Pass-choice value, the value of the chosen option minus a
typical choice, is a skill that shows up in a player's other matches
(+0.075 xG per 100 passes per SD, replicated on 126 unseen matches), but
it is driven by forwards and does not separate deep midfielders.

An audit also found that a coordinate-normalisation step had reversed
the attacking direction for about half of all events and, uncorrected,
produced the opposite finding. Every failed test is published with the code. We release a
scorecard for every deep midfielder, with uncertainty intervals and an
evidence tier for each dimension (Figure 1).

---

### Table 1. Pre-registered results on held-back data (per SD of the player's score in his other matches, compared with teammates in the same match)

| Trait | Test | Held-back data | Estimate [95% CI] | Holm p |
|---|---|---|---|---|
| Press resistance | Stability within DMs | 2015/16 (185 DMs); reserved (182) | 0.666; 0.696 | — |
| Press resistance | Travels club to country | reserved, 127 players | r = 0.650 [0.500, 0.797] | < 0.002 |
| Press resistance (team-adjusted) | Team reaches final third, all players | reserved, 1,985 matches | +1.28 pp [0.99, 1.57] | 3.7e-17 |
| Speeding up | Team reaches final third, all players | 2015/16 La Liga, Serie A, Ligue 1 | +0.63 pp [0.45, 0.81] | 7.7e-11 |
| Recycling | same | same | -0.62 pp [-0.82, -0.43] | 3.8e-09 |
| Switching | same | same | +0.37 pp [0.22, 0.51] | 2.5e-06 |
| Switching, with press resistance | same, deep midfielders (141) | same | +0.74 pp [0.41, 1.07] | 3.1e-05 |
| Speed-up vs press resistance | Correlation within DMs | same | r = -0.29 [-0.44, -0.12] | — |
| Pass-choice value | Chance value of his passes | women's holdout, 126 matches | +0.078 xG / 100 passes [0.024, 0.132] | 0.005 |

### Figure 1. Regista scorecard excerpt
[To be produced by Task 54: within-DM percentiles with 90% intervals and
evidence tiers for the rule-selected players.]

---

## Source map (not part of the submission)
- Match counts: study 292 (engine), 2015/16 1,551 (development 414 +
  replication 1,137), reserved 1,985 (1,184 women's), holdout 126;
  total 3,954. PFF WC2022 64 (same matches as the study's WC2022).
- PR stability: results/44 (0.666, n 185); results/48 report-only (0.696, n 182).
- PR travels: results/48 C4 (+0.650 [0.500, 0.797], 127 movers).
- PR team-adjusted -> Y_F3: results/48 C6 (+1.281 [0.988, 1.573], Holm 3.7e-17).
- Tempo stability: results/53 S1-S3 (0.898, 0.844, 0.830), S4 0.806, S5 0.688.
- Tempo -> Y_F3 all players: results/53 R4 (+0.6274, Holm 7.71e-11),
  R5 (-0.6239, 3.82e-09), R6 (+0.3684, 2.53e-06).
- DM switching with PR: results/53 R1 (+0.7430 [0.4128, 1.0731], Holm 3.09e-05).
- Trade-off: results/53 C1 (-0.292 [-0.439, -0.122]).
- Busquets M4_ACCEL rank 133/141 (5.7%); M2 rank 9/141 (6.4%); Kroos
  M4_SWITCH rank 9/141 (6.4%): results/53 Step 4 DM tables.
- Availability: results/38 (stability DM 0.740, n 28; P-test all
  -0.0692 per 100 receptions per SD, p 0.0028; not confirmed).
- Pass-choice value: results/35 (+0.0747, Holm 0.0087); results/37
  holdout (+0.0780 [0.0237, 0.1322], p 0.0048); forwards: results/41;
  DM null: results/35, 37.
- Coordinate audit: results/24 (80/156 vs 76/156 team-periods flipped);
  engine v1 xG -0.138 vs v5 +0.249 (same-match test, results/25).

## Open items before submission
1. Figure 1 from Task 54.
2. The quick-and-safe Busquets claim uses the 2015/16 replication-league
   DM table; if Figure 1 uses a different group, update the percentile.
3. PFF-derived numbers (availability) appear in the abstract: author to
   confirm PFF's terms allow this before submission.
4. Word count (body currently 395).
5. Repo URL after it goes public.
