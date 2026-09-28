"""
Task 26, Step 1(b): score the holdout candidates with the FROZEN
engine v5 pass-success model (`pass_success_model_v3.json`) and its own
frozen fill_values (`engine_v2_step4_pass_success_v3.json`). No
retraining, no refitting -- reuses `pass_success_v2.score_all_candidates`
unchanged via monkeypatched I/O paths and the already-fitted model.

Run: python src/engine_v2/pass_success_score_holdout.py
"""
import json
import warnings
from pathlib import Path

import xgboost as xgb

import pass_success_v2 as ps2

warnings.filterwarnings("ignore")

DATA_DIR = Path(__file__).parent.parent.parent / "data"
MODEL_PATH_V3 = DATA_DIR / "processed" / "engine_v2" / "pass_success_model_v3.json"
FILL_VALUES_PATH = DATA_DIR / "engine_v2_step4_pass_success_v3.json"

ps2.PARTS_DIR = DATA_DIR / "processed" / "engine_v2" / "options_parts_holdout"
ps2.SCORED_DIR = DATA_DIR / "processed" / "engine_v2" / "options_scored_holdout"


def main():
    print("Task 26 Step 1(b): scoring holdout candidates with the frozen pass-success model v3 ...")
    model = xgb.XGBClassifier()
    model.load_model(str(MODEL_PATH_V3))
    fill_values = json.loads(FILL_VALUES_PATH.read_text())["fill_values"]
    ps2.score_all_candidates(model, fill_values)
    print(f"\nWrote scored candidates to {ps2.SCORED_DIR}")


if __name__ == "__main__":
    main()
