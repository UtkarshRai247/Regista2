"""
Task 51: the regista scorecard (descriptive; no new measures, no claims).
docs/specs/task-51-regista-scorecard.md.

Card A (2015/16, Task 44's 185 DMs): PR2_flag_keep, A1 (Task 45), W (Task
  46; rebuilt with task46_part_b.fit_w because the table was never saved),
  HOLD_VARIATION, MOVE_ON_SPEED (Task 44 tempo residuals).
Card B (study, Task 27's 111 DMs): Decision (v5 cross-fitted), PR2_flag_keep
  (Task 46's study version), W (rebuilt as Task 46), RQ_rel (Task 34),
  HOLD_VARIATION / MOVE_ON_SPEED (Task 26's corrected-coordinate tempo,
  regenerated with match ids as Task 39 did, into new tempo_task51_* files),
  AV (Task 38, PFF WC2022, >= 300 moments).
Card C (reserved, second use): DMs with >= 5 La Liga seasons with >= 50
  pressured receptions each; PR2_flag_keep per season with 90% intervals.

Per player x dimension: n; raw value; Task 29 shrinkage within the card's
group (estimate_sigma2w_rho -> v_i with design effect -> DerSimonian-Laird
-> shrink, 90%), fitted on the players meeting the floor; percentile of the
shrunken value in the group; CLEARLY ABOVE / CLEARLY BELOW when the 90%
interval excludes the DL group mean, else CAN'T TELL; below the floor ->
"not enough data". HOLD_VARIATION is a per-player SD: Task 29's per-unit-mean
method does not apply (Task 44 said so; unresolved), so it gets n, raw SD and
the percentile of the raw SD, no interval.
RQ_rel within-DM reliability on Card B: Task 38's R1 (availability_tests.r1:
>= 4 matches, 100 random match half-splits, Spearman-Brown median).

Run: python src/engine_v2/task51_scorecard.py
"""
import json
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent / "pff"))
sys.path.append(str(Path(__file__).parent.parent / "tempo"))
import availability as av  # noqa: E402
import availability_tests as avt  # noqa: E402
import redesign_metrics_v2  # noqa: E402,F401 -- applies Task 26 Step 2's patch to redesign_metrics
import redesign_metrics as rm  # noqa: E402
import task44_build as tb  # noqa: E402
from crossfit import FOLDS_PATH  # noqa: E402
from task28_step1_2 import estimate_sigma2w_rho  # noqa: E402
from task29_step1_2 import dersimonian_laird, shrink, Z_90  # noqa: E402
from task44_gate import receipt_flags, EV_DIR  # noqa: E402
from task46_part_b import fit_w  # noqa: E402
from task27_step1_deep_midfield import name_matches  # noqa: E402
from task41_lists_availability import LIST_L  # noqa: E402
from task39_tempo_ptest import V2_MOVE, V2_HOLD  # noqa: E402
from task50_robustness import mem_gate, MEM_LOG  # noqa: E402

warnings.filterwarnings("ignore")

DATA_DIR = Path(__file__).parent.parent.parent / "data"
PROC = DATA_DIR / "processed"
E2 = PROC / "engine_v2"
OUT = {c: PROC / f"scorecard_card_{c.lower()}.parquet" for c in ("A", "B", "C")}
SUMMARY_PATH = DATA_DIR / "engine_v2_task51.json"
TASK46 = json.loads((DATA_DIR / "engine_v2_task46_part_b.json").read_text())
LA_LIGA, MIN_SEASONS, MIN_PR = 11, 5, 50
TEMPO_FLOOR = 200  # preregistered tempo floor: src/tempo/reliability.py GATE_THRESHOLD

# Tiers and within-DM reliabilities, fixed by the brief; reliabilities cited from existing pages.
T1, T2, T3 = "TIER 1", "TIER 2", "TIER 3"
REL = {
    "PR2_flag_keep": (0.666, "docs/results/44-big-five-1516.md:120 (2015/16 DMs, 185)"),
    "A1": (0.487, "docs/results/45-press-resistance-vetting.md:48 (2015/16 DMs, 185)"),
    "W": (0.802, "docs/results/46-movers-and-spatial-physical.md:73 (2015/16 DMs, 185)"),
    "HOLD_VARIATION": (0.730, "docs/results/44-big-five-1516.md:119 (2015/16 DMs, 185)"),
    "MOVE_ON_SPEED": (0.475, "docs/results/44-big-five-1516.md:118 (2015/16 DMs, 185)"),
    "Decision": (0.451, "docs/results/32-critique-diagnostics.md:265 (study DMs at 200 passes, 51 player-seasons)"),
    "AV": (0.740, "docs/results/38-availability.md:122 (WC2022 DMs, 28)"),
}
TIER = {"PR2_flag_keep": T1, "A1": T1, "W": T2, "HOLD_VARIATION": T2, "RQ_rel": T2, "AV": T2,
        "Decision": T3, "MOVE_ON_SPEED": T3}
NOTE = {"AV": "linked to FEWER chances in WC2022; exploratory",
        "Decision": "Tier 3: within-DM reliability ~0.45; its confirmed results link is carried by forwards",
        "MOVE_ON_SPEED": "Tier 3: within-DM reliability 0.475 in 2015/16",
        "A1": "team-adjusted press resistance, shown beside PR2_flag_keep",
        "HOLD_VARIATION": "per-player SD: Task 29's interval method does not apply; no interval shown"}


def score(units: pd.DataFrame, group: dict, floor: int, stat: str = "mean") -> tuple:
    """units: player_id, match_id, value. group: player_id -> name. Returns per-player rows and DL summary."""
    u = units[units["player_id"].isin(group)].dropna(subset=["value"])
    n = u.groupby("player_id").size().reindex(list(group), fill_value=0)
    ok = set(n.index[n >= floor])
    rows = pd.DataFrame({"player_id": list(group), "name": [group[p] for p in group], "n": n.values})
    uu = u[u["player_id"].isin(ok)]
    dl = None
    if stat == "sd":
        raw = uu.groupby("player_id")["value"].std(ddof=1)
        rows["raw"] = rows["player_id"].map(raw)
        rows["shrunken"] = rows["ci_low_90"] = rows["ci_high_90"] = np.nan
        rows["percentile"] = rows["raw"].rank(pct=True) * 100
        rows["label"] = np.where(rows["player_id"].isin(ok), "NO INTERVAL", "not enough data")
    else:
        pp = uu.rename(columns={"value": "decision_new"})[["player_id", "match_id", "decision_new"]]
        s2, rho, _ = estimate_sigma2w_rho(pp)
        g = pp.groupby("player_id")
        st = pd.DataFrame({"m_i": g["decision_new"].mean(), "n_i": g.size(), "G_i": g["match_id"].nunique()}).reset_index()
        st["v_i"] = s2 * (1 + (st["n_i"] / st["G_i"] - 1) * rho) / st["n_i"]
        d = dersimonian_laird(st["m_i"].values, st["v_i"].values)
        t = shrink(st, d["mu_w"], d["tau2"], "m_i", "v_i").set_index("player_id")
        dl = {**d, "sigma2_w": s2, "rho": rho, "n_players": len(t)}
        rows["raw"] = rows["player_id"].map(t["m_i"])
        for c in ("shrunken_i", "ci_low_90", "ci_high_90"):
            rows[c.replace("_i", "")] = rows["player_id"].map(t[c])
        rows["percentile"] = rows["shrunken"].rank(pct=True) * 100
        sv = np.sort(t["shrunken_i"].values)
        for c in ("ci_low_90", "ci_high_90"):  # interval end points on the percentile scale of the group's shrunken values
            rows[c + "_pct"] = [100 * np.searchsorted(sv, x, side="right") / len(sv) if pd.notna(x) else np.nan for x in rows[c]]
        rows["label"] = np.select([~rows["player_id"].isin(ok), rows["ci_low_90"] > d["mu_w"], rows["ci_high_90"] < d["mu_w"]],
                                  ["not enough data", "CLEARLY ABOVE", "CLEARLY BELOW"], "CAN'T TELL")
    return rows, dl


def card(name: str, group: dict, dims: list) -> tuple:
    out, summ = [], {}
    for dim, units, floor, stat, rel in dims:
        rows, dl = score(units, group, floor, stat)
        r, src = rel
        rows = rows.assign(card=name, dimension=dim, floor=floor, tier=TIER[dim], reliability=r, reliability_source=src,
                           note=NOTE.get(dim, ""))
        out.append(rows)
        summ[dim] = {"tier": TIER[dim], "reliability": r, "reliability_source": src, "floor": floor,
                     "n_meeting_floor": int((rows["label"] != "not enough data").sum()),
                     "counts": rows["label"].value_counts().to_dict(), "dl": dl}
        print(f"  {name} {dim}: {summ[dim]['counts']}", flush=True)
    return pd.concat(out, ignore_index=True), summ


def w_study() -> pd.DataFrame:
    folds = pd.read_csv(FOLDS_PATH)
    folds = folds[folds["match_id"].isin({int(p.stem) for p in EV_DIR.glob("*.parquet")})]
    fold_st = dict(zip(folds["match_id"], folds["fold"]))
    mids = sorted(fold_st)
    tb.EV16 = DATA_DIR / "raw" / "events"
    sd = pd.concat([tb.event_features(m)[["match_id", "event_id", "score_diff"]] for m in mids], ignore_index=True)
    rst = pd.concat([receipt_flags(m) for m in mids], ignore_index=True).merge(sd, on=["match_id", "event_id"], how="left")
    W, base = fit_w(rst, fold_st)
    return W, base


def tempo_study() -> tuple:
    """Task 39's tempo_residuals_with_ids, writing to new tempo_task51_* paths (earlier files untouched)."""
    rm.OUT_PATH = PROC / "tempo_task51_metrics.parquet"
    rm.MOVE_RESID_PATH = PROC / "tempo_task51_move_residuals.parquet"
    rm.HOLD_RESID_PATH = PROC / "tempo_task51_hold_residuals.parquet"
    rm.SUMMARY_PATH = DATA_DIR / "tempo_task51_redesign_rerun.json"
    _, move_df, hold_df, _ = rm.main()
    for new, old_path in ((move_df, V2_MOVE), (hold_df, V2_HOLD)):
        old = pd.read_parquet(old_path)
        assert len(new) == len(old)
        assert (new["player_id"].values == old["player_id"].values).all()
        assert np.allclose(new["residual"].values, old["residual"].values, rtol=0, atol=1e-12)
    return move_df, hold_df


def units(df, col, pid="player_id", mid="match_id"):
    return df[[pid, mid, col]].rename(columns={pid: "player_id", mid: "match_id", col: "value"})


def praised(group: dict) -> dict:
    out = {}
    for nm in LIST_L:
        hits = [p for p, full in group.items() if isinstance(full, str) and name_matches(nm, full)]
        out[nm] = hits
    return out


def main():
    print("Task 51: regista scorecard ...")
    summary = {}

    # ---------------- Card A ----------------
    mem_gate("card A")
    roles = pd.read_parquet(tb.ROLES_PATH).set_index("player_id")
    gA = roles.loc[roles["is_dm"], "player_name"].to_dict()
    Rc = pd.read_parquet(tb.RECEPTIONS_PATH)
    R = Rc[Rc["pr2_flag_keep"].notna()].copy()
    R["a1"] = R["pr2_flag_keep"] - R.groupby("team")["pr2_flag_keep"].transform("mean")
    W16, w16_base = fit_w(Rc, tb.match_folds(sorted(Rc["match_id"].unique())))
    move16 = pd.read_parquet(tb.MOVE_PATH)
    hold16 = pd.read_parquet(tb.HOLD_PATH)
    check = {"W_1516_rebuilt": w16_base, "W_1516_task46": TASK46["W_1516"]}
    print(f"  W 2015/16 rebuilt {w16_base} vs Task 46 {TASK46['W_1516']}", flush=True)
    # reproduction of Task 44 / Task 45 DM tables (no floor, as those tasks ran)
    for dim, u in (("PR2_flag_keep", units(R, "pr2_flag_keep")), ("A1", units(R, "a1"))):
        rows, dl = score(u, gA, 0)
        check[f"{dim}_no_floor"] = {"mu_w": dl["mu_w"], "Q": dl["Q"], "above": int((rows["label"] == "CLEARLY ABOVE").sum()),
                                    "below": int((rows["label"] == "CLEARLY BELOW").sum())}
    print(f"  reproduction checks: {check}", flush=True)
    A, sA = card("A", gA, [
        ("PR2_flag_keep", units(R, "pr2_flag_keep"), MIN_PR, "mean", REL["PR2_flag_keep"]),
        ("A1", units(R, "a1"), MIN_PR, "mean", REL["A1"]),
        ("W", units(W16, "w"), 100, "mean", REL["W"]),
        ("HOLD_VARIATION", units(hold16, "residual"), TEMPO_FLOOR, "sd", REL["HOLD_VARIATION"]),
        ("MOVE_ON_SPEED", units(move16, "residual"), TEMPO_FLOOR, "mean", REL["MOVE_ON_SPEED"]),
    ])
    A.to_parquet(OUT["A"])
    summary["A"] = {"group_size": len(gA), "dims": sA, "praised": praised(gA)}
    del Rc, R, W16, move16, hold16

    # ---------------- Card B ----------------
    mem_gate("card B")
    lb = pd.read_parquet(PROC / "leaderboard_v5c.parquet", columns=["player_id", "player_name", "is_deep_midfield"])
    gB = lb.loc[lb["is_deep_midfield"], ["player_id", "player_name"]].set_index("player_id")["player_name"].to_dict()
    dec = pd.read_parquet(E2 / "pass_der_crossfit_v5.parquet", columns=["match_id", "player_id", "decision"])
    prs = pd.read_parquet(E2 / "task46_study_pr_flag.parquet", columns=["match_id", "player_id", "pr2_flag_keep"])
    Wst, wst_base = w_study()
    check["W_study_rebuilt"], check["W_study_task46"] = wst_base, TASK46["W_study"]
    print(f"  W study rebuilt {wst_base} vs Task 46 {TASK46['W_study']}", flush=True)
    rq = pd.read_parquet(E2 / "task34_receptions.parquet", columns=["match_id", "player_id", "rq_rel"])
    rq_r1 = avt.r1(rq.rename(columns={"player_id": "pff_player_id", "match_id": "pff_game_id"}), "rq_rel", set(gB))
    rq_r1["method"] = "Task 38 R1 (src/pff/availability_tests.r1): players >= 4 matches, 100 random match half-splits, Spearman-Brown, median"
    TIER["RQ_rel"] = T2 if rq_r1["median"] >= 0.60 else T3
    REL["RQ_rel"] = (rq_r1["median"], "computed in Task 51 (Card B DMs, Task 38's R1)")
    if TIER["RQ_rel"] == T3:
        NOTE["RQ_rel"] = f"Tier 3: within-DM reliability {rq_r1['median']:.3f} < 0.60 (Task 51, Task 38's method)"
    print(f"  RQ_rel R1 within Card B DMs: {rq_r1} -> {TIER['RQ_rel']}", flush=True)
    mem_gate("card B tempo")
    moveS, holdS = tempo_study()
    mom = pd.read_parquet(av.MOMENTS_PATH, columns=["pff_game_id", "pff_player_id", "av"])
    pm = avt.player_map()
    pff2sb = pm.drop_duplicates("pff_player_id").set_index("pff_player_id")["sb_player_id"]
    mom["player_id"] = mom["pff_player_id"].map(pff2sb)
    rel_b = {k: (v[0], v[1]) for k, v in REL.items()}
    B, sB = card("B", gB, [
        ("Decision", units(dec, "decision"), 100, "mean", rel_b["Decision"]),
        ("PR2_flag_keep", units(prs, "pr2_flag_keep"), MIN_PR, "mean", rel_b["PR2_flag_keep"]),
        ("W", units(Wst, "w"), 100, "mean", rel_b["W"]),
        ("RQ_rel", units(rq, "rq_rel"), 100, "mean", rel_b["RQ_rel"]),
        ("HOLD_VARIATION", units(holdS, "residual"), TEMPO_FLOOR, "sd", rel_b["HOLD_VARIATION"]),
        ("MOVE_ON_SPEED", units(moveS, "residual"), TEMPO_FLOOR, "mean", rel_b["MOVE_ON_SPEED"]),
        ("AV", units(mom.dropna(subset=["player_id"]), "av", mid="pff_game_id"), 300, "mean", rel_b["AV"]),
    ])
    B.to_parquet(OUT["B"])
    summary["B"] = {"group_size": len(gB), "dims": sB, "praised": praised(gB), "RQ_rel_R1": rq_r1,
                    "n_av_players_in_group": int(B[(B["dimension"] == "AV") & (B["n"] > 0)].shape[0])}

    # ---------------- Card C ----------------
    mem_gate("card C")
    rr = pd.read_parquet(E2 / "task48_receptions.parquet", columns=["match_id", "player_id", "competition_id", "season_id", "pr2_flag_keep"])
    r48 = pd.read_parquet(E2 / "task48_roles.parquet").set_index("player_id")
    ing = json.loads((DATA_DIR / "engine_v2_task48_ingest.json").read_text())["per_competition_season"]
    season_name = {r["season_id"]: r["season"] for r in ing if r["competition_id"] == LA_LIGA}
    ll = rr[(rr["competition_id"] == LA_LIGA) & rr["pr2_flag_keep"].notna() & rr["player_id"].isin(set(r48.index[r48["is_dm"]]))]
    ps = ll.groupby(["player_id", "season_id"]).size().rename("n").reset_index()
    ps = ps[ps["n"] >= MIN_PR]
    nseas = ps.groupby("player_id").size()
    qual = sorted(nseas.index[nseas >= MIN_SEASONS])
    rowsC = []
    for pid in qual:
        seasons = set(ps.loc[ps["player_id"] == pid, "season_id"])
        u = ll[(ll["player_id"] == pid) & ll["season_id"].isin(seasons)]
        pp = u.assign(player_id=u["season_id"]).rename(columns={"pr2_flag_keep": "decision_new"})[["player_id", "match_id", "decision_new"]]
        s2, rho, _ = estimate_sigma2w_rho(pp)  # Task 29's within-group noise, with the player-season as the group
        for sid, g in pp.groupby("player_id"):
            n, G, m = len(g), g["match_id"].nunique(), g["decision_new"].mean()
            v = s2 * (1 + (n / G - 1) * rho) / n
            rowsC.append({"card": "C", "player_id": pid, "name": r48.loc[pid, "player_name"], "season_id": int(sid),
                          "season": season_name[sid], "n": n, "n_matches": G, "raw": m,
                          "ci_low_90": m - Z_90 * np.sqrt(v), "ci_high_90": m + Z_90 * np.sqrt(v),
                          "sigma2_w": s2, "rho": rho, "dimension": "PR2_flag_keep", "tier": T1,
                          "reliability": REL["PR2_flag_keep"][0], "reliability_source": REL["PR2_flag_keep"][1]})
    C = pd.DataFrame(rowsC).sort_values(["player_id", "season"])
    C.to_parquet(OUT["C"])
    summary["C"] = {"n_players": len(qual), "players": {int(p): r48.loc[p, "player_name"] for p in qual},
                    "seasons_per_player_all_dms": {int(k): int(v) for k, v in nseas.sort_values(ascending=False).items()},
                    "n_player_seasons": len(C)}
    print(f"  Card C: {summary['C']['players']} ({len(C)} player-seasons)", flush=True)

    SUMMARY_PATH.write_text(json.dumps({"summary": summary, "checks": check, "tiers": TIER,
                                        "reliability": {k: list(v) for k, v in REL.items()}, "notes": NOTE,
                                        "tempo_floor": TEMPO_FLOOR, "memory_log": MEM_LOG}, indent=2, default=str))
    print(f"Wrote {SUMMARY_PATH} and {', '.join(str(p) for p in OUT.values())}")


if __name__ == "__main__":
    main()
