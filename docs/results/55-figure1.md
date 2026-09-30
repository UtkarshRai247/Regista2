# Task 55: Figure 1 for the abstract, and a Card B note (presentation only)
Date: 2026-09-29
Status: COMPLETE

Presentation only:
- No number, tier, selection rule or computation changed.
- Figure 1 was redrawn from the saved Task 54 Card A values.
- Holdout, reserved and replication data were not touched.

## Checklist
| Section | Status |
|---|---|
| Step 0: brief committed alone by the research lead | COMPLETE (aa6e714; abstract update e6e5482, by the research lead) |
| Step 1: Figure 1 redrawn (PNG + PDF) from saved values; values checked | COMPLETE |
| Step 2: Card B note on `index.html` and `index_public.html` | COMPLETE |

## 1. Headline
Figure 1 was redrawn from the saved Task 54 Card A values:
- Same five rows and six columns as Task 54 A5.
- All 30 plotted (percentile, low, high) triples equal the saved Task 54 A5 values.
- `figure1.png`: 1,600 x 560 px, 82,678 bytes. `figure1.pdf`: 29,775 bytes.

The research lead's Card B note appears once in each scorecard page, on Card B only.

## 2. What I did
- Ran `.venv/bin/python src/engine_v2/task55_figure1.py`.
  - **Figure.** It reads `data/processed/scorecard_v2_card_a.parquet` and the `figure1` block of `data/engine_v2_task54.json` (the rows saved by Task 54), and recomputes nothing.
  - **Page note.** It inserts one element into each page's Card A/B render template. The element is shown only when the card is B.
- **Figure layout.** Rows:
  - Toni Kroos *
  - Sergio Busquets *
  - Thiago Motta
  - Jorginho
  - Claudio Marchisio

  Columns, each with its tier badge underneath:
  - Press resistance (PR2_flag_keep)
  - Speeds play up (style) (M4_ACCEL)
  - Recycles (style) (M4_SLOW)
  - Switches play (style) (M4_SWITCH)
  - Quick and safe under pressure (M2)
  - Asks for the ball under pressure (W)

  The one-line title and the footnote are the brief's text verbatim.
- **Value labels.** Where the dot is at the 85th percentile or above, the label sits to the left of the interval, so it never covers a dot at 98-100.
- **Page check.** Checked in Chrome from a local server:
  - `index.html`: Card A 185 rows with no note; Card B 111 rows with the note; Card C with no note.
  - `index_public.html`: Card B 111 rows with the note.
  - No console errors.

## 3. Numbers
| File | Size | Notes |
|---|---|---|
| `docs/scorecard/figure1.png` | 82,678 bytes | 1,600 x 560 px (10.0 x 3.5 in at 160 dpi) |
| `docs/scorecard/figure1.pdf` | 29,775 bytes | vector |
| `docs/scorecard/index.html` | 1,519,014 → 1,519,316 bytes | Card B note added |
| `docs/scorecard/index_public.html` | 1,460,217 → 1,460,519 bytes | Card B note added |

**Plotted values.** All 30 (row, column) triples of (percentile, 90% low, 90% high) were asserted equal to the saved Task 54 A5 values in `scorecard_v2_card_a.parquet`. They are the same figures listed in `docs/results/54-scorecard-v2-and-repo-prep.md`, section A5, and are saved in `data/engine_v2_task55.json`.

## 4. Deviations from the brief
- **Column titles are wrapped.** The three longest titles are wrapped onto two lines so neighbouring titles do not overlap: "Speeds play up (style)", "Switches play (style)" and "Asks for the ball under pressure". The wording is unchanged.
- **The Card B note is placed** directly under the Card B heading, as a bordered paragraph.

## 5. Problems and surprises
- A first draft of the figure had the two longest column titles overlapping. I wrapped them and redrew it (Section 4).
- The first run's page edits were reverted with `git checkout` before the final run, so the note is inserted exactly once.

## 6. Questions for the research lead
None.

## 7. Files produced
- `src/engine_v2/task55_figure1.py`
- `docs/scorecard/figure1.png` (redrawn), `docs/scorecard/figure1.pdf` (new)
- `docs/scorecard/index.html`, `docs/scorecard/index_public.html`: note added
- `data/engine_v2_task55.json` (not committed): the value check and sizes
- Commits: the hash is recorded below.
- Side effects: a temporary local web server (127.0.0.1:8753) for the page check, now stopped.
- Not staged: `docs/JOURNAL.md` and `AGENTS.md`.

## 8. Confidence
High. The figure is drawn directly from the saved values, with an equality assertion, and the page change is a single asserted insertion.
