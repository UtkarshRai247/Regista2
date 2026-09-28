"""
Task 26, Step 2: re-run MOVE_ON_SPEED / HOLD_VARIATION with the
preregistered specification (Amendment T-2.3) UNCHANGED, but with
`redesign_metrics.py`'s own local `team_period_directions` fixed to
match `engine_v2/geometry.py`'s Task 24 correction (StatsBomb
events/360 frames are already team-relative -- every team attacks
toward x=120 in its own events, so there is nothing to infer; the
function returns +1 for every (team, period) actually present).

`redesign_metrics.py` keeps its own local, independently-ported copy of
this function by design (zero import-time dependency on
src/decision_engine/ or src/engine_v2/, the same sys.path reasoning
`engine_v2/geometry.py`'s own docstring gives). Rather than edit that
frozen file in place (which would silently change what Task 16b's own
results page reproduces from its recorded commit), this script
monkeypatches the ONE function on the module object before calling its
unchanged `main()` -- the same technique used throughout this project
to reuse a frozen script's other functions while changing one piece
(e.g. `falsification_v2.py`'s `t4mod.EV_DIR` monkeypatch).

Run: python src/tempo/redesign_metrics_v2.py
"""
import warnings
from pathlib import Path

import pandas as pd

import redesign_metrics as rm

warnings.filterwarnings("ignore")

DATA_DIR = Path(__file__).parent.parent.parent / "data"


def team_period_directions_fixed(events: pd.DataFrame) -> dict:
    """Routed to engine_v2's corrected convention (Task 24): +1 for
    every (team, period) actually present in `events`."""
    teams = [t for t in events["team"].dropna().unique().tolist()]
    periods = sorted(events["period"].dropna().unique().tolist())
    return {(t, p): 1 for t in teams for p in periods}


rm.team_period_directions = team_period_directions_fixed
rm.OUT_PATH = DATA_DIR / "processed" / "tempo_redesign_metrics_v2.parquet"
rm.MOVE_RESID_PATH = DATA_DIR / "processed" / "tempo_redesign_move_residuals_v2.parquet"
rm.HOLD_RESID_PATH = DATA_DIR / "processed" / "tempo_redesign_hold_residuals_v2.parquet"
rm.SUMMARY_PATH = DATA_DIR / "tempo_step2b_redesign_v2.json"

if __name__ == "__main__":
    rm.main()
