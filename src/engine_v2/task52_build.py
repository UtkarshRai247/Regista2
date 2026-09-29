"""
Task 52, Steps 3-4 and Amendment A: build the NEW tempo measures' unit tables
on the DEVELOPMENT half only. docs/specs/task-52-tempo-development.md
(incl. Amendment A and Clarification B).

Replication lock: every file opened here is a per-match raw file (events,
frames, EV grid) whose match id is in docs/splits/tempo_split.csv's
DEVELOPMENT half (open_dev() asserts it). Every baseline is fitted on 5
match folds within development (seed 20260929). The only derived tables
read are EXISTING measures used as comparators (existing time on ball),
read with a development match-id filter and dropped immediately.

Receipt spell (Step 3): from each completed Ball Receipt* (receiver =
actor), walk forward in index order. The spell ends at the receiver's next
Pass (T = pass timestamp - receipt timestamp). Excluded: a receiver Shot;
a loss (receiver Miscontrol / Dispossessed / incomplete Dribble, or the
possession number changes); any Foul Committed / Foul Won; a period end
(Half End or period change); any other player's on-ball event (ON_BALL).
Timed = ends in his Pass and 0 < T <= 15.
Context (no identity): reception x, y; play pattern; the receipt's
under_pressure; period; minute; score difference (task44_build.event_features
logic); study only: visible opponents within 10 units of the receiver in
the receipt's freeze frame. g_T = cross-fitted XGBRegressor (Task 35's
settings) of log T; r = log T - g_T_oof.
M1 OPENING (study): a visible teammate (not the receiver) whose distance to
the opponent goal centre (120, 40) is >= 10 units smaller than the
receiver's, with no visible opponent within 5 units of him and none within
2 units of the receiver-to-him segment (geometry.point_segment_perp_distance).
M2: unit = pressured completed reception (task44_gate.receipt_flags); FK = 1
if the spell ends with his completed Pass with T <= 1.5 s (also 1.0, 2.0);
baseline = cross-fitted XGBClassifier (Task 42's settings) on the context.
Pass categories (Amendment A): eligible passes (2015/16: task44_build.
eligible_passes; study: the pass ids in the match's options_ev_v4 file);
dx = end x - start x; SWITCH = pass_switch; ACCEL = not SWITCH and (Through
Ball technique or dx >= 15); SLOW = not SWITCH and dx <= -5; KEEP otherwise.
M4 baselines: one classifier per category on the origin context (pass
x, y, play pattern, under_pressure, period, minute, score difference; study:
visible opponents within 10 units of the passer).
M5 (study): options_ev_v4 candidates restricted as policy_score_v8 (p_success
>= 0.05, distance_u <= 45, not offside_v4); OPPORTUNITY = best EV among
candidates with forward_progress_u >= 15 > best EV among the rest (False if
there is no such candidate).
M6: unit = completed eligible pass; team on-ball events (TEAM_ON_BALL) in the
same possession; V_before = (pass start x - x of the team's 3rd previous
on-ball event) / seconds; V_after = (x of the team's 3rd on-ball event after
the reception - pass end x) / seconds from the reception; both > 0 s;
baseline = cross-fitted XGBRegressor on origin context + V_before.
Outcomes for D3 / K2 from the same development raw events: Y_F3
(task42_outcomes), POSS_XG (task50_puzzle), keep_spell (task43_spells).

Run: python src/engine_v2/task52_build.py
"""
import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
import xgboost as xgb
from sklearn.metrics import r2_score, roc_auc_score

import task42_outcomes as t42o
import task43_spells as t43s
import task44_build as tb
import task50_puzzle as t50
from geometry import point_segment_perp_distance
from offside_v4 import add_offside_v4_column
from policy_baseline_fix import RESTRICT_MIN_P_SUCCESS, RESTRICT_MAX_DISTANCE_U
from task33_step3_f_state import XGB_REGRESSOR_KWARGS
from task42_step2 import CLF_KWARGS
from task44_gate import receipt_flags
from task50_robustness import mem_gate, MEM_LOG
from task52_split import dev_ids, SEED

warnings.filterwarnings("ignore")

DATA = Path(__file__).parent.parent.parent / "data"
OUT = DATA / "processed" / "engine_v2"
SUMMARY_PATH = DATA / "engine_v2_task52_build.json"
DS = {"2015/16": {"slug": "1516", "events": DATA / "raw_1516" / "events", "frames": None},
      "study": {"slug": "study", "events": DATA / "raw" / "events", "frames": DATA / "raw" / "frames"}}
EV_GRID = DATA / "processed" / "engine_v2" / "options_ev_v4"
EXISTING_TOB = {"2015/16": DATA / "processed" / "tempo_task44_time_on_ball.parquet",
                "study": DATA / "processed" / "tempo_time_on_ball.parquet"}
ON_BALL = {"Pass", "Ball Receipt*", "Carry", "Dribble", "Shot", "Miscontrol", "Dispossessed", "Clearance",
           "Interception", "Ball Recovery", "Block", "Goal Keeper", "50/50"}
TEAM_ON_BALL = {"Pass", "Ball Receipt*", "Carry", "Dribble", "Shot"}
FOULS = {"Foul Committed", "Foul Won"}
T_MAX, GOAL = 15.0, np.array([120.0, 40.0])
CTX = ["x", "y", "play_pattern_code", "under_pressure", "period", "minute", "score_diff"]
FK_CUTS = (1.0, 1.5, 2.0)
N_FOLDS = 5
DEV = {k: set(dev_ids(k)) for k in DS}


def open_dev(ds: str, mid: int, kind: str) -> pd.DataFrame:
    """The only way this task opens per-match files: asserts the match is DEVELOPMENT."""
    assert int(mid) in DEV[ds], f"REPLICATION match {mid} ({ds}) must not be opened"
    path = {"events": DS[ds]["events"], "frames": DS[ds]["frames"], "grid": EV_GRID}[kind] / f"{mid}.parquet"
    return pd.read_parquet(path)


def secs(ts) -> np.ndarray:
    p = pd.Series(ts).str.split(":", expand=True).astype(float)
    return (p[0] * 3600 + p[1] * 60 + p[2]).values


def loc(v):
    return (float(v[0]), float(v[1])) if isinstance(v, (list, np.ndarray)) and len(v) >= 2 else (np.nan, np.nan)


def frame_tools(fr: pd.DataFrame | None):
    return {} if fr is None else {eid: g for eid, g in fr.groupby("id")}


def opp10_and_opening(frames: dict, eid, xy):
    g = frames.get(eid)
    if g is None:
        return np.nan, np.nan
    pts = np.array([list(l) for l in g["location"]], dtype=float)
    act = g["actor"].values.astype(bool)
    mate = g["teammate"].values.astype(bool)
    me = pts[act][0] if act.any() else np.array(xy)
    opp = pts[~mate]
    n10 = int((np.hypot(*(opp - me).T) <= 10).sum()) if len(opp) else 0
    d_me = np.hypot(*(GOAL - me))
    opening = False
    for t in pts[mate & ~act]:
        if d_me - np.hypot(*(GOAL - t)) < 10:
            continue
        if len(opp) and (np.hypot(*(opp - t).T) <= 5).any():
            continue
        if len(opp) and any(point_segment_perp_distance(tuple(o), tuple(me), tuple(t))[0] <= 2 for o in opp):
            continue
        opening = True
        break
    return n10, float(opening)


def team_events(i, step, poss, team, team_ob, n, want=3):
    """Up to `want` of the same team's on-ball events before (step -1) or after (+1) index i, same possession."""
    out, k = [], i + step
    while 0 <= k < n and poss[k] == poss[i] and len(out) < want:
        if team[k] == team[i] and team_ob[k]:
            out.append(k)
        k += step
    return out


def match_units(ds: str, mid: int) -> tuple:
    ev = open_dev(ds, mid, "events").sort_values("index").reset_index(drop=True)
    fr = frame_tools(open_dev(ds, mid, "frames")) if ds == "study" else {}
    tb.EV16 = DS[ds]["events"]
    feats = tb.event_features(mid).set_index("event_id")
    flags = receipt_flags(mid, DS[ds]["events"]).set_index("event_id")["pressured_flag"]
    t42o.EVENTS_DIR = t43s.EVENTS_DIR = DS[ds]["events"]
    y_f3 = t42o.match_outcomes(mid)[0].set_index("event_id")["y_f3"]
    keep = t43s.match_spells(mid).set_index("event_id")["keep_spell"]
    typ, pl, team, poss, per = (ev[c].values for c in ("type", "player_id", "team", "possession", "period"))
    t = secs(ev["timestamp"])
    xy = [loc(v) for v in ev["location"]]
    exy = [loc(v) for v in ev["pass_end_location"]] if "pass_end_location" in ev else [(np.nan, np.nan)] * len(ev)
    n = len(ev)

    rec = []
    for i in np.flatnonzero((typ == "Ball Receipt*") & ev["ball_receipt_outcome"].isna().values):
        reason, T, end_id, end_ok = "no_end_found", np.nan, None, np.nan
        for k in range(i + 1, n):
            if per[k] != per[i] or typ[k] == "Half End":
                reason = "period_end"; break
            if poss[k] != poss[i]:
                reason = "loss"; break
            if typ[k] in FOULS:
                reason = "foul"; break
            if pl[k] == pl[i]:
                if typ[k] == "Pass":
                    reason, T, end_id = "pass", t[k] - t[i], ev.at[k, "id"]
                    end_ok = float(pd.isna(ev.at[k, "pass_outcome"]))
                    break
                if typ[k] == "Shot":
                    reason = "shot"; break
                if typ[k] in ("Miscontrol", "Dispossessed") or (typ[k] == "Dribble" and ev.at[k, "dribble_outcome"] == "Incomplete"):
                    reason = "loss"; break
                continue
            if typ[k] in ON_BALL:
                reason = "other_on_ball"; break
        eid = ev.at[i, "id"]
        f = feats.loc[eid] if eid in feats.index else None
        n10, opening = opp10_and_opening(fr, eid, xy[i]) if ds == "study" else (np.nan, np.nan)
        rec.append({"match_id": mid, "event_id": eid, "player_id": pl[i], "team": team[i], "x": xy[i][0], "y": xy[i][1],
                    "play_pattern_code": f["play_pattern_code"] if f is not None else np.nan,
                    "under_pressure": float(bool(ev.at[i, "under_pressure"])) if pd.notna(ev.at[i, "under_pressure"]) else 0.0,
                    "period": int(per[i]), "minute": int(ev.at[i, "minute"]),
                    "score_diff": f["score_diff"] if f is not None else np.nan,
                    "opp10": n10, "opening": opening, "end_reason": reason, "T": T, "end_pass_id": end_id,
                    "end_pass_complete": end_ok, "pressured_flag": bool(flags.get(eid, False)),
                    "y_f3": y_f3.get(eid, np.nan), "keep_spell": keep.get(eid, np.nan)})
    R = pd.DataFrame(rec)

    # eligible passes
    if ds == "2015/16":
        elig = set(tb.eligible_passes(mid)["event_id"])
        grid = None
    else:
        grid = open_dev(ds, mid, "grid")
        elig = set(grid["event_id"].unique())
    idx_of = {e: i for i, e in enumerate(ev["id"].values)}
    team_ob = np.array([typ[k] in TEAM_ON_BALL and not np.isnan(xy[k][0]) for k in range(n)])
    rows = []
    for eid in elig:
        j = idx_of.get(eid)
        if j is None:
            continue
        sx, sy = xy[j]
        ex, ey = exy[j]
        dx = ex - sx
        switch = bool(ev.at[j, "pass_switch"]) if pd.notna(ev.at[j, "pass_switch"]) else False
        through = ev.at[j, "pass_technique"] == "Through Ball"
        cat = "SWITCH" if switch else "ACCEL" if (through or dx >= 15) else "SLOW" if dx <= -5 else "KEEP"
        complete = pd.isna(ev.at[j, "pass_outcome"])
        vb = va = np.nan
        if complete:
            same = team_events(j, -1, poss, team, team_ob, n)
            if len(same) >= 3 and t[j] - t[same[2]] > 0:
                vb = (sx - xy[same[2]][0]) / (t[j] - t[same[2]])
            r_i = None
            for k in range(j + 1, n):
                if poss[k] != poss[j]:
                    break
                if typ[k] == "Ball Receipt*" and team[k] == team[j]:
                    r_i = k
                    break
            if r_i is not None:
                after = team_events(r_i, 1, poss, team, team_ob, n)
                if len(after) >= 3 and t[after[2]] - t[r_i] > 0:
                    va = (xy[after[2]][0] - ex) / (t[after[2]] - t[r_i])
        f = feats.loc[eid] if eid in feats.index else None
        n10 = opp10_and_opening(fr, eid, xy[j])[0] if ds == "study" else np.nan
        rows.append({"match_id": mid, "event_id": eid, "player_id": pl[j], "team": team[j], "position": ev.at[j, "position"],
                     "x": sx, "y": sy, "end_x": ex, "dx": dx, "category": cat, "pass_complete": float(complete),
                     "play_pattern_code": f["play_pattern_code"] if f is not None else np.nan,
                     "under_pressure": float(bool(ev.at[j, "under_pressure"])) if pd.notna(ev.at[j, "under_pressure"]) else 0.0,
                     "period": int(per[j]), "minute": int(ev.at[j, "minute"]),
                     "score_diff": f["score_diff"] if f is not None else np.nan, "opp10": n10,
                     "v_before": vb, "v_after": va, "y_f3": y_f3.get(eid, np.nan)})
    P = pd.DataFrame(rows)
    if grid is not None and len(P):
        g = add_offside_v4_column(grid, ev, open_dev(ds, mid, "frames"))
        g = g[(g["p_success"] >= RESTRICT_MIN_P_SUCCESS) & (g["distance_u"] <= RESTRICT_MAX_DISTANCE_U) & (~g["offside_v4"])]
        fwd = g["forward_progress_u"] >= 15
        best_a = g[fwd].groupby("event_id")["EV"].max()
        best_o = g[~fwd].groupby("event_id")["EV"].max()
        opp = pd.concat([best_a.rename("a"), best_o.rename("o")], axis=1)
        opp["opportunity"] = opp["a"].notna() & (opp["o"].isna() | (opp["a"] > opp["o"]))
        P["opportunity"] = P["event_id"].map(opp["opportunity"]).fillna(False).astype(float)
        P["n_restricted"] = P["event_id"].map(g.groupby("event_id").size()).fillna(0)
    ids = set(R["event_id"]) | set(P["event_id"])
    px = t50.match_outcomes(DS[ds]["events"] / f"{mid}.parquet", ids).set_index("event_id")["poss_xg"]
    R["poss_xg"] = R["event_id"].map(px)
    P["poss_xg"] = P["event_id"].map(px)
    return R, P


def folds_for(mids: list) -> dict:
    perm = np.random.default_rng(SEED).permutation(sorted(mids))
    return {int(m): i % N_FOLDS for i, m in enumerate(perm)}


def crossfit(df, feats, y, kind):
    oof = np.full(len(df), np.nan)
    f = df["fold"].values
    for k in range(N_FOLDS):
        tr, te = f != k, f == k
        if kind == "reg":
            m = xgb.XGBRegressor(**XGB_REGRESSOR_KWARGS).fit(df.loc[tr, feats].astype(float), df.loc[tr, y].astype(float))
            oof[te] = m.predict(df.loc[te, feats].astype(float))
        else:
            m = xgb.XGBClassifier(**CLF_KWARGS).fit(df.loc[tr, feats].astype(float), df.loc[tr, y].astype(int))
            oof[te] = m.predict_proba(df.loc[te, feats].astype(float))[:, 1]
    fit = float(r2_score(df[y], oof)) if kind == "reg" else float(roc_auc_score(df[y].astype(int), oof))
    return oof, fit


def dist(s: pd.Series) -> dict:
    q = s.quantile([0.05, 0.25, 0.5, 0.75, 0.95])
    return {"n": int(s.size), "mean": float(s.mean()), "sd": float(s.std()), **{f"q{int(k * 100)}": float(v) for k, v in q.items()}}


def run(ds: str) -> dict:
    mids = sorted(DEV[ds])
    mem_gate(f"{ds}: build units ({len(mids)} dev matches)")
    parts = [match_units(ds, m) for m in mids]
    R = pd.concat([p[0] for p in parts], ignore_index=True)
    P = pd.concat([p[1] for p in parts], ignore_index=True)
    fold = folds_for(mids)
    R["fold"], P["fold"] = R["match_id"].map(fold), P["match_id"].map(fold)
    ctx = CTX + (["opp10"] if ds == "study" else [])
    out = {"n_dev_matches": len(mids), "n_completed_receptions": len(R), "end_reason": R["end_reason"].value_counts().to_dict()}

    # Step 3: time on ball and g_T
    R["timed"] = (R["end_reason"] == "pass") & (R["T"] > 0) & (R["T"] <= T_MAX)
    Tm = R[R["timed"]].copy()
    Tm["logT"] = np.log(Tm["T"])
    Tm["g_T"], out["g_T_oof_r2"] = crossfit(Tm, ctx, "logT", "reg")
    R["r"] = R["event_id"].map(Tm.set_index("event_id")["logT"] - Tm.set_index("event_id")["g_T"])
    out["T_distribution"] = dist(Tm["T"])
    out["T_all_pass_endings_before_trim"] = {"n_T_le_0": int(((R["end_reason"] == "pass") & (R["T"] <= 0)).sum()),
                                             "n_T_gt_15": int(((R["end_reason"] == "pass") & (R["T"] > T_MAX)).sum())}
    # comparison with the existing tempo module (EXISTING table, read with a development match-id filter)
    ex = pq.read_table(EXISTING_TOB[ds], columns=["match_id", "event_id", "time_on_ball"],
                       filters=[("match_id", "in", mids)]).to_pandas()
    ex = ex[ex["match_id"].isin(DEV[ds])]
    j = Tm.merge(ex, left_on=["match_id", "end_pass_id"], right_on=["match_id", "event_id"], how="inner", suffixes=("", "_ex"))
    j = j.dropna(subset=["time_on_ball"])
    out["compare_existing_time_on_ball"] = {"table": str(EXISTING_TOB[ds].relative_to(DATA.parent)),
                                            "filter": "match_id in DEVELOPMENT ids", "n_joined": len(j),
                                            "pearson": float(j["T"].corr(j["time_on_ball"])),
                                            "spearman": float(j["T"].corr(j["time_on_ball"], method="spearman")),
                                            "mean_abs_diff": float((j["T"] - j["time_on_ball"]).abs().mean())}

    # M1 opening share (study)
    if ds == "study":
        out["opening_share_timed_with_frame"] = float(Tm["opening"].mean())
        out["n_timed_with_frame"] = int(Tm["opening"].notna().sum())

    # M2
    Pr = R[R["pressured_flag"]].copy()
    for c in FK_CUTS:
        Pr[f"fk_{c}"] = ((R.loc[Pr.index, "end_reason"] == "pass") & (Pr["end_pass_complete"] == 1)
                         & (Pr["T"] > 0) & (Pr["T"] <= c)).astype(int)
        Pr[f"p_fk_{c}"], out[f"fk_{c}_auc"] = crossfit(Pr, ctx, f"fk_{c}", "clf")
        out[f"fk_{c}_base_rate"] = float(Pr[f"fk_{c}"].mean())
    for c in FK_CUTS:
        R.loc[Pr.index, f"fk_{c}"] = Pr[f"fk_{c}"]
        R.loc[Pr.index, f"fk_res_{c}"] = Pr[f"fk_{c}"] - Pr[f"p_fk_{c}"]
    out["n_pressured_receptions"] = len(Pr)

    # M4 / M5 / M6
    out["category_share_all"] = P["category"].value_counts(normalize=True).to_dict()
    for cat in ("ACCEL", "KEEP", "SLOW", "SWITCH"):
        P[f"is_{cat}"] = (P["category"] == cat).astype(int)
        p, out[f"m4_{cat}_auc"] = crossfit(P, ctx, f"is_{cat}", "clf")
        P[f"res_{cat}"] = P[f"is_{cat}"] - p
    if ds == "study":
        out["opportunity_share"] = float(P["opportunity"].mean())
    U = P[(P["pass_complete"] == 1) & P["v_before"].notna() & P["v_after"].notna()].copy()
    U["v_pred"], out["m6_oof_r2"] = crossfit(U, ctx + ["v_before"], "v_after", "reg")
    P["m6_res"] = P["event_id"].map(U.set_index("event_id")["v_after"] - U.set_index("event_id")["v_pred"])
    out["n_m6_units"] = len(U)
    out["n_completed_eligible_passes"] = int((P["pass_complete"] == 1).sum())
    out["n_eligible_passes"] = len(P)
    out["v_before"], out["v_after"] = dist(U["v_before"]), dist(U["v_after"])

    slug = DS[ds]["slug"]
    R.to_parquet(OUT / f"task52_{slug}_receptions.parquet")
    P.to_parquet(OUT / f"task52_{slug}_passes.parquet")
    print(f"  {ds}: {json.dumps(out, default=str)[:1500]}", flush=True)
    return out


def main():
    print("Task 52 build (DEVELOPMENT half only) ...")
    res = {ds: run(ds) for ds in DS}
    SUMMARY_PATH.write_text(json.dumps({"datasets": res, "memory_log": MEM_LOG}, indent=2, default=str))
    print(f"Wrote {SUMMARY_PATH}")


if __name__ == "__main__":
    main()
