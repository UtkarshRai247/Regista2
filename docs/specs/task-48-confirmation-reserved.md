# Task 48 — Confirmation on the untouched (RESERVED) data

Written 2026-09-28 by the research lead after reading results 46 and 47,
BEFORE any reserved file has been opened. This is the ONLY use of the
reserved data. Every definition, threshold and test below is fixed now;
none may change after the data is opened (operational gaps are recorded
as deviations and resolved in the way that least favours the
hypothesis).

## Data
The 64 reserved (competition_id, season_id) pairs listed in
docs/results/46-movers-and-spatial-physical.md, read from
data/raw_1516/open-data-master/ (events, matches, lineups). Event data
only. Report matches and events per competition-season, and which
competitions are club and which are national-team. Run
task24_evidence.py part (i) (team-relative coordinates).

## Step 0 — Commit this brief alone. Record the hash.

## Step 1 — Measures (definitions unchanged from the named tasks)
- Eligible pass, event-only g features, Y_F3, net xG window 10,
  completion and retention controls: exactly as in Task 44 and its
  corrections (dff3e4e, 8f6ff58), with g refit on the reserved data
  (5 match folds, seed 20260928).
- Roles: Task 32's rule (>= 100 eligible passes). Deep midfielder
  (DM) = >= 50% of eligible passes at C/L/R Defensive Midfield AND
  >= 300 eligible passes (lower than 2015/16's 500 because most
  reserved players have fewer matches; fixed now).
- PR2_flag_keep: Task 44 Step 2's definition; baseline refit here.
- W (physical willingness): Task 46 Part B's definition; baseline refit.
- E1, P_H: Task 47 Step 1's definitions; baseline refit.
Report counts per role, the DM list (names, matches, pressured
receptions), and every baseline's AUC.

## Step 2 — The confirmatory family (fixed now; Holm across all five)
C1 DM:  PR2_flag_keep -> Y_F3. Unit = pressured reception; S =
        other-match mean (>= 50 elsewhere). Task 44 P-test. Coef > 0.
C2 DM:  W -> Y_F3. Unit = completed reception; S = other-match W
        (>= 100 elsewhere). Task 46 B3 (alone). Coef > 0.
C3 ALL: Task 47 Step 2's model. E1 coef < 0; AND the Task 47 (a)
        placebo must NOT be negative with p < 0.05.
C4 ALL: press resistance travels: players with a CLUB context and an
        INTERNATIONAL context in the reserved data (>= 30 pressured
        receptions each); PR2_flag_keep correlation disattenuated with
        split-half reliabilities, 1,000-player bootstrap (Task 46
        A-ii's recipe). p = share of bootstrap r_true <= 0 (x2 for
        two-sided). r_true > 0 required. If fewer than 15 movers
        qualify, C4 is NOT RUN and drops from the family (report n).
C6 ALL: PR2_flag_keep -> Y_F3 with S = other-match A1 score (Task 45's
        team demeaning, by team x competition-season). Coef > 0.
CONFIRMED (each): Holm-adjusted p < 0.05 with the stated sign, AND the
positive control on the same rows (C1, C2, C6) has p < 0.05.
Report coefficient, 95% CI, raw p, Holm p, n units, n players, MDE.

## Step 3 — Report only (no claim)
- C1 and C2 with Y = net xG.
- Stability (Task 38's method, >= 10 matches) of PR2_flag_keep and W,
  DMs and all.
- The praised list (Task 41 Step 7's method; direction higher for
  PR2_flag_keep) for players present.
- Deep-midfield tables (Task 29's method) for PR2_flag_keep and W.
- The spatial-vs-physical trade-off CANNOT be tested here (no positional
  data); say so.

## HARD RULES
- This is the single use of the reserved data. Do not run anything on it
  that is not listed here.
- No change to any definition fixed in Tasks 32-47.
- Holdout untouched. Memory gate as in Task 25; one match in memory.
- No memory writes. Don't edit docs/JOURNAL.md. No interpretation.
- When finished, reply only that the task is done plus commit hashes.

## Output
docs/results/48-confirmation-reserved.md (template). Commit per rule 9.
