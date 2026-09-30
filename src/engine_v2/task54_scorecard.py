"""
Task 54, Part A (A1-A6): scorecard v2. docs/specs/task-54-scorecard-v2-and-repo-prep.md.
Descriptive only; no tests, no claims.

Card A (2015/16, all five leagues, Task 44's 185 DMs):
  - PR2_flag_keep, A1, W, HOLD_VARIATION, MOVE_ON_SPEED scored as Task 51, from the
    same existing tables (W from task52_w_1516, the Task 46 W written to disk in Task 52).
  - A1: Task 52/53 tempo measures M4_ACCEL, M4_SLOW, M4_SWITCH, M3_speed, M2 on ALL
    1,551 matches with ONE baseline fit per measure (5 match folds over all 2015/16
    ids, task52_build.folds_for, seed 20260929), Task 53's definitions. Units come
    from the existing built unit tables task52_1516_* (development) and
    task53_1516rep_* (replication); no raw event file is opened.
Card B (study, Task 27's 111 DMs): Task 51's dimensions rebuilt from built tables
  only (pass_der_crossfit_v5, task46_study_pr_flag, task52_w_study, task34_receptions,
  tempo_task52_study_*_ids, PFF availability moments). A4: each dimension's
  within-DM stability on the study sample itself (Task 38's method via
  task52_tests.r1, >= 4 matches); Task 51's automatic rule (< 0.60 -> TIER 3) applies.
Card C: Task 51's parquet, tier relabelled (A2: press resistance = TIER 1B).
A2 tiers fixed in the brief. A3: HOLD_VARIATION interval = player-level bootstrap
  over his matches (1,000 resamples, seed 20260929), 90% percentile interval;
  labels against the mean of the group's raw SDs (players meeting the floor).
Scoring for every other dimension: task51_scorecard.score (Task 29's method).

Run: python src/engine_v2/task54_scorecard.py
"""
import json
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent / "pff"))
import availability as av  # noqa: E402
import availability_tests as avt  # noqa: E402
import task44_build as tb  # noqa: E402
import task52_build as b52  # noqa: E402
import task52_tests as t52  # noqa: E402
from task51_scorecard import score, units, TEMPO_FLOOR, MIN_PR  # noqa: E402
from task50_robustness import mem_gate, MEM_LOG  # noqa: E402

warnings.filterwarnings("ignore")

REPO = Path(__file__).parent.parent.parent
DATA = REPO / "data"
PROC = DATA / "processed"
E2 = PROC / "engine_v2"
OUT = {c: PROC / f"scorecard_v2_card_{c.lower()}.parquet" for c in ("A", "B", "C")}
SUMMARY_PATH = DATA / "engine_v2_task54.json"
SEED = 20260929
R53 = "docs/results/53-tempo-replication.md"

TIER = {"M4_SWITCH": "TIER 1A", "PR2_flag_keep": "TIER 1B", "A1": "TIER 1B", "M4_ACCEL": "TIER 1B", "M4_SLOW": "TIER 1B",
        "M2": "TIER 1B", "M3_speed": "TIER 2", "W": "TIER 2", "HOLD_VARIATION": "TIER 2", "AV": "TIER 2",
        "Decision": "TIER 3", "MOVE_ON_SPEED": "TIER 3", "RQ_rel": "TIER 3"}
EVIDENCE = {
    "M4_SWITCH": "Tier 1A: switching -> reaching the final third within DMs, confirmed on held-back 2015/16 leagues (Task 53 R1)",
    "PR2_flag_keep": "Tier 1B: travels club <-> country and team-adjusted version -> final third, confirmed on reserved data (Task 48 C4, C6)",
    "A1": "Tier 1B (shown beside PR2_flag_keep): team-adjusted press resistance -> final third, confirmed on reserved data (Task 48 C6)",
    "M4_ACCEL": "Tier 1B: speeding up -> final third, all players, confirmed on held-back 2015/16 leagues (Task 53 R4)",
    "M4_SLOW": "Tier 1B: recycling -> less final-third progression, all players, confirmed on held-back 2015/16 leagues (Task 53 R5)",
    "M2": "Tier 1B: quick and safe under pressure -> final third, all players, confirmed on held-back 2015/16 leagues (Task 53 R7)",
    "M3_speed": "Tier 2: stable within DMs (Task 53 S4); DM results claim R2 not confirmed",
    "W": "Tier 2: stable within DMs; no confirmed results link (Task 48 C2 not confirmed)",
    "HOLD_VARIATION": "Tier 2: stable within DMs; no confirmed results link",
    "AV": "Tier 2: linked to FEWER chances in WC2022; exploratory (Task 38)",
    "Decision": "Tier 3: within-DM reliability ~0.45; its confirmed results link is carried by forwards",
    "MOVE_ON_SPEED": "Tier 3: within-DM reliability 0.475 in 2015/16",
    "RQ_rel": "Tier 3: within-DM reliability 0.419 on Card B's DMs (Task 51)",
}
STYLE = {"M4_ACCEL", "M4_SLOW", "M4_SWITCH"}
STYLE_NOTE = "STYLE: a high or low value is a type, not better or worse"
REL_A = {
    "PR2_flag_keep": (0.666, "docs/results/44-big-five-1516.md:120 (2015/16 DMs, 185)"),
    "A1": (0.487, "docs/results/45-press-resistance-vetting.md:48 (2015/16 DMs, 185)"),
    "W": (0.802, "docs/results/46-movers-and-spatial-physical.md:73 (2015/16 DMs, 185)"),
    "HOLD_VARIATION": (0.730, "docs/results/44-big-five-1516.md:119 (2015/16 DMs, 185)"),
    "MOVE_ON_SPEED": (0.475, "docs/results/44-big-five-1516.md:118 (2015/16 DMs, 185)"),
    "M4_ACCEL": (0.898, f"{R53} S1 (2015/16 replication-league DMs, 141)"),
    "M4_SLOW": (0.844, f"{R53} S2 (2015/16 replication-league DMs, 141)"),
    "M4_SWITCH": (0.830, f"{R53} S3 (2015/16 replication-league DMs, 141)"),
    "M3_speed": (0.806, f"{R53} S4 (2015/16 replication-league DMs, 141)"),
    "M2": (0.688, f"{R53} S5 (2015/16 replication-league DMs, 141)"),
}


def hold_rows(u: pd.DataFrame, group: dict, floor: int) -> pd.DataFrame:
    """A3: raw SD, bootstrap-over-matches 90% interval, labels vs the group mean of raw SDs."""
    u = u[u["player_id"].isin(group)].dropna(subset=["value"])
    n = u.groupby("player_id").size().reindex(list(group), fill_value=0)
    ok = [p for p in group if n[p] >= floor]
    rng = np.random.default_rng(SEED)
    raw, lo, hi = {}, {}, {}
    for p in ok:
        g = u[u["player_id"] == p]
        by = [x.to_numpy(float) for _, x in g.groupby("match_id")["value"]]
        raw[p] = float(g["value"].std(ddof=1))
        bs = np.empty(1000)
        for k in range(1000):
            pick = rng.integers(0, len(by), len(by))
            bs[k] = np.concatenate([by[i] for i in pick]).std(ddof=1)
        lo[p], hi[p] = float(np.percentile(bs, 5)), float(np.percentile(bs, 95))
    rows = pd.DataFrame({"player_id": list(group), "name": [group[p] for p in group], "n": n.values})
    rows["raw"] = rows["player_id"].map(raw)
    rows["shrunken"] = np.nan
    rows["ci_low_90"], rows["ci_high_90"] = rows["player_id"].map(lo), rows["player_id"].map(hi)
    rows["percentile"] = rows["raw"].rank(pct=True) * 100
    sv = np.sort(rows["raw"].dropna().values)
    for c in ("ci_low_90", "ci_high_90"):
        rows[c + "_pct"] = [100 * np.searchsorted(sv, x, side="right") / len(sv) if pd.notna(x) else np.nan for x in rows[c]]
    mu = float(np.mean(list(raw.values())))
    rows["label"] = np.select([~rows["player_id"].isin(ok), rows["ci_low_90"] > mu, rows["ci_high_90"] < mu],
                              ["not enough data", "CLEARLY ABOVE", "CLEARLY BELOW"], "CAN'T TELL")
    return rows, {"group_mean_raw_sd": mu, "n_players": len(ok), "bootstrap": "1,000 resamples of matches, 90% percentile interval"}


def card(name: str, group: dict, dims: list, rel: dict, tier: dict, evidence: dict = EVIDENCE) -> tuple:
    out, summ = [], {}
    for dim, u, floor, stat in dims:
        if stat == "sd":
            rows, dl = hold_rows(u, group, floor)
        else:
            rows, dl = score(u, group, floor, stat)
        note = "; ".join(x for x in (STYLE_NOTE if dim in STYLE else "", evidence[dim]) if x)
        rows = rows.assign(card=name, dimension=dim, floor=floor, tier=tier[dim], reliability=rel[dim][0],
                           reliability_source=rel[dim][1], note=note, style=dim in STYLE)
        out.append(rows)
        summ[dim] = {"tier": tier[dim], "reliability": rel[dim][0], "reliability_source": rel[dim][1], "floor": floor,
                     "n_meeting_floor": int((rows["label"] != "not enough data").sum()),
                     "counts": rows["label"].value_counts().to_dict(), "dl": dl}
        print(f"  {name} {dim}: {tier[dim]} rel {rel[dim][0]} {summ[dim]['counts']}", flush=True)
    return pd.concat(out, ignore_index=True), summ


def tempo_all_1516() -> tuple:
    """A1: union of the built development + replication unit tables; one baseline per measure over all 1,551 matches."""
    R = pd.concat([pd.read_parquet(E2 / "task52_1516_receptions.parquet"), pd.read_parquet(E2 / "task53_1516rep_receptions.parquet")],
                  ignore_index=True)
    P = pd.concat([pd.read_parquet(E2 / "task52_1516_passes.parquet"), pd.read_parquet(E2 / "task53_1516rep_passes.parquet")],
                  ignore_index=True)
    mids = sorted(set(R["match_id"]) | set(P["match_id"]))
    fold = b52.folds_for(mids)
    R["fold"], P["fold"] = R["match_id"].map(fold), P["match_id"].map(fold)
    ctx = b52.CTX
    info = {"n_matches": len(mids), "n_completed_receptions": len(R), "n_eligible_passes": len(P)}
    R["timed"] = (R["end_reason"] == "pass") & (R["T"] > 0) & (R["T"] <= b52.T_MAX)
    Tm = R[R["timed"]].copy()
    Tm["logT"] = np.log(Tm["T"])
    Tm["g_T"], info["g_T_oof_r2"] = b52.crossfit(Tm, ctx, "logT", "reg")
    Tm["r"] = Tm["logT"] - Tm["g_T"]
    Pr = R[R["pressured_flag"]].copy()
    Pr["fk"] = ((Pr["end_reason"] == "pass") & (Pr["end_pass_complete"] == 1) & (Pr["T"] > 0) & (Pr["T"] <= 1.5)).astype(int)
    p, info["fk_1.5_auc"] = b52.crossfit(Pr, ctx, "fk", "clf")
    Pr["m2"] = Pr["fk"] - p
    for cat in ("ACCEL", "SLOW", "SWITCH"):
        P[f"is_{cat}"] = (P["category"] == cat).astype(int)
        p, info[f"m4_{cat}_auc"] = b52.crossfit(P, ctx, f"is_{cat}", "clf")
        P[f"res_{cat}"] = P[f"is_{cat}"] - p
    Tm["speed"] = -Tm["r"]
    info.update({"n_timed": len(Tm), "n_pressured": len(Pr)})
    return {"M4_ACCEL": units(P, "res_ACCEL"), "M4_SLOW": units(P, "res_SLOW"), "M4_SWITCH": units(P, "res_SWITCH"),
            "M3_speed": units(Tm, "speed"), "M2": units(Pr, "m2")}, info


def main():
    print("Task 54 Part A: scorecard v2 ...")
    summary = {}
    # ---------------- Card A ----------------
    mem_gate("card A")
    roles = pd.read_parquet(tb.ROLES_PATH).set_index("player_id")
    gA = roles.loc[roles["is_dm"], "player_name"].to_dict()
    Rc = pd.read_parquet(tb.RECEPTIONS_PATH, columns=["match_id", "event_id", "player_id", "team", "pr2_flag_keep"])
    R = Rc[Rc["pr2_flag_keep"].notna()].copy()
    R["a1"] = R["pr2_flag_keep"] - R.groupby("team")["pr2_flag_keep"].transform("mean")
    W16 = pd.read_parquet(E2 / "task52_w_1516.parquet", columns=["match_id", "player_id", "w"])
    move16, hold16 = pd.read_parquet(tb.MOVE_PATH), pd.read_parquet(tb.HOLD_PATH)
    tempo, tinfo = tempo_all_1516()
    print(f"  A1 tempo baselines: {tinfo}", flush=True)
    A, sA = card("A", gA, [
        ("PR2_flag_keep", units(R, "pr2_flag_keep"), MIN_PR, "mean"),
        ("A1", units(R, "a1"), MIN_PR, "mean"),
        ("M4_SWITCH", tempo["M4_SWITCH"], 100, "mean"),
        ("M4_ACCEL", tempo["M4_ACCEL"], 100, "mean"),
        ("M4_SLOW", tempo["M4_SLOW"], 100, "mean"),
        ("M2", tempo["M2"], 50, "mean"),
        ("M3_speed", tempo["M3_speed"], 100, "mean"),
        ("W", units(W16, "w"), 100, "mean"),
        ("HOLD_VARIATION", units(hold16, "residual"), TEMPO_FLOOR, "sd"),
        ("MOVE_ON_SPEED", units(move16, "residual"), TEMPO_FLOOR, "mean"),
    ], REL_A, TIER)
    A.to_parquet(OUT["A"])
    t51a = pd.read_parquet(PROC / "scorecard_card_a.parquet")
    chk = {}
    for dim in ("PR2_flag_keep", "A1", "W", "MOVE_ON_SPEED"):
        x = A[A["dimension"] == dim].set_index("player_id")["shrunken"]
        y = t51a[t51a["dimension"] == dim].set_index("player_id")["shrunken"]
        chk[f"A_{dim}_max_abs_diff_vs_task51"] = float((x - y.reindex(x.index)).abs().max())
    summary["A"] = {"group_size": len(gA), "dims": sA, "tempo_build": tinfo}
    del Rc, R, W16, move16, hold16, tempo

    # ---------------- Card B ----------------
    mem_gate("card B")
    lb = pd.read_parquet(PROC / "leaderboard_v5c.parquet", columns=["player_id", "player_name", "is_deep_midfield"])
    gB = lb.loc[lb["is_deep_midfield"], ["player_id", "player_name"]].set_index("player_id")["player_name"].to_dict()
    mom = pd.read_parquet(av.MOMENTS_PATH, columns=["pff_game_id", "pff_player_id", "av"])
    pm = avt.player_map()
    mom["player_id"] = mom["pff_player_id"].map(pm.drop_duplicates("pff_player_id").set_index("pff_player_id")["sb_player_id"])
    uB = {"Decision": (units(pd.read_parquet(E2 / "pass_der_crossfit_v5.parquet", columns=["match_id", "player_id", "decision"]), "decision"), 100, "mean"),
          "PR2_flag_keep": (units(pd.read_parquet(E2 / "task46_study_pr_flag.parquet", columns=["match_id", "player_id", "pr2_flag_keep"]), "pr2_flag_keep"), MIN_PR, "mean"),
          "W": (units(pd.read_parquet(E2 / "task52_w_study.parquet", columns=["match_id", "player_id", "w"]), "w"), 100, "mean"),
          "RQ_rel": (units(pd.read_parquet(E2 / "task34_receptions.parquet", columns=["match_id", "player_id", "rq_rel"]), "rq_rel"), 100, "mean"),
          "HOLD_VARIATION": (units(pd.read_parquet(PROC / "tempo_task52_study_hold_residuals_ids.parquet"), "residual"), TEMPO_FLOOR, "sd"),
          "MOVE_ON_SPEED": (units(pd.read_parquet(PROC / "tempo_task52_study_move_residuals_ids.parquet"), "residual"), TEMPO_FLOOR, "mean"),
          "AV": (units(mom.dropna(subset=["player_id"]), "av", mid="pff_game_id"), 300, "mean")}
    stab, relB, tierB = {}, {}, {}
    for dim, (u, _, stat) in uB.items():  # A4: within-DM stability on the study sample itself
        st = t52.stats_table(u.rename(columns={"value": "v"}), "v", stat, None)
        stab[dim] = t52.r1(st, stat, 1, 4, set(gB))
        m = stab[dim]["median"]
        relB[dim] = (m, "computed in Task 54 on Card B's DMs (Task 38's method, >= 4 matches"
                     + ("; match = PFF game" if dim == "AV" else "") + ")")
        tierB[dim] = TIER[dim] if (m is not None and m >= 0.60) else "TIER 3"
        print(f"  B stability {dim}: {stab[dim]} -> {tierB[dim]}", flush=True)
    evB = {d: (EVIDENCE[d] if tierB[d] == TIER[d] else
               f"Tier 3 by Task 51's automatic rule: within-DM stability on the study sample "
               f"{'not computable' if relB[d][0] is None else f'{relB[d][0]:.3f}'} < 0.60 (A2 tier {TIER[d]})") for d in uB}
    B, sB = card("B", gB, [(d, u, f, s) for d, (u, f, s) in uB.items()], relB, tierB, evB)
    B.to_parquet(OUT["B"])
    t51b = pd.read_parquet(PROC / "scorecard_card_b.parquet")
    for dim in ("Decision", "PR2_flag_keep", "W", "RQ_rel", "MOVE_ON_SPEED", "AV"):
        x = B[B["dimension"] == dim].set_index("player_id")["shrunken"]
        y = t51b[t51b["dimension"] == dim].set_index("player_id")["shrunken"]
        chk[f"B_{dim}_max_abs_diff_vs_task51"] = float((x - y.reindex(x.index)).abs().max())
    summary["B"] = {"group_size": len(gB), "dims": sB, "stability_A4": stab}

    # ---------------- Card C ----------------
    C = pd.read_parquet(PROC / "scorecard_card_c.parquet").assign(tier=TIER["PR2_flag_keep"], note=EVIDENCE["PR2_flag_keep"])
    C.to_parquet(OUT["C"])
    summary["C"] = {"n_players": int(C["player_id"].nunique()), "n_player_seasons": len(C)}

    # ---------------- A5 / A6 selections ----------------
    ids = pd.read_csv(REPO / "docs" / "splits" / "praised_ids.csv")
    pr = A[(A["dimension"] == "PR2_flag_keep") & (A["label"] != "not enough data")]
    praised_present = [int(p) for p in ids["player_id"] if int(p) in gA]
    top3 = pr.sort_values("shrunken", ascending=False)["player_id"].head(3).astype(int).tolist()
    rows = list(dict.fromkeys(praised_present + top3))
    summary["figure1"] = {"praised_present": praised_present, "top3_pr2_shrunk": top3, "rows": rows,
                          "names": {p: gA[p] for p in rows}}
    a6 = {}
    for p in (5203, 5574):
        for d in ("M4_ACCEL", "M2", "M4_SWITCH"):
            r = A[(A["player_id"] == p) & (A["dimension"] == d)].iloc[0]
            a6[f"{gA.get(p)}|{d}"] = {k: (None if pd.isna(r[k]) else (float(r[k]) if not isinstance(r[k], str) else r[k]))
                                      for k in ("n", "raw", "shrunken", "percentile", "ci_low_90_pct", "ci_high_90_pct", "label")}
    summary["A6"] = a6
    summary["checks"] = chk
    summary["memory_log"] = MEM_LOG
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2, default=str))
    print(f"  checks: {chk}\n  figure1 rows: {summary['figure1']}\n  A6: {json.dumps(a6)}")
    print(f"Wrote {SUMMARY_PATH}")


if __name__ == "__main__":
    main()
