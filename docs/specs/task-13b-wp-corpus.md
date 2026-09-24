# Task 13b — Win probability from the full open-data corpus

Governing document: docs/specs/analysis-plan-v3.md, Amendment v3-1.
Run this AFTER Task 13 is complete, or in a separate session. It must
not block or delay Task 13.

## Step 1 — Acquire
Download the StatsBomb open-data event corpus (github.com/hudl/open-data).
Prefer a shallow git clone; if that is impractical, fetch per-match via
statsbombpy. Store OUTSIDE the repo or under data/ (gitignored). Report
the method used, the wall-clock time, and the disk consumed.
Do not commit any raw data.

## Step 2 — Extract, streaming
Process match by match; never hold the corpus in memory. From each match
extract only: match_id, competition_id, season_id, competition gender,
season start year, final score, and the minute+period of every goal
(Shot with outcome Goal, plus Own Goal events, penalties included;
shootouts excluded).
Filter per v3-1.1: men's competitions, 2010-11 season onward, EXCLUDING
the 299 study matches. Report qualifying matches, total goals, and the
competitions represented.
Write the compact extract to data/processed/wp_corpus_goals.parquet.

## Step 3 — Build WP-corpus
Same Poisson construction as WP-299 (plan v3 section 2): per-minute
scoring rates for leading, level and trailing teams, then
WP(goal difference, minutes remaining), draws = half a win.
Report the estimated rates side by side with WP-299's.

## Step 4 — Select by calibration (v3-1.2)
Validate BOTH WP-299 and WP-corpus on the 299-match sample's states:
per-bucket n, predicted, observed, and Brier score for each.
Apply the gate and the lower-Brier rule. Report which is PRIMARY and
why, in one line.
If PRIMARY changes from WP-299 to WP-corpus, recompute EV_O3,
Decision_O3 and Execution_O3 for all options with the primary WP and
overwrite data/processed/options_o3.parquet, reporting that it was
rebuilt.

## HARD RULES
- Selection is on calibration only. Do not look at any leaderboard,
  player name, or referee result in this task.
- Report the comparison in full even if WP-299 wins.
- Streaming extraction only; report peak memory.
- No memory writes. Don't edit docs/JOURNAL.md.
- When finished, reply only that the task is done plus commit hashes.

## Output
docs/results/13b-wp-corpus.md (template). Commit per rule 9.
