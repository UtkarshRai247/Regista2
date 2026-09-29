# Regista 2 — Chat Handoff (v2)

Written 2026-09-28 (evening, Pacific) by the outgoing research lead, after Task 48.
This document is authoritative for project state. Where it conflicts with an older results page, benchmark file, abstract draft or the previous handoff, the conflict is flagged explicitly (section 4C) rather than silently resolved.

The previous handoff (written before this chat; it covers Tasks 00–21 in more detail) is preserved in git history at commit 16b8bcf (docs/CHAT-HANDOFF.md as first committed). This file replaces it.

## 0. How this was written, and what was and was not read in full

Read in full for this handoff:
- docs/JOURNAL.md (all 991 lines in the working copy, including an uncommitted 132-line block; see 4C)
- docs/DECISIONS.md
- docs/ROADMAP.md
- docs/DATA_LICENSES.md
- docs/specs/analysis-plan-pillar4.md and its two amendments
- the previous docs/CHAT-HANDOFF.md
- docs/results/48-confirmation-reserved.md

Read in full earlier in this chat, and summarised from those readings:
- docs/ENGINE_AUDIT.md
- docs/specs/engine-v2-rebuild.md
- docs/results/19d, 21 through 47
- every brief from Task 22 through Task 48

NOT re-read line by line for this handoff: results pages 00–19c, briefs 00–21, analysis-plan-v2.md, analysis-plan-v3.md and analysis-plan-tempo.md. For those, the numbers below come from the journal and the previous handoff, which were cross-checked against each other and agree. Where an exact figure from a page I did not re-open matters, the page is named in section 6. Treat any figure marked "(from chat summary)" as needing a check against its results page before it goes into the abstract.

---

## 1. Project identity

**What it is.** Regista 2 is a solo research project by Utkarsh Rai (University of Washington, CS undergraduate; GitHub UtkarshRai247). It tries to measure what separates elite deep-lying creative midfielders ("registas") from each other, using only free public soccer data. The football question: can the "eye test" that scouts and fans use to rank players like Kroos, Verratti, Busquets, Pedri, Rodri and Frenkie de Jong be quantified well enough to compare them? The author wants the project centred on comparing players, not on transfer-market value, and has worried about it becoming too technical to be popular.

**External target.** MIT Sloan Sports Analytics Conference 2026 (SSAC26), Research Papers Competition.
- Abstract deadline: **Oct 1 2026, 11:59pm ET** (8:59pm Pacific).
- Full paper, if selected: **Dec 4 2026**.
- Requirements (checked online in this chat):
  - the abstract is under 500 words, with up to two tables or figures;
  - it must report actual, not promised, results;
  - an open-source GitHub repository is required;
  - entries are judged on novelty, academic rigour and impact.
- The repo is **still private**. D-001 said public on Sep 28; that has not happened.
- **The author's standing positions, stated repeatedly in this chat:**
  - He will NOT submit a methods-oriented abstract.
  - He will NOT submit a tempo-led abstract.
  - He will NOT skip SSAC26.
  - He wants the models improved first and the abstract written after.
  - He objects to rules where one failed test ends a line of work, and has asked the research lead to be less pessimistic.
  - He agreed the repo goes public (usage-rights questions to be handled at publication time).

**Why it exists: the Regista 1 critique.** Regista 1 ("the Architect Framework") built six metrics for deep-lying playmakers on StatsBomb open data, with Granit Xhaka as its case study. A systematic review found flaws serious enough to require a rebuild:
1. **Circular validation.** It separated known registas from non-registas, using labels that came from the intuitions being tested.
2. **Style mixed with quality.** The composite "Architect Score" added z-scores of "what he does" to "how well he does it", with arbitrary equal weights and no units. Xhaka ranked 9th of 22 on a framework partly built around him.
3. **A positional value proxy.** "Decision Surplus" valued options by pitch location, which undervalues deep zones: exactly where registas play.
4. **Off-policy extrapolation.** The pass-success model was trained only on chosen passes (AUC 0.935), which says nothing about options nobody chose.
5. **Wrong baseline.** Surplus was measured against the best option (regret), not against what a typical player chooses.
6. **Attention treated as attribution.** Transformer attention weights were used for credit assignment.
7. **Player and system unidentifiable.** One team-season (Leverkusen 2023/24) cannot separate player from coach.
8. **No uncertainty.** Split-half reliability was r = 0.47 (p = 0.24) on 8 players.

**The five pillars** (the planned response):
1. **Decision engine:** a learned value function, full action space, behaviour-policy baseline, decomposed into Decision / Execution / Risk. Answers flaws 3–5.
2. **Visibility calibration** of freeze frames against full tracking data. Answers the partial-visibility weakness of StatsBomb 360.
3. **A hierarchical model** separating player from team context, with uncertainty intervals. Answers flaws 7–8.
4. **Outcome and market grounding.** Does the measure relate to real results (and market value)? Answers flaw 1.
5. **Unsupervised role discovery.** Answers flaw 2.

---

## 2. Full status by pillar and module, with real numbers

Plain terms used below:
- **Reliability:** how consistently a measure ranks the same player on two halves of his data (1.0 = perfect).
- **P-test:** the pass-level out-of-match test (Task 35). It compares a player's passes with his teammates' passes in the same game, using his score from his OTHER matches.
- **Holm:** a correction for running several tests at once.
- **MDE:** minimum detectable effect, the smallest effect the test had 80% power to see.

### Pillar 1 — Decision engine: ACCEPTED (engine v5); the valid results test is positive and replicated, but concentrated in forwards

**Engine v1 (Task 01).** Withdrawn by D-015 after docs/ENGINE_AUDIT.md found five defects:
1. EV was algebraically a risk score.
2. The value model could not see defenders.
3. Execution was a completion residual.
4. The scored destination was not the pass played (median 5.05 yd off; 35.1 yd on 50+ yd passes).
5. Several coordinate, lane and offside defects.

Historic v1 numbers, all withdrawn:
- Decision reliability 0.744 [0.691, 0.792] at ≥200 passes; Execution 0.482.
- Pass-success AUC 0.867; value AUC 0.799 in-sample, 0.743 out-of-fold.
- v1 outcome test: team xG −0.138 per SD (p = 0.0002).

**Engine v2 (Tasks 15–19d).** A 4-yard destination grid (~423 candidates per pass, 106,141,669 rows). The chosen option is the grid cell containing pass_end_location. Two value models: P(team scores within 10 actions) and P(opponent scores within 10 actions). A calibrated softmax policy baseline.
- It failed T4 scenario_c from Task 19d.
- Task 21 (possession-state features) stopped at its premise check.
- History, including T1–T6 per task: previous handoff, section 2.

**Task 22 (possession perspective).** Two real code defects were fixed and kept:
- **Fix A:** value rows now come only from the team in possession. About 13.5% of events were by the non-possessing team (checked on one match), mostly Pressure.
- **Fix B:** the scoring label now counts its own event. Previously a scoring shot was labelled 0.

The premise check still failed: ball behind the line looked less dangerous in bands 80–100 and 100–120. The research lead's check was crude, confounded by the ball's width position (wide byline states).

**Task 23 (diagnostics, no change).** Rule R3 fired: in the central channel, band 100–120, behind the line scored 2.6% vs 10.0% not behind. The synthetic scenario_c frame has no goalkeeper and only 6 players; frames with ≤6 visible players are under 1% of training data.

**Task 24 — ROOT CAUSE (the biggest single error in the project).** StatsBomb event AND 360 frame coordinates are already team-relative: every team attacks toward x = 120. geometry.team_period_directions assumed pitch-fixed coordinates and rotated the lower-mean-shot-x team 180° in almost every period. Evidence:
- 156/156 team-periods had mean shot x > 60 (first 40 matches).
- The opponent keeper sat at median x = 117.4, with 99.9% beyond x = 100.
- 80 of 156 team-periods got +1 and 76 got −1.
- Confirmed on all 299 matches.

About half of all events had been valued with the attack reversed since engine v1. The same function also fed src/tempo/redesign_metrics.py.

After the fix:
- G1 (own-third "beyond line" share) fell from 14.8% to 2.30%.
- G2 passed: P(score) rises toward goal.
- Behind the line now scores MORE than not-behind in every band.
- The 1% G1 bar was the research lead's error (it ignored visibility). Task 25 attributed the residual to off-camera players.

**Engine v5 (Task 25) = the accepted engine.** Direction fix + Fixes A and B + Task 21 features removed.

| Test | Bar | v5 |
|---|---|---|
| T1 snap displacement | ≤ 2 u | 1.6125 |
| T2 defence response | material; sign reported | +0.01272 (positive) |
| T3 Spearman(EV, p_success) | < 0.90 | −0.2396 |
| T4a unmarked vs marked | unmarked higher | 0.01853 vs −0.00883 |
| T4b open vs cluster | open higher | 0.00536 vs −0.04014 |
| T4c through ball | ≥ corpus p90 | 0.02378 vs 0.01169 |
| T5 calibration | ≤ 5 pp | 2.18 pp |
| T6 reliability @200 | ≥ 0.60 | 0.8191 |

Other v5 facts:
- Cross-fit out-of-fold AUCs: pass success 0.9116, M_for 0.8745, M_against 0.7222.
- Policy top-1 accuracy 8.07%, top-3 21.39%.
- Offside: Task 19c's calibration procedure re-run on corrected data selected **R1_K10** (≥10 visible opponents, no tolerance, no half restriction). FP 2.91%, recall 37.72%; the naive rule had FP 11.84%, recall 91.77%.
- Softmax temperature 0.1562.
- Execution is not computed: a known cross-team defect in decision_execution_risk.py.
- The engine uses **292 matches, not 299.** Seven matches (3837706, 3877115, 3877170, 3877194, 3895158, 3895266, 3895309) have frames whose event IDs do not match their event file (results/32, section 3).

**Same-match outcome validation (cross-fitted, 583 team-matches, Task 25)**, coefficient per SD of team Decision (p):

| Outcome | H-O1 | H-O2 | PH-O1 | PH-O2 | PH-O4 |
|---|---|---|---|---|---|
| xG | +0.2486 (2.4e-10) | +0.0917 (0.069) | +0.2404 (1.1e-7) | +0.2683 (2.5e-5) | +0.2753 (6.2e-9) |
| Goals | +0.2147 (2.3e-4) | +0.2641 (3.9e-4) | +0.2412 (8.4e-6) | +0.2758 (2.1e-5) | +0.2416 (1.6e-4) |

(H-O1 is the basic model; H-O2 adds completion, progressive passes and xA; PH-O1/PH-O2/PH-O4 are the post-hoc variants, with PH-O2 adding team-context fixed effects.)

Holdout (Task 26: 126 women's matches, 250 team-matches, frozen engine): xG H-O1 +0.2611 (6.7e-6), H-O2 +0.0664 (0.326), PH-O1 +0.1764 (0.037), PH-O4 +0.3762 (5.6e-7); goals H-O1 +0.3358 (1.3e-6), H-O2 +0.2797 (2.1e-4), PH-O1 +0.3702 (3.0e-7), PH-O4 +0.4652 (5.7e-11). PH-O2 was not computable.

**BUT Task 32 showed these same-match links are largely mechanical.** Decision and xG are measured in the same match, so a pass into the box both scores well and precedes the shot. In the out-of-match LINEUP test, the players' other-match Decision gave xG +0.08 (p = 0.17), and within team (PH-O2) about −0.11 (from chat summary). The holdout test above is same-match too, so it shares this weakness.

**Task 35 — the valid test.** Team-match out-of-match tests had MDEs of 0.12–0.52 xG per match per SD, against a between-team SD of about 0.65: nearly blind. The P-test (designed after those failures, disclosed; includes a positive control):

| Measure (study, all passers) | n passes / players | coef per 100 passes per SD | 95% CI | p (Holm) |
|---|---|---|---|---|
| Positive control: completion (pp) | 168,855 / 440 | +2.201 | [1.798, 2.604] | 9.5e-27 |
| **v5 Decision** | 168,855 / 440 | **+0.0747** | [0.0269, 0.1224] | 0.0022 (0.0087) |
| v6 Decision (Task 33) | 153,279 / 402 | +0.0468 | [0.0163, 0.0773] | 0.0027 (0.0087) |
| v5 ev_chosen (raw) | 168,855 / 440 | +0.0589 | [−0.0013, 0.1191] | 0.055 (0.11) |
| Reception RQ_rel (per 100 receptions) | 166,087 / 446 | +0.0238 | [−0.0410, 0.0887] | 0.47 |

**Task 37 — holdout confirmation of the P-test (final holdout use; holdout now SPENT):**
- v5 Decision **+0.0780** [0.0237, 0.1322], p = 0.0048, on 58,000 passes / 227 players.
- Control +2.814 pp (p = 1.3e-18).
- Deep midfielders +0.0075, p = 0.81 (44 players).

**Task 41 — vetting of the P-test** (from chat summary; see results/41):
- It survives controls for the player's usual starting x, y and mean ev_chosen, and exact position-label fixed effects. It is slightly stronger with location controls.
- It survives excluding the passer's own shots, 5- and 15-event horizons, and two-way clustering.
- **Split by role, only forwards show it** (21 players, about +0.61 per 100 per SD). CB p ≈ 0.08. FB, DM, CM and AM/W are null.
- So the replicated Decision result is currently a forwards result, not a regista result.

**Engine v6 variant (Task 33)**, kept as a variant, not a replacement:
- Fix A3: incomplete passes are retargeted to the intended teammate (within 15° of the line and 10 u of the end), else excluded.
- Fix A2: the baseline becomes f(state), "the EV a player typically achieves from this situation", cross-fitted.
- Out-of-match LINEUP gate: xG −0.08 (p = 0.25), FAIL.
- The situation part f(state) out-of-match: H-O1 +0.30 (p = 1.5e-7) but PH-O2 −0.06 (p = 0.72). That is team strength, not player skill.
- The deep-midfield table shows none above or below the mean; Spearman vs v5 is 0.43.
- The research lead's sanity check wrongly required zero means by pass length and outcome, which are part of the choice.

**Other Decision diagnostics (Task 32, from chat summary):**
- 535 of 537 players have positive mean Decision, so the typical-choice baseline is biased low.
- Incomplete passes contribute about 40% of between-player variance (execution leaking into choice).
- Role explains 64% of between-player variance.
- Within-role reliability: about 0.45 for DMs and 0.46 for CBs, against 0.82 overall.
- In-sample (same-match) raw ev_chosen beat Decision. The P-test reversed that.
- Cross-fitted player tables barely differ from in-sample tables.

### Pillar 2 — Visibility calibration: ABANDONED

1. Prior art (Graph Imputer, Omidshafiei et al. 2022; Everett et al. arXiv 2311.14642; a 2026 arXiv training-free imputation paper).
2. PFF's tracking is not ground truth: 57.2% of player positions are ESTIMATED (sample match; about 62% across all 64 matches in Task 36).

PFF data was later used for other purposes (Tasks 36–38, 42–43, 46), which contradicts D-005 (see 4C).

### Pillar 3 — Player vs system: DONE for Decision (with a serious caveat); DONE for press resistance at all-player level

**Study B on engine v1** (withdrawn): S = 0.654 [0.566, 0.755]; Tier 1 allowed, Tier 2 not.
- The interval-method saga (cluster bootstrap covered the truth in 10/100 simulations; parametric and profile 93%) is in the previous handoff and results/10.

**Study B on engine v5** (Task 26):
- S = 0.7939 [0.7086, 0.8866] (parametric bootstrap).
- PH-B1 (position fixed effects) 0.7683 [0.6793, 0.8774].
- PH-B3 0.8589 [0.7545, 0.9474].
- PH-B2 mover correlation (disattenuated) 0.6234 [0.2586, 1.0]. **Tier 2 ALLOWED** under the pre-registered rule.

**Task 27 sensitivity:** after residualising unit means on zone and pressure shares, PH-B2 = 0.2716 [−0.1372, 0.6626]. Part of "travels" is role persisting. Report the Tier 2 verdict only together with this.

**Press resistance (Task 46, study sample):**
- Variance split S = 0.740 [0.635, 0.867] for all players. For deep midfielders S = 0.405 [0.000, 1.000] (uninformative).
- Club vs country movers: r_true 0.924 [0.735, 1.000] on only 24 movers; the DM version is unmeasurable (4 movers).
- 2015/16 club vs national team 5–8 years later: 0.740 [0.579, 0.888] (91 players); DMs capped 1.0 [0.786, 1.0] (12 players).
- **Confirmed on the reserved data (Task 48 C4):** r_true **+0.650 [0.500, 0.797]**, 127 movers, Holm p < 0.002.

### Pillar 4 — Outcome and market grounding

**Market (closed):**
- Decision −0.285, p = 0.733, CI [−1.925, 1.355]; −2.40% value per SD. n = 125 units / 96 players, R² 0.588.
- H3 −0.775, p = 0.111.
- MDE ≈ 2.35 log points (≈22% value per SD): underpowered by about 2×.
- Two of six robustness variants were significantly negative (p = 0.043, 0.033); none positive.
- Pivot: D-012.

**Outcome:** see Pillar 1. Current state:
- (a) v1 was negative.
- (b) v5 same-match is positive but largely mechanical.
- (c) The pass-level out-of-match P-test is positive and replicated on the holdout, carried by forwards.
- (d) Press resistance predicts reaching the final third (confirmed; see the press resistance module below).
- (e) Team-match out-of-match tests are underpowered. Do not describe their nulls as "no effect".

**Referees 1 and 2, win probability (Tasks 13–14b, on engine v1):**
- No objective won Referee 1.
- Referee 2 was underpowered (23 of 77 expert-selected players matched; MDE 0.267 AUC).
- The strength-conditioned win-probability model is validated (Brier 0.0893 vs 0.1093) and reusable, but unused since the rebuild.

### Pillar 5 — Role discovery: CUT (D-002), never started

### Study A (sport-wide blind spots) and Study C (choice vs execution): WITHDRAWN with engine v1

Study A's best v1 survivor (middle third, not under pressure, lateral_medium, level/trailing) was never re-run on v5. Details: journal and results 05–09b.

### Module — Tempo: USABLE as a style measure; no confirmed link to results

- Tasks 16/16b: median_time_on_ball 0.939 and one_touch_share 0.959 USABLE; pressure_delta 0.595 provisional (a restatement of hold time, r −0.858); pace_delta and tempo_variation not measurable. The Task 16b redesign gave MOVE_ON_SPEED 0.783 and HOLD_VARIATION 0.881.
- Re-run on corrected coordinates (Task 26): about 0.77 and 0.88.
- Task 39 P-test (study): MOVE_ON_SPEED −0.0076 (p 0.548, Holm 0.601); HOLD_VARIATION +0.0154 (p 0.30). Within DMs, MOVE +0.0587 [0.0063, 0.1111], p 0.028, Holm 0.056. Task 39's brief was found uncommitted and not written in the main chat; it was adopted with claim rules (commit 9b2e49f).
- Task 44 (2015/16), within DMs:
  - stability: MOVE 0.475 (FAIL), HOLD 0.730 (PASS);
  - P1 (MOVE → net xG) +0.0096, p = 0.27, not confirmed;
  - secondary: MOVE → reaching the final third across all players −0.325 (p = 3e-5); HOLD within DMs → net xG −0.034 (p = 0.0019) and → final third +0.401 (p = 0.0026). All secondary.

### Module — Reception quality (Task 34): stable trait, no demonstrated results link

- RQ = space to the nearest visible opponent at reception, context-adjusted. RQ_rel is the same relative to teammates.
- R1 (stability) passed, but largely through role.
- Within DMs, the club–country mover correlation was about 0.25, with a CI touching zero (from chat summary).
- R3 (out-of-match results) failed; PH-O2 was the wrong sign.
- Busquets, Verratti and Vitinha receive in LESS space than teammates; Kroos is near the top.
- Task 35 DM P-test: RQ_rel +0.0555 [0.0158, 0.0952], p 0.0062, Holm 0.0248. It did not survive the 12-test within-DM family correction in Task 41.
- Exact numbers: results/34.

### Module — Availability, "always free" (Task 38, PFF WC2022): stable, NEGATIVELY linked to chances; not confirmed

- AVAILABLE = 5–40 m from the ball, nearest opponent ≥3 m, passing lane ≥2 m. The baseline deliberately excludes the player's own location.
- 584,874 moments / 639 players; base rate 0.334.
- Stability: DMs 0.740 [0.647, 0.814] (n = 28); all 0.620 (n = 183).
- P-test: all −0.0692 [−0.1146, −0.0238], p = 0.0028; DMs −0.1749, p = 0.0515.
- Q = 277.94 on 58 df; 12 above / 14 below the mean (Busquets, de Jong and Bellingham below).
- AV vs RQ_rel +0.361.
- AV_vis (camera-visible only) agrees on every test.
- Negative at all 9 threshold combinations (Task 41).
- Progressive availability (AV_prog, Task 42 Step 3): see results/42.
- Interpretation risk: "available" may mean "standing somewhere safe".

### Module — Press resistance (Tasks 42–48): the strongest player-level line, partly confirmed

Definitions:
- **PR_keep (Task 42):** judged the first action after a pressured reception. Weak, because 84% of first actions are carries.
- **PR2 (Task 43):** judged how the receiver's spell ends (his completed pass vs a loss), context-adjusted.
- **PR2_flag (Task 44):** event-only; pressure from StatsBomb's under_pressure flag. It correlates r = 0.840 [0.784, 0.881] with the frame-based PR2 (n = 148).

Results by task:
- **Task 42 (study):** PR_keep → reaching the final third, all players, p = 0.0014. The pre-existing praised list scored higher, T = +0.69, p = 0.014 (direction declared in advance). Stability was untestable (7 player-seasons).
- **Task 43 (study):**
  - PR2 stability: DM 0.39, all 0.54 (from chat summary); no results link.
  - Praised list p ≈ 0.07; nothing survives across all 7 praised-list tests.
  - PFF vs StatsBomb press resistance: r = 0.778 [0.648, 0.864], n = 55.
  - The DM retention control failed (20 players).
- **Task 44 (2015/16 big five, 1,551 matches, event only, definitions fixed before download):**
  - DM stability 0.666 [0.610, 0.714] (n = 185) PASS; PR2_flag_fwd 0.587 FAIL.
  - Q = 703.6 on 184 df; 27 above / 35 below.
  - Praised list (5 players present: Kroos, Modrić, Verratti, Busquets, De Bruyne) T = +1.444, p = 0.0011, Holm(4) 0.0044.
  - P2 (DM → final third) +0.775 pp [−0.013, 1.562], p = 0.054, Holm 0.108: not confirmed.
  - Secondary, all players: → final third +1.835 pp, p = 1.7e-27; → net xG −0.046, p = 7e-5.
  - Top of the DM table: Thiago Motta, Jorginho, Marchisio, Busquets, Kroos (then De Rossi, Moutinho, Cazorla, Biglia). Bottom: Nzonzi, Krychowiak, Kouyaté and similar.
- **Task 45 (2015/16 second use): the team-style test FAILED.**
  - A1 (team×season demeaned): DM stability 0.487; praised list T = +0.274, p = 0.54.
  - A2 (plus unpressured passing style): 0.518, T = −0.514.
  - Team fixed effects are only 0.85% of unit variance. Spearman vs unadjusted: A1 0.773, A2 0.490.
  - Unadjusted PR correlates +0.573 with unpressured completion rate.
  - Under pressure the top-20 DMs pass backward 37.4% vs 31.8% for the bottom 20, and forward 32.6% vs 40.5%: they recycle, as the author predicted.
  - A1 still predicts reaching the final third: DMs +0.64, p = 0.041; all +1.60, p = 1.4e-27.
  - Per the fixed rule, the DM result was described as "possibly team style".
  - Interpretation (research lead, recorded before Task 46): with one season, team demeaning compares Busquets with Iniesta and Xavi; it cannot separate team style from good players clustering. Movers are the proper test.
- **Task 46 (movers; spatial vs physical):** movers under Pillar 3 above; spatial vs physical under the next module.
- **Task 48 (reserved data, single use, 1,985 matches, 64 competition-seasons, 1,184 of them women's):**

| Test | Result | Verdict |
|---|---|---|
| C1 DM PR2_flag_keep → final third | +0.572 [−0.502, 1.645], p 0.297, Holm 0.567 | not confirmed |
| C2 DM willingness W → final third | −0.310, p 0.284 | not confirmed |
| C3 deterrence (all) | −0.00241 [−0.00512, +0.00029], p 0.080, Holm 0.241; placebo +0.00030, p 0.062 | not confirmed |
| **C4 travels club ↔ country (all)** | **r_true +0.650 [0.500, 0.797], 127 movers** | **CONFIRMED** |
| **C6 team-adjusted PR → final third (all)** | **+1.281 pp [0.988, 1.573], p 9.2e-18, Holm 3.7e-17; control +8.586 pp** | **CONFIRMED** |

  Report-only on the reserved data:
  - DM stability of PR2_flag_keep 0.696 (n = 182); W 0.781.
  - Praised list on PR2_flag_keep (unadjusted): T = +1.581, p = 1e-4, 8 players present, all with positive z (De Bruyne +1.94, Xhaka +2.26, Busquets +1.20, Modrić +0.95, Kroos +1.23, Kimmich +1.77, Rodri +1.97, de Jong +1.33). This is report-only and unadjusted for team.
  - C1 with net xG: −0.0825, p = 0.022.

### Module — Spatial vs physical press resistance (the author's idea; Task 46): exploratory, cannot be confirmed with event-only data

Measures:
- **Physical willingness (W):** how often a player takes the ball while pressed, context-adjusted.
- **Physical success:** PR2_flag_keep.
- **Spatial S1:** RQ_rel (360).
- **Spatial S2:** PFF availability when the passer is pressed (AV_out).

Results:
- W stability: DM 0.802, all 0.924 (2015/16).
- Spatial vs willingness (study, all): r = −0.754 [−0.788, −0.714]; 1 player in the top quartile of both vs 33.4 expected, p = 1.3e-18.
- Deep midfielders: RQ_rel vs W −0.473 [−0.614, −0.303] (n = 98); PFF AV_out vs W −0.336 [−0.602, −0.003] (n = 35).
- Spatial vs success is POSITIVE: all players +0.507.
- Results links: W → final third, all −1.48, p = 1e-28. Within DMs, W +0.333 (p = 0.037) and jointly W +0.368 (p = 0.018) with PR +0.533 (p = 0.0017).
- Task 48 C2 did not confirm the DM W link.

### Module — Pressure deterrence ("opponents stop pressing him"; the author's idea; Task 47): exploratory, NOT confirmed

2015/16:
- First-half escape success E1 → change in pressure on him: −0.00371 per SD [−0.00640, −0.00103], p = 0.0068 (11,491 player-matches / 1,577 players).
- Placebo (pressure on his teammates) +0.00055, p = 0.0007. Not negative, so the rule passed; it fits pressure being shifted onto teammates.
- Concentrated in minutes 46–67 (−0.00529, p = 0.0024).
- DMs +0.00503, p = 0.31.
- Season level: press-resistant players are pressed less in every role (pooled within-role r = −0.316).

Reserved (C3): p = 0.080, **not confirmed**.

---

## 3. Every methodology decision, and the walk-backs

Formal decisions D-001 to D-016 are in docs/DECISIONS.md (not restated; D-016 was written by Claude Code in Task 38 on instruction). **No D-017 or later exists**, although many decisions have been taken since D-015 (see 4C, item 3).

Walk-backs 1–10 are from before this chat. Full text: previous handoff section 4 (commit 16b8bcf) and the journal.
1. D-009 → D-012: the market headline was abandoned (underpowered; project drift caught by the author).
2. D-011 (angle-matching) → reversed by D-015. It conflated the action with the outcome and caused engine defect 4.
3. Amendment v2-2: Gate D replaced (it would have compared each candidate with itself).
4. Amendment v2-5.1 bootstrap bug: Study B Tier 1 was flipped twice by method corrections, never by changing a rule.
5. Amendment v2-8.2's compositional explanation of v1's negative outcome link was refuted.
6. Amendment v2-9.1: possession share was controlled as a confounder when it was plausibly a mediator (research lead's error).
7. Amendment v3-2.2's sample-composition diagnosis was refuted by the 2,090-match corpus.
8. Task 19's "offside is undetectable" was a sort-index bug (Task 19c).
9. Task 15's T4 pass was invalid (corrupted defensive line; Task 19d).
10. Task 21's fix was stopped by its own premise check.

Walk-backs and decisions from this chat (Tasks 22–48):

11. **Deadline strategy.**
    - The research lead recommended submitting a defensible methods abstract; the author declined.
    - A tempo-led abstract was declined.
    - The research lead then declared engine work stopped for Oct 1 under rule R3 (Task 23); the author overrode this.
    - The subsequent search found the Task 24 root cause.
    - Lesson recorded: the research lead's stop rules conflated "stop claiming" with "stop investigating". From then on, guardrails replaced stop rules:
      - tests are never rewritten to pass;
      - holdouts are used once, on pre-declared gates;
      - everything is disclosed.
12. **Task 22's premise check was crude** (confounded by lateral position); the research lead's design error.
13. **Task 24's direction bug:** the single largest error. It existed since engine v1 and in tempo. It was found only after the author refused to stop.
14. **Task 25's G1 bar (1%)** ignored visibility; the residual 2.30% was attributed to visibility by a pre-specified check.
15. **Task 26's deep-midfield group was wrong** (anyone ever listed at DM, which included De Bruyne, Müller and Foden). Task 27 set it to ≥50% of eligible passes at DM positions: 111 players.
16. **Shrinkage errors, all the research lead's:**
    - Task 26 used uniform shrinkage.
    - Task 27's match-clustered variance collapses to zero with one match.
    - Task 28's pooled noise and unweighted method-of-moments gave tau² = 0 within DMs.
    - Task 29 used within-group noise with DerSimonian–Laird (Q = 140.53 on 110 df, p = 0.0263; Vitinha and Busquets above the mean; independent match-split reliability 0.1846, n = 16). The "exactly one check passes" rule then allowed naming only those two.
    - Disclosure: the Task 29 brief named Busquets and Vitinha as examples of high-volume players before results existed.
    - Under v6 (Task 33) no DM separates.
17. **The abstract draft** (docs/abstract/SSAC26-abstract-draft.md) was written after Task 29 and parked at the author's request ("too soon"). It is now STALE and must not be used: it says 299 matches and headlines the mechanical same-match link.
18. **Task 32:** the same-match outcome link is mostly mechanical; the typical-choice baseline is biased; execution leaks into Decision; role dominates.
19. **Task 33:** the pre-declared fixes A2/A3 fail the out-of-match gate. The sanity-check spec was wrong.
20. **Tasks 32–34's out-of-match nulls were over-read** by the research lead as "no skill". Task 35's power check showed those tests were nearly blind. Corrected in the record.
21. **The P-test was designed after failures** (disclosed), with a positive control. It was replicated on the holdout (Task 37), which is now spent.
22. **Task 38's brief error:** pressure "not null" is always true. Corrected before the run (d552381): pressureType != 'N'. Recorded as D-016.
23. **"Elite registas take the ball in traffic"** was built on examples picked after seeing the tables. Task 41's test on the pre-existing praised list (plan v3 section 5: Kroos, Modrić, Verratti, Busquets, De Bruyne, Xhaka, de Jong, Kimmich, Rodri, Pedri, Gündoğan, Grillitsch, Shaparenko) found no difference on availability, availability-visible, reception space or Decision. Claim withdrawn.
24. **Task 41:** no within-DM result survives one Holm correction across the 12-test family.
25. **Task 42's claim rule required a positive control** that did not exist for reception units. Corrected with a retention control (4d6405a). Claude Code's first run used the old control and was re-run; the superseded pages are c8ec94d/3d97f4e.
26. **Task 42's PR_keep definition was weak** (first action = carry 84% of the time); the research lead's brief. Task 43 redefined it and was disclosed as a second attempt; the lead faded.
27. **Task 44 corrections before running:**
    - read the local ZIP (f89863f);
    - eligible pass defined without frames (dff3e4e);
    - event-only situation control g (8f6ff58).
28. **Task 45 amended before running at the author's request:**
    - style controls taken only from unpressured passes, and the claim wording no longer treats a style-adjustment failure as "no skill" (ca9362f);
    - a per-role Step 6 added (51c29d1).
29. **Task 45's team demeaning in one season over-controls;** replaced as the decisive test by movers (Task 46), which were then confirmed on the reserved data (Task 48 C4).
30. **Task 48's reserved data composition was described inaccurately** to the author before running ("La Liga Barcelona matches, Premier League 2003/04, Copa América…"). In fact 1,184 of 1,985 matches are women's club and international football. The brief did not restrict gender, and D-007's men's-only rule was not applied. Correction commit e55d830.
31. **Benchmarks:** v5 (docs/BENCHMARK-v5.md, tag benchmark-v5), v6 (docs/BENCHMARK-v6.md, tag benchmark-v6, Task 35 per-pass inputs added to the snapshot) and v7 (docs/BENCHMARK-v7.md, written but NOT frozen or tagged).
32. **Distributed compute (Mac + HP Pavilion):** reviewed and deliberately parked (see section 5).
33. **The author asked for PFF to be used without resolving licensing now** ("worry at repo time"). Accepted for internal work; it contradicts D-005 until a new decision is recorded.

---

## 4. Known limitations and open risks

### 4A. Measurement and design
1. **Holdout and reserved data are both SPENT.** No untouched StatsBomb open data is known to remain. Anything new before Oct 1 cannot be externally confirmed.
2. The confirmed Decision skill (P-test) is **carried by 21 forwards** in the study sample. Nothing about deep midfielders is confirmed for Decision.
3. The same-match outcome tests (Tasks 25, 26) are **partly mechanical**. Never present them as "better decisions cause more goals".
4. The typical-choice baseline is biased (535/537 players positive), so "better than the typical choice" is not literally true; only differences between players are.
5. Decision still scores where the ball ended, not where it was aimed (v5). Execution is not computed.
6. Freeze frames show only visible players and carry no identities (except the actor). Offside is recall-limited (37.72%).
7. **Press resistance claims** (confirmed: travels club↔country; team-adjusted version predicts reaching the final third):
   - (a) its link with net xG is NEGATIVE in 2015/16 (p = 7e-5) and within DMs on the reserved data (p = 0.022). A reviewer will ask why keeping the ball goes with fewer chances;
   - (b) within-DM results links are not confirmed;
   - (c) the praised-list edge is unadjusted and disappears under single-season team demeaning;
   - (d) event-only "pressure" is StatsBomb's under_pressure flag;
   - (e) its novelty relative to existing public "press resistance" work has NOT been literature-checked.
8. **Availability:** measured in WC2022 only (64 matches). It is not location-adjusted, so it may partly be "standing somewhere safe".
9. **The spatial-vs-physical trade-off** cannot be confirmed with event-only data.
10. **Tempo:** a style measure, no confirmed results link. MOVE_ON_SPEED attribution is shared with the receiver.
11. **Sample structure:** study club data is four focal teams (PSG, Leverkusen, Barcelona, Inter Miami). La Liga in the reserved set is Barcelona matches only. The Premier League 2003/04 is Arsenal only.
12. **Many tests have been run.** Family corrections were applied within tasks and, for praised-list and within-DM tests, across tasks. Any abstract claim must state its own correction.

### 4B. Narrative and submission risks
1. **The core Decision metric is not new.** KU Leuven's "Creative Decision Rating" (un-xPass, KDD 2023, StatsBomb 360) defines essentially the same quantity: chosen-option value minus predicted typical choice, from destination-likelihood, reward and success models. From its published summary, it was validated by use cases, not by an out-of-match results test (the full paper was not read).
2. Other close prior work:
   - Power et al., KDD 2017 (risk/reward from tracking);
   - EPV (Fernández, Bornn, Cervone), xT, VAEP, OBV;
   - StatsBomb's commercial "ball receipts in space";
   - SkillCorner pressure-at-reception metrics.

   Novelty must rest on what surrounds the metric (the tests, the replication, player vs team, press resistance travelling, the direction-bug warning), not on the metric.
3. The author's constraint (not methods-oriented, not tempo-led) limits which true results can be the headline. The currently confirmed, player-centred results are:
   - (i) decision quality is an individual skill that shows up in other matches (P-test, replicated), mainly for attackers;
   - (ii) press resistance is a stable player trait that travels between club and country and predicts team progression (confirmed on untouched data).

   Deep-midfielder-specific separation is NOT confirmed by any measure.
4. The repo must be public, with a link, at submission. The Task 30 brief (repo prep) exists but predates PFF use and needs revising.

### 4C. Discrepancies and gaps found while writing this handoff (flagged, not resolved)
1. **The journal is far behind.**
   - Committed entries end at Task 14a.
   - An uncommitted 132-line block (engine audit, Task 16, Task 16b) sits in the working copy.
   - There are no entries for Tasks 12, 13, 14b, 14b-prep, 15, 17–48.
   - The research lead repeatedly promised to update it in this chat and did not.
2. **D-005 ("no PFF-derived number appears in the abstract, paper, or repo")** is contradicted by Tasks 36–38, 42, 43 and 46, which use PFF data. No decision reverses D-005, and its licence rationale was already known to be partly wrong.
3. **D-002 cut the "off-ball availability extension"**, yet Task 38 built it. No decision records the reversal. Nor are the following recorded as decisions:
   - engine v5 acceptance;
   - the R1_K10 offside rule;
   - the P-test becoming the primary results test;
   - holdout use (Tasks 26, 37);
   - 2015/16 and reserved-data use;
   - the DM definition;
   - the shrinkage method.
4. **D-007 is men's-only**; the holdout (Tasks 26, 37) and 1,184 reserved matches are women's. D-007 allowed non-market use but this was never recorded.
5. **Match count:** records and the abstract draft say 299 matches; the engine uses 292 (seven event/frame-ID mismatches).
6. **ROADMAP.md is stale** (last revised Sep 20).
7. **docs/STATUS.md does not exist**, although CLAUDE.md requires it.
8. **DATA_LICENSES.md** does not record:
   - the full PFF download (Task 36, data/raw_pff/);
   - the StatsBomb 2015/16 and reserved downloads (data/raw_1516/open-data-master/, data/raw_reserved/);
   - the women's holdout (data/raw_holdout/).
9. **StatsBomb terms (checked online in this chat):** non-commercial research use, attribution with the logo, and registration at the StatsBomb resource centre is requested. The author has not been confirmed as registered.
10. **Clock alignment:** Task 00 reported a constant +2.0 s PFF↔StatsBomb offset (n = 2 goals). Task 36 found the offset varies by a few seconds per event. That is why Task 38 used PFF's own event snapshots.
11. **The Task 39 brief** was found uncommitted in docs/specs/ and was not written in the main chat. Origin unknown.
12. **AGENTS.md** exists untracked at the repo root (a "Project Guide", origin unknown). It has not been reviewed against CLAUDE.md.
13. **Several briefs were committed together rather than alone** (Tasks 37+38, 46+47, 45 with BENCHMARK-v7); recorded as deviations on the results pages.
14. **BENCHMARK-v6 lists reception quality and tempo "see results page"** rather than numbers. BENCHMARK-v7 was never frozen or tagged.
15. **Figures marked "(from chat summary)"** in section 2 were not re-verified against their results pages for this handoff.

---

## 5. What is running or blocked right now

**Running:** nothing. The last completed task is Task 48 (commits 21dd601, 8578fa3, e55d830; brief 2161d66).

**Not done / blocked:**
- **Abstract:** not written for real. The parked draft is stale.
- **Repo publication:** not done. The Task 30 brief (docs/specs/task-30-repo-public-prep.md) was written before PFF use and never run. It needs revising for PFF, women's data, STATUS.md, and the journal and decisions backlog.
- **Records:** journal backfill, D-017+ decisions, STATUS.md, ROADMAP, DATA_LICENSES (all research-lead or Claude Code jobs; see 4C).
- **Execution** (cross-team defect) is unfixed and unused.
- **Possible remaining work** the author has signalled interest in:
  - making the engine and models better (the engine v7 ideas: choices between visible teammates, choice rank instead of value, only decisive passes, xG-based value labels — never briefed);
  - spatial-vs-physical and deterrence (exploratory);
  - press resistance for all roles.

  Any new result cannot be externally confirmed before Oct 1 (all fresh data is spent).

**Distributed compute (Mac + HP Pavilion):**
- The author brought a design from another Claude session: DISTRIBUTED-COMPUTE.md, benchmark_node.py, dispatch.py, pipeline_interface.py and run_chunk.py (uploaded to the chat; NOT saved in the repo). Pavilion: Windows, i7-1255U, 16 GB; native Python plus OpenSSH Server; static split by benchmarked speed; SSH/rsync.
- The research lead's review:
  - (a) compute is not the bottleneck: cross-fit took 1,474 s (v4) and 1,072 s (v5); a full EV recompute plus cross-fit is about 60–65 min;
  - (b) the design's manifest scores all matches per fold, whereas each fold must score only its own held-out matches (fold file: FOLDS_PATH in crossfit_v4/v5);
  - (c) policy training reads the other folds' matches and must stay on the Mac;
  - (d) cross-platform XGBoost output (Apple ARM vs Intel) must be shown identical on the same matches before trust;
  - (e) the paper's numbers must be reproducible on one machine.
- Parked by agreement. No brief was written, and the Pavilion was never configured.
- Machine facts: MacBook Pro M4, 16 GB. Memory gate = live pressure ≥40% free and ≥3 GB available (macOS memory_pressure); never swap-in-use. Process one match at a time.

**External:**
- The email to fchelp@pff.com (licence and ESTIMATED-flag questions) has no known reply.
- SSAC26 abstract due Oct 1 11:59pm ET.

---

## 6. Pointers (open these rather than relying on this summary)

| Topic | File |
|---|---|
| Previous handoff (Tasks 00–21 detail) | git show 16b8bcf:docs/CHAT-HANDOFF.md |
| Journal (narrative to Task 16b) | docs/JOURNAL.md |
| Decisions D-001…D-016 | docs/DECISIONS.md |
| Engine v1 audit | docs/ENGINE_AUDIT.md |
| Engine v2 design and T1–T7 battery | docs/specs/engine-v2-rebuild.md |
| Preregistrations | docs/specs/analysis-plan-pillar4.md, analysis-plan-v2.md, analysis-plan-v3.md, analysis-plan-tempo.md |
| Benchmarks and critiques | docs/BENCHMARK-v5.md, -v6.md, -v7.md; docs/CRITIQUE-v5.md (incl. CDR addendum), docs/CRITIQUE-v6.md; docs/benchmark/manifest-v5.txt, manifest-v6.txt |
| Possession perspective, defects A/B | docs/results/22-possession-perspective.md |
| scenario_c diagnostics, R3 | docs/results/23-scenario-c-diagnostics.md |
| Direction bug evidence | docs/results/24-direction-fix.md (script task24_evidence.py) |
| Engine v5 battery and outcome tables | docs/results/25-engine-rebuild-v5.md |
| Holdout (same-match), tempo re-run, leaderboard, Study B v5 | docs/results/26-holdout-and-player-results.md |
| DM group, EB shrinkage, PH-B2 residualised | docs/results/27-player-results-hardened.md |
| Variance fix; DM noise, DL, Vitinha/Busquets | docs/results/28-shrinkage-variance-fix.md, 29-deep-midfield-noise.md |
| Critique diagnostics (mechanical link, 292 vs 299, role share) | docs/results/32-critique-diagnostics.md |
| v6 fixes and gate | docs/results/33-fixes-a2-a3.md |
| Reception quality (brief committed 5ac7246 before reading 33) | docs/results/34-reception-quality.md |
| Power and P-test | docs/results/35-power-and-pass-level-test.md |
| PFF ingest and alignment | docs/results/36-pff-ingest.md |
| Holdout P-test (final holdout use) | docs/results/37-holdout-ptest.md |
| Availability | docs/results/38-availability.md |
| Tempo P-test | docs/results/39-tempo-ptest.md |
| Benchmark v6 freeze | docs/results/40-benchmark-v6-freeze.md |
| Vetting round 2 (roles, praised list, thresholds, family) | docs/results/41-vetting-round-2.md |
| Role-appropriate outcomes, PR v1, AV_prog | docs/results/42-improvement-round-2.md |
| PR v2, PFF cross-check | docs/results/43-press-resistance-v2.md |
| 2015/16 confirmation, DM tables | docs/results/44-big-five-1516.md |
| Team and style vetting, per role | docs/results/45-press-resistance-vetting.md |
| Movers, spatial vs physical | docs/results/46-movers-and-spatial-physical.md |
| Deterrence | docs/results/47-pressure-deterrence.md |
| Reserved confirmation (the 64 competition-seasons listed) | docs/results/48-confirmation-reserved.md |
| Stale abstract draft (do not use) | docs/abstract/SSAC26-abstract-draft.md |
| Repo-prep brief (needs revising) | docs/specs/task-30-repo-public-prep.md |
| Data locations | data/raw/ (study), data/raw_holdout/ (women's, spent), data/raw_pff/ and data/processed/pff/, data/raw_1516/open-data-master/ (full StatsBomb ZIP incl. 2015/16), data/raw_reserved/ (spent), data/benchmark_v5/, data/benchmark_v6/ |

---

## 7. Standing rules for the new chat

Copied verbatim from the author's instructions at the start of the project (as recorded in the previous handoff, section 8):

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

Later modifications to this arrangement, agreed in the project (copied from the previous handoff):
- The research lead has direct read/write access to the repo via a filesystem tool and now writes plan and brief files itself, then gives the author a single short prompt to paste into Claude Code. The author usually replies only "task done" plus commit hashes; the research lead reads the results page directly.
- Claude Code's standing routines (from CLAUDE.md): write a results page per task to docs/results/NN-name.md using docs/results/TEMPLATE.md; on "wrap up", update docs/STATUS.md in under 15 lines. docs/STATUS.md does not currently exist.
- CLAUDE.md's Reporting discipline list (rules 1–9) governs Claude Code:
  - "print" means literal text in the reply;
  - no COMPLETE without a per-section checklist;
  - running a subset of a brief is a deviation;
  - do not make research decisions;
  - headlines reflect the weakest evidence;
  - state what a finding would invalidate;
  - no unrequested persistent state (including memory writes);
  - refer to prior work by file path and date;
  - commit all new/changed files under src/ and docs/ at task end.
- The journal is maintained by the research lead only. Claude Code must not edit docs/JOURNAL.md.

Working conventions added in this chat:
- **Tools:** the research lead reads and writes files on the author's Mac through the Filesystem tool (Desktop only) and Desktop Commander. It may run read-only checks in the project .venv. It commits its own briefs, and its corrections to briefs, BEFORE any result exists, so git timestamps show the plan preceded the data.
- **Brief corrections:** when Claude Code finds a gap in a brief, the research lead appends a correction marked "factual error" or "gap", commits it, and Claude Code records it under Deviations.
- **Prompt format:** the paste-in prompt is "Read docs/specs/task-NN-....md and execute it exactly. Follow CLAUDE.md's reporting discipline."
- **Guardrails instead of stop rules:**
  - acceptance tests are never rewritten to pass;
  - holdouts are used once, on gates declared in advance;
  - every attempt and failure is disclosed;
  - named-player ranks are output, never a criterion;
  - claims need the stated correction and, for results tests, a positive control on the same rows.
- **Nulls:** treat any null as a possible bug or a power problem until checked (Task 35's lesson). Report MDEs.
- **Tone:** the author wants optimism and persistence. Stay constructive while keeping the guardrails.

---

## 8. Opening message for the new chat (paste as the first message)

Read docs/CHAT-HANDOFF.md in full before doing anything else, and treat it as authoritative for project state. Where it conflicts with an older results page, benchmark, abstract draft or the previous handoff, the handoff wins, and section 4C lists the known discrepancies.

You are the research lead. I'm the messenger with no technical background; Claude Code builds on my machine. Section 7 has the full rules we work under, copied verbatim. Follow them.

Then read these, in order:
- docs/results/48-confirmation-reserved.md
- docs/results/45-press-resistance-vetting.md
- docs/results/46-movers-and-spatial-physical.md
- docs/results/37-holdout-ptest.md
- docs/BENCHMARK-v6.md