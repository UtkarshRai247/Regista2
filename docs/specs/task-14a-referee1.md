# Task 14a — Referee 1: do the objectives predict real outcomes?

Governing document: docs/specs/analysis-plan-v3.md, Amendments v3-1 to
v3-4. Read plan section 3 carefully.
NO leaderboards, NO player names, NO expert lists in this task.

## Step 0 — Commit Amendment v3-4 alone. Record hash and SHA-256.

## Step 1 — Rebuild the outcome inputs for each objective
For O1 (existing), O2 (clipped) and O3, build:
  - team-match mean Decision_obj (expect ~583-598 units; report actual
    counts per objective and any difference caused by O3's 99.6%
    option coverage);
  - possession-level mean Decision_obj over open-play possessions with
    at least 3 eligible passes (the same possessions Task 11 built;
    reuse that construction exactly).
Report how many units each objective loses relative to O1 and why.

## Step 2 — Run the identical battery per objective
Exactly the specifications already preregistered and already run for
O1. No new controls, no new outcomes, no changes.
  (a) team-match: xG and goals, WITH possession share (v2-6.3 primary
      form) and WITHOUT it (v2-9.2 PH-O4 form), clustered by team
      context;
  (b) possession level: probability the possession ends in a shot
      (logistic) and possession xG (OLS), with starting zone, number of
      passes and team-context fixed effects, clustered by match.
Report every coefficient standardized, with CI, p and n, in one table
per outcome with the three objectives side by side.

## Step 3 — Apply the plan's comparison rule
Plan v3 section 3: an objective WINS Referee 1 if BOTH the
possession-level xG coefficient AND the team-match xG coefficient in
the PH-O4 form (no possession share) are positive with CIs excluding
zero. Report WIN / NOT WIN for each objective. The rule is fixed.

## Step 4 — Report, do not interpret
State the three verdicts. Do not say which objective is "better", do
not mention players, do not speculate about the paper.

## HARD RULES
- No leaderboards, no player names, no expert lists, no Referee 2.
- No specification changes of any kind.
- Report all three objectives fully, including any that fail.
- No memory writes. Don't edit docs/JOURNAL.md.
- When finished, reply only that the task is done plus commit hashes.

## Output
docs/results/14a-referee1.md (template). Commit per rule 9.
