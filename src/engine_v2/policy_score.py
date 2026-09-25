"""
Task 17, Step 2 (build) + Step 3 input: scores the FULL 106,141,669-row
engine-v2 candidate corpus with the already-trained (Task 15, frozen,
not retrained here) policy_model.json, softmax-normalizes within each
pass's own option set, and reduces it to one compact per-pass table.

No feature/threshold/retraining changes: the policy model and
CANDIDATE_FEATURES are exactly Task 15's. The only new computation here
is the NaN-imputation fill values, recomputed from the full corpus
(rather than reusing Task 15's training-subsample-derived fill values,
which were never persisted to disk) -- this affects only the rare
zero-visible-opponent rows and is an imputation constant, not a model
or feature change.

Run: python src/engine_v2/policy_score.py
"""
import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import xgboost as xgb

from common import CANDIDATE_FEATURES, prep_X

warnings.filterwarnings("ignore")

DATA_DIR = Path(__file__).parent.parent.parent / "data"
EV_DIR = DATA_DIR / "processed" / "engine_v2" / "options_ev"
POLICY_MODEL_PATH = DATA_DIR / "processed" / "engine_v2" / "policy_model.json"
OUT_PATH = DATA_DIR / "processed" / "engine_v2" / "pass_policy_summary.parquet"
SUMMARY_PATH = DATA_DIR / "engine_v2_step2_policy_sharpness.json"


def softmax_per_group(scores: np.ndarray, groups: np.ndarray) -> np.ndarray:
    df = pd.DataFrame({"score": scores, "group": groups})
    out = np.empty(len(df))
    for _, g in df.groupby("group"):
        s = g["score"].values
        e = np.exp(s - s.max())
        out[g.index] = e / e.sum()
    return out


def mass_in_top_n(p_sorted_desc: np.ndarray, n: int) -> float:
    return float(p_sorted_desc[:n].sum())


def process_match(match_id: int, model, fill_values: dict) -> list:
    df = pd.read_parquet(EV_DIR / f"{match_id}.parquet")
    X, _ = prep_X(df, CANDIDATE_FEATURES, fill_values)
    raw_score = model.predict_proba(X)[:, 1]
    df["policy_probability"] = softmax_per_group(raw_score, df["event_id"].values)
    df["var_option"] = df["p_success"] * (1 - df["p_success"]) * (df["V_net_success"] - df["V_net_turnover"]) ** 2
    df["ev_x_prob"] = df["EV"] * df["policy_probability"]
    df["var_x_prob"] = df["var_option"] * df["policy_probability"]

    rows = []
    for eid, g in df.groupby("event_id", sort=False):
        p = g["policy_probability"].values
        p_sorted = np.sort(p)[::-1]
        entropy = float(-(p * np.log(p + 1e-15)).sum())
        chosen_row = g[g["chosen"]]
        rows.append({
            "match_id": match_id, "event_id": eid, "team": g["team"].iloc[0],
            "n_candidates": len(g),
            "ev_chosen": float(chosen_row["EV"].iloc[0]) if len(chosen_row) else None,
            "var_chosen": float(chosen_row["var_option"].iloc[0]) if len(chosen_row) else None,
            "policy_weighted_ev": float(g["ev_x_prob"].sum()),
            "policy_weighted_var": float(g["var_x_prob"].sum()),
            "unweighted_mean_ev": float(g["EV"].mean()),
            "entropy": entropy, "effective_options": float(np.exp(entropy)),
            "top10_mass": mass_in_top_n(p_sorted, 10), "top50_mass": mass_in_top_n(p_sorted, 50),
        })
    return rows


def main():
    print("Step 2: scoring policy on full corpus, building per-pass summary ...")
    model = xgb.XGBClassifier()
    model.load_model(str(POLICY_MODEL_PATH))

    match_ids = sorted(int(p.stem) for p in EV_DIR.glob("*.parquet"))
    print("  computing full-corpus fill values (imputation constants, not a feature change) ...")
    maxes = {c: -np.inf for c in CANDIDATE_FEATURES}
    for mid in match_ids:
        df = pd.read_parquet(EV_DIR / f"{mid}.parquet", columns=CANDIDATE_FEATURES)
        for c in CANDIDATE_FEATURES:
            m = df[c].max()
            if pd.notna(m) and m > maxes[c]:
                maxes[c] = float(m)
    fill_values = maxes

    all_rows = []
    for i, mid in enumerate(match_ids):
        all_rows.extend(process_match(mid, model, fill_values))
        if (i + 1) % 50 == 0:
            print(f"  {i + 1}/{len(match_ids)} matches, passes so far={len(all_rows)}")

    summary_df = pd.DataFrame(all_rows)
    summary_df.to_parquet(OUT_PATH)
    print(f"  {len(summary_df)} passes summarized -> {OUT_PATH}")

    corr = float(summary_df["policy_weighted_ev"].corr(summary_df["unweighted_mean_ev"]))
    med_eff = float(summary_df["effective_options"].median())

    def pct(s):
        return {str(p): float(np.percentile(s, p)) for p in (5, 25, 50, 75, 95)}

    report = {
        "n_passes": len(summary_df),
        "entropy_distribution": pct(summary_df["entropy"]),
        "effective_options_distribution": pct(summary_df["effective_options"]),
        "median_effective_options": med_eff,
        "top10_mass_distribution": pct(summary_df["top10_mass"]),
        "top50_mass_distribution": pct(summary_df["top50_mass"]),
        "corr_policy_weighted_vs_unweighted_mean_ev": corr,
        "pre_specified_reading": {
            "median_effective_options_gt_100": bool(med_eff > 100),
            "correlation_gt_0.95": bool(corr > 0.95),
            "diffuse_baseline_flag": bool(med_eff > 100 or corr > 0.95),
        },
        "fill_values": fill_values,
    }
    SUMMARY_PATH.write_text(json.dumps(report, indent=2, default=str))
    print(json.dumps({k: v for k, v in report.items() if k != "fill_values"}, indent=2, default=str))
    print(f"\nWrote {SUMMARY_PATH}")
    return report


if __name__ == "__main__":
    main()
