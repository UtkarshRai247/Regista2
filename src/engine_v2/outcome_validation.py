"""
Task 17, Step 5 (ONLY runs because Step 4's T6 passed): outcome
validation, specifications UNCHANGED from analysis-plan-v2.md sections
v2-6.3 (H-O1/H-O2), v2-8.3 (PH-O1/PH-O2/PH-O3), v2-9.2 (PH-O4), applied
to engine v2's Decision instead of v1's. This is the test engine v1
failed (docs/results/10-validation.md, 11-outcome-diagnostics.md,
12-artifacts.md) -- reported here exactly as it comes out, beside v1's
published figures.

Inputs specific to engine v2, disclosed (not a specification change):
possession_share / zone shares / pressure_share use engine v2's OWN
eligible-pass population (options_ev's `chosen` rows, 250,850 total),
not v1's passes_situation.parquet (part of the withdrawn engine).
completion_rate/progressive_rate/xa_per_pass are computed the same way
v1 did -- per_pass_reference_flags over ALL of a team's passes, inner-
joined down to the eligible population -- ported unchanged in
validation_common.py.

Run: python src/engine_v2/outcome_validation.py
"""
import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm

from geometry import team_period_directions, normalize_xy
from validation_common import fit_ols, load_matches_meta, per_pass_reference_flags, zone_of

warnings.filterwarnings("ignore")

DATA_DIR = Path(__file__).parent.parent.parent / "data"
EVENTS_DIR = DATA_DIR / "raw" / "events"
EV_DIR = DATA_DIR / "processed" / "engine_v2" / "options_ev"
PASS_DER_PATH = DATA_DIR / "processed" / "engine_v2" / "pass_der.parquet"
SUMMARY_PATH = DATA_DIR / "engine_v2_step5_outcome_validation.json"

MIN_POSSESSION_PASSES = 3


def build_team_match_units() -> tuple:
    matches_meta = load_matches_meta()
    rows = []
    for mid, m in matches_meta.items():
        rows.append({"match_id": mid, "team": m["home_team"], "is_home": 1, "goals": m["home_score"],
                     "competition_id": m["competition_id"], "season_id": m["season_id"]})
        rows.append({"match_id": mid, "team": m["away_team"], "is_home": 0, "goals": m["away_score"],
                     "competition_id": m["competition_id"], "season_id": m["season_id"]})
    return pd.DataFrame(rows), matches_meta


def add_decision(units: pd.DataFrame) -> pd.DataFrame:
    pass_der = pd.read_parquet(PASS_DER_PATH, columns=["match_id", "team", "decision"])
    dec = pass_der.groupby(["match_id", "team"])["decision"].mean().reset_index().rename(columns={"decision": "mean_decision"})
    return units.merge(dec, on=["match_id", "team"], how="left")


def add_possession_share(units: pd.DataFrame, match_ids: list) -> pd.DataFrame:
    rows = []
    for mid in match_ids:
        df = pd.read_parquet(EV_DIR / f"{mid}.parquet", columns=["team", "chosen"])
        chosen = df[df["chosen"]]
        for team, n in chosen.groupby("team").size().items():
            rows.append({"match_id": mid, "team": team, "n_eligible_passes": int(n)})
    counts_df = pd.DataFrame(rows)
    out = units.merge(counts_df, on=["match_id", "team"], how="left")
    out["n_eligible_passes"] = out["n_eligible_passes"].fillna(0)
    total_per_match = out.groupby("match_id")["n_eligible_passes"].transform("sum")
    out["possession_share"] = out["n_eligible_passes"] / total_per_match
    return out


def add_zone_pressure_shares(units: pd.DataFrame, match_ids: list) -> pd.DataFrame:
    rows = []
    for mid in match_ids:
        df = pd.read_parquet(EV_DIR / f"{mid}.parquet",
                              columns=["team", "chosen", "passer_x", "passer_y", "period", "under_pressure"])
        chosen = df[df["chosen"]].copy()
        ev = pd.read_parquet(EVENTS_DIR / f"{mid}.parquet", columns=["team", "period", "type", "location"])
        directions = team_period_directions(ev)
        chosen["direction"] = [directions.get((t, p), 1) for t, p in zip(chosen["team"], chosen["period"])]
        nx = [normalize_xy(x, y, d)[0] for x, y, d in zip(chosen["passer_x"], chosen["passer_y"], chosen["direction"])]
        chosen["zone"] = [zone_of(v) for v in nx]
        counts = chosen.groupby("team").size()
        zone_counts = chosen.groupby(["team", "zone"]).size().unstack(fill_value=0)
        pressure = chosen.groupby("team")["under_pressure"].mean()
        for team in counts.index:
            row = {"match_id": mid, "team": team}
            for z in ("defensive", "middle", "final"):
                row[f"{z}_share"] = float(zone_counts.loc[team, z]) / counts[team] if z in zone_counts.columns else 0.0
            row["pressure_share"] = float(pressure.loc[team])
            rows.append(row)
    return units.merge(pd.DataFrame(rows), on=["match_id", "team"], how="left")


def add_reference_rates(units: pd.DataFrame, match_ids: list) -> pd.DataFrame:
    frames = []
    for i, mid in enumerate(match_ids):
        flags = per_pass_reference_flags(mid)
        elig = pd.read_parquet(EV_DIR / f"{mid}.parquet", columns=["match_id", "event_id", "chosen"])
        elig = elig[elig["chosen"]][["match_id", "event_id"]]
        flags = flags.merge(elig, on=["match_id", "event_id"], how="inner")
        frames.append(flags)
        if (i + 1) % 50 == 0:
            print(f"    reference rates: {i + 1}/{len(match_ids)} matches")
    flags_df = pd.concat(frames, ignore_index=True)
    agg = flags_df.groupby(["match_id", "team"]).agg(
        completion_rate=("complete", "mean"), progressive_rate=("progressive", "mean"),
        xa_per_pass=("xa", "mean")).reset_index()
    return units.merge(agg, on=["match_id", "team"], how="left")


def add_xg(units: pd.DataFrame) -> pd.DataFrame:
    match_ids = sorted(int(p.stem) for p in EVENTS_DIR.glob("*.parquet"))
    rows = []
    for mid in match_ids:
        ev = pd.read_parquet(EVENTS_DIR / f"{mid}.parquet", columns=["type", "team", "shot_statsbomb_xg"])
        shots = ev[ev["type"] == "Shot"]
        for team, xg in shots.groupby("team")["shot_statsbomb_xg"].sum().items():
            rows.append({"match_id": mid, "team": team, "xg": float(xg)})
    xg_df = pd.DataFrame(rows)
    out = units.merge(xg_df, on=["match_id", "team"], how="left")
    out["xg"] = out["xg"].fillna(0.0)
    return out


def build_comp_season_dummies(units: pd.DataFrame) -> tuple:
    units = units.copy()
    units["comp_season"] = units["competition_id"].astype(str) + "_" + units["season_id"].astype(str)
    dummies = pd.get_dummies(units["comp_season"], prefix="cs", drop_first=True).astype(float)
    return pd.concat([units, dummies], axis=1), list(dummies.columns)


def build_team_context_dummies(units: pd.DataFrame) -> tuple:
    units = units.copy()
    units["team_context"] = units["team"].astype(str) + "|" + units["competition_id"].astype(str) + "|" + units["season_id"].astype(str)
    dummies = pd.get_dummies(units["team_context"], prefix="tc", drop_first=True).astype(float)
    return pd.concat([units, dummies], axis=1), list(dummies.columns)


def build_possessions(match_ids: list) -> tuple:
    pass_der = pd.read_parquet(PASS_DER_PATH, columns=["match_id", "event_id", "team", "decision", "competition_id", "season_id"])
    records = []
    n_team_mismatch = 0
    for i, mid in enumerate(match_ids):
        ev = pd.read_parquet(EVENTS_DIR / f"{mid}.parquet")
        ev = ev.sort_values("index").reset_index(drop=True)
        ev_idx = ev.set_index("id")
        directions = team_period_directions(ev)

        pp = pass_der[pass_der["match_id"] == mid].copy()
        if len(pp) == 0:
            continue
        pp["possession"] = pp["event_id"].map(ev_idx["possession"])
        pp["possession_team"] = pp["event_id"].map(ev_idx["possession_team"])
        pp["order_idx"] = pp["event_id"].map(ev_idx["index"])
        loc = pp["event_id"].map(ev_idx["location"])
        pp["passer_x"] = loc.apply(lambda l: l[0] if isinstance(l, (list, np.ndarray)) else np.nan)
        pp["passer_y"] = loc.apply(lambda l: l[1] if isinstance(l, (list, np.ndarray)) else np.nan)
        pp["period"] = pp["event_id"].map(ev_idx["period"])
        n_team_mismatch += int((pp["team"] != pp["possession_team"]).sum())
        pp = pp[pp["team"] == pp["possession_team"]]

        shots = ev[ev["type"] == "Shot"].copy()
        shots = shots[shots["team"] == shots["possession_team"]]
        shot_agg = shots.groupby("possession").agg(possession_xg=("shot_statsbomb_xg", "sum"))

        for poss_id, g in pp.groupby("possession"):
            if len(g) < MIN_POSSESSION_PASSES:
                continue
            g_sorted = g.sort_values("order_idx")
            direction = directions.get((g_sorted["possession_team"].iloc[0], g_sorted["period"].iloc[0]), 1)
            nx0, _ = normalize_xy(g_sorted["passer_x"].iloc[0], g_sorted["passer_y"].iloc[0], direction)
            ends_in_shot = poss_id in shot_agg.index
            possession_xg = float(shot_agg.loc[poss_id, "possession_xg"]) if ends_in_shot else 0.0
            records.append({
                "match_id": mid, "possession": poss_id, "team": g_sorted["possession_team"].iloc[0],
                "competition_id": g_sorted["competition_id"].iloc[0], "season_id": g_sorted["season_id"].iloc[0],
                "starting_zone": zone_of(nx0), "n_passes": len(g),
                "mean_decision": float(g["decision"].mean()),
                "ends_in_shot": ends_in_shot, "possession_xg": possession_xg,
            })
        if (i + 1) % 50 == 0:
            print(f"    possessions: {i + 1}/{len(match_ids)} matches")
    return pd.DataFrame(records), n_team_mismatch


def fit_pho3(poss: pd.DataFrame) -> dict:
    poss = poss.copy()
    poss["decision_z"] = (poss["mean_decision"] - poss["mean_decision"].mean()) / poss["mean_decision"].std(ddof=1)
    poss["team_context"] = poss["team"].astype(str) + "|" + poss["competition_id"].astype(str) + "|" + poss["season_id"].astype(str)

    tc_outcome_var = poss.groupby("team_context")["ends_in_shot"].agg(["mean", "size"])
    degenerate = tc_outcome_var[(tc_outcome_var["mean"] == 0) | (tc_outcome_var["mean"] == 1)]
    n_dropped_possessions = int(degenerate["size"].sum())
    degenerate_names = list(degenerate.index)
    poss = poss[~poss["team_context"].isin(degenerate.index)].copy()

    zone_dummies = pd.get_dummies(poss["starting_zone"], prefix="zone", drop_first=False).astype(float)
    zone_dummies = zone_dummies.drop(columns=[c for c in ["zone_middle"] if c in zone_dummies.columns])
    tc_dummies = pd.get_dummies(poss["team_context"], prefix="tc", drop_first=True).astype(float)
    poss = pd.concat([poss.reset_index(drop=True), zone_dummies.reset_index(drop=True), tc_dummies.reset_index(drop=True)], axis=1)

    predictors = ["decision_z", "n_passes"] + list(zone_dummies.columns) + list(tc_dummies.columns)
    X = sm.add_constant(poss[predictors].astype(float))
    groups = poss["match_id"]

    y_a = poss["ends_in_shot"].astype(float)
    logit_model = sm.Logit(y_a, X).fit(cov_type="cluster", cov_kwds={"groups": groups}, disp=0)
    mfx = logit_model.get_margeff()
    mfx_frame = mfx.summary_frame()
    r = mfx_frame.loc["decision_z"]
    # statsmodels' own summary_frame columns (confirmed by direct inspection,
    # includes an upstream typo "Cont. Int. Hi."): dy/dx, Std. Err., z,
    # Pr(>|z|), Conf. Int. Low, Cont. Int. Hi. -- accessed by name, not
    # position, to be robust to the exact statsmodels version installed.
    logit_result = {
        "n": int(len(poss)), "pseudo_r2": float(logit_model.prsquared),
        "decision_z_margfx": {"dydx": float(r["dy/dx"]), "se": float(r["Std. Err."]),
                                "ci_low": float(r["Conf. Int. Low"]), "ci_high": float(r["Cont. Int. Hi."]),
                                "p_value": float(r["Pr(>|z|)"])},
        "n_dropped_possessions_degenerate_tc": n_dropped_possessions,
        "degenerate_team_contexts": degenerate_names,
    }

    y_b = poss["possession_xg"]
    ols_model = sm.OLS(y_b, X).fit(cov_type="cluster", cov_kwds={"groups": groups})
    ols_result = {
        "n": int(len(poss)), "r_squared": float(ols_model.rsquared),
        "decision_z_coef": {
            "coef": float(ols_model.params["decision_z"]), "se": float(ols_model.bse["decision_z"]),
            "ci_low": float(ols_model.conf_int().loc["decision_z", 0]), "ci_high": float(ols_model.conf_int().loc["decision_z", 1]),
            "p_value": float(ols_model.pvalues["decision_z"]),
        },
    }
    return {"ends_in_shot_logit": logit_result, "possession_xg_ols": ols_result}


def main():
    print("Step 5: outcome validation (v2-6.3/8.3/9.2, specifications unchanged) ...")
    units, matches_meta = build_team_match_units()
    print(f"  team-match units: {len(units)}")

    ev_match_ids = sorted(int(p.stem) for p in EV_DIR.glob("*.parquet"))
    units = add_decision(units)
    n_missing = int(units["mean_decision"].isna().sum())
    print(f"  Decision missing for {n_missing} team-match rows")

    print("  possession share ...")
    units = add_possession_share(units, ev_match_ids)
    print("  zone/pressure shares ...")
    units = add_zone_pressure_shares(units, ev_match_ids)
    print("  reference rates (completion/progressive/xA) ...")
    units = add_reference_rates(units, ev_match_ids)
    print("  xG ...")
    units = add_xg(units)

    units["decision_mean"] = units["mean_decision"].mean()
    units["decision_sd"] = units["mean_decision"].std(ddof=1)
    units["decision_z"] = (units["mean_decision"] - units["decision_mean"]) / units["decision_sd"]

    has_decision = units["mean_decision"].notna()
    dummied, cs_cols = build_comp_season_dummies(units[has_decision])
    dummied, tc_cols = build_team_context_dummies(dummied)
    keep_cols = ["match_id", "team", "comp_season", "team_context"] + cs_cols + tc_cols
    units = units.merge(dummied[keep_cols], on=["match_id", "team"], how="left")

    ho1_predictors = ["decision_z", "possession_share", "is_home"] + cs_cols
    ho2_predictors = ho1_predictors + ["completion_rate", "progressive_rate", "xa_per_pass"]
    zone_share_cols = ["final_share", "defensive_share", "pressure_share"]
    pho1_predictors = ["decision_z", "possession_share", "is_home"] + cs_cols + zone_share_cols
    pho2_predictors = ["decision_z", "possession_share", "is_home"] + zone_share_cols + tc_cols
    pho4_predictors = ["decision_z", "is_home"] + cs_cols

    team_match_results = {}
    for outcome in ("xg", "goals"):
        for label, predictors in (("H-O1", ho1_predictors), ("H-O2", ho2_predictors),
                                    ("PH-O1", pho1_predictors), ("PH-O2", pho2_predictors), ("PH-O4", pho4_predictors)):
            res = fit_ols(units, outcome, predictors, "team_context")
            team_match_results[f"{outcome}_{label}"] = res
            print(f"  {outcome} {label}: n={res['n']}, decision_z coef={res['coefficients']['decision_z']['coef']:.4f}, "
                  f"p={res['coefficients']['decision_z']['p_value']:.4g}")

    print("  building possessions (PH-O3) ...")
    poss, n_team_mismatch = build_possessions(ev_match_ids)
    print(f"  possessions (>= {MIN_POSSESSION_PASSES} passes): {len(poss)}; "
          f"eligible passes whose team differs from possession_team: {n_team_mismatch}")
    pho3 = fit_pho3(poss)
    print(f"  PH-O3(a) ends_in_shot margfx: {pho3['ends_in_shot_logit']['decision_z_margfx']}")
    print(f"  PH-O3(b) possession_xg coef: {pho3['possession_xg_ols']['decision_z_coef']}")

    summary = {
        "n_team_match_units": len(units), "n_missing_decision": n_missing,
        "team_match_results": team_match_results,
        "n_possessions": len(poss), "n_team_mismatch_passes": n_team_mismatch,
        "possession_level_results": pho3,
    }
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2, default=str))
    print(f"\nWrote {SUMMARY_PATH}")
    return summary


if __name__ == "__main__":
    main()
