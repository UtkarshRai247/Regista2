# Task 12: Total-effect spec, leaderboard, worked example (Amendment v2-9)
Date: 2026-09-23
Status: COMPLETE

## Per-section checklist (per brief docs/specs/task-12-artifacts.md)
- Step 0 (commit Amendment v2-9 alone, record hash + SHA-256): COMPLETE
- Step 1 (PH-O4 total-effect refit vs. PRIMARY, v2-9.2): COMPLETE
- Step 2 (leaderboard, v2-9.4a): COMPLETE
- Step 3 (worked example, v2-9.4b): COMPLETE
- Hard rules (no new hypotheses, fixed median-gap rule, leaderboard
  reported as computed, no interpretation for the paper, no memory
  writes, JOURNAL.md untouched): COMPLETE

## 1. Headline
PH-O4 (no possession-share control) is **not significant for xG**
(+0.0271 per SD, p=0.532) but **stays significantly negative for goals**
(-0.2088, p<0.001) — consistent with v2-9.1's mediator concern for xG
specifically (the total effect on xG collapses once possession isn't
held fixed) but not fully resolving the goals result the same way. This
is descriptive only and does not reopen the closed v2-8.4 verdict. The
leaderboard (160 qualifying players) and the worked example (18,928
qualifying passes, one selected by the fixed median-gap rule) are
reported below exactly as computed, with no claims attached, per the
brief.

## 2. What I did
Reproduce with: `.venv/bin/python src/decision_engine/task12_artifacts.py`.

- **Step 0**: committed `docs/specs/analysis-plan-v2.md` alone (Amendment
  v2-9, 49 new lines) as commit `07114da`; new file SHA-256 =
  `b62062b34f894e4b10d4b7ff8192d5934caef888baa951d0398972fe57ed81fc`.
  Separately committed `docs/JOURNAL.md`'s pending Task 11 retrospective
  entry (research lead's own edit, not touched by me) as `b693c03`.
- **Step 1**: refit H-O1's own predictors minus `possession_share`
  (`decision_z + is_home + competition-season FE`) for xG and goals,
  clustered by team context, on the same 583-row frame Task 11 built
  (`task11_outcome_diagnostics.build_diagnostics_frame`), via
  `task10_partB_outcome.fit_ols` (unchanged). Task 10's H-O1 and Task
  11's PH-O1 numbers were read from their existing JSON outputs, not
  recomputed.
- **Step 2**: built the frozen per-pass Decision table
  (`decompose.build_per_pass_table`) once and pooled it directly to
  `player_id` (not `player_id x competition_id x season_id`, unlike
  `decompose.py`'s own `main()` output) — kept players with >=200 pooled
  eligible passes. Reused `task01b_diagnostics.py`'s exact `comp_names`
  dict and its mode-position-from-raw-events pattern (extended here to
  also take the mode `player` name field, since the brief asks for
  player name and no existing lookup provided one), then
  `task04_situation_context.position_group()` to bucket the mode
  position. Computed `overall_mean` and shrunken Decision (Section
  "Design decisions" below).
  **Design decision (disclosed)**: the brief's formula, `shrunken = mean
  + 0.744 x (player mean - overall mean)`, doesn't specify whether
  `overall_mean` is the unweighted mean of qualifying players' own
  per-player means, or the pass-count-weighted grand mean pooling all
  their passes together. Used the standard empirical-Bayes convention —
  shrink toward the mean of the same per-unit statistic being estimated,
  each qualifying player counted once (unweighted) — and also computed
  the pass-weighted alternative for transparency (Section 3); the two
  differ by 0.0026 (0.1946 vs. 0.1972), small relative to the spread
  between players.
- **Step 3**: rebuilt the confirmation-half `avail` table via Task
  05/06's unchanged `confirmation_match_ids`/`load_and_prepare`/
  `build_available_types_table` chain, filtered to the brief's cell
  (`zone=="middle"`, `under_pressure==False`, `game_state in ("level",
  "trailing")`, chosen type != `lateral_medium`, `lateral_medium`
  available), computed `g = ev_star(lateral_medium) - ev_star(chosen)`
  per qualifying pass, and selected by the fixed median-gap rule.
  **Design decision (disclosed)**: "the median-gap pass" doesn't map to
  a single row when the qualifying count is even. Fixed rule, decided
  before looking at who it would select: sort ascending by `g` (ties
  broken by `match_id`, `event_id`), take index `(n-1)//2`. With
  n=18,928 (even), this is the lower-middle element.
  For the selected pass's full option-level detail, joined its typed
  candidate rows to `options_policy.parquet` directly (verified
  row-aligned with `options_ev.parquet`: 1,237,611 rows each, identical
  key columns, `options_policy` a strict superset) — one join instead of
  two. Hit and fixed two join bugs before trusting the output (Section
  5). Saved the selected pass's full joined option table (7 candidates)
  to `data/processed/worked_example.csv`.

## 3. Numbers

### Step 1 — PH-O4 vs. PRIMARY (n=583, clustered by team context)

| Spec | Label | Outcome | n | R² | Decision_z coef | 95% CI | p |
|---|---|---|---|---|---|---|---|
| H-O1 | PRIMARY | xG | 583 | 0.1665 | -0.1381 | [-0.2104, -0.0659] | 0.00018 |
| PH-O1 | PRIMARY | xG | 583 | 0.1725 | -0.1532 | [-0.2289, -0.0774] | 0.00007 |
| PH-O4 | DESCRIPTIVE | xG | 583 | 0.0068 | **+0.0271** | [-0.0580, 0.1123] | 0.532 |
| H-O1 | PRIMARY | goals | 583 | 0.1979 | -0.4031 | [-0.5124, -0.2939] | <1e-12 |
| PH-O1 | PRIMARY | goals | 583 | 0.2004 | -0.4101 | [-0.5223, -0.2978] | <1e-15 |
| PH-O4 | DESCRIPTIVE | goals | 583 | 0.0521 | **-0.2088** | [-0.3089, -0.1087] | <1e-4 |

No conclusion is stated about which specification is "correct," per the
brief.

### Step 2 — Leaderboard
**160 players** qualify (>=200 pooled eligible passes across all
contexts). `overall_mean` (unweighted, used for shrinkage) = **0.1946**
decision-per-100; pass-weighted alternative = 0.1972. Reliability =
0.744 (Task 01b, `docs/results/01b-diagnostics.md`).

**Top 20 by shrunken Decision per 100:**

| Player | Position | Competitions | n eligible | Raw D/100 | Shrunken D/100 |
|---|---|---|---|---|---|
| Florian Grillitsch | Midfielder | Bundesliga 2023/24, UEFA Euro 2020, UEFA Euro 2024 | 219 | 0.4711 | 0.4003 |
| Mykola Shaparenko | Midfielder | UEFA Euro 2020, UEFA Euro 2024 | 207 | 0.4054 | 0.3515 |
| Moriba Kourouma Kourouma | Midfielder | La Liga 2020/21 | 201 | 0.3946 | 0.3434 |
| Philippe Coutinho Correia | Midfielder | La Liga 2020/21 | 295 | 0.3685 | 0.3240 |
| İlkay Gündoğan | Midfielder | FIFA World Cup 2022, UEFA Euro 2020, UEFA Euro 2024 | 320 | 0.3599 | 0.3176 |
| Joshua Kimmich | Defender | Bundesliga 2023/24, FIFA World Cup 2022, UEFA Euro 2020, UEFA Euro 2024 | 564 | 0.3497 | 0.3100 |
| Pedro González López | Midfielder | FIFA World Cup 2022, La Liga 2020/21, UEFA Euro 2020, UEFA Euro 2024 | 1567 | 0.3472 | 0.3081 |
| Ronald Federico Araújo da Silva | Defender | La Liga 2020/21 | 513 | 0.3256 | 0.2920 |
| Rodrigo Hernández Cascante | Defender | FIFA World Cup 2022, UEFA Euro 2020, UEFA Euro 2024 | 887 | 0.3148 | 0.2841 |
| William Saliba | Defender | FIFA World Cup 2022, Ligue 1 2021/22, UEFA Euro 2024 | 369 | 0.3136 | 0.2831 |
| Hakan Çalhanoğlu | Midfielder | UEFA Euro 2020, UEFA Euro 2024 | 227 | 0.3120 | 0.2819 |
| Warren Zaire Emery | Defender | Ligue 1 2022/23 | 265 | 0.3095 | 0.2801 |
| Eric García Martret | Defender | UEFA Euro 2020 | 215 | 0.3069 | 0.2782 |
| Georginio Wijnaldum | Midfielder | Ligue 1 2021/22, UEFA Euro 2020, UEFA Euro 2024 | 274 | 0.3019 | 0.2744 |
| Bernardo Mota Veiga de Carvalho e Silva | Midfielder | FIFA World Cup 2022, UEFA Euro 2020, UEFA Euro 2024 | 363 | 0.3005 | 0.2734 |
| Nicolò Barella | Midfielder | UEFA Euro 2020, UEFA Euro 2024 | 290 | 0.2996 | 0.2727 |
| Illia Zabarnyi | Defender | UEFA Euro 2020, UEFA Euro 2024 | 341 | 0.2960 | 0.2700 |
| Sergino Dest | Defender | FIFA World Cup 2022, La Liga 2020/21 | 775 | 0.2926 | 0.2675 |
| Sergi Roberto Carnicer | Defender | La Liga 2020/21 | 523 | 0.2908 | 0.2662 |
| Pau Francisco Torres | Defender | FIFA World Cup 2022, La Liga 2020/21, UEFA Euro 2020 | 522 | 0.2882 | 0.2642 |

**Bottom 20 by shrunken Decision per 100:**

| Player | Position | Competitions | n eligible | Raw D/100 | Shrunken D/100 |
|---|---|---|---|---|---|
| Ivan Perišić | Forward | FIFA World Cup 2022, UEFA Euro 2020, UEFA Euro 2024 | 205 | -0.1213 | -0.0404 |
| Kevin De Bruyne | Midfielder | FIFA World Cup 2022, UEFA Euro 2020, UEFA Euro 2024 | 265 | -0.1150 | -0.0357 |
| Denzel Dumfries | Defender | FIFA World Cup 2022, UEFA Euro 2020, UEFA Euro 2024 | 257 | -0.0832 | -0.0121 |
| Amine Adli | Midfielder | Bundesliga 2023/24 | 227 | -0.0267 | 0.0300 |
| Daley Blind | Defender | FIFA World Cup 2022, UEFA Euro 2020 | 362 | 0.0005 | 0.0502 |
| Daniel Olmo Carvajal | Forward | Bundesliga 2023/24, FIFA World Cup 2022, UEFA Euro 2020, UEFA Euro 2024 | 341 | 0.0104 | 0.0575 |
| Luke Shaw | Defender | FIFA World Cup 2022, UEFA Euro 2020, UEFA Euro 2024 | 409 | 0.0242 | 0.0678 |
| Ángel Fabián Di María Hernández | Forward | FIFA World Cup 2022, Ligue 1 2021/22 | 633 | 0.0267 | 0.0697 |
| Bukayo Saka | Forward | FIFA World Cup 2022, UEFA Euro 2020, UEFA Euro 2024 | 251 | 0.0280 | 0.0707 |
| Abdou Diallo | Defender | FIFA World Cup 2022, Ligue 1 2021/22 | 277 | 0.0429 | 0.0818 |
| Neymar da Silva Santos Junior | Forward | FIFA World Cup 2022, Ligue 1 2021/22, Ligue 1 2022/23 | 1197 | 0.0494 | 0.0866 |
| Joakim Mæhle | Defender | Bundesliga 2023/24, FIFA World Cup 2022, UEFA Euro 2020, UEFA Euro 2024 | 271 | 0.0591 | 0.0938 |
| Cristian Gabriel Romero | Defender | FIFA World Cup 2022 | 246 | 0.0749 | 0.1055 |
| Kylian Mbappé Lottin | Forward | FIFA World Cup 2022, Ligue 1 2021/22, Ligue 1 2022/23, UEFA Euro 2020, UEFA Euro 2024 | 1366 | 0.0769 | 0.1071 |
| Piotr Zieliński | Midfielder | FIFA World Cup 2022, UEFA Euro 2020, UEFA Euro 2024 | 226 | 0.0777 | 0.1076 |
| Martin Braithwaite Christensen | Forward | FIFA World Cup 2022, La Liga 2020/21, UEFA Euro 2020 | 224 | 0.0805 | 0.1097 |
| Giovanni Di Lorenzo | Defender | UEFA Euro 2020, UEFA Euro 2024 | 337 | 0.0842 | 0.1125 |
| Carlos Henrique Casimiro | Midfielder | FIFA World Cup 2022, La Liga 2020/21 | 222 | 0.0848 | 0.1129 |
| Christian Dannemann Eriksen | Midfielder | FIFA World Cup 2022, UEFA Euro 2020, UEFA Euro 2024 | 227 | 0.0932 | 0.1191 |
| Nordi Mukiele Mulere | Defender | Ligue 1 2022/23 | 278 | 0.0935 | 0.1194 |

### Step 3 — Worked example
18,928 qualifying passes (confirmation half, middle third, no pressure,
level or trailing, chosen type != lateral_medium, lateral_medium
available). Selected pass: index 9,463 of 18,928 (0-indexed, sorted
ascending by g), g = 0.0001651.

- **Match**: 3857276, FIFA World Cup 2022, minute 89.
- **Team**: Canada. **Passer position group**: Defender.
- **Chosen option**: type `lateral_short`, (x=62.05, y=68.38), distance
  11.98, angle 59.12°, p_success=0.9800, EV=0.001096, policy
  probability=0.1666.
- **Best lateral_medium option**: (x=78.13, y=80.61), distance 31.64,
  angle 45.35°, p_success=0.9816, EV=0.001598, policy
  probability=0.1723.
- **Frame**: 7 total candidate options, 13 visible players.
- **What happened next**: pass complete. Next event: Canada, Ball
  Receipt* (Jonathan David). Then: Canada, Carry (Jonathan David).
- Full 7-row option table: `data/processed/worked_example.csv`
  (committed, per the brief's explicit instruction).

## 4. Deviations from the brief
- **None in scope or method.** PH-O4 used exactly H-O1's own predictors
  minus possession share; the leaderboard and worked example followed
  v2-9.4's specifications exactly, including the fixed selection rule
  for Step 3.
- **Disclosed implementation choices** (both stated plainly above, not
  hidden): the "overall mean" definition for shrinkage (unweighted
  across qualifying players), and the even-`n` tie-break for the
  median-gap pass (lower-middle index after sorting, decided before
  seeing the result).

## 5. Problems and surprises
- **Two join bugs were caught and fixed before trusting the worked
  example's numbers, both from column-name collisions or population
  mismatches, not from the underlying data.**
  1. Reading the FULL `options_policy.parquet` (1.2M rows) before
     restricting to the one selected pass's `(match_id, event_id)`
     produced a `ValueError: Can only compare identically-labeled Series
     objects` in the join's own collision-diagnostic step — the same
     class of bug Task 09's `compute_g_p_l_ph2` hit (a differently-
     shaped groupby index between a small subset and the full
     population). Fixed by filtering `options_policy.parquet` to the
     pass's own match/event before any groupby, mirroring Task 09's
     fix exactly.
  2. `opt` (from `load_and_prepare`) already carries its own `_merge`,
     `ev`, `distance`, `pass_complete`, and `team` columns from an
     earlier join; naively merging in `options_policy`'s same-named
     columns either raised `ValueError: Cannot use name of an existing
     column for indicator column` (for `_merge`) or silently produced
     `_x`/`_y`-suffixed duplicates that a later `KeyError: 'ev'` caught.
     Fixed by dropping the stale `_merge` column first and explicitly
     renaming every genuinely-new column pulled from `options_policy`
     with a `_pol` suffix, so no column name is ever ambiguous.
  Both were caught by the code failing loudly (an exception), not by a
  silently wrong number — verified the fixed join's diagnostics
  (`match_rate=1.0`, 0 collisions, 0 group-size mismatches) before
  trusting any of the worked example's reported values.
- **Face validity note on the leaderboard, reported factually and
  without comment on what it means**: several players widely regarded as
  elite attacking creators (Kevin De Bruyne, Kylian Mbappé, Neymar,
  Bukayo Saka) appear in the bottom 20 by this metric, while several
  players less associated with public "creativity" reputations appear at
  the top. The brief explicitly asks for the leaderboard "as computed,
  whoever is on it" — reported exactly that way, with no filtering or
  reframing. This is a face-validity observation for the research lead
  to weigh, not a claim I am making about the metric's quality.
- Nothing else was missing, broken, or malformed. The confirmation-half
  join for Step 3's full candidate population matched 100.0%.

## 6. Questions for the research lead
None. Both places where the brief left an implementation detail
underspecified (the shrinkage formula's "overall mean," and the
even-count median tie-break) have a single standard, defensible
resolution that was applied and disclosed plainly (Section 2) rather
than raised as an open question, since neither materially changes any
number's substance (the two "overall mean" candidates differ by 0.0026;
the median tie-break is inherent to picking one specific pass, not
a judgment call about the science).

## 7. Files produced
- `src/decision_engine/task12_artifacts.py` — this task's full script
  (PH-O4 refit, leaderboard, worked example, all three steps).
- `data/task12_artifacts.json` — full run summary (all coefficients,
  full leaderboard, worked example detail). Gitignored.
- `data/processed/worked_example.csv` — the selected pass's full 7-row
  option table. **Committed**, per the brief's explicit "commit it"
  instruction — the one intentional exception to the project's usual
  "nothing under data/ is committed" rule this task makes.
- Git commits made this task: `07114da` (Amendment v2-9 alone, Step 0);
  `b693c03` (docs/JOURNAL.md, research lead's own Task 11 entry,
  committed separately per the established pattern); `[this task's own
  commit hash, to be recorded below once made]`.

## 8. Confidence
High. Both numerical bugs encountered were caught by the code failing
loudly rather than producing a silently wrong number, and were fixed by
mechanical, well-precedented means (population restriction, explicit
column renaming) rather than any judgment call about the underlying
statistics. Step 1's numbers were cross-checked against Task 10/11's own
already-verified H-O1/PH-O1 outputs (read back, not recomputed) so there
is no room for drift between them. The worked example's join diagnostics
(100.0% match rate, zero collisions) were checked before any of its
numbers were trusted. The weakest link is the same one flagged in every
outcome-related task so far: what any of this means for the project's
central Decision metric is deliberately not addressed here — Steps 2-3
are declared descriptive artifacts with no hypotheses attached, and I
have kept them that way.
