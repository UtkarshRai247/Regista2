# Task 00 — Data Audit

## Purpose
Find out what data actually exists on disk and online, and whether
StatsBomb 360 and PFF FC World Cup 2022 tracking can be joined at match
and event level. This decides which research direction we commit to on
Sep 20. Do not build models. Do not compute metrics.

## Terms
- Event data: a row per on-ball action (pass, shot, tackle) with time,
  location, player.
- 360 / freeze frame: a snapshot of the positions of the players VISIBLE
  in the broadcast frame at the moment of an event. Not all 22.
- Tracking data: continuous positions of all players many times per
  second. PFF's World Cup release is derived from broadcast video.

## Hard constraints
- Download at most ONE PFF match as a sample. Do not pull the full
  corpus. Report its size and extrapolate.
- Nothing goes in git. Confirm /data is gitignored.
- Time-box each section. If something is blocked, write the blocker and
  move on. Do NOT invent workarounds.
- Report what you observe, not what you expect. If a dataset is not
  where the docs say, say so.

## Section A — What we already have
Inventory the Regista 1 repo and any local data directories.
Report: which competitions and seasons, match counts, whether 360 frames
are present, total disk size, and which parts of the Regista 1 pipeline
are reusable (list the modules and what each does).

## Section B — StatsBomb open data
Enumerate the open data competitions programmatically. For EACH
competition-season, report: match count, whether event data exists,
whether 360 data exists, and how many matches have 360.
Do not assume which competitions have 360 — check.
Flag specifically whether FIFA World Cup 2022 has 360 coverage and for
how many of the 64 matches.

## Section C — PFF FC World Cup 2022 tracking
Locate the public release and report the host, the access process
(open download, form, account), and the stated license.
Download one match. Report: file format, size, frame rate, coordinate
system and pitch dimensions, what identifiers exist for players, teams
and matches, whether the ball is tracked, whether there are flags for
players who are off-camera or interpolated, and how completeness varies
across a match.
Extrapolate the full 64-match size.

## Section D — The alignment question (most important)
Only if B and C both succeed.
1. Match-level: build a candidate crosswalk between the 64 PFF matches
   and StatsBomb World Cup 2022 matches using date, teams and score.
   Report how many match unambiguously and list any that do not.
2. Event-level: for ONE matched game, test whether StatsBomb event
   timestamps can be aligned to PFF frames. Use unambiguous reference
   events (kickoffs, goals, and a few shots). Report the offset, whether
   it drifts across the match, and the residual error in seconds.
3. Report honestly whether an event-to-frame join looks feasible,
   marginal, or not feasible. "Marginal" is an acceptable answer.

## Section E — Market value data for the Pillar 4 option
We need player market valuations that can legally be republished in a
public repo.
Check what exists and report for each: source, coverage (leagues,
seasons, player counts), license and redistribution terms, and how it
could be joined to player names in Wyscout or StatsBomb data.
Explicitly check Transfermarkt's terms of use and whether any existing
openly-licensed derivative datasets exist.
Do not scrape anything in this task.

## Section F — Licenses and credit
Create docs/DATA_LICENSES.md. For every dataset touched in A-E record:
name, source URL, license, whether the raw data may be redistributed in
a public repo, and the exact attribution wording the provider requires.
Where redistribution is not allowed, note that we will ship a download
script instead.

## Output
1. docs/results/00-data-audit.md following docs/results/TEMPLATE.md.
   One page. Section 6 (questions for the research lead) matters most —
   be specific.
2. docs/DATA_LICENSES.md.
3. Any download or inventory scripts in /src, runnable and documented.
