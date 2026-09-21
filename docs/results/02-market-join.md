# Task 02: Market Value Join and Primary Model (through Gate C)
Date: 2026-09-19
Status: COMPLETE

## 1. Headline
The metric is frozen (commit `9db72ef`), the crosswalk resolves 99/102
players automatically with 3 genuine name collisions left for manual
review, and the join lands at **79 final units across 65 distinct
players** — down from 138 mainly because of a striking, competition-
specific gap: **94.5% of missing valuations (52/55) come from the three
tournament competitions**, where transfermarkt appears to update player
values going *into* a tournament rather than in the 90 days after it
ends. Per Gate C's hard rule, **no model has been fit and the Decision-
value relationship has not been examined** — only predictor/control
descriptives and their mutual correlations are reported below.

## 2. What I did
- **Step 0**: added a narrow `.gitignore` exception and committed
  `data/processed/player_season_metrics.parquet` exactly as Task 01 left
  it — commit `9db72ef940c4b403a48f21ea2068d51f0dfab25d`, SHA-256
  `582b46b83da0c8d1594251f4331a08735a8d8cb6a792e61947405ca7af1d5787`.
  Nothing about the metric has changed since.
- **Step 1**: downloaded the maintainer's single DuckDB file for
  `dcaribou/transfermarkt-datasets` (210.8 MB, all 12 tables, no Kaggle
  account needed) to `data/transfermarkt-datasets.duckdb`. Confirmed the
  exact snapshot date on download and updated `docs/DATA_LICENSES.md`.
- Pulled StatsBomb lineups for all 299 matches (`sb.lineups()`, not
  previously fetched) — needed for each player's StatsBomb-reported
  `country`, the crosswalk's secondary key. 299/299, 0 failures.
- **Step 2**: built the crosswalk (`src/market_join/crosswalk.py`).
  Caught and fixed a real matching bug before finalizing (Section 5) —
  StatsBomb's own `player_nickname` field and a token-subset check
  resolved most of what naive whole-string fuzzy matching got
  confidently wrong, not just low-confidence about.
- **Step 3**: attached valuations (`src/market_join/valuations.py`) —
  nearest record within +90 days of each competition-season's end date,
  plus the closest record to +12 months for H3.
- **Step 4**: built every control in the spec (`src/market_join/controls.py`)
  — age, position group, minutes/completion%/progressive-passes-90 (from
  Task 01's own output), goals+assists/90 (computed fresh here),
  tournament-vs-league indicator, club strength (via `appearances`,
  Section 4), contract expiry.
- Reproduce the whole chain: `python src/market_join/pull_lineups.py &&
  python src/market_join/crosswalk.py && python src/market_join/valuations.py
  && python src/market_join/controls.py`

## 3. Numbers

### Step 0 — Freeze
- Commit: `9db72ef940c4b403a48f21ea2068d51f0dfab25d`
- File: `data/processed/player_season_metrics.parquet`
- SHA-256: `582b46b83da0c8d1594251f4331a08735a8d8cb6a792e61947405ca7af1d5787`

### Step 2 — Crosswalk (102 players)
| Match method | Count |
|---|---|
| exact | 50 |
| normalized (incl. StatsBomb-nickname matches) | 43 |
| fuzzy (token-subset or high-ratio) | 6 |
| manual_review | 3 |

**Manual review list, in full, with candidate context:**
1. **Idrissa Gana Gueye** (Senegal) — 2 transfermarkt candidates both
   named "Idrissa Gueye": id=126665, b.1989-09-26, Everton FC; id=1178488,
   b.2006-09-16, FC Metz. The 1989-born Everton player is almost
   certainly correct given our sample's timeframe, but left for the
   research lead to confirm, not auto-resolved.
2. **Dayotchanculle Upamecano** (France) — only one same-country
   candidate exists at all (id=344695, "Dayot Upamecano", b.1998-10-27,
   Bayern Munich), but the whole-string fuzzy ratio (0.769) sits below
   the 0.90 acceptance bar because of the truncated first name. Very
   likely correct; flagged rather than silently lowering the threshold.
3. **Jonas Hofmann** (Germany) — 2 candidates: id=7161, b.1992-07-14,
   Bayer 04 Leverkusen; id=227085, b.1997-02-07, FC Schalke 04. Our unit
   is from Bundesliga 2023/24, which the 1992-born Leverkusen player's
   current club is consistent with, but not proof for that specific
   season.

### Step 3-4 — Sample flow, 138 units → final
| Filter | Units remaining | Lost here |
|---|---|---|
| ≥200 eligible passes (Task 01b) | 138 | — |
| Crosswalk resolved | 134 | 4 (3 players, one plays 2 units) |
| Valuation within +90 days | 79 | 55 |
| Club strength available | 79 | 0 |
| Age available | 79 | 0 |
| **Final analysis sample** | **79** | **65 distinct players** |

**The 55 valuation-window losses are not evenly spread** — this is the
headline data-quality finding of this task:
| Competition | Units lost |
|---|---|
| Euro 2024 | 26 |
| Euro 2020 | 13 |
| WC2022 | 13 |
| Ligue 1 2022/23 | 2 |
| Ligue 1 2021/22 | 1 |
| Bundesliga, La Liga, MLS | 0 |

52 of 55 (94.5%) come from the three tournament competitions. For the
tournament cases with a valuation somewhere nearby, the nearest one
typically sits 34-48 days on the *other side* of the 90-day window —
consistent with transfermarkt updating values ahead of a tournament
(summer transfer window) and not again until well after.

### Final sample descriptives (n=79)
| Variable | Mean | SD | Min | Median | Max |
|---|---|---|---|---|---|
| Decision (per 100 passes) | 0.195 | 0.088 | -0.027 | 0.207 | 0.395 |
| Completion % | 0.896 | 0.045 | 0.768 | 0.908 | 0.968 |
| Progressive passes/90 | 12.57 | 5.20 | 4.85 | 11.93 | 37.34 |
| Goals+assists/90 | 0.303 | 0.352 | 0.000 | 0.184 | 1.545 |
| Minutes played | 1,349 | 783 | 285 | 1,300 | 3,162 |
| Age at season end | 26.83 | 4.78 | 17.24 | 27.16 | 37.18 |
| Club strength (€, median teammate value) | 22.6M | 5.8M | 2.5M | 22.5M | 38.0M |

Position group: 41 Defender, 28 Midfielder, 10 Forward (no goalkeepers
— excluded by construction in Task 01, not filtered here). Tournament
vs. league: 17 vs. 62. Contract expiry populated for 68/79 (86.1%).

**Outcome variable (reported as a bare distribution only — not
correlated against anything here, per the hard rule):**
market value: mean €39.5M, median €30.0M, range €4.5M-€180M. Valuation
gap from season-end: mean 20.5 days, max 88 (comfortably inside the
90-day window by construction). H3 secondary (12-month) valuation
available for all 79 units, but the gap to the actual 12-month target
ranges from -188 to +37 days — several H3 values are a poor stand-in
for "exactly 12 months later" and should be read with that caveat.

### Correlation matrix — predictors and controls only (n=79)
Decision is included (it's a predictor of interest); the outcome
(market value) is not — per the hard rule, its relationship to anything
else has not been examined.

| | Decision | Compl.% | Prog./90 | G+A/90 | Minutes | Age | Club str. | Tourn. | Def. | Fwd. | Mid. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Decision | 1.00 | 0.54 | -0.03 | -0.44 | -0.13 | -0.24 | 0.01 | -0.07 | 0.05 | -0.43 | 0.24 |
| Completion% | 0.54 | 1.00 | 0.38 | -0.75 | -0.24 | -0.03 | 0.09 | 0.05 | 0.38 | -0.66 | 0.06 |
| Prog. passes/90 | -0.03 | 0.38 | 1.00 | -0.41 | -0.29 | 0.36 | 0.07 | 0.38 | 0.24 | -0.29 | -0.05 |
| Goals+assists/90 | -0.44 | -0.75 | -0.41 | 1.00 | 0.35 | 0.09 | 0.01 | -0.24 | -0.46 | 0.72 | -0.02 |
| Minutes | -0.13 | -0.24 | -0.29 | 0.35 | 1.00 | 0.21 | 0.01 | -0.53 | -0.08 | 0.28 | -0.11 |
| Age | -0.24 | -0.03 | 0.36 | 0.09 | 0.21 | 1.00 | 0.13 | -0.09 | -0.10 | 0.21 | -0.03 |
| Club strength | 0.01 | 0.09 | 0.07 | 0.01 | 0.01 | 0.13 | 1.00 | -0.13 | 0.07 | -0.07 | -0.02 |
| Tournament | -0.07 | 0.05 | 0.38 | -0.24 | -0.53 | -0.09 | -0.13 | 1.00 | 0.07 | -0.20 | 0.06 |
| Defender | 0.05 | 0.38 | 0.24 | -0.46 | -0.08 | -0.10 | 0.07 | 0.07 | 1.00 | -0.40 | -0.77 |
| Forward | -0.43 | -0.66 | -0.29 | 0.72 | 0.28 | -0.20 | -0.07 | -0.02 | -0.40 | 1.00 | -0.28 |
| Midfielder | 0.24 | 0.06 | -0.05 | -0.02 | 0.06 | -0.03 | -0.02 | 0.06 | -0.77 | -0.28 | 1.00 |

**Three pairs exceed |r|=0.7**: Completion% vs. Goals+assists/90
(-0.75), Forward vs. Goals+assists/90 (0.72), and Defender vs.
Midfielder (-0.77, a mechanical artifact of one-hot-encoding a 3-level
category with a small sample — not a substantive finding). The first
two are real and worth the research lead's attention before fitting:
completion% and finishing output move together strongly in this sample,
and forwards drive almost all of the goals+assists signal, as expected
positionally.

## 4. Deviations from the brief
- **Club strength construction** (spec explicitly asks this be flagged):
  there is no dedicated "squad as of date X" table in
  `transfermarkt-datasets` — confirmed in planning research. Approximated
  via the `appearances` table: a player's club at the valuation date is
  their nearest-dated appearance's `player_club_id`; team-mates are
  other players with an appearance for that same club within ±90 days;
  each team-mate's own value is their nearest valuation within ±180
  days; club strength is the median of those, excluding the player.
  **This control is built from the same two tables (`appearances`,
  `player_valuations`) as the outcome itself** — exactly the caveat the
  spec asked to be noted.
- **Position group buckets** (Defender/Midfielder/Forward) aren't
  specified in the brief — a 3-group scheme was chosen to keep cells
  large enough at n=79; stated here rather than assumed silently.
- **Crosswalk matching order** (exact → StatsBomb-nickname → token-subset
  → fuzzy-ratio) goes beyond the spec's literal 4-category list, but
  every outcome still gets labeled as one of the 4 specified methods
  (`exact` / `normalized` / `fuzzy` / `manual_review`) — the extra steps
  are what feed those buckets, not a 5th category.

## 5. Problems and surprises
- **Caught and fixed a real crosswalk bug before finalizing, not just a
  low-confidence case.** An initial whole-string fuzzy-ratio matcher
  didn't just score correct matches low — it confidently returned WRONG
  players for several real cases (e.g. "Jorge Luiz Frello Filho" →
  "Luiz Felipe" at 0.529, when the actual match is "Jorginho" via
  StatsBomb's own nickname field; "Kléper Laveran Lima Ferreira" →
  "Flávio Ferreira" at 0.605, when the actual match is "Pepe"). Using
  StatsBomb's `player_nickname` field directly (available for 991/2,972
  players in the pulled lineups) and a token-subset check resolved
  essentially all of these correctly and are why manual_review dropped
  from an initial ~26 candidates to 3 genuine ones.
- **A silent country-name mismatch** (`Côte d'Ivoire` vs. transfermarkt's
  `Cote d'Ivoire`) caused one player (Kossonou) to fail country-based
  disambiguation entirely — fixed by normalizing country strings the
  same way names are normalized (accent-strip, lowercase) before
  comparing.
- **The tournament-vs-league valuation gap (Section 3) is the most
  substantive finding here.** It's not a bug — it's a real pattern in
  how transfermarkt's valuation-update cadence interacts with a
  90-day-after-the-fact window, and it disproportionately removes
  tournament units (which also happen to be exactly where our earlier
  360-data feasibility work concentrated). Worth the research lead
  knowing this before deciding whether the frozen ±90-day window should
  be revisited for tournament competitions specifically in future work
  — not changed here, per the hard rule against modifying the
  specification mid-task.
- **H3's 12-month gap ranges from -188 to +37 days** (Section 3) — a
  meaningful share of the H3 secondary-analysis valuations are not
  close to actually being 12 months out. Flagged for whoever runs the
  H3 analysis.

## 6. Questions for the research lead
1. **Do the 3 manual-review crosswalk cases get resolved, and how?**
   Full candidate context is in Section 3. If all 3 resolve to the
   listed most-likely candidate, up to 4 more units could re-enter the
   pipeline (pending their own valuation-window and club-strength
   checks) — I did not attempt this myself.
2. **Is the 94.5% tournament-concentrated valuation-window loss
   something to address before fitting** (e.g., a wider or
   tournament-specific window in a future amendment), or is n=79 (17
   tournament, 62 league) an acceptable sample to fit Amendment 1's
   primary specification on as-is? I have not fit anything pending this.
3. **The completion%/goals+assists collinearity (r=-0.75) and the
   forward-position/goals+assists collinearity (r=0.72)** — both real,
   both plausible on football grounds, but worth a decision on whether
   either needs addressing (e.g., dropping one, or accepting the
   overlap) before the primary model is fit.
4. **Gate C is answered — is fitting the primary model authorized now?**
   Per the hard rule, I have not touched the Decision-value relationship
   in any way and won't until this is confirmed.

## 7. Files produced
- `src/decision_engine/` — no changes; the frozen commit is the exact
  state Task 01 left it in.
- `src/market_join/pull_lineups.py`, `download_transfermarkt.py`,
  `crosswalk.py`, `valuations.py`, `controls.py`.
- `data/raw/lineups/*.parquet` (gitignored, 299 files).
- `data/transfermarkt-datasets.duckdb` (gitignored, 210.8 MB).
- `data/processed/player_crosswalk.csv`,
  `units_with_valuations.parquet`, `market_join_analysis_sample.parquet`
  (gitignored).
- `docs/DATA_LICENSES.md` — snapshot date/download URL added.
- `.gitignore` — one narrow exception for the frozen metric file.
- `docs/results/02-market-join.md` — this page.
- One git commit: `9db72ef` (Step 0's freeze — the only commit in this
  repo so far).

## 8. Confidence
High confidence in Steps 0-1 (a git commit and file hash are either
right or provably wrong — verified) and in the crosswalk's 99 resolved
matches (spot-checked a random sample, all correct; the 3 remaining
manual_review cases are genuinely ambiguous, not algorithm failures).
Medium confidence in club strength — it's a reasonable, clearly-flagged
approximation given the data available, but it's the one control built
from the same tables as the outcome, and its accuracy at the level of
"who was actually in the squad on this exact date" hasn't been
independently verified beyond the construction logic itself. The
weakest link is sample size after the tournament-valuation gap: 79
units (17 tournament) is workably close to the ~138-unit expectation
Amendment 1 was written against, but meaningfully smaller, and that
shrinkage is concentrated in exactly the matches most tied to
high-profile competitions.
