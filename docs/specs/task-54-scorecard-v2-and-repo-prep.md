# Task 54 — Scorecard v2 (tempo added, Figure 1) and repo preparation

Written 2026-09-29 by the research lead, before any result. Descriptive
and housekeeping only: no new tests, no new claims. Holdout, reserved,
and the Task 53 replication half are not re-analysed beyond what is
listed. Supersedes the unrun Task 30 brief (repo prep), which predates
the PFF, women's and 2015/16 data.

## Step 0 — The research lead commits this brief alone; record the hash.
(The abstract draft docs/abstract/SSAC27-abstract-v2.md is committed
with it.)

## Part A — Scorecard v2

A1. Card A (2015/16, all five leagues, Task 44's 185 deep midfielders):
    add Task 52/53's tempo measures (M4_ACCEL, M4_SLOW, M4_SWITCH,
    M3_speed, M2), computed on ALL 1,551 matches with ONE baseline fit
    per measure (5 match folds over all 2015/16, seed 20260929), same
    definitions as Task 53. This is descriptive, not a test.
A2. Tiers (fixed now; shown on every card with the evidence behind it):
    TIER 1A, confirmed on held-back data FOR DEEP MIDFIELDERS:
      switching (M4_SWITCH; Task 53 R1).
    TIER 1B, stable within DMs and confirmed on held-back data for ALL
      players: press resistance (PR2_flag_keep, A1 beside it; Task 48
      C4, C6), speeding up (M4_ACCEL; R4), recycling (M4_SLOW; R5),
      quick-and-safe under pressure (M2; R7).
    TIER 2, stable, no confirmed results link: release speed (M3_speed),
      willingness (W), HOLD_VARIATION, AV (with its "fewer chances;
      exploratory" note).
    TIER 3, not reliable enough within DMs: Decision, MOVE_ON_SPEED,
      RQ_rel.
    Tempo style measures (M4_*) are labelled STYLE on the card (a high
    or low value is a type, not better or worse); the tier describes
    the evidence, not a ranking of quality.
A3. HOLD_VARIATION interval: player-level bootstrap over his matches
    (1,000 resamples, seed 20260929), 90% percentile interval; apply the
    CLEARLY ABOVE / BELOW / CAN'T TELL labels.
A4. Card B reliabilities: compute each dimension's within-DM stability
    on the study sample itself (Task 38's method, >= 4 matches) and show
    it; Task 51's automatic Tier 3 rule (< 0.60) applies.
A5. Figure 1 (docs/scorecard/figure1.png, for the abstract): Card A,
    rows = the praised-list deep midfielders present (by ID from
    docs/splits/praised_ids.csv) plus the top three deep midfielders by
    shrunken press resistance; columns = PR2_flag_keep, M4_ACCEL,
    M4_SLOW, M4_SWITCH, M2, W; each cell = within-DM percentile with its
    90% interval; tier badges in the column header. Names are output;
    the selection rule is the one above, nothing else.
A6. Also report, for the abstract's check: Busquets' and Kroos'
    percentile and interval on M4_ACCEL, M2 and M4_SWITCH in Card A.
A7. Rebuild docs/scorecard/index.html with A1-A4. Also write a PUBLIC
    variant docs/scorecard/index_public.html with every PFF-derived
    value (AV) removed and a note that it is omitted.

## Part B — Repo preparation (do NOT change visibility, do NOT push)
B1. History scan across ALL git history: any committed file under data/
    or any raw StatsBomb/PFF data file; any secret (keys, tokens,
    passwords, .env, SSH keys); any personal email other than
    urai2@uw.edu and rai.utkarsh2007@gmail.com (the commit author); any
    file > 10 MB. If data or a secret is found, STOP and report; do not
    rewrite history.
B2. List every committed file that contains PFF-derived numbers (results
    pages, JSONs, scorecard files, abstract drafts), so the author can
    decide before going public.
B3. README.md at the repo root: what the project measures (no claims
    beyond the abstract draft); data credits "Data: StatsBomb (open
    data)" with a link to https://github.com/statsbomb/open-data and the
    note to accept StatsBomb's user agreement and register at their
    resource centre, and "Tracking: PFF FC / Gradient Sports World Cup
    2022" with a note that PFF data is not redistributed; StatsBomb logo
    only if a copy exists in their media pack (else a TODO line); how to
    download each dataset (study, holdout, 2015/16 and reserved via the
    open-data ZIP, PFF via the author's source); how to reproduce the
    headline results (the script sequence for Tasks 24-25, 35, 37, 44,
    48, 52-53, 51/54); where the preregistrations, results pages
    (including every failed test), benchmarks and decisions live.
B4. .gitignore covers data/, .venv/, __pycache__/, .DS_Store, model and
    output files. LICENSE: MIT, "Utkarsh Rai", 2026. requirements.txt
    from the packages the headline scripts import, versions from .venv.
B5. Do NOT stage docs/JOURNAL.md or AGENTS.md.
B6. Report the exact command the author runs to make the repo public,
    without running it.

## HARD RULES
- No new tests or claims. No change to any earlier artifact.
- Holdout untouched; reserved and replication data only read through
  the existing built tables named above.
- Do not change repo visibility; do not push; do not rewrite history.
- No memory writes. No interpretation.
- When finished, reply only that the task is done plus commit hashes.

## Output
docs/results/54-scorecard-v2-and-repo-prep.md (template). Commit per rule 9.
