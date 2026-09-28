# SSAC27 abstract — DRAFT v1 (research lead, 2026-09-28)

Status: draft for the author's review. Every number is traced to a
results page in the source map at the bottom. Limit: 500 words, up to
two tables or figures.

---

## Measuring the Regista: A Falsification-Tested Model of Passing Decisions

Passing statistics count what happened: completions, progressive passes,
expected assists. They do not ask whether the passer chose well from the
options he had. We build a decision model on StatsBomb 360 open data
(299 matches, 250,850 passes). For every pass, it evaluates about 420
candidate destinations on a 4-yard grid using the freeze frame: the
probability the ball arrives, and how the passing team's chances of
scoring and conceding within the next ten actions change if it does or
does not. A second model learns what players typically choose in that
situation. A player's Decision score is how much more value his chosen
pass carried than the typical choice.

Before any player result, the engine had to pass six pre-registered
falsification tests (for example, an unmarked teammate must outrank a
marked one at equal completion probability, and a through ball behind a
square defensive line must rank in the top decile) plus out-of-sample
outcome tests. It failed repeatedly until an audit found that coordinate
handling had rotated about half of all events by 180 degrees; the
uncorrected engine had concluded that teams with better decision-makers
create less xG. The corrected engine passes all six tests. With every
match scored by models that never saw it, a one-standard-deviation
higher team Decision score is associated with +0.25 xG per match
(p < 10^-9) and +0.21 goals (p < 0.001). On 126 women's international
matches never used in development, scored by the frozen model, the
associations replicate (+0.26 xG, +0.34 goals; both p < 10^-5; Table 1).
After controlling for completion rate, progressive passes and expected
assists, the goals association survives in both samples; the xG
association does not.

Decision behaves like a player trait. Split-half reliability is 0.82 at
200 passes, and 79% (90% CI 71-89%) of its systematic variation sits
with players rather than team systems (2,099 player-team units, 159 team
contexts). Players who moved between club and country kept their scores
(disattenuated r = 0.62, CI 0.26-1.00), but this falls to 0.27
(CI -0.14 to 0.66) after adjusting for where on the pitch they pass:
part of what "travels" is role.

Among 111 deep midfielders (at least half their passes from defensive
midfield), Decision is nearly independent of standard statistics
(|r| <= 0.19 with expected assists, completion rate and progressive
passes); it measures something they do not. Deep midfielders do differ
(heterogeneity p = 0.026), but modestly. Only Vitinha and Sergio
Busquets have 90% intervals entirely above the group average (Table 2),
and an independent split-half check among the 16 highest-volume players
was underpowered. At open-data sample sizes, the honest answer to "who
is the best regista?" is that two players separate from the pack and
the rest cannot yet be told apart.

Code, pre-registered analysis plans and every failed test are public at
[REPO URL]. Data: StatsBomb.

---

### Table 1. Team Decision and match outcomes (coefficient per 1 SD of team Decision; p)

| Outcome | Study sample, cross-fitted (583 team-matches) | Holdout, frozen model (250 team-matches) |
|---|---|---|
| xG | +0.249 (p = 2.4e-10) | +0.261 (p = 6.7e-6) |
| Goals | +0.215 (p = 2.3e-4) | +0.336 (p = 1.3e-6) |
| xG, controlling for completion, progressive passes, xA | +0.092 (p = 0.069) | +0.066 (p = 0.33) |
| Goals, same controls | +0.264 (p = 3.9e-4) | +0.280 (p = 2.1e-4) |

Uncorrected engine, same xG test: -0.138 (p = 1.8e-4).

### Table 2. Deep midfielders with at least 500 eligible passes (Decision per 100 passes, shrunken, 90% interval; group average 0.228)

| Player | Passes | Decision | 90% interval |
|---|---|---|---|
| Vitinha | 1,764 | 0.270 | 0.236-0.305 |
| Sergio Busquets | 2,994 | 0.265 | 0.236-0.295 |
| Marco Verratti | 3,518 | 0.248 | 0.219-0.276 |
| Toni Kroos | 855 | 0.246 | 0.205-0.288 |
| Pierre-Emile Højbjerg | 826 | 0.240 | 0.199-0.282 |
| Granit Xhaka | 3,510 | 0.236 | 0.207-0.264 |
| Miralem Pjanić | 620 | 0.235 | 0.192-0.278 |
| Remo Freuler | 552 | 0.234 | 0.189-0.278 |
| Jorginho | 694 | 0.225 | 0.181-0.268 |
| Robert Andrich | 1,533 | 0.219 | 0.183-0.254 |
| N'Golo Kanté | 521 | 0.218 | 0.174-0.263 |
| Aurélien Tchouaméni | 812 | 0.217 | 0.175-0.259 |
| Exequiel Palacios | 1,634 | 0.213 | 0.177-0.248 |
| Leandro Paredes | 858 | 0.210 | 0.169-0.251 |
| Marcelo Brozović | 833 | 0.203 | 0.161-0.244 |
| Declan Rice | 1,050 | 0.195 | 0.155-0.234 |

---

## Source map (not part of the submission)
- 299 matches, 250,850 passes, ~106M candidates: results/25 and the crossfit summary.
- Six tests, all pass: results/25, falsification table.
- Coordinate bug, ~half of events: results/24 (confirmed on all 299 matches).
- Uncorrected xG -0.138 p=1.8e-4: results/25 outcome table, engine v1 column.
- Cross-fitted xG +0.2486 p=2.4e-10; goals +0.2147 p=2.3e-4; H-O2 xG +0.0917 p=0.069; H-O2 goals +0.2641 p=3.9e-4: results/25.
- Holdout 126 matches, 250 units; xG +0.2611 p=6.7e-6; goals +0.3358 p=1.3e-6; H-O2 xG +0.0664 p=0.326; H-O2 goals +0.2797 p=2.1e-4: results/26 Step 1.
- Reliability 0.8191 at 200 passes: results/25 T6.
- S = 0.7939, parametric bootstrap CI [0.7086, 0.8866]; 2,099 units, 159 contexts: results/26 Section 13.
- PH-B2 0.6234 [0.2586, 1.0]; residualised 0.2716 [-0.1372, 0.6626]: results/26, results/27.
- 111 deep midfielders; |r| <= 0.19 (xA 0.18, completion -0.19, progressive -0.06): results/27 Step 4(d).
- Q p = 0.0263; Vitinha and Busquets only; 16 players, reliability 0.1846: results/29.
- Table 2 values: results/29 Step 4(b).

## Open items before submission
1. "Associated with", not "predicts": team Decision and xG/goals are
   measured in the same match. Do not strengthen this wording.
2. Word count check (target <= 500 for the body).
3. Repo URL once public; StatsBomb credit and logo in the repo README.
4. Author name and affiliation per the submission form.
5. Disclosure: the Task 29 brief named Busquets and Vitinha as examples
   of high-volume players before results existed (chosen for sample
   size, not rank). Recorded in the journal.
