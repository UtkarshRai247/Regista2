# Task 55 — Figure 1 for the abstract, and a Card B note (presentation only)

Written 2026-09-29 by the research lead after reading
docs/results/54-scorecard-v2-and-repo-prep.md. Presentation only: no
number, tier, selection rule or computation changes. Holdout, reserved
and replication data are not touched.

Answers to Task 54's questions:
1. Card B keeps the automatic Tier 3 labels with their reasons. Add one
   note at the top of Card B (both page variants): "The modern-era sample
   has few matches per deep midfielder, so most dimensions are not
   stable enough here to rank players. Use Card A (2015/16) for
   rankings; Card B is shown for completeness."
2. The abstract now uses Card A's percentiles (research lead has updated
   docs/abstract/SSAC27-abstract-v2.md).
3. The PFF publication decision is the author's.

## Step 0 — The research lead commits this brief alone; record the hash.

## Step 1 — Redraw Figure 1 from the saved Card A values (no recomputation)
docs/scorecard/figure1.png, same rows (Kroos, Busquets, then the top
three by press resistance) and same values/intervals as Task 54 A5.
- Plain column titles: "Press resistance", "Speeds play up (style)",
  "Recycles (style)", "Switches play (style)", "Quick and safe under
  pressure", "Asks for the ball under pressure". Tier badge under each.
- Short player names: Toni Kroos, Sergio Busquets, Thiago Motta,
  Jorginho, Claudio Marchisio. Mark praised-list players with *.
- Title (one line): "Figure 1. Where elite deep midfielders sit: 2015/16
  big five, 185 deep midfielders (percentile within deep midfielders,
  90% interval)". Footnote: "* on a list of praised midfielders fixed
  before any measure. Style columns describe type, not quality. Data:
  StatsBomb open data."
- Remove the empty space above the panels; place value labels so they
  do not overlap the dot at 98-100. Width about 1,600 px, readable when
  scaled to half-page. Also save figure1.pdf.
Report the file sizes and confirm every plotted value equals Task 54 A5.

## Step 2 — Card B note on both scorecard pages
Add the note from answer 1 to docs/scorecard/index.html and
index_public.html (no other change).

## HARD RULES
- No computation, tier, value or selection change.
- No memory writes. Don't edit docs/JOURNAL.md. No interpretation.
- When finished, reply only that the task is done plus commit hashes.

## Output
docs/results/55-figure1.md (template). Commit per rule 9.
