"""
Task 25, Step 2 (Task 24's Step 4): recompute V_net_success/
V_net_turnover/EV corpus-wide using the corrected candidate features
(`options_scored_v2`, from `pass_success_v3.py`) and the retrained
value models (`value_models_v5_retrain.py`'s `value_model_for_v5.json`/
`value_model_against_v5.json`). Reuses `ev_policy.build_ev_for_match`
unchanged via monkeypatched I/O directories.

Run: python src/engine_v2/ev_recompute_v4.py
"""
import warnings
from pathlib import Path

import xgboost as xgb

import ev_policy as evp

warnings.filterwarnings("ignore")

DATA_DIR = Path(__file__).parent.parent.parent / "data"
MODEL_FOR_PATH_V5 = DATA_DIR / "processed" / "engine_v2" / "value_model_for_v5.json"
MODEL_AGAINST_PATH_V5 = DATA_DIR / "processed" / "engine_v2" / "value_model_against_v5.json"

evp.SCORED_DIR = DATA_DIR / "processed" / "engine_v2" / "options_scored_v2"
evp.EV_DIR = DATA_DIR / "processed" / "engine_v2" / "options_ev_v4"


def main():
    print("Task 25 Step 2: recomputing EV corpus-wide on corrected geometry + retrained value models ...")
    model_for = xgb.XGBClassifier()
    model_for.load_model(str(MODEL_FOR_PATH_V5))
    model_against = xgb.XGBClassifier()
    model_against.load_model(str(MODEL_AGAINST_PATH_V5))

    match_ids = sorted(int(p.stem) for p in evp.SCORED_DIR.glob("*.parquet"))
    n_rows = 0
    for i, mid in enumerate(match_ids):
        n = evp.build_ev_for_match(mid, model_for, model_against)
        if n:
            n_rows += n
        if (i + 1) % 50 == 0:
            print(f"  {i + 1}/{len(match_ids)} matches, EV rows so far={n_rows}")
    print(f"  total EV rows: {n_rows}")
    print(f"\nWrote per-match files to {evp.EV_DIR}")
    return n_rows


if __name__ == "__main__":
    main()
