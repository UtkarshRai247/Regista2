# Task 44 — A fresh, untouched dataset: StatsBomb's full 2015/16 big-five leagues

Written 2026-09-28 by the research lead after reading
docs/results/43-press-resistance-v2.md, before any result and before
any 2015/16 file has been downloaded.

## Why
Every deep-midfielder test so far has been starved of data: 28 deep
midfielders with 4+ matches, 20 in the press-resistance results rows.
Task 43 showed the press-resistance measure is real in one sense (two
independent providers agree, r = 0.78) but could not show it is stable
or that it matters, because each player has too few pressured
receptions. StatsBomb's open data contains every match of the 2015/16
Premier League, La Liga, Serie A, Bundesliga and Ligue 1 (event data,
no 360 frames): whole seasons for Busquets, Kroos, Verratti, Pjanic,
Jorginho, Kante, Xabi Alonso, Weigl and others. It has never been
touched by this project. Measures whose definitions are ALREADY fixed
and need only events (press resistance, flag version; tempo) can be
tested on it as a genuine out-of-sample confirmation.

## Step 0 — Commit this brief alone. Record the hash.

## Step 1 — Ingest (no analysis)
statsbombpy, competition/season ids (9,27), (11,27), (12,27), (2,27),
(7,27). Write events per match to `data/raw_1516/` (never into
data/raw/ or data/raw_holdout/). Report match counts per league,
integrity, and run task24_evidence.py's team-relative coordinate check
(share of team-periods with mean shot x > 60).

## Step 2 — Event-only press resistance, checked BEFORE any 2015/16 analysis
PR2_flag: exactly Task 43's spell, keep_spell and fwd_spell, but
PRESSURED = StatsBomb under_pressure on the Ball Receipt* OR on the
receiver's first on-ball event of the spell (no frame needed).
Baseline: Task 42's classifier settings; context from events only:
reception x, y (event location), play pattern, period, minute.
Compute it on the 292-match STUDY sample and correlate player-level
PR2_flag_keep with Task 43's PR2_keep (players with >= 50 pressured
receptions in both). GATE: r >= 0.70. If it fails, press resistance is
not run on 2015/16 (tempo still is), and the page says why.

## Step 3 — Build the 2015/16 measures (definitions unchanged)
- PR2_flag_keep, PR2_flag_fwd (Step 2 definition; baseline refit on
  2015/16 with 5 match folds, seed 20260928).
- MOVE_ON_SPEED, HOLD_VARIATION: the preregistered tempo definitions,
  run with the corrected-coordinate code (Task 26 Step 2 /
  redesign_metrics_v2) on 2015/16, outputs to new files.
- Roles: Task 32 Step 4's rule on 2015/16 positions. Deep midfielder =
  >= 50% of eligible passes at C/L/R Defensive Midfield and >= 500
  eligible passes.
- Outcomes: Task 42's Y_F3 and Task 35's net xG window 10.
Report counts of players per role and per league.

## Step 4 — Confirmatory tests (bars fixed now)
PRIMARY (the two leads from the study sample), each within deep
midfielders, Holm across the two:
  P1: MOVE_ON_SPEED -> net xG (unit = pass), coefficient > 0.
  P2: PR2_flag_keep -> Y_F3 (unit = pressured reception), coef > 0.
Design: Task 35 Step 2 P-test (S = leave-one-match-out, >= 100 passes
or >= 50 pressured receptions elsewhere; g refit; role FE; team-match
FE; SE by player). Positive controls on the same rows: completion
(passes) and Task 43's retention definition (receptions).
CONFIRMED if Holm p < 0.05, coefficient > 0, and the control on the
same rows is positive with p < 0.05. P2 is only run if Step 2's gate
passed; if not, P1 alone uses p < 0.05.
SECONDARY (reported, not claimed): all other measure x outcome
combinations, within deep midfielders and for all players.
R1 stability: Task 38's method (100 random splits of a player's
MATCHES), players with >= 10 matches; deep midfielders and all. Bar
0.60 for a stability claim.
Praised list: Task 41 Step 7's method on each measure, players present
in 2015/16. Pre-declared direction: higher on PR2_flag_keep; none for
tempo (two-sided). A statement needs p < 0.05 after Holm across the
praised-list tests of this task.

## Step 5 — Deep-midfield tables (output only)
Task 29's method, within the 2015/16 deep-midfield group, for every
measure that passes R1.

## HARD RULES
- No change to any definition fixed in Tasks 26, 42 or 43 beyond the
  event-only pressure flag of Step 2.
- data/raw_1516/ is new; study and holdout data untouched.
- Memory gate as in Task 25; one match in memory at a time.
- Commit the page after Step 2, then at the end.
- No memory writes. Don't edit docs/JOURNAL.md. No interpretation.
- When finished, reply only that the task is done plus commit hashes.

## Output
docs/results/44-big-five-1516.md (template). Commit per rule 9.

## Operational note (2026-09-28, research lead)
The author will download StatsBomb's open-data repository manually as a
ZIP and unzip it into `data/raw_1516/`. Step 1 therefore reads the local
copy instead of calling statsbombpy: take the match lists from
`data/matches/<competition_id>/27.json` for competition ids 2, 7, 9, 11
and 12 inside the unzipped folder, and the events from
`data/events/<match_id>.json`. Use only those 2015/16 matches; ignore
every other file in the download. If the ZIP is incomplete or any listed
match's events file is missing, stop and list what is missing.

## Correction (gap in the brief, marked as such; 2026-09-28)
2015/16 has no 360 frames, so the engine's "eligible pass" rule (which
requires a freeze frame with >= 6 visible players) cannot apply. For
2015/16 ONLY:
- eligible pass = the engine's rule with the frame condition removed:
  a Pass, not an excluded pass type (set pieces etc., as in the
  engine), non-goalkeeper passer, with an end location. This defines
  the role rule, the deep-midfield group, the P-test pass units and the
  pass-count floors (>= 500; >= 100 elsewhere).
- Tempo's S (MOVE_ON_SPEED, HOLD_VARIATION) keeps its own preregistered
  eligibility (is_open_play_pass), unchanged, exactly as in the study
  sample.
Report on the page how many 2015/16 passes each rule admits. Record
this in the deviations section.
