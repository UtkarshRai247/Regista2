"""
Task 01 — Step 5: behavior policy.

"Typical player" = pooled across all players, situational features only,
no player-identity feature (stated plainly per the plan: a player-specific
policy would make Decision ~= 0 by construction for every player,
defeating the point of the metric).

Trained on ALL candidate rows (chosen=1, unchosen=0) — unlike Step 2,
which only trains on chosen rows, this model needs both classes to learn
what makes an option likely to be picked. Same feature set as Step 1/2.
Match-level held-out split (same leakage logic as Step 2).

At inference, each pass's candidate scores are softmax-normalized over
that pass's own option set to get policy_probability(option), which sums
to 1 per pass, as needed by the Decision formula in Step 6.

Run: python src/decision_engine/policy.py
"""
import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.model_selection import GroupShuffleSplit

from pass_success import FEATURES, prep_X

warnings.filterwarnings("ignore")

DATA_DIR = Path(__file__).parent.parent.parent / "data"
SCORED_PATH = DATA_DIR / "processed" / "options_ev.parquet"
MODEL_PATH = DATA_DIR / "processed" / "policy_model.json"
OUT_PATH = DATA_DIR / "processed" / "options_policy.parquet"


def softmax_per_group(scores: np.ndarray, groups: np.ndarray) -> np.ndarray:
    out = np.empty_like(scores, dtype=float)
    df = pd.DataFrame({"score": scores, "group": groups})
    for _, idx in df.groupby("group").groups.items():
        s = df.loc[idx, "score"].values
        e = np.exp(s - s.max())
        out[idx] = e / e.sum()
    return out


def main():
    opts = pd.read_parquet(SCORED_PATH)

    gss = GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=42)
    train_idx, test_idx = next(gss.split(opts, groups=opts["match_id"]))
    train, test = opts.iloc[train_idx].copy(), opts.iloc[test_idx].copy()
    assert set(train["match_id"]) & set(test["match_id"]) == set(), "match leakage!"

    X_train, y_train = prep_X(train), train["chosen"].astype(int)
    X_test = prep_X(test)

    model = xgb.XGBClassifier(
        n_estimators=200, max_depth=4, learning_rate=0.05,
        subsample=0.8, colsample_bytree=0.8, random_state=42,
        eval_metric="logloss",
    )
    model.fit(X_train, y_train)
    model.save_model(MODEL_PATH)

    raw_score = model.predict_proba(X_test)[:, 1]
    policy_prob = softmax_per_group(raw_score, test["event_id"].values)
    test["policy_probability"] = policy_prob

    # top-1 / top-3 accuracy per pass on the held-out set
    ranked = test.sort_values(["event_id", "policy_probability"], ascending=[True, False])
    ranked["rank"] = ranked.groupby("event_id").cumcount()
    chosen_ranks = ranked.loc[ranked["chosen"], ["event_id", "rank"]]
    top1_acc = float((chosen_ranks["rank"] == 0).mean())
    top3_acc = float((chosen_ranks["rank"] < 3).mean())

    # score the FULL dataset (train+test) for downstream Decision calc
    X_all = prep_X(opts)
    opts["policy_raw_score"] = model.predict_proba(X_all)[:, 1]
    opts["policy_probability"] = softmax_per_group(
        opts["policy_raw_score"].values, opts["event_id"].values
    )
    opts.to_parquet(OUT_PATH)

    summary = {
        "n_train_matches": int(train["match_id"].nunique()),
        "n_test_matches": int(test["match_id"].nunique()),
        "n_test_passes": int(test["event_id"].nunique()),
        "top1_accuracy": top1_acc,
        "top3_accuracy": top3_acc,
    }
    print(json.dumps(summary, indent=2))
    (DATA_DIR / "policy_summary.json").write_text(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
