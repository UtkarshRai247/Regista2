# Task 14b-prep — Compile the expert selection lists (compile only)

Governing document: docs/specs/analysis-plan-v3.md section 4 and
Amendment v3-4.3. This task COMPILES and STOPS. No leaderboards, no
Referee 2, no Decision values touched. The research lead verifies the
lists before Task 14b runs.

## Target competition-seasons (the study's own eight)
FIFA World Cup 2022; UEFA Euro 2020; UEFA Euro 2024; La Liga 2020/21;
Ligue 1 2021/22; Ligue 1 2022/23; Bundesliga 2023/24; MLS 2023.

## Step 1 — Find a published, dated, externally authored selection
For each, search for an official or major-outlet Team of the
Tournament / Team of the Season / Best XI. Preference order:
  1. The competition's own governing body (UEFA, the league).
  2. The national players' union award (e.g. UNFP for Ligue 1).
  3. A single named major outlet, if neither of the above exists.
Record for each selection: competition, season, source organisation,
publication date, source URL, and every player named with their
position as published.

## Step 2 — Hard sourcing rules
- Every player row must come from a page you actually fetched. Do not
  reconstruct a list from memory or from a summary you did not open.
- If you cannot find a qualifying selection for a competition-season,
  record it as NO LIST with the searches you tried. Do not substitute a
  different competition, a different season, or a fan-voted XI.
- Do not merge multiple outlets' XIs into one list. One source per
  competition-season.
- Player names exactly as published; no normalisation yet.

## Step 3 — Output the list for verification
Write data/expert_lists/selections.csv with columns:
  competition, season, source_org, publication_date, source_url,
  player_name_as_published, position_as_published
Commit it. Then PRINT the full CSV contents as plain text in your reply
so the research lead can verify every row against the sources.

## HARD RULES
- Compile only. Do not compute anything, do not join to our data, do
  not look at any Decision value or leaderboard.
- No memory writes. Don't edit docs/JOURNAL.md.
- Report NO LIST honestly rather than finding something weaker.

## Output
docs/results/14b-prep-expert-lists.md (template) plus the committed CSV,
and the CSV printed in your reply.
