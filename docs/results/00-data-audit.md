# Task 00: Data Audit
Date: 2026-09-18
Status: COMPLETE

## 1. Headline
All six sections are done. StatsBomb's open data is fully open, covers 80
competition-seasons including FIFA World Cup 2022 with 360 data on all 64
matches. PFF's WC2022 tracking data (initially thought blocked — the missing
signup form was a client-side adblocker issue, not a dead site) is now in
hand for one sample match, and the news is good: all 64 PFF matches
crosswalk unambiguously to StatsBomb's 64 WC2022 matches by date+teams, and
a direct event-to-frame alignment test on two goals in the sample match
shows a clean, consistent ~2-second offset with no measurable drift.
**Pillar 2's cross-validation angle looks feasible, not just viable.**

## 2. What I did
- Located the Regista 1 reference repo (two clones exist; used the more
  advanced one, `/Users/utkarshrai/Desktop/Regista`, HEAD `5f54322`).
- Inventoried its `src/` modules, `data/raw`, and `data/processed` by
  reading file listings, `.gitignore`, `README.md`, and grepping ingestion
  scripts for what they actually pull (`data_ingestion.py`,
  `phase2_ingestion.py`).
- Read the local `.parquet` files directly (installed `pyarrow`/`pandas`
  into a fresh `.venv` in Regista 2 — see Deviations) to check column
  schemas and the `match_status_360` field on match metadata.
- Wrote `src/audit_statsbomb.py`, using `statsbombpy` (zero-auth) to
  enumerate every competition-season StatsBomb publishes, with match
  counts and 360 coverage per competition-season. Reproduce with:
  `source .venv/bin/activate && python src/audit_statsbomb.py`
- Researched PFF's WC2022 tracking release (WebSearch/WebFetch/browser) to
  find its host, access process, and license — see Section 5 for the saga.
  You supplied the actual Drive folder once the client-side blocker was
  identified; downloaded exactly one sample match (game 3812: Senegal vs
  Netherlands) — tracking, events, metadata, roster — plus the two small
  reference files (`competitions.csv`, `players.csv`) and the full
  `Metadata/` folder (64 tiny per-game files, ~43KB total, needed for the
  Section D.1 crosswalk — not tracking data, so this doesn't violate the
  "one match only" constraint on the actual bulky corpus).
- Wrote `src/audit_pff.py` to inspect the sample match (format, frame rate,
  coordinate system, visibility/confidence flags, ball coverage).
- Wrote `src/audit_alignment.py`: crosswalked all 64 PFF matches against
  StatsBomb's 64 WC2022 matches by date+teams, then tested event-to-frame
  alignment on the sample match's two goals.
- Researched Transfermarkt's terms and openly-licensed derivative
  datasets (WebSearch/WebFetch) — did not scrape anything, per the spec.
- Wrote `docs/DATA_LICENSES.md` covering every dataset touched above.
- Confirmed `git status` in this repo shows nothing data-related staged,
  and that `data/` and `.venv/` are both gitignored.

## 3. Numbers

**Regista 1 local data** (all via `statsbombpy`, StatsBomb open data only):

| Dataset | Matches | Raw events present | Raw 360 frames present | `match_status_360` |
|---|---|---|---|---|
| Leverkusen 2023/24 (Bundesliga) | 34 | yes | no (`.gitignore`'d, not on disk) | available (34/34) |
| Euro 2020 | 51 | yes | no (`.gitignore`'d, not on disk) | available (51/51) |
| Euro 2024 | 51 | yes | no (`.gitignore`'d, not on disk) | available (51/51) |
| La Liga historical | unknown (raw file absent) | no (excluded, >100MB) | no | not checked |

`data/raw` = 57M, `data/processed` = 67M (~28 files), repo total = 239M
(107M of that is `.git` history). 14 Python modules in `src/`, listed with
one-line purpose in Section 7.

**StatsBomb open data enumeration** (`src/audit_statsbomb.py`, 80
competition-seasons, 0 errors):
- Total matches across all competition-seasons: 3,961
- Matches with 360 data available: 426, across 12 competition-seasons
- **FIFA World Cup 2022 (competition_id=43, season_id=106): 64/64 matches
  have 360 available** — full coverage, the number the spec asked for
  explicitly.
- Other 360-covered competition-seasons: Bundesliga 2023/24 (34/34), La
  Liga 2020/21 (35/35), Ligue 1 2022/23 (32/32), Ligue 1 2021/22 (26/26),
  MLS 2023 (6/6), Euro 2024 (51/51), Euro 2020 (51/51), Women's Euro 2025
  (31/31), Women's Euro 2022 (31/31), Women's World Cup 2023 (64/64),
  African Cup of Nations 2023 (1/52 — partial).

**PFF sample match** (game 3812, Senegal vs Netherlands, 2022-11-21, Al
Thumama Stadium, `src/audit_pff.py`):
- Tracking file: 48.5MB compressed, 185,746 frames, both periods, ~29.94
  implied fps (metadata states 29.97) — matches the spec's 30fps-class
  broadcast-derived expectation.
- Coordinates: meters, pitch-center origin, observed bounds roughly
  ±56.7m x / ±37.9m y against a stated 105m x 68m pitch (players/ball run
  slightly outside the touchline bounds, as expected). **This is a
  different coordinate convention than StatsBomb's** (120x80 arbitrary
  units, corner origin) — any join needs an explicit unit/origin
  conversion, not just a rescale.
- Ball position present in 66.8% of frames — not fully tracked either.
- Player-frames: 57.2% flagged `ESTIMATED` visibility (not directly
  observed, i.e. inferred/off-camera) vs `VISIBLE`; confidence is `LOW`
  for ~64% of player-frames, `HIGH` for ~32%, `MEDIUM` for the rest. **PFF's
  "full tracking" is itself majority-inferred, not majority-observed** —
  worth knowing before treating it as ground truth against StatsBomb's
  freeze frames.
- Identifiers: `gameRefId`, per-player `jerseyNum` + team side in tracking
  frames; `playerId`/`playerName`/`teamId` in the 2,010-event
  `events.json` for this match; a `game_event_id` field on ~25% of frames
  directly links a tracking frame to a specific event (PFF's own internal
  join key — useful even beyond the StatsBomb comparison).
- Extrapolated full 64-match size (from this one sample): tracking
  ≈ 48.5MB × 64 ≈ **3.1GB**; events ≈ 16.6MB × 64 ≈ **1.06GB**; metadata/
  rosters negligible (~KB each). Total ≈ **4.2GB**, single-sample estimate
  — extra-time games will run larger.

**Section D — match-level crosswalk** (`src/audit_alignment.py`):
**64/64 PFF matches matched unambiguously** to a StatsBomb WC2022 match by
date + team names. Zero ambiguous or unmatched cases.

**Section D — event-to-frame alignment** (one matched game, two goals):

| Scorer | StatsBomb clock | PFF clock | Offset |
|---|---|---|---|
| Gakpo | 83:50 | 83:48 | +2.0s |
| Klaassen | 98:18 | 98:16 | +2.0s |

Identical +2.0s offset on both goals, 15 minutes apart — **no measurable
drift** (PFF's clock granularity is whole seconds, so true precision is
±1s). **Verdict: feasible**, not just marginal — StatsBomb events can be
aligned to PFF frames with a simple constant offset, at least for this
match.

## 4. Deviations from the brief
- Installed `pyarrow` in Regista 2's new `.venv` (not previously used
  anywhere in this repo) to actually read the existing `.parquet` files
  in Regista 1 for Section A rather than reporting filenames only. This
  wasn't in the original stdlib-only plan; it's read-only and matches
  what Regista 1 already depends on, so it didn't seem worth stopping for,
  but flagging per CLAUDE.md rule 5.
- Section B originally planned as a manual git sparse-checkout/`ls-tree`
  parse of the open-data repo; switched to `statsbombpy` instead (per your
  correction during planning) since it's already a Regista 1 dependency
  and StatsBomb's data needs no auth at all.
- Section C's download happened via browser (you shared a Google Drive
  folder link, and Drive's file listing wasn't queryable through the
  available Drive API tool for this shared-not-owned folder) rather than
  the originally planned `src/audit_pff.py`-does-the-download approach.
  The analysis script (`src/audit_pff.py`) is still there and scripted —
  only the initial fetch was manual/browser-driven.
- Downloaded the entire `Metadata/` folder (all 64 games, ~43KB total)
  rather than just game 3812's metadata, specifically to run the Section
  D.1 match-level crosswalk across all 64 matches as the spec asks. This
  is metadata, not tracking data — nowhere near "the full corpus" the
  spec says not to pull — but it's more than the literal "one match"
  framing, so flagging it as a deliberate, scoped exception.

## 5. Problems and surprises
- **Local 360 data doesn't actually exist despite being "available."**
  Regista 1's match metadata says 360 is available for every local
  competition (Leverkusen, Euro 2020, Euro 2024), and the codebase has
  working code to pull it (`phase2_ingestion.py::pull_360_frames`,
  writing to `euro2024_frames.pkl` etc.), but none of those `.pkl` files
  are present on disk right now — `.gitignore` excludes `*.pkl` and
  `data/raw/frame_lookup.pkl` specifically. The README's "118K freeze
  frames" claim likely refers to a past run whose cache was never
  committed and has since been cleaned up or not regenerated in this
  checkout. **This is not a blocker** — StatsBomb confirms the data is
  still there to re-pull — but it means Regista 2 starts from zero on 360
  frames, not from something inherited.
- **`shot_freeze_frame` is not the same thing as 360 data.** The events
  parquet files DO contain a `shot_freeze_frame` column, which is
  StatsBomb's older, shots-only freeze-frame feature (pre-dates the "360"
  product and only covers the moment of a shot). Worth being precise
  about this distinction going forward since both are called "freeze
  frame" informally.
- **PFF's release has no stated license anywhere public** — not on the
  blog posts, not on the Drive folder itself. The folder is owned by
  `gradientsports.archive@pff.com`, confirming it's the legitimate
  official source, but no terms document was found attached anywhere.
  `docs/DATA_LICENSES.md` records this as genuinely unresolved — it's not
  a "haven't checked yet" gap, it's "checked, nothing there."
- Two Regista 1 clones exist on disk (`~/Desktop/Regista`, canonical, and
  `~/Regista`, 2.4G, 4 commits behind, with a bloated `.venv` and a stray
  nested duplicate clone inside it). Not touched or cleaned up — flagging
  since it's unrelated dead disk usage, not something this task should
  delete unasked.
- Could not independently verify Transfermarkt's Terms of Use text — the
  fetch tool available in this session cannot reach transfermarkt.com at
  all (blocked at the tool level, not a site error). Relied on secondary
  sources describing the general practice of using licensed derivatives
  instead of scraping directly.
- StatsBomb's GitHub org was renamed to `hudl` after Hudl's acquisition —
  `github.com/statsbomb/open-data` now 301-redirects to
  `github.com/hudl/open-data`. Same data (confirmed: `data/three-sixty/`
  has exactly 426 files there, matching the 426-match count in Section 3
  above). This was checked after the user pointed at that URL thinking it
  might be the PFF release — it isn't. It's the same StatsBomb 360 data
  already counted here, not PFF's separate full-tracking product.
- **PFF's self-serve signup form is genuinely broken, confirmed by
  rendering both blog posts in a real browser** (not just a fetch): both
  `blog.fc.pff.com/blog/pff-fc-release-2022-world-cup-data` (original) and
  `blog.fc.pff.com/blog/enhanced-2022-world-cup-dataset` (newer,
  "restructured by game" version) contain the sentence "fill out the form
  below" with **no form, embed, or iframe actually present** on either
  page — confirmed via screenshot and the page's accessibility tree, not
  just a parsing artifact. Their main product site, `fc.pff.com` (the
  "Request a live demo" link), currently serves an "Oops | PFF" error page
  — the whole property looks to be having an outage or a broken deploy,
  not something specific to us. The `kloppy` library's loader docs for
  this dataset just point back to the same broken blog post.
- **Root cause of the "broken form": a client-side adblocker, not a dead
  site.** After exhausting the alternate-access search (Wayback, mirrors,
  `kloppy` source, Kaggle/Zenodo/Hugging Face, cited papers — all dead
  ends) and having the user email `fchelp@pff.com`, the actual fix turned
  out to be much simpler: the user's Brave browser adblocker was silently
  stripping the embedded signup-form widget on PFF's page. Once tried
  without it, the form worked and produced a Google Drive folder link
  directly. **Lesson for next time**: when an embedded third-party form
  "isn't there," try a different browser/adblocker-off session before
  concluding the provider's site is broken — it's a much cheaper check
  than searching for alternate hosts (saved to memory for future
  sessions). The email to PFF is now moot but wasn't wasted — it also
  confirmed the request/contact route works if this ever recurs.

## 6. Questions for the research lead
1. **Pillar 2 now looks strong on both data availability and
   cross-validation feasibility — is it the pick for GO/NO-GO 1 (Sep
   20)?** StatsBomb's 360 data is fully open (64/64 on WC2022), the match
   crosswalk against PFF's tracking is 64/64 clean, and the one alignment
   test done so far shows a tight, driftless offset. This is now a
   data-readiness green light, not a methodology decision — but which
   pillar to lead with is still yours to call.
2. **PFF's license is genuinely unresolved, not just unchecked.** No
   terms document exists anywhere on their public pages or the Drive
   folder. Before any PFF-derived numbers appear in a publishable result
   (even indirectly, e.g. a validation statistic), someone should get an
   explicit answer from PFF (`fchelp@pff.com` is a confirmed working
   contact) on redistribution/publication terms — this doesn't block
   internal analysis, but would block the SSAC repo going public with
   anything derived from it.
3. **Is the CC0 `dcaribou/transfermarkt-datasets` snapshot (frozen since
   mid-July 2026) acceptable for Pillar 4**, or is a current/live
   Transfermarkt value needed badly enough to justify a human (not
   scraper) checking Transfermarkt's terms directly? I did not make this
   call — it trades data freshness against legal certainty and touches
   the redistribution requirement for the public SSAC repo.

## 7. Files produced
- `src/audit_statsbomb.py` — enumerates all StatsBomb open-data
  competition-seasons via `statsbombpy`; writes
  `data/_statsbomb_audit_cache.json` (gitignored, local cache of the raw
  results, 80 rows).
- `src/audit_pff.py` — inspects the one downloaded PFF sample match
  (format, frame rate, coordinates, visibility/confidence, ball coverage,
  event count).
- `src/audit_alignment.py` — Section D: crosswalks all 64 PFF matches to
  StatsBomb's 64 WC2022 matches; tests event-to-frame alignment on the
  sample match's two goals.
- `data/pff_sample/` (gitignored) — the one sample match's raw files:
  `3812.tracking.jsonl.bz2` (48.5MB), `3812.events.json` (16.6MB),
  `3812.metadata.json`, `3812.roster.json`, `competitions.csv`,
  `players.csv`, plus `all_metadata/` (all 64 games' small metadata files,
  used only for the Section D.1 crosswalk).
- `data/pff_matches.json`, `data/statsbomb_wc2022_matches.json`
  (gitignored) — the two match lists the crosswalk script joins.
- `docs/DATA_LICENSES.md` — license/attribution/redistribution status for
  every dataset touched: StatsBomb open data, PFF WC2022 (license
  genuinely unresolved, not just unchecked), Transfermarkt (not used),
  `dcaribou/transfermarkt-datasets` (CC0), and the local Regista 1
  derived files.
- `docs/results/00-data-audit.md` — this page.
- `.venv/` in this repo (gitignored) — `statsbombpy`, `pandas`, `pyarrow`
  installed for this and future data tasks.
- Regista 1 modules confirmed reusable for later tasks (not copied,
  just inventoried): `data_ingestion.py` / `phase2_ingestion.py`
  (StatsBomb + 360 pulling pattern), `baseline_metrics.py`,
  `novel_metrics.py`, `decision_surplus.py`, `defensive_topology.py`,
  `transformer_model.py` (metric/model logic relevant to Pillar 1),
  `phase2_validation.py` / `phase2_scores.py` (cross-sample statistical
  validation pattern relevant to Pillar 3).

## 8. Confidence
High confidence on Sections A, B, and C — all direct measurement (file
listings, `git log`, a clean 0-error enumeration script, actually parsing
the downloaded tracking/event files) with nothing inferred. Section D:
the match-level crosswalk (64/64) is solid — pure joins on hard
identifiers. The event-alignment result (n=2 goals, one match) is a much
thinner sample than "confident" implies — it's a clean, encouraging
signal, not a validated methodology. Don't treat "+2.0s, no drift" as
settled until it's checked on more matches and more event types (not just
goals, which are unusually unambiguous compared to e.g. tackles or
passes). Section E: medium confidence, unchanged — the CC0 derivative
dataset's license is solid, but Transfermarkt's own terms weren't
independently readable by any tool available this session. The weakest
link is now the event-alignment sample size, not data availability.
