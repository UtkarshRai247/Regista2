# Task 36: PFF / Gradient WC2022 ingest and alignment
Date: 2026-09-28
Status: BLOCKED at Step 1. Files must be downloaded by the author; Steps 2-4 have NOT RUN on the full data.

## Checklist
| Section | Status |
|---|---|
| Step 0 — commit brief alone | COMPLETE (3535c71) |
| Step 1 — download | BLOCKED (35 of 390 files fetched; see Section 3) |
| Step 2 — per-match audit (64) | NOT RUN (script written, tested on the Task 00 sample match 3812 only) |
| Step 3 (a)-(d) — alignment | NOT RUN (script written, tested on 3812 only) |
| Step 4 — per-frame tables | NOT RUN (script written, tested on 3812 only) |

## 1. Headline
Step 1 stopped: gdown fetched 35 of 390 Drive files (35 of 64 files in "Event Data/March 14, 2025", nothing else). Google Drive then refused further anonymous downloads ("Cannot retrieve the public link of the file ... or have had many accesses").
Nothing from Steps 2-4 has been run on the downloaded data.

## 2. What I did
- Step 0: committed the brief alone (3535c71).
- Disk: 159 GiB free (`df -h`), above the ~5 GB plus headroom required.
- Installed gdown 6.4.0 into `.venv`. This is the brief-authorised dependency; it also pulled in beautifulsoup4 4.15.0, filelock 4.0.5, PySocks 1.7.1, soupsieve 2.10 and tqdm 4.70.1.
- `gdown.download_folder(<folder URL>, skip_download=True, use_cookies=False)` listed all 390 files. gdown 6.4.0 did not apply the 50-file-per-folder cap.
- `gdown.download_folder(..., output="data/raw_pff", use_cookies=False, resume=True, retries=3)` downloaded 35 files (373 MB), then stopped. A second attempt and a re-listing failed with the Drive error above. No cookies, account or credentials were used. Partial `.part` files were deleted.
- Scripts for Steps 2-4 were written and run end to end on the Task 00 sample (PFF 3812 = StatsBomb 3857285) only, with outputs in the session scratchpad (not in data/):
  - `src/pff/align.py --stage players`
  - `src/pff/frames.py`
  - `src/pff/align.py --stage clock`
  These numbers are a test of the code, not a Step 2-4 result.

## 3. Numbers — Step 1 inventory (from the Drive listing)

| Subfolder | Expected | Present | Missing |
|---|---|---|---|
| Event Data (top level) | 64 json + spec v2.5 pdf | 0 | all 65 |
| Event Data/May 1, 2025 | 64 json + spec v2.4 pdf | 0 | all 65 |
| Event Data/March 14, 2025 | 64 json | 35 (all parse as JSON, 373 MB) | 29 |
| Tracking Data | 64 .jsonl.bz2 + spec v2.2 pdf | 0 | all 65 |
| Metadata | 64 json | 0 | all 64 |
| Rosters | 64 json | 0 | all 64 |
| top level | competitions.csv, players.csv, PFF FC Change Log.docx | 0 | all 3 |

The 64 PFF game ids (every game-level folder uses `<id>.json`, and Tracking uses `<id>.jsonl.bz2`) are:
3812-3859 (48 ids) and 10502-10517 (16 ids).
Missing from "Event Data/March 14, 2025": 3831-3859 (29 files).
No terms or licence file appears in the listing. The top-level files are two CSVs, the change-log docx and three spec PDFs.

Code test on sample 3812 only (not a result):
- 25 of 27 PFF shots paired to StatsBomb.
- Median offset +1.91 s, spread 8.47 s (flagged > 2 s), slope +0.019 s/min.
- Converted-position check: median 3.52 units for the ball and 3.52 units for the shooter.
- 678,566 rows (30,842 frames at 5 fps).
- 52 of 52 roster players mapped.

## 4. Deviations from the brief
- Steps 2-4 not run (blocked by Step 1, as the brief instructs).
- Operational choices already built into the untested-at-scale scripts, listed so they are visible before the run:
  - **Clock:** PFF clock = `periodElapsedTime`. `periodGameClockTime` is cumulative (period 2 starts at 2700 s), while StatsBomb timestamps are period-relative. Metadata `startPeriod*` is null for the 10502-10517 matches, so it is not used.
  - **Event Data version:** the top-level "Event Data" version (shipped with the v2.5 spec) is the one used.
  - **Positions:** raw, not smoothed, arrays.
  - **Velocity:** backward difference over 3 raw frames (~0.1 s).
  - **Downsampling:** the frame nearest each 0.2 s step.
  - **Ball:** stored in each row's team frame.
  - **Periods:** clock pairing and the table cover periods 1-4 only.
  - **Name confirmation:** similarity threshold 0.6.
  - **Crosswalk:** re-implemented against local StatsBomb matches rather than importing `audit_alignment.py` (which is unmodified).

## 5. Problems and surprises
- Drive stopped serving anonymous downloads after 35 files. The error names a permission or "many accesses" (quota) cause. The first failure (a Google-native docx) and the later refusals may have different causes; not investigated further.
- The sample tracking file has 889 frames with a duplicated video timestamp. The script counts these and guards the velocity calculation against them.
- In the sample, the offset spread across paired shots (8.5 s) is far above the brief's 2 s flag. The median (1.9 s) matches Task 00's ~2 s.

## 6. Questions for the research lead
- Q1: Which Event Data version should be used? There are three: top level (v2.5 spec), May 1 2025 (v2.4 spec) and March 14 2025.
- Q2: The operational choices in Section 4 (clock field, raw vs smoothed, velocity window, ball frame, periods 1-4).

## 7. Files produced
- `src/pff/align.py`, `src/pff/frames.py` (new; `src/audit_pff.py` and `src/audit_alignment.py` untouched).
- `data/raw_pff/Event Data/March 14, 2025/` holds 35 json files (not committed).
- Side effects:
  - gdown and its 5 dependencies installed in `.venv`.
  - Test outputs in the session scratchpad only.
- Commits: brief 3535c71; this page and the scripts 5ea026f.

## 8. Confidence
There is no result yet. The scripts ran correctly end to end on one match, and the coordinate and clock logic behaved as expected there.
