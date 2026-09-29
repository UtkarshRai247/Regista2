# Task 44: A fresh, untouched dataset: StatsBomb 2015/16 big-five leagues
Date: 2026-09-28
Status: PARTIAL (Step 1 only; Steps 2-5 NOT RUN — the session's usage limit was reached)

## Checklist
| Section | Status |
|---|---|
| Step 0 — brief committed alone | COMPLETE (5b80f43; operational note f89863f, both by the research lead) |
| Memory gate | COMPLETE (57% free, ~4.88 GB, 17:00 PDT) |
| Step 1 — ingest | COMPLETE |
| Step 2 — press-resistance gate (study sample) | NOT RUN |
| Step 3 — 2015/16 measures | NOT RUN |
| Step 4 — confirmatory tests | NOT RUN |
| Step 5 — DM tables | NOT RUN |

## 1. Headline
Step 1 only (ingest, no analysis).
- All 1,551 listed 2015/16 matches were ingested with no problems.
- Every team-period with shots (6,155) has a mean shot x > 60 (share 1.0000), so the events are team-relative.
- The Bundesliga list has only 34 matches, and Ligue 1 has 377.

## 2. What I did
- `.venv/bin/python src/engine_v2/task44_ingest.py`:
  - Reads the author's unzipped open-data copy (`data/raw_1516/open-data-master/`). Match lists come from `data/matches/<comp>/27.json`; events from `data/events/<id>.json`.
  - Flattens each events file with statsbombpy's own `entities.events` + `helpers.filter_and_group_events` (what `sb.events` does after fetching).
  - Writes `data/raw_1516/events/<id>.parquet` and `data/raw_1516/matches/<comp>_27.parquet`.
  - Checks row counts against each JSON file's length.

## 3. Numbers
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
