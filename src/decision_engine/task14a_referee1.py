"""
Task 14a — Referee 1: do the objectives predict real outcomes?

Governing document: docs/specs/analysis-plan-v3.md, Amendments v3-1 to
v3-4; plan v3 section 3. Re-runs the IDENTICAL preregistered outcome
battery (v2-6.3 H-O1, v2-9.2 PH-O4, v2-8.3 possession-level PH-O3) for
O1, O2 and O3, and applies the plan's fixed win rule. No leaderboards,
no player names, no expert lists, no Referee 2.

Run: python src/decision_engine/task14a_referee1.py
"""
import json
import warnings

import numpy as np
import pandas as pd
import statsmodels.api as sm
import xgboost as xgb

from decompose import DATA_DIR, EVENTS_DIR, PV_MODEL_PATH, build_per_pass_table, match_competition_lookup
from task10_partB_outcome import (
    PASSES_PATH, add_possession_share, add_xg, build_team_match_units, fit_ols,
)
from task11_outcome_diagnostics import build_comp_season_dummies
from task13_objectives import O1_MODEL_PATH, O2_OPTIONS_PATH, O3_OPTIONS_PATH, POLICY_PATH
from task13c_wp_diagnostic import build_match_score_table, build_team_bin_lookup, compute_strength_proxy

warnings.filterwarnings("ignore")

SUMMARY_PATH = DATA_DIR / "task14a_referee1.json"
MIN_POSSESSION_PASSES = 3
OBJECTIVES = ["O1", "O2", "O3"]


# ---------------------------------------------------------------------------
# Step 1: per-pass Decision for each objective (Decision only -- no
# Execution/realized-value needed for Referee 1)
# ---------------------------------------------------------------------------

def compute_decision_only(df: pd.DataFrame) -> pd.DataFrame:
    """First half of decompose.build_per_pass_table (Decision =
    EV(chosen) - policy-weighted EV) without the realized-value /
    Execution half, which Referee 1 doesn't need."""
    df = df.copy()
    df["ev_x_prob"] = df["ev"] * df["policy_probability"]
    per_pass = df.groupby("event_id").agg(
        match_id=("match_id", "first"), team=("team", "first"), player_id=("player_id", "first"),
        ev_chosen=("ev", lambda s: s[df.loc[s.index, "chosen"]].iloc[0]),
        policy_weighted_ev=("ev_x_prob", "sum"),
    ).reset_index()
    per_pass["decision"] = per_pass["ev_chosen"] - per_pass["policy_weighted_ev"]
    return per_pass


def build_per_pass_o1(policy: pd.DataFrame) -> pd.DataFrame:
    o1_model = xgb.XGBClassifier()
    o1_model.load_model(O1_MODEL_PATH)
    return build_per_pass_table(policy, o1_model, verbose=True)


def build_per_pass_o2(policy: pd.DataFrame) -> pd.DataFrame:
    o2_options = pd.read_parquet(O2_OPTIONS_PATH)
    assert len(o2_options) == len(policy), "options_o2.parquet is no longer positionally aligned with options_policy.parquet"
    df = policy.copy()
    df["ev"] = o2_options["ev"].values
    return compute_decision_only(df)


def build_per_pass_o3(policy: pd.DataFrame, match_ids: list) -> tuple:
    """options_o3.parquet only covers the 99.6% of options whose team had
    a resolvable strength bin (Task 13c). Reconstruct the same keep_mask
    deterministically (proxy + team-bin lookup, no WP/model work needed)
    so options_o3.parquet's rows can be attached positionally."""
    match_table = build_match_score_table()
    proxy = compute_strength_proxy(match_table)
    bin_lookup = build_team_bin_lookup(match_ids, proxy)
    tagged = policy.merge(bin_lookup, on=["match_id", "team"], how="left")
    assert len(tagged) == len(policy), "team-bin lookup produced a fan-out"
    keep_mask = tagged["strength_bin"].notna().values

    o3_options = pd.read_parquet(O3_OPTIONS_PATH)
    n_keep = int(keep_mask.sum())
    assert len(o3_options) == n_keep, (
        f"reconstructed keep_mask ({n_keep}) doesn't match options_o3.parquet ({len(o3_options)})"
    )
    df = policy[keep_mask].copy()
    df["ev"] = o3_options["ev"].values
    per_pass = compute_decision_only(df)
    return per_pass, keep_mask, tagged


def step1_decisions() -> dict:
    print("Step 1: building per-pass Decision for O1, O2, O3 ...")
    policy = pd.read_parquet(POLICY_PATH)
    match_ids = sorted(int(p.stem) for p in EVENTS_DIR.glob("*.parquet"))

    per_pass_o1 = build_per_pass_o1(policy)
    per_pass_o2 = build_per_pass_o2(policy)
    per_pass_o3, keep_mask, tagged = build_per_pass_o3(policy, match_ids)

    n_options_missing_o3 = int((~keep_mask).sum())
    teams_missing = sorted(tagged.loc[~keep_mask, "team"].unique().tolist())
    print(f"  per-pass rows: O1={len(per_pass_o1)}, O2={len(per_pass_o2)}, O3={len(per_pass_o3)}")
    print(f"  options without a resolvable O3 team-strength bin: {n_options_missing_o3}/{len(policy)}")
    print(f"  teams missing a strength proxy (options dropped): {teams_missing}")

    return {
        "per_pass": {"O1": per_pass_o1, "O2": per_pass_o2, "O3": per_pass_o3},
        "n_options_missing_o3": n_options_missing_o3, "teams_missing_o3": teams_missing,
    }


def build_team_match_frame(per_pass: dict) -> tuple:
    units, _ = build_team_match_units()
    units = add_possession_share(units)
    units = add_xg(units)
    units, cs_cols = build_comp_season_dummies(units)
    units["team_context"] = (units["team"].astype(str) + "|" + units["competition_id"].astype(str)
                              + "|" + units["season_id"].astype(str))

    n_units = {}
    for obj in OBJECTIVES:
        dec = per_pass[obj].groupby(["match_id", "team"])["decision"].mean().reset_index().rename(
            columns={"decision": f"mean_decision_{obj}"})
        units = units.merge(dec, on=["match_id", "team"], how="left")
        mean_, sd_ = units[f"mean_decision_{obj}"].mean(), units[f"mean_decision_{obj}"].std(ddof=1)
        units[f"decision_z_{obj}"] = (units[f"mean_decision_{obj}"] - mean_) / sd_
        n_units[obj] = int(units[f"mean_decision_{obj}"].notna().sum())
    print(f"  team-match units with valid Decision: {n_units} (of {len(units)} total)")
    return units, cs_cols, n_units


def build_possessions_multi(per_pass: dict) -> pd.DataFrame:
    """Parametrized copy of task11_outcome_diagnostics.build_possessions,
    extended to carry decision_o1/o2/o3 through the SAME possession
    membership in one pass (so all three objectives are evaluated over
    identical possessions)."""
    base = per_pass["O1"][["match_id", "event_id", "team", "decision"]].rename(columns={"decision": "decision_O1"})
    for obj in ("O2", "O3"):
        base = base.merge(
            per_pass[obj][["event_id", "decision"]].rename(columns={"decision": f"decision_{obj}"}),
            on="event_id", how="left",
        )
    passes_zone = pd.read_parquet(PASSES_PATH, columns=["match_id", "event_id", "zone"])
    base = base.merge(passes_zone, on=["match_id", "event_id"], how="left")
    comp_lookup = match_competition_lookup()

    match_ids = sorted(base["match_id"].unique())
    records = []
    for i, mid in enumerate(match_ids):
        ev = pd.read_parquet(EVENTS_DIR / f"{mid}.parquet")
        ev = ev.sort_values("index").reset_index(drop=True)
        ev_idx = ev.set_index("id")

        pp = base[base["match_id"] == mid].copy()
        pp["possession"] = pp["event_id"].map(ev_idx["possession"])
        pp["possession_team"] = pp["event_id"].map(ev_idx["possession_team"])
        pp["order_idx"] = pp["event_id"].map(ev_idx["index"])
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
            rec = {
                "match_id": mid, "possession": poss_id, "team": g_sorted["possession_team"].iloc[0],
                "competition_id": comp_id, "season_id": season_id,
                "starting_zone": g_sorted["zone"].iloc[0], "n_passes": len(g),
                "ends_in_shot": ends_in_shot, "possession_xg": possession_xg,
            }
            for obj in OBJECTIVES:
                col = f"decision_{obj}"
                rec[f"mean_decision_{obj}"] = float(g[col].mean()) if g[col].notna().any() else None
            records.append(rec)
        if (i + 1) % 50 == 0:
            print(f"  possessions: {i + 1}/{len(match_ids)} matches")
    return pd.DataFrame(records)


# ---------------------------------------------------------------------------
# Step 2: identical battery per objective
# ---------------------------------------------------------------------------

def fit_team_match_battery(units: pd.DataFrame, cs_cols: list, obj: str) -> dict:
    decision_col = f"decision_z_{obj}"
    with_share = [decision_col, "possession_share", "is_home"] + cs_cols
    without_share = [decision_col, "is_home"] + cs_cols
    results = {}
    for outcome in ("xg", "goals"):
        for label, predictors in (("H-O1_form", with_share), ("PH-O4_form", without_share)):
            res = fit_ols(units, outcome, predictors, "team_context")
            res["decision_coef"] = res["coefficients"].pop(decision_col)
            results[f"{outcome}_{label}"] = res
    return results


def fit_pho3_battery(poss: pd.DataFrame, obj: str) -> dict:
    """Parametrized copy of task11_outcome_diagnostics.step3_pho3,
    parameterized on which objective's possession-level decision to use."""
    decision_col = f"mean_decision_{obj}"
    sub = poss.dropna(subset=[decision_col]).copy()
    sub["decision_z"] = (sub[decision_col] - sub[decision_col].mean()) / sub[decision_col].std(ddof=1)
    sub["team_context"] = (sub["team"].astype(str) + "|" + sub["competition_id"].astype(str)
                            + "|" + sub["season_id"].astype(str))

    tc_outcome_var = sub.groupby("team_context")["ends_in_shot"].agg(["mean", "size"])
    degenerate = tc_outcome_var[(tc_outcome_var["mean"] == 0) | (tc_outcome_var["mean"] == 1)]
    n_dropped_possessions = int(degenerate["size"].sum())
    sub = sub[~sub["team_context"].isin(degenerate.index)].copy()

    zone_dummies = pd.get_dummies(sub["starting_zone"], prefix="zone", drop_first=False).astype(float)
    zone_dummies = zone_dummies.drop(columns=["zone_middle"])
    tc_dummies = pd.get_dummies(sub["team_context"], prefix="tc", drop_first=True).astype(float)
    sub = pd.concat([sub, zone_dummies, tc_dummies], axis=1)

    predictors = ["decision_z", "n_passes"] + list(zone_dummies.columns) + list(tc_dummies.columns)
    X = sm.add_constant(sub[predictors].astype(float))
    groups = sub["match_id"]

    y_a = sub["ends_in_shot"].astype(float)
    logit_model = sm.Logit(y_a, X).fit(cov_type="cluster", cov_kwds={"groups": groups}, disp=0)
    mfx = logit_model.get_margeff()
    mfx_frame = mfx.summary_frame()
    r = mfx_frame.loc["decision_z"]
    logit_result = {
        "n": int(len(sub)), "pseudo_r2": float(logit_model.prsquared),
        "decision_z_margfx": {"dydx": float(r["dy/dx"]), "se": float(r["Std. Err."]),
                               "ci_low": float(r["Conf. Int. Low"]), "ci_high": float(r["Cont. Int. Hi."]),
                               "p_value": float(r["Pr(>|z|)"])},
    }

    y_b = sub["possession_xg"]
    ols_model = sm.OLS(y_b, X).fit(cov_type="cluster", cov_kwds={"groups": groups})
    ols_result = {
        "n": int(len(sub)), "r_squared": float(ols_model.rsquared),
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
    return {"logit_ends_in_shot": logit_result, "ols_possession_xg": ols_result, "diagnostics": diagnostics}


# ---------------------------------------------------------------------------
# Step 3: comparison rule
# ---------------------------------------------------------------------------

def apply_comparison_rule(team_match_results: dict, pho3_results: dict, obj: str) -> dict:
    xg_pho4 = team_match_results[obj]["xg_PH-O4_form"]["decision_coef"]
    xg_poss = pho3_results[obj]["ols_possession_xg"]["decision_z_coef"]
    team_match_win = xg_pho4["coef"] > 0 and xg_pho4["ci_low"] > 0
    possession_win = xg_poss["coef"] > 0 and xg_poss["ci_low"] > 0
    wins = team_match_win and possession_win
    return {"team_match_pho4_xg_positive_excl_zero": team_match_win,
            "possession_xg_positive_excl_zero": possession_win, "wins": wins}


def main():
    print("Step 0 (already committed): Amendment v3-4")

    step1 = step1_decisions()
    per_pass = step1["per_pass"]

    print("\nStep 1: team-match units ...")
    units, cs_cols, n_units = build_team_match_frame(per_pass)

    print("\nStep 1: possessions (built once, all three objectives together) ...")
    poss = build_possessions_multi(per_pass)
    n_poss = {obj: int(poss[f"mean_decision_{obj}"].notna().sum()) for obj in OBJECTIVES}
    print(f"  possessions (n_passes>={MIN_POSSESSION_PASSES}): {len(poss)} total; "
          f"with valid Decision: {n_poss}")

    print("\nStep 2: fitting the identical battery per objective ...")
    team_match_results, pho3_results = {}, {}
    for obj in OBJECTIVES:
        print(f"\n=== {obj} ===")
        team_match_results[obj] = fit_team_match_battery(units, cs_cols, obj)
        for k, v in team_match_results[obj].items():
            print(f"  {k}: n={v['n']}, R2={v['r_squared']:.4f}, decision={v['decision_coef']}")
        pho3_results[obj] = fit_pho3_battery(poss, obj)
        print(f"  possession logit: n={pho3_results[obj]['logit_ends_in_shot']['n']}, "
              f"decision_margfx={pho3_results[obj]['logit_ends_in_shot']['decision_z_margfx']}")
        print(f"  possession OLS: n={pho3_results[obj]['ols_possession_xg']['n']}, "
              f"decision_coef={pho3_results[obj]['ols_possession_xg']['decision_z_coef']}")
        print(f"  possession diagnostics: {pho3_results[obj]['diagnostics']}")

    print("\nStep 3: applying the fixed comparison rule ...")
    verdicts = {}
    for obj in OBJECTIVES:
        verdicts[obj] = apply_comparison_rule(team_match_results, pho3_results, obj)
        print(f"  {obj}: {'WIN' if verdicts[obj]['wins'] else 'NOT WIN'} -- {verdicts[obj]}")

    summary = {
        "status": "COMPLETE",
        "n_options_missing_o3": step1["n_options_missing_o3"], "teams_missing_o3": step1["teams_missing_o3"],
        "n_team_match_units": n_units, "n_possessions_total": len(poss), "n_possessions_valid": n_poss,
        "team_match_results": team_match_results, "possession_results": pho3_results, "verdicts": verdicts,
    }
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2, default=str))
    print(f"\nWrote summary to {SUMMARY_PATH}")


if __name__ == "__main__":
    main()
