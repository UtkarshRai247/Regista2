# SSAC27 abstract — DRAFT v2 (research lead, 2026-09-29)

Supersedes docs/abstract/SSAC27-abstract-draft.md (v1, stale: it used
the same-match outcome link, now known to be partly mechanical, and
said 299 matches). Every number below is traced in the source map.
Limit: 500 words for the body; up to two tables/figures.

---

## The Regista's Trade-off: Measuring Tempo and Press Resistance in Elite Deep Midfielders

Deep-lying playmakers are judged by the eye test: they "dictate the
tempo" and "never lose the ball." These qualities are easy to see and
hard to count, and a count means little unless it describes the player
rather than his team. We turn both into measures from free data and show
that they are stable within deep midfielders, that they help a team move
the ball up the pitch, and that press resistance follows the player from
club to country.

We use nearly 4,000 StatsBomb open-data matches, men's and women's, club
and international, plus PFF broadcast tracking of the 2022 World Cup.
Every measure compares what a player did with what is typical in the
same situation, predicted from location, pressure, score and type of
play by models trained on other matches. Press resistance asks whether
he keeps the ball after receiving it under pressure. Tempo choices ask
how often he speeds play up with a forward or through pass, slows it
down by recycling, or switches play, and how often he releases the ball
quickly and safely when pressed. A pass-value engine scores about 420
possible destinations per pass. The tests are what is new. Each was
pre-registered; results are measured against a player's teammates in the
same match, using his scores from other matches; club and international
appearances separate player from team; and every headline result was
confirmed on data held back from development.

Press resistance is stable within deep midfielders (split-half
reliability 0.67-0.70) and follows the player between club and national
team (disattenuated r = 0.65, 127 players). On 1,985 untouched matches,
a player one standard deviation more press-resistant sees his pressured
receptions lead to the final third 1.3 percentage points more often than
his teammates' (p < 10^-16).

Tempo choices are among the most stable traits we measured (0.83-0.90
within deep midfielders). On 1,137 held-back matches, players who speed
play up or switch it more often help their teams progress (+0.63 and
+0.37 points), and those who recycle more often slow it (-0.62; all
Holm-adjusted p < 10^-5). For deep midfielders, switching adds to press
resistance (+0.74 points, p < 10^-4), while speeding up trades off
against it: 6s who accelerate more often are less press-resistant (r =
-0.29). Elite registas sit at different points on it. Among 185 deep
midfielders, Busquets and Kroos are both in the top 2% for press
resistance; Busquets rarely speeds play up (bottom 8%) but releases
quickly and safely under pressure (top 7%), while Kroos is a switcher
(top 5%) who seldom accelerates (bottom 30%).

Pass-choice value is a skill measured in a player's other matches and
replicated on 126 unseen matches (+0.075 xG per 100 passes per SD), but
it mainly separates forwards. Being "always available" is stable but
goes with fewer chances in tracked World Cup matches (exploratory). We
release a scorecard for every deep midfielder, with uncertainty
intervals and an evidence tier for each dimension (Figure 1); code and
pre-registrations are public.

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
- Player percentiles (Card A, 185 DMs, results/54 A5-A6): Busquets PR2 98, M4_ACCEL 8.1, M2 93.0; Kroos PR2 98, M4_SWITCH 95.7, M4_ACCEL 29.2.
- Availability: results/38 (stability DM 0.740, n 28; P-test all
  -0.0692 per 100 receptions per SD, p 0.0028; not confirmed).
- Pass-choice value: results/35 (+0.0747, Holm 0.0087); results/37
  holdout (+0.0780 [0.0237, 0.1322], p 0.0048); forwards: results/41;
  DM null: results/35, 37.
- Robustness of C6 by subset and whole-possession xG (+0.0386, p 0.019, reserved, all players): results/50.
- Availability sample: PFF WC2022, 64 matches (results/38).
- Coordinate audit: results/24 (80/156 vs 76/156 team-periods flipped);
  engine v1 xG -0.138 vs v5 +0.249 (same-match test, results/25).

## Open items before submission
1. Figure 1 from Task 54.
2. Percentiles now come from Card A (185 DMs), the same group as Figure 1.
3. PFF-derived result (availability) kept in the abstract per D-018 (author, option a).
4. Word count: body 495 words (title excluded; 507 with the title).
5. Repo URL after it goes public.
