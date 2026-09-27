"""
Task 21, Step 2 (continued): recomputes V_net_success/V_net_turnover/EV
corpus-wide using the RETRAINED value models (value_models_v3.py, with
the three new possession-state features). Reuses `ev_policy.build_ev_for_match`
unchanged (already takes model_for/model_against as parameters) via
monkeypatching its output directory -- every prior task's own `options_ev*`
directory is left untouched. `options_scored/` (pass-success-scored input,
unaffected by this task) is read as-is.

Run: python src/engine_v2/ev_recompute_v3.py
"""
import warnings
from pathlib import Path

import xgboost as xgb

import ev_policy as evp

warnings.filterwarnings("ignore")

DATA_DIR = Path(__file__).parent.parent.parent / "data"
MODEL_FOR_PATH_V3 = DATA_DIR / "processed" / "engine_v2" / "value_model_for_v3.json"
MODEL_AGAINST_PATH_V3 = DATA_DIR / "processed" / "engine_v2" / "value_model_against_v3.json"

evp.EV_DIR = DATA_DIR / "processed" / "engine_v2" / "options_ev_v3"


def main():
    print("Task 21 Step 2: recomputing EV corpus-wide with possession-state value models ...")
    model_for = xgb.XGBClassifier()
    model_for.load_model(str(MODEL_FOR_PATH_V3))
    model_against = xgb.XGBClassifier()
    model_against.load_model(str(MODEL_AGAINST_PATH_V3))

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
