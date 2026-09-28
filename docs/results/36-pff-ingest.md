# Task 36: PFF / Gradient WC2022 ingest and alignment
Date: 2026-09-28
Status: COMPLETE (every section run; operational choices in Section 4). An earlier version of this page (commit 5ea026f) recorded Step 1 as BLOCKED. This version replaces it after the author downloaded the files.

## Checklist
| Section | Status |
|---|---|
| Step 0 — commit brief alone | COMPLETE (3535c71) |
| Step 1 — download + integrity | COMPLETE (gdown fetched 35 files, then Drive refused; the author downloaded the rest in a browser, see Section 2) |
| Step 2 — per-match audit, all 64 | COMPLETE |
| Step 3(a) — match crosswalk | COMPLETE (64/64) |
| Step 3(b) — clock offsets | COMPLETE |
| Step 3(c) — player mapping | COMPLETE (99.81% mapped; 6 flagged entries listed) |
| Step 3(d) — coordinate conversion + check | COMPLETE |
| Step 4 — 5 fps per-frame tables | COMPLETE (64 files) |
| Memory gate | COMPLETE (69% free, ~5.78 GB before the tracking pass) |

## 1. Headline
All 64 matches were ingested, crosswalked (64/64), audited and written as 5 fps tables: 43,498,265 rows, 0.55 GB.
Every one of the 64 matches exceeds the brief's 2 s clock-spread flag. The median offset per match ranges from +0.26 to +2.07 s, and within-match spread ranges from 2.1 to 12.0 s.
The converted PFF positions sit a median 3.0 StatsBomb units from StatsBomb's shot location for the ball, and 3.0 units for the shooter (n=1,371 / 1,374 paired shots). The shooter median rises to 11.2 units when the shooter is ESTIMATED rather than VISIBLE (n=225).

## 2. What I did
- **Step 0:** committed the brief alone (3535c71).
- **Step 1:**
  - Disk had 159 GiB free.
  - Installed gdown 6.4.0 into `.venv` (brief-authorised). It pulled in beautifulsoup4 4.15.0, filelock 4.0.5, PySocks 1.7.1, soupsieve 2.10 and tqdm 4.70.1.
  - gdown, without cookies or credentials, listed all 390 files (no 50-file cap in 6.4.0). It downloaded 35, then Drive refused with "Cannot retrieve the public link ... or have had many accesses".
  - Stopped per the brief and gave the author the missing list (commit 5ea026f). The author downloaded the folder in a browser into two folders at the repo root, "FIFA World Cup 2022" and "FIFA World Cup 2022 2".
  - The two folders' tracking files were disjoint, 47 + 18 = 65 (64 matches plus the spec PDF). The 35 gdown-fetched files were byte-identical to the author's copies.
  - I moved everything into `data/raw_pff/` and removed the now-empty root folders.
  - Integrity: every `.json` parsed, and every `.jsonl.bz2` fully decompressed (`bz2` read to EOF). The inventory is in `data/pff_task36_inventory.json`.
- **Step 3(a)(c):** `.venv/bin/python src/pff/align.py --stage players`.
- **Steps 2, 4:** `.venv/bin/python src/pff/frames.py`, one streaming pass per tracking file, one match in memory at a time. It also collected shot clocks and 30 fps shot-window snapshots for Step 3(b)(d).
- **Step 3(b)(d):** `.venv/bin/python src/pff/align.py --stage clock`, which also writes `time_sb` into each table.
- **Tables:** `.venv/bin/python src/pff/report.py`.
- **Reproduce:** the four commands above, in that order.
- **Pre-run test:** the full pipeline was first run on the Task 00 sample (3812) in the session scratchpad.

## 3. Numbers

### Step 1 — inventory (all files present, none corrupt)
| Subfolder | Expected | Present | Corrupt | Size | Other files |
|---|---|---|---|---|---|
| Event Data (top level) | 64 | 64 | 0 | 1.150 GB | PFF FC Event Data Specification v2.5.pdf |
| Event Data/May 1, 2025 | 64 | 64 | 0 | 1.065 GB | PFF FC Event Data Specification v2.4.pdf |
| Event Data/March 14, 2025 | 64 | 64 | 0 | 0.696 GB | — |
| Tracking Data (.jsonl.bz2) | 64 | 64 | 0 | 2.776 GB | PFF FC Tracking Data Specification v2.2.pdf |
| Metadata | 64 | 64 | 0 | <0.001 GB | — |
| Rosters | 64 | 64 | 0 | <0.001 GB | — |
| Top level | — | — | — | — | competitions.csv, players.csv, PFF FC Change Log.docx |

Total 5.3 GB. **No terms-of-use or licence file came with the data.** The top level holds only the two CSVs and the change-log docx; the three PDFs are data specifications.

### Step 2 — audit distribution across 64 matches

| Quantity | min | Q1 | median | Q3 | max |
|---|---|---|---|---|---|
| frames | 171,128 | 178,610 | 181,920 | 187,418 | 255,182 |
| implied fps (lowest period) | 29.98 | 30.04 | 30.06 | 30.08 | 30.15 |
| ball-present share | 0.532 | 0.650 | 0.681 | 0.700 | 0.788 |
| player-frames VISIBLE | 0.252 | 0.332 | 0.377 | 0.414 | 0.513 |
| player-frames ESTIMATED | 0.487 | 0.586 | 0.623 | 0.668 | 0.748 |
| confidence HIGH | 0.105 | 0.192 | 0.233 | 0.284 | 0.364 |
| confidence MEDIUM | 0.033 | 0.059 | 0.072 | 0.091 | 0.143 |
| confidence LOW | 0.556 | 0.639 | 0.690 | 0.717 | 0.825 |
| x min / max (m) | −60.00 / 52.15 | | −53.59 / 53.94 | | −52.23 / 60.28 |
| y min / max (m) | −41.68 / 35.43 | | −37.19 / 37.30 | | −35.64 / 40.92 |
| frames with duplicated video timestamp | 54 | 557 | 649 | 829 | 1,245 |

- Metadata fps is 29.97 in all 64 matches.
- Pitch is 105 × 68 in all.
- Periods in tracking: (1, 2) in 61 matches and (1, 2, 3, 4) in 3.
- Frames outside periods 1-4: 0. Frames with a null clock: 0.
- `periodElapsedTime` − (video time − metadata startPeriod): max 0.0005 s over the 59 matches whose metadata has startPeriod. The other 5 (knockout ids) have null startPeriod.

Outliers (outside Q1 − 1.5 IQR, Q3 + 1.5 IQR; reported, not acted on):
- frames and rows: 10517, 10506, 10508 (the 3 extra-time matches), and 3813 (211,122 frames).
- implied fps: 3848 (30.15), 3815, 3821, 3817 (29.98).
- ball-present: 3852 (0.788), 3831 (0.780), 3844 (0.532), 3840 (0.568).
- confidence MEDIUM: 3850 (0.143).
- x_max: 10508 (60.28).
- y_min: 3839 (−41.68), 3817 (−39.93).
- y_max: 3849 (40.92), 3832 (40.41).
- duplicated timestamps: 10506 (1,245); 3815, 3821 and 3817 (54-57, low).

### Step 3(a) — match crosswalk
64/64 matched unambiguously by date + teams. The table is `data/processed/pff/crosswalk.csv` (pff_game_id → statsbomb_match_id). The pairs are in the Step 3(b) table below.

### Step 3(b) — clock (offset = StatsBomb − PFF, seconds; periods 1-4)
- PFF shots: 1,501. StatsBomb shots: 1,453. Paired: 1,374.
- 58 PFF shots had no tracking frame within 0.5 s of their event time, so they could not be clocked or paired.
- Median of per-match medians: **+0.90 s** (range +0.26 to +2.07).
- **64/64 matches flagged (spread > 2 s)**; spreads range 2.12 to 12.03 s.
- Drift slope ranges −0.032 to +0.041 s per match-minute (median +0.003).
- Every period had at least one pair, so each match-period median offset was used for time_sb (no fallback to the match median).

| PFF | StatsBomb | Match | PFF shots | SB shots | paired | median | IQR | spread | slope s/min |
|---|---|---|---|---|---|---|---|---|---|
| 3812 | 3857285 | Senegal v Netherlands | 27 | 25 | 25 | 1.909 | 1.589 | 8.473 | 0.019 |
| 3813 | 3857271 | England v Iran | 20 | 21 | 20 | 0.664 | 1.052 | 4.341 | 0.006 |
| 3814 | 3857286 | Qatar v Ecuador | 16 | 11 | 11 | 0.879 | 1.490 | 2.123 | −0.009 |
| 3815 | 3857282 | United States v Wales | 13 | 13 | 13 | 1.096 | 1.176 | 3.649 | 0.018 |
| 3816 | 3857300 | Argentina v Saudi Arabia | 24 | 18 | 18 | 0.667 | 1.138 | 4.636 | −0.008 |
| 3817 | 3857254 | Denmark v Tunisia | 26 | 24 | 21 | 1.351 | 2.615 | 4.516 | 0.015 |
| 3818 | 3857265 | Mexico v Poland | 21 | 17 | 17 | 0.326 | 0.996 | 6.428 | 0.014 |
| 3819 | 3857279 | France v Australia | 26 | 27 | 26 | 0.578 | 0.084 | 4.869 | −0.001 |
| 3820 | 3857277 | Morocco v Croatia | 14 | 13 | 13 | 0.440 | 1.279 | 2.948 | −0.021 |
| 3821 | 3857284 | Germany v Japan | 40 | 38 | 36 | 0.577 | 1.078 | 5.435 | −0.003 |
| 3822 | 3857291 | Spain v Costa Rica | 18 | 17 | 16 | 0.850 | 1.098 | 4.619 | 0.002 |
| 3823 | 3857268 | Belgium v Canada | 32 | 31 | 30 | 1.038 | 1.419 | 5.363 | 0.006 |
| 3824 | 3857290 | Switzerland v Cameroon | 17 | 15 | 15 | 1.867 | 1.642 | 6.580 | 0.041 |
| 3825 | 3857287 | Uruguay v South Korea | 17 | 17 | 16 | 1.387 | 1.457 | 5.666 | 0.029 |
| 3826 | 3857298 | Portugal v Ghana | 22 | 20 | 20 | 0.648 | 1.812 | 8.131 | 0.008 |
| 3827 | 3857258 | Brazil v Serbia | 27 | 28 | 25 | 0.908 | 1.939 | 5.294 | 0.014 |
| 3828 | 3857273 | Wales v Iran | 31 | 31 | 29 | 1.611 | 2.207 | 7.147 | 0.020 |
| 3829 | 3857301 | Qatar v Senegal | 23 | 22 | 20 | 0.367 | 1.198 | 5.284 | −0.010 |
| 3830 | 3857274 | Netherlands v Ecuador | 17 | 17 | 16 | 0.279 | 0.963 | 3.146 | −0.012 |
| 3831 | 3857272 | England v United States | 18 | 18 | 18 | 0.702 | 1.724 | 8.850 | 0.014 |
| 3832 | 3857288 | Tunisia v Australia | 24 | 23 | 22 | 1.734 | 1.498 | 7.868 | 0.029 |
| 3833 | 3857297 | Poland v Saudi Arabia | 26 | 26 | 24 | 0.736 | 0.956 | 4.471 | −0.003 |
| 3834 | 3857266 | France v Denmark | 31 | 31 | 29 | 0.735 | 1.267 | 7.329 | −0.001 |
| 3835 | 3857289 | Argentina v Mexico | 9 | 9 | 9 | 0.639 | 1.251 | 4.352 | 0.015 |
| 3836 | 3857295 | Japan v Costa Rica | 18 | 17 | 17 | 0.976 | 1.851 | 5.444 | 0.011 |
| 3837 | 3857283 | Belgium v Morocco | 21 | 20 | 20 | 1.090 | 2.785 | 9.445 | 0.028 |
| 3838 | 3857281 | Croatia v Canada | 22 | 21 | 21 | 1.107 | 1.341 | 5.661 | 0.024 |
| 3839 | 3857263 | Spain v Germany | 20 | 18 | 17 | 1.196 | 1.252 | 3.600 | −0.032 |
| 3840 | 3857259 | Cameroon v Serbia | 31 | 28 | 27 | 0.746 | 1.978 | 6.539 | 0.002 |
| 3841 | 3857299 | South Korea v Ghana | 31 | 28 | 28 | 0.582 | 1.083 | 6.417 | 0.011 |
| 3842 | 3857269 | Brazil v Switzerland | 16 | 19 | 15 | 0.486 | 1.331 | 3.009 | 0.007 |
| 3843 | 3857270 | Portugal v Uruguay | 27 | 26 | 24 | 1.025 | 1.665 | 12.034 | −0.002 |
| 3844 | 3857267 | Ecuador v Senegal | 22 | 22 | 22 | 1.323 | 1.606 | 5.654 | −0.000 |
| 3845 | 3857294 | Netherlands v Qatar | 20 | 18 | 18 | 1.235 | 1.626 | 5.570 | 0.004 |
| 3846 | 3857261 | Wales v England | 23 | 25 | 23 | 0.429 | 1.727 | 5.020 | −0.004 |
| 3847 | 3857278 | Iran v United States | 17 | 16 | 15 | 0.679 | 1.070 | 6.565 | −0.014 |
| 3848 | 3857257 | Australia v Denmark | 23 | 22 | 21 | 1.745 | 1.312 | 5.677 | 0.003 |
| 3849 | 3857275 | Tunisia v France | 15 | 15 | 13 | 2.070 | 0.993 | 5.863 | 0.004 |
| 3850 | 3857264 | Poland v Argentina | 28 | 28 | 26 | 1.684 | 2.329 | 9.536 | 0.000 |
| 3851 | 3857260 | Saudi Arabia v Mexico | 38 | 36 | 36 | 0.897 | 0.825 | 11.353 | 0.006 |
| 3852 | 3857296 | Croatia v Belgium | 24 | 27 | 24 | 0.858 | 1.470 | 4.474 | −0.023 |
| 3853 | 3857276 | Canada v Morocco | 13 | 12 | 12 | 0.472 | 0.468 | 6.710 | −0.020 |
| 3854 | 3857255 | Japan v Spain | 19 | 18 | 18 | 1.442 | 1.366 | 5.246 | 0.009 |
| 3855 | 3857292 | Costa Rica v Germany | 41 | 38 | 38 | 0.257 | 2.311 | 7.572 | −0.007 |
| 3856 | 3857293 | Ghana v Uruguay | 23 | 21 | 21 | 1.320 | 1.543 | 4.919 | −0.002 |
| 3857 | 3857262 | South Korea v Portugal | 26 | 25 | 22 | 0.493 | 1.588 | 3.202 | 0.011 |
| 3858 | 3857256 | Serbia v Switzerland | 24 | 26 | 24 | 0.533 | 0.403 | 3.392 | 0.006 |
| 3859 | 3857280 | Cameroon v Brazil | 30 | 28 | 28 | 0.976 | 1.095 | 4.425 | 0.004 |
| 10502 | 3869117 | Netherlands v United States | 31 | 29 | 29 | 0.262 | 1.786 | 5.199 | 0.005 |
| 10503 | 3869151 | Argentina v Australia | 19 | 19 | 19 | 1.373 | 1.150 | 8.415 | 0.007 |
| 10504 | 3869152 | France v Poland | 29 | 28 | 26 | 0.452 | 1.586 | 5.601 | −0.015 |
| 10505 | 3869118 | England v Senegal | 17 | 18 | 17 | 0.976 | 1.610 | 5.136 | −0.004 |
| 10506 | 3869219 | Japan v Croatia | 28 | 30 | 27 | 0.598 | 1.426 | 9.039 | 0.004 |
| 10507 | 3869253 | Brazil v South Korea | 30 | 26 | 26 | 1.497 | 1.630 | 7.099 | −0.016 |
| 10508 | 3869220 | Morocco v Spain | 20 | 18 | 17 | 0.933 | 1.039 | 3.451 | −0.000 |
| 10509 | 3869254 | Portugal v Switzerland | 24 | 25 | 22 | 1.528 | 1.402 | 4.253 | −0.002 |
| 10510 | 3869420 | Croatia v Brazil | 23 | 29 | 21 | 0.420 | 2.013 | 5.948 | −0.013 |
| 10511 | 3869321 | Netherlands v Argentina | 13 | 21 | 12 | 1.127 | 0.533 | 2.914 | −0.001 |
| 10512 | 3869486 | Morocco v Portugal | 22 | 21 | 20 | 1.719 | 1.975 | 9.096 | −0.019 |
| 10513 | 3869354 | England v France | 24 | 24 | 23 | 0.746 | 0.881 | 3.994 | 0.006 |
| 10514 | 3869519 | Argentina v Croatia | 22 | 21 | 21 | 1.471 | 1.792 | 4.820 | 0.020 |
| 10515 | 3869552 | France v Morocco | 31 | 27 | 26 | 0.898 | 1.303 | 8.355 | 0.002 |
| 10516 | 3869684 | Croatia v Morocco | 22 | 21 | 19 | 2.047 | 1.963 | 5.379 | −0.023 |
| 10517 | 3869685 | Argentina v France | 35 | 30 | 30 | 1.433 | 1.302 | 6.183 | −0.011 |

### Step 3(c) — players
- Roster entries: 3,230. Mapped (team + shirt, name confirmed ≥0.6): **3,224 (99.81%)**.
- **Flagged, not mapped (6):** Morocco #1, PFF "Bono", against StatsBomb "Yassine Bounou" (name score 0.44), in PFF 3820, 3853, 10508, 10512, 10515 and 10516. The team + shirt match is unique in each case. The name rule flags it, and I did not override it. See Q3.
- No roster entry lacked a team + shirt match, and none had multiple matches.
- StatsBomb lineup players with no PFF roster entry (14):
  - Bassam Hisham Al Rawi (Qatar #15, 3857294)
  - Stephen Eustáquio (Canada #7, 3857276)
  - Alireza Beiranvand (Iran #1, 3857273)
  - Fodé Ballo Touré (Senegal #12, 3857301)
  - Cheikhou Kouyaté (Senegal #8, 3857301 and 3857267)
  - James Maddison (England #25, 3857271 and 3857272)
  - Romelu Lukaku (Belgium #9, 3857268)
  - Danilo (Brazil #2, 3857269)
  - Riyadh Sharahili (Saudi Arabia #26, 3857300)
  - Yassine Bounou (Morocco #1, 3857283)
  - Joshua Sargent (United States #24, 3869117)
  - Nayef Aguerd (Morocco #5, 3869552)

### Step 3(d) — coordinate conversion and check
Conversion (PFF metres, centre origin, L × W from metadata, here always 105 × 68) to StatsBomb units (120 × 80, corner origin), in the named team's own attacking frame:
- Attacking PFF +x: sb_x = (x + L/2)·120/L, sb_y = (W/2 − y)·80/W.
- Attacking PFF −x: sb_x = (L/2 − x)·120/L, sb_y = (y + W/2)·80/W.
- Attack direction comes from metadata `homeTeamStartLeft` (periods 1-2, flipped in 2) and `homeTeamStartLeftExtraTime` (periods 3-4, flipped in 4).

The script's self-check asserts corners, centre and the 180° relation. The results below were not used to adjust the conversion.

Distance (StatsBomb units) between the StatsBomb shot location and the converted PFF position at the aligned time. The nearest 30 fps frame was never more than 0.017 s from the target.

| | n | q10 | q25 | median | q75 | q90 | share ≤2 | share ≤5 |
|---|---|---|---|---|---|---|---|---|
| ball | 1,371 | 0.96 | 1.70 | **3.01** | 5.43 | 10.36 | 0.329 | 0.715 |
| shooter | 1,374 | 0.90 | 1.57 | **2.96** | 6.76 | 13.61 | 0.349 | 0.672 |

- By flag, ball: VISIBLE median 2.23 (n=734), ESTIMATED 4.10 (n=637).
- By flag, shooter: VISIBLE 2.45 (n=1,149), ESTIMATED 11.23 (n=225).
- Per-match median ball distance ranges from 1.27 to 7.22 (median 2.94).

### Step 4 — per-frame tables
`data/processed/pff/<statsbomb_match_id>.parquet`, 64 files. Total **43,498,265 rows**, 1,977,071 frames, 0.551 GB.
- Per match: rows 626,653-933,302 (median 665,458); size 8.1-11.5 MB (median 8.4).
- One row per (frame, player). Columns: period, pff_clock (periodElapsedTime), time_sb, video_time, side, team, jersey, player_id (StatsBomb), x, y, vx, vy (StatsBomb units, per second, own-team frame), visibility, confidence, ball_x, ball_y (same row's team frame), ball_visibility.
- Rows without a StatsBomb player_id: 187,653, all from the 6 flagged Morocco #1 entries.

## 4. Deviations from the brief
- **Step 1 route:** gdown fetched 35 files, then Drive refused. The rest were downloaded by the author in a browser, as the brief allows. I moved them from the repo root into `data/raw_pff/`.
- **Clock field:** PFF's `periodGameClockTime` is cumulative (period 2 starts at 2700 s), and StatsBomb timestamps are period-relative. I used `periodElapsedTime`, which is period-relative and agrees with metadata startPeriod to 0.0005 s. Metadata startPeriod is null for 5 matches, so it is not used for the clock.
- **Shot pairing and clock:** a PFF shot's clock is the tracking frame nearest its event startTime, within 0.5 s. The 58 shots with no such frame were not paired. Pairing is greedy one-to-one, smallest gap first. Periods 1-4 only (no tracking file contains a shoot-out).
- **time_sb:** pff_clock + that match-period's median offset.
- **Event Data version:** the top-level version (v2.5 spec) was used for shots and shooters. Three versions exist; see Q1.
- **Positions:** raw `homePlayers`/`awayPlayers`, not the `*Smoothed` arrays.
- **Velocity:** backward difference over the previous 3 raw frames of the same player (~0.1 s), NaN if that span is over 0.2 s or zero.
- **Downsampling:** per period, the frame nearest each 0.2 s step of periodElapsedTime.
- **Ball coordinates:** stored in each row's team frame, so the same ball appears in two frames per 5 fps frame.
- **Name confirmation:** difflib ratio ≥ 0.6 on normalised names, or token-subset. The Morocco #1 entries fail this rule and are left flagged.
- **Crosswalk:** re-implemented against local StatsBomb matches; `src/audit_alignment.py` and `src/audit_pff.py` are unmodified.
- **Extra files not named by the brief:** `src/pff/report.py` (formats the tables above), and `data/processed/pff/_work/` (per-match shot clocks and 30 fps shot-window snapshots used by Step 3).

## 5. Problems and surprises
- **The clock offset is not constant.** Spread exceeds 2 s in all 64 matches, and the IQR is ~1-2.8 s in most. Taken at face value, this invalidates Task 00's "constant ~2 s offset" description, which was based on two goals. It also means a single per-period offset aligns tracking to StatsBomb events only to within a few seconds for a given event. Drift slopes are small (|slope| ≤ 0.041 s/min), so the variation is event-to-event rather than a trend across the match.
- **The median offset is +0.90 s across matches**, not the ~2 s Task 00 found. The sample match 3812 itself has a median of +1.91.
- **ESTIMATED positions are far from StatsBomb's shot location.** Shooter median 11.2 units, against 2.4 for VISIBLE. ESTIMATED is 49-75% of player-frames, and LOW confidence is 56-83%.
- **Missing extra time:** the tracking for 10510 (Croatia v Brazil) and 10511 (Netherlands v Argentina) has no periods 3-4, although StatsBomb has periods 3-5 for both. Only 3 of the 5 extra-time matches have extra-time tracking.
- **Duplicated video timestamps:** 54-1,245 frames per match.
- **Coordinates beyond the pitch:** up to ±60.3 m in x and ±41.7 m in y.
- **No terms or licence file** came with the data.

## 6. Questions for the research lead
- Q1: Which Event Data version should be used (top level with v2.5 spec, used here; May 1 2025 with v2.4; or March 14 2025)?
- Q2: Given every match exceeds the 2 s spread flag, is a per-period median offset the intended alignment, or should events be aligned individually?
- Q3: Should the Morocco #1 "Bono" / "Yassine Bounou" entries (6 matches, 187,653 rows) be mapped despite the name rule?
- Q4: Operational choices in Section 4: clock field, raw vs smoothed positions, velocity window, ball frame, periods 1-4.
- Q5: Should the 2 matches missing extra-time tracking be recorded anywhere beyond this page?

## 7. Files produced
- `src/pff/align.py`, `src/pff/frames.py`, `src/pff/report.py`.
- `data/raw_pff/` (5.3 GB, raw, never committed).
- `data/processed/pff/`:
  - `<sb_match_id>.parquet` × 64
  - `crosswalk.csv`
  - `player_map.csv`
  - `shot_pairs.parquet`
  - `shot_coordinate_check.parquet`
  - `_work/` (128 files)
- `data/pff_task36_inventory.json`, `data/pff_task36_players.json`, `data/pff_task36_audit.json`, `data/pff_task36_clock.json`.
- None of the data/ files are committed.
- Side effects:
  - gdown and 5 dependencies installed in `.venv`.
  - The author's two download folders were moved from the repo root into `data/raw_pff/`.
  - Sample test outputs are in the session scratchpad.
- Commits: brief 3535c71; blocked interim 5ea026f / 36ec6d8; this version 73be066.

## 8. Confidence
- The ingest is complete and verified: every file was read, 64/64 matches were crosswalked, and 99.81% of players were mapped.
- The coordinate conversion checks out on visible data (median ~2.2-2.5 units).
- The weakest link is time alignment. Offsets vary by several seconds within every match, so any use that needs event-level synchrony between StatsBomb events and tracking is limited by that, not by the per-period median.
