# Task 01b — Pre-join Diagnostics

Short task. No market value data. Do not load or join transfermarkt
data.

## 1. Sample flow table
Report attrition as a table, from all events in the 299-match sample
down to the final analysis units, one row per filter, with counts
remaining after each:
  all events -> passes -> open play -> freeze frame present ->
  >=6 visible players -> angle match accepted -> aggregated to
  player-competition-season -> >=200 eligible passes
Report the final count of units and the number of distinct players.

## 2. Re-estimate reliability with repeated splits
Re-run Gate A reliability for Decision and Execution using 100 repeated
random splits at the 200-pass threshold. Report median, 5th and 95th
percentile across splits. This supersedes the single-split numbers.

## 3. Pass success model calibration on chosen passes
Check whether the Step 2 model is miscalibrated specifically on chosen
passes. Report predicted vs observed completion rate in deciles of
predicted probability, for chosen passes only. State whether the model
systematically over- or under-predicts success on chosen passes, and
whether that explains the persistent negative Execution mean.

## 4. Descriptives for the analysis sample
For the 138-unit sample: distribution of Decision, mean and SD, and the
10 highest and 10 lowest players by Decision with their position and
competition. This is a face-validity check, not a result.

## Output
docs/results/01b-diagnostics.md following the template.
