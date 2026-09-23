# Task 09b — Horizon sensitivity retry (v2-6.2, v2-7.2)

Short task. Only Part 2 of Task 09, resumed.

## Step 0 — Commit Amendment v2-7 alone. Record hash and SHA-256.

## Step 1 — Check the machine first
Swap-in-use is NOT the gate: macOS never reclaims written swap, so it
records past pressure, not present headroom. Use live pressure instead.
Report `memory_pressure | tail -3` and `vm_stat`. Compute available
memory as (free + inactive + purgeable) x page size.
Gate: proceed if system-wide memory free percentage >= 40% AND
available memory >= 3 GB. Otherwise STOP and report both numbers.

## Step 2 — Resume horizon 5, then run horizon 15
Resume from data/processed/possession_value_parts_h5/ (197 of 299
matches cached). Then build horizon 15 from scratch. Per-match parquet
parts, nothing accumulated in memory across matches.
Re-check live pressure every 50 matches; if free percentage drops below
20% OR available memory falls below 1.5 GB, STOP, report how many
matches are cached, and leave the cache resumable. Do not gate on swap.

## Step 3 — Recompute and apply the rule
Non-cross-fitted values, confirmation half, for the 3 candidates that
were ROBUST before cross-fitting (middle zone, lateral_medium, all three
game states): G + CI, P, L, PH-2, at horizon 5 and horizon 15, with the
horizon-10 numbers alongside.
Apply v2-6.2's fixed rule and report horizon-robust YES/NO per candidate.

## HARD RULES
- Frozen code except the horizon parameter. The verified
  build_match_rows_horizon function is already validated against the
  horizon-10 cache; do not modify it.
- No other analysis. No memory writes. Don't edit docs/JOURNAL.md.
- Report partial progress honestly if it stops again.
- When finished, reply only that the task is done plus commit hashes.

## Output
docs/results/09b-horizon.md (template). Commit per rule 9.
