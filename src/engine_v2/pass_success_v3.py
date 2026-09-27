"""
Task 25, Step 2 (Task 24's Step 4): retrain the pass-success model on
the corrected candidate features (`options_parts_v2`, built by
`grid_v2.py` on the now-fixed geometry). Reuses `pass_success_v2.py`'s
`main`/`load_chosen_rows`/`score_all_candidates` UNCHANGED (same
hyperparameters, same match-disjoint split, same T5/T7 definitions) via
monkeypatched I/O paths, so Task 15's original `options_scored/` and
`pass_success_model.json` are left untouched.

Run: python src/engine_v2/pass_success_v3.py
"""
import warnings
from pathlib import Path

import pass_success_v2 as ps2

warnings.filterwarnings("ignore")

DATA_DIR = Path(__file__).parent.parent.parent / "data"
ps2.PARTS_DIR = DATA_DIR / "processed" / "engine_v2" / "options_parts_v2"
ps2.SCORED_DIR = DATA_DIR / "processed" / "engine_v2" / "options_scored_v2"
ps2.MODEL_PATH = DATA_DIR / "processed" / "engine_v2" / "pass_success_model_v3.json"
ps2.SUMMARY_PATH = DATA_DIR / "engine_v2_step4_pass_success_v3.json"

if __name__ == "__main__":
    ps2.main()
