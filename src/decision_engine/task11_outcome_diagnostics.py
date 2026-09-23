"""
Task 11 — Outcome diagnostics (Amendment v2-8). Post-hoc diagnostics for
Task 10 Part B's negative Decision-outcome finding. H-O1/H-O2 (Task 10)
are NOT recomputed here -- only read back for comparison.

Run: python src/decision_engine/task11_outcome_diagnostics.py
"""
import json
import warnings

import numpy as np
import pandas as pd
import statsmodels.api as sm
import xgboost as xgb

from decompose import DATA_DIR, EVENTS_DIR, PV_MODEL_PATH, build_per_pass_table, match_competition_lookup
from task04_situation_context import load_matches_meta
from task10_partB_outcome import add_decision, add_possession_share, add_xg, build_team_match_units, fit_ols

warnings.filterwarnings("ignore")

POLICY_PATH = DATA_DIR / "processed" / "options_policy.parquet"
PASSES_PATH = DATA_DIR / "processed" / "passes_situation.parquet"
TASK10_SUMMARY_PATH = DATA_DIR / "task10_partB_outcome.json"
SUMMARY_PATH = DATA_DIR / "task11_outcome_diagnostics.json"

MIN_POSSESSION_PASSES = 3


def add_zone_pressure_shares(units: pd.DataFrame) -> pd.DataFrame:
    passes = pd.read_parquet(PASSES_PATH, columns=["match_id", "team", "zone", "under_pressure"])
    counts = passes.groupby(["match_id", "team"]).size().rename("n_eligible_passes")
    zone_counts = passes.groupby(["match_id", "team", "zone"]).size().unstack(fill_value=0)
    zone_counts = zone_counts.div(counts, axis=0).reset_index()
    zone_counts = zone_counts.rename(columns={"defensive": "defensive_share", "middle": "middle_share",
                                                "final": "final_share"})
    pressure = passes.groupby(["match_id", "team"])["under_pressure"].mean().rename("pressure_share").reset_index()
    out = units.merge(zone_counts, on=["match_id", "team"], how="left")
    out = out.merge(pressure, on=["match_id", "team"], how="left")
    return out


def build_comp_season_dummies(units: pd.DataFrame) -> tuple:
    units = units.copy()
    units["comp_season"] = units["competition_id"].astype(str) + "_" + units["season_id"].astype(str)
    dummies = pd.get_dummies(units["comp_season"], prefix="cs", drop_first=True).astype(float)
    return pd.concat([units, dummies], axis=1), list(dummies.columns)


def build_team_context_dummies(units: pd.DataFrame) -> tuple:
    units = units.copy()
    units["team_context"] = (units["team"].astype(str) + "|" + units["competition_id"].astype(str)
                              + "|" + units["season_id"].astype(str))
    dummies = pd.get_dummies(units["team_context"], prefix="tc", drop_first=True).astype(float)
    return pd.concat([units, dummies], axis=1), list(dummies.columns)


def build_diagnostics_frame() -> pd.DataFrame:
    units, _ = build_team_match_units()
    units = add_decision(units)
    units = add_possession_share(units)
    units = add_zone_pressure_shares(units)
    units = add_xg(units)
    units["decision_mean"] = units["mean_decision"].mean()
    units["decision_sd"] = units["mean_decision"].std(ddof=1)
    units["decision_z"] = (units["mean_decision"] - units["decision_mean"]) / units["decision_sd"]
    # Dummy columns are built only on rows with a computable Decision (the
    # regression sample), not the full 598. Building them on all 598 first
    # produced all-zero columns for team-contexts whose ONLY appearance was
    # in one of the 15 dropped rows (e.g. Toronto FC, Cincinnati, Charlotte,
    # Borussia Dortmund each have all their rows among the 15) -- an
    # all-zero dummy column made PH-O2's design matrix rank-deficient
    # (verified via SVD: rank 164 of 168 params, condition number 1.8e18).
    has_decision = units["mean_decision"].notna()
    dummied, cs_cols = build_comp_season_dummies(units[has_decision])
    dummied, tc_cols = build_team_context_dummies(dummied)
    keep_cols = ["match_id", "team", "comp_season", "team_context"] + cs_cols + tc_cols
    units = units.merge(dummied[keep_cols], on=["match_id", "team"], how="left")
    return units, cs_cols, tc_cols


def step1_correlations(units: pd.DataFrame) -> pd.DataFrame:
    cols = ["mean_decision", "final_share", "middle_share", "defensive_share",
            "pressure_share", "possession_share", "xg"]
    sub = units.dropna(subset=cols)
    return sub[cols].corr(), len(sub)


def step2_pho1_pho2(units: pd.DataFrame, cs_cols: list, tc_cols: list) -> dict:
    zone_share_cols = ["final_share", "defensive_share", "pressure_share"]
    pho1_predictors = ["decision_z", "possession_share", "is_home"] + cs_cols + zone_share_cols
    pho2_predictors = ["decision_z", "possession_share", "is_home"] + zone_share_cols + tc_cols

    results = {}
    for outcome in ("xg", "goals"):
        for label, predictors, cluster_col in (
            ("PH-O1", pho1_predictors, "team_context"), ("PH-O2", pho2_predictors, "team_context"),
        ):
            res = fit_ols(units, outcome, predictors, cluster_col)
            results[f"{outcome}_{label}"] = res
    return results


def build_possessions() -> pd.DataFrame:
    policy = pd.read_parquet(POLICY_PATH)
    pv_model = xgb.XGBClassifier()
    pv_model.load_model(PV_MODEL_PATH)
    per_pass = build_per_pass_table(policy, pv_model, verbose=True)
    passes_zone = pd.read_parquet(PASSES_PATH, columns=["match_id", "event_id", "zone"])
    per_pass = per_pass.merge(passes_zone, on=["match_id", "event_id"], how="left")
    comp_lookup = match_competition_lookup()

    match_ids = sorted(per_pass["match_id"].unique())
    records = []
    n_team_mismatch = 0
    for i, mid in enumerate(match_ids):
        ev = pd.read_parquet(EVENTS_DIR / f"{mid}.parquet")
        ev = ev.sort_values("index").reset_index(drop=True)
        ev_idx = ev.set_index("id")

        pp = per_pass[per_pass["match_id"] == mid].copy()
        pp["possession"] = pp["event_id"].map(ev_idx["possession"])
        pp["possession_team"] = pp["event_id"].map(ev_idx["possession_team"])
        pp["order_idx"] = pp["event_id"].map(ev_idx["index"])
        n_team_mismatch += int((pp["team"] != pp["possession_team"]).sum())
        # A small share of eligible passes are stray opponent touches that
        # StatsBomb still tags with the same possession id (a loose ball
        # regained and immediately lost, etc.) -- verified by inspection.
        # Excluded here so a possession's stats reflect only its own
        # attributed team's decisions, matching the Shot-side filter below.
        pp = pp[pp["team"] == pp["possession_team"]]

        shots = ev[ev["type"] == "Shot"].copy()
        shots = shots[shots["team"] == shots["possession_team"]]
        shot_agg = shots.groupby("possession").agg(possession_xg=("shot_statsbomb_xg", "sum"))

        comp_id, season_id = comp_lookup.get(mid, (None, None))
        for poss_id, g in pp.groupby("possession"):
            if len(g) < MIN_POSSESSION_PASSES:
                continue
            g_sorted = g.sort_values("order_idx")
            ends_in_shot = poss_id in shot_agg.index
            possession_xg = float(shot_agg.loc[poss_id, "possession_xg"]) if ends_in_shot else 0.0
            records.append({
                "match_id": mid, "possession": poss_id, "team": g_sorted["possession_team"].iloc[0],
                "competition_id": comp_id, "season_id": season_id,
                "starting_zone": g_sorted["zone"].iloc[0], "n_passes": len(g),
                "mean_decision": float(g["decision"].mean()),
                "ends_in_shot": ends_in_shot, "possession_xg": possession_xg,
            })
        if (i + 1) % 50 == 0:
            print(f"  possessions: {i + 1}/{len(match_ids)} matches")

    print(f"Eligible passes whose own team differs from their possession_team: {n_team_mismatch}")
    return pd.DataFrame(records)


def step3_pho3(poss: pd.DataFrame) -> tuple:
    poss = poss.copy()
    poss["decision_z"] = (poss["mean_decision"] - poss["mean_decision"].mean()) / poss["mean_decision"].std(ddof=1)
    poss["team_context"] = (poss["team"].astype(str) + "|" + poss["competition_id"].astype(str)
                             + "|" + poss["season_id"].astype(str))

    # A team-context with zero variance in ends_in_shot makes its own fixed
    # effect non-identifiable and causes the logistic MLE to fail to
    # converge (complete separation) -- same class of problem, same fix, as
    # Task 08's PH-B1 all-zero is_GK dummy (docs/results/08-studies-b-c.md):
    # drop the degenerate group, report exactly which one and how large.
    tc_outcome_var = poss.groupby("team_context")["ends_in_shot"].agg(["mean", "size"])
    degenerate = tc_outcome_var[(tc_outcome_var["mean"] == 0) | (tc_outcome_var["mean"] == 1)]
    n_dropped_possessions = int(degenerate["size"].sum())
    poss = poss[~poss["team_context"].isin(degenerate.index)].copy()

    zone_dummies = pd.get_dummies(poss["starting_zone"], prefix="zone", drop_first=False).astype(float)
    zone_dummies = zone_dummies.drop(columns=["zone_middle"])
    tc_dummies = pd.get_dummies(poss["team_context"], prefix="tc", drop_first=True).astype(float)
    poss = pd.concat([poss, zone_dummies, tc_dummies], axis=1)

    predictors = ["decision_z", "n_passes"] + list(zone_dummies.columns) + list(tc_dummies.columns)
    X = sm.add_constant(poss[predictors].astype(float))
    groups = poss["match_id"]

    y_a = poss["ends_in_shot"].astype(float)
    logit_model = sm.Logit(y_a, X).fit(cov_type="cluster", cov_kwds={"groups": groups}, disp=0)
    # get_margeff() uses the already-fitted model's covariance (cluster-robust,
    # set above) automatically -- it does not take its own cov_type/cov_kwds.
    mfx = logit_model.get_margeff()
    mfx_frame = mfx.summary_frame()

    def mfx_row(name):
        r = mfx_frame.loc[name]
        return {"dydx": float(r["dy/dx"]), "se": float(r["Std. Err."]),
                "ci_low": float(r["Conf. Int. Low"]), "ci_high": float(r["Cont. Int. Hi."]),
                "p_value": float(r["Pr(>|z|)"])}

    logit_result = {"n": int(len(poss)), "pseudo_r2": float(logit_model.prsquared),
                     "decision_z_margfx": mfx_row("decision_z")}

    y_b = poss["possession_xg"]
    ols_model = sm.OLS(y_b, X).fit(cov_type="cluster", cov_kwds={"groups": groups})
    ols_result = {
        "n": int(len(poss)), "r_squared": float(ols_model.rsquared),
        "decision_z_coef": {
            "coef": float(ols_model.params["decision_z"]), "se": float(ols_model.bse["decision_z"]),
            "ci_low": float(ols_model.conf_int().loc["decision_z", 0]),
            "ci_high": float(ols_model.conf_int().loc["decision_z", 1]),
            "p_value": float(ols_model.pvalues["decision_z"]),
        },
    }
    diagnostics = {"n_degenerate_team_contexts_dropped": len(degenerate),
                   "degenerate_team_contexts": degenerate.reset_index().to_dict("records"),
                   "n_possessions_dropped": n_dropped_possessions}
    return {"logit_ends_in_shot": logit_result, "ols_possession_xg": ols_result}, diagnostics


def apply_v2_8_4(pho2_xg: dict, pho3_a: dict) -> dict:
    pho2_positive_excl_zero = (pho2_xg["coefficients"]["decision_z"]["coef"] > 0
                                and pho2_xg["coefficients"]["decision_z"]["ci_low"] > 0)
    pho3a_positive_excl_zero = (pho3_a["decision_z_margfx"]["dydx"] > 0
                                 and pho3_a["decision_z_margfx"]["ci_low"] > 0)
    allowed = pho2_positive_excl_zero and pho3a_positive_excl_zero
    return {"allowed": allowed, "pho2_xg_positive_excl_zero": pho2_positive_excl_zero,
            "pho3a_positive_excl_zero": pho3a_positive_excl_zero}


def main():
    print("Building team-match diagnostics frame ...")
    units, cs_cols, tc_cols = build_diagnostics_frame()
    print(f"Team-match units: {len(units)}, with Decision: {units['mean_decision'].notna().sum()}")

    corr, n_corr = step1_correlations(units)
    print(f"\nStep 1 correlation matrix (n={n_corr}):")
    print(corr.to_string())

    print("\nStep 2: fitting PH-O1/PH-O2 ...")
    step2_results = step2_pho1_pho2(units, cs_cols, tc_cols)
    for k, v in step2_results.items():
        print(f"{k}: n={v['n']}, R2={v['r_squared']:.4f}, decision_z={v['coefficients']['decision_z']}")

    print("\nStep 3: building possessions ...")
    poss = build_possessions()
    print(f"Possessions with >= {MIN_POSSESSION_PASSES} eligible passes: {len(poss)}")
    step3_results, step3_diagnostics = step3_pho3(poss)
    print(json.dumps(step3_results, indent=2))
    print(json.dumps(step3_diagnostics, indent=2))

    print("\nStep 4: applying v2-8.4 ...")
    verdict = apply_v2_8_4(step2_results["xg_PH-O2"], step3_results["logit_ends_in_shot"])
    print(json.dumps(verdict, indent=2))

    task10 = json.loads(TASK10_SUMMARY_PATH.read_text())
    summary = {
        "status": "COMPLETE",
        "step1_correlation_matrix": corr.to_dict(), "step1_n": n_corr,
        "step2_results": step2_results, "task10_ho1_ho2_for_comparison": task10["results"],
        "step3_n_possessions": len(poss), "step3_results": step3_results,
        "step3_diagnostics": step3_diagnostics, "v2_8_4_verdict": verdict,
    }
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2, default=str))
    poss.to_csv(DATA_DIR / "processed" / "task11_possessions.csv", index=False)
    print(f"\nWrote summary to {SUMMARY_PATH}")


if __name__ == "__main__":
    main()
