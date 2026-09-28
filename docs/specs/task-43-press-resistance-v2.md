# Task 43 — Press resistance, done properly (a disclosed second attempt)

Written 2026-09-28 by the research lead after reading
docs/results/42-improvement-round-2.md, before any result.
Study sample and PFF WC2022 only; holdout spent.

## Why, and the disclosure
Task 42's press-resistance measure gave the project's first
pre-declared hit on the praised-players list (PR_keep, T = +0.69,
p = 0.014, direction "higher" declared in advance), and across all
players PR_keep predicted reaching the final third (p = 0.0014). But
its "keep" outcome was weak, and that is the research lead's brief's
fault: it judged the receiver's FIRST action, which is a carry 84% of
the time, and a carry is almost never lost. So "keep" mostly measured
"didn't lose it in the first second". Stability could also only be
checked on 7 player-seasons.
This task fixes the definition (Task 42 Q1: yes, judge the end of his
spell) and the stability check. It is a SECOND ATTEMPT made after
seeing Task 42, and is reported as such beside Task 42's numbers,
whatever it shows.

## Step 0 — Commit this brief alone. Record the hash.

## Step 1 — The corrected measure (StatsBomb 360, 292 matches)
Units: Task 42's pressured receptions (same PRESSURED rule).
The receiver's SPELL = from the reception until the first of: his Pass,
his Shot, his Miscontrol, his Dispossessed, his failed Dribble, or an
opponent's on-ball event in the same possession (Ball Recovery,
Interception, Duel won, Block, Clearance) or the possession ending.
  keep_spell = 1 if the spell ends with his COMPLETED pass; 0 if it
               ends in any loss above or an incomplete pass. Spells
               ending in his shot are excluded (report the count).
  fwd_spell  = 1 if keep_spell AND the completed pass's end x minus
               the reception x is >= 5 units; else 0.
Baseline: Task 42's classifier specification and context features,
refit for each outcome. PR2_keep, PR2_fwd = outcome - p_oof; player
score = mean over his pressured receptions.
Report: n spells, exclusions, base rates, baseline AUC, and the
correlation of player PR2_keep with Task 42's PR_keep.

## Step 2 — Stability at player level
Task 38's R1 method: for each player, 100 random splits of his MATCHES
into halves; correlate half-means across players; Spearman-Brown.
Players with >= 4 matches and >= 40 pressured receptions. Report for
the 111 deep midfielders' subset and for all players.
PASS if the deep-midfield median >= 0.60 (report n).

## Step 3 — Results (P-test)
As Task 42 Step 2 R2 (unit = pressured reception, S = other-match PR2,
>= 50 elsewhere, Y_F3 and net xG window 10, team-match FE, role FE,
g refit, SE by player), with the RETENTION control redefined the same
way: Y = keep_spell over ALL his completed receptions, S = his
other-match keep_spell rate (>= 100 elsewhere). All players and deep
midfielders.

## Step 4 — Praised list
Task 41 Step 7's method, list and permutation settings, >= 50 pressured
receptions. Pre-declared direction: HIGHER on PR2_keep and PR2_fwd.
Also report the Holm-adjusted p across EVERY directional praised-list
test so far: Task 41 (AV, AV_vis, RQ_rel: lower), Task 42 (PR_keep,
PR_fwd: higher) and this task (PR2_keep, PR2_fwd: higher).

## Step 5 — A second data source (convergent check, report only)
PFF WC2022: receptions where PFF's pressureType (on the reception or
the receiver's initial touch) is not 'N'; keep_pff = his spell (PFF
possession events) ends with his completed pass. Context-adjust with a
baseline of the same form. For players with >= 30 such receptions in
BOTH sources restricted to WC2022 matches: Pearson correlation between
PFF-based and StatsBomb-based press resistance, with 95% CI.

## Step 6 — Deep-midfield table
Task 29's method on PR2_keep and PR2_fwd (output only).

## Claim rule (fixed now)
- Within-DM results: Holm across this task's DM results tests, AND the
  retention control positive on the same rows. Labelled "study sample
  only; second attempt".
- Praised list: a statement is allowed only if the Holm-adjusted p
  across all directional praised-list tests (Step 4) is < 0.05.
- Stability: the stated bar.
- Whatever the outcome, Task 42's version stays reported beside this.

## HARD RULES
- No change to earlier artifacts or definitions other than the new
  measures here.
- Holdout untouched.
- Memory gate as in Task 25. Commit the page after Step 2, then at end.
- No memory writes. Don't edit docs/JOURNAL.md. No interpretation.
- When finished, reply only that the task is done plus commit hashes.

## Output
docs/results/43-press-resistance-v2.md (template). Commit per rule 9.
