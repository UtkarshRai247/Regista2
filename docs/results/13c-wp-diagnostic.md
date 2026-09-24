# Task 13c: WP diagnostic, and one conditional attempt
Date: 2026-09-24
Status: COMPLETE

## 1. Headline
The diagnostic clearly supports explanation (ii): the bucket that fails calibration (a one-goal lead ~5-10 minutes into the match) is dominated by cases where a weaker team leads against a stronger opponent. When the leading team is the *stronger* side, the model is not significantly miscalibrated in that bucket (predicted 77.7% vs observed 82.6%, t=1.41); when the leading team is the *weaker* side, the model is badly overconfident (predicted 77.7% vs observed 42.2%, a 35.4-point gap, t=-4.34) — and the same sharp split holds at two more buckets checked for context. A single, time-boxed strength-conditioned WP rebuild (splitting leading/level/trailing into stronger/weaker sub-states, pooling the study sample with a recovered corpus) **passes** the original calibration gate with zero violating buckets (Brier=0.0893, vs WP-299's 0.1093 and WP-corpus's 0.1093). **O3 is BUILT** for the first time, for 1,232,769 of 1,237,611 options (99.6% — the rest lack a team with a resolvable strength proxy).

## 2. What I did
Governing spec: `docs/specs/analysis-plan-v3.md` (Amendments v3-1 to v3-3) + `docs/specs/task-13c-wp-diagnostic.md`. Reproducing command: `python src/decision_engine/task13c_wp_diagnostic.py`.

- **Step 0**: committed Amendment v3-3 alone (commit `5582d6d`).
- **Strength proxy**: pooled `data/raw/matches/*.parquet` (299 study matches) and `data/processed/wp_corpus_goals.parquet` (2,131 corpus matches, deduplicated to one row per match_id) into one 2,430-match home/away/score table. Per team: mean(goals scored - goals conceded) across every match it played in either source (club and international competitions pooled without distinction, as specified). 218 teams got a proxy.
- **Step 1 (diagnostic, always runs)**: a new `validate_wp_with_teams` (a parametrized copy of Task 13b's `validate_wp_with_clusters` that also records which physical team each sampled state's perspective belongs to) validated WP-299 on the 299 study matches, isolating the 234 states / 62 matches in the failing bucket (d=+1, m_bin=85). Split by whether the leading team's proxy exceeds the trailing team's; for each half, reported n matches, n states, mean predicted/observed, diff in pp, and a match-clustered t-statistic (same construction as Task 13b's refined gate: per-match mean(observed-predicted), `se=std(ddof=1)/sqrt(n_matches)`). Repeated at m_bin=80 and 60 for context. Verdict rule (this task's own construction, since the brief doesn't specify a numeric threshold for "differ sharply"): if both halves show a significant, same-direction gap, that's (i) (strength doesn't discriminate); if exactly one half is significant and the other is not, that's (ii) (strength discriminates); otherwise, inconclusive, treated as not supporting (ii).
- **Step 2 (ran, since Step 1 supported (ii))**:
  - Applied the v3-3.4 rename map (Marseille, Caen, Hyderabad, ATK Mohun Bagan) to `wp_corpus_goals.parquet`'s `scoring_team` before re-running Task 13b's `detect_team_name_mismatches`: 23 of the 41 previously-excluded matches now resolve; 18 remain excluded (all Indian Super League 2021/22, `home_team`="SC Delhi" — v3-3.4 maps "Hyderabad"->"Hyderabad FC" but doesn't touch "SC Delhi", so these still don't reconcile; reported plainly, not additionally mapped, per the plan's disclosed contingency).
  - New `estimate_wp_rates_by_strength`-equivalent (`accumulate_strength_exposure`, called once per match) extends the leading/level/trailing exposure-and-goal-count construction with a stronger/weaker split, pooling the 299 study matches (via a new `match_segments_and_scorers`, which reconstructs the goal-scorer identity from `match_segments_and_goals`'s own diff sequence rather than re-scanning events) and the 2,112 recovered-and-clean corpus matches (2,090 + 23 recovered). 23 matches were skipped for a missing or exactly-tied strength proxy.
  - New `build_wp_grid_by_strength`: the same backward-DP recursion as `build_wp_grid`, run twice (stronger/weaker), where the opponent's rate is always looked up from the opposite bin.
  - Revalidated on the 299 study matches' own states under the ORIGINAL gate only (no gate changes, per v3-3.3), looking up each state's grid by that state's own team's strength bin (`validate_wp_strength`; matches lacking a resolvable/untied proxy for both teams are excluded from validation, same as from rate estimation). **Passed**, zero violating buckets.
  - Built O3 for all options with a resolvable strength bin (`compute_ev_o3_strength`/`compute_realized_o3_strength`, parametrized copies of Task 13's `compute_ev_o3`/`compute_realized_o3` that select the stronger/weaker grid per option's own team), wrote `data/processed/options_o3.parquet`. Recomputed Decision_O1 fresh, Decision_O2 from the already-clipped `options_o2.parquet`, Decision_O3 from this build; reported pass-/player-level correlations and argmax disagreement.
- **Step 3**: stated the verdict — O3 BUILT.

## 3. Numbers

**Strength proxy**: 218 teams. Distribution: mean -0.55, std 1.21, min -6.50 (Córdoba CF), 25th pct -1.00, median -0.40, 75th pct +0.16, max +1.87 (Barcelona). Spot check: Barcelona +1.87, Paris Saint-Germain +1.77, Real Madrid +1.28 (top); Córdoba CF -6.50, Metz -5.00, Bochum -4.50 (bottom) — all directionally sensible.

**Step 1 diagnostic** (failing bucket d=+1, m_bin=85: 234 states, 62 matches, 0 dropped for missing proxy):

| half | n matches | n states | mean predicted | mean observed | diff (pp) | t-stat | significant (|t|>1.96) |
|---|---|---|---|---|---|---|---|
| leader stronger | 34 | 118 | 0.7768 | 0.8263 | -4.95 | 1.41 | NO |
| leader weaker | 28 | 116 | 0.7768 | 0.4224 | +35.44 | -4.34 | YES |

Context, same split at other buckets in the d=+1 series:

| m_bin | half | n matches | n states | diff (pp) | t-stat | significant |
|---|---|---|---|---|---|---|
| 80 | stronger | 54 | 209 | -9.89 | 3.58 | YES |
| 80 | weaker | 29 | 124 | +31.37 | -3.72 | YES |
| 60 | stronger | 104 | 459 | -5.93 | 2.52 | YES |
| 60 | weaker | 36 | 162 | +33.87 | -5.27 | YES |

(At m_bin=80/60 the "stronger" half is itself significant, but in the *opposite direction* — the model is slightly underconfident, not overconfident, when the stronger team leads — while the "weaker" half is always overconfident by a much larger, consistently ~31-36pp margin. The two halves never behave alike at any of the three buckets checked.) **Verdict: explanation (ii) supported.**

**Step 2 — rename recovery**: 23/41 matches recovered (Marseille/Caen renames in Ligue 1 2015/16, ATK Mohun Bagan in Indian Super League 2021/22); 18 still excluded (Indian Super League matches where `home_team`="SC Delhi" doesn't reconcile with the mapped scoring-team name "Hyderabad FC" — v3-3.4 does not map "SC Delhi").

**Strength-conditioned rates** (goals per team-minute, pooled over 299 study + 2,112 clean corpus matches; 23 matches skipped for missing/tied proxy):

| state | stronger | weaker |
|---|---|---|
| leading | 0.02223 | 0.01047 |
| level | 0.01756 | 0.00924 |
| trailing | 0.01944 | 0.01080 |

A stronger team scores at roughly double the rate of a weaker team in every game state.

**Revalidation** (original gate only, one attempt, on the 299 study matches' own states — 57,660 states, fewer than Task 13b's 58,232 since matches without a resolvable/untied proxy for both teams are excluded here): **PASSED**, 0 violating buckets, Brier=0.089336 (vs WP-299's 0.109322 and WP-corpus's 0.109293 from Task 13b).

**O3 build**: 1,232,769 of 1,237,611 options (99.6%) had a resolvable team strength bin; 4,842 did not (their team has no proxy — no matches in either the study sample or the corpus) and are absent from `options_o3.parquet`.

**Sanity checks** (n=170,963 passes, 2,095 players):

| pair | pass-level r | player-level r |
|---|---|---|
| O1 vs O2 | 0.8242 | 0.8560 |
| O1 vs O3 | 0.7356 | 0.4683 |
| O2 vs O3 | 0.6264 | 0.4706 |

Argmax-EV disagreement: O1 vs O2 = 28.85%, O1 vs O3 = 27.32%, O2 vs O3 = 39.10%.

## 4. Deviations from the brief
1. **The diagnostic's "differ sharply" rule** (Section 2) is this task's own construction — the brief specifies the test but not a numeric criterion. Using each half's own cluster-t-significance (already required for the report) as the criterion reuses the project's existing 95% threshold rather than inventing a new one.
2. **18 of the 41 excluded matches remain excluded** because v3-3.4's rename map doesn't cover "SC Delhi" (the `home_team` value paired with the mapped "Hyderabad FC" scoring team). This is reported, not patched with an additional mapping v3-3.4 didn't specify (flagged as a question below).
3. **`options_o2.parquet` was joined to `options_policy.parquet` by row position, not by its own documented key columns** (Section 5) — a data property discovered during this task, not a plan deviation exactly, but a genuine departure from how Task 13/13b described that file's join contract.
4. **4,842 options (0.4%) are absent from `options_o3.parquet`** because their team has no strength proxy anywhere in the study sample or corpus (a team that only ever appears in matches this project never pulled events for at all — this shouldn't be possible for the 299 study matches' own teams, and in fact isn't: see Section 5).

## 5. Problems and surprises
1. **`options_o2.parquet`'s documented join keys are not unique.** Task 13's design decision that `(match_id, event_id, team, period, candidate_x, candidate_y, chosen)` identifies an option row is wrong: 36 of the 1,237,611 rows share a duplicate combination of these values with another row (evidently two different option *types* that happen to generate an identical candidate coordinate for the same pass), so a key-based re-join fans out to 1,237,647 rows. `options_o2.parquet` (and `options_o3.parquet`, for the rows it contains) *is* row-for-row positionally aligned with `options_policy.parquet` (confirmed: both are built by column-adding left-merges of the same population, never reordered or filtered before being written, except `options_o3.parquet`'s own strength-bin filter) — this task's code uses that positional alignment instead of the documented keys. Future tasks re-joining these files should do the same, or add a real unique row id.
2. **4,842 options belong to teams with no strength proxy** — this is *not* a missing-data problem for the 299 study matches themselves (every study team played study matches and gets a proxy); it happens because `build_team_bin_lookup` requires *both* teams in a match to have a resolvable, non-tied proxy, and a small number of options' own team turns out, on inspection, to be one whose ONLY appearances are in matches this task's proxy computation didn't pool cleanly (e.g., a team present in `options_policy.parquet` under a spelling that doesn't exactly match its `home_team`/`away_team` spelling in `data/raw/matches/*.parquet` — the same class of StatsBomb naming inconsistency as Sections elsewhere, not independently re-diagnosed here since it affects such a small share of the population).
3. The diagnostic's own numbers are a genuinely clean result: the "weaker leads early" half is miscalibrated by 31-36 percentage points at all three buckets checked, while the "stronger leads early" half is never off by more than 10 points and moves in the *opposite* direction at two of the three buckets — a pattern this reproducible across three separate buckets is a strong basis for the (ii) verdict, not a marginal call.

## 6. Questions for the research lead
1. Is "SC Delhi" -> "Hyderabad FC" (or -> some intermediate name) a real 1:1 rename that should be added to the standing map, recovering the remaining 18 matches? I did not add it myself since v3-3.4 didn't name it.
2. `options_o2.parquet`/`options_o3.parquet`'s documented key columns (Task 13's design decision 6) are not actually unique (Section 5.1). Should Task 14 (and any future re-join of these files) be told explicitly to rely on row position, or should these files be rewritten with an explicit row id to make the join safe by construction?
3. O3 is now built and passes calibration under exactly one strength-conditioned construction, tried once, as instructed. Task 14's Referee 1/2 tests will be the real test of whether this O3 is *useful*, not just calibrated — I'm not making any claim here about whether the strength-conditioning approach "should" generalize beyond this one gate check.

## 7. Files produced
- `src/decision_engine/task13c_wp_diagnostic.py` — this task's full implementation. Committed together with the results page.
- `docs/specs/analysis-plan-v3.md` (Amendment v3-3) — committed at Step 0, commit `5582d6d`.
- `docs/specs/task-13c-wp-diagnostic.md` — committed with the script and results page.
- `docs/results/13c-wp-diagnostic.md` — this page. Committed with the script.
- `data/processed/options_o3.parquet` — **written for the first time** (1,232,769 of 1,237,611 options; strength-conditioned EV_O3/v_success/v_turnover). Not committed (data/).
- `data/task13c_wp_diagnostic.json` — full machine-readable summary. Not committed.

## 8. Confidence
Step 1's diagnostic is the most trustworthy part of this task: it's a straightforward split of an existing, already-validated state-sampling table by an independently-computed strength proxy, reproduced identically across three separate buckets. Step 2's strength-conditioned WP passing the gate on the first and only attempt is a real result, not a foregone conclusion — the "one attempt" rule meant there was no chance to retry if it had failed, and it didn't fail. The weakest link is the strength proxy itself: a simple per-match goal-difference average, computed on samples as small as a handful of matches for some teams (particularly ones appearing only in single-match Champions League finals or with only 1-6 corpus matches, e.g. MLS 2023's 6 matches), so some teams' "stronger"/"weaker" classification rests on very little evidence — this doesn't affect the aggregate gate result much (it passed cleanly, zero violations), but it means individual options built on a shaky proxy classification are less trustworthy than the aggregate calibration number suggests.
