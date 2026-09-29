"""
Task 44, Step 3: build the 2015/16 measures with unchanged definitions.
docs/specs/task-44-big-five-1516.md. Inputs: data/raw_1516/events (Step 1).

Author's decisions (asked; 2015/16 has no 360 frames):
- eligible pass = the engine's rule (grid.py) minus the frame condition:
  Pass, pass_type not in EXCLUDED_PASS_TYPES, passer position not
  Goalkeeper, pass_end_location present;
- g features = Task 35's feature set minus every 360-derived feature:
  ball x, y; previous located event x, y (rotated when it is the other
  team's event, as value_models_v5); time remaining in the period; score
  difference; play_pattern_code; under_pressure; period; minute.

Measures: PR2_flag_keep / PR2_flag_fwd (Task 44 Step 2 definition,
baseline refit on 2015/16 with 5 match folds, seed 20260928);
MOVE_ON_SPEED / HOLD_VARIATION per-pass residuals (time_on_ball.main and
redesign_metrics.main with Task 26 Step 2's patch, unchanged, with input
and output paths redirected to new 2015/16 files); roles by Task 32's rule
on 2015/16 positions (players with >= 100 eligible passes), deep
midfielder = >= 50% DM positions AND >= 500 eligible passes; outcomes Y_F3
(Task 42) and net xG window 10 (Task 35).

Run: python src/engine_v2/task44_build.py   (after task44_ingest.py and task44_gate.py)
"""
import json
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.append(str(Path(__file__).parent.parent / "tempo"))
import task35_ptest as tp  # noqa: E402
import task42_outcomes as t42o  # noqa: E402
import task43_spells as t43s  # noqa: E402
from task44_gate import receipt_flags, fit_baseline  # noqa: E402
from task32_step4 import ROLE_POSITIONS  # noqa: E402
from value_models import PATTERN_CODE  # noqa: E402
from grid import EXCLUDED_PASS_TYPES  # noqa: E402
import time_on_ball as tob  # noqa: E402
import metrics as tempo_metrics  # noqa: E402
import redesign_metrics_v2  # noqa: E402,F401 -- applies Task 26 Step 2's patch to redesign_metrics
import redesign_metrics as rm  # noqa: E402

warnings.filterwarnings("ignore")

DATA_DIR = Path(__file__).parent.parent.parent / "data"
EV16 = DATA_DIR / "raw_1516" / "events"
M16 = DATA_DIR / "raw_1516" / "matches"
PROC = DATA_DIR / "processed" / "engine_v2"
PASSES_PATH = PROC / "task44_passes.parquet"
RECEPTIONS_PATH = PROC / "task44_receptions.parquet"
ROLES_PATH = PROC / "task44_roles.parquet"
MOVE_PATH = DATA_DIR / "processed" / "tempo_task44_move_residuals_ids.parquet"
HOLD_PATH = DATA_DIR / "processed" / "tempo_task44_hold_residuals_ids.parquet"
SUMMARY_PATH = DATA_DIR / "engine_v2_task44_step3.json"
SEED = 20260928
N_FOLDS = 5
G_FEATURES = ["ball_x", "ball_y", "prev_x", "prev_y", "time_remaining_period", "score_diff", "play_pattern_code",
              "under_pressure", "period", "minute"]
ROLE_MIN_PASSES, DM_MIN_PASSES, SHARE = 100, 500, 0.50


def competition_lookup() -> dict:
    out = {}
    for f in M16.glob("*.parquet"):
        c, s = (int(x) for x in f.stem.split("_"))
        for mid in pd.read_parquet(f, columns=["match_id"])["match_id"]:
            out[int(mid)] = (c, s)
    return out


def match_folds(mids: list) -> dict:
    perm = np.random.default_rng(SEED).permutation(sorted(mids))
    return {int(m): i % N_FOLDS for i, m in enumerate(perm)}


def event_features(mid: int) -> pd.DataFrame:
    """value_models_v5.build_match_rows_v5's non-frame features, for every located event."""
    ev = pd.read_parquet(EV16 / f"{mid}.parquet").sort_values("index").reset_index(drop=True)
    ev["t"] = ev["minute"] * 60 + ev["second"]
    period_end = ev.groupby("period")["t"].transform("max")
    teams = ev["team"].dropna().unique().tolist()
    score = {t: 0 for t in teams}
    is_goal = ((ev["type"] == "Shot") & (ev.get("shot_outcome") == "Goal")) | (ev["type"] == "Own Goal Against")
    up = ev["under_pressure"].fillna(False).astype(bool) if "under_pressure" in ev else pd.Series(False, index=ev.index)
    rows, prev_loc, prev_team = [], None, None
    for i in range(len(ev)):
        r = ev.iloc[i]
        team, loc = r["team"], r["location"]
        opp = [t for t in teams if t != team]
        opponent = opp[0] if opp else None
        has_loc = isinstance(loc, (list, np.ndarray))
        if has_loc:
            if prev_loc is None:
                px, py = loc[0], loc[1]
            elif prev_team != team:
                px, py = 120.0 - prev_loc[0], 80.0 - prev_loc[1]
            else:
                px, py = prev_loc[0], prev_loc[1]
            if r["type"] in ("Pass", "Ball Receipt*"):
                rows.append({"match_id": mid, "event_id": r["id"], "ball_x": float(loc[0]), "ball_y": float(loc[1]),
                             "prev_x": float(px), "prev_y": float(py),
                             "time_remaining_period": float(period_end.iloc[i] - r["t"]),
                             "score_diff": (score.get(team, 0) - score.get(opponent, 0)) if opponent else 0,
                             "play_pattern_code": PATTERN_CODE.get(r["play_pattern"], PATTERN_CODE["Other"]),
                             "under_pressure": float(up.iloc[i]), "period": int(r["period"]), "minute": int(r["minute"])})
            prev_loc, prev_team = loc, team
        if is_goal.iloc[i]:
            scorer = opponent if r["type"] == "Own Goal Against" else team
            if scorer in score:
                score[scorer] += 1
    return pd.DataFrame(rows)


def eligible_passes(mid: int) -> pd.DataFrame:
    ev = pd.read_parquet(EV16 / f"{mid}.parquet", columns=["id", "type", "pass_type", "position", "pass_end_location",
                                                          "team", "player_id", "pass_outcome"])
    ok = (ev["type"] == "Pass") & (~ev["pass_type"].isin(EXCLUDED_PASS_TYPES)) & (ev["position"] != "Goalkeeper") \
        & ev["pass_end_location"].apply(lambda v: isinstance(v, (list, np.ndarray)))
    p = ev[ok].rename(columns={"id": "event_id"})
    p["pass_complete"] = p["pass_outcome"].isna().astype(float)
    p["match_id"] = mid
    return p[["match_id", "event_id", "team", "player_id", "position", "pass_complete"]]


def main():
    print("Task 44 Step 3: building 2015/16 measures ...")
    for mod in (tp, t42o, t43s):
        mod.EVENTS_DIR = EV16
    comp = competition_lookup()
    mids = sorted(comp)
    folds = match_folds(mids)

    feats, passes, rec, spells, outs, ys = [], [], [], [], [], []
    for i, m in enumerate(mids):
        feats.append(event_features(m))
        passes.append(eligible_passes(m))
        rec.append(receipt_flags(m, EV16))
        spells.append(t43s.match_spells(m))
        outs.append(t42o.match_outcomes(m)[0][["match_id", "event_id", "y_f3", "y_shot"]])
        ys.append(tp.net_xg_after(m))
        if (i + 1) % 200 == 0:
            print(f"  {i + 1}/{len(mids)} matches")
    feat = pd.concat(feats, ignore_index=True)
    out = pd.concat(outs, ignore_index=True).merge(pd.concat(ys, ignore_index=True), on=["match_id", "event_id"])

    P = pd.concat(passes, ignore_index=True).merge(feat, on=["match_id", "event_id"], how="left") \
        .merge(out, on=["match_id", "event_id"], how="left")
    P["competition_id"] = P["match_id"].map(lambda m: comp[m][0])
    P["fold"] = P["match_id"].map(folds)

    Rc = pd.concat(rec, ignore_index=True).merge(pd.concat(spells, ignore_index=True).drop(columns=["player_id"]),
                                                on=["match_id", "event_id"], how="left")
    Rc = Rc.merge(feat.drop(columns=["play_pattern_code", "period", "minute"]), on=["match_id", "event_id"], how="left") \
           .merge(out, on=["match_id", "event_id"], how="left")
    Rc["competition_id"] = Rc["match_id"].map(lambda m: comp[m][0])
    Rc["fold"] = Rc["match_id"].map(folds)
    pr = Rc[Rc["pressured_flag"] & Rc["keep_spell"].notna()].copy().reset_index(drop=True)
    base = fit_baseline(pr, folds)
    Rc = Rc.merge(pr[["match_id", "event_id", "pr2_flag_keep", "pr2_flag_fwd"]], on=["match_id", "event_id"], how="left")
    print(f"  eligible passes {len(P)}; completed receipts {len(Rc)}; pressured with spell outcome {len(pr)}; {base}")

    # roles (Task 32's rule on 2015/16 eligible-pass positions)
    per = P.groupby("player_id").agg(n=("event_id", "size"),
                                     **{f"n_{r}": ("position", lambda s, ps=ps: int(s.isin(ps).sum())) for r, ps in ROLE_POSITIONS.items()})
    per = per[per["n"] >= ROLE_MIN_PASSES]
    for r in ROLE_POSITIONS:
        per[f"share_{r}"] = per[f"n_{r}"] / per["n"]
    per["role"] = [next((r for r in ROLE_POSITIONS if row[f"share_{r}"] >= SHARE), "MIXED") for _, row in per.iterrows()]
    per["is_dm"] = (per["share_DM"] >= SHARE) & (per["n"] >= DM_MIN_PASSES)
    league = P.groupby("player_id")["competition_id"].agg(lambda s: s.mode().iloc[0])
    per["league"] = per.index.map(league)
    names = pd.concat([pd.read_parquet(EV16 / f"{m}.parquet", columns=["player_id", "player"]) for m in mids]) \
        .dropna().drop_duplicates("player_id").set_index("player_id")["player"]
    per["player_name"] = per.index.map(names)
    per.reset_index().to_parquet(ROLES_PATH)
    role_counts = per["role"].value_counts().to_dict()
    role_by_league = per.groupby(["league", "role"]).size().unstack(fill_value=0).to_dict("index")
    dm_by_league = per[per["is_dm"]].groupby("league").size().to_dict()
    print(f"  roles: {role_counts}; DM: {int(per['is_dm'].sum())} {dm_by_league}")

    P.to_parquet(PASSES_PATH)
    Rc.to_parquet(RECEPTIONS_PATH)

    # tempo, unchanged code, redirected paths
    tob.EVENTS_DIR = EV16
    tob.OUT_PATH = DATA_DIR / "processed" / "tempo_task44_time_on_ball.parquet"
    tob.SUMMARY_PATH = DATA_DIR / "tempo_task44_time_on_ball.json"
    _, tob_summary = tob.main()
    rm.EVENTS_DIR = EV16
    rm.TIME_ON_BALL_PATH = tob.OUT_PATH
    rm.OUT_PATH = DATA_DIR / "processed" / "tempo_task44_metrics.parquet"
    rm.MOVE_RESID_PATH = DATA_DIR / "processed" / "tempo_task44_move_residuals.parquet"
    rm.HOLD_RESID_PATH = DATA_DIR / "processed" / "tempo_task44_hold_residuals.parquet"
    rm.SUMMARY_PATH = DATA_DIR / "tempo_task44_redesign.json"
    tempo_metrics.match_competition_lookup = competition_lookup
    _, move_df, hold_df, tempo_summary = rm.main()
    move_df[["match_id", "event_id", "player_id", "residual"]].to_parquet(MOVE_PATH)
    hold_df[["match_id", "event_id", "player_id", "residual"]].to_parquet(HOLD_PATH)

    SUMMARY_PATH.write_text(json.dumps({
        "n_matches": len(mids), "n_eligible_passes": len(P), "n_completed_receipts": len(Rc),
        "n_pressured_flag": int(Rc["pressured_flag"].sum()), "n_pressured_with_spell_outcome": len(pr),
        "pr2_flag_baseline": base, "role_counts": role_counts, "roles_by_league": role_by_league,
        "n_dm": int(per["is_dm"].sum()), "dm_by_league": dm_by_league,
        "tempo_time_on_ball": tob_summary.get("coverage") if isinstance(tob_summary, dict) else None,
        "tempo_move_n": int(len(move_df)), "tempo_hold_n": int(len(hold_df)),
        "y_f3_rate_passes": float(P["y_f3"].mean()), "y_net_xg_mean_passes": float(P["y_net_xg"].mean())},
        indent=2, default=str))
    print(f"Wrote {SUMMARY_PATH}")


if __name__ == "__main__":
    main()
