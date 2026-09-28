"""
Task 32, Step 6 (B1): does the typical-choice model earn its place?
All IN-SAMPLE (full corpus, 292 matches -- same population as every
other Task 32 step). Per pass:
  b1 = ev_chosen alone
  b2 = ev_chosen - mean EV of ALL candidates for that pass (uniform
       baseline, from the EV corpus)
  b3 = Decision (ev_chosen - policy_weighted_ev, pass_der_v8's decision_new)
Team-match means, standardised, each fit alone under H-O1/PH-O2 for
xG and goals (coef, p, R^2), then b3+b1 together and b3+b2 together.
Also, within the 111 deep midfielders, correlations among the three
player-level versions.

Reuses build_team_match_units/add_possession_share/add_zone_pressure_shares/
add_xg/build_comp_season_dummies/build_team_context_dummies/fit_ols
unchanged from outcome_validation.py / validation_common.py.

Run: python src/engine_v2/task32_step6.py
"""
import json
import warnings
from pathlib import Path

import pandas as pd

from validation_common import fit_ols
from outcome_validation import (
    build_team_match_units, add_possession_share, add_zone_pressure_shares,
    add_xg, build_comp_season_dummies, build_team_context_dummies,
)

warnings.filterwarnings("ignore")

DATA_DIR = Path(__file__).parent.parent.parent / "data"
EV_DIR = DATA_DIR / "processed" / "engine_v2" / "options_ev"
EV_V4_DIR = DATA_DIR / "processed" / "engine_v2" / "options_ev_v4"
PASS_DER_V8_PATH = DATA_DIR / "processed" / "engine_v2" / "pass_der_v8.parquet"
LEADERBOARD_V5C_PATH = DATA_DIR / "processed" / "leaderboard_v5c.parquet"
SUMMARY_PATH = DATA_DIR / "engine_v2_task32_step6.json"


def build_per_pass_baselines() -> pd.DataFrame:
    der = pd.read_parquet(PASS_DER_V8_PATH,
                           columns=["match_id", "event_id", "player_id", "decision_new"])
    match_ids = sorted(der["match_id"].unique())
    frames = []
    for mid in match_ids:
        df = pd.read_parquet(EV_V4_DIR / f"{mid}.parquet", columns=["match_id", "event_id", "team", "chosen", "EV"])
        chosen = df[df["chosen"]][["match_id", "event_id", "team", "EV"]].rename(columns={"EV": "ev_chosen"})
        mean_all = df.groupby("event_id")["EV"].mean().rename("mean_ev_all_candidates").reset_index()
        chosen = chosen.merge(mean_all, on="event_id", how="left")
        frames.append(chosen)
    ev = pd.concat(frames, ignore_index=True)
    out = der.merge(ev, on=["match_id", "event_id"], how="inner")
    out["b1"] = out["ev_chosen"]
    out["b2"] = out["ev_chosen"] - out["mean_ev_all_candidates"]
    out["b3"] = out["decision_new"]
    return out


def zscore(s: pd.Series) -> pd.Series:
    return (s - s.mean()) / s.std(ddof=1)


def main():
    print("Task 32 Step 6 (B1): baseline comparison (in-sample) ...")
    per_pass = build_per_pass_baselines()
    print(f"  {len(per_pass)} passes joined")

    team_match = per_pass.groupby(["match_id", "team"]).agg(
        b1=("b1", "mean"), b2=("b2", "mean"), b3=("b3", "mean")).reset_index()
    for col in ("b1", "b2", "b3"):
        team_match[f"{col}_z"] = zscore(team_match[col])

    units, _ = build_team_match_units()
    ev_match_ids = sorted(int(p.stem) for p in EV_DIR.glob("*.parquet"))
    units = add_possession_share(units, ev_match_ids)
    units = add_zone_pressure_shares(units, ev_match_ids)
    units = add_xg(units)
    units = units.merge(team_match[["match_id", "team", "b1_z", "b2_z", "b3_z"]], on=["match_id", "team"], how="inner")
    print(f"  {len(units)} team-match units with all three baselines")

    dummied, cs_cols = build_comp_season_dummies(units)
    dummied, tc_cols = build_team_context_dummies(dummied)
    units = units.merge(dummied[["match_id", "team", "comp_season", "team_context"] + cs_cols + tc_cols],
                          on=["match_id", "team"], how="left")

    zone_share_cols = ["final_share", "defensive_share", "pressure_share"]

    def ho1(zcols):
        return zcols + ["possession_share", "is_home"] + cs_cols

    def pho2(zcols):
        return zcols + ["possession_share", "is_home"] + zone_share_cols + tc_cols

    results = {}
    specs = [("b1_alone", ["b1_z"]), ("b2_alone", ["b2_z"]), ("b3_alone", ["b3_z"]),
              ("b3_plus_b1", ["b3_z", "b1_z"]), ("b3_plus_b2", ["b3_z", "b2_z"])]
    for outcome in ("xg", "goals"):
        for spec_name, zcols in specs:
            for label, predictor_fn in (("H-O1", ho1), ("PH-O2", pho2)):
                predictors = predictor_fn(zcols)
                res = fit_ols(units, outcome, predictors, "team_context")
                key = f"{outcome}_{spec_name}_{label}"
                results[key] = res
                coefs = {c: f"{res['coefficients'][c]['coef']:.4f} (p={res['coefficients'][c]['p_value']:.3g})"
                         for c in zcols}
                print(f"  {key}: n={res['n']}, R2={res['r_squared']:.4f}, {coefs}")

    print("  within-111-deep-midfielders player-level correlations ...")
    dm_ids = set(pd.read_parquet(LEADERBOARD_V5C_PATH, columns=["player_id", "is_deep_midfield"])
                 .loc[lambda d: d["is_deep_midfield"], "player_id"])
    pp_dm = per_pass[per_pass["player_id"].isin(dm_ids)]
    player_level = pp_dm.groupby("player_id").agg(b1=("b1", "mean"), b2=("b2", "mean"), b3=("b3", "mean")).reset_index()
    corr = player_level[["b1", "b2", "b3"]].corr()
    print(f"    n_dm_players_with_passes={len(player_level)}")
    print(corr)

    summary = {
        "n_passes": len(per_pass), "n_team_match_units": len(units), "results": results,
        "dm_player_level_correlations": {"n": len(player_level), "corr": corr.to_dict()},
    }
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2, default=str))
    print(f"\nWrote {SUMMARY_PATH}")
    return summary


if __name__ == "__main__":
    main()
