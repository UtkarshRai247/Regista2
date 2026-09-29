# Task 44: A fresh, untouched dataset: StatsBomb 2015/16 big-five leagues
Date: 2026-09-28
Status: PARTIAL (Steps 1-2 run; Steps 3-5 NOT RUN yet — interim commit after Step 2 required by the brief)

## Checklist
| Section | Status |
|---|---|
| Step 0 — brief committed alone | COMPLETE (5b80f43; operational note f89863f, both by the research lead) |
| Memory gate | COMPLETE (57% / 4.88 GB at 17:00 before Step 1; 54% / 4.53 GB at 18:43 before Step 2) |
| Step 1 — ingest | COMPLETE |
| Step 2 — press-resistance gate (study sample) | COMPLETE (GATE PASS) |
| Step 3 — 2015/16 measures | NOT RUN |
| Step 4 — confirmatory tests | NOT RUN |
| Step 5 — DM tables | NOT RUN |

## 1. Headline
Steps 1-2 only. **Step 2 gate PASSES:** on the 292-match study sample, player-level event-only press resistance (PR2_flag_keep) correlates r = 0.840, 95% CI [0.784, 0.881], with Task 43's frame-based PR2_keep (148 players with ≥50 pressured receptions in both; bar 0.70). Press resistance will therefore be run on 2015/16.
Step 1 (ingest, no analysis):
- All 1,551 listed 2015/16 matches were ingested with no problems.
- Every team-period with shots (6,155) has a mean shot x > 60 (share 1.0000), so the events are team-relative.
- The Bundesliga list has only 34 matches, and Ligue 1 has 377.

## 2. What I did
- `.venv/bin/python -W ignore src/engine_v2/task44_gate.py` (Step 2, study sample, run before any 2015/16 analysis):
  - Uses Task 43's spell outcomes (`task43_spells.parquet`).
  - PRESSURED_flag = `under_pressure` on the Ball Receipt* OR on the receiver's first on-ball event of the spell (his first Pass, Carry, Dribble, Shot, Miscontrol or Dispossessed after the receipt, same possession).
  - Baseline: Task 42's classifier settings, with event-only context (receipt location x, y, play pattern, period, minute), on Task 35's folds.
- `.venv/bin/python src/engine_v2/task44_ingest.py`:
  - Reads the author's unzipped open-data copy (`data/raw_1516/open-data-master/`). Match lists come from `data/matches/<comp>/27.json`; events from `data/events/<id>.json`.
  - Flattens each events file with statsbombpy's own `entities.events` + `helpers.filter_and_group_events` (what `sb.events` does after fetching).
  - Writes `data/raw_1516/events/<id>.parquet` and `data/raw_1516/matches/<comp>_27.parquet`.
  - Checks row counts against each JSON file's length.

## 3. Numbers

### Step 2 — gate (study sample, 292 matches)
- Completed receipts: 271,830. PRESSURED_flag: 62,006 (flag on the receipt 19,506; on the first spell event only 42,500).
- Units with a spell outcome: 59,911. Of these, 25,136 are also in Task 43's frame-based pressured set.
- keep_spell base rate 0.607, baseline OOF AUC 0.602. fwd_spell base rate 0.225, AUC 0.644.
- **Player mean PR2_flag_keep vs Task 43 PR2_keep: r = 0.840 [0.784, 0.881], n = 148 → GATE PASS (≥ 0.70).**

### Step 1 — ingest
| Competition | matches listed | ingested | events |
|---|---|---|---|
| Premier League (2) | 380 | 380 | 1,313,773 |
| Ligue 1 (7) | 377 | 377 | 1,358,593 |
| 1. Bundesliga (9) | 34 | 34 | 115,240 |
| La Liga (11) | 380 | 380 | 1,295,354 |
| Serie A (12) | 380 | 380 | 1,353,739 |

Coordinate check: 6,155 team-periods with shots, and a share of 1.0000 have mean shot x > 60.

## 4. Deviations from the brief
- **Coordinate check:** only task24_evidence.py's part (i) was run. Its parts (ii) and (iii) need 360 frames, which 2015/16 does not have.
- **Decisions already made by the author when asked, for the steps not yet run:**
  - eligible pass = the engine rule minus the frame condition;
  - g = Task 35's feature set minus the 360-derived features.

## 5. Problems and surprises
- The Bundesliga has 34 matches, not a full season, and Ligue 1 has 377 matches, not 380. These are the files in StatsBomb's lists; nothing listed is missing.

## 6. Questions for the research lead
- None.

## 7. Files produced
- `src/engine_v2/task44_ingest.py`.
- `data/raw_1516/events/` (1,551 parquet), `data/raw_1516/matches/`, `data/engine_v2_task44_step1.json` (not committed).

## 8. Confidence
Ingest verified by row counts. Nothing else has been run yet.
