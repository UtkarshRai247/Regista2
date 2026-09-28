"""
Task 34, Step 1: reception quality (RQ). docs/specs/task-34-reception-quality.md.

space = distance from the receiver (the 360 frame's actor) to the nearest
VISIBLE opponent (teammate == False, keeper included), capped at 15.
A frame with zero visible opponents gets space = 15 (the cap applied to
an infinite distance) -- disclosed, counted, raised as a question.

f(context): XGBoost regression cross-fitted on the SAME 5 match folds as
engine v5 (crossfit.FOLDS_PATH), features exactly: receiver x, y;
play_pattern_code (value_models.PATTERN_CODE); n visible opponents;
period; minute; opponent team-context's mean space allowed in its OTHER
matches. No player or own-team identity.

RQ = space - f_oof; RQ_rel = RQ - mean RQ of the receiver's teammates in
the same team-context (team x competition x season), excluding himself.

Run: python src/engine_v2/task34_step1_rq.py
"""
import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.metrics import r2_score

from value_models import PATTERN_CODE
from validation_common import zone_of, match_competition_lookup
from crossfit import FOLDS_PATH, N_FOLDS

warnings.filterwarnings("ignore")

DATA_DIR = Path(__file__).parent.parent.parent / "data"
EVENTS_DIR = DATA_DIR / "raw" / "events"
FRAMES_DIR = DATA_DIR / "raw" / "frames"
EV_DIR = DATA_DIR / "processed" / "engine_v2" / "options_ev_v4"
OUT_PATH = DATA_DIR / "processed" / "engine_v2" / "task34_receptions.parquet"
SUMMARY_PATH = DATA_DIR / "engine_v2_task34_step1.json"

SPACE_CAP = 15.0
XGB_REGRESSOR_KWARGS = dict(objective="reg:squarederror", n_estimators=300, max_depth=6,
                             learning_rate=0.05, subsample=0.8, random_state=20260928)
F_FEATURES = ["recv_x", "recv_y", "play_pattern_code", "n_visible_opp", "period", "minute", "opp_ctx_mean_space"]


def match_receptions(mid: int) -> tuple:
    ev = pd.read_parquet(EVENTS_DIR / f"{mid}.parquet",
                          columns=["id", "type", "ball_receipt_outcome", "player_id", "team", "period",
                                   "minute", "play_pattern", "position"])
    rec = ev[(ev["type"] == "Ball Receipt*") & ev["ball_receipt_outcome"].isna()]
    n_all = len(rec)
    fr = pd.read_parquet(FRAMES_DIR / f"{mid}.parquet", columns=["id", "teammate", "actor", "location"])
    fr = fr[fr["id"].isin(set(rec["id"]))]
    xy = np.array(fr["location"].tolist(), dtype=float).reshape(-1, 2)
    fr = fr.assign(x=xy[:, 0], y=xy[:, 1])
    actor = fr[fr["actor"]].drop_duplicates("id").set_index("id")[["x", "y"]]
    opp = fr[~fr["teammate"]].join(actor, on="id", rsuffix="_a", how="inner")
    opp["d"] = np.hypot(opp["x"] - opp["x_a"], opp["y"] - opp["y_a"])
    nearest = opp.groupby("id")["d"].agg(["min", "size"])

    rec = rec[rec["id"].isin(actor.index)].copy()
    rec["recv_x"] = rec["id"].map(actor["x"])
    rec["recv_y"] = rec["id"].map(actor["y"])
    rec["n_visible_opp"] = rec["id"].map(nearest["size"]).fillna(0).astype(int)
    rec["space"] = rec["id"].map(nearest["min"]).fillna(np.inf).clip(upper=SPACE_CAP)
    rec["play_pattern_code"] = rec["play_pattern"].map(lambda p: PATTERN_CODE.get(p, PATTERN_CODE["Other"]))
    rec["match_id"] = mid
    teams = ev["team"].dropna().unique().tolist()
    assert len(teams) == 2, (mid, teams)
    rec["opponent"] = rec["team"].map({teams[0]: teams[1], teams[1]: teams[0]})
    return rec.drop(columns=["type", "ball_receipt_outcome", "play_pattern"]).rename(columns={"id": "event_id"}), n_all


def leave_match_out_mean(df: pd.DataFrame, key: str, val: str) -> pd.Series:
    """Per row: mean of `val` over rows with the same `key` in OTHER matches."""
    tot = df.groupby(key)[val].agg(["sum", "count"])
    bym = df.groupby([key, "match_id"])[val].agg(["sum", "count"])
    idx = pd.MultiIndex.from_arrays([df[key], df["match_id"]])
    s = tot["sum"].reindex(df[key]).values - bym["sum"].reindex(idx).values
    c = tot["count"].reindex(df[key]).values - bym["count"].reindex(idx).values
    return pd.Series(np.where(c > 0, s / np.where(c > 0, c, 1), np.nan), index=df.index)


def main():
    print("Task 34 Step 1: reception quality ...")
    folds = pd.read_csv(FOLDS_PATH)
    ev_mids = {int(p.stem) for p in EV_DIR.glob("*.parquet")}
    folds = folds[folds["match_id"].isin(ev_mids)]
    fold_of = dict(zip(folds["match_id"], folds["fold"]))
    match_ids = sorted(fold_of)
    assert len(match_ids) == 292, len(match_ids)

    parts, n_all_total = [], 0
    for mid in match_ids:
        r, n_all = match_receptions(mid)
        parts.append(r)
        n_all_total += n_all
    df = pd.concat(parts, ignore_index=True)
    print(f"  successful receptions: {n_all_total}; with 360 frame + actor: {len(df)} ({len(df)/n_all_total:.2%})")

    comp = match_competition_lookup()
    df["competition_id"] = df["match_id"].map(lambda m: comp[m][0])
    df["season_id"] = df["match_id"].map(lambda m: comp[m][1])
    cs = df["competition_id"].astype(str) + "|" + df["season_id"].astype(str)
    df["team_context"] = df["team"].astype(str) + "|" + cs
    df["opp_context"] = df["opponent"].astype(str) + "|" + cs
    df["opp_ctx_mean_space"] = leave_match_out_mean(df, "opp_context", "space")
    df["fold"] = df["match_id"].map(fold_of)

    n_zero_opp = int((df["n_visible_opp"] == 0).sum())
    print(f"  frames with zero visible opponents (space set to cap {SPACE_CAP}): {n_zero_opp}")
    print(f"  opp_ctx_mean_space missing (opponent context has no other match): {int(df['opp_ctx_mean_space'].isna().sum())}")

    oof = np.full(len(df), np.nan)
    for k in range(N_FOLDS):
        tr, te = df["fold"] != k, df["fold"] == k
        model = xgb.XGBRegressor(**XGB_REGRESSOR_KWARGS)
        model.fit(df.loc[tr, F_FEATURES].astype(float), df.loc[tr, "space"])
        oof[te.values] = model.predict(df.loc[te, F_FEATURES].astype(float))
        print(f"  fold {k}: train {int(tr.sum())}, test {int(te.sum())}")
    df["f_oof"] = oof
    r2 = float(r2_score(df["space"], df["f_oof"]))
    print(f"  pooled OOF R^2: {r2:.4f} (n={len(df)})")

    df["rq"] = df["space"] - df["f_oof"]
    ctx = df.groupby("team_context")["rq"].agg(["sum", "count"])
    pl = df.groupby(["team_context", "player_id"])["rq"].agg(["sum", "count"])
    idx = pd.MultiIndex.from_arrays([df["team_context"], df["player_id"]])
    s = ctx["sum"].reindex(df["team_context"]).values - pl["sum"].reindex(idx).values
    c = ctx["count"].reindex(df["team_context"]).values - pl["count"].reindex(idx).values
    df["rq_rel"] = df["rq"] - np.where(c > 0, s / np.where(c > 0, c, 1), np.nan)
    print(f"  rq_rel undefined (no teammate receptions in context): {int(df['rq_rel'].isna().sum())}")

    df["zone"] = df["recv_x"].apply(zone_of)
    by_zone = []
    for z, g in df.groupby("zone"):
        by_zone.append({"zone": z, "n": len(g), "mean_space": float(g["space"].mean()),
                        "mean_rq": float(g["rq"].mean()), "se_rq": float(g["rq"].std(ddof=1) / np.sqrt(len(g)))})
        print(f"    zone {z}: n={len(g)}, mean space={g['space'].mean():.3f}, mean RQ={g['rq'].mean():.4f}")

    q = [0.01, 0.05, 0.25, 0.5, 0.75, 0.95, 0.99]
    dist = {col: {"mean": float(df[col].mean()), "sd": float(df[col].std()),
                  **{f"q{int(p*100):02d}": float(df[col].quantile(p)) for p in q}}
            for col in ("space", "f_oof", "rq", "rq_rel")}
    dist["share_space_at_cap"] = float((df["space"] >= SPACE_CAP).mean())
    dist["n_visible_opp"] = {"mean": float(df["n_visible_opp"].mean()),
                             **{f"q{int(p*100):02d}": float(df["n_visible_opp"].quantile(p)) for p in q}}

    df.to_parquet(OUT_PATH)
    summary = {"n_matches": len(match_ids), "n_successful_receptions": n_all_total, "n_receptions": len(df),
               "share_with_frame": len(df) / n_all_total, "n_zero_visible_opp": n_zero_opp,
               "n_opp_ctx_missing": int(df["opp_ctx_mean_space"].isna().sum()),
               "n_rq_rel_undefined": int(df["rq_rel"].isna().sum()),
               "features": F_FEATURES, "oof_r2": r2, "mean_rq_overall": float(df["rq"].mean()),
               "by_zone": by_zone, "distributions": dist,
               "n_players": int(df["player_id"].nunique()), "n_team_contexts": int(df["team_context"].nunique())}
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2, default=str))
    print(f"Wrote {OUT_PATH} and {SUMMARY_PATH}")


if __name__ == "__main__":
    main()
