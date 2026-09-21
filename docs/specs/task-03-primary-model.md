# Task 03 — Primary Model

Amendment 2 of docs/specs/analysis-plan-pillar4.md is now in force.
Gate C is AUTHORIZED. Fitting is authorized. Do not stop again unless
something specified here is impossible.

## Step 1 — Rebuild the join under Amendment 2
- Apply the 3 crosswalk resolutions from A2.3.
- Widen the valuation window to 180 days, earliest record in window.
- Add days_to_valuation as a variable.
- Report the updated sample flow table and the final unit and player
  counts. Report tournament vs league split.
- Confirm explicitly that the 79 previously-matched units retained
  their original valuation records. If any changed, STOP and report.

## Step 2 — Fit the primary model
Exactly as specified in A2.2. OLS on log market value, standard errors
clustered by player.
Report: coefficients, clustered standard errors, t-statistics,
p-values, 95% confidence intervals, n, R-squared.
Report VIF for every predictor, with Decision's called out.

## Step 3 — Interpret Decision's coefficient in plain units
Report what a one-standard-deviation increase in Decision corresponds
to in percentage market value, with its confidence interval.
State whether the CI includes zero, and report the smallest effect the
data could rule out. A null must be reported as a precise null or an
imprecise one, not just "not significant".

## Step 4 — Secondary: H3
Same specification, outcome = change in log market value from the
valuation date to the closest record 12 months later. Include starting
log value as a control. Report sample size; if under 60 units, label it
underpowered.

## Step 5 — Robustness set (report ALL, no selection)
a. 90-day window, original 79 units
b. League units only
c. Minimum 250 passes instead of 200
d. Midfielders only
e. Without club strength
f. Attenuation-corrected Decision coefficient, using reliability 0.744
   (5th-95th: 0.691-0.792), with the corrected CI reflecting that range
Report every one, including any that contradict the primary result.

## Step 6 — Exploratory, clearly labeled
Execution in the primary specification, with its reliability stated
inline as 0.482 [0.300, 0.603] and a note that it is not trustworthy.

## Output
docs/results/03-primary-model.md following the template.
Report what the models say. Do not editorialize about whether the
result is good or bad for the project.
