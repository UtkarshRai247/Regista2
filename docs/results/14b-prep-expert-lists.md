# Task 14b-prep: Compile the expert selection lists (compile only)
Date: 2026-09-24
Status: PARTIAL

## 1. Headline
7 of the study's 8 competition-seasons have a published, dated, externally-authored Team of the Tournament/Season, each fetched directly and recorded with its source URL. La Liga 2020/21 is recorded as **NO LIST**: no active LaLiga end-of-season gala existed for that season (reported inactive since 2016/17), no players' union list exists before 2021/22 (AFE's awards began with that first edition), and no clean single-major-outlet season-end XI specific to 2020/21 was found after multiple searches — reported honestly rather than substituting a weaker source. No leaderboard, no Referee 2, and no Decision value of any kind was touched.

## 2. What I did
Governing spec: `docs/specs/analysis-plan-v3.md` section 4 and Amendment v3-4.3, executed via `docs/specs/task-14b-prep-expert-lists.md`. This is a pure web-research/compile task — no code was written or run.

For each of the study's 8 competition-seasons, searched (WebSearch) then fetched (WebFetch) the candidate source page directly, following the stated preference order: (1) the competition's own governing body, (2) the national players' union award, (3) a single named major outlet if neither exists. Every row in the CSV traces to a page actually fetched in this session (URLs below). No list was reconstructed from a search-result snippet alone without opening the page.

- **FIFA World Cup 2022**: confirmed via Wikipedia's "FIFA World Cup awards" page that FIFA has given no official Team of the Tournament/Dream Team since 2006, and ran no fan-voted Dream Team poll for 2022 (unlike 2010-2018 and 2026). Fell to preference 3: fetched Sky Sports' dated "World Cup team of the tournament" article.
- **UEFA Euro 2020 / 2024**: UEFA's own technical-observer Team of the Tournament exists and is published on uefa.com for both; fetched both pages directly.
- **La Liga 2020/21**: see Section 5 for the full search trail; recorded NO LIST.
- **Ligue 1 2021/22 / 2022/23**: UNFP's own Trophées ceremony publishes an "équipe type" (team of the season) every year; fetched two French football outlets (CulturePSG, Foot Mercato) that reported the UNFP results with full rosters and dates (UNFP's own site was searched but no stable per-season archive page was found within this session; the outlets fetched report the UNFP's results specifically, not their own independent picks).
- **Bundesliga 2023/24**: fetched bundesliga.com's own "Bundesliga Team of the Season" article (a DFL/EA SPORTS award combining fan (40%), club (30%) and expert (30%) votes, published on the league's own site) and cross-checked the full roster against Bayer 04 Leverkusen's own official site, which reported the identical 11 players.
- **MLS 2023**: fetched MLS's own official mlssoccer.com announcement of the "2023 MLS Best XI," selected by media, players and club technical staff.

Wrote `data/expert_lists/selections.csv` (columns: `competition, season, source_org, publication_date, source_url, player_name_as_published, position_as_published`). Added a `.gitignore` allowlist exception for it (following the existing `data/processed/` and `data/splits/` pattern, since `data/*` is otherwise ignored).

## 3. Numbers
- 8 target competition-seasons; 7 with a recorded selection, 1 NO LIST.
- 77 player rows total (11 players x 7 competition-seasons).
- Sources used: UEFA.com (2), bundesliga.com (1), mlssoccer.com (1), Sky Sports (1, fallback), CulturePSG/Foot Mercato reporting UNFP's own results (2).

## 4. Deviations from the brief
1. **UNFP's own site was not the fetched source URL.** Step 1's preference order names "the national players' union award (e.g. UNFP for Ligue 1)" as preference 2; I could not locate a stable, dated unfp.org archive page for either season within this session's searching, so the source_url in both Ligue 1 rows points to a football news outlet (CulturePSG for 2021/22, Foot Mercato for 2022/23) reporting UNFP's own official results, not to unfp.org itself. `source_org` is recorded as "UNFP" (the actual selecting body) since that is accurate; the URL is the page I actually fetched and verified the roster against, per the hard sourcing rule.
2. **Bundesliga's publication date has some uncertainty.** The bundesliga.com URL itself (`vote-now-for-the-bundesliga-team-of-the-season-2023-24...`) suggests the page was originally published to open voting, then apparently updated in place to show final results without a URL change — my first fetch of it returned an inconsistent date (April 5, 2024, before the season's own final matchday). The roster it now shows is corroborated exactly by Bayer 04 Leverkusen's own official site, dated May 3, 2024; that corroborating date is what's recorded, disclosed here since it wasn't extracted from the exact `source_url` cell itself.
3. **Player names likely lost diacritics in extraction.** WebFetch converts each page to markdown and summarizes it through a small model before I see the text; several names that should carry accents or diacritics in the original page (e.g. Mbappé, Højbjerg, Fabián Ruiz, Bürki, Khéphren Thuram, Loïs Openda) came back to me without them consistently. I recorded names exactly as my fetch returned them rather than "correcting" them from outside knowledge (which would violate "no normalisation yet" in the other direction), but this means the CSV's spelling is only as faithful as the fetch tool's own text extraction, not a byte-for-byte transcription of the source HTML. Flagged explicitly for the verification pass this task exists to support.

## 5. Problems and surprises
**La Liga 2020/21 — full search trail for the NO LIST verdict:**
1. LaLiga's own governing-body award: found no dedicated LaLiga.com "Team of the Season" article for 2020/21 specifically (only one exists, so far as this session could find, for the 2023/24 season onward, and that one is a 15-player longlist, not a final XI). A secondary source stated LaLiga's own end-of-season gala/ceremony format had been inactive since 2016/17.
2. Players' union: AFE (Asociación de Futbolistas Españoles) runs "Premios AFE," but its own "Primera edición" (first edition) covers the 2021/22 season — there is no AFE award for 2020/21.
3. EA Sports "LaLiga Santander TOTS" for 2020/21 exists, but only as an EA/FIFA Ultimate Team video-game product page (ea.com), not hosted or announced as an award on laliga.com itself (unlike the Bundesliga case, where bundesliga.com carried its own article) — judged not to meet "a published, dated, externally authored selection" in the sense the task intends, since it's a game-content release, not editorial or organizational recognition.
4. Single major outlet: Opta Analyst publishes a data-driven "Team of the Season" for La Liga in some seasons, but none specific to 2020/21 was found. Football365's 2020/21 XI exists and is dated, but is explicitly self-described in its own text as "hotly anticipated, unofficial awards" by a named individual columnist — judged too far from "a single named major outlet['s]" institutional selection to use as the one row for this competition-season, especially with the hard rule to report NO LIST rather than settle for something weaker.
Recorded as NO LIST rather than using any of the above.

## 6. Questions for the research lead
1. Is Football365's individually-authored, self-described-unofficial 2020/21 La Liga XI (found but not used) an acceptable preference-3 substitute, or should La Liga 2020/21 stay excluded from Referee 2's coverage as this page currently has it? I did not decide this myself, per the hard sourcing rules.
2. The two Ligue 1 rows cite outlets reporting UNFP's results rather than unfp.org directly (Section 4.1). Is that acceptable provenance, or should the actual unfp.org pages be tracked down before this CSV is treated as final?
3. Section 4.3's diacritic-loss issue means this CSV should be checked character-by-character against the live pages, not just for the right players — some names as recorded may not exactly match the source's own spelling.

## 7. Files produced
- `data/expert_lists/selections.csv` — the compiled list, printed in full in this task's chat reply. Committed together with the rest of this batch, commit `3fe3a77`.
- `.gitignore` — one new allowlist exception for `data/expert_lists/selections.csv`, following the existing pattern. Committed, commit `3fe3a77`.
- `docs/specs/task-14b-prep-expert-lists.md` — committed with this results page, commit `3fe3a77`.
- `docs/results/14b-prep-expert-lists.md` — this page. Committed, commit `3fe3a77`.

## 8. Confidence
Moderate. The rosters themselves for the 7 covered competition-seasons are corroborated by at least a second independent mention in every case (visible in the search results even where only one page was fetched per the "one source per competition-season" rule), so the player *sets* are very likely correct. The two weakest points are exactly the ones flagged above: the diacritic fidelity of individual name spellings (Section 4.3), and whether La Liga 2020/21's NO LIST verdict should instead fall back to the Football365 outlet (Section 6.1) — both are handed to the research lead's verification pass by design, which is what this task exists to support.
