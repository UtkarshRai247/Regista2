"""
Task 25, Step 2 (Task 24's Step 4): rebuild the candidate option space
and CANDIDATE_FEATURES on the CORRECTED geometry (geometry.py's
team_period_directions now returns +1 for every (team, period), fixed
in Task 24). `compute_candidate_features`'s own `direction` argument is
downstream of `team_period_directions`, so the full ~106M-row candidate
corpus must be rebuilt from scratch -- not just the value-model layer,
unlike Tasks 19d/21/22 which only touched the value models.

Reuses `grid.py`'s `process_match`/`main` UNCHANGED (no logic in that
file needs to change -- it already calls the now-fixed
`team_period_directions` via import) via monkeypatched output paths, so
Task 15's original `options_parts/` is left untouched.

Run: python src/engine_v2/grid_v2.py
"""
import warnings
from pathlib import Path

import grid

warnings.filterwarnings("ignore")

DATA_DIR = Path(__file__).parent.parent.parent / "data"
grid.OUT_DIR = DATA_DIR / "processed" / "engine_v2" / "options_parts_v2"
grid.SUMMARY_PATH = DATA_DIR / "engine_v2_step2_options_v2.json"

if __name__ == "__main__":
    grid.main()
