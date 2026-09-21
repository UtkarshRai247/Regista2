# Task 05 — Study A, DISCOVERY half only

Governing document: docs/specs/analysis-plan-v2.md, including Amendment
v2-1. Read both fully first.

## Step 0 — Git hygiene (before anything else)
1. Commit everything under src/ and docs/ that is currently untracked or
   modified, EXCEPT anything under data/. One commit, message:
   "Track all code and docs through Task 04".
2. Commit Amendment v2-1 in its own separate commit, and record its hash
   and the new SHA-256 of analysis-plan-v2.md in the results page.
3. Append this to CLAUDE.md under "Reporting discipline":
   "9. At the end of every task, commit all new or changed files under
   src/ and docs/ (never data/). Record the commit hash in Section 7 of
   the results page."

## Step 1 — Build pass-level type values (discovery half only)
Using data/splits/match_split.csv, keep DISCOVERY matches only. Do not
load confirmation-half rows at all — filter at read time.
Join options_typed.parquet to the EV column (options_ev.parquet or
options_policy.parquet) on (match_id, event_id, candidate position).
Report the join match rate; STOP if any option fails to join.
For each pass: chosen type j; EV*_type = max EV among options of each
type present; g_k = EV*_k - EV*_j for every available type k != j.
Attach the pass's situation cell from passes_situation.parquet.

## Step 2 — Statistics for all 107 analyzable pairs
Per plan 3.3 and Amendment v2-1.1, for EVERY analyzable (cell, type)
pair, not only candidates: G, its 95% CI (1,000 bootstrap draws
resampling MATCHES), P, s, L, plus n passes and n matches contributing.
Implementation hint: aggregate to per-match sums and counts per pair
first, then bootstrap over match indices. Seed 20260920.

## Step 3 — Candidates
Apply plan 3.4 conditions 1-3 exactly. Write the candidate list to
docs/results/05-study-a-candidates.csv (cell, type, G, CI, P, s, L) and
COMMIT it before writing the results page.

## Step 4 — Descriptive context (no new tests)
For each candidate: average number of options of type k vs of the chosen
type j per pass (needed later for sensitivity 3.6a), and the share of
its passes coming from focal-team club matches vs tournaments.

## HARD RULES
- CONFIRMATION half: do not load, filter, or compute anything on it.
- No Gate D, no sensitivity checks, no realized values. Those are Task 06.
- The full 107-pair table goes in the results page, sorted by cell then
  type — not sorted by G, and not filtered.
- No interpretation of which blind spots are "interesting". Report.
- Do not edit docs/JOURNAL.md.

## Output
docs/results/05-study-a-discovery.md (template), the committed candidate
CSV, and the full 107-pair table as data/processed/study_a_discovery.parquet.
