# Task 36 — Bring in the PFF / Gradient WC2022 tracking data (ingest and align only)

Written 2026-09-28 by the research lead. Infrastructure only: no
analysis, no metric, no outcome is computed. The analysis plan (Task 37)
is written after this task's audit and before any analysis runs.

Background: Task 00 (docs/results/00-data-audit.md) already audited one
sample match (3812), crosswalked all 64 PFF matches to StatsBomb's 64
WC2022 matches by date and teams (`src/audit_alignment.py`,
`data/pff_matches.json`), and found a constant ~2 s clock offset on two
goals. It also found 57% of player-frames flagged ESTIMATED (not seen by
camera) and ~64% LOW confidence.

Source: the author's Drive folder
https://drive.google.com/drive/folders/1_a_q1e9CXeEPJ3GdCv_3-rNO3gPqacfa
(subfolders: Event Data, Tracking Data, Metadata, Rosters).
Destination: `data/raw_pff/` (gitignored; nothing from it is ever
committed). Usage terms are handled by the author at repo-publication
time; this task only records what terms file, if any, comes with the
data.

## Step 0 — Commit this brief alone. Record the hash.

## Step 1 — Download
Try `gdown` (pip install into the .venv) for each subfolder. Google
Drive folder downloads via gdown are capped at 50 files per folder; if
any subfolder cannot be fully fetched, fetch the rest by file ID if
gdown lists them, and otherwise STOP after listing exactly which files
are missing so the author can download them in a browser into the right
subfolder. Do not use any other account or credentials.
Check free disk space first (need about 5 GB plus headroom).
Report per subfolder: files expected (64 per game-level folder), files
present, total size, any corrupt/unreadable file (bz2 test for
tracking).

## Step 2 — Per-match audit (all 64)
Using `src/audit_pff.py`'s logic generalised to all matches (new script,
do not edit the original): frames, fps, periods, ball-present share,
player-frame visibility (VISIBLE vs ESTIMATED) and confidence shares,
coordinate bounds. Report the distribution across matches and any match
that is an outlier.

## Step 3 — Align to StatsBomb
(a) Match level: reuse `data/pff_matches.json` / `audit_alignment.py`;
    confirm 64/64 and write a table pff_game_id -> StatsBomb match_id.
(b) Clock: per match and per period, estimate the PFF-vs-StatsBomb clock
    offset from every shot/goal that can be paired (same team, same
    period, nearest time within 10 s). Report per-match median offset,
    its spread, and any drift (offset vs match time slope). Flag matches
    where the spread exceeds 2 s.
(c) Players: map PFF player IDs to StatsBomb player IDs using team +
    shirt number from rosters, confirmed by name similarity. Report the
    share mapped, and list every unmapped or ambiguous player.
(d) Coordinates: write the conversion from PFF metres (centre origin,
    105 x 68 stated) to StatsBomb units (120 x 80, corner origin,
    team-relative as established in Task 24), and verify it on paired
    shots: median distance between StatsBomb shot location and the
    converted PFF ball/shooter position at the aligned time.

## Step 4 — A standard per-frame table (downsampled)
For each match, write `data/processed/pff/<statsbomb_match_id>.parquet`
at 5 frames per second: time (StatsBomb clock), period, ball x/y (if
present), and per player: StatsBomb player_id, team, x/y in StatsBomb
units, velocity (from the 30 fps positions before downsampling), and
the visibility and confidence flags. Report rows and size.

## HARD RULES
- No metric, model or outcome computation.
- Nothing under data/ is committed. No credentials entered anywhere.
- Do not modify `src/audit_pff.py` or `src/audit_alignment.py`.
- Memory gate as in Task 25; one match in memory at a time.
- No memory writes. Don't edit docs/JOURNAL.md. No interpretation.
- When finished, reply only that the task is done plus commit hashes,
  or, if Step 1 stops, the list of files the author must download.

## Output
docs/results/36-pff-ingest.md (template). Commit per rule 9.
