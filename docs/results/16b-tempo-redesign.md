# Task 16b: Tempo — diagnostic and one redesign
Date: 2026-09-26
Status: COMPLETE

## 1. Headline
The diagnostic (D1-D4) confirms all four suspected causes of Task 16's pace_delta/tempo_variation failure: possession sequences were built from the withdrawn engine's 171,618-row matched subset rather than the 289,001 raw open-play passes (75.4% of matched possessions differ in n_passes by >=2 once rebuilt), 42.0% of a player's "without him" comparison sequences occurred while he was off the pitch, and pace_delta's own reliability jumps from 0.456 (match-level split) to 0.913 (sequence-level split, n=54) at the 200 threshold — most of Task 16's measured unreliability was the split, not the metric. The one redesign attempt succeeded: MOVE_ON_SPEED (0.783) and HOLD_VARIATION (0.881) are both USABLE at the 200-threshold gate, replacing pace_delta and tempo_variation. The tempo module now ships with five usable-or-provisional metrics: median_time_on_ball, one_touch_share, pressure_delta (all unchanged from Task 16), plus MOVE_ON_SPEED and HOLD_VARIATION.

## 2. What I did
- Read `docs/specs/analysis-plan-tempo.md` in full, including Amendment T-2, and committed it alone (`b210ce5`).
- Executed `docs/specs/task-16b-tempo-redesign.md` exactly as written:
  - Step 1 (`src/tempo/redesign_diagnostic.py`): ran D1-D4, reported below, no interpretation beyond them, no branching.
  - Step 2 (`src/tempo/redesign_metrics.py`): built MOVE_ON_SPEED and HOLD_VARIATION from `tempo_time_on_ball.parquet`'s existing 209,775-row population (all open-play passes with a resolvable receipt chain), never `passes_situation.parquet`.
  - Step 3 (`src/tempo/redesign_reliability.py`): ran the unchanged gate machinery (`reliability.reliability_sweep_pass_level`, imported unmodified from Task 16) on both redesigned metrics.
  - Step 4 (`src/tempo/redesign_final.py`): built the final five-metric table (raw value + within-position-group z-score per T-2.5), correlation matrix, public-metric correlations, and top/bottom-20-by-z-score leaderboards for all five survivors.
- No file from Task 16 (`time_on_ball.py`, `possessions.py`, `metrics.py`, `reliability.py`, `relationships.py`) was modified; `docs/JOURNAL.md` was not touched.
- Reproduce with (from repo root, `.venv` active):
  `python src/tempo/redesign_diagnostic.py && python src/tempo/redesign_metrics.py && python src/tempo/redesign_reliability.py && python src/tempo/redesign_final.py`
- Total wall clock: ~6 minutes across all four steps, well under the 3-hour box.

## 3. Numbers

### Step 1 — Diagnostic (T-2.2)

**D1 Contamination.** Old sequences (from `passes_situation.parquet`, as shipped in Task 16): 20,042. New sequences (from ALL 289,001 open-play passes): 29,134. Median n_passes: 6 old vs 6 new (unchanged at the median). Median pace: 0.283 old vs 0.373 new. Of the 20,042 old possessions, all 20,042 have a matching new possession (same match/possession/team key); of those matched pairs, **75.36%** differ in n_passes by 2 or more.

**D2 Ratio noise.** On the new (uncontaminated) sequences, n=29,134: pace (n_passes/duration) percentiles p5/p25/p50/p75/p95/p99 = 0.229/0.307/0.373/0.478/0.856/1.309. Using (n_passes-1)/duration instead: 0.183/0.261/0.320/0.392/0.616/0.911 — materially lower throughout, confirming the ratio's sensitivity to the numerator convention. Share of sequences with duration under 3 seconds: 2.36%.

**D3 On-pitch.** Across all of Task 16's own "without him" comparison sequences (181,410 total, from the old/shipped construction), **41.998%** occurred while the player was off the pitch (not yet substituted on, or already substituted off), based on Starting XI lineups and Substitution timestamps.

**D4 Split granularity.** pace_delta reliability recomputed with the SAME (old, contaminated) construction, splitting each player's own "with" sequences at the sequence level instead of the match level, "without" pool held fixed and unsplit:

| threshold | n_units | sequence-level median [p5,p95] | Task 16's match-level median [p5,p95] |
|---|---|---|---|
| 100 | 149 | 0.883 [0.863, 0.904] | 0.330 [0.273, 0.420] |
| 150 | 75 | 0.920 [0.895, 0.938] | 0.408 [0.322, 0.486] |
| **200** | **54** | **0.913 [0.877, 0.940]** | **0.456 [0.368, 0.531]** |
| 250 | 48 | 0.914 [0.871, 0.942] | 0.512 [0.390, 0.632] |
| 300 | 44 | 0.918 [0.882, 0.941] | 0.561 [0.359, 0.661] |
| 400 | 34 | 0.930 [0.902, 0.956] | 0.667 [0.499, 0.760] |
| 500 | 22 | 0.948 [0.915, 0.972] | 0.751 [0.651, 0.836] |

Note the n_units at each threshold is far smaller here (54 at 200, vs 195 for the match-level split on the same old sequences) — the sequence-level split requires a player to have 200 of his own OLD (contaminated) sequences, a much rarer count than 200 time-on-ball involvements, so this comparison is diagnostic evidence only (T-2.2's own instruction), not a metric ready to ship.

### Step 2 — Redesign construction (T-2.3)

Both metrics built from the 209,775-row resolved/bounded population (identical to Task 16's `tempo_time_on_ball.parquet`), joined 1:1 (209,775/209,775) to a freshly built ALL-open-play-pass event stream (289,001 rows) for zone, `pass_length`, and next-pass timing.

- **MOVE_ON_SPEED**: 29,400 passes dropped as the last pass of their (match, possession, team) group (no next pass to measure to); 0 intervals were non-positive. n=180,375 pass-level observations across 2,945 player-seasons (n per player: p5=2, p25=9, median=24, p75=55, p95=210). Regression `log(interval) ~ zone + under_pressure + pass_length` within (match_id, team) fixed effects (exact group-demeaning): within R²=0.185. Residual distribution: p5=-0.947, p25=-0.333, p50=-0.019, p75=0.342, p95=0.937.
- **HOLD_VARIATION**: n=209,775 (full population), 2,905 player-seasons (n per player: p5=2, p25=12, median=30, p75=66, p95=233). Regression `time_on_ball ~ zone + under_pressure + pass_length` within the same fixed effects: within R²=0.042. Player-level SD-of-residual distribution: p5=0.597, p25=0.979, p50=1.230, p75=1.494, p95=1.924.

### Step 3 — The gate (T-2.4), unchanged 0.70/0.50 cutoffs at threshold 200

| threshold | n_units | move_on_speed median [p5,p95] | n_units | hold_variation median [p5,p95] |
|---|---|---|---|---|
| 100 | 395 | 0.606 [0.548, 0.661] | 473 | 0.785 [0.759, 0.811] |
| 150 | 248 | 0.694 [0.648, 0.744] | 290 | 0.846 [0.824, 0.869] |
| **200** | **164** | **0.783 [0.749, 0.827]** | **195** | **0.881 [0.857, 0.902]** |
| 250 | 110 | 0.811 [0.745, 0.852] | 128 | 0.882 [0.854, 0.911] |
| 300 | 88 | 0.821 [0.773, 0.865] | 95 | 0.908 [0.870, 0.932] |
| 400 | 57 | 0.834 [0.771, 0.883] | 60 | 0.921 [0.901, 0.938] |
| 500 | 48 | 0.861 [0.793, 0.904] | 53 | 0.931 [0.904, 0.950] |

**Verdicts at 200: MOVE_ON_SPEED USABLE (0.783), HOLD_VARIATION USABLE (0.881).** Both clear 0.70 with a monotonically increasing curve, the same clean pattern median_time_on_ball/one_touch_share showed in Task 16. Neither needed a second attempt (there is no second attempt permitted regardless, per T-2.4).

### Step 4 — Final five-metric table (n=195 units at the 200-involvement floor; pressure_delta n=188, unchanged from Task 16)

Correlation matrix (raw values):

| | median_time_on_ball | one_touch_share | pressure_delta | move_on_speed | hold_variation |
|---|---|---|---|---|---|
| median_time_on_ball | 1.000 | -0.844 | -0.858 | 0.117 | 0.669 |
| one_touch_share | -0.844 | 1.000 | 0.667 | -0.305 | -0.373 |
| pressure_delta | -0.858 | 0.667 | 1.000 | -0.047 | -0.569 |
| move_on_speed | 0.117 | -0.305 | -0.047 | 1.000 | -0.033 |
| hold_variation | 0.669 | -0.373 | -0.569 | -0.033 | 1.000 |

Correlation with public metrics:

| | completion_pct | progressive_passes_per_90 | xa_per_90 |
|---|---|---|---|
| median_time_on_ball | 0.376 | 0.286 | -0.417 |
| one_touch_share | -0.508 | -0.349 | 0.551 |
| pressure_delta | -0.259 | -0.165 | 0.261 |
| move_on_speed | 0.064 | 0.054 | -0.225 |
| hold_variation | 0.160 | 0.117 | -0.194 |

move_on_speed, top 5 of 195 by within-position z (fastest team ball movement after them, relative to position peers): Victor Boniface (Fwd, z=2.81), Georginio Wijnaldum (Mid, z=2.35), Jonas Hofmann (Mid, z=2.20), Theo Hernández (Def, z=2.01), Ronald Araújo (Def, z=2.01). Bottom 5 (slowest): John Stones (Def, z=-2.62), César Azpilicueta (Def, z=-2.27), Achraf Hakimi (Def, z=-2.25), Raphaël Varane (Def, z=-2.24), Daley Blind (Def, z=-2.22).

hold_variation, top 5 (most variable hold time relative to position peers): Manuel Akanji (Def, z=3.57), Tim Ream (Def, z=2.90), Frenkie de Jong (Mid, z=2.82), Bernardo Silva (Mid, z=2.71), Milan Škriniar (Def, z=2.66). Bottom 5 (most consistent): Lorenzo Insigne (Fwd, z=-1.93), Kalvin Phillips (Mid, z=-1.81), Kieran Trippier (Def, z=-1.60), Pedro González López (Mid, z=-1.57), Antoine Griezmann (Mid, z=-1.57).

median_time_on_ball/one_touch_share/pressure_delta's within-position z-score leaderboards (T-2.5) reorder Task 16's raw leaderboards but do not change which players are extreme (e.g. Akanji tops median_time_on_ball both raw, z=4.62, and by pressure_delta drop, z=-4.45 — the most extreme unit in the dataset on both, consistent with T-2.6's point that pressure_delta is close to arithmetic with median_time_on_ball).

## 4. Deviations from the brief
None from `task-16b-tempo-redesign.md`'s Steps 0-4 or hard rules. Three implementation choices, disclosed per project convention:
- **Fixed-effect estimation.** `C(match_team)` is absorbed by exact group-mean demeaning ((match_id, team) fixed effects, the Frisch-Waugh-Lovell "within" transformation) rather than ~600 dummy columns in an explicit OLS design matrix. This produces mathematically identical residuals to a dummy-variable regression for a one-way fixed effect and is not an approximation; it was chosen for tractability (avoiding a 180,000+ x 600 dense design matrix), not to change the model.
- **Zone reused, reimplemented locally.** "Zone" is not redefined by Amendment T-2; this task reuses the project's existing defensive/middle/final-thirds convention (`task04_situation_context.py`, direction-normalized via shot locations as in `pitch_direction.py`), ported as a local, pure-geometry function in `redesign_metrics.py` rather than imported, to keep `src/tempo/` at zero import-time dependency on `src/decision_engine/`, consistent with Task 16's own stated convention for `position_group`/`match_competition_lookup`/`spearman_brown`.
- **position_group/name lookup reused by import, not re-copied.** `redesign_final.py` imports `position_group` and `build_position_and_name_lookup` directly from `src/tempo/relationships.py` (a sibling module within the same package, already independent of `src/decision_engine/`) rather than duplicating that logic a second time. This differs from the plan file's stated intent to write "a small local copy" but produces identical behavior with no new dependency on the withdrawn engine; noted here since it is a deviation from what was planned, even though not from the task spec itself.

## 5. Problems and surprises
- D4 is the largest surprise: sequence-level reliability (0.913 at 200, though on only 54 units) is nearly double the shipped match-level reliability (0.456) for the exact same, still-contaminated pace_delta construction. This means Task 16's NOT MEASURABLE verdict for pace_delta was driven substantially by an overly coarse split choice, not by the metric being inherently unreliable — a genuine limitation in Task 16's own disclosed "split-unit granularity" choice, now superseded by the redesign rather than repaired directly (per T-2.3/T-2.4, the fix is replacement, not patching the old metric).
- Both within-R² values for the redesign regressions are modest (0.185 for move_on_speed's log-interval model, 0.042 for hold_variation's time_on_ball model) — most variance in interval-to-next-pass and time_on_ball is NOT explained by zone/pressure/pass_length within a match-team. This is expected (these are noisy, context-dependent quantities) and does not by itself threaten the metrics' reliability, since reliability is about split-half agreement of the player-level mean/SD of residuals, not the regression's own fit — but it does mean the "controls" absorb only a modest share of situational variance, so a player's move_on_speed/hold_variation still reflects considerable unmodeled context beyond zone/pressure/distance.
- move_on_speed correlates only weakly with the three existing time-on-ball-based metrics (|r| <= 0.31) and hold_variation correlates moderately with median_time_on_ball (0.669) and pressure_delta (-0.569) — unlike Task 16's three original metrics, which were all highly intercorrelated (|r| 0.67-0.86) and read as largely the same construct. MOVE_ON_SPEED in particular looks like a genuinely different dimension (weak correlation with everything, including the public metrics), though this task makes no claim about what that dimension means.
- The correlation with public metrics is weak-to-modest for both redesigned metrics (|r| <= 0.225), noticeably weaker than one_touch_share's or median_time_on_ball's correlations with the same public metrics (up to |r|=0.55). This module makes no interpretive claim about this difference; it is reported for the paper to weigh.

## 6. Questions for the research lead
None. Amendment T-2 and `task-16b-tempo-redesign.md` fully specified every step; the three items in Section 4 are disclosed implementation choices, not open questions.

## 7. Files produced
- `src/tempo/redesign_diagnostic.py` — Step 1: D1-D4. Committed, commit `9a1df7b`.
- `src/tempo/redesign_metrics.py` — Step 2: MOVE_ON_SPEED/HOLD_VARIATION construction and regression. Committed, commit `9a1df7b`.
- `src/tempo/redesign_reliability.py` — Step 3: the gate, reusing `reliability.reliability_sweep_pass_level` unmodified. Committed, commit `9a1df7b`.
- `src/tempo/redesign_final.py` — Step 4: final five-metric table, correlations, leaderboards. Committed, commit `9a1df7b`.
- `data/tempo_step1b_diagnostic.json`, `data/tempo_step2b_redesign.json`, `data/tempo_step3b_reliability.json`, `data/tempo_step4b_final.json` — step summaries (all numbers in Section 3 come from these). Not committed (data/).
- `data/processed/tempo_redesign_metrics.parquet`, `tempo_redesign_move_residuals.parquet`, `tempo_redesign_hold_residuals.parquet` — per-player and per-pass redesigned-metric tables. Not committed (data/).
- `docs/specs/analysis-plan-tempo.md` (Amendment T-2) — committed alone at Step 0, commit `b210ce5`, SHA-256 `49734efdc88e9772bce41286f9640caeb5be1c1b2ad5403317ca20bf5e2ccc58`.
- `docs/specs/task-16b-tempo-redesign.md` — the executed task spec. Committed, commit `9a1df7b`.
- `docs/results/16b-tempo-redesign.md` — this page. Committed, commit `9a1df7b`.

## 8. Confidence
High for D1-D4 (deterministic recomputation, all four confirm the amendment's stated hypotheses without needing any judgment call) and for the two redesigned metrics' gate verdicts (both clear 0.70 well within margin and rise monotonically with more data, the same pattern the two Task-16 USABLE metrics showed). Lower confidence on interpretation: the redesign's low within-R² means the "controls" are weak, so move_on_speed/hold_variation are reliable in the split-half sense but still reflect a lot of unmodeled context; and D4's dramatic reliability jump from a mere split-granularity change is a reminder that reliability numbers in this module are sensitive to construction choices in ways not fully explored even now (T-1.4/T-2.4 both bar further exploration, so this is disclosed as a limitation, not investigated further).
