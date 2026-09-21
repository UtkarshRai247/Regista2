# Task 04: Situation context join

Date: 2026-09-20
Status: COMPLETE

## Per-section checklist (per brief docs/specs/task-04-situation-context.md)
- Step 0 (freeze preregistration): COMPLETE
- Step 1 (situation context join, 171,618 passes): COMPLETE
- Step 2 (option typing): COMPLETE
- Step 3 (discovery/confirmation split): COMPLETE
- Step 4 (feasibility counts): COMPLETE
- Hard rules (counts only, confirmation half untouched, no retraining): COMPLETE

## 1. Headline
All four steps ran clean: the 171,618-pass population, option typing,
and match split reproduce exactly what the brief specified, and the
score-reconstruction validation gate passed with zero mismatches across
all 299 matches. 107 of 162 (cell, option-type) pairs clear the ≥100-chosen
analyzability floor in the discovery half, so Study A has a workable
starting set. Two field definitions the brief left open (channel
boundaries, position group) were implemented with a stated default and
are flagged below for the research lead, not decided silently.

## 2. What I did
Reproduce with: `.venv/bin/python src/decision_engine/task04_situation_context.py`
(after Step 0's git commit, done separately — see below).

- **Step 0**: committed `docs/specs/analysis-plan-v2.md` and
  `docs/specs/task-04-situation-context.md` only (commit
  `e1ee6aca24ea8cbc3d8e875d6887388ce34eee46`), hashed the preregistration
  (`sha256(analysis-plan-v2.md) = 7ff2fd23dc64cabfee14d64b4ff6d126313e306b8bb7e1abb04b8e982ab5fcf2`),
  appended D-012/D-013/D-014 to `docs/DECISIONS.md` verbatim as given in
  the brief. Did not touch `docs/JOURNAL.md`.
- **Step 1**: took the 171,618 distinct `(match_id, event_id)` pairs
  already in `data/processed/options_scored.parquet` (Task 01's matched
  population) as the pass base — this guarantees exact reuse of Task 01's
  eligibility definition rather than re-deriving it. For each of the 299
  matches: computed `team_period_directions` and normalized passer
  coordinates via `pitch_direction.normalize_xy` (options_scored.parquet
  stores RAW coordinates — `options.py` never normalizes, confirmed by
  reading it); joined `under_pressure` (filled `NaN`→`False`), `period`,
  `minute`, `second`, `play_pattern` from the raw event; assigned passer
  zone (thirds on normalized x) and channel (thirds on normalized y);
  counted total visible players from the freeze frame (`len(frame)`,
  same definition `options.py` uses for its own ≥6 eligibility check);
  reconstructed cumulative score per team (ordered by the events' strictly
  monotonic `index`, excluding `period == 5` shootouts, crediting `Shot`+
  `shot_outcome=="Goal"` and `"Own Goal Against"` events — the same
  convention `decompose.py`'s `compute_realized_values` already uses
  elsewhere in this codebase, reused here for consistency) to get
  leading/level/trailing at the moment of each pass.
- **Validation gate**: compared every match's reconstructed final score
  to `home_score`/`away_score` from `data/raw/matches/*.parquet`, for
  all 299 matches (not just the 292 that have an eligible pass in
  `options_scored.parquet` — see Section 4). Zero mismatches, so
  Steps 2-4 proceeded.
- **Step 2**: read `options_scored.parquet` and immediately dropped its
  `p_success` column on load (see Section 4 — never read
  `options_ev.parquet`/`options_policy.parquet`). Confirmed the distance
  unit empirically: penalty-kick locations (`shot_type=="Penalty"`)
  sit a median 12.00 units from the nearer goal line across 195
  penalties (mean 11.97, sd 0.11) — matches Law 1's 12-yard penalty mark,
  so 1 StatsBomb unit = 1 yard (0.9144m). Converted 15m/30m to 16.404/
  32.808 units. Recomputed bearing on normalized coordinates (reusing
  `options.bearing`/`circular_diff`) relative to straight-at-goal (0°)
  for direction typing; reused the existing `distance` column as-is for
  length typing (normalization is an isometry, so distance is identical
  computed on raw or normalized coordinates).
- **Step 3**: split all 299 matches 50/50 stratified by competition-season,
  seed 20260920, via `numpy.random.default_rng` applied per stratum in a
  fixed (sorted) order for reproducibility. Committed
  `data/splits/match_split.csv` (commit `a9021eb`), after adding a
  `.gitignore` exception for it (the existing `data/*` ignore pattern
  would otherwise have silently dropped it, same as everything else
  under `data/`).
- **Step 4**: computed all feasibility counts from the discovery half
  (cells, pairs) and the full sample (Study B contexts, club structure,
  visible-player distribution), as specified.
- **Compliance check**: asserted neither output parquet file contains
  `ev`, `p_success`, `policy_probability`, `v_success`, `v_turnover`, or
  `policy_raw_score` — confirmed clean.

## 3. Numbers

**Step 1**
- Matched passes: **171,618** — exact match to the expected count (n=171,618).
- Score validation: **0 mismatches / 299 matches**.
- Zone: defensive 36,901 (21.5%), middle 97,365 (56.7%), final 37,352 (21.8%). (n=171,618)
- Channel: left 58,912 (34.3%), centre 54,834 (31.9%), right 57,872 (33.7%). (n=171,618)
- Game state: level 83,046 (48.4%), leading 45,948 (26.8%), trailing 42,624 (24.8%). (n=171,618)
- Under pressure: confirmed `True`/`NaN` only (no literal `False`) across
  the raw events, so `NaN → False` is the correct fill, as the brief
  expected.
- Visible players per frame: median **17**, mean 16.75 (sd 3.03), range 6-22. (n=171,618)

**Step 2**
- Unit evidence: median penalty-spot distance to goal line = 12.00
  units (n=195 penalties, mean 11.97, sd 0.11) → 1 unit = 1 yard.
  Converted thresholds: short < 16.404 units, medium 16.404-32.808,
  long ≥ 32.808.
- Option type shares (n=1,237,611 option rows): lateral_medium 28.37%,
  lateral_long 19.55%, lateral_short 16.26%, forward_medium 8.62%,
  backward_medium 8.29%, forward_short 7.78%, backward_short 7.75%,
  forward_long 1.77%, backward_long 1.62%.

**Step 3**
- 299 matches split: 148 discovery / 151 confirmation.
- Per competition-season (discovery/confirmation): Ligue1 21/22 13/13,
  Ligue1 22/23 16/16, Bundesliga 23/24 17/17, La Liga 20/21 17/18,
  World Cup 2022 32/32, MLS 2023 3/3, Euro 2020 25/26, Euro 2024 25/26.

**Step 4**
- 18/18 situation cells populated in the discovery half (none empty),
  ranging from 615 passes (final third, under pressure, leading) to
  21,787 (middle third, no pressure, level).
- **107 of 162** (cell, option-type) pairs are analyzable (≥100 chosen
  in the discovery half).
- Study B (full sample, 20-pass floor per player x team x
  competition-season context): **345** players with 2+ contexts; **132**
  club-plus-international movers; **119** of those movers (90.2%) have
  the same position group in at least one club and one international
  context (see Section 4 for how "same" was operationalized).
- Club competition structure: World Cup 2022 and both Euros have no
  focal team (max team-match-count well below total matches — 7 of 64,
  7 of 51, 7 of 51 respectively). Ligue 1 21/22, Ligue 1 22/23,
  Bundesliga 23/24, La Liga 20/21, and MLS 2023 are each built around
  one focal team appearing in every match with eligible passes: Paris
  Saint-Germain (26/26 and 31/31 matches), Bayer Leverkusen (31/31),
  Barcelona (35/35), and Inter Miami (3/3) respectively.

## 4. Deviations from the brief

1. **`options_scored.parquet` was not value-quantity-free as assumed.**
   It carries `p_success` (Task 01 Step 2's output) alongside distance/
   geometry columns, though never `ev`/`policy_probability`. This script
   drops `p_success` immediately on load and never reads it again; the
   compliance assertion at the end confirms neither output file carries
   it (or `ev`, `v_success`, `v_turnover`, `policy_raw_score`,
   `policy_probability`). Flagging because the plan assumed this file
   was already value-free — it wasn't quite, and the guard against it
   is a design choice, not something the brief specified.
2. **Channel boundary (left/centre/right)** is not defined anywhere in
   `analysis-plan-v2.md` or the existing codebase. Used equal thirds of
   normalized pitch width (0-26.67 / 26.67-53.33 / 53.33-80), symmetric
   with how the plan splits the passer zone into thirds along x. This
   is a secondary/descriptive field only (never used to define a
   primary cell or gate per section 2 of the plan), so it cannot affect
   any Study A/B/C result — see Section 6.
3. **Position group** (GK/Defender/Midfielder/Forward) is not defined
   anywhere in the plan, and is needed only for the Step 4 Study B
   "movers with the same position group" count. Bucketed from
   StatsBomb's `position` name substrings (`"Back"` → Defender,
   `"Midfield"` → Midfielder, else → Forward, `"Goalkeeper"` → GK). See
   Section 6.
4. **"Same position group in both" comparison logic**: a mover can have
   more than one club context and/or more than one international
   context. Compared the *set* of position groups across all of a
   mover's club contexts against the set across all their international
   contexts, counting a match if the sets intersect at all. Not
   specified by the brief; purely descriptive, does not affect any
   primary result.
5. **Score-validation scope**: the brief says the reconstructed score
   must match "every one of the 299 matches." 7 of the 299 matches
   contribute zero eligible/matched passes to `options_scored.parquet`
   (Task 01 attrition, not new to this task). I validated all 299
   matches regardless (using the raw event/match files directly, not
   gated on whether a match appears in `options_scored.parquet`), per
   the literal brief wording, rather than only the 292 that produce a
   pass in the output.

## 5. Problems and surprises

- **MLS 2023's already-small sample halves further once eligibility is
  applied.** The original Task 01 sample has 6 MLS 2023 matches, but 3
  of them (all involving Inter Miami: vs. Toronto FC, vs. Cincinnati,
  vs. Charlotte) contribute **zero** eligible/matched passes — meaning
  the Task 04 situation dataset and Step 4's club-competition-structure
  numbers for MLS rest on only 3 matches, all Inter Miami. This isn't a
  new bug (it's inherited from Task 01's angle-matching/frame-visibility
  filters), but it's a sharper concentration than the raw "6 matches"
  figure suggests, and worth keeping in mind for any MLS-specific
  Study A/B/C reporting.
- Two of Bayer Leverkusen's Bundesliga 23/24 matches and one PSG Ligue 1
  22/23 match also contribute zero eligible passes (7 total across the
  sample) — same underlying cause, smaller effect elsewhere.
- Nothing else was missing, broken, or malformed: `under_pressure`,
  `play_pattern`, `minute`/`second`, `shot_outcome`, and the own-goal
  event types were all present and behaved as expected on inspection.

## 6. Questions for the research lead

1. Is the equal-thirds-of-width channel boundary (0-26.67/26.67-53.33/
   53.33-80 on normalized y) the right default, or is there a preferred
   boundary (e.g., aligned to the width of the penalty area/six-yard
   box instead of raw thirds)? This only affects a secondary/descriptive
   field, never a primary cell.
2. Is GK/Defender/Midfielder/Forward (bucketed from StatsBomb position
   name substrings) the right position-group granularity for the Study
   B "same position group" mover count, or should it be finer (e.g.
   separating out wing-backs, or defensive vs. attacking midfielders)?
   This only affects one descriptive count in Step 4.
3. MLS 2023's eligible-pass sample is 3 matches, all Inter Miami (see
   Section 5). Is this still usable as its own team context for Study
   B, or should it be treated as too thin to include?

## 7. Files produced
- `data/processed/passes_situation.parquet` — 171,618 rows, one per
  matched pass, with situation context (zone, channel, pressure, game
  state, score_diff, visible-player count, team context, play_pattern,
  minute/second). Gitignored (derived, not committed).
- `data/processed/options_typed.parquet` — 1,237,611 rows, one per
  option/candidate, with normalized coordinates, `direction_type`,
  `length_type`, `option_type`, `chosen`, `pass_complete`, and the
  existing opponent-proximity/lane fields. Gitignored.
- `data/splits/match_split.csv` — 299 rows (`match_id`, `competition_id`,
  `season_id`, `half`). Committed (commit `a9021eb`).
- `data/task04_situation_context.json` — full run summary (unit
  evidence, option-type shares, split counts, feasibility counts,
  club-competition-structure detail). Gitignored, for reference.
- `src/decision_engine/task04_situation_context.py` — the script that
  produces all of the above. Not committed (matches this repo's current
  practice of leaving `src/`/`docs/` untracked beyond the two explicit
  git-commit instructions in the brief — see note below).
- `docs/DECISIONS.md` — appended D-012, D-013, D-014.
- `.gitignore` — added an exception for `data/splits/match_split.csv`
  (same pattern as the existing `player_season_metrics.parquet`
  exception), since it would otherwise be silently ignored.

**Note on git scope**: only the two commits the brief explicitly asked
for were made (the preregistration freeze in Step 0, and the split file
in Step 3). Everything else this task touched or produced (this script,
this results page, the `DECISIONS.md` edit) is left uncommitted, matching
the repo's existing state (only Task 01's D-008 freeze commit and the
Step 0/3 commits above exist in git history; all other docs/src content
predates this task and was already untracked).

## 8. Confidence
High on Steps 0, 1, and 3 — the population count matches exactly
(171,618), the score-reconstruction gate passed with zero mismatches
across all 299 matches (a strong end-to-end integrity check on the
event-ordering and own-goal-crediting logic), and the split file's
per-competition counts reconcile to 299. Medium-high on Step 2 — the
unit determination is a genuine empirical check (12.00 units median
against 195 penalties, tight sd of 0.11) rather than an assumption, but
the direction-typing thresholds (45°/135°) are applied exactly as
specified with no independent way to sanity-check them against ground
truth. Lowest confidence is on the two flagged secondary fields (channel
boundary, position group) in Section 6 — both are reasonable defaults
but genuinely undefined by the brief, and neither affects a primary
Study A/B/C result if the research lead wants them changed.
