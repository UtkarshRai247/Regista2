"""
Task 18, Step 3 (continued): re-runs the FULL outcome-validation battery
(v2-6.3/8.3/9.2, specifications unchanged) on the CROSS-FITTED Decision
from crossfit.py, reusing every general-purpose builder from
outcome_validation.py (team-match units, possession share, zone/pressure
shares, reference rates, xG, dummy builders, PH-O3's possession builder
and fit) unchanged -- only the Decision SOURCE differs (pass_der_
crossfit.parquet's out-of-fold `decision` column instead of Task 17's
in-sample pass_der.parquet).

Run: python src/engine_v2/outcome_validation_crossfit.py
"""
import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

from geometry import team_period_directions, normalize_xy
from validation_common import zone_of, fit_ols, match_competition_lookup
from outcome_validation import (
    build_team_match_units, add_possession_share, add_zone_pressure_shares,
    add_reference_rates, add_xg, build_comp_season_dummies, build_team_context_dummies,
    fit_pho3, MIN_POSSESSION_PASSES,
)

warnings.filterwarnings("ignore")

DATA_DIR = Path(__file__).parent.parent.parent / "data"
EVENTS_DIR = DATA_DIR / "raw" / "events"
EV_DIR = DATA_DIR / "processed" / "engine_v2" / "options_ev"
PASS_DER_CROSSFIT_PATH = DATA_DIR / "processed" / "engine_v2" / "pass_der_crossfit.parquet"
SUMMARY_PATH = DATA_DIR / "engine_v2_step3_outcome_validation_crossfit.json"


def add_decision_crossfit(units: pd.DataFrame) -> pd.DataFrame:
    pass_der = pd.read_parquet(PASS_DER_CROSSFIT_PATH, columns=["match_id", "team", "decision"])
    dec = pass_der.groupby(["match_id", "team"])["decision"].mean().reset_index().rename(columns={"decision": "mean_decision"})
    return units.merge(dec, on=["match_id", "team"], how="left")


def build_possessions_crossfit(match_ids: list) -> tuple:
    pass_der = pd.read_parquet(PASS_DER_CROSSFIT_PATH, columns=["match_id", "event_id", "team", "decision"])
    comp_lookup = match_competition_lookup()
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
            comp_id, season_id = comp_lookup.get(mid, (None, None))
            records.append({
                "match_id": mid, "possession": poss_id, "team": g_sorted["possession_team"].iloc[0],
                "competition_id": comp_id, "season_id": season_id,
                "starting_zone": zone_of(nx0), "n_passes": len(g),
                "mean_decision": float(g["decision"].mean()),
                "ends_in_shot": ends_in_shot, "possession_xg": possession_xg,
            })
        if (i + 1) % 50 == 0:
            print(f"    possessions: {i + 1}/{len(match_ids)} matches")
    df = pd.DataFrame(records)
    return df, n_team_mismatch


def main():
    print("Step 3: outcome validation on cross-fitted Decision (v2-6.3/8.3/9.2, specifications unchanged) ...")
    units, matches_meta = build_team_match_units()
    ev_match_ids = sorted(int(p.stem) for p in EV_DIR.glob("*.parquet"))

    units = add_decision_crossfit(units)
    n_missing = int(units["mean_decision"].isna().sum())
    print(f"  Decision missing for {n_missing} team-match rows")

    units = add_possession_share(units, ev_match_ids)
    units = add_zone_pressure_shares(units, ev_match_ids)
    print("  reference rates ...")
    units = add_reference_rates(units, ev_match_ids)
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

    print("  building possessions (PH-O3) on cross-fitted Decision ...")
    poss, n_team_mismatch = build_possessions_crossfit(ev_match_ids)
    print(f"  possessions (>= {MIN_POSSESSION_PASSES} passes): {len(poss)}")
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
