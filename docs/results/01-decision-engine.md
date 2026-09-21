# Task 01: Decision Engine and Reliability Gate
Date: 2026-09-19
Status: COMPLETE

## 1. Headline
The pipeline runs end to end on 299 matches (8 men's, 360-covered
competition-seasons) and both gates report cleanly. **Gate A (overall
reliability) fails the pre-registered 0.50 threshold for Decision
(0.227), Execution (0.131), and Risk (0.310)** — but reliability for the
1,624 players is driven almost entirely by pass volume: for the 63
players with >500 eligible passes, Decision reliability is 0.864 and
Risk is 0.778, both comfortably above 0.70. **Gate B finds no
problematic correlation between Decision and Execution (r=0.058) or any
public metric (all |r|<0.34)** — the one pair over the 0.70 threshold is
Decision vs. Risk (r=-0.776), which is not one of the pairs the
preregistration's separation check names. Per the spec's hard rule,
nothing proceeds past these gates without an instruction from the
research lead.

## 2. What I did
- Re-derived the sample from StatsBomb's live `competition_gender` field
  (not name-guessing) joined against Task 00's 360-coverage cache:
  8 competition-seasons, 299 matches (table in Section 3). Reproduce:
  `python src/decision_engine/sample.py`
- Installed `xgboost` + `scikit-learn` (plus the `libomp` system library
  xgboost needs on macOS) — justified: the spec names gradient boosting
  explicitly, and `xgboost` is Regista 1's established choice for this
  exact kind of tabular task.
- Pulled events + 360 frames for all 299 matches fresh (`src/decision_engine/pull_data.py`).
  Hit two real infrastructure problems along the way (Section 5); both
  fixed, final pull completed 299/299 matches, 0 failures.
- **Stopped and asked before writing Step 1**: StatsBomb's 360 freeze
  frames carry no player identity, so the actual pass recipient can't be
  read off a frame row directly — this wasn't anticipated by the brief.
  Resolved via D-011 (angle-matching, details below).
- Built option sets (Step 1, `src/decision_engine/options.py`), trained
  the pass-success model (Step 2, `pass_success.py`), the possession-value
  model (Step 3, `possession_value.py` — including a self-caught pitch-
  direction-normalization fix, Section 5), computed EV per option
  (Step 4, `expected_value.py`), trained the behavior policy (Step 5,
  `policy.py`), and decomposed Decision/Execution/Risk per pass,
  aggregated per player-competition-season (Step 6, `decompose.py`).
- Ran Gate A (`gate_a_reliability.py`) and Gate B (`gate_b_separation.py`)
  on the full sample and stopped, per the spec's hard rule.

## 3. Numbers

### Sample (Step 0)
Re-derived programmatically via `competition_gender == "male"`, not
hardcoded — confirmed identical to Task 00's audit:

| Competition-season | competition_id | season_id | Matches |
|---|---|---|---|
| Bundesliga 2023/24 | 9 | 281 | 34 |
| FIFA World Cup 2022 | 43 | 106 | 64 |
| La Liga 2020/21 | 11 | 90 | 35 |
| Ligue 1 2022/23 | 7 | 235 | 32 |
| Ligue 1 2021/22 | 7 | 108 | 26 |
| Major League Soccer 2023 | 44 | 107 | 6 |
| UEFA Euro 2024 | 55 | 282 | 51 |
| UEFA Euro 2020 | 55 | 43 | 51 |
| **Total** | | | **299** |

Data pull: 299/299 matches, 0 permanent failures (222 freshly pulled,
77 already cached from earlier testing).

### Step 1 — Option sets
250,850 open-play passes had a freeze frame with ≥6 visible players
(the eligible population). Of those, after angle-matching (D-011):

| Outcome | Count | Share of eligible |
|---|---|---|
| Matched (chosen candidate identified) | 171,618 | 68.4% |
| Unmatched (best bearing diff > 15°) | 76,150 | 30.4% |
| Ambiguous (rival candidate within 10°/5m) | 3,081 | 1.2% |

**Drop rate is not uniform by outcome — flagging loudly as instructed**:
completed passes drop at **28.9%**, incomplete passes drop at **47.4%**
— incomplete passes are ~1.6x more likely to be excluded from the
Decision/Execution/Risk analysis. This is a real, non-trivial bias risk:
Execution is computed only on matched passes, so if failed passes are
systematically harder to angle-match (plausible — a misdirected pass
has no clear "intended" bearing to match against), Execution estimates
skew toward the passes that were easiest to identify, not a random
sample of all attempts.

Option-set size: mean 7.0, median 7.0 visible teammates per pass.
Bearing-difference distribution for accepted matches: mean 5.9°, median
5.3°, 90th percentile 12.2° (well inside the 15° acceptance threshold,
i.e. most accepted matches are unambiguous, not borderline).
Validation check (completed passes only): angle-matching agrees with
simple nearest-to-endpoint matching **76.5%** of the time (116,739 /
152,502) — a real, honest 23.5% disagreement rate between the two
methods, reported as asked, not smoothed over.

### Step 2 — Pass success model
AUC **0.867** (233 train matches / 59 test matches, split by match to
avoid leakage). Calibration is close across deciles (e.g. predicted
0.86 vs actual 0.84 in one mid-range bin; predicted 0.996 vs actual
0.997 in the top bin — full table in `data/pass_success_summary.json`).
Only **0.015%** of unchosen candidates fall outside the training
feature range (extrapolation is negligible).

### Step 3 — Possession value model
AUC **0.799** on 1,136,007 action-state rows from the full event stream
of all 299 matches (per D-010's resolved scope), positive-label rate
0.59% (does the possessing team score within the next 10 actions).
Pitch-direction normalization (added after a self-caught bug, Section 5)
needed its no-shots-in-period fallback in only **1 of 646** team-periods
— direction inference from shot locations is reliable at this scale.

### Step 4 — Expected value
Chosen options score higher mean EV (-0.00021) than unchosen options
(-0.00241) — the intended sanity check passes: players' actual choices
outscore the alternatives they didn't take, on average, though the
distributions overlap substantially (both roughly ±0.01-0.02 std).

### Step 5 — Behavior policy
Top-1 accuracy **40.3%**, top-3 accuracy **73.9%** (35,356 held-out
passes, 59 match-disjoint test matches). Random-guessing baseline given
a mean option-set size of 7 would be ~14% (top-1) / ~43% (top-3) — the
policy substantially beats chance.

### Step 6 — Decomposition
2,901 player-competition-season rows. `execution_per_100` has a small
but consistent negative mean (-0.163, std 0.83) — realized outcomes run
slightly below what the expected-value model predicted, on average.
Not obviously a bug (checked the code twice), but worth the research
lead's attention — see Section 5.

### GATE A — Reliability (STOP AND REPORT)
Split-half correlation, Spearman-Brown corrected, 1000-iteration
bootstrap CI, seed=42:

| Metric | Overall (n=1,624) | >500 passes (n=63) | ≤500 passes (n=1,561) |
|---|---|---|---|
| Decision | **0.227** [0.031, 0.376] | **0.864** [0.786, 0.918] | 0.189 [0.011, 0.336] |
| Execution | **0.131** [-0.003, 0.243] | 0.630 [0.382, 0.784] | 0.051 [-0.114, 0.195] |
| Risk | **0.310** [0.124, 0.458] | **0.778** [0.623, 0.884] | 0.101 [-0.221, 0.343] |

Against the preregistered thresholds in `analysis-plan-pillar4.md`
(≥0.70 proceed, 0.50-0.70 proceed with attenuation correction, <0.50
stop): **overall reliability for all three metrics is below 0.50** —
the preregistered stop condition. The >500-pass subgroup tells a
different story entirely (Decision and Risk both clear 0.70). Only 63
of 1,624 players (3.9%) clear 500 eligible passes.

### GATE B — Separation (STOP AND REPORT)

| | Decision | Execution | Risk | Prog. passes/90 | xA/90 | Completion% |
|---|---|---|---|---|---|---|
| Decision | 1.000 | 0.058 | -0.776 | 0.093 | -0.026 | 0.338 |
| Execution | 0.058 | 1.000 | 0.031 | 0.124 | 0.047 | 0.457 |
| Risk | -0.776 | 0.031 | 1.000 | -0.004 | 0.035 | -0.151 |

Decision vs. Execution: r=0.058 (clean separation). Decision vs. every
named public metric: all |r| < 0.34 (clean separation). **The only pair
above 0.70 is Decision vs. Risk (r=-0.776)** — not one of the pairs
`analysis-plan-pillar4.md`'s separation check names (it names Decision
vs. Execution and Decision vs. public metrics only), but flagged for
the research lead's attention since it may reflect how Risk was
constructed (Section 4).

## 4. Deviations from the brief
- **D-011 (chosen-candidate identification)**: StatsBomb 360 frames
  carry no player identity. Resolved via angle-matching per your
  instruction — bearing from passer to pass_end_location vs. bearing to
  each visible teammate, accept within 15°, reject as ambiguous if a
  rival is within 10°/5m. Recorded in `docs/DECISIONS.md`.
- **D-010 (possession-value training scope)**: trained on the full
  event stream of the 299-match sample only, not all 3,961 StatsBomb
  matches, per your resolution. Recorded in `docs/DECISIONS.md`.
- **Turnover-value construction (Step 4, not asked as a blocking
  question — stated here for visibility)**: "value after turnover, from
  the possessing team's perspective" = the same Step 3 model evaluated
  on the post-turnover state from the new possessor's side, negated.
  Post-turnover phase modeled as `play_pattern = "From Counter"`;
  post-success phase modeled as `"Regular Play"`. No alternative
  construction was implied by a single trained value function, but
  these two phase assumptions are mine, not the spec's.
- **Behavior policy pooling (Step 5)**: "typical player" = pooled
  across all players, situational features only, no player-identity
  feature. A player-specific policy would make Decision ≈ 0 by
  construction for every player, defeating the metric's purpose — the
  only reading consistent with what Decision is for.
- **Risk formula (Step 6)**: the spec says "EV variance of the chosen
  option relative to the policy-weighted average variance" without a
  formula. Implemented as `Var(option) = p_success*(1-p_success)*
  (v_success - v_turnover)^2` (the variance of that option's two-point
  success/turnover outcome), then `Risk = Var(chosen) -
  policy_weighted_avg(Var)` — mirroring Decision's exact "chosen minus
  policy-weighted-average" structure. This is very likely why Decision
  and Risk correlate at -0.776 in Gate B (Section 5) — a different Risk
  construction might not show this collinearity.
- **Reference metrics (progressive passes, xA, completion%, minutes)**
  computed over each player's FULL event activity that competition-
  season, not restricted to the frames-eligible subset used for
  Decision/Execution/Risk — these are meant to be the ordinary, standard
  versions of these metrics for Gate B's separation check, not an
  artificially restricted comparison.
- **Progressive pass definition** (not specified in the brief): a
  completed pass that reduces attack-direction-normalized distance to
  the center of the opponent's goal by ≥10m. A stated simplification,
  not the FBref/Opta definition (which varies threshold by pitch zone).
- **Minutes played**: derived from Starting XI lineups + Substitution
  events + match end time. Does not separately handle red-card
  ejections — a minor, rare-case simplification.

## 5. Problems and surprises
- **Two real infrastructure failures during the data pull, both fixed**:
  (1) `statsbombpy`'s built-in `requests_cache` layer degrades severely
  on a long bulk pull under this machine's tight memory (fresh calls:
  ~0.1-0.5s; after ~30 matches in one long-running process: 30-50s/call)
  — fixed by disabling the cache for this one-pass use case. (2)
  `statsbombpy`'s internal `requests.get()` calls carry no timeout, so a
  single stalled connection hangs the whole pull forever;
  `socket.setdefaulttimeout()` does **not** fix this (urllib3 manages
  its own timeout independently) — fixed by monkeypatching `requests.get`
  directly. Both saved to memory for future sessions. Net effect: the
  pull stalled twice (once for ~2 hours, once indefinitely) before these
  fixes, then completed cleanly in a few minutes once both were in place.
- **Self-caught bug: possession-value model initially ignored attacking
  direction.** StatsBomb's raw pitch coordinates are absolute, not
  relative to which end a team attacks — and teams switch ends between
  periods. Without normalizing for this, "high x" doesn't consistently
  mean "close to goal," undermining the exact flaw the spec says to fix
  (a location-only value function). Caught and fixed before the first
  full run, not after — added `pitch_direction.py`, inferring each
  team's attacking direction per period from shot locations.
- **Incomplete passes drop out of the eligible sample at 1.6x the rate
  of completed passes** (47.4% vs 28.9%, Section 3) — flagged loudly per
  your instruction. This is a real bias risk for Execution specifically,
  since it's computed only on matched (non-dropped) passes.
- **`execution_per_100`'s slightly negative mean** (-0.163 across 2,901
  player-seasons) is a stable pattern (also present in every partial-data
  test run), not sample noise. Not clearly a bug, but not obviously
  expected either — flagged for the research lead rather than
  explained away.
- **Gate A's overall/subgroup split is the headline finding of this
  entire task.** Reliability is essentially unmeasurable below 500
  passes (Decision 0.19, Execution 0.05, Risk 0.10 — all far below 0.50)
  but strong above it (Decision 0.86, Risk 0.78). This looks like a
  sample-size/noise story, not "the metric is meaningless," but that
  interpretation is the research lead's call, not mine.
- **Gate B's Decision-Risk correlation (-0.776)** likely traces to my
  own Risk formula construction (Section 4) rather than a finding about
  the world — flagging clearly so it isn't mistaken for a "the pillars
  aren't separable" result, which is what the preregistration's named
  pairs are actually checking for (and those all pass cleanly).

## 6. Questions for the research lead
1. **Gate A failed the pre-registered overall threshold (<0.50 for all
   three metrics) — per the spec's hard rule, nothing proceeds without
   your instruction.** The >500-pass subgroup (63 players) clears 0.70
   for Decision and Risk. Is a minimum-passes threshold (e.g., restrict
   Pillar 4's sample to players above some eligible-pass floor) an
   acceptable path forward, or does the overall failure mean this
   pillar's measurement approach needs rework before any market join?
   I have not touched Task 2 or any market data — this is squarely
   blocked on your answer.
2. **Is the Risk formula construction (Section 4) acceptable**, given
   it's my own construction (not spelled out in the brief) and appears
   to be driving Gate B's one above-threshold correlation? If you have
   a different formula in mind, Risk (and only Risk) would need
   recomputing — Decision and Execution don't depend on it.
3. **Is the 1.6x completed-vs-incomplete drop-rate gap (Section 5)
   acceptable to proceed with, or does it need addressing** (e.g., a
   less strict bearing threshold, or explicitly modeling the bias)
   before Execution numbers are trusted?
4. **`execution_per_100`'s consistent small negative mean** — is this
   expected (e.g., a known asymmetry in how realized outcomes compare
   to blended EV predictions), or does it suggest a calibration issue
   worth chasing before Task 2?

## 7. Files produced
- `src/decision_engine/sample.py` — Step 0, re-derives the sample from
  live StatsBomb data.
- `src/decision_engine/pull_data.py` — data pull, with the cache-disable
  and timeout-monkeypatch fixes from Section 5.
- `src/decision_engine/pitch_direction.py` — shared attack-direction
  normalization, used by Steps 3, 4, and 6.
- `src/decision_engine/options.py` — Step 1, including D-011 angle-matching.
- `src/decision_engine/pass_success.py` — Step 2.
- `src/decision_engine/possession_value.py` — Step 3.
- `src/decision_engine/expected_value.py` — Step 4.
- `src/decision_engine/policy.py` — Step 5.
- `src/decision_engine/decompose.py` — Step 6, including the shared
  `build_per_pass_table()` also used by Gate A.
- `src/decision_engine/gate_a_reliability.py`, `gate_b_separation.py` —
  the two gates.
- `data/raw/{events,frames,matches}/` (gitignored) — raw pulls, 299 matches.
- `data/processed/*.parquet` (gitignored) — options, scored options, EV,
  policy, and the final `player_season_metrics.parquet` (2,901 rows).
- `data/gate_a_reliability.json`, `data/gate_b_separation.json`
  (gitignored) — full gate output.
- `docs/DECISIONS.md` — D-010, D-011 appended.
- `docs/results/01-decision-engine.md` — this page.

## 8. Confidence
High confidence in Steps 1-5's mechanics (AUCs and calibration are
sane, the chosen-vs-unchosen EV sanity check passes, the behavior
policy clearly beats chance) and in the pitch-direction fix (validated:
fallback needed in only 1/646 team-periods). **Gate A's result is the
one I'd stake the least on procedurally and the most on substantively**
— the split-half method itself is standard and the code was verified
against a shared function used identically in both `decompose.py` and
the gate script, but the underlying finding (reliability collapses
below 500 passes) is exactly the kind of result that's easy to
misread as "the pipeline is broken" when it may just be an honest
statement about noise at low sample sizes. The weakest link is Risk's
formula (Section 4) — it's my own construction, and Gate B's one
above-threshold correlation traces directly to it.
