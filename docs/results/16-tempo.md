# Task 16: Tempo module
Date: 2026-09-24
Status: COMPLETE

## 1. Headline
Of the five preregistered tempo metrics, two (median_time_on_ball, one_touch_share) are USABLE at the 200-involvement gate (split-half reliability 0.939 and 0.959), one (pressure_delta) is only PROVISIONAL (0.595), and two (pace_delta, tempo_variation) are NOT MEASURABLE (0.456 and 0.097) and are dropped per Amendment T-1.3. No repair pass was triggered: Step 1's Carry sanity check passed and receipt-chain coverage (72.6%) exceeded the 40% floor on the first attempt, so both pre-specified remedies (T-1.2a, T-1.2b) went unused. No outcome or Decision/Execution/Risk claim is made anywhere in this task, per plan section 7 and the hard rule against touching engine v1 columns.

## 2. What I did
- Read `docs/specs/analysis-plan-tempo.md` in full, including Amendment T-1, and committed it alone (`aba4050`).
- Read `docs/specs/task-16-tempo.md` in full and executed it as written, one step at a time:
  - Step 1 (`src/tempo/time_on_ball.py`): built time-on-ball for every open-play pass across all 299 study matches by walking backward through the match's own event index to find the same player's preceding `Ball Receipt*`, allowing an intervening same-player `Carry`. Reported coverage, unresolved-reason breakdown, the 0-15s bound exclusion, the full distribution, and the Carry sanity check before anything else — all gates passed, no repair triggered.
  - Step 2 (`src/tempo/metrics.py`, using `src/tempo/possessions.py` for the possession-sequence definition): built the five per-player-season quantities plus `pressure_delta`/`pace_delta` bootstrap CIs (1,000 draws, clustered by match).
  - Step 3 (`src/tempo/reliability.py`): ran the 100-repeat split-half Spearman-Brown reliability sweep at all 7 thresholds for all 5 metrics, classified each at the 200-threshold gate.
  - Step 4 (`src/tempo/relationships.py`): computed the correlation matrix and public-metric correlations and top/bottom-20 leaderboards for the 3 qualifying metrics only; `pace_delta`/`tempo_variation` were not touched, per the gate.
- Reproduce with (from repo root, `.venv` active):
  `python src/tempo/time_on_ball.py && python src/tempo/metrics.py && python src/tempo/reliability.py && python src/tempo/relationships.py`
- Total wall clock: well under the 3-hour box (~12 minutes across all four steps).

## 3. Numbers

### Step 1 — time on ball construction (n=289,001 open-play passes, 299 matches)
- Resolved: 209,783 (72.589%). Unresolved: 79,218 (27.411%), broken down as other/undetermined 45,135, won by tackle/interception 21,104, first event of possession 8,682, header 4,297.
- Excluded by the 0-15s bound: 8 of 209,783 resolved (209,775 remain).
- Distribution of time_on_ball (seconds), n=209,775: p5=0.000, p25=0.377, p50=1.130, p75=2.034, p95=4.301.
  - Complete passes (n=184,872): p5=0.000, p25=0.480, p50=1.155, p75=2.070, p95=4.347.
  - Incomplete passes (n=24,903): p5=0.000, p25=0.040, p50=0.871, p75=1.764, p95=3.917.
- Carry sanity check: median time_on_ball when preceded by a same-player Carry = 1.285s (n=175,139) vs 0.000s with no preceding Carry (n=34,636). PASSED. No repair pass triggered.

### Step 2 — per-player-season units
- 2,988 (player, competition, season) units with time-on-ball metrics (median_time_on_ball, IQR, one_touch_share, pressure_delta).
- 20,042 possession sequences (>=3 passes) built across the 299 matches; 0 excluded for zero/negative duration.
- 2,846 units with pace metrics (pace_delta, tempo_variation); 2,997 units after the outer merge.

### Step 3 — THE GATE: split-half reliability (Spearman-Brown, 100 repeats, median [p5, p95] across repeats)

| threshold | n_units | median_time_on_ball | one_touch_share | pressure_delta | pace_delta | tempo_variation |
|---|---|---|---|---|---|---|
| 100 | 473 | 0.892 [0.878, 0.906] | 0.920 [0.910, 0.928] | 0.510 [0.416, 0.591] | 0.330 [0.273, 0.420] | 0.129 [0.037, 0.261] |
| 150 | 290 | 0.918 [0.895, 0.928] | 0.943 [0.935, 0.951] | 0.486 [0.361, 0.593] | 0.408 [0.322, 0.486] | 0.056 [-0.076, 0.180] |
| **200** | **195** | **0.939 [0.921, 0.949]** | **0.959 [0.950, 0.967]** | **0.595 [0.472, 0.710]** | **0.456 [0.368, 0.531]** | **0.097 [-0.086, 0.255]** |
| 250 | 128 | 0.955 [0.943, 0.965] | 0.969 [0.962, 0.975] | 0.684 [0.527, 0.767] | 0.512 [0.390, 0.632] | 0.228 [0.050, 0.382] |
| 300 | 95 | 0.959 [0.949, 0.969] | 0.972 [0.963, 0.980] | 0.652 [0.500, 0.807] | 0.561 [0.359, 0.661] | 0.409 [0.252, 0.557] |
| 400 | 60 | 0.967 [0.955, 0.978] | 0.980 [0.970, 0.986] | 0.813 [0.685, 0.891] | 0.667 [0.499, 0.760] | 0.480 [0.258, 0.643] |
| 500 | 53 | 0.968 [0.948, 0.978] | 0.982 [0.975, 0.987] | 0.890 [0.816, 0.932] | 0.751 [0.651, 0.836] | 0.548 [0.362, 0.729] |

Gate verdicts at threshold=200 (fixed, preregistered): **median_time_on_ball USABLE, one_touch_share USABLE, pressure_delta PROVISIONAL, pace_delta NOT MEASURABLE, tempo_variation NOT MEASURABLE.** Per T-1.3, pace_delta and tempo_variation are reported here and dropped — no diagnosis was attempted, per T-1.1/T-1.4.

### Step 4 — relationships (qualifying metrics only, n=195 units at the 200-involvement floor; pressure_delta n=188 due to some units lacking both under/not-under-pressure observations)

Correlation matrix (n=195, pressure_delta n=188):

| | median_time_on_ball | one_touch_share | pressure_delta |
|---|---|---|---|
| median_time_on_ball | 1.000 | -0.844 | -0.858 |
| one_touch_share | -0.844 | 1.000 | 0.667 |
| pressure_delta | -0.858 | 0.667 | 1.000 |

Correlation with public metrics (from `player_season_metrics.parquet`'s `completion_pct`/`progressive_passes_per_90`/`xa_per_90` only):

| | completion_pct | progressive_passes_per_90 | xa_per_90 |
|---|---|---|---|
| median_time_on_ball | 0.376 | 0.286 | -0.417 |
| one_touch_share | -0.508 | -0.349 | 0.551 |
| pressure_delta | -0.259 | -0.165 | 0.261 |

median_time_on_ball, top 10 of 195 (highest, longest time on ball): Manuel Akanji (2.60s, Euro2024, n=212), Nathan Aké (1.85s, WC2022, n=276), John Stones (1.83s, three tournaments, n=441 and n=373 — two separate competition-season units), Édmond Tapsoba (1.79s, Bundesliga23/24, n=1381), Marquinhos (1.78s, three comps, n=290), Aymeric Laporte (1.77s, three comps, n=373), Harry Maguire (1.77s, two comps, n=323), Raphaël Varane (1.76s, two comps, n=215), Aymeric Laporte (1.76s, three comps, n=580). Bottom 10 (shortest): Victor Boniface (0.08s, Bundesliga23/24, n=259), Antoine Griezmann (0.22s, WC2022+LaLiga, n=205), Sergio Busquets (0.42s, four comps, n=207), Amine Adli (0.48s, Bundesliga23/24, n=336), plus repeat Griezmann/Busquets/Wirtz/Pjanić/Rice units at 0.6-0.8s. All top-10 rows are Defenders; the bottom-10 rows are all Midfielders/Forwards.

one_touch_share, top 10 (highest one-touch share): Boniface (0.622), Griezmann (0.522), Busquets (0.493), Adli (0.482), Busquets (0.451), Florian Wirtz (0.442), Griezmann (0.429), Kylian Mbappé (0.426), Jonas Hofmann (0.426), Busquets (0.426) — the same forward/attacking-midfield names as median_time_on_ball's bottom, consistent with the -0.844 correlation. Bottom 10 (lowest one-touch share): Akanji (0.061), Joško Gvardiol (0.067), Dayot Upamecano (0.067), Andreas Christensen (0.068), Pau Torres (0.068), Toby Alderweireld (0.072), Varane (0.073), Rúben Dias (0.074), Jonathan Tah (0.074), Tapsoba (0.075) — all Defenders.

pressure_delta (median time-on-ball under pressure minus not-under-pressure; more negative = larger drop in time on ball when pressured), top 10 of 188 (least negative, smallest drop): Boniface (-0.117), Griezmann (-0.145), Kyle Walker (-0.440), Griezmann (-0.540), Busquets (-0.560), Jordi Alba (-0.567), Giovanni Di Lorenzo (-0.614), Adli (-0.624), Declan Rice (-0.644), Milan Škriniar (-0.652). Bottom 10 (most negative, largest drop): Akanji (-2.579), Aké (-1.866), Maguire (-1.804), Marquinhos (-1.795), Stones (-1.756), Kalidou Koulibaly (-1.654), David Alaba (-1.649), Varane (-1.644), Tapsoba (-1.621), Thiago Silva (-1.612) — again dominated by the same high-median_time_on_ball defenders, consistent with the -0.858 correlation (players who hold the ball longest under no pressure also show the largest absolute drop under pressure).

## 4. Deviations from the brief
None from `task-16-tempo.md` as executed. Three construction choices were left underspecified by the brief/plan and were resolved as documented in code comments (restated here per project rule 6, since they are not literal deviations but disclosed judgment calls a reader needs to interpret the numbers):
- **Split-unit granularity for reliability (Step 3).** median_time_on_ball/one_touch_share/pressure_delta are split at the pass level (each player's own time_on_ball rows); pace_delta/tempo_variation are split at the match level (each player's own contributing matches), matching how their point estimates are already clustered-by-match in Step 2. The plan does not specify split granularity for the rhythm metrics.
- **tempo_variation's referent.** Plan section 4 names two SD-based quantities under one heading. The gate list in section 5 names exactly five metrics including one "tempo_variation," so that name was read as the within-player SD of sequence pace (the rhythm quantity), and the SD of the player's own time_on_ball was computed as an ungated descriptive addendum (`sd_time_on_ball` in `tempo_metrics.parquet`) rather than a sixth gated metric.
- **Possession-sequence code path.** Task 11's possession-sequence definition (>=3 eligible passes, same team) is reused, but reimplemented directly in `src/tempo/possessions.py` against raw events rather than calling `task11_outcome_diagnostics.build_possessions()`, because that function's first step computes the frozen (now-withdrawn) per-pass Decision table. This is the same definition, not the same code path; it reproduced Task 11's own historical count exactly (20,042 sequences).

## 5. Problems and surprises
- No repair pass was needed. Both anticipated failure modes in Amendment T-1.2 (Carry sanity check failure, <40% coverage) did not occur on the first attempt — coverage was 72.6%, well above the 40% floor, and the Carry check passed cleanly (1.285s vs 0.000s median). This is a null result on the repair mechanism itself, not evidence the mechanism is unneeded: a different data slice could still trigger it.
- Two of the five preregistered metrics (pace_delta, tempo_variation) are NOT MEASURABLE at reliability 0.456 and 0.097 respectively — tempo_variation's reliability is close to zero, meaning a player's within-player pace variability computed from one random half of his sequences is essentially uncorrelated with the same quantity from the other half at n=195 units. If this were taken at face value as a stable player trait, it would be wrong; the module correctly refuses to interpret it. This undermines the "rhythm" side of the tempo module (plan section 4) specifically — only the "time on ball" and "composure" (pressure_delta, provisionally) sides survive the gate.
- pressure_delta is PROVISIONAL, not USABLE, at the preregistered 200-threshold gate (0.595, below the 0.70 USABLE cutoff) even though it clears 0.70 at threshold >=400 (n=60 units). Any use of pressure_delta as reported here should be read with that caveat; it was not promoted past PROVISIONAL because the gate is fixed at 200 per T-1.1, with no post-hoc threshold selection.
- The correlation structure across the three surviving metrics is very high in magnitude (|r| = 0.67-0.86 among the three; up to |r|=0.55 with public metrics), and all three leaderboards are dominated by the same names in inverted order (long-time-on-ball defenders vs. low-time-on-ball forwards/attacking-midfielders). This is consistent with all three metrics substantially reflecting the same underlying construct (positional role / how much time a player is afforded on the ball), rather than three independent tempo dimensions, though the module does not attempt to adjudicate that.
- `n_units_pace` (2,846) and `n_units_time_on_ball` (2,988) do not merge to 2,988+2,846; the merged file has 2,997 rows because 9 units appear in the pace set but not the time-on-ball set for that exact (player, competition, season) key (this arises from the outer merge and was not separately investigated, since pace_delta was dropped by the gate before Step 4).

## 6. Questions for the research lead
None. `task-16-tempo.md` and Amendment T-1 were unambiguous for every decision this task made; the three items in Section 4 are disclosed constructions, not open questions.

## 7. Files produced
- `src/tempo/__init__.py` — empty package marker. Committed, commit `ddb8da3`.
- `src/tempo/time_on_ball.py` — Step 1: time-on-ball construction, coverage/sanity/distribution reporting, repair-pass logic (unused this run). Committed, commit `ddb8da3`.
- `src/tempo/possessions.py` — independent reimplementation of Task 11's possession-sequence definition, used by Steps 2 and 3. Committed, commit `ddb8da3`.
- `src/tempo/metrics.py` — Step 2: per-player-season quantities (median_time_on_ball, IQR, one_touch_share, pressure_delta+CI, pace_delta+CI, tempo_variation). Committed, commit `ddb8da3`.
- `src/tempo/reliability.py` — Step 3: the gate (7-threshold split-half Spearman-Brown reliability sweep, classification). Committed, commit `ddb8da3`.
- `src/tempo/relationships.py` — Step 4: correlation matrix, public-metric correlations, top/bottom-20 leaderboards for qualifying metrics only. Committed, commit `ddb8da3`.
- `data/processed/tempo_time_on_ball.parquet` — per-pass time_on_ball table (209,775 rows after bounds). Not committed (data/).
- `data/processed/tempo_metrics.parquet` — per-player-season metrics table (2,997 rows). Not committed (data/).
- `data/tempo_step1_time_on_ball.json`, `data/tempo_step2_metrics.json`, `data/tempo_step3_reliability.json`, `data/tempo_step4_relationships.json` — step summaries (all four numbers in Section 3 come from these files). Not committed (data/).
- `docs/specs/analysis-plan-tempo.md` — preregistration, committed separately at Step 0, commit `aba4050`, prior to this task's execution.
- `docs/specs/task-16-tempo.md` — the executed task spec. Committed, commit `ddb8da3`.
- `docs/results/16-tempo.md` — this page. Committed, commit `ddb8da3`.

## 8. Confidence
High for Step 1 (deterministic construction, sanity check passed, coverage figure stated plainly) and for the two USABLE metrics (median_time_on_ball, one_touch_share — reliability >0.93 at the gate threshold and rising monotonically with more data, the expected pattern). Lower for pressure_delta (PROVISIONAL only) — treat any single-player pressure_delta value as noisy at n=200 involvements. The weakest link is tempo_variation and pace_delta, which are NOT MEASURABLE and are not used anywhere past Step 3; their unreliability may reflect a genuine absence of a stable within-player "rhythm" signal at this sample size, or a construction problem (e.g., possession-sequence pace being dominated by teammates' contributions rather than the focal player's own tempo) that this task's one-repair-pass, no-further-diagnosis rule (T-1.1) does not permit investigating further.
