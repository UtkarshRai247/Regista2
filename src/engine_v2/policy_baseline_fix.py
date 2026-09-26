"""
Task 18, Step 1: sharpen the policy baseline. Two changes, judged ONLY
on held-out policy accuracy (top-1/top-3 accuracy, log-likelihood,
effective options, mass concentration) -- never on a Decision value or
an outcome, per the hard rule.

(a) RESTRICTED CANDIDATE SET for the policy: drop candidates with
    p_success < 0.05, offside destinations, and destinations beyond 45
    yards. All three columns already exist in options_ev (Task 15's
    frozen output); no retraining, no feature changes -- the
    pass-success/value models and their features are untouched, only
    which candidates the POLICY considers is restricted.
(b) TEMPERATURE CALIBRATION: a single scalar T fit on TRAINING matches'
    restricted candidates by maximizing log-likelihood of the actual
    chosen destination under softmax(raw_score / T), then applied
    (fixed) to the held-out TEST matches for every reported metric.

No new dependency: scipy (already used in this project) provides
logsumexp and a bounded scalar minimizer.

Run: python src/engine_v2/policy_baseline_fix.py
"""
import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import xgboost as xgb
from scipy.special import logsumexp
from scipy.optimize import minimize_scalar

from common import CANDIDATE_FEATURES, match_disjoint_split, prep_X

warnings.filterwarnings("ignore")

DATA_DIR = Path(__file__).parent.parent.parent / "data"
EV_DIR = DATA_DIR / "processed" / "engine_v2" / "options_ev"
POLICY_MODEL_PATH = DATA_DIR / "processed" / "engine_v2" / "policy_model.json"
SUMMARY_PATH = DATA_DIR / "engine_v2_step1_policy_baseline_fix.json"

RESTRICT_MIN_P_SUCCESS = 0.05
RESTRICT_MAX_DISTANCE_U = 45.0
RNG_SEED = 42
TEST_SIZE = 0.2


def load_scored_match(mid: int, model, fill_values: dict) -> pd.DataFrame:
    cols = CANDIDATE_FEATURES + ["match_id", "event_id", "chosen", "p_success",
                                   "offside_destination", "EV"]
    df = pd.read_parquet(EV_DIR / f"{mid}.parquet", columns=cols)
    X, _ = prep_X(df, CANDIDATE_FEATURES, fill_values)
    df["raw_score"] = model.predict_proba(X)[:, 1]
    return df


def softmax_per_group(scores: np.ndarray, groups: np.ndarray, T: float = 1.0) -> np.ndarray:
    df = pd.DataFrame({"score": scores / T, "group": groups})
    out = np.empty(len(df))
    for _, g in df.groupby("group"):
        s = g["score"].values
        e = np.exp(s - s.max())
        out[g.index] = e / e.sum()
    return out


def policy_metrics(df: pd.DataFrame, T: float, restricted: bool) -> dict:
    """df: candidate rows for one policy 'world' (already filtered if
    restricted). Computes policy_probability via softmax(raw_score/T)
    within event_id, then top-1/3 accuracy (only over passes whose
    chosen candidate survived filtering), effective options, mass
    concentration, and the policy-weighted vs unweighted mean EV
    correlation (over whichever candidates are present)."""
    df = df.copy()
    df["policy_probability"] = softmax_per_group(df["raw_score"].values, df["event_id"].values, T)

    has_chosen = df.groupby("event_id")["chosen"].any()
    covered_events = set(has_chosen[has_chosen].index)
    n_total_passes = df["event_id"].nunique()
    n_covered = len(covered_events)

    top1_hits, top3_hits, loglik = 0, 0, 0.0
    entropies, top10_masses, top50_masses = [], [], []
    weighted_evs, unweighted_evs = [], []
    for eid, g in df.groupby("event_id"):
        p = g["policy_probability"].values
        p_sorted = np.sort(p)[::-1]
        entropy = float(-(p * np.log(p + 1e-15)).sum())
        entropies.append(entropy)
        top10_masses.append(float(p_sorted[:10].sum()))
        top50_masses.append(float(p_sorted[:50].sum()))
        weighted_evs.append(float((g["EV"] * g["policy_probability"]).sum()))
        unweighted_evs.append(float(g["EV"].mean()))
        if eid in covered_events:
            ranked = g.sort_values("policy_probability", ascending=False).reset_index(drop=True)
            rank = ranked.index[ranked["chosen"]].tolist()[0]
            top1_hits += int(rank == 0)
            top3_hits += int(rank < 3)
            chosen_p = float(g.loc[g["chosen"], "policy_probability"].iloc[0])
            loglik += np.log(max(chosen_p, 1e-15))

    corr = float(pd.Series(weighted_evs).corr(pd.Series(unweighted_evs)))
    return {
        "restricted": restricted, "temperature": T,
        "n_total_passes": int(n_total_passes), "n_covered_passes": int(n_covered),
        "coverage": n_covered / n_total_passes if n_total_passes else None,
        "top1_accuracy": top1_hits / n_covered if n_covered else None,
        "top3_accuracy": top3_hits / n_covered if n_covered else None,
        "mean_log_likelihood_per_pass": loglik / n_covered if n_covered else None,
        "median_effective_options": float(np.median(np.exp(entropies))),
        "median_top10_mass": float(np.median(top10_masses)), "median_top50_mass": float(np.median(top50_masses)),
        "corr_policy_weighted_vs_unweighted_mean_ev": corr,
    }


def fit_temperature(train_df: pd.DataFrame) -> float:
    """Single scalar T maximizing log-likelihood of the chosen candidate
    under softmax(raw_score/T), fit on TRAINING matches' restricted
    candidates (only passes whose chosen candidate survived
    restriction)."""
    has_chosen = train_df.groupby("event_id")["chosen"].any()
    covered = set(has_chosen[has_chosen].index)
    df = train_df[train_df["event_id"].isin(covered)]

    def neg_log_lik(T):
        total = 0.0
        for _, g in df.groupby("event_id"):
            s = g["raw_score"].values / T
            log_probs = s - logsumexp(s)
            total -= log_probs[g["chosen"].values.argmax()]
        return total

    result = minimize_scalar(neg_log_lik, bounds=(0.001, 20.0), method="bounded",
                              options={"xatol": 1e-3})
    return float(result.x)


def restrict(df: pd.DataFrame) -> pd.DataFrame:
    return df[(df["p_success"] >= RESTRICT_MIN_P_SUCCESS) & (~df["offside_destination"])
              & (df["distance_u"] <= RESTRICT_MAX_DISTANCE_U)]


def main():
    print("Step 1: sharpen the policy baseline ...")
    model = xgb.XGBClassifier()
    model.load_model(str(POLICY_MODEL_PATH))

    match_ids = sorted(int(p.stem) for p in EV_DIR.glob("*.parquet"))
    print("  computing fill values (imputation constants, unchanged from Task 17's approach) ...")
    fill_values = {c: -np.inf for c in CANDIDATE_FEATURES}
    for mid in match_ids:
        df = pd.read_parquet(EV_DIR / f"{mid}.parquet", columns=CANDIDATE_FEATURES)
        for c in CANDIDATE_FEATURES:
            m = df[c].max()
            if pd.notna(m) and m > fill_values[c]:
                fill_values[c] = float(m)

    match_df = pd.DataFrame({"match_id": match_ids})
    train_matches, test_matches = match_disjoint_split(match_df, "match_id", TEST_SIZE, RNG_SEED)
    train_ids, test_ids = set(train_matches["match_id"]), set(test_matches["match_id"])
    print(f"  match-disjoint split: {len(train_ids)} train, {len(test_ids)} test matches")

    print("  scoring train matches ...")
    train_frames = [load_scored_match(mid, model, fill_values) for mid in sorted(train_ids)]
    train_df = pd.concat(train_frames, ignore_index=True)
    print("  scoring test matches ...")
    test_frames = [load_scored_match(mid, model, fill_values) for mid in sorted(test_ids)]
    test_df = pd.concat(test_frames, ignore_index=True)
    print(f"  train candidates: {len(train_df)}, test candidates: {len(test_df)}")

    print("  BEFORE (full candidate set, T=1) ...")
    before = policy_metrics(test_df, T=1.0, restricted=False)
    print(f"    {before}")

    print("  restricting candidate set (p_success>=0.05, not offside, distance_u<=45) ...")
    train_restricted = restrict(train_df)
    test_restricted = restrict(test_df)
    per_pass_counts = test_restricted.groupby("event_id").size()
    print(f"    restricted candidates/pass (test): mean={per_pass_counts.mean():.1f}, "
          f"median={per_pass_counts.median():.1f}, p90={per_pass_counts.quantile(0.9):.1f}")

    print("  fitting temperature on training matches' restricted candidates ...")
    T_fitted = fit_temperature(train_restricted)
    print(f"    fitted temperature: {T_fitted:.4f}")

    print("  AFTER (restricted candidate set, calibrated temperature) ...")
    after = policy_metrics(test_restricted, T=T_fitted, restricted=True)
    print(f"    {after}")

    behavioral = after["median_effective_options"] < 100 and after["corr_policy_weighted_vs_unweighted_mean_ev"] < 0.95
    print(f"\n  PRE-SPECIFIED READING: baseline is {'BEHAVIORAL' if behavioral else 'STILL NOT BEHAVIORAL'} "
          f"(median effective options {after['median_effective_options']:.1f}, "
          f"corr {after['corr_policy_weighted_vs_unweighted_mean_ev']:.4f})")

    summary = {
        "n_train_matches": len(train_ids), "n_test_matches": len(test_ids),
        "restricted_candidates_per_pass_test": {
            "mean": float(per_pass_counts.mean()), "median": float(per_pass_counts.median()),
            "p90": float(per_pass_counts.quantile(0.9))},
        "fitted_temperature": T_fitted,
        "before": before, "after": after,
        "pre_specified_reading": {"median_effective_options_lt_100": after["median_effective_options"] < 100,
                                    "correlation_lt_0.95": after["corr_policy_weighted_vs_unweighted_mean_ev"] < 0.95,
                                    "behavioral": behavioral},
        "fill_values": fill_values,
        "train_match_ids": sorted(train_ids), "test_match_ids": sorted(test_ids),
    }
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2, default=str))
    print(f"\nWrote {SUMMARY_PATH}")
    return summary


if __name__ == "__main__":
    main()
