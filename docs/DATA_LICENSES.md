# Data Licenses

One entry per dataset touched during Task 00 (data audit). Updated as new
datasets are touched in later tasks — do not remove entries for datasets
that stop being used, note that instead.

---

## StatsBomb open data
- Source: https://github.com/hudl/open-data (StatsBomb's org was renamed to
  `hudl` after Hudl's acquisition of StatsBomb; the old
  `github.com/statsbomb/open-data` URL now 301-redirects here — same repo,
  same content, confirmed by matching file counts).
- Competitions used/enumerated: all 80 competition-seasons currently in the
  repo, including FIFA World Cup 2022 (competition_id=43, season_id=106).
- License: no separate LICENSE file in the repo; the README states the
  data is free to use under StatsBomb's user agreement. Exact attribution
  wording quoted from the README: **"state the data source as StatsBomb and
  use our logo, available in our Media Pack."**
- Redistribution: the README does not state an explicit prohibition on
  redistribution, only the attribution requirement. We have NOT located or
  read a full formal Terms & Conditions document beyond the README — if the
  public SSAC repo will redistribute raw StatsBomb files (not just derived
  metrics), that fuller document should be read before publication, not
  assumed from the README alone.
- Access: fully open, no signup, no auth token required (confirmed via
  `statsbombpy` with no credentials).

## PFF FC World Cup 2022 tracking data
- Source: signup form at
  https://www.blog.fc.pff.com/blog/pff-fc-release-2022-world-cup-data
  delivers a Google Drive folder (owned by `gradientsports.archive@pff.com`,
  confirming it's the official source). The form appeared broken during
  this audit — root cause was a client-side adblocker (Brave Shields)
  stripping the embedded widget, not a dead site; it worked once tried
  without it.
- License: **not stated anywhere** — not on the blog posts, not on the
  Drive folder itself, not in any file inside it. This was checked, not
  just unattempted: no LICENSE/terms file exists in the folder (contains
  `Event Data/`, `Metadata/`, `Rosters/`, `Tracking Data/`,
  `competitions.csv`, `players.csv`, a change-log doc — no terms doc).
  Contact for questions: fchelp@pff.com (confirmed reachable, per the
  email already sent during this audit).
- Redistribution: **unresolved.** Get an explicit answer from PFF before
  any PFF-derived number (even a validation statistic) goes into a public
  SSAC repo artifact. Does not block internal/private analysis.
- Access: one sample match downloaded for Task 00 (game 3812) — tracking
  (48.5MB compressed), events (16.6MB), metadata, roster. Stored in
  `data/pff_sample/` (gitignored). The full 64-match corpus was NOT
  downloaded, per the spec's constraint; extrapolated full size ≈ 4.2GB.
- If redistribution turns out not to be allowed: ship a documented
  download/signup-instruction script instead of the raw data, per the
  spec's own fallback rule.

## Transfermarkt (direct)
- Not used. The spec explicitly rules out scraping in this task, and our
  tooling could not independently fetch transfermarkt.com to verify its
  Terms of Use text (the page is not reachable through the available
  fetch tool). No Transfermarkt data has been touched, scraped, or stored.

## transfermarkt-datasets (CC0 derivative)
- Source: https://github.com/dcaribou/transfermarkt-datasets (also
  mirrored on Kaggle as `davidcariboo/player-scores`)
- Download URL used (Task 02): single DuckDB file, all 12 tables, no
  Kaggle account needed —
  `https://pub-e682421888d945d684bcae8890b0ec20.r2.dev/data/transfermarkt-datasets.duckdb`
  (210.8 MB), saved to `data/transfermarkt-datasets.duckdb` (gitignored).
- License: **CC0-1.0**, stated directly in the repository — public domain,
  no attribution legally required (crediting the source is still good
  practice).
- Coverage: 88,000+ games, 50,000+ players, 12 tables including a
  `player_valuations` table (~650,000+ historical market-value records).
  Covers major club competitions plus national-team tournaments (World Cup,
  UEFA Euro, Copa América, AFCON, AFC Asian Cup).
- Freshness: **exact snapshot date confirmed on download (2026-09-19):
  `games` table max date 2026-07-06, `player_valuations` max date
  2026-06-12.** The maintainer's automated collection pipeline stopped
  succeeding in mid-July 2026 with no resume date — this is a frozen
  snapshot, not a live feed. All 8 of our sample competition-seasons
  (including the +12-month H3 window for the most recent ones) end well
  before this cutoff.
- Redistribution: CC0 permits full redistribution in the public SSAC repo
  with no restriction. This is the recommended market-value source for
  Pillar 4 — it avoids touching Transfermarkt directly at all.

## Local Regista 1 derived files (data/raw, data/processed)
- Source: pulled via `statsbombpy` from StatsBomb open data (see above);
  same license and attribution requirement passes through.
- These files live in the separate Regista 1 repo
  (`/Users/utkarshrai/Desktop/Regista`), not copied into Regista 2. Nothing
  from Regista 1's `/data` has been added to this repo or to git.

## Update 2026-09-29 (research lead)
- PFF: the author decided (D-018) to publish PFF-derived RESULTS with
  credit to PFF FC / Gradient Sports; no raw PFF data is committed.
  PFF's reply on terms is still outstanding.
- Also downloaded since this file was written, all StatsBomb open data
  under the same StatsBomb terms: the women's holdout (data/raw_holdout/,
  Women's Euro 2022, WWC 2023, Women's Euro 2025), the 2015/16 big-five
  leagues and the rest of the open-data release
  (data/raw_1516/open-data-master/), used in Tasks 44-53. None is
  committed.
- Full PFF WC2022 download: data/raw_pff/ (Task 36), not committed.
