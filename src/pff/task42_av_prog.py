"""
Task 42, Step 3 (C): progressive availability on PFF WC2022.
docs/specs/task-42-improvement-round-2.md.

AV_prog: Task 38's AVAILABLE AND the teammate is at least 5 m nearer the
opponent goal than the ball. The teammate's and ball's x in the passing
team's attacking frame (metres, centre origin: sign x PFF x, with Task
36's attack_sign) are re-derived from the same PFF event snapshots for each
Task 38 moment (Task 38's moments file is not modified). Baseline refit
with availability.fit_oof (Task 38's settings); R1 and R2 via
availability_tests; praised list via Task 41's perm_test (>= 300 moments,
Task 32 roles via the player map).

Run: python src/pff/task42_av_prog.py
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import xgboost as xgb

sys.path.insert(0, str(Path(__file__).parent.parent / "engine_v2"))
import availability as av  # noqa: E402
import availability_tests as avt  # noqa: E402
from frames import attack_sign, load_meta  # noqa: E402
from task33_step3_f_state import XGB_REGRESSOR_KWARGS  # noqa: E402
from task32_step4 import assign_roles  # noqa: E402
from task27_step1_deep_midfield import name_matches  # noqa: E402
from task41_lists_availability import perm_test, LIST_L, MIN_PFF_MOMENTS  # noqa: E402

DATA_DIR = Path(__file__).parent.parent.parent / "data"
LEADERBOARD_V5C_PATH = DATA_DIR / "processed" / "leaderboard_v5c.parquet"
SUMMARY_PATH = DATA_DIR / "pff_task42_step3.json"
SEED = 20260928
PROG_M = 5.0


def attacking_x(mom: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for gid, g in mom.groupby("pff_game_id"):
        meta = load_meta(int(gid))
        events = json.loads((av.EVENTS_DIR / f"{gid}.json").read_text())
        for idx, gg in g.groupby("event_idx"):
            e = events[int(idx)]
            side, period = gg["side"].iloc[0], int(gg["period"].iloc[0])
            sign = attack_sign(meta, side, period)
            ball = e["ball"][0]
            mates = e["homePlayers"] if side == "home" else e["awayPlayers"]
            pos = {int(m["playerId"]): (m["x"], m["y"]) for m in mates if m.get("x") is not None}
            for pid in gg["pff_player_id"]:
                mx, my = pos[int(pid)]
                rows.append((gid, idx, pid, sign * mx, sign * ball["x"], float(np.hypot(mx - ball["x"], my - ball["y"]))))
    return pd.DataFrame(rows, columns=["pff_game_id", "event_idx", "pff_player_id", "mate_x_att", "ball_x_att", "d_ball_chk"])


def main():
    print("Task 42 Step 3: progressive availability ...")
    mom = pd.read_parquet(av.MOMENTS_PATH)
    rec = pd.read_parquet(av.RECEPTIONS_PATH)
    cw = pd.read_csv(av.OUT_DIR / "crosswalk.csv")
    ax = attacking_x(mom)
    mom = mom.merge(ax, on=["pff_game_id", "event_idx", "pff_player_id"], how="left")
    assert mom["mate_x_att"].notna().all()
    assert np.allclose(mom["d_ball"], mom["d_ball_chk"], atol=1e-9)
    mom["prog"] = (mom["mate_x_att"] - mom["ball_x_att"]) >= PROG_M
    mom["available_base"] = mom["available"]
    mom["available"] = (mom["available_base"].astype(bool) & mom["prog"]).astype(int)

    folds = av.match_folds(sorted(cw["pff_game_id"].astype(int)))
    mom["p_prog"], auc = av.fit_oof(mom, folds)
    mom["av_prog"] = mom["available"] - mom["p_prog"]
    step1 = {"n_moments": len(mom), "share_prog": float(mom["prog"].mean()),
             "base_rate_av_prog": float(mom["available"].mean()), "base_rate_av_task38": float(mom["available_base"].mean()),
             "baseline_oof_auc": auc,
             "p_target_given_av_prog": float(mom.loc[mom["available"] == 1, "is_target"].mean()),
             "p_target_given_not": float(mom.loc[mom["available"] == 0, "is_target"].mean())}
    print(f"  {step1}")

    pm = avt.player_map()
    mom_for_dm = mom.assign(av=mom["av_prog"])
    dm_ids, _ = avt.dm_group(mom_for_dm, pm, cw)
    r1 = {"DM": avt.r1(mom, "av_prog", dm_ids), "all_outfield": avt.r1(mom, "av_prog")}
    r1["pass_DM"] = bool(r1["DM"]["median"] >= 0.60)

    oof = np.full(len(rec), np.nan)
    for k in range(av.N_FOLDS):
        tr, te = (rec["fold"] != k).values, (rec["fold"] == k).values
        mdl = xgb.XGBRegressor(**XGB_REGRESSOR_KWARGS).fit(rec.loc[tr, avt.G_FEATURES].astype(float), rec.loc[tr, "y_net_xg"])
        oof[te] = mdl.predict(rec.loc[te, avt.G_FEATURES].astype(float))
    rec["g_oof"] = oof
    r2 = avt.r2(rec, mom, "av_prog", dm_ids)
    for k in ("PRIMARY_all_outfield", "DM_report"):
        r = r2[k]
        print(f"  R2 {k}: n={r['n_rows']} players={r['n_players']} coef100={r['coef_per_sd_per100']:+.4f} "
              f"CI={[round(x, 4) for x in r['ci95_per100']]} p={r['p']:.4g} MDE={r['mde_80_per100']:.4f}")
    print(f"  R1: {r1}")

    lb = pd.read_parquet(LEADERBOARD_V5C_PATH, columns=["player_id", "player_name"])
    roles = assign_roles(set(lb["player_id"])).set_index("player_id")["role"]
    names = lb.set_index("player_id")["player_name"].to_dict()
    l_ids = {lb.loc[lb["player_name"].apply(lambda f: name_matches(nm, f)), "player_id"].iloc[0] for nm in LIST_L}
    pff2sb = pm.drop_duplicates("pff_player_id").set_index("pff_player_id")["sb_player_id"]
    a = mom.groupby("pff_player_id")["av_prog"].agg(["mean", "size"])
    a = a[a["size"] >= MIN_PFF_MOMENTS]
    vals = pd.DataFrame({"sb_player_id": a.index.map(pff2sb).astype(float), "m": a["mean"].values})
    vals["role"] = vals["sb_player_id"].map(roles)
    r3 = perm_test(vals.dropna(subset=["role"]), l_ids, np.random.default_rng(SEED))
    r3["present_names"] = [names.get(r["sb_player_id"]) for r in r3.get("present", [])]
    print(f"  praised list: present={r3['n_present']} T={r3.get('T')} p={r3.get('p_two_sided')}")

    SUMMARY_PATH.write_text(json.dumps({"step": step1, "n_dm": len(dm_ids), "r1": r1, "r2": r2, "praised_list": r3},
                                       indent=2, default=str))
    print(f"Wrote {SUMMARY_PATH}")


if __name__ == "__main__":
    main()
