# Regista 2 — Chat Handoff

Written 2026-09-28 by the outgoing research lead. This document is
authoritative for project state. Where it conflicts with an older
results page, the conflict is flagged explicitly in section 9.

---

## 1. Project identity

**What it is.** Regista 2 is a solo research project by Utkarsh Rai
(University of Washington, CS undergraduate) that tries to measure what
separates elite deep-lying creative midfielders — registas — from each
other, using only free, public soccer data. The football question is:
can the "eye test" that scouts and fans use to rank players like Kroos,
Verratti, Busquets, Pedri, Rodri and Frenkie de Jong be quantified well
enough to compare them against each other?

**External target.** MIT Sloan Sports Analytics Conference 2027
(SSAC27) Research Papers Competition.
- Abstract deadline: **Oct 1 2026, 11:59pm ET** (target submission Sep 30).
- Full paper, if selected: **Dec 4 2026**.
- The competition requires a **public GitHub repository including the
  data used**. Decision D-006 resolves this by shipping code and
  download scripts rather than raw third-party data.
- The repo is currently **still private**; D-001 said it would go public
  Sep 28. That has not happened.

**Why it exists — the Regista 1 critique.** Regista 1 ("the Architect
Framework") built six metrics for deep-lying playmakers on StatsBomb
open data and presented Granit Xhaka as its case study. A systematic
review found flaws serious enough to require a rebuild rather than a
patch:

1. **Circular validation.** Its main test separated known registas from
   known non-registas. The labels came from the same intuitions the
   framework was meant to test, so it confirmed priors rather than
   measuring value.
2. **Style mixed with quality.** The composite "Architect Score" added
   z-scores of metrics describing *what a player does* to metrics
   describing *how well*, with equal weights chosen arbitrarily and no
   units. Xhaka ranked 9th of 22 on a framework partly designed around
   him.
3. **A positional value proxy.** Decision Surplus valued options by
   pitch location, which systematically undervalues deep zones — exactly
   where the studied population plays.
4. **Off-policy extrapolation.** Counterfactual pass values relied on a
   success model trained only on passes players actually chose; the
   0.935 AUC was measured on chosen passes and said nothing about
   unchosen ones.
5. **Wrong baseline.** Surplus was measured against the *best* option
   (regret), not against what a typical player would choose.
6. **Attention treated as attribution.** Transformer attention weights
   were used for credit assignment, which the interpretability
   literature does not support.
7. **Player and system unidentifiable.** One team-season (Leverkusen
   2023/24) cannot separate a player's skill from his coach's system.
8. **No uncertainty.** Point estimates throughout; split-half
   reliability was r=0.47 (p=0.24) on 8 players.

**The five pillars** were the planned response:
1. A rebuilt decision engine: learned value function, full action space,
   behavior-policy baseline, decomposed into Decision / Execution / Risk.
2. Visibility calibration of freeze frames against full tracking.
3. A hierarchical model separating player from team context.
4. Outcome and market grounding.
5. Unsupervised role discovery.

---

## 2. Full status by pillar

### Pillar 1 — Decision engine — REBUILT ONCE, CURRENTLY NOT ACCEPTED

**Engine v1 (Task 01):** built, used for Tasks 01–14b, then **withdrawn
as a measurement** (D-015) after `docs/ENGINE_AUDIT.md` found five
defects. Its numbers (for the record, all now withdrawn):
- Decision split-half reliability 0.744 (5th–95th: 0.691–0.792) at ≥200
  eligible passes; Execution 0.482 (0.300–0.603), never reaching 0.70 at
  any threshold up to 500.
- Pass success AUC 0.867; possession value AUC 0.799 in-sample, 0.743
  out-of-fold; behavior policy ~3× random at top-1.
- Separation: Decision vs Execution r=0.058, vs progressive passes 0.093,
  vs xA −0.026, vs completion% 0.338; Decision vs Risk −0.776.

**The five defects (full detail in `docs/ENGINE_AUDIT.md`):**
1. **EV was algebraically a risk score.** EV = V_turn + p·(V_succ −
   V_turn); the bracket barely varied across destinations while p varied
   0.98→0.50, so ranking by EV was ranking by completion probability.
   Turnovers were also double-penalised.
2. **The value model could not see defenders.** Features were ball
   location, previous location, time, score, play pattern. A ball
   through the line and a sideways ball to the same coordinate scored
   identically. This violated the Task 01 brief in writing.
3. **Execution measured nothing.** It reduces to (1−p)(V_succ − V_turn)
   on completed passes — a completion-rate residual. Invalidates Study C.
4. **The scored destination was often not the pass played.** Median 5.05
   yards off; 50.4% >5y, 29.2% >10y, 13.2% >20y; by length: 0–20y ~4y,
   20–30y 5.5y, 30–50y 10.1y, 50y+ 35.1y. Error grew with pass length —
   worst for the progressive passes that define the studied population.
   It also corrupted the pass-success model's training pairs.
5. Feature/option-space defects: non-direction-normalised coordinates
   and absolute bearings in the success model; a 1-yard "lane" threshold
   from a yards/metres confusion so lane congestion never fired; no
   offside check; no representation of passes into space; congested-area
   passes discarded by an ambiguity rule.

**Engine v2 (Tasks 15, 17, 18, 19, 19c, 19d):** destinations on a 4-yard
grid (~423 candidates per pass, 106,141,669 candidate rows) with the
chosen option being the cell containing the actual `pass_end_location`;
direction-normalised shared features; two value models (P(team scores in
10 actions), P(opponent scores in 10)); symmetric net value; calibrated
softmax policy baseline.

Falsification battery history:

| Test | Pass condition | Task 15 | Task 19c | Task 19d (current) |
|---|---|---|---|---|
| T1 destination fidelity | ≤2 yards | 1.61y PASS | — | — |
| T2 value model sees defence | responds materially | −0.0159 (~41×) PASS | — | −0.0207 (~55×) PASS |
| T3 EV not a risk score | Spearman < 0.90 | 0.599 PASS | — | 0.664 PASS |
| T4 three synthetic scenarios | all three hold | 3/3 PASS | 3/3 PASS | **scenario_c FAIL** |
| T5 calibration by length | ≤5pp per bucket | max 2.73pp PASS | unaffected | unaffected PASS |
| T6 Decision reliability @200 | ≥0.60 | 0.780 | 0.658 | **0.615 PASS (thin)** |

**T4 scenario_c**: "through ball to a teammate beyond a square defensive
line must be in the top EV decile" — EV 0.00232 vs corpus 90th
percentile 0.00402. **FAIL.**

**Therefore the engine does not currently meet its own acceptance
criteria** (`docs/specs/engine-v2-rebuild.md` section 6 requires all
three T4 scenarios). Under the rule written into Task 21's brief, **no
player-level claim may be made until it does.**

Other engine v2 numbers:
- Policy baseline sharpening (Task 18): median effective options 421.7 →
  56.3; correlation between policy-weighted and unweighted baseline
  0.9986 → 0.855; top-1 accuracy up roughly half again. Cost: Decision
  reliability 0.780 → 0.704.
- Offside (Tasks 19, 19c): the original rule flagged **43.11%** of real
  completed passes as offside with 50.51% recall. Cause was a sort-index
  bug (`opp_nx_sorted[1]`, second-*smallest* x, instead of `[-2]`).
  Corrected: FP 23.69%, recall 46.58%. Calibrated rule **R4** (K≥10
  visible opponents, attacking half only, 1-yard tolerance) clears the
  pre-specified 5% false-positive bar at FP 4.83%, recall 16.96%. R4 is
  the rule currently in force. Restricted-policy coverage of real chosen
  destinations: 54.5% (Task 18) → 96.3% (Task 19, offside dropped) →
  91.7% (Task 19c, R4).
- Orientation sweep (Task 19d): found **one further instance of the same
  bug**, in `value_models.py`'s `frame_ahead_features`, which built the
  value models' *training data*. Both value models had been trained on a
  corrupted `defensive_line_x` / `ball_beyond_defensive_line` throughout
  Tasks 15–19c. After fixing: M_for AUC 0.8706 → 0.8660, M_against
  0.9108 → 0.9103; T4 scenario_c began failing; cross-fitted outcome
  coefficients shrank, and **two specifications (xG and goals under
  H-O2, the richest control set) lost significance for the first time**.
- Task 21 (possession-state features) **stopped at its premise check**.
  The proposed fix assumed "beyond the line with a teammate near scores
  more than beyond the line with none". That held in only **1 of 3**
  pitch bands (60–80), was inverted in 80–100 and 100–120, including
  **zero scoring events in 2,602 beyond-line-with-teammate rows** in the
  80–100 band. Per the brief, Steps 4 and 5 were not run. No claim is
  made about whether the v3 models are better.

Empirical table that motivated Task 21 (from
`value_model_rows_v2.parquet`), P(team scores within 10 actions):

| Band | Not beyond line | Beyond line |
|---|---|---|
| 0–40 | 0.73% | 0.99% |
| 40–60 | 0.27% | 0.21% |
| 60–80 | 0.31% | 0.13% |
| 80–100 | 0.98% | 0.28% |
| 100–120 | 2.96% | 1.18% |

Conceding rises in the final band, 0.48% → 0.84%. In this data a ball
beyond the defensive line is **less** dangerous — mostly balls through
to the keeper, overhit crosses and passes to nobody.

### Pillar 2 — Visibility calibration — ABANDONED (twice over)

1. **Prior art.** DeepMind's Graph Imputer (Omidshafiei et al., *Sci
   Rep* 2022) already does off-screen imputation with a simulated
   broadcast camera mask; Everett et al. (arXiv 2311.14642) reports
   ~7.33m error for non-visible players and ships a StatsBomb-360 mode
   with a visible/estimated flag; a 2026 arXiv paper does training-free
   off-screen imputation with a simulated-viewport benchmark and
   measures downstream effects on a possession-quality score.
2. **The data killed the premise.** PFF's tracking was to be ground
   truth, but **57.2%** of its player-position rows are flagged
   ESTIMATED rather than VISIBLE. It is another imputation model, not
   ground truth.

Also relevant: PFF has **no stated licence anywhere** (checked: blog
posts, Drive folder, all files). D-005 dropped PFF partly on that basis.
**See the discrepancy in section 9** — the licence rationale was later
judged to be wrong, but that correction was never recorded in
DECISIONS.md or the journal.

### Pillar 3 — Hierarchical player-vs-system model — BUILT, THEN WITHDRAWN WITH ENGINE V1

Study B on engine v1 (Tasks 07, 08, 10):
- Hand-built REML estimator passed all three parameter-recovery
  scenarios on the real design (mean |S error| 0.032, 0.002, 0.003).
- 1,701 stage-1 units, 1,232 players, 157 team contexts. Gate E passed:
  345 players with 2+ contexts, 132 club-plus-international movers, 119
  of them in the same position group.
- S (player share of systematic variance) = **0.654**.
- Interval history, which matters: cluster bootstrap with original ids
  gave [0.626, 0.785] (biased **up** — duplicate players looked like one
  player replicating himself); with fresh ids [0.363, 0.573] (biased
  **down** — duplicates inside one team context looked like team-level
  replication). The corrected interval **did not contain the point
  estimate**, which is a diagnostic of a broken method.
- Coverage test (Task 10): cluster bootstrap covered truth in **10 of
  100** simulations. Parametric bootstrap and profile likelihood both
  **93%**. They tied exactly; the code broke the tie by list order, which
  was disclosed, and verdicts were computed both ways and were identical.
- Primary interval (parametric bootstrap): **S = 0.654 [0.566, 0.755]**;
  with position fixed effects [0.547, 0.743]. **Tier 1 ALLOWED** — within
  the systems observed, most systematic variation sits with the player.
- **Tier 2 NOT ALLOWED.** Mover correlation r = 0.053 [−0.126, 0.259];
  disattenuated 0.10 [−0.25, 0.53]; multi-context-only fit's lower bound
  0.466. Design calculation: a decisive test needs about **314 movers**
  at current reliability; this sample has 132.
- Only **11 players** clear 200 passes in both club and international
  contexts — which is why the naive "does it travel" design was dead and
  the pass-level crossed model was used instead.

All of this is withdrawn as measurement under D-015 and must be re-run
on an accepted engine (Task 20 brief exists but has not been run).

### Pillar 4 — Outcome and market grounding — MARKET CLOSED; OUTCOME VALIDATION IS THE LIVE REFEREE

**Market test (Tasks 02, 03, 10, 11), closed:**
- 125 units, 96 players, 61 tournament / 64 league, after widening the
  valuation window to 180 days (Amendments v2-1, v2-2).
- Decision coefficient **−0.285, p = 0.733, 95% CI [−1.925, 1.355]**;
  −2.40% market value per SD, CI [−15.13%, +12.24%]. n=125, R²=0.588,
  VIF max 3.53.
- H3 (later correction): Decision −0.775, p = 0.111.
- Robustness: 2 of 6 variants (90-day/79-unit, league-only) significantly
  negative (p=0.043, 0.033); none significantly positive.
- **Minimum detectable effect ≈ 2.35 log points ≈ 22% market value per
  SD.** The study was underpowered by roughly a factor of two. The null
  describes the sample size, not the market.

**Outcome validation — engine v1 (Tasks 10, 11), the test it failed:**
- Team-match xG: **−0.138** per SD (p=0.0002); goals **−0.403**
  (p<1e-12); both survived adding completion rate, progressive passes
  and xA.
- Zone-mix controls and team fixed effects made it **worse**, not better
  (−0.153, then −0.176). The compositional explanation was refuted.
- Possession level (20,030 possessions): more shots (+0.012 per SD,
  p=0.0003), **no** improvement in possession xG (p=0.236).
- Raw correlation of team mean Decision with xG: **+0.021**. It
  correlates +0.341 with possession share, which correlates +0.384 with
  xG. **Possession share is plausibly a mediator, not a confounder** —
  a specification error by the research lead, disclosed in Amendment
  v2-9.1. The preregistered results stand as reported.

**Outcome validation — engine v2 (Tasks 17, 18, 19, 19c, 19d):** every
sign reversed:

| Specification | Engine v1 | Engine v2 (Task 17, in-sample) |
|---|---|---|
| Team xG (H-O1) | −0.138 | +0.269 |
| Team xG, team fixed effects | −0.176 | +0.283 |
| Team goals | −0.403 | +0.318 |
| Possession ends in shot | +0.012 | +0.058 |
| Possession xG | −0.001 (null) | +0.015 |

Cross-fitting (Task 18) **held**: signs kept, most significance kept,
magnitudes shrank 30–45%, which is the expected size of in-sample
inflation. After the Task 19d orientation fix the coefficients shrank
further and two H-O2 specifications lost significance. Exact current
figures: `docs/results/19d-orientation-sweep.md`, Step 5.

**Referee 1 / Referee 2 (plan v3, Tasks 14a, 14b), on engine v1:**
- Referee 1: **no objective wins.** The rule required both a positive
  possession-level xG coefficient and a positive team-match xG
  coefficient without possession share. None of O1/O2/O3 managed both.
  Ordering was consistent across every team-level test: O3 > O2 > O1.
- Referee 2: **UNDERPOWERED**, declared before any AUC was computed.
  Only 23 of 77 selected players matched our qualifying units; the
  minimum detectable AUC improvement was **0.267**. It cannot decide
  between objectives in either direction, including in O1's favour.
- Leaderboard movement under O3 vs O1 (withdrawn, but informative):
  Grillitsch 1 → 64, Shaparenko 2 → 110, while Kroos (112 → 123),
  Verratti (117 → 103), Modrić (129 → 128) and De Bruyne (159 → 160)
  stayed at the bottom under every objective. This is what prompted the
  engine audit.

### Pillar 5 — Role discovery — CUT (D-002), never started.

### Additional module: Tempo (Tasks 16, 16b) — COMPLETE AND INDEPENDENT

The only part of the project untouched by the engine defects: it uses
millisecond event timestamps and ball-receipt events, no value model, no
expected value, no option set. **It survives D-015 intact.**

Task 16 (first build):
- Coverage 72.6% of open-play passes have a resolvable receipt chain;
  carry sanity check passed first time (1.285s vs 0.000s).
- `median_time_on_ball` **0.939 USABLE**; `one_touch_share` **0.959
  USABLE**; `pressure_delta` 0.595 PROVISIONAL; `pace_delta` 0.456 and
  `tempo_variation` 0.097 **NOT MEASURABLE**, reported and dropped.

Task 16b (diagnostic + one redesign), all four suspected causes
confirmed with sizes:
- **Contamination:** sequences had been built from engine v1's 171,618
  *matched* passes rather than 289,001 open-play passes. 75.4% of
  possessions differ in pass count by ≥2. Median pace 0.283 → 0.373.
- **On-pitch:** **42.0%** of "without him" comparison sequences occurred
  while the player was off the pitch.
- **Split granularity (dominant cause):** on the same contaminated data,
  splitting at sequence level instead of match level moves pace_delta
  reliability from **0.456 to 0.913**. Diagnostic only — that split
  needs 200 sequences per player and n falls to 54.
- **Ratio noise:** real but smaller; 2.4% of sequences under 3 seconds.
- Redesign succeeded first time: **MOVE_ON_SPEED 0.783**,
  **HOLD_VARIATION 0.881**, both USABLE, monotone reliability curves.

Why MOVE_ON_SPEED matters: it is **nearly orthogonal to everything
else** — 0.117 with median time on ball, 0.064 with completion rate,
0.054 with progressive passes, −0.225 with xA. It is the first quantity
in this project that is both reliable and not a restatement of role or
safety. HOLD_VARIATION is weaker on that count (0.669 with median time
on ball).

Tempo limitations already on the record:
- The usable metrics substantially encode **role**: the ten longest
  holders are all centre-backs (Akanji 2.60s, Aké, Stones, Tapsoba,
  Marquinhos); fastest releasers are forwards and attacking midfielders
  (Boniface 0.08s, Griezmann, Busquets). All tempo metrics are therefore
  also reported as within-position-group z-scores.
- `pressure_delta` correlates **−0.858** with median time on ball, close
  to arithmetic (longer holders have more room to drop; nobody drops
  below zero). It is described as a restatement of baseline hold time,
  **not** as composure. Deliberately not repaired.
- MOVE_ON_SPEED measures how fast the **team's** next pass follows his,
  so attribution is shared with the receiver.
- **No outcome test exists for any tempo metric**, by design: it would
  need a working value model, and running it on engine v1 would build on
  a withdrawn measurement.
- Face validity, recorded but never used as a criterion: hold variation
  is topped by Akanji, Ream, Frenkie de Jong, Bernardo Silva, Skriniar.

---

## 3. Data

**Sample:** 299 matches, 8 men's competition-seasons with StatsBomb 360
coverage: FIFA World Cup 2022, UEFA Euro 2020, UEFA Euro 2024, La Liga
2020/21, Ligue 1 2021/22, Ligue 1 2022/23, Bundesliga 2023/24, MLS 2023.
1,145,062 events → 328,892 passes → 289,001 open play → 251,229 with a
freeze frame → 250,850 with ≥6 visible → 171,618 angle-matched (engine
v1 only; engine v2 does not drop these).

**Structural fact to remember:** every club competition-season is built
around **one focal team** — PSG (both Ligue 1 seasons), Leverkusen,
Barcelona, Inter Miami (3 usable matches). Opponents appear in only a
match or two each. The three tournaments (166 of 299 matches) have no
focal team. Any "the sport does X" claim from club data is partly "these
four elite possession sides do X".

**StatsBomb open data (Task 00 audit):** 80 competition-seasons; 426
matches with 360 across 12 competition-seasons; World Cup 2022 has 360
on all 64 matches. Units confirmed empirically as **yards** (195 penalty
spots at median 12.00 units from goal). StatsBomb's GitHub org is now
`hudl/open-data`. Freeze frames carry **no player identity** — only
teammate/actor/keeper flags and locations.

**Score reconstruction validated on all 299 matches** — game-state cells
are trustworthy.

**Market values:** `dcaribou/transfermarkt-datasets`, **CC0-1.0**,
snapshot 2026-07-06, ~650k valuation records. Chosen specifically to
avoid touching Transfermarkt directly.

**Expert selection lists** (`data/expert_lists/selections.csv`): 7 of 8
competition-seasons, 77 selected players. Sources are heterogeneous —
UEFA technical observers (both Euros), players' unions (UNFP for both
Ligue 1 seasons, VDV for Bundesliga), a league office (MLS), and a
single newspaper's journalist XI (World Cup 2022, Sky Sports; FIFA
publishes no official team). La Liga 2020/21 has **no** qualifying
selection and is excluded. The bundesliga.com list was **rejected** for
weighting fan votes at 40% and replaced with the VDV XI.

**Win probability (Tasks 13, 13b, 13c):** built from the 299-match
sample first (failed calibration), then from a 2,090-match men's
2010-11+ corpus (also failed, same bucket, refuting the
sample-composition hypothesis), then fixed by **conditioning scoring
rates on team strength**. The diagnostic was decisive: when the
*stronger* team leads early, predicted 77.7% vs observed 82.6%
(t=1.41); when the *weaker* team leads early, 77.7% vs **42.2%**
(t=−4.34). Strength-conditioned model: zero violating buckets under the
original gate, Brier **0.0893** vs 0.1093 for both earlier versions.
Stronger teams score roughly twice as fast as weaker ones in every game
state. This function is validated and reusable.

**Licences:** see `docs/DATA_LICENSES.md`. StatsBomb open data is free
with attribution ("state the data source as StatsBomb and use our
logo"); full terms beyond the README were never read, which is why D-006
ships code not data.

---

## 4. Every methodology decision, and the walk-backs

Formal decisions D-001 to D-015 are in `docs/DECISIONS.md` and are not
restated here. What follows is the decision *history* including
reversals, because the reversals carry most of the information.

**Decisions that were later reversed or shown wrong:**

1. **D-009 (Pillar 4 as headline) → reversed by D-012.** The market test
   was powered only for ~22%-per-SD effects. The project had drifted
   from "measure registas" to "measure Transfermarkt". The author caught
   this, not the research lead.
2. **D-011 (angle-matching) → reversed by D-015.** The reasoning was
   that `pass_end_location` is post-hoc information. That conflated the
   **action** (where he played it) with the **outcome**. This single
   decision caused engine defect 4 and corrupted the pass-success
   model's training pairs.
3. **Amendment v2-2's Gate D → replaced by a stricter version.** The
   original compared a candidate pass type's calibration to the *modal
   chosen type in the same cell* — but the candidates **were** the modal
   types, so the gate would have compared each to itself and passed
   automatically. Caught before any confirmation data was loaded.
4. **Amendment v2-5.1 bootstrap bug.** Resampled duplicate players kept
   their original ids, inflating the player share. Fixing it flipped
   Study B's Tier 1 verdict from ALLOWED to NOT ALLOWED — and then the
   coverage test (Task 10) showed **both** bootstrap variants were
   invalid, and the parametric bootstrap restored Tier 1. A verdict was
   reversed twice by method correction, never by changing a rule.
5. **Amendment v2-8.2's compositional explanation → refuted.** Zone-mix
   controls and team fixed effects made the negative outcome association
   *stronger*, not weaker.
6. **Amendment v2-9.1 — the research lead's own specification error.**
   Controlling for possession share in the preregistered outcome test
   probably controlled for a **mediator**, removing the pathway the test
   was meant to detect. Disclosed; the preregistered result stands as
   reported.
7. **Amendment v3-2.2's sample-composition diagnosis → refuted by the
   corpus** (Task 13b). Recorded as refuted rather than quietly dropped.
8. **Task 19's conclusion "offside is not detectable from freeze frames"
   → false.** It rested on a sort-index bug, not a measurement
   (Task 19c). The clearest example in the project of a null mistaken
   for a finding.
9. **Task 15's T4 pass → invalid.** It passed with a corrupted
   `defensive_line_x`; with the feature corrected, scenario_c fails
   (Task 19d).
10. **Task 21's proposed fix → stopped by its own premise check.** The
    empirical table did not support the mechanism, so no falsification
    battery or outcome validation was run on the v3 models.

**Standing protections adopted along the way, all of which earned their
keep:**
- Preregistration before results, with dated amendments appended, never
  edits above.
- Gates with thresholds fixed in advance (Gate A reliability, Gate B
  separation, Gate C sample, Gate D calibration, Gate E identifiability,
  T1–T7 falsification).
- Discovery/confirmation split by match (seed 20260920), candidates
  committed before the confirmation half is touched.
- Cross-fitting so no match is scored by a model that saw it.
- Interval methods chosen by **simulated coverage**, not by which answer
  they give.
- Named-player ranks are always **output, never input**; nothing may be
  tuned on them.
- One-repair-pass rules and time boxes on modules (Amendment T-1) to
  stop diagnostic loops.

---

## 5. Known limitations and open risks

**Engine / measurement**
1. **The engine does not currently pass its acceptance battery** (T4
   scenario_c). No player-level claim is permitted until it does.
2. **The value model is a ball-position model, not a possession-state
   model.** It cannot distinguish "through ball arriving at a teammate"
   from "ball running through to the keeper". Task 21's attempted fix
   failed its premise check; the representational problem is unsolved.
3. Decision reliability at 200 passes is **0.615** — above the 0.60 gate
   but thin. A higher threshold should probably be chosen by reliability
   before ranking anyone.
4. Off-policy estimation remains: values for options nobody chose are
   extrapolations.
5. Freeze frames show only visible players; body orientation, off-camera
   runners and player velocities are unavailable. Offside is detectable
   only under restrictive conditions (R4) at 16.96% recall.
6. Two instances of the same sort-index bug were found in independently
   written feature builders. A committed test now asserts the two agree
   (`test_frame_features_agree.py`). Assume more such bugs are possible.

**Sample / design**
7. Four focal club teams dominate the club data (see section 3).
8. A 200-pass floor selects centre-backs and central midfielders; the
   engine v1 sample was 72 defenders / 42 midfielders / 11 forwards.
9. Only 11 players clear 200 passes in both club and international
   contexts; 132 club-plus-international movers against ~314 needed for
   a decisive "does it travel" test.
10. Referee 2's benchmark is heterogeneous (four kinds of selecting body)
    and underpowered (MDE 0.267 AUC). The World Cup row is the weakest
    provenance and contributes the most units; a sensitivity excluding it
    is required wherever Referee 2 is reported.

**Narrative risks for the submission**
11. The paper currently has **no accepted player-level result**. The
    defensible assets are: the engine audit, the tempo module, the
    validated win-probability function, the measurement/reliability
    results, and the methodology.
12. Several headline candidates have already died: market mispricing
    (underpowered), Study A's blind spots (withdrawn with engine v1),
    the objective comparison (no objective won Referee 1).
13. Repeated null results were, on at least two occasions, presented as
    findings when they were engineering errors. **Any null in this
    project should be treated as a suspected bug until an audit says
    otherwise.**

---

## 6. What is running or blocked right now

**Completed and committed:** Tasks 00 through 21 except Task 20. Latest
commits referenced: Task 19d `362cda3 / 20ec298 / db75a8b`; Task 21's
hashes are in `docs/results/21-possession-state.md` Section 7.

**Blocked:**
- **Task 20 (player results: threshold, Study B rebuilt, leaderboard)** —
  brief written at `docs/specs/task-20-player-results.md`, **not run**,
  and must not be run until the engine passes its battery.
- Abstract — not drafted.
- Repo publication — not done.

**Nothing is currently executing.**

**Distributed compute (Mac + "Pavilion"):** *this has never been set up
or discussed in the project record.* All work to date ran on a single
MacBook Pro (Apple M4, 16 GB unified memory, no CUDA). If a second
machine exists, it is unknown to this handoff — treat it as not
configured. Known compute facts: engine v2 has ~106 million candidate
rows; a full EV recompute plus cross-fit runs about 60–65 minutes;
memory failures occurred historically when a script held all 299 matches
at once, fixed by per-match parquet parts; and the correct memory gate is
**live pressure** (proceed at ≥40% free and ≥3 GB available), never
swap-in-use, because macOS never reclaims written swap.

**Outstanding external item:** an email was sent to `fchelp@pff.com`
asking for explicit written permission to use the 2022 World Cup
dataset, publish derived results, and ship a download script instead of
raw data, plus a question about what the ESTIMATED visibility flag
means. No reply as of this handoff.

---

## 7. Pointers — where the detail actually lives

Do not reconstruct these from this document; open the file.

| Topic | File |
|---|---|
| Full narrative history, all entries | `docs/JOURNAL.md` (991 lines) |
| Formal decisions D-001…D-015 | `docs/DECISIONS.md` |
| The five engine defects, in full | `docs/ENGINE_AUDIT.md` |
| Engine v2 design and the T1–T7 battery | `docs/specs/engine-v2-rebuild.md` |
| Market-test preregistration + amendments 1–2 | `docs/specs/analysis-plan-pillar4.md` |
| Studies A/B/C preregistration + amendments v2-1…v2-9 | `docs/specs/analysis-plan-v2.md` |
| Objective comparison + amendments v3-1…v3-5 | `docs/specs/analysis-plan-v3.md` |
| Tempo preregistration + amendments T-1, T-2 | `docs/specs/analysis-plan-tempo.md` |
| Data audit, licences, coverage | `docs/results/00-data-audit.md`, `docs/DATA_LICENSES.md` |
| Study A discovery table (all 107 pairs) | `docs/results/05-study-a-discovery.md` |
| Study A confirmation, Gate D, sensitivities | `docs/results/06-study-a-confirmation.md` |
| Study B, recovery test, Gate E | `docs/results/07-study-b.md`, `08-studies-b-c.md` |
| Interval coverage test, MDE audit, outcome validation | `docs/results/10-validation.md` |
| Outcome diagnostics and the mediator problem | `docs/results/11-outcome-diagnostics.md` |
| Engine v1 leaderboards under O1/O2/O3 | `docs/results/14b-leaderboards-referee2.md` |
| Engine v2 build and battery | `docs/results/15-engine-v2-build.md` |
| Engine v2 validation, policy sharpness | `docs/results/17-engine-v2-validation.md`, `18-policy-and-crossfit.md` |
| Offside bug and fix | `docs/results/19-offside-fix.md`, `19c-offside-fix.md` |
| Orientation sweep (full WRONG/CORRECT/UNCLEAR table) | `docs/results/19d-orientation-sweep.md` |
| Tempo | `docs/results/16-tempo.md`, `16b-tempo-redesign.md` |
| Task 21 premise failure | `docs/results/21-possession-state.md` |

---

## 8. Standing rules for the new chat

Copied verbatim from the author's instructions at the start of the
project:

> Roles: you are the research lead. All methodology, evaluation design,
> decisions and interpretation happen here. Claude Code does all the
> building on my computer. I'm the messenger between you.
>
> Rules:
> 1. Never make me write files. When something must exist as a file, give
>    me one copy-paste block starting with the exact file name, and tell me
>    to paste it into Claude Code with "save this exactly as <file name>".
> 2. Explain any technical term in one plain sentence the first time.
> 3. Keep replies short and plain. No code unless I ask. Decisions first,
>    reasoning after.
> 4. Work backward from the deadline. Give me a week-by-week timeline with
>    go/no-go checkpoints, and cut scope if needed.
> 5. Before any modeling, do a literature check on Pillars 2 and 4 and
>    tell me honestly whether the novelty holds.
> 6. For any headline claim (especially Pillar 4), write the analysis plan
>    first: hypotheses, controls, and what result would count as failure.
> 7. Push back on weak choices. An honest negative result is acceptable.
> 8. After each Claude Code task I'll paste its results page back. You
>    interpret it and give me the next task.

**Later modifications to this arrangement, agreed in the project:**
- The research lead has direct read/write access to the repo via a
  filesystem tool and now writes plan and brief files itself, then gives
  the author a single short prompt to paste into Claude Code. The author
  usually replies only "task done" plus commit hashes; the research lead
  reads the results page directly.
- Claude Code's standing routines (from `CLAUDE.md`): write a results
  page per task to `docs/results/NN-name.md` using
  `docs/results/TEMPLATE.md`; on "wrap up", update `docs/STATUS.md` in
  under 15 lines. **`docs/STATUS.md` does not currently exist.**
- `CLAUDE.md`'s Reporting discipline list (rules 1–9) governs Claude
  Code: "print" means literal text in the reply; no COMPLETE without a
  per-section checklist; running a subset of a brief is a deviation; do
  not make research decisions; headlines reflect the weakest evidence;
  state what a finding would invalidate; no unrequested persistent state
  (including memory writes); refer to prior work by file path and date;
  commit all new/changed files under `src/` and `docs/` at task end.
- The journal is maintained by the research lead only. Claude Code must
  not edit `docs/JOURNAL.md`.

---

## 9. Discrepancies and gaps found while writing this handoff

Flagged rather than resolved.

1. **The journal stops before the rebuild.** `docs/JOURNAL.md`'s last
   entry is Task 16b (2026-09-26). **Tasks 15, 17, 18, 19, 19c, 19d and
   21 have no journal entries**, although they include the entire engine
   v2 rebuild and its validation. The results pages are the only record.
   This should be backfilled.
2. **D-005's stated reason is partly wrong and was never corrected in
   the record.** It drops PFF citing an unresolved licence. It was later
   established that (a) downloading via the signup form is clearly
   permitted use, (b) redistribution was never required because D-006
   ships code not raw data, and (c) the substantive reason to drop
   Pillar 2 is the 57.2% ESTIMATED positions plus prior art. Neither
   DECISIONS.md nor the journal records this correction.
3. **No decision entries exist for engine v2's key choices.** The
   offside rule R4, the policy restriction and temperature calibration,
   and the possession-state feature attempt live only in briefs and
   results pages. There is no D-016 or later.
4. **`docs/ROADMAP.md` is stale.** Its "revised roadmap" is dated
   2026-09-20 and schedules Go/No-Go 2 for Sep 26 and submission for
   Sep 30, none of which survived the rebuild.
5. **`docs/STATUS.md` does not exist** despite being required by
   `CLAUDE.md`'s standing routines.
6. **D-001 says the repo goes public Sep 28.** It has not.
7. **Task 21's Step 3 table was generated by an uncommitted one-off
   script** (disclosed in that results page, Section 4), so that table is
   not reproducible from committed code.
8. Engine v1 leaderboard numbers appear in both `12-artifacts.md` and
   `14b-leaderboards-referee2.md`; the `12` figures predate the
   objective comparison. Both are withdrawn under D-015 and neither
   should be cited.

---

## 10. The honest summary

The process worked: preregistration, gates, cross-fitting,
coverage-tested intervals and stricter checks repeatedly caught real
errors, including several of the research lead's own. But for thirteen
tasks it audited *conclusions* drawn from an instrument nobody had
audited. **Preregistration disciplines inference, not measurement.**

The engine was rebuilt and is much better than v1 — destinations are the
pass that was actually played, expected value is no longer a proxy for
safety (Spearman 0.664 against near-1.0 before), the value model
responds to defensive context, and outcome validation reverses from
strongly negative to positive and survives cross-fitting. But it fails
one of its own acceptance scenarios, and the reason is a genuine
representational limit: the value model knows where the ball is, not who
has it.

With the abstract deadline at Oct 1 and no accepted player-level result,
the realistic options are (a) submit on what is defensible — the audit,
the tempo module, the measurement results — or (b) miss SSAC27 and build
the thing properly for a later venue. That decision belongs to the
author, and the new chat should put it to him early rather than assume.
