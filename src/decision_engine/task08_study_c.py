"""
Task 08 — PART 2: Study C (plan section 5). Choice or execution?

Units: 138 player x competition-season units with >= 200 eligible passes.
For each of 100 random split-halves: cross-half covariances give the
noise-corrected ("true") variance of Decision, of Execution, and their
covariance (plan 5.2). Bootstrap resamples UNITS (ordinary bootstrap --
no crossed-random-effects identity issue here, unlike Study B).

Run: python src/decision_engine/task08_study_c.py
"""
import json
import warnings

import numpy as np
import pandas as pd
import xgboost as xgb

from decompose import DATA_DIR, PV_MODEL_PATH, build_per_pass_table, match_competition_lookup

warnings.filterwarnings("ignore")

POLICY_PATH = DATA_DIR / "processed" / "options_policy.parquet"
METRICS_PATH = DATA_DIR / "processed" / "player_season_metrics.parquet"
SUMMARY_PATH = DATA_DIR / "task08_study_c.json"

SEED = 20260920
MIN_PASSES = 200
N_SPLITS = 100
N_BOOTSTRAP = 1000
N_SPLITS_PER_BOOT = 20


def load_units_138():
    policy = pd.read_parquet(POLICY_PATH)
    pv_model = xgb.XGBClassifier()
    pv_model.load_model(PV_MODEL_PATH)
    print("Running decompose.build_per_pass_table (Decision + Execution, all 299 matches) ...")
    per_pass = build_per_pass_table(policy, pv_model, verbose=True)
    comp_lookup = match_competition_lookup()
    per_pass["competition_id"] = per_pass["match_id"].map(lambda m: comp_lookup.get(m, (None, None))[0])
    per_pass["season_id"] = per_pass["match_id"].map(lambda m: comp_lookup.get(m, (None, None))[1])

    metrics = pd.read_parquet(METRICS_PATH)
    qualifying = metrics[metrics["n_eligible_passes"] >= MIN_PASSES][["player_id", "competition_id", "season_id"]]
    print(f"Units with >= {MIN_PASSES} eligible passes: {len(qualifying)}")
    assert len(qualifying) == 138, f"expected 138 units, found {len(qualifying)}"

    merged = per_pass.merge(qualifying, on=["player_id", "competition_id", "season_id"])
    return merged, qualifying


def one_split(grouped: dict, keys: list, rng: np.random.Generator) -> dict:
    h1_dec, h2_dec, h1_exe, h2_exe = [], [], [], []
    for key in keys:
        dec, exe = grouped[key]
        n = len(dec)
        perm = rng.permutation(n)
        half = n // 2
        idx1, idx2 = perm[:half], perm[half:]
        h1_dec.append(dec[idx1].mean()); h2_dec.append(dec[idx2].mean())
        h1_exe.append(exe[idx1].mean()); h2_exe.append(exe[idx2].mean())
    h1_dec, h2_dec, h1_exe, h2_exe = (np.array(a) for a in (h1_dec, h2_dec, h1_exe, h2_exe))
    true_var_dec = float(np.cov(h1_dec, h2_dec)[0, 1])
    true_var_exe = float(np.cov(h1_exe, h2_exe)[0, 1])
    true_cov = float(0.5 * (np.cov(h1_dec, h2_exe)[0, 1] + np.cov(h2_dec, h1_exe)[0, 1]))
    choice_share = true_var_dec / (true_var_dec + true_var_exe) if (true_var_dec + true_var_exe) != 0 else np.nan
    return {"true_var_dec": true_var_dec, "true_var_exe": true_var_exe,
            "true_cov": true_cov, "choice_share": choice_share}


def main():
    merged, qualifying = load_units_138()
    grouped = {}
    for (pid, cid, sid), g in merged.groupby(["player_id", "competition_id", "season_id"]):
        grouped[(pid, cid, sid)] = (g["decision"].values, g["execution"].values)
    keys = list(grouped.keys())
    assert len(keys) == 138

    print(f"Running {N_SPLITS} primary splits (seed {SEED}) ...")
    rng = np.random.default_rng(SEED)
    splits = [one_split(grouped, keys, rng) for _ in range(N_SPLITS)]
    choice_shares = np.array([s["choice_share"] for s in splits])
    true_var_exe_arr = np.array([s["true_var_exe"] for s in splits])
    true_var_dec_arr = np.array([s["true_var_dec"] for s in splits])
    true_cov_arr = np.array([s["true_cov"] for s in splits])

    primary = {
        "choice_share_median": float(np.median(choice_shares)),
        "choice_share_p5": float(np.percentile(choice_shares, 5)),
        "choice_share_p95": float(np.percentile(choice_shares, 95)),
        "true_var_dec_median": float(np.median(true_var_dec_arr)),
        "true_var_exe_median": float(np.median(true_var_exe_arr)),
        "true_var_exe_p5": float(np.percentile(true_var_exe_arr, 5)),
        "true_var_exe_p95": float(np.percentile(true_var_exe_arr, 95)),
        "true_cov_median": float(np.median(true_cov_arr)),
    }
    print(json.dumps(primary, indent=2))

    # Raw (uncorrected) share: no split-half correction, straight sample
    # variance of each unit's own overall mean Decision/Execution.
    unit_means = merged.groupby(["player_id", "competition_id", "season_id"]).agg(
        mean_decision=("decision", "mean"), mean_execution=("execution", "mean"),
    )
    raw_var_dec = float(unit_means["mean_decision"].var(ddof=1))
    raw_var_exe = float(unit_means["mean_execution"].var(ddof=1))
    raw_share = raw_var_dec / (raw_var_dec + raw_var_exe)
    print(f"Raw (uncorrected) share: {raw_share} (raw_var_dec={raw_var_dec}, raw_var_exe={raw_var_exe})")

    print(f"Bootstrapping (1,000 draws resampling units, {N_SPLITS_PER_BOOT} splits/draw) ...")
    boot_rng = np.random.default_rng(SEED + 1)
    keys_arr = np.array(keys, dtype=object)
    n_units = len(keys_arr)
    boot_medians = np.empty(N_BOOTSTRAP)
    for b in range(N_BOOTSTRAP):
        drawn_idx = boot_rng.integers(0, n_units, size=n_units)
        drawn_keys = [tuple(keys_arr[i]) for i in drawn_idx]
        draw_shares = [one_split(grouped, drawn_keys, boot_rng)["choice_share"] for _ in range(N_SPLITS_PER_BOOT)]
        boot_medians[b] = np.median(draw_shares)
    boot_ci = (float(np.nanpercentile(boot_medians, 2.5)), float(np.nanpercentile(boot_medians, 97.5)))
    print(f"Bootstrap 95% CI for choice share: {boot_ci}")

    failure_triggered = (primary["true_var_exe_median"] < 0) or (
        primary["true_var_exe_p5"] < 0 and primary["true_var_exe_p95"] > 0)
    print(f"Plan 5.3 failure condition triggered: {failure_triggered}")

    summary = {
        "status": "COMPLETE", "n_units": 138, "n_splits": N_SPLITS,
        "primary": primary, "raw_uncorrected_share": raw_share,
        "raw_var_dec": raw_var_dec, "raw_var_exe": raw_var_exe,
        "bootstrap_ci": boot_ci, "n_bootstrap": N_BOOTSTRAP, "n_splits_per_bootstrap": N_SPLITS_PER_BOOT,
        "failure_condition_triggered": bool(failure_triggered),
    }
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2, default=str))
    print(f"\nWrote summary to {SUMMARY_PATH}")


if __name__ == "__main__":
    main()
