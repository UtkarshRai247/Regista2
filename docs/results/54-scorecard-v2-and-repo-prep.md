# Task 54: Scorecard v2 (tempo added, Figure 1) and repo preparation
Date: 2026-09-29
Status: COMPLETE (B1 stopped the first run; resolved by the research lead in e771149; Part A and B2-B6 then run; deviations in Section 4)

Descriptive and housekeeping only: no new tests and no new claims.
- Holdout untouched. Reserved and replication data were read only through existing built tables; no raw event file was opened in this run.
- Repository visibility not changed, nothing pushed, no history rewritten.

## Checklist
| Section | Status |
|---|---|
| Step 0: brief + abstract draft committed by the research lead | COMPLETE (4fef446; abstract edits 94b2eee, 054bf01; B1 resolution e771149) |
| B1: history scan | COMPLETE in the first run (164e291, d23ba32), which stopped the task. Resolved by the research lead (e771149, recorded below and as D-017). Not re-run |
| A1: tempo measures on Card A, one baseline per measure over all 1,551 matches | COMPLETE |
| A2: tiers | COMPLETE |
| A3: HOLD_VARIATION bootstrap interval and labels | COMPLETE (both cards) |
| A4: Card B within-DM stability on the study sample; automatic Tier 3 rule | COMPLETE (6 of 7 Card B dimensions end in Tier 3) |
| A5: Figure 1 | COMPLETE (`docs/scorecard/figure1.png`) |
| A6: Busquets / Kroos values | COMPLETE |
| A7: `index.html` + `index_public.html` | COMPLETE (checked in Chrome from a local server) |
| B2: committed files with PFF-derived numbers | COMPLETE |
| B3: README.md | COMPLETE (StatsBomb logo = TODO line) |
| B4: .gitignore / LICENSE / requirements.txt | COMPLETE |
| B5: JOURNAL.md / AGENTS.md not staged | COMPLETE |
| B6: command to make the repo public (not run) | COMPLETE |
| Memory gate (Task 25) | COMPLETE (card A 53% / 4.2 GB; card B 45% / 3.9 GB) |

## 1. Headline
- **Card B (study sample, 111 DMs):** on the study sample's own DMs, only AV reaches 0.60 stability (0.693, 23 players). By Task 51's automatic rule, the other six Card B dimensions show as Tier 3 there:
  - PR2_flag_keep 0.052 (78 players)
  - W 0.560
  - HOLD_VARIATION 0.499
  - RQ_rel 0.419
  - Decision 0.281
  - MOVE_ON_SPEED 0.092
- **Card A (2015/16, 185 DMs):** carries the five tempo measures with the brief's tiers. M4_SWITCH is 1A. M4_ACCEL, M4_SLOW and M2 are 1B, alongside PR2_flag_keep and A1. M3_speed is 2.
- **A6 check against the abstract:** the values sit a few percentile points off some of the abstract's wording (see A6 below).

## 2. What I did
- **Decision recorded (Resolution of the B1 stop, e771149).** The five tracked files under `data/` are fine to publish, stay tracked, and the `.gitignore` whitelist is kept:
  - `data/splits/match_split.csv`
  - `data/splits/cv_folds.csv`
  - `data/processed/player_season_metrics.parquet`: engine v1, withdrawn per D-015; the README says "engine v1, withdrawn; do not use".
  - `data/processed/worked_example.csv`
  - `data/expert_lists/selections.csv`

  None is raw StatsBomb or PFF data. PFF's organisational addresses stay in the docs. Appended to `docs/DECISIONS.md` as D-017 (CLAUDE.md rule 7).
- **Part A:** `.venv/bin/python -W ignore src/engine_v2/task54_scorecard.py`, then `task54_outputs.py`.
  - **A1.** Units are the union of the existing built unit tables `task52_1516_{receptions,passes}` (development) and `task53_1516rep_{receptions,passes}` (replication): 1,551 matches, 1,158,231 completed receptions, 1,286,650 eligible passes. No raw event file was opened.
    - One baseline per measure on 5 match folds over all 1,551 ids (`task52_build.folds_for`, seed 20260929), with Task 53's definitions:
      - g_T (log T; out-of-fold R^2 0.058; 879,624 timed receptions) → M3_speed = -r
      - FK <= 1.5 s classifier (AUC 0.614; 333,082 pressured receptions) → M2
      - M4_ACCEL / SLOW / SWITCH classifiers (AUC 0.647 / 0.616 / 0.674)
    - Scored with Task 51's `score` (Task 29's method), floors M2 >= 50 and M3 / M4 >= 100.
  - **Carried-over dimensions** (Card A: PR2_flag_keep, A1, W, MOVE_ON_SPEED; Card B: Decision, PR2_flag_keep, W, RQ_rel, MOVE_ON_SPEED, AV) were rebuilt from the same existing tables. They reproduce Task 51's shrunk values exactly (max absolute difference 0.0 in every dimension).
  - **A2.** Tiers as fixed in the brief; each dimension carries its evidence text. M4_* carry the STYLE label.
  - **A3.** HOLD_VARIATION: 1,000 bootstrap resamples of each player's matches (seed 20260929), SD of the pooled residuals, 90% percentile interval. Labels are against the mean of the group's raw SDs (players meeting the floor).
  - **A4.** Task 52's generalised Task 38 R1 (100 random match halves, Spearman-Brown median), players >= 4 matches, within Card B's DMs. For AV the match is the PFF game. Below 0.60 moves to Tier 3.
  - **Card C** carried from Task 51 with its tier relabelled to 1B.
  - **A7.** Task 51's page generator, extended for 1A / 1B badges, STYLE markers and a public note. The public variant drops every AV row and the PFF credit and shows an omission note. Served from 127.0.0.1 and checked in Chrome:
    - Card A: 185 rows, 10 dimensions, click-through works, 1A badge shown.
    - Card B: 111 rows; the public Card B has 6 dimensions and no AV column.
    - Card C chart renders.
    - No console errors; no external requests (only the page itself loaded).
- **Part B:** B2 by keyword scan of `git ls-files`, then line-by-line reading of every match. The README, LICENSE, `requirements.txt` and `.gitignore` were written as listed. `requirements.txt` comes from an AST import scan of 84 local modules reached from the headline scripts; 11 third-party packages, versions from `.venv/bin/pip freeze`.

## 3. Numbers
### Part A: counts, reliabilities, tiers (per dimension)

**Card A — 2015/16 big five (all five leagues; group = Task 44's 185 DMs).** Group size 185.

| Dimension | Tier | within-DM reliability (source) | floor | meeting floor | CLEARLY ABOVE | CLEARLY BELOW | CAN'T TELL | not enough data |
|---|---|---|---|---|---|---|---|---|
| PR2_flag_keep | TIER 1B | 0.666 (docs/results/44-big-five-1516.md:120 (2015/16 DMs, 185)) | 50 | 185 | 27 | 35 | 123 | 0 |
| A1 | TIER 1B | 0.487 (docs/results/45-press-resistance-vetting.md:48 (2015/16 DMs, 185)) | 50 | 185 | 9 | 13 | 163 | 0 |
| M4_SWITCH (STYLE) | TIER 1A | 0.830 (docs/results/53-tempo-replication.md S3 (2015/16 replication-league DMs, 141)) | 100 | 185 | 36 | 45 | 104 | 0 |
| M4_ACCEL (STYLE) | TIER 1B | 0.898 (docs/results/53-tempo-replication.md S1 (2015/16 replication-league DMs, 141)) | 100 | 185 | 58 | 54 | 73 | 0 |
| M4_SLOW (STYLE) | TIER 1B | 0.844 (docs/results/53-tempo-replication.md S2 (2015/16 replication-league DMs, 141)) | 100 | 185 | 39 | 48 | 98 | 0 |
| M2 | TIER 1B | 0.688 (docs/results/53-tempo-replication.md S5 (2015/16 replication-league DMs, 141)) | 50 | 185 | 25 | 30 | 130 | 0 |
| M3_speed | TIER 2 | 0.806 (docs/results/53-tempo-replication.md S4 (2015/16 replication-league DMs, 141)) | 100 | 185 | 44 | 41 | 100 | 0 |
| W | TIER 2 | 0.802 (docs/results/46-movers-and-spatial-physical.md:73 (2015/16 DMs, 185)) | 100 | 185 | 47 | 43 | 95 | 0 |
| HOLD_VARIATION | TIER 2 | 0.730 (docs/results/44-big-five-1516.md:119 (2015/16 DMs, 185)) | 200 | 185 | 38 | 44 | 103 | 0 |
| MOVE_ON_SPEED | TIER 3 | 0.475 (docs/results/44-big-five-1516.md:118 (2015/16 DMs, 185)) | 200 | 183 | 5 | 14 | 164 | 2 |

**Card B — study sample (group = Task 27's 111 DMs).** Group size 111.

| Dimension | Tier | within-DM reliability (source) | floor | meeting floor | CLEARLY ABOVE | CLEARLY BELOW | CAN'T TELL | not enough data |
|---|---|---|---|---|---|---|---|---|
| Decision | TIER 3 | 0.281 (computed in Task 54 on Card B's DMs (Task 38's method, >= 4 matches)) | 100 | 111 | 2 | 0 | 109 | 0 |
| PR2_flag_keep | TIER 3 | 0.052 (computed in Task 54 on Card B's DMs (Task 38's method, >= 4 matches)) | 50 | 37 | 2 | 3 | 32 | 74 |
| W | TIER 3 | 0.560 (computed in Task 54 on Card B's DMs (Task 38's method, >= 4 matches)) | 100 | 106 | 12 | 8 | 86 | 5 |
| RQ_rel | TIER 3 | 0.419 (computed in Task 54 on Card B's DMs (Task 38's method, >= 4 matches)) | 100 | 98 | 6 | 8 | 84 | 13 |
| HOLD_VARIATION | TIER 3 | 0.499 (computed in Task 54 on Card B's DMs (Task 38's method, >= 4 matches)) | 200 | 35 | 8 | 8 | 19 | 76 |
| MOVE_ON_SPEED | TIER 3 | 0.092 (computed in Task 54 on Card B's DMs (Task 38's method, >= 4 matches)) | 200 | 29 | 3 | 4 | 22 | 82 |
| AV | TIER 2 | 0.693 (computed in Task 54 on Card B's DMs (Task 38's method, >= 4 matches; match = PFF game)) | 300 | 46 | 7 | 6 | 33 | 65 |

**Card C:** 1 player (Sergio Busquets i Burgos), 11 La Liga seasons; tier relabelled TIER 1B.

### A5: Figure 1 rows (Card A)
Praised-list DMs present in Card A, by ID: Toni Kroos (5574) and Sergio Busquets i Burgos (5203). The other 11 praised ids are not among Task 44's 185 DMs. Top three by shrunk PR2_flag_keep: Thiago Motta (4325), Jorge Luiz Frello Filho (7024), Claudio Marchisio (8294).

| Player | PR2_flag_keep | M4_ACCEL | M4_SLOW | M4_SWITCH | M2 | W |
|---|---|---|---|---|---|---|
| Toni Kroos | 98 [85, 99] CLEARLY ABOVE | 29 [17, 41] CLEARLY BELOW | 25 [14, 43] CLEARLY BELOW | 96 [92, 98] CLEARLY ABOVE | 83 [52, 95] CLEARLY ABOVE | 12 [1, 24] CLEARLY BELOW |
| Sergio Busquets i Burgos | 98 [88, 100] CLEARLY ABOVE | 8 [3, 15] CLEARLY BELOW | 68 [48, 85] CAN'T TELL | 72 [51, 84] CAN'T TELL | 93 [82, 99] CLEARLY ABOVE | 39 [19, 61] CAN'T TELL |
| Thiago Motta | 100 [98, 100] CLEARLY ABOVE | 7 [3, 14] CLEARLY BELOW | 65 [44, 82] CAN'T TELL | 27 [11, 49] CLEARLY BELOW | 98 [92, 99] CLEARLY ABOVE | 44 [24, 69] CAN'T TELL |
| Jorge Luiz Frello Filho | 99 [98, 100] CLEARLY ABOVE | 21 [15, 31] CLEARLY BELOW | 78 [63, 90] CLEARLY ABOVE | 1 [0, 2] CLEARLY BELOW | 100 [99, 100] CLEARLY ABOVE | 20 [9, 37] CLEARLY BELOW |
| Claudio Marchisio | 99 [94, 100] CLEARLY ABOVE | 50 [31, 69] CAN'T TELL | 70 [44, 88] CAN'T TELL | 98 [95, 99] CLEARLY ABOVE | 97 [87, 99] CLEARLY ABOVE | 31 [14, 57] CAN'T TELL |

### A6: Busquets and Kroos in Card A (percentile within 185 DMs, 90% interval on the percentile scale)

| Player | Measure | n units | shrunk | percentile | 90% interval | label |
|---|---|---|---|---|---|---|
| Sergio Busquets i Burgos | M4_ACCEL | 2299 | -0.0752 | 8.1 | [2.7, 14.6] | CLEARLY BELOW |
| Sergio Busquets i Burgos | M2 | 429 | +0.1554 | 93.0 | [81.6, 98.9] | CLEARLY ABOVE |
| Sergio Busquets i Burgos | M4_SWITCH | 2299 | +0.0091 | 72.4 | [50.8, 84.3] | CAN'T TELL |
| Toni Kroos | M4_ACCEL | 2339 | -0.0380 | 29.2 | [16.8, 41.1] | CLEARLY BELOW |
| Toni Kroos | M2 | 354 | +0.1216 | 82.7 | [52.4, 94.6] | CLEARLY ABOVE |
| Toni Kroos | M4_SWITCH | 2339 | +0.0286 | 95.7 | [91.9, 97.8] | CLEARLY ABOVE |

For the abstract's check, the abstract draft's (`docs/abstract/SSAC27-abstract-v2.md`) wording next to these percentiles:

| Abstract wording | Card A value |
|---|---|
| Busquets "rarely speeds play up (bottom 6%)" | M4_ACCEL percentile 8.1 |
| Busquets "releases quickly and safely under pressure (top 7%)" | M2 percentile 93.0 |
| Kroos "a switcher (top 7%)" | M4_SWITCH percentile 95.7 |
| Kroos "seldom accelerates (bottom 27%)" | M4_ACCEL percentile 29.2 |
| Marchisio "top 4% for both switching and quick, safe release" | M4_SWITCH 98, M2 97 (Figure 1 table above) |

### B2: committed files that contain PFF-derived numbers
Found by a keyword scan (AV, availab*, PFF, pff_) of every tracked file, then reading each matching line. Files where the match was only the ordinary word "available" or a PFF mention without numbers are left out.

| File | PFF-derived content |
|---|---|
| `docs/results/36-pff-ingest.md` | PFF ingest counts, alignment and clock statistics (Task 36) |
| `docs/results/38-availability.md` | AV results: reliabilities, tests, DM table (Task 38) |
| `docs/results/40-benchmark-v6-freeze.md` | row counts of the Task 38 availability tables; Task 38 spot-check (12 / 14) |
| `docs/results/41-vetting-round-2.md` | AV / AV_vis threshold and praised-list results (Task 41) |
| `docs/results/42-improvement-round-2.md` | PFF AV_prog results (Task 42 Step 3) |
| `docs/results/43-press-resistance-v2.md` | PR2 PFF vs StatsBomb check (Task 43 Step 5) |
| `docs/results/46-movers-and-spatial-physical.md` | B2 S2: AV_out trade-off correlations (Task 46) |
| `docs/results/51-regista-scorecard.md` | AV counts and reliability on the scorecard (Task 51) |
| `docs/results/54-scorecard-v2-and-repo-prep.md` (this page) | AV counts and Card B AV stability (0.693) |
| `docs/results/00-data-audit.md` | PFF data audit counts (frames, matches, crosswalk) |
| `docs/BENCHMARK-v6.md` | AV results (Task 38) |
| `docs/BENCHMARK-v7.md` | PR2 PFF vs StatsBomb r = 0.778 |
| `docs/abstract/SSAC27-abstract-v2.md` | availability result in 64 WC2022 matches (the draft itself notes this at its line 115) |
| `docs/CHAT-HANDOFF.md` | AV / PFF numbers in the handoff summary |
| `docs/DECISIONS.md` | "57% of PFF player-positions are ESTIMATED" (D-005) |
| `docs/JOURNAL.md` (committed version) | PFF frame counts and crosswalk (for example 185,746 frames, 64/64) |
| `docs/scorecard/index.html` (Task 51 and now v2) | AV values per player (Card B) |
| `docs/scorecard/figure_praised.png` (Task 51) | AV panel for the Card B praised players |
| `docs/benchmark/manifest-v6.txt` | file names, sizes and checksums of PFF-derived tables (no measured values) |
| `docs/splits/praised_ids.csv`, `docs/results/53-tempo-replication.md` | presence of players in the PFF player map ("pff_map"); no measured values |

Not listed:
- `docs/scorecard/index_public.html` (no AV values) and `docs/scorecard/figure1.png` (Card A only).
- Code under `src/pff/` and other `src/` files. They process PFF data but contain no PFF-derived results.
- Brief files under `docs/specs/`, which describe PFF tests but contain no results.

### B6: command to make the repository public (NOT run)
The repository has no git remote. From the repo root, the author would run:
```
gh repo create Regista2 --public --source=. --remote=origin --push
```
This creates the GitHub repository, sets it as `origin`, and pushes. Alternatively, if a private GitHub repository already exists, run `gh repo edit <owner>/Regista2 --visibility public --accept-visibility-change-consequences`. Tags would need `git push origin --tags` separately.

## 4. Deviations from the brief
- **A1 source.** The tempo measures on all 1,551 matches were built from the existing built unit tables of Tasks 52 and 53, not from raw events, to respect the hard rule that replication data is read only through existing built tables. The units, context columns and definitions are those tables' own. Only the baselines were refit, once, over all matches.
- **A3 reference for the labels.** For HOLD_VARIATION the brief names no group reference. I used the mean of the raw SDs of the group's players who meet the floor.
- **A4 method for SD measures.** Task 38's method averages units per half. For HOLD_VARIATION the SD formula was applied per half (Task 52's generalised R1).
- **Card A reliability sources.** The tempo measures show Task 53's replication-league DM stabilities (S1-S5, 141 DMs), the only within-DM values from held-back data. The others show their Task 44 / 45 / 46 citations, as in Task 51.
- **B2 method.** The list comes from a keyword scan plus line-by-line reading. A PFF-derived number phrased without any of the keywords would be missed.
- **B3 README.** The "author's source" for PFF is described by pointing to `docs/DATA_LICENSES.md`. The logo is a TODO line: no StatsBomb Media Pack copy is in the repo. The open-data ZIP contains an image folder, but the brief asks specifically for the Media Pack.
- **B6.** Two forms are given because no remote exists yet.

## 5. Problems and surprises
- **Card B: most dimensions are not stable within the study sample's own DMs.**
  - PR2_flag_keep 0.052 (78 players), MOVE_ON_SPEED 0.092, Decision 0.281. These are low even relative to Task 51's cited values, which came from 2015/16 or other samples.
  - What this would invalidate, taken at face value: showing Card B's press resistance with the Tier 1B evidence of the 2015/16 and reserved data. On Card B it shows as Tier 3 by the brief's rule.
  - Only 37 of Card B's 111 DMs meet the press-resistance floor.
- **Tier labels differ between cards.** Press resistance is Tier 1B on Cards A and C but Tier 3 on Card B, because A4's automatic rule applies to Card B only.
- **Busquets' M4_ACCEL percentile is 8.1 against the abstract's "bottom 6%", and Kroos' M4_SWITCH is 95.7 against "top 7%".** I did not locate the computation behind the abstract's percentiles; the abstract's source map is the place to check.
- **`docs/scorecard/index.html` is 1.5 MB** (every player-dimension row embedded).

## 6. Questions for the research lead
1. **Card B tiers:** with A4 moving press resistance and W to Tier 3 on Card B, should Card B keep them as shown (Tier 3 with the reason), or show them differently?
2. **The abstract's percentiles for Busquets and Kroos** differ slightly from Card A's (Section 5). Which source should the abstract use?
3. **B2:** the author decides, per file, whether PFF-derived numbers can go public.

## 7. Files produced
- **Scripts:** `src/engine_v2/task54_scorecard.py` (A1-A6), `src/engine_v2/task54_outputs.py` (A5, A7).
- **Scorecard:** `docs/scorecard/index.html` (rebuilt), `docs/scorecard/index_public.html`, `docs/scorecard/figure1.png`.
- **Repo files:** `README.md`, `LICENSE`, `requirements.txt`, `.gitignore` (added `*.pkl`, `*.joblib`, `*.onnx`, `*.model`, `*.ubj`, `output/`, `outputs/`).
- `docs/DECISIONS.md`: D-017 appended.
- **Data, not committed:** `data/processed/scorecard_v2_card_{a,b,c}.parquet`, `data/engine_v2_task54.json`.
- **Commits:**
  - 164e291 and d23ba32: the stopped first run.
  - 59216d9: Part A, B2-B6 and this page.
- **Side effects:** a temporary local web server (127.0.0.1:8752) for the page check, now stopped.
- **Not staged (B5):** `docs/JOURNAL.md` (pre-existing uncommitted change) and `AGENTS.md` (untracked).

## 8. Confidence
- **Strong:** every carried-over scorecard value reproduces Task 51 exactly, and the one-fit tempo baselines use the saved Task 52 / 53 units.
- **Weakest links:**
  - Card B's small, unstable study-sample groups.
  - The keyword-based B2 list.
