"""
Task 36, Steps 2 and 4 (plus the inputs for Step 3(b)/(d)): one streaming
pass over each PFF tracking file, one match in memory at a time.
docs/specs/task-36-pff-ingest.md.

Step 2 audit (src/audit_pff.py's logic, generalised; the original is not
modified): frames, fps (metadata and implied within periods), periods,
ball-present share, player-frame visibility and confidence shares,
coordinate bounds, plus max |periodElapsedTime - (videoTime -
startPeriod)| where the metadata has startPeriod.

Step 4 table, data/processed/pff/<statsbomb_match_id>.parquet, one row per
(kept frame, player), periods 1-4:
  - frames kept at 5 fps: per period, the frame nearest each 0.2 s step of
    periodElapsedTime;
  - x/y converted from PFF metres (centre origin, pitch L x W from
    metadata) to StatsBomb units (120 x 80, corner origin), in the
    player's OWN team's attacking frame (team-relative, Task 24); ball in
    the same row's team frame;
  - vx/vy from the raw 30 fps positions (not the *Smoothed arrays):
    backward difference over the previous 3 raw frames in which the player
    appears (~0.1 s), dt <= 0.2 s, else NaN; StatsBomb units per second;
  - pff_clock = periodElapsedTime; align.py --stage clock adds time_sb.
Also writes, under data/processed/pff/_work/: each PFF shot's tracking
clock, and raw 30 fps rows within 12 s of each PFF shot (for Step 3(d)).

Run: python src/pff/frames.py   (after align.py --stage players)
"""
import bz2
import json
import sys
import time
from collections import defaultdict, deque
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).parent.parent.parent
DATA_DIR = ROOT / "data"
PFF_DIR = DATA_DIR / "raw_pff"
EVENTS_DIR = PFF_DIR / "Event Data"  # top-level version (ships with the v2.5 spec); see results page
OUT_DIR = DATA_DIR / "processed" / "pff"
WORK_DIR = OUT_DIR / "_work"
SUMMARY_PATH = DATA_DIR / "pff_task36_audit.json"

STEP_S = 0.2
VEL_LAG = 3
VEL_MAX_DT = 0.2
SHOT_WINDOW_S = 12.0
PERIODS = (1, 2, 3, 4)


def load_meta(gid: int) -> dict:
    m = json.loads((PFF_DIR / "Metadata" / f"{gid}.json").read_text())
    return m[0] if isinstance(m, list) else m


def pitch(meta: dict) -> tuple:
    p = meta["stadium"]["pitches"][0]
    return float(p["length"]), float(p["width"])


def attack_sign(meta: dict, side: str, period: int) -> int:
    """+1 if `side` attacks toward PFF +x in `period`."""
    left = meta["homeTeamStartLeft"] if period in (1, 2) else meta.get("homeTeamStartLeftExtraTime")
    if left is None:
        return 0
    home = 1 if left else -1
    if period in (2, 4):
        home = -home
    return home if side == "home" else -home


def to_sb(x, y, sign: int, meta: dict) -> tuple:
    L, W = pitch(meta)
    x, y = np.asarray(x, dtype=float), np.asarray(y, dtype=float)
    if sign == 1:
        return (x + L / 2) * 120 / L, (W / 2 - y) * 80 / W
    if sign == -1:
        return (L / 2 - x) * 120 / L, (y + W / 2) * 80 / W
    return np.full_like(x, np.nan), np.full_like(y, np.nan)


def _self_check():
    meta = {"stadium": {"pitches": [{"length": 105.0, "width": 68.0}]}}
    assert np.allclose(to_sb(-52.5, 34, 1, meta), (0, 0)) and np.allclose(to_sb(52.5, -34, 1, meta), (120, 80))
    assert np.allclose(to_sb(0, 0, 1, meta), (60, 40)) and np.allclose(to_sb(0, 0, -1, meta), (60, 40))
    assert np.allclose(to_sb(52.5, 34, -1, meta), (0, 80))
    # the same physical point seen by the two teams is rotated 180 degrees
    a, b = to_sb(20.0, 10.0, 1, meta), to_sb(20.0, 10.0, -1, meta)
    assert np.allclose((a[0] + b[0], a[1] + b[1]), (120, 80))


def pff_shots(gid: int, roster: list) -> list:
    shirt = {int(r["player"]["id"]): str(r["shirtNumber"]) for r in roster}
    out = []
    for e in json.loads((EVENTS_DIR / f"{gid}.json").read_text()):
        pe, ge = e.get("possessionEvents") or {}, e.get("gameEvents") or {}
        if pe.get("possessionEventType") == "SH":
            sid = pe.get("shooterPlayerId")
            out.append({"video_time": float(e["startTime"]), "event_period": ge.get("period"), "team": ge.get("teamName"),
                        "shooter_pff_id": sid, "shooter_jersey": shirt.get(int(sid)) if sid is not None else None})
    return out


def process_match(gid: int, mid: int, pmap: pd.DataFrame) -> dict:
    meta = load_meta(gid)
    home, away = meta["homeTeam"]["name"], meta["awayTeam"]["name"]
    roster = json.loads((PFF_DIR / "Rosters" / f"{gid}.json").read_text())
    idmap = {(t.lower(), str(s)): p for t, s, p in pmap[["team", "shirt", "sb_player_id"]].itertuples(index=False)}
    team_of = {"home": home, "away": away}
    L, W = pitch(meta)
    shots = pff_shots(gid, roster)
    shot_best = [(np.inf, None, None) for _ in shots]
    shot_vt = np.array([s["video_time"] for s in shots]) if shots else np.array([])

    n_frames, per_period = 0, defaultdict(lambda: [0, np.inf, -np.inf])
    ball_frames, vis, conf = 0, defaultdict(int), defaultdict(int)
    bounds = [np.inf, -np.inf, np.inf, -np.inf]
    clock_dev, n_other_period, n_null_clock = 0.0, 0, 0
    n_dup_vt, prev_vt = 0, None
    hist = defaultdict(lambda: deque(maxlen=VEL_LAG + 1))
    cols = defaultdict(list)
    snap = defaultdict(list)
    pending = None  # (key, dist, frame_record)

    def emit(rec):
        period, clk, vt, ball, players = rec
        for side, jersey, x, y, v, c, vx_m, vy_m in players:
            sign = attack_sign(meta, side, period)
            sx, sy = to_sb(x, y, sign, meta)
            bx, by = to_sb(ball[0], ball[1], sign, meta) if ball else (np.nan, np.nan)
            cols["period"].append(period); cols["pff_clock"].append(clk); cols["video_time"].append(vt)
            cols["side"].append(side); cols["team"].append(team_of[side]); cols["jersey"].append(jersey)
            cols["player_id"].append(idmap.get((team_of[side].lower(), jersey)))
            cols["x"].append(float(sx)); cols["y"].append(float(sy))
            cols["vx"].append(sign * vx_m * 120 / L if sign else np.nan)
            cols["vy"].append(-sign * vy_m * 80 / W if sign else np.nan)
            cols["visibility"].append(v); cols["confidence"].append(c)
            cols["ball_x"].append(float(bx)); cols["ball_y"].append(float(by))
            cols["ball_visibility"].append(ball[2] if ball else None)

    with bz2.open(PFF_DIR / "Tracking Data" / f"{gid}.jsonl.bz2", "rt") as f:
        for line in f:
            fr = json.loads(line)
            n_frames += 1
            period, clk, vt = fr.get("period"), fr.get("periodElapsedTime"), fr["videoTimeMs"] / 1000.0
            n_dup_vt += int(vt == prev_vt)
            prev_vt = vt
            pp = per_period[period]
            pp[0] += 1; pp[1] = min(pp[1], vt); pp[2] = max(pp[2], vt)
            balls = fr.get("balls") or []
            ball = (balls[0]["x"], balls[0]["y"], balls[0].get("visibility")) if balls else None
            if ball:
                ball_frames += 1
            players = []
            for side, key in (("home", "homePlayers"), ("away", "awayPlayers")):
                for p in fr.get(key) or []:
                    vis[p["visibility"]] += 1
                    conf[p["confidence"]] += 1
                    x, y = p["x"], p["y"]
                    bounds[0], bounds[1] = min(bounds[0], x), max(bounds[1], x)
                    bounds[2], bounds[3] = min(bounds[2], y), max(bounds[3], y)
                    h = hist[(side, str(p["jerseyNum"]))]
                    if h and vt - h[-1][0] > VEL_MAX_DT:
                        h.clear()
                    h.append((vt, x, y))
                    if len(h) == VEL_LAG + 1 and 0 < vt - h[0][0] <= VEL_MAX_DT:
                        dt = vt - h[0][0]
                        vxm, vym = (x - h[0][1]) / dt, (y - h[0][2]) / dt
                    else:
                        vxm = vym = np.nan
                    players.append((side, str(p["jerseyNum"]), x, y, p["visibility"], p["confidence"], vxm, vym))
            if period not in PERIODS:
                n_other_period += 1
                continue
            if clk is None:
                n_null_clock += 1
                continue
            start = meta.get(f"startPeriod{period}")
            if start is not None:
                clock_dev = max(clock_dev, abs(clk - (vt - start)))

            if len(shot_vt):
                d = np.abs(shot_vt - vt)
                for i in np.where(d < 0.5)[0]:
                    if d[i] < shot_best[i][0]:
                        shot_best[i] = (d[i], period, clk)
                if (d <= SHOT_WINDOW_S).any():
                    for side, jersey, x, y, v, c, _, _ in players:
                        for k, val in zip(("period", "pff_clock", "side", "jersey", "x", "y", "visibility"),
                                          (period, clk, side, jersey, x, y, v)):
                            snap[k].append(val)
                    if ball:
                        for k, val in zip(("period", "pff_clock", "side", "jersey", "x", "y", "visibility"),
                                          (period, clk, "ball", None, ball[0], ball[1], ball[2])):
                            snap[k].append(val)

            g = round(clk / STEP_S)
            key, dist = (period, g), abs(clk - g * STEP_S)
            if pending is None or pending[0] != key:
                if pending is not None:
                    emit(pending[2])
                pending = (key, dist, (period, clk, vt, ball, players))
            elif dist < pending[1]:
                pending = (key, dist, (period, clk, vt, ball, players))
    if pending is not None:
        emit(pending[2])

    df = pd.DataFrame(cols)
    out_path = OUT_DIR / f"{mid}.parquet"
    df.to_parquet(out_path)
    pd.DataFrame(snap).to_parquet(WORK_DIR / f"{gid}_shot_snapshots.parquet")
    sh = pd.DataFrame(shots)
    if len(sh):
        sh["frame_gap_s"] = [b[0] for b in shot_best]
        sh["period"] = [b[1] for b in shot_best]
        sh["pff_clock"] = [b[2] for b in shot_best]
    sh.to_parquet(WORK_DIR / f"{gid}_pff_shots.parquet")

    n_pf = sum(vis.values())
    fps_implied = {int(k): v[0] / (v[2] - v[1]) for k, v in per_period.items()
                   if k in PERIODS and v[2] > v[1]}
    return {"pff_game_id": gid, "statsbomb_match_id": mid, "home": home, "away": away,
            "n_frames": n_frames, "fps_meta": meta.get("fps"), "fps_implied_by_period": fps_implied,
            "periods": sorted(int(k) for k in per_period if k is not None),
            "frames_by_period": {str(k): v[0] for k, v in per_period.items()},
            "n_frames_other_period": n_other_period, "n_duplicate_video_time": n_dup_vt, "n_frames_null_clock": n_null_clock,
            "ball_present_share": ball_frames / n_frames,
            "visible_share": vis.get("VISIBLE", 0) / n_pf, "estimated_share": vis.get("ESTIMATED", 0) / n_pf,
            "visibility_counts": dict(vis), "confidence_counts": dict(conf),
            "confidence_shares": {k: v / n_pf for k, v in conf.items()},
            "x_min": bounds[0], "x_max": bounds[1], "y_min": bounds[2], "y_max": bounds[3],
            "pitch_length": L, "pitch_width": W,
            "max_clock_dev_vs_meta_s": clock_dev if any(meta.get(f"startPeriod{p}") is not None for p in (1, 2)) else None,
            "n_pff_shots": len(shots), "n_pff_shots_without_frame": int(sum(b[1] is None for b in shot_best)),
            "rows_out": len(df), "frames_out": int(df.groupby(["period", "pff_clock"]).ngroups) if len(df) else 0,
            "bytes_out": out_path.stat().st_size,
            "rows_unmapped_player": int(df["player_id"].isna().sum()) if len(df) else 0,
            "tracking_bytes": (PFF_DIR / "Tracking Data" / f"{gid}.jsonl.bz2").stat().st_size}


def main():
    _self_check()
    WORK_DIR.mkdir(parents=True, exist_ok=True)
    cw = pd.read_csv(OUT_DIR / "crosswalk.csv")
    pmap = pd.read_csv(OUT_DIR / "player_map.csv")
    pmap = pmap[pmap["status"] == "mapped"]
    audit = json.loads(SUMMARY_PATH.read_text()) if SUMMARY_PATH.exists() else {}
    for _, r in cw.iterrows():
        gid, mid = int(r["pff_game_id"]), int(r["statsbomb_match_id"])
        if str(gid) in audit and (OUT_DIR / f"{mid}.parquet").exists():
            continue  # resume after an interruption
        t0 = time.time()
        pm = pmap[pmap["pff_game_id"] == gid].assign(shirt=lambda d: d["shirt"].astype(str))
        audit[str(gid)] = process_match(gid, mid, pm)
        SUMMARY_PATH.write_text(json.dumps(audit, indent=2, default=str))
        a = audit[str(gid)]
        print(f"  {gid}->{mid}: frames={a['n_frames']} rows_out={a['rows_out']} est={a['estimated_share']:.3f} "
              f"ball={a['ball_present_share']:.3f} ({time.time() - t0:.0f}s)", flush=True)


if __name__ == "__main__":
    sys.exit(main())
