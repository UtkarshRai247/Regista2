# Task 51 — The regista scorecard

Written 2026-09-29 by the research lead, before any scorecard number
exists. Descriptive product, no new claims: it presents measures that
already exist, each labelled with how much evidence stands behind it.
No new measure definitions. Holdout untouched. Run after Task 50.

## Why
The project has several validated or stable measures of how a deep
midfielder plays. Coaches and scouts need them on one page, with honest
uncertainty, compared only with players in the same role. This is the
practical output of the project and a candidate figure for the
abstract.

## Step 0 — The research lead commits this brief alone; record the hash.

## Step 1 — Two cards (populations fixed now)
CARD A, "2015/16 big five": Task 44's 185 deep midfielders.
  Dimensions: press resistance (PR2_flag_keep, unadjusted), press
  resistance team-adjusted (A1, Task 45), willingness to receive under
  pressure (W, Task 46), HOLD_VARIATION, MOVE_ON_SPEED.
CARD B, "360 era" (study sample): Task 27's 111 deep midfielders.
  Dimensions: Decision (v5, cross-fitted), press resistance
  (PR2_flag_keep computed on the study sample, Task 46's version), W,
  space at reception (RQ_rel, Task 34), HOLD_VARIATION, MOVE_ON_SPEED
  (Task 26's corrected-coordinate tempo); and, for players in PFF
  WC2022 with >= 300 moments, availability (AV, Task 38).
CARD C, "career line" (reserved data, second use, descriptive): for
  every deep midfielder with >= 5 La Liga seasons in the reserved data
  and >= 50 pressured receptions in each, PR2_flag_keep per season with
  90% intervals.

## Step 2 — Per player, per dimension
n units; raw mean; shrunken mean and 90% interval by Task 29's method
(within-group noise, DerSimonian-Laird, within the card's group);
percentile of the shrunken value within the group; and a label:
CLEARLY ABOVE / CLEARLY BELOW (interval excludes the group mean) or
CAN'T TELL. Players below a dimension's floor show "not enough data".
Floors: PR and A1 >= 50 pressured receptions; W and RQ_rel >= 100
receptions; tempo per its preregistered floor; Decision >= 100
eligible passes; AV >= 300 moments.

## Step 3 — Evidence tier per dimension (fixed now; shown on every card)
TIER 1 — stable in deep midfielders, travels with the player, linked to
  team results on untouched data: press resistance (PR2_flag_keep; A1
  shown beside it).
TIER 2 — stable in deep midfielders, no confirmed link to results:
  W, HOLD_VARIATION, RQ_rel, AV (AV with the note "linked to FEWER
  chances in WC2022; exploratory").
TIER 3 — not reliable enough within deep midfielders to rank them:
  Decision (within-DM reliability ~0.45; its confirmed results link is
  carried by forwards) and MOVE_ON_SPEED (0.475 in 2015/16). Shown
  greyed, with the reason.
For each dimension, show its within-DM reliability from the existing
results pages (cite the page). For RQ_rel within Card B's group, compute
it with Task 38's method (players >= 4 matches) and report it; if it is
below 0.60, RQ_rel moves to Tier 3 automatically.

## Step 4 — Outputs
- data/processed/scorecard_card_a.parquet, _card_b.parquet,
  _card_c.parquet.
- docs/scorecard/index.html: one self-contained page, no external
  requests. A sortable, searchable table per card; click a player to
  open his card (a bar per dimension: percentile with interval, tier
  badge, n). A legend explaining the tiers in plain words. Credits:
  "Data: StatsBomb (open data)" on all cards, and "Tracking: PFF FC /
  Gradient Sports WC2022" where AV appears.
- docs/scorecard/figure_praised.png: for each card, the praised-list
  players present (Task 41's fixed list), one row each, Tier 1 and Tier
  2 dimensions only, with intervals and the group median marked.
- docs/scorecard/figure_career.png: Card C's career lines.
Report on the results page: group sizes, per-dimension counts above /
below / can't tell, the within-DM reliability per dimension, and the
tier each dimension ended in.

## HARD RULES
- No new measures or claims; names are output, never a criterion.
- Every dimension carries its tier and reliability on the page.
- No change to earlier artifacts. Holdout untouched.
- No memory writes. Don't edit docs/JOURNAL.md. No interpretation.
- When finished, reply only that the task is done plus commit hashes.

## Output
docs/results/51-regista-scorecard.md (template). Commit per rule 9.
