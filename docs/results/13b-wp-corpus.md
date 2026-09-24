# Task 13b: Win probability from the full open-data corpus
Date: 2026-09-23
Status: PARTIAL

## 1. Headline
Neither WP-299 nor WP-corpus passes the calibration gate, under either the original rule or Amendment v3-2.3's match-clustered refinement — O3 stays UNVALIDATED and was not built. The corpus (2,090 additional matches, ~7x the study sample after excluding 41 matches for a team-naming data-quality issue) produced per-minute scoring rates for leading/level/trailing teams (0.01872/0.01334/0.01328) that are close to WP-299's own (0.01918/0.01368/0.01324) and do not meaningfully change the prediction at the specific bucket that fails (a one-goal lead ~5-10 minutes into the match: WP-corpus predicts 77.4% vs WP-299's 77.7%, both against an observed 62.6%, both still off by >14.8 percentage points). This is evidence against Amendment v3-2.2's sample-composition explanation for WP-299's failure — the same failure persists with a much larger, differently-composed corpus. O2's clipping fix (Amendment v3-2.1) was applied successfully: 0.30% of option-level predictions were negative before clipping, and Decision_O2's correlation with Decision_O1 is essentially unchanged from Task 13's own (unclipped) numbers (pass level r=0.824, player level r=0.856, n=171,618 passes / 2,097 players).

## 2. What I did
Governing spec: `docs/specs/analysis-plan-v3.md` (Amendments v3-1, v3-2) + `docs/specs/task-13b-wp-corpus.md` (revised). Reproducing command: `python src/decision_engine/task13b_wp_corpus.py` (resumable — if `data/processed/wp_corpus_goals.parquet` already exists it skips the network pull and starts from Step 3).

- **Step 0**: committed Amendment v3-2 + the revised `task-13b-wp-corpus.md` together (commit `addb407`), before any other work.
- **Step 1 (Acquire)**: used `statsbombpy` rather than a git clone — disclosed deviation, see Section 4. `sb.competitions()` filtered to `competition_gender=="male"` and season-start-year (parsed from `season_name`) `>= 2010`: 35 qualifying competition-seasons. `sb.matches()` for each gave 2,430 matches; excluding the 299 study matches left 2,131. Acquired in 9.9s.
- **Step 2 (Extract)**: for each of the 2,131 matches, `sb.events(match_id=...)` (one match's events in memory at a time; `pull_data.py`'s exact `requests_cache`-disable + 30s-timeout patch reused verbatim), extracting every goal's minute/period/elapsed-minutes/scoring-team via this project's own frozen goal-detection expression (`(type=="Shot") & (shot_outcome=="Goal") | (type=="Own Goal Against")`) and each match's own duration (max elapsed time over all non-shootout events). Wrote one compact parquet, `data/processed/wp_corpus_goals.parquet` (one row per goal, plus a sentinel null-goal row for any zero-goal match). Extraction: 2,131/2,131 matches, 0 failed, 5,923 goals, wall-clock 1,804.7s (30.1 min), peak RSS 0.46GB.
- **Data-quality finding, before Step 3 could run**: 41 of the 2,131 matches had a goal whose `scoring_team` (from `sb.events()`) matched neither the match's own `home_team` nor `away_team` (from `sb.matches()`) — a genuine team-naming inconsistency in StatsBomb's own data, the same class of finding `docs/results/10-validation.md` already documented for "Marseille" vs "Olympique de Marseille" in the 299-match study sample. Full detail in Section 5. These 41 matches were excluded from rate estimation (a match whose scorer can't be matched to home/away can't have its score-difference state reconstructed) — not silently renamed or guessed at. 2,090 matches were used.
- **Step 3 (Build WP-corpus)**: per-minute scoring rates for leading/level/trailing teams estimated from the 2,090 clean corpus matches' own goal times (same construction as Task 13's WP-299: segments between goals, state = the scorer's own goal-difference sign immediately before scoring, exposure in team-minutes). Grid built via `task13_objectives.build_wp_grid` (reused unmodified), same d_max=15 and m_max as Task 13's own WP-299 grid.
- **Step 3b (O2 clipping, v3-2.1)**: reloaded the O2 regressor and rebuilt the 1,237,611-row option context (`task13_objectives.build_option_context`, reused unmodified). New `compute_ev_o2_clipped`/`compute_realized_o2_clipped` clip the raw regressor prediction at 0 before the turnover branch is negated (a raw prediction represents accumulated xG for whichever team is attacking, which cannot be negative; the negated turnover value is expected to be <=0 and is not touched). Rewrote `data/processed/options_o2.parquet`.
- **Step 4 (Select; build O3 if a WP passes)**: validated both WP-299 and WP-corpus on the 299 study matches' own states (same states both times). Original gate: same rule as Task 13 (any bucket with n>=100 off by >10pp fails). Refined gate (v3-2.3): a bucket already failing the original 10pp threshold fails only if the match-clustered difference is significant at 95% (normal approximation, `|mean(per-match diff)/se| > 1.96`, `se = std(per-match diffs, ddof=1)/sqrt(n_matches)` — the brief specifies "significant at 95%" without naming an exact estimator; this is disclosed as this task's construction). Applied the documented selection procedure exactly. Since neither WP passed either gate, O3 was not built.
- **Sanity checks**: recomputed Decision_O1 fresh (`decompose.build_per_pass_table`, unmodified) and Decision_O2 using the Step 3b **clipped** values (per v3-2.1's "applied identically everywhere O2 is used" — this is the current, non-stale O1-vs-O2 comparison; Task 13's own results page is left untouched, per instruction). Pass- and player-level correlations and argmax disagreement via `task13_objectives.decision_correlations`/`argmax_disagreement`, reused unmodified.

## 3. Numbers

**Corpus scope**: 35 men's competition-seasons, 2010-11 onward: 1. Bundesliga 2015/16, African Cup of Nations 2023, Champions League 2010/11-2018/19 (9 finals), Copa America 2024, FIFA World Cup 2018, Indian Super League 2021/22, La Liga 2010/11-2019/20 (10 seasons), Ligue 1 2015/16, Premier League 2015/16, Serie A 2015/16 — plus the 8 competition-seasons the study sample itself is drawn from (fully excluded by match_id, contributing 0 additional matches). 2,131 qualifying matches; 2,090 used after the team-name-mismatch exclusion; 5,923 goals extracted (82 of them, across the 41 excluded matches, not used in rate estimation).

**WP-299 vs WP-corpus rates** (goals per team-minute):

| state | WP-299 (299 matches) | WP-corpus (2,090 matches) |
|---|---|---|
| leading | 0.019178 | 0.018723 |
| level | 0.013682 | 0.013341 |
| trailing | 0.013242 | 0.013276 |

**Gate verdicts** (validated on the 299 study matches' own 58,232 sampled states, both WP functions):

| function | original gate | Brier | refined gate |
|---|---|---|---|
| WP-299 | FAILED | 0.109322 | FAILED |
| WP-corpus | FAILED | 0.109293 | FAILED |

Both functions fail at the identical bucket: d=+-1, m_bin=85 (a one-goal lead with 80-85 minutes remaining, n=234 states / 62 matches):

| function | d | mean_predicted | mean_observed | abs_diff_pp | t-stat (clustered) |
|---|---|---|---|---|---|
| WP-299 | 1 | 0.7768 | 0.6261 | 15.07 | -2.156 |
| WP-299 | -1 | 0.2232 | 0.3739 | 15.07 | 2.156 |
| WP-corpus | 1 | 0.7742 | 0.6261 | 14.81 | -2.107 |
| WP-corpus | -1 | 0.2258 | 0.3739 | 14.81 | 2.107 |

Both `|t|` exceed the 1.96 critical value even after clustering by 62 matches — the refined gate does not rescue either function.

**O2 clipping** (Amendment v3-2.1): 0.30% of the 1,237,611 x 2 raw option-level predictions (success- and turnover-state, pooled) were negative before clipping. On the same held-out test set Task 13 used (n=225,460 rows, 60 matches), 1.75% of raw predictions were negative (identical to Task 13's own figure, as expected — same model, same split). Post-clipping calibration deciles:

| bin | n | mean_predicted | mean_actual |
|---|---|---|---|
| (-0.001, 0.00118] | 22546 | 0.00059 | 0.00144 |
| (0.00118, 0.00177] | 22549 | 0.00150 | 0.00178 |
| (0.00177, 0.00228] | 22543 | 0.00202 | 0.00223 |
| (0.00228, 0.00277] | 22546 | 0.00253 | 0.00222 |
| (0.00277, 0.00336] | 22546 | 0.00305 | 0.00290 |
| (0.00336, 0.00414] | 22546 | 0.00374 | 0.00296 |
| (0.00414, 0.00546] | 22546 | 0.00472 | 0.00461 |
| (0.00546, 0.00801] | 22546 | 0.00663 | 0.00569 |
| (0.00801, 0.0126] | 22546 | 0.01002 | 0.01045 |
| (0.0126, 2.002] | 22546 | 0.02346 | 0.02250 |

(The first bin's lower edge printing as slightly negative, "-0.001," is `pandas.qcut`'s own boundary-nudging behavior on a batch with a point mass of exact zeros from clipping, not an actual negative prediction surviving the clip.)

**O1 vs O2 (clipped) sanity checks**: n=171,618 passes, 2,097 players. Pass-level correlation r=0.8243. Player-level correlation r=0.8560. Argmax-EV disagreement: 28.86%. (Task 13's own unclipped numbers: 0.8241 / 0.8558 / 28.86% — clipping affected too small a share of values to move these.)

## 4. Deviations from the brief
1. **Acquisition used `statsbombpy`, not a git clone.** The brief prefers a shallow clone; `data/events/` in the open-data repo is one flat directory of JSON files for the entire corpus (all 80 competition-seasons, including women's and pre-2010), so a directory-level sparse-checkout would pull far more than the 2,131 matches needed. Per-match `statsbombpy` calls transfer strictly less data for this specific, small, named subset, and reuse this project's own already-flattened, already-proven goal-detection convention instead of a second raw-JSON parser. Confirmed via GitHub's own repo-size API before choosing this path (repo size ~7.4GB; our per-match target set is ~2,131 matches, not the whole corpus).
2. **The 41-match team-name-mismatch exclusion** (Section 5) is this task's own construction, since the brief doesn't anticipate it. Matches are excluded, not renamed/patched.
3. **The refined gate's significance test** (normal approximation, `|t|>1.96` on cluster means) is this task's own construction of "significant at 95%," since the brief and Amendment v3-2.3 specify the requirement but not an estimator.
4. **O2's realized-value (Execution) computation was also given the clipping fix** (`compute_realized_o2_clipped`), not just the option-level EV (`compute_ev_o2_clipped`) — the brief's Step 3b text names `options_o2.parquet` and calibration explicitly, but "applied identically everywhere O2 is used" (v3-2.1) would be violated if Execution_O2 used an unclipped value function while Decision_O2/EV_O2 used a clipped one.
5. **Task 13's own O1-vs-O2 correlation numbers are superseded, not edited.** This page reports the current (clipped) O1-vs-O2 correlations; `docs/results/13-objectives.md` is left exactly as it was, per instruction.

## 5. Problems and surprises
1. **Team-name mismatch, 41 matches (data quality).** `sb.events()`'s `team` field uses a short or former club name that differs from `sb.matches()`'s `home_team`/`away_team` for two competition-seasons: Ligue 1 2015/16 ("Marseille" for "Olympique de Marseille", "Caen" for "Stade Malherbe Caen" — 14 matches) and Indian Super League 2021/22 ("Hyderabad" for presumably "Hyderabad FC" — not present in either home/away field at all in these rows, and "ATK Mohun Bagan" for "Mohun Bagan Super Giant", a genuine club rebrand StatsBomb's events data didn't backfill — 27 matches). This is the same underlying class of StatsBomb data inconsistency Task 10 already found in "Marseille," now appearing at corpus scale (41/2,131 = 1.9% of qualifying matches). Excluded from rate estimation rather than name-mapped, since a mapping would be an invented data-cleaning rule.
2. **The corpus does not fix WP-299's calibration failure.** This is the substantive finding of this task: a ~7x-larger, differently-composed sample produces nearly the same leading/level/trailing rates and the identical failing bucket, at nearly the identical magnitude (15.07pp vs 14.81pp). Amendment v3-2.2's diagnosis — that WP-299's failure reflects the study sample's own composition (a few possession-dominant teams) — is not supported by this result. The more likely explanation, not tested here, is that the one-minute-discretized, memoryless (state-only, no time-since-goal or minute-of-match interaction) Markov construction itself is structurally too coarse for an early-match single-goal lead, regardless of which sample estimates its rates.
3. Nothing else was found broken; both self-checks this task depends on (Task 13's own, already verified) and the new team-name-mismatch check ran and behaved as expected.

## 6. Questions for the research lead
1. Given the corpus does not resolve the gate failure, is a corpus-scale WP effort worth pursuing further (e.g., a finer state space than leading/level/trailing, or a non-memoryless construction), or does this result mean O3 should be abandoned under the current construction? I am not proposing a specific fix — this is a question about direction, not a request to patch WP now.
2. Is "Hyderabad" (Indian Super League 2021/22) actually "Hyderabad FC," and should team-name mappings for well-understood 1:1 renames (this one, "Marseille," "Caen," "ATK Mohun Bagan") be pre-registered as a standing data-cleaning rule for future corpus work, rather than an exclusion decided fresh each time? This is a real recurring cost (41 matches lost here) that a documented mapping could recover, but it is a methodology decision, not mine to make unilaterally.
3. Task 13's own results page (`docs/results/13-objectives.md`) still reports the unclipped O1-vs-O2 correlation numbers, which are now superseded by this page's clipped numbers (a negligible difference, 0.8241->0.8243 pass level, but a real one). Should Task 13's page be left as the historical record it was at the time (as I've done here), or does the paper's own accounting need a note explicitly pointing from one to the other?

## 7. Files produced
- `src/decision_engine/task13b_wp_corpus.py` — this task's full implementation. Committed together with the results page, commit `f45faae`.
- `docs/specs/analysis-plan-v3.md` (Amendment v3-2), `docs/specs/task-13b-wp-corpus.md` (revised) — committed at Step 0, commit `addb407`.
- `docs/results/13b-wp-corpus.md` — this page. Committed with the script, commit `f45faae`.
- `data/processed/wp_corpus_goals.parquet` — compact per-goal corpus extract (6,074 rows: 5,923 goals + sentinel rows for zero-goal matches, across 2,131 matches). Not committed (data/).
- `data/processed/options_o2.parquet` — **rewritten** with clipped v_success/v_turnover/ev (Task 13's own version is overwritten; the pre-clipping version is not separately retained). Not committed.
- `data/processed/options_o3.parquet` — **not written** (neither WP function passed either gate).
- `data/task13b_wp_corpus.json` — full machine-readable summary (every number in this page traces back to it). Not committed.

## 8. Confidence
The extraction (2,131/2,131 matches, 0 failures) and the gate machinery (reused, unmodified, from Task 13's own already-validated functions) are as trustworthy as Task 13's own results. The team-name-mismatch exclusion is a conservative, disclosed choice, not a guess — it costs 41 matches out of 2,131 (1.9%), a small fraction, so its effect on the estimated rates is limited regardless of which way it's eventually resolved. The central finding — that a much larger corpus does not fix WP-299's calibration failure — rests on a single held-out validation population (the 299 study matches' own states, 58,232 samples), the same one Task 13 used; it says the corpus doesn't fix THIS test, not that no WP function ever could. The weakest link is the refined (match-clustered) gate's significance test, a normal approximation on 62 clusters per bucket — a small-sample t-correction might shift the exact t-statistic slightly, but both t-stats (2.11-2.16) are far enough past 1.96 that this would not plausibly flip either verdict.
