"""
Task 38, Step 1: "always available" -- is a teammate a genuinely open
option at his teammates' passes? docs/specs/task-38-availability.md.

PFF events and their embedded 22-player snapshots only (top-level Event
Data, v2.5 spec). For every PA/CR event (nonEvent false, periods 1-4),
for every OUTFIELD teammate of the passer present in the snapshot (not
the passer, not positionGroupType GK), in PFF metres:
  d_ball = ball -> teammate; space = teammate -> nearest opponent;
  lane = min distance from any opponent to the segment ball -> teammate
  AVAILABLE = 5 <= d_ball <= 40 and space >= 3 and lane >= 2.
Baseline p(context): XGBoost classifier cross-fitted over 5 folds of
MATCHES (seed 20260928) on ball x/y (passing team's attacking frame,
Task 36's frames.to_sb / attack_sign), passer under pressure
(pressureType != 'N' -- told decision D-016; the brief's "not null" is
always true), opponents within 10 m of the ball, score difference for
the passing team, period, minute, the teammate's positionGroupType.
AV = AVAILABLE - p_oof. AV_vis: moments where the teammate AND his nearest
opponent are VISIBLE, baseline refit on that subset with the same folds.

Also extracts Step 3 R2's reception units (completed PA/CR with a
receiver): Y = net StatsBomb xG over the next 10 PFF possession events
(PFF shots paired in Task 36's shot_pairs; unpaired shots excluded and
counted), and the reception's context (ball location at the receiver's
next PFF event in his team's frame, that event's pressure, period, minute).

Run: python src/pff/availability.py
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.metrics import roc_auc_score

sys.path.insert(0, str(Path(__file__).parent.parent / "engine_v2"))
from frames import to_sb, attack_sign, load_meta, PFF_DIR, OUT_DIR  # noqa: E402
from geometry import point_segment_perp_distance  # noqa: E402

DATA_DIR = Path(__file__).parent.parent.parent / "data"
EVENTS_DIR = PFF_DIR / "Event Data"
SB_EVENTS = DATA_DIR / "raw" / "events"
SB_MATCHES = DATA_DIR / "raw" / "matches" / "43_106.parquet"
MOMENTS_PATH = OUT_DIR / "availability_moments.parquet"
RECEPTIONS_PATH = OUT_DIR / "availability_receptions.parquet"
SUMMARY_PATH = DATA_DIR / "pff_task38_step1.json"

SEED = 20260928
N_FOLDS = 5
PERIODS = (1, 2, 3, 4)
Y_WINDOW = 10
CLF_KWARGS = dict(objective="binary:logistic", n_estimators=300, max_depth=6, learning_rate=0.05,
                  subsample=0.8, random_state=SEED)
FEATURES = ["ball_x", "ball_y", "under_pressure", "n_opp_10m_ball", "score_diff", "period", "minute", "pos_code"]
BONO_OVERRIDE = {"team": "Morocco", "shirt": "1"}  # brief Q3 / D-016: map to Yassine Bounou


def seg_dist(p: np.ndarray, a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Distance from each point p (n x 2) to segment a-b (point-to-segment, clamped)."""
    ab = b - a
    L2 = float(ab @ ab)
    if L2 == 0:
        return np.hypot(*(p - a).T)
    t = np.clip(((p - a) @ ab) / L2, 0, 1)
    proj = a + t[:, None] * ab
    return np.hypot(*(p - proj).T)


def _self_check():
    pts = np.array([[1.0, 1.0], [-2.0, 0.5], [7.0, -3.0]])
    a, b = np.array([0.0, 0.0]), np.array([5.0, 0.0])
    got = seg_dist(pts, a, b)
    want = [point_segment_perp_distance(tuple(p), tuple(a), tuple(b))[0] for p in pts]
    assert np.allclose(got, want), (got, want)


def match_folds(gids: list) -> dict:
    perm = np.random.default_rng(SEED).permutation(sorted(gids))
    return {int(g): i % N_FOLDS for i, g in enumerate(perm)}


def sb_xg_by_pair(gid: int, pairs: pd.DataFrame) -> dict:
    sub = pairs[pairs["pff_game_id"] == gid]
    if len(sub) == 0:
        return {}
    mid = int(sub["statsbomb_match_id"].iloc[0])
    ev = pd.read_parquet(SB_EVENTS / f"{mid}.parquet", columns=["id", "shot_statsbomb_xg"]).set_index("id")
    return {round(float(vt), 3): float(ev.loc[sid, "shot_statsbomb_xg"])
            for vt, sid in zip(sub["video_time"], sub["sb_event_id"])}


def process_match(gid: int, pairs: pd.DataFrame) -> tuple:
    meta = load_meta(gid)
    home_id = int(meta["homeTeam"]["id"])
    events = json.loads((EVENTS_DIR / f"{gid}.json").read_text())
    xg_of = sb_xg_by_pair(gid, pairs)
    pe = [e.get("possessionEvents") or {} for e in events]
    ge = [e.get("gameEvents") or {} for e in events]
    poss_idx = [i for i, p in enumerate(pe) if p.get("possessionEventType")]

    away_id = int(meta["awayTeam"]["id"])
    goals, ko_periods = {}, set()
    moments, receptions = [], []
    n_pass_events, n_no_ball, shots_seen, shots_unpaired = 0, 0, 0, 0
    for i, (e, p, g) in enumerate(zip(events, pe, ge)):
        team_id = g.get("teamId")
        if p.get("possessionEventType") == "SH":
            shots_seen += 1
            if round(float(e["startTime"]), 3) not in xg_of:
                shots_unpaired += 1
        if p.get("possessionEventType") in ("PA", "CR") and not p.get("nonEvent") and g.get("period") in PERIODS:
            n_pass_events += 1
            balls = e.get("ball") or []
            if not balls or balls[0].get("x") is None:
                n_no_ball += 1
            else:
                side = "home" if int(team_id) == home_id else "away"
                mates, opps = (e["homePlayers"], e["awayPlayers"]) if side == "home" else (e["awayPlayers"], e["homePlayers"])
                opps = [o for o in opps if o.get("x") is not None]
                ball = np.array([balls[0]["x"], balls[0]["y"]], dtype=float)
                period = int(g["period"])
                sign = attack_sign(meta, side, period)
                bx, by = to_sb(ball[0], ball[1], sign, meta)
                opp_xy = np.array([[o["x"], o["y"]] for o in opps], dtype=float)
                opp_vis = np.array([o.get("visibility") == "VISIBLE" for o in opps])
                n_opp_10 = int((np.hypot(*(opp_xy - ball).T) <= 10).sum()) if len(opps) else 0
                own = sum(v for k, v in goals.items() if k == team_id)
                other = sum(v for k, v in goals.items() if k != team_id)
                ctx = {"pff_game_id": gid, "event_idx": i, "period": period,
                       "minute": int(g.get("startGameClock") or 0) // 60,
                       "ball_x": float(bx), "ball_y": float(by),
                       "under_pressure": int(p.get("pressureType") not in (None, "N")),
                       "pressure_code": p.get("pressureType"),
                       "n_opp_10m_ball": n_opp_10, "score_diff": own - other, "team_id": int(team_id),
                       "side": side}
                passer = p.get("passerPlayerId")
                target = p.get("targetPlayerId")
                for m in mates:
                    if m.get("playerId") == passer or m.get("positionGroupType") == "GK" or m.get("x") is None:
                        continue
                    t = np.array([m["x"], m["y"]], dtype=float)
                    d_ball = float(np.hypot(*(t - ball)))
                    if len(opps):
                        dd = np.hypot(*(opp_xy - t).T)
                        j = int(dd.argmin())
                        space, nearest_vis = float(dd[j]), bool(opp_vis[j])
                        lane = float(seg_dist(opp_xy, ball, t).min())
                    else:
                        space, nearest_vis, lane = np.inf, False, np.inf
                    moments.append({**ctx, "pff_player_id": int(m["playerId"]), "position": m.get("positionGroupType"),
                                    "d_ball": d_ball, "space": space, "lane": lane,
                                    "available": int(5 <= d_ball <= 40 and space >= 3 and lane >= 2),
                                    "is_target": int(target is not None and int(target) == int(m["playerId"])),
                                    "mate_visible": m.get("visibility") == "VISIBLE", "nearest_opp_visible": nearest_vis})

                rec_id = p.get("receiverPlayerId")
                if p.get("passOutcomeType") == "C" and rec_id is not None:
                    later = [k for k in poss_idx if k > i][:Y_WINDOW]
                    y, n_unp = 0.0, 0
                    for k in later:
                        if pe[k].get("possessionEventType") == "SH":
                            xg = xg_of.get(round(float(events[k]["startTime"]), 3))
                            if xg is None:
                                n_unp += 1
                                continue
                            y += xg if ge[k].get("teamId") == team_id else -xg
                    nxt = next((k for k in range(i + 1, min(i + 4, len(events))) if ge[k].get("playerId") == rec_id), None)
                    r = {"pff_game_id": gid, "event_idx": i, "team_id": int(team_id), "side": side, "period": period,
                         "minute": ctx["minute"], "pff_player_id": int(rec_id), "y_net_xg": y, "n_unpaired_shots_in_window": n_unp,
                         "rec_x": np.nan, "rec_y": np.nan, "rec_pressure": np.nan,
                         "role": next((m.get("positionGroupType") for m in mates if m.get("playerId") == rec_id), None)}
                    if nxt is not None:
                        nb = events[nxt].get("ball") or []
                        if nb and nb[0].get("x") is not None:
                            rx, ry = to_sb(nb[0]["x"], nb[0]["y"], sign, meta)
                            r["rec_x"], r["rec_y"] = float(rx), float(ry)
                        pt = pe[nxt].get("pressureType") or (events[nxt].get("initialTouch") or {}).get("initialPressureType")
                        r["rec_pressure"] = np.nan if pt is None else float(pt != "N")
                    receptions.append(r)
        # Score from kickoff restarts: every kickoff in periods 1-4 except the first of its period is
        # taken by the team that just conceded (PFF's shotOutcomeType 'G' includes disallowed goals and
        # shoot-out kicks and misses own goals -- 24/64 matches disagreed with StatsBomb's final score).
        if g.get("setpieceType") == "K" and g.get("period") in PERIODS:
            if g["period"] in ko_periods:
                scorer = away_id if int(team_id) == home_id else home_id
                goals[scorer] = goals.get(scorer, 0) + 1
            ko_periods.add(g["period"])
    info = {"n_pass_events": n_pass_events, "n_pass_events_no_ball": n_no_ball, "n_shots": shots_seen,
            "n_shots_unpaired": shots_unpaired, "goals_by_team_id": {str(k): v for k, v in goals.items()},
            "home_id": home_id, "home": meta["homeTeam"]["name"], "away": meta["awayTeam"]["name"]}
    return moments, receptions, info


def fit_oof(df: pd.DataFrame, folds: dict) -> tuple:
    fold = df["pff_game_id"].map(folds).values
    oof = np.full(len(df), np.nan)
    for k in range(N_FOLDS):
        tr, te = fold != k, fold == k
        m = xgb.XGBClassifier(**CLF_KWARGS).fit(df.loc[tr, FEATURES].astype(float), df.loc[tr, "available"])
        oof[te] = m.predict_proba(df.loc[te, FEATURES].astype(float))[:, 1]
    return oof, float(roc_auc_score(df["available"], oof))


def main():
    _self_check()
    cw = pd.read_csv(OUT_DIR / "crosswalk.csv")
    pairs = pd.read_parquet(OUT_DIR / "shot_pairs.parquet", columns=["pff_game_id", "statsbomb_match_id", "video_time", "sb_event_id"])
    gids = sorted(cw["pff_game_id"].astype(int))
    folds = match_folds(gids)

    all_m, all_r, infos = [], [], {}
    for gid in gids:
        m, r, info = process_match(gid, pairs)
        all_m.extend(m)
        all_r.extend(r)
        infos[gid] = info
    mom = pd.DataFrame(all_m)
    rec = pd.DataFrame(all_r)
    pos_codes = {p: i for i, p in enumerate(sorted(mom["position"].dropna().unique()))}
    mom["pos_code"] = mom["position"].map(pos_codes)
    print(f"  moments: {len(mom)}; pass events: {sum(i['n_pass_events'] for i in infos.values())}")

    mom["p_oof"], auc = fit_oof(mom, folds)
    mom["av"] = mom["available"] - mom["p_oof"]
    vis = mom["mate_visible"] & mom["nearest_opp_visible"]
    mv = mom[vis].copy()
    mv["p_oof_vis"], auc_vis = fit_oof(mv, folds)
    mom["p_oof_vis"] = np.nan
    mom.loc[vis, "p_oof_vis"] = mv["p_oof_vis"].values
    mom["av_vis"] = mom["available"] - mom["p_oof_vis"]

    pmap = pd.read_csv(OUT_DIR / "player_map.csv")
    ok = (pmap["status"] == "mapped") | ((pmap["team"] == BONO_OVERRIDE["team"]) & (pmap["shirt"].astype(str) == BONO_OVERRIDE["shirt"]))
    sb_of = pmap[ok].drop_duplicates("pff_player_id").set_index("pff_player_id")["sb_player_id"]
    mom["sb_player_id"] = mom["pff_player_id"].map(sb_of)
    rec["sb_player_id"] = rec["pff_player_id"].map(sb_of)
    mom["fold"] = mom["pff_game_id"].map(folds)
    rec["fold"] = rec["pff_game_id"].map(folds)
    mom.to_parquet(MOMENTS_PATH)
    rec.to_parquet(RECEPTIONS_PATH)

    sbm = pd.read_parquet(SB_MATCHES, columns=["match_id", "home_team", "away_team", "home_score", "away_score"]).set_index("match_id")
    score_mismatch = []
    for gid, info in infos.items():
        mid = int(cw.loc[cw["pff_game_id"] == gid, "statsbomb_match_id"].iloc[0])
        s = sbm.loc[mid]
        pff_home = info["goals_by_team_id"].get(str(info["home_id"]), 0)
        pff_total = sum(info["goals_by_team_id"].values())
        if pff_total != s["home_score"] + s["away_score"] or (info["home"].lower() == s["home_team"].lower() and pff_home != s["home_score"]):
            score_mismatch.append({"pff_game_id": gid, "pff_goals": info["goals_by_team_id"], "home": info["home"],
                                   "sb": f"{s['home_team']} {s['home_score']}-{s['away_score']} {s['away_team']}"})

    av = mom["available"] == 1
    summary = {
        "n_matches": len(gids), "n_pass_events": int(sum(i["n_pass_events"] for i in infos.values())),
        "n_pass_events_no_ball": int(sum(i["n_pass_events_no_ball"] for i in infos.values())),
        "n_moments": len(mom), "base_rate_available": float(mom["available"].mean()),
        "baseline_oof_auc": auc, "mean_av": float(mom["av"].mean()),
        "n_moments_vis": int(vis.sum()), "base_rate_available_vis": float(mom.loc[vis, "available"].mean()),
        "baseline_oof_auc_vis": auc_vis, "mean_av_vis": float(mom.loc[vis, "av_vis"].mean()),
        "p_target_given_available": float(mom.loc[av, "is_target"].mean()), "n_available": int(av.sum()),
        "p_target_given_not_available": float(mom.loc[~av, "is_target"].mean()), "n_not_available": int((~av).sum()),
        "share_of_targets_that_were_available": float(mom.loc[mom["is_target"] == 1, "available"].mean()),
        "n_target_moments": int(mom["is_target"].sum()),
        "component_rates": {"d_ball_5_40": float(mom["d_ball"].between(5, 40).mean()),
                            "space_ge3": float((mom["space"] >= 3).mean()), "lane_ge2": float((mom["lane"] >= 2).mean())},
        "n_players_moments": int(mom["pff_player_id"].nunique()),
        "n_moments_no_sb_id": int(mom["sb_player_id"].isna().sum()),
        "n_receptions": len(rec), "n_receptions_no_next_event": int(rec["rec_x"].isna().sum()),
        "n_shots_pff": int(sum(i["n_shots"] for i in infos.values())),
        "n_shots_unpaired": int(sum(i["n_shots_unpaired"] for i in infos.values())),
        "n_receptions_with_unpaired_shot_in_window": int((rec["n_unpaired_shots_in_window"] > 0).sum()),
        "score_mismatch_vs_statsbomb": score_mismatch, "position_codes": pos_codes,
        "folds": {str(k): v for k, v in folds.items()},
    }
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2, default=str))
    print(json.dumps({k: v for k, v in summary.items() if k not in ("folds", "score_mismatch_vs_statsbomb")}, indent=1, default=str))
    print("score mismatches:", len(score_mismatch))


if __name__ == "__main__":
    main()
