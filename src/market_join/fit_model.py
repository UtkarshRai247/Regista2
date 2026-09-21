"""
Task 03 — Steps 2-6: fit the primary model, interpret Decision, H3
secondary, full robustness set, and one clearly-labeled exploratory
model. Reports what the models say — no editorializing.

Run: python src/market_join/fit_model.py
"""
import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.stats.outliers_influence import variance_inflation_factor

warnings.filterwarnings("ignore")

DATA_DIR = Path(__file__).parent.parent.parent / "data"

PRIMARY_SAMPLE = DATA_DIR / "processed" / "market_join_analysis_sample_180d.parquet"
ROBUST_A_SAMPLE = DATA_DIR / "processed" / "market_join_analysis_sample.parquet"  # 90-day, original 79
ROBUST_C_SAMPLE = DATA_DIR / "processed" / "market_join_analysis_sample_250p.parquet"

BASE_CONTROLS = [
    "completion_pct", "progressive_passes_per_90", "goals_assists_per_90",
    "minutes_played", "age_at_season_end", "is_tournament", "club_strength_m",
    "days_to_valuation",
]
POSITION_DUMMIES = ["position_group_Midfielder", "position_group_Forward"]  # Defender = reference


def prep(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["log_valuation"] = np.log(df["valuation_eur"])
    df["club_strength_m"] = df["club_strength_eur"] / 1e6
    if "days_to_valuation" not in df.columns and "valuation_gap_days" in df.columns:
        # the original Task 02 (90-day) file predates this column name;
        # same underlying quantity
        df["days_to_valuation"] = df["valuation_gap_days"]
    df["is_tournament"] = df["is_tournament"].astype(int)
    dummies = pd.get_dummies(df["position_group"], prefix="position_group").astype(int)
    for col in POSITION_DUMMIES:
        if col not in dummies.columns:
            dummies[col] = 0
    df = pd.concat([df, dummies[POSITION_DUMMIES]], axis=1)
    return df


def fit_ols(df: pd.DataFrame, predictors: list, outcome: str = "log_valuation",
            cluster_col: str = "player_id"):
    cols = predictors + [outcome, cluster_col]
    sub = df.dropna(subset=cols).copy()
    X = sm.add_constant(sub[predictors].astype(float))
    y = sub[outcome].astype(float)
    model = sm.OLS(y, X).fit(cov_type="cluster", cov_kwds={"groups": sub[cluster_col]})
    return model, sub


def coef_table(model) -> list:
    ci = model.conf_int()
    rows = []
    for name in model.params.index:
        rows.append({
            "term": name, "coef": float(model.params[name]),
            "clustered_se": float(model.bse[name]),
            "t": float(model.tvalues[name]), "p": float(model.pvalues[name]),
            "ci_low": float(ci.loc[name, 0]), "ci_high": float(ci.loc[name, 1]),
        })
    return rows


def vif_table(sub: pd.DataFrame, predictors: list) -> list:
    X = sm.add_constant(sub[predictors].astype(float))
    out = []
    for i, name in enumerate(X.columns):
        if name == "const":
            continue
        out.append({"term": name, "vif": float(variance_inflation_factor(X.values, i))})
    return out


def decision_interpretation(model, sub: pd.DataFrame) -> dict:
    sd = sub["decision_per_100"].std()
    beta = model.params["decision_per_100"]
    ci = model.conf_int().loc["decision_per_100"]

    def pct(b):
        return (np.exp(b * sd) - 1) * 100

    pct_point = pct(beta)
    pct_lo, pct_hi = sorted([pct(ci[0]), pct(ci[1])])
    includes_zero = ci[0] <= 0 <= ci[1]
    near_zero_bound = pct_lo if abs(pct_lo) < abs(pct_hi) else pct_hi
    return {
        "decision_sd": float(sd), "pct_change_point": float(pct_point),
        "pct_change_ci": [float(pct_lo), float(pct_hi)],
        "ci_includes_zero": bool(includes_zero),
        "smallest_ruled_out_effect_pct": float(near_zero_bound),
        "null_type": ("imprecise (CI is wide relative to plausible effect sizes)"
                       if includes_zero and (pct_hi - pct_lo) > 10
                       else "precise (CI is tight around zero)" if includes_zero
                       else "not a null - CI excludes zero"),
    }


def run_and_report(label: str, df: pd.DataFrame, predictors: list, results: dict):
    model, sub = fit_ols(df, predictors)
    results[label] = {
        "n": int(model.nobs), "r_squared": float(model.rsquared),
        "n_clusters": int(sub["player_id"].nunique()),
        "coefficients": coef_table(model),
    }
    return model, sub


def main():
    results = {}

    # ---------- Step 1 recap ----------
    primary_df = prep(pd.read_parquet(PRIMARY_SAMPLE))
    predictors = ["decision_per_100"] + BASE_CONTROLS + POSITION_DUMMIES

    # ---------- Step 2/3: primary model ----------
    model, sub = run_and_report("primary", primary_df, predictors, results)
    results["primary"]["vif"] = vif_table(sub, predictors)
    results["primary"]["decision_interpretation"] = decision_interpretation(model, sub)

    # ---------- Step 4: H3 secondary ----------
    h3_df = primary_df.dropna(subset=["valuation_12mo_eur"]).copy()
    h3_df["log_valuation_12mo"] = np.log(h3_df["valuation_12mo_eur"])
    h3_df["log_change"] = h3_df["log_valuation_12mo"] - h3_df["log_valuation"]
    h3_predictors = predictors + ["log_valuation"]  # starting value as control
    h3_model, h3_sub = fit_ols(h3_df, h3_predictors, outcome="log_change")
    results["h3_secondary"] = {
        "n": int(h3_model.nobs), "r_squared": float(h3_model.rsquared),
        "n_clusters": int(h3_sub["player_id"].nunique()),
        "coefficients": coef_table(h3_model),
        "underpowered": bool(h3_model.nobs < 60),
    }

    # ---------- Step 5: robustness set ----------
    robustness = {}

    # (a) 90-day window, original 79 units
    a_df = prep(pd.read_parquet(ROBUST_A_SAMPLE))
    run_and_report("a_90day_original79", a_df, predictors, robustness)

    # (b) league units only
    b_df = primary_df[primary_df["is_tournament"] == 0].copy()
    b_predictors = [p for p in predictors if p != "is_tournament"]
    run_and_report("b_league_only", b_df, b_predictors, robustness)

    # (c) min 250 passes, 180-day window
    if ROBUST_C_SAMPLE.exists():
        c_df = prep(pd.read_parquet(ROBUST_C_SAMPLE))
        run_and_report("c_min250passes", c_df, predictors, robustness)
    else:
        robustness["c_min250passes"] = {"error": "sample file not built"}

    # (d) midfielders only
    d_df = primary_df[primary_df["position_group"] == "Midfielder"].copy()
    d_predictors = [p for p in predictors if p not in POSITION_DUMMIES]
    run_and_report("d_midfielders_only", d_df, d_predictors, robustness)

    # (e) without club strength
    e_predictors = [p for p in predictors if p != "club_strength_m"]
    run_and_report("e_without_club_strength", primary_df, e_predictors, robustness)

    # (f) attenuation-corrected Decision coefficient
    rel_point, rel_lo, rel_hi = 0.744, 0.691, 0.792
    beta = model.params["decision_per_100"]
    ci = model.conf_int().loc["decision_per_100"]
    corrected_beta = beta / rel_point
    corrected_ci = [ci[0] / rel_hi, ci[1] / rel_lo]  # conservative: least/most inflation
    robustness["f_attenuation_corrected"] = {
        "method": "corrected_beta = beta_hat / reliability_point_estimate; "
                  "corrected CI = [ci_low / reliability_p95, ci_high / reliability_p5] "
                  "(conservative combination of coefficient uncertainty and reliability uncertainty)",
        "reliability_used": {"point": rel_point, "p5": rel_lo, "p95": rel_hi},
        "raw_beta": float(beta), "raw_ci": [float(ci[0]), float(ci[1])],
        "corrected_beta": float(corrected_beta),
        "corrected_ci": [float(corrected_ci[0]), float(corrected_ci[1])],
    }

    results["robustness"] = robustness

    # ---------- Step 6: exploratory (Execution added) ----------
    exp_predictors = predictors + ["execution_per_100"]
    exp_model, exp_sub = fit_ols(primary_df, exp_predictors)
    results["exploratory_with_execution"] = {
        "warning": "EXPLORATORY - Execution reliability is 0.482 [0.300, 0.603], "
                   "NOT TRUSTWORTHY. Not part of the primary or robustness results.",
        "n": int(exp_model.nobs), "r_squared": float(exp_model.rsquared),
        "coefficients": coef_table(exp_model),
    }

    print(json.dumps(results, indent=2, default=str))
    (DATA_DIR / "primary_model_results.json").write_text(json.dumps(results, indent=2, default=str))


if __name__ == "__main__":
    main()
