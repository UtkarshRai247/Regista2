# Task 19c — Offside: fix the sort index, re-test, re-run if it passes

The Task 19 conclusion ("offside is not detectable from freeze frames")
rests on a bug, not on a measurement. Fix, retest against the same
ground truth, and only then decide.

## Step 0 — Commit this brief. Record hash.

## Step 1 — The bug
src/engine_v2/features.py, offside block:
    opp_nx_sorted = np.sort(opp_n[:, 0])   # ascending
    second_rearmost_nx = opp_nx_sorted[1]  # second SMALLEST x
Coordinates are normalised so the PASSING team attacks toward high x, so
the defending goalkeeper has the HIGHEST x and the last defender the
second-highest. The offside line is the second-LARGEST x among
opponents: opp_nx_sorted[-2], not [1].
As written the line sits at the opponents' second-most-advanced player,
usually a forward pressing high, so nearly every forward destination is
flagged.
Change that one index. Change nothing else in the file.
Before rerunning anything, print a worked example from one real frame:
all opponent normalised x values sorted, the old line, the new line, the
passer's x, and the flag under each for three candidate destinations.

## Step 2 — Re-test against ground truth, same criterion as Task 19
On the same eligible population and the same StatsBomb "Pass Offside"
labels (790 in-population cases), report for the CORRECTED rule:
  - false-positive rate on completed passes;
  - recall on truly-offside passes;
  - both broken down by visible-opponent count and attacking half;
  - the Task 19 figures (43.11% / 50.51%) beside them.
Then re-run the Task 19 Step 2 candidate families R1-R4 on top of the
corrected rule and apply the SAME fixed selection rule: maximise recall
subject to a false-positive rate on completed passes below 5%.

## Step 3 — Only if a rule now clears the 5% bar
Re-enable offside filtering in the restriction with the selected rule,
then re-run Task 19 Steps 3 and 4 exactly as before: restricted-policy
coverage, refit temperature, recompute Decision/Risk, T6 reliability
sweep, separation check, and the cross-fitted outcome-validation
battery.
Report four columns where available: engine v1 published, Task 18
cross-fitted, Task 19 cross-fitted (no offside), and Task 19c
cross-fitted (corrected offside).
If no rule clears the bar even after the fix, offside filtering stays
dropped and Task 19's conclusion stands — but it is then a real
measurement rather than an artefact. Report which it is.

## HARD RULES
- One code change: the sort index. Nothing else in features.py, no
  other engine component, no retraining of value or success models
  beyond what the cross-fitting harness already does.
- The selection rule is fixed; do not adjust the 5% bar.
- Check whether any OTHER feature in features.py uses a sorted-array
  index that assumes the wrong end, and report what you find. Do not
  fix anything you find without reporting it first.
- No leaderboards, no player identity, no interpretation.
- No memory writes. Don't edit docs/JOURNAL.md.
- When finished, reply only that the task is done plus commit hashes.

## Output
docs/results/19c-offside-fix.md (template). Commit per rule 9.
