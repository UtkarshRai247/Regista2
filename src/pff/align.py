"""
Task 36, Step 3: align the PFF WC2022 data to StatsBomb.
docs/specs/task-36-pff-ingest.md.

(a) Match crosswalk: audit_alignment.crosswalk()'s date + team-name rule,
    re-implemented against the local StatsBomb matches file (the original
    fetches via statsbombpy and is not modified). Must be 64/64.
(b) Clock: PFF shot period clock = the tracking file's
    periodElapsedTime at the frame nearest the PFF event's startTime
    (taken by frames.py; metadata startPeriod{p} is missing for some
    knockout matches, so it is not used). Paired to StatsBomb shots: same
    team, same period, nearest within 10 s, one-to-one (greedy, smallest
    gap first). offset = StatsBomb - PFF (s). Periods 1-4 only.
(c) Players: PFF roster (team + shirt number) -> StatsBomb lineup
    (team + jersey number, statsbombpy open data), confirmed by name
    similarity.
(d) Coordinates: on every paired shot, distance between the StatsBomb
    shot location and the converted PFF ball / shooter position at the
    aligned time (StatsBomb clock - match-period median offset), from
    frames.py's 30 fps shot-window snapshots. Then writes time_sb into
    each per-frame table.

Run order: python src/pff/align.py --stage players
           python src/pff/frames.py
           python src/pff/align.py --stage clock
"""
import argparse
import difflib
import json
import re
import unicodedata
from pathlib import Path

import numpy as np
import pandas as pd

from frames import to_sb, attack_sign, load_meta, OUT_DIR, WORK_DIR, PFF_DIR

ROOT = Path(__file__).parent.parent.parent
DATA_DIR = ROOT / "data"
SB_MATCHES = DATA_DIR / "raw" / "matches" / "43_106.parquet"
SB_EVENTS = DATA_DIR / "raw" / "events"
SUMMARY_PLAYERS = DATA_DIR / "pff_task36_players.json"
SUMMARY_CLOCK = DATA_DIR / "pff_task36_clock.json"

PAIR_WINDOW_S = 10.0
SPREAD_FLAG_S = 2.0
NAME_CONFIRM = 0.6
PLAY_PERIODS = (1, 2, 3, 4)


def norm(name) -> str:
    if name is None or (isinstance(name, float) and np.isnan(name)):
        return ""
    s = unicodedata.normalize("NFKD", str(name))
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"[^a-zA-Z\s]", " ", s)
    return " ".join(s.lower().split())


def name_score(pff_name: str, sb_names: list) -> float:
    a = norm(pff_name)
    best = 0.0
    for b in map(norm, sb_names):
        if not a or not b:
            continue
        if set(a.split()) <= set(b.split()) or set(b.split()) <= set(a.split()):
            return 1.0
        best = max(best, difflib.SequenceMatcher(None, a, b).ratio())
    return best


def crosswalk() -> pd.DataFrame:
    pff = json.loads((DATA_DIR / "pff_matches.json").read_text())
    sbm = pd.read_parquet(SB_MATCHES, columns=["match_id", "match_date", "home_team", "away_team"])
    rows = []
    for p in pff:
        c = sbm[sbm["match_date"].astype(str) == p["date"]]
        h, a = c["home_team"].str.lower(), c["away_team"].str.lower()
        ph, pa = p["home"].lower(), p["away"].lower()
        hit = c[((h == ph) & (a == pa)) | ((h == pa) & (a == ph))]
        rows.append({"pff_game_id": int(p["pff_id"]),
                     "statsbomb_match_id": int(hit["match_id"].iloc[0]) if len(hit) == 1 else None,
                     "date": p["date"], "pff_home": p["home"], "pff_away": p["away"], "n_candidates": len(hit)})
    return pd.DataFrame(rows)


def sb_lineups(mid: int) -> pd.DataFrame:
    from statsbombpy import sb
    import requests
    import requests_cache
    requests_cache.uninstall_cache()
    if not getattr(requests.get, "_timeout_patched", False):
        orig = requests.get

        def get(*a, **k):
            k.setdefault("timeout", 30)
            return orig(*a, **k)
        get._timeout_patched = True
        requests.get = get
    for attempt in range(3):
        try:
            lu = sb.lineups(match_id=mid)
            break
        except Exception:
            if attempt == 2:
                raise
    rows = []
    for team, df in lu.items():
        for _, r in df.iterrows():
            rows.append({"team": team, "sb_player_id": int(r["player_id"]), "sb_name": r["player_name"],
                         "sb_nickname": r.get("player_nickname"), "jersey": str(int(r["jersey_number"]))})
    return pd.DataFrame(rows)


def map_players(gid: int, mid: int) -> tuple:
    roster = json.loads((PFF_DIR / "Rosters" / f"{gid}.json").read_text())
    lu = sb_lineups(mid)
    rows = []
    for r in roster:
        team, shirt = r["team"]["name"], str(r["shirtNumber"])
        hit = lu[(lu["team"].str.lower() == team.lower()) & (lu["jersey"] == shirt)]
        rec = {"pff_game_id": gid, "statsbomb_match_id": mid, "team": team, "shirt": shirt,
               "pff_player_id": int(r["player"]["id"]), "pff_name": r["player"]["nickname"],
               "started": r.get("started"), "n_sb_candidates": len(hit)}
        if len(hit) == 1:
            h = hit.iloc[0]
            score = name_score(rec["pff_name"], [h["sb_name"], h["sb_nickname"]])
            rec.update({"sb_player_id": int(h["sb_player_id"]), "sb_name": h["sb_name"], "name_score": score,
                        "status": "mapped" if score >= NAME_CONFIRM else "ambiguous_name"})
        else:
            rec.update({"sb_player_id": None, "sb_name": None, "name_score": None,
                        "status": "no_team_shirt_match" if len(hit) == 0 else "multiple_team_shirt_matches"})
        rows.append(rec)
    out = pd.DataFrame(rows)
    unused = lu[~lu["sb_player_id"].isin(out["sb_player_id"].dropna().astype(int))]
    return out, unused.assign(statsbomb_match_id=mid)


def stage_players():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    cw = crosswalk()
    n_ok = int(cw["statsbomb_match_id"].notna().sum())
    print(f"(a) crosswalk: {n_ok}/{len(cw)} matched unambiguously")
    assert n_ok == 64 and len(cw) == 64 and cw["statsbomb_match_id"].is_unique
    cw["statsbomb_match_id"] = cw["statsbomb_match_id"].astype(int)
    cw[["pff_game_id", "statsbomb_match_id", "date", "pff_home", "pff_away"]].to_csv(OUT_DIR / "crosswalk.csv", index=False)

    maps, unused = [], []
    for _, r in cw.iterrows():
        m, u = map_players(int(r["pff_game_id"]), int(r["statsbomb_match_id"]))
        maps.append(m)
        unused.append(u)
        print(f"  {r['pff_game_id']}->{r['statsbomb_match_id']}: mapped {(m['status'] == 'mapped').sum()}/{len(m)}")
    pmap = pd.concat(maps, ignore_index=True)
    pmap.to_csv(OUT_DIR / "player_map.csv", index=False)
    unused = pd.concat(unused, ignore_index=True)
    summary = {"crosswalk_matched": n_ok, "n_roster_entries": len(pmap),
               "status_counts": pmap["status"].value_counts().to_dict(),
               "share_mapped": float((pmap["status"] == "mapped").mean()),
               "not_mapped": pmap[pmap["status"] != "mapped"].to_dict("records"),
               "n_sb_lineup_players_not_in_pff_roster": len(unused),
               "sb_lineup_players_not_in_pff_roster": unused.to_dict("records")}
    SUMMARY_PLAYERS.write_text(json.dumps(summary, indent=2, default=str))
    print(f"  share mapped: {summary['share_mapped']:.4f}; status: {summary['status_counts']}")


def ts_seconds(ts: str) -> float:
    h, m, s = ts.split(":")
    return int(h) * 3600 + int(m) * 60 + float(s)


def sb_shots(mid: int) -> pd.DataFrame:
    ev = pd.read_parquet(SB_EVENTS / f"{mid}.parquet", columns=["id", "type", "period", "timestamp", "minute", "second",
                                                                  "team", "player_id", "location"])
    s = ev[(ev["type"] == "Shot") & ev["period"].isin(PLAY_PERIODS)].copy()
    s["sb_clock"] = s["timestamp"].map(ts_seconds)
    return s.rename(columns={"id": "sb_event_id"}).drop(columns=["type", "timestamp"])


def pair(pff: pd.DataFrame, sb: pd.DataFrame) -> pd.DataFrame:
    cands = []
    for i, p in pff.iterrows():
        for j, s in sb[(sb["period"] == p["period"]) & (sb["team"].str.lower() == str(p["team"]).lower())].iterrows():
            gap = abs(s["sb_clock"] - p["pff_clock"])
            if gap <= PAIR_WINDOW_S:
                cands.append((gap, i, j))
    used_p, used_s, out = set(), set(), []
    for gap, i, j in sorted(cands):
        if i in used_p or j in used_s:
            continue
        used_p.add(i)
        used_s.add(j)
        out.append({**pff.loc[i].to_dict(), **sb.loc[j].drop(["period", "team"]).to_dict()})
    df = pd.DataFrame(out)
    if len(df):
        df["offset"] = df["sb_clock"] - df["pff_clock"]
    return df


def clock_summary(pairs: pd.DataFrame) -> dict:
    if len(pairs) == 0:
        return {"n_paired": 0}
    o = pairs["offset"]
    match_min = pairs["minute"] + pairs["second"] / 60
    slope = float(np.polyfit(match_min, o, 1)[0]) if len(pairs) >= 3 and match_min.nunique() > 1 else None
    return {"n_paired": len(pairs), "median": float(o.median()),
            "iqr": float(o.quantile(0.75) - o.quantile(0.25)),
            "min": float(o.min()), "max": float(o.max()), "spread": float(o.max() - o.min()),
            "flag_spread_gt_2s": bool(o.max() - o.min() > SPREAD_FLAG_S),
            "per_period_median": {int(k): float(v) for k, v in pairs.groupby("period")["offset"].median().items()},
            "per_period_n": {int(k): int(v) for k, v in pairs.groupby("period").size().items()},
            "slope_s_per_min": slope}


def period_offsets(pairs: pd.DataFrame, periods) -> dict:
    """Median offset per period; the match median where a period has no pair."""
    med = float(pairs["offset"].median()) if len(pairs) else np.nan
    per = pairs.groupby("period")["offset"].median().to_dict() if len(pairs) else {}
    return {int(p): (float(per[p]), "period") if p in per else (med, "match_median") for p in periods}


def stage_clock():
    cw = pd.read_csv(OUT_DIR / "crosswalk.csv")
    clock, pairs_all, offsets_used, coord_rows = {}, [], {}, []
    for _, r in cw.iterrows():
        gid, mid = int(r["pff_game_id"]), int(r["statsbomb_match_id"])
        meta = load_meta(gid)
        ps = pd.read_parquet(WORK_DIR / f"{gid}_pff_shots.parquet")
        ps = ps[ps["period"].isin(PLAY_PERIODS)].reset_index(drop=True)
        ss = sb_shots(mid)
        pairs = pair(ps, ss)
        cs = clock_summary(pairs)
        cs.update({"n_pff_shots": len(ps), "n_sb_shots": len(ss)})
        clock[gid] = cs

        frame_path = OUT_DIR / f"{mid}.parquet"
        fr = pd.read_parquet(frame_path)
        offs = period_offsets(pairs, sorted(fr["period"].unique()))
        offsets_used[gid] = {str(k): {"offset": v[0], "source": v[1]} for k, v in offs.items()}
        fr["time_sb"] = fr["pff_clock"] + fr["period"].map({k: v[0] for k, v in offs.items()})
        fr.to_parquet(frame_path)

        if len(pairs):
            snap = pd.read_parquet(WORK_DIR / f"{gid}_shot_snapshots.parquet")
            home = meta["homeTeam"]["name"]
            for _, pr in pairs.iterrows():
                p = int(pr["period"])
                target = pr["sb_clock"] - offs[p][0]
                sp = snap[snap["period"] == p]
                if len(sp) == 0:
                    continue
                t_near = sp.loc[(sp["pff_clock"] - target).abs().idxmin(), "pff_clock"]
                f = sp[sp["pff_clock"] == t_near]
                side = "home" if str(pr["team"]).lower() == home.lower() else "away"
                sign = attack_sign(meta, side, p)
                rec = {"pff_game_id": gid, "statsbomb_match_id": mid, "period": p, "team": pr["team"],
                       "frame_gap_s": float(abs(t_near - target)), "sb_x": pr["location"][0], "sb_y": pr["location"][1]}
                ball = f[f["side"] == "ball"]
                if len(ball):
                    bx, by = to_sb(ball["x"].iloc[0], ball["y"].iloc[0], sign, meta)
                    rec.update({"ball_x": bx, "ball_y": by, "d_ball": float(np.hypot(bx - rec["sb_x"], by - rec["sb_y"])),
                                "ball_visibility": ball["visibility"].iloc[0]})
                shooter = f[(f["side"] == side) & (f["jersey"] == str(pr["shooter_jersey"]))]
                if len(shooter):
                    sx, sy = to_sb(shooter["x"].iloc[0], shooter["y"].iloc[0], sign, meta)
                    rec.update({"shooter_x": sx, "shooter_y": sy,
                                "d_shooter": float(np.hypot(sx - rec["sb_x"], sy - rec["sb_y"])),
                                "shooter_visibility": shooter["visibility"].iloc[0]})
                coord_rows.append(rec)
            pairs_all.append(pairs.assign(pff_game_id=gid, statsbomb_match_id=mid))
        print(f"  {gid}->{mid}: pff={len(ps)} sb={len(ss)} paired={cs['n_paired']} median={cs.get('median')} "
              f"spread={cs.get('spread')} slope={cs.get('slope_s_per_min')}")

    pairs_df = pd.concat(pairs_all, ignore_index=True)
    pairs_df["location"] = pairs_df["location"].map(list)
    pairs_df.to_parquet(OUT_DIR / "shot_pairs.parquet")
    coord = pd.DataFrame(coord_rows)
    coord.to_parquet(OUT_DIR / "shot_coordinate_check.parquet")
    q = [0.1, 0.25, 0.5, 0.75, 0.9]

    def dist_summary(col):
        s = coord[col].dropna()
        return {"n": len(s), **{f"q{int(x*100)}": float(s.quantile(x)) for x in q},
                "share_le_2": float((s <= 2).mean()), "share_le_5": float((s <= 5).mean())}

    summary = {"n_pairs_total": len(pairs_df), "clock": {str(k): v for k, v in clock.items()},
               "offsets_used": {str(k): v for k, v in offsets_used.items()},
               "coord_check": {"d_ball": dist_summary("d_ball"), "d_shooter": dist_summary("d_shooter"),
                               "frame_gap_s_max": float(coord["frame_gap_s"].max())}}
    SUMMARY_CLOCK.write_text(json.dumps(summary, indent=2, default=str))
    print(f"  coord check: {summary['coord_check']}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", choices=["players", "clock"], required=True)
    stage_players() if ap.parse_args().stage == "players" else stage_clock()
