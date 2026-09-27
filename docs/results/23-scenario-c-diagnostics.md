# Task 23: Why does scenario_c fail? Diagnostics only, no model changes
Date: 2026-09-27
Status: COMPLETE (diagnostics-only task; no model/feature/threshold code was touched, per the brief's hard rules)

## Disclosure (per the brief, repeated here)
This task continues engine work past Task 22's "no Task 22b" stop rule.
The engine has now failed its acceptance battery or a premise check
three times (Task 19d, 21, 22). Any later acceptance is post hoc — this
must be disclosed in any abstract or paper that uses this work.

## Section checklist
- Step 0 (commit brief alone): COMPLETE
- Step 1 / D1 (take scenario_c apart): COMPLETE
- Step 2 / D2 (central beyond-line, both bands): COMPLETE
- Step 3 / D3 (top-decile description): COMPLETE
- Step 4 (holdout download + ingest only): COMPLETE (125/126 matches with full events+frames; 1 match's 360 frames failed to parse — see Section 5)
- Decision-rule evaluation (R1-R4, holdout gate, hard stop): reported below as a factual evaluation of the brief's own pre-written rules against this task's measurements — not a decision made by this task.

## 1. Headline
Applying the research lead's own pre-written decision rules to this
task's measurements: **R3 fires** — in Task 22's corrected rows
(in-possession, own-event-inclusive labels), a ball beyond the
defensive line in the CENTRAL channel does NOT score more often than a
ball not beyond it, in either band 80-100 (0.26% vs 1.64%) or band
100-120 (2.59% vs 10.02%), and this holds under the dead-ball
sensitivity check. Per R3's own stated text: "this data does not
support scenario_c's football premise. The engine cannot pass its
battery as written. Engine work stops for Oct 1. The test is NOT
rewritten." **R4 also fires** independently: scenario_c's synthetic
frame has no goalkeeper-depth defender and only 6 visible players,
below the 0.88% of Task 19d's training rows with 6-or-fewer visible
players — per R4, this is "reported as a flaw in the test itself and
recorded for the paper," with any amendment to the test being "a
separate, disclosed decision" that would still require passing holdout
replication. R1 and R2 do not fire (R1 requires V_net_success at or
above corpus p90 — it is at the 3.66th percentile, not the 90th; R2
requires central beyond-line to score higher in BOTH bands, which D2
shows is false in both).

## 2. What I did
1. Committed `task-23-scenario-c-diagnostics.md` alone (Step 0).
2. Wrote `task23_d1.py`: reruns all three T4 scenarios through Task
   19d's value models (`value_model_for_v2.json`/`value_model_against_v2.json`)
   and the current, unchanged pass-success model, printing every
   STATE_FEATURES value of both the success and turnover states plus
   p_success/V_net_success/V_net_turnover/EV. For scenario_c, built a
   fixed sample of the Task 19d corpus (`options_ev_v2`) — 50,000 rows
   from each of 30 matches chosen by `np.random.default_rng(20260927)`
   from all 292 match files — and reported scenario_c's percentile on
   each of the four quantities, plus the EV p90 from both this sample
   and a reproduction of the committed test's own first-30-alphabetical/
   seed-42 sampling. Also reported the `n_visible_players` distribution
   in `value_model_rows_v2.parquet` and scenario_c's own visible-player
   count and goalkeeper status (Step 1).
3. Wrote `task23_d2.py`: from `value_model_rows_diagnostic_v4.parquet`
   (Task 22's diagnostic file), in-possession rows only, new labels,
   split by band × channel (CENTRAL = \|ball_y−40\|≤10, WIDE otherwise)
   × beyond-line, with a sensitivity re-run dropping From
   Corner/Free Kick/Throw In rows (Step 2).
4. Wrote `task23_d3.py`: reused Step 1's exact seeded sample, added
   direction-normalized destination coordinates (band, channel), and
   described the EV≥p90 subset against the full sample on destination
   band, channel, pass distance, p_success, and share of exact teammate
   destinations (Step 3).
5. Wrote `src/decision_engine/pull_holdout_data.py` (mirrors the
   existing `pull_data.py` pull logic exactly, output directory and
   competition-season list changed only) and ran it to pull events +
   360 frames for the three 360-covered competition-seasons not in the
   study sample, into `data/raw_holdout/` (Step 4).

Reproduce with (from `src/engine_v2/`, `.venv` activated):
`python task23_d1.py && python task23_d2.py && python task23_d3.py`,
and (from the repo root) `python src/decision_engine/pull_holdout_data.py`.

## 3. Numbers

### D1 — scenario_a and scenario_b (Task 19d models, current pass-success model)
| scenario | option | p_success | V_net_success | V_net_turnover | EV |
|---|---|---|---|---|---|
| a | unmarked runner | 0.7500 (injected) | −0.00474 | 0.01470 | 0.00012 |
| a | marked sideways | 0.7500 (injected) | 0.00303 | −0.03251 | −0.00585 |
| b | into cluster | 0.0787 | 0.00606 | −0.01060 | −0.00929 |
| b | into open space | 0.9925 | 0.00543 | −0.01217 | 0.00529 |

Both a/b comparisons point the same direction as their own T4 assertions
(unmarked > marked, open space > cluster) — this task changes nothing,
so this is a restatement, not a new finding.

Full STATE_FEATURES for both states of every a/b option are in
`data/engine_v2_task23_d1.json`; not reproduced in full here for space,
but every field the brief asked for is in that file.

### D1 — scenario_c, in full
| quantity | success state | turnover state |
|---|---|---|
| ball_x, ball_y | 95.0, 40.0 | 25.0, 40.0 |
| prev_x, prev_y | 60.0, 40.0 | 60.0, 40.0 |
| opponents_ahead_of_ball | 0 | 0 |
| teammates_ahead_of_ball | 0 | 4 |
| numerical_advantage_ahead | 0 | 4 |
| distance_to_nearest_opponent_u | 25.50 | 0.0 |
| opponents_within_5u / 10u | 0 / 0 | 1 / 1 |
| defensive_line_x | 70.0 | NaN (no opponents in this direction) |
| ball_beyond_defensive_line | True | False |
| n_visible_players | 6 | 6 |
| time_remaining_period, score_diff | 1000.0, 0 | 1000.0, 0 |
| play_pattern_code | 0 (Regular Play) | 4 (From Counter) |

p_success=0.9469, V_net_success=−0.00086, V_net_turnover=0.05912,
EV=0.00232.

**Percentiles in the seeded sample (n=1,500,000, 30 of 292 matches, seed=20260927):**
| quantity | scenario_c value | percentile |
|---|---|---|
| p_success | 0.9469 | 73.59 |
| V_net_success | −0.00086 | **3.66** |
| V_net_turnover | 0.05912 | 99.98 |
| EV | 0.00232 | 86.55 (83.72 in the committed-test-style sample) |

**EV p90, two sampling procedures (both on `options_ev_v2`):**
| sample | EV p90 |
|---|---|
| seeded (30 random matches, seed=20260927) | 0.00320 |
| committed-test-style (first 30 alphabetical, seed=42/file — reproduced here, not the original `options_ev` the committed test itself points at) | 0.00402 |

Scenario_c's EV (0.00232) is below BOTH p90 thresholds — the ~26%
difference between the two thresholds does not change the verdict.

**V_net_success p90 (seeded sample): 0.00709.** Scenario_c's
V_net_success (−0.00086) is far below this — **R1's condition (V_net_success
at or above p90 while EV is not) does NOT hold.**

**n_visible_players in Task 19d's training rows (n=976,691):** mean
16.17, median 17, 1st pct 7, 5th pct 10, min 1, max 22. **Share with ≤6
visible players: 0.8827%** (under the brief's 1% reference point).
Scenario_c's synthetic frame has exactly 6 visible players (4 opponents
+ 1 teammate + the actor) and no opponent positioned as a goalkeeper —
all 4 opponents sit at x=70, none near the high-x end of the passer's
attacking frame where Task 19c/19d established the defending
goalkeeper actually sits (`defensive_line_x` convention).

### D2 — band × channel × beyond-line, in-possession rows, new labels (n=828,728)
| band | channel | beyond line | n | P(score in 10) | P(concede in 10) |
|---|---|---|---|---|---|
| 80-100 | CENTRAL | No | 16,800 | 1.6429% | 0.0417% |
| 80-100 | CENTRAL | Yes | 12,555 | 0.2628% | 0.0398% |
| 80-100 | WIDE | No | 77,433 | 0.9118% | 0.0310% |
| 80-100 | WIDE | Yes | 35,050 | 0.2882% | 0.0456% |
| 100-120 | CENTRAL | No | 6,858 | 10.0175% | 0.1167% |
| 100-120 | CENTRAL | Yes | 16,999 | 2.5884% | 0.0941% |
| 100-120 | WIDE | No | 19,588 | 2.8385% | 0.0000% |
| 100-120 | WIDE | Yes | 21,996 | 1.3002% | 0.0318% |

**Central beyond-line scores LOWER than central not-beyond in both
bands** (80-100: 0.26% vs 1.64%; 100-120: 2.59% vs 10.02%).

**Sensitivity (dropping From Corner/Free Kick/Throw In rows — 334,158
of 828,728 in-possession rows, 40.32%):**
| band | channel | beyond line | n | P(score in 10) | P(concede in 10) |
|---|---|---|---|---|---|
| 80-100 | CENTRAL | No | 10,687 | 1.5065% | 0.0094% |
| 80-100 | CENTRAL | Yes | 7,954 | 0.3520% | 0.0251% |
| 80-100 | WIDE | No | 44,150 | 0.9151% | 0.0091% |
| 80-100 | WIDE | Yes | 21,983 | 0.3230% | 0.0364% |
| 100-120 | CENTRAL | No | 3,589 | 9.6406% | 0.1393% |
| 100-120 | CENTRAL | Yes | 11,483 | 2.2381% | 0.1045% |
| 100-120 | WIDE | No | 9,749 | 3.3439% | 0.0000% |
| 100-120 | WIDE | Yes | 14,504 | 1.0962% | 0.0138% |

Same qualitative result: central beyond-line still scores lower than
central not-beyond in both bands (80-100: 0.35% vs 1.51%; 100-120:
2.24% vs 9.64%). **R3's condition holds under this sensitivity check
too.**

### D3 — top EV decile (EV≥0.00320, n=150,000) vs full seeded sample (n=1,500,000)
| quantity | full sample | top decile |
|---|---|---|
| band 0-40 | 28.84% | 31.09% |
| band 40-60 | 20.83% | 13.98% |
| band 60-80 | 20.86% | 15.54% |
| band 80-100 | 17.56% | 23.59% |
| band 100-120 | 11.91% | 15.80% |
| channel WIDE | 66.14% | 64.52% |
| channel CENTRAL | 33.86% | 35.48% |
| distance_u mean / median | 35.90 / 37.03 | 29.16 / 27.32 |
| p_success mean / median | 0.7140 / 0.7790 | 0.8233 / 0.9018 |
| share exact teammate destination | 1.68% | 4.57% |

No interpretation, per the brief.

### Step 4 — holdout data pull
| competition-season | matches | 360 available | pulled (events+frames) |
|---|---|---|---|
| Women's Euro 2022 (comp 53, season 106) | 31 | 31 | 30 |
| Women's World Cup 2023 (comp 72, season 107) | 64 | 64 | 64 |
| Women's Euro 2025 (comp 53, season 315) | 31 | 31 | 31 |
| **Total** | **126** | **126** | **125** |

Frame coverage: 125/126 (99.21%). Written to `data/raw_holdout/{events,frames,matches}/`,
never `data/raw/`. No model, feature, or outcome code was run on this
data in this task.

## 4. Deviations from the brief
None from the hard rules (no engine file, model, feature, threshold, or
test changed; no retraining; no new EV corpus; holdout data downloaded
and counted only). One disclosed operationalization: "percentile of
p_success/V_net_success/V_net_turnover/EV" and "both p90 values" are
reported using the seeded sample (30 random matches, seed=20260927) as
the primary reference, with the committed-test-style sample (first 30
alphabetical files, seed=42/file) reported alongside for comparison —
both computed on `options_ev_v2` as the brief specifies, not on the
committed test's own `options_ev` (Task 15's original corpus), since
the brief is explicit the comparison should be "across the Task 19d
corpus."

## 5. Problems and surprises
- One holdout match (3845506, Women's Euro 2022) pulled its events
  successfully but its 360 frames failed to parse twice with
  `Expecting ',' delimiter: line 92794 column 3` — a malformed/truncated
  JSON response from StatsBomb's own 360 data endpoint for this match,
  not a bug in the pull script (the same script pulled 125 other
  matches' frames without incident). This match's events file exists;
  its frames file does not. Frame coverage is reported as 125/126, not
  126/126.
- Scenario_c's success state (`distance_to_nearest_opponent_u=25.50`,
  0 opponents within 10 units, `ball_beyond_defensive_line=True`) is
  about as unmarked and advanced a position as a state can be, yet
  `V_net_success` for it sits at the 3.66th percentile of the corpus —
  this is consistent with, not contradicted by, D2's finding that even
  the CENTRAL channel does not show beyond-line states scoring more
  than not-beyond states: the model's low valuation of this exact kind
  of state tracks a real pattern in the data it was trained on, not an
  isolated model quirk.
- Scenario_c's turnover state has `distance_to_nearest_opponent_u=0.0`
  (the ball lands exactly on an opponent's recorded position) and a
  4-0 numerical disadvantage for the counter-attacking side — its
  `V_net_turnover` (99.98th percentile) is about as extreme a value as
  the corpus contains. Both halves of scenario_c's EV are therefore
  built from near-boundary states of the corpus's own distribution,
  which is itself part of why R4 (a synthetic frame far outside the
  training data) fires alongside R3.
- R3 and R4 fire on independent grounds and do not resolve each other:
  R3 says the DATA does not support the football premise the test
  encodes; R4 says the TEST's own frame is unusually sparse relative to
  training data. Both are true simultaneously in this diagnostic and
  are reported as such, per the brief's instruction that "the next task
  is chosen by these [rules], not by what looks promising."

## 6. Questions for the research lead
1. R3's stated consequence is "Engine work stops for Oct 1. The test is
   NOT rewritten." R4's stated consequence is that the test's flaw is
   "recorded for the paper" and any amendment is "a separate, disclosed
   decision" gated on holdout replication. These two rules, read
   together, appear to allow R4's path (an amended, holdout-validated
   test) even while R3 has independently fired on the CURRENT test. Is
   that the intended reading, or does R3 firing close off R4's path
   entirely for this abstract cycle?
2. This task's own hard rule forbids retraining or a new EV corpus, so
   nothing here tests whether a value-model fix (as R2 would have
   authorized) might have changed D2's central-channel result. Given R2
   did not fire (D2 shows beyond-line scoring lower, not higher, in
   both bands), is that avenue considered closed, or is there a reading
   of "one fix attempt on the value model" that the research lead wants
   pursued despite R2 technically not applying?
3. The holdout data (`data/raw_holdout/`) is now on disk but per this
   task's hard rules has not been touched by any model/feature/outcome
   code. Given R3 has fired, should the holdout data be left in place
   for a possible future use, or is there no further engine work
   expected to need it before Oct 1?

## 7. Files produced
- `src/engine_v2/task23_d1.py` — new. Reruns T4's three scenarios
  through Task 19d's value models, reports full STATE_FEATURES, and
  scenario_c's corpus percentiles (seeded + committed-test-style
  samples).
- `src/engine_v2/task23_d2.py` — new. Band × channel × beyond-line
  split on Task 22's corrected diagnostic rows, plus the dead-ball
  sensitivity check.
- `src/engine_v2/task23_d3.py` — new. Top-EV-decile description
  (destination band/channel/distance/p_success/teammate-destination
  share) vs the full seeded sample.
- `src/decision_engine/pull_holdout_data.py` — new. Pulls the three
  holdout competition-seasons into `data/raw_holdout/`.
- `data/processed/engine_v2/task23_d1_sample.parquet` — new data
  artifact (the seeded sample, reused by D3; not committed, `data/` is
  never committed).
- `data/engine_v2_task23_d1.json`, `engine_v2_task23_d2.json`,
  `engine_v2_task23_d3.json` — new summary JSONs backing Section 3
  (also under `data/`, not committed).
- `data/raw_holdout/events/*.parquet` (126 files), `frames/*.parquet`
  (125 files), `matches/*.parquet` (3 files) — new raw data, not
  committed (`data/` is never committed), never written into
  `data/raw/`.
- `docs/results/23-scenario-c-diagnostics.md` — this file.
- Commit hashes: `2ce6e5d` (brief alone, Step 0), `<pending>` (this
  results page + Steps 1–3 scripts + Step 4's holdout-pull script) — to
  be filled in a follow-up commit per CLAUDE.md rule 9.

## 8. Confidence
High confidence in every number reported: D1/D2/D3 are direct
recomputations against already-frozen, previously-validated models and
corpora (Task 19d's models, Task 22's diagnostic rows), with no new
modeling step introduced anywhere in this task. The one place a
methodology choice was made (which sample to treat as primary for
percentiles) is disclosed in Section 4. The weakest link is Section
1/6's application of the brief's own R1-R4 rules: this task evaluated
each rule's stated CONDITION against the data exactly as written, but
whether the stated CONSEQUENCES (engine work stopping, holdout gating,
test amendment) are actually enacted is a decision for the research
lead, not something this results page enacts on its own authority.
