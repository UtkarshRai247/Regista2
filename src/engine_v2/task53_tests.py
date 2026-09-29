"""
Task 53, Steps 3-4: the pre-registered replication family and the report-only
items, on the 2015/16 REPLICATION leagues (single use).
docs/specs/task-53-tempo-replication.md.

Units: task53_1516rep_{receptions,passes}.parquet (task53_build.py).
Existing comparators (Clarification B): PR2_flag_keep (task44_receptions) and
W (task52_w_1516), read with a replication-league match-id filter.
Helpers reused unchanged from task52_tests (measure formulas, floors, D1 R1,
other-match S, D3 P-test with controls, g features, roles / DM rule), with
task52_build's id sets switched to the replication ids (task53_build.switch_guard).

STABILITY S1-S5: D1 R1 within DMs, players >= 10 matches; PASS if median >= 0.60.
RESULTS R1-R7: Task 44 P-test design (fe_fit; R1 = fit_multi with
  [M4_SWITCH, PR2_flag_keep]); control = completion (passes) / retention
  (receptions) on the same rows; Holm across R1-R7; CONFIRMED = Holm p < 0.05,
  stated sign, control > 0 with p < 0.05.
CULMINATION C1, C2: DM player-level r, 1,000-player bootstrap 95% CI.
K1: raw r (always) + disattenuated only when both D1 reliabilities >= 0.30,
  never clipped; PC1 share of {PR2_flag_keep, W, M4_ACCEL, M2}.
Report only: D3 cells; K2 with PR2_flag_keep; praised list by ID
  (docs/splits/praised_ids.csv); Task 29 DM tables (task42_step2.dm_table) for
  measures passing their stability claim; M2 "drop excluded spells" sensitivity.

Run: python src/engine_v2/task53_tests.py   (after task53_build.py)
"""
import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from statsmodels.stats.multitest import multipletests

import task53_build as t53b

REP = t53b.switch_guard()  # before importing anything that reads the id sets

import task35_ptest as tp  # noqa: E402
import task52_tests as t52  # noqa: E402
from task41_lists_availability import perm_test  # noqa: E402
from task41_ptest_vetting import fit_multi  # noqa: E402
from task42_step2 import dm_table  # noqa: E402
from task50_puzzle import safe_dummy_check  # noqa: E402
from task50_robustness import mem_gate, MEM_LOG  # noqa: E402
from task52_split import SEED  # noqa: E402

warnings.filterwarnings("ignore")

REPO = Path(__file__).parent.parent.parent
DATA = REPO / "data"
E2 = DATA / "processed" / "engine_v2"
SUMMARY_PATH = DATA / "engine_v2_task53.json"
DS = "2015/16"
MIN_MATCHES = 10
SPECS = {
    "M2": ("pressured", "fk_res_1.5", "mean", None, 50, 1),
    "M2_1.0": ("pressured", "fk_res_1.0", "mean", None, 50, 1),
    "M2_2.0": ("pressured", "fk_res_2.0", "mean", None, 50, 1),
    "M2_sens": ("sens", "fk_sens_res_1.5", "mean", None, 50, 1),
    "M3_speed": ("timed", "r", "mean", None, 100, -1),
    "M3_var": ("timed", "r", "sd", None, 100, 1),
    "M4_ACCEL": ("passes", "res_ACCEL", "mean", None, 100, 1),
    "M4_KEEP": ("passes", "res_KEEP", "mean", None, 100, 1),
    "M4_SLOW": ("passes", "res_SLOW", "mean", None, 100, 1),
    "M4_SWITCH": ("passes", "res_SWITCH", "mean", None, 100, 1),
    "PR2_flag_keep": ("pr2", "pr2_flag_keep", "mean", None, 50, 1),
    "W": ("w", "w", "mean", None, 100, 1),
}
STAB = {"S1": "M4_ACCEL", "S2": "M4_SLOW", "S3": "M4_SWITCH", "S4": "M3_speed", "S5": "M2"}
FAMILY = {  # name: (group, measure, outcome, unit kind, stated sign)
    "R1": ("DM", "M4_SWITCH", "y_f3", "pass", +1), "R2": ("DM", "M3_speed", "y_f3", "rec", -1),
    "R3": ("DM", "M2", "poss_xg", "rec", +1), "R4": ("all", "M4_ACCEL", "y_f3", "pass", +1),
    "R5": ("all", "M4_SLOW", "y_f3", "pass", -1), "R6": ("all", "M4_SWITCH", "y_f3", "pass", +1),
    "R7": ("all", "M2", "y_f3", "rec", +1),
}
REPORT_MEASURES = ["M2", "M3_speed", "M3_var", "M4_ACCEL", "M4_SLOW", "M4_SWITCH"]
K1_SET = ["PR2_flag_keep", "W", "M2", "M3_speed", "M4_ACCEL", "M4_SLOW", "M4_SWITCH"]
PC1_SET = ["PR2_flag_keep", "W", "M4_ACCEL", "M2"]
DISATT_MIN_REL = 0.30


def load() -> dict:
    R = pd.read_parquet(E2 / "task53_1516rep_receptions.parquet")
    P = pd.read_parquet(E2 / "task53_1516rep_passes.parquet")
    assert R["match_id"].isin(REP).all() and P["match_id"].isin(REP).all()
    return {"receptions": R, "passes": P, "pressured": R[R["pressured_flag"]], "timed": R[R["timed"]],
            "sens": R[R["fk_sens_res_1.5"].notna()],
            "pr2": t52.read_dev(E2 / "task44_receptions.parquet", ["match_id", "event_id", "player_id", "pr2_flag_keep"], DS),
            "w": t52.read_dev(E2 / "task52_w_1516.parquet", ["match_id", "event_id", "player_id", "w"], DS)}


def boot_r(V: pd.DataFrame, x: str, y: str, boots) -> tuple:
    j = V[[x, y]].dropna()
    arr = V[[x, y]].to_numpy(float)
    bs = []
    for bi in boots:
        s = arr[bi]
        s = s[np.isfinite(s).all(1)]
        if len(s) >= 4:
            bs.append(np.corrcoef(s[:, 0], s[:, 1])[0, 1])
    bs = np.array(bs)
    return len(j), float(j[x].corr(j[y])), bs


def main():
    print(f"Task 53 tests on {len(REP)} 2015/16 REPLICATION matches ...")
    mem_gate("replication tests")
    t = load()
    role, dm, names = t52.roles_and_dm(DS, t["passes"])
    ST = {m: t52.stats_table(t[s[0]], s[1], s[2], s[3]) for m, s in SPECS.items()}
    vals = {m: t52.player_values(ST[m], SPECS[m][2], SPECS[m][4], SPECS[m][5]) for m in SPECS}
    praised = pd.read_csv(REPO / "docs" / "splits" / "praised_ids.csv")
    pids = set(praised["player_id"].astype(int))
    out = {"n_matches": len(REP), "n_players_receptions": int(t["receptions"]["player_id"].nunique()),
           "n_players_passes": int(t["passes"]["player_id"].nunique()), "n_players_with_role": int(len(role)), "n_dm": len(dm),
           "n_players_meeting_floor": {m: {"all": int(v.notna().sum()), "DM": int(v[v.index.isin(dm)].notna().sum())} for m, v in vals.items()},
           "category_share_all": t["passes"]["category"].value_counts(normalize=True).to_dict(),
           "category_share_dm": t["passes"][t["passes"]["player_id"].isin(dm)]["category"].value_counts(normalize=True).to_dict()}

    # D1 for every measure (the S-claims are the DM rows of S1-S5)
    d1 = {m: {"DM": t52.r1(ST[m], SPECS[m][2], SPECS[m][5], MIN_MATCHES, dm), "all": t52.r1(ST[m], SPECS[m][2], SPECS[m][5], MIN_MATCHES)}
          for m in SPECS}
    out["D1"] = d1
    out["stability"] = {s: {"measure": m, **d1[m]["DM"], "PASS": bool(d1[m]["DM"]["median"] is not None and d1[m]["DM"]["median"] >= 0.60)}
                        for s, m in STAB.items()}
    print(f"  stability: {({s: (v['measure'], v['median'], v['PASS']) for s, v in out['stability'].items()})}", flush=True)

    gf, gcols = t52.g_features(DS, t)
    U = {"rec": t52.unit_frame(DS, t, "rec", gf, gcols, role), "pass": t52.unit_frame(DS, t, "pass", gf, gcols, role)}
    S_of = {m: t52.other_match(ST[m], SPECS[m][2], SPECS[m][4], SPECS[m][5]) for m in SPECS}

    # RESULTS family
    fam = {}
    for name, (grp, m, y, kind, sign) in FAMILY.items():
        d = U[kind] if grp == "all" else U[kind][U[kind]["player_id"].isin(dm)]
        ctl = "keep_spell" if kind == "rec" else "pass_complete"
        if name == "R1":
            dd = d.merge(S_of[m].rename(columns={"S_raw": m}), on=["player_id", "match_id"], how="left") \
                  .merge(S_of["PR2_flag_keep"].rename(columns={"S_raw": "PR2_flag_keep"}), on=["player_id", "match_id"], how="left")
            rows = dd.dropna(subset=[m, "PR2_flag_keep", y, f"g_{y}"])
            jm = fit_multi(rows, y, [m, "PR2_flag_keep"], f"g_{y}")
            c = tp.fe_fit(rows.rename(columns={"S_ctl": "S_raw"}), ctl, f"g_{ctl}")
            r = {"coef_per_sd": jm[m]["coef_per_sd"], "coef_per_sd_per100": jm[m]["coef_per_sd_per100"],
                 "ci95_per100": jm[m]["ci95_per100"], "p": jm[m]["p"], "n_rows": len(rows),
                 "n_players": int(rows["player_id"].nunique()), "PR2_flag_keep_in_model": jm["PR2_flag_keep"],
                 "control": {k: c[k] for k in ("coef_per_sd_per100", "ci95_per100", "p", "n_rows")}}
        else:
            r = t52.ptest(d, S_of[m], y, ctl)
        r.update({"group": grp, "measure": m, "outcome": y, "stated_sign": sign})
        fam[name] = r
    holm = multipletests([fam[k]["p"] for k in FAMILY], method="holm")[1]
    for k, h in zip(FAMILY, holm):
        f = fam[k]
        f["p_holm"] = float(h)
        f["sign_ok"] = bool(np.sign(f["coef_per_sd_per100"]) == f["stated_sign"])
        f["control_ok"] = bool(f["control"]["coef_per_sd_per100"] > 0 and f["control"]["p"] < 0.05)
        f["CONFIRMED"] = bool(h < 0.05 and f["sign_ok"] and f["control_ok"])
        print(f"  {k}: {f['measure']} {f['group']} {f['outcome']} {f['coef_per_sd_per100']:+.4f} {f['ci95_per100']} p={f['p']:.3g} "
              f"holm={h:.3g} n={f['n_rows']}/{f['n_players']} control {f['control']['coef_per_sd_per100']:+.3f} p={f['control']['p']:.2g} "
              f"-> {'CONFIRMED' if f['CONFIRMED'] else 'not confirmed'}", flush=True)
    out["results_family"] = fam

    # CULMINATION C1, C2 and K1
    V = pd.DataFrame({m: vals[m] for m in K1_SET})
    V = V[V.index.isin(dm)]
    rng = np.random.default_rng(SEED)
    boots = [rng.integers(0, len(V), len(V)) for _ in range(1000)]
    rel = {m: d1[m]["DM"]["median"] for m in K1_SET}
    k1 = {}
    for i, x in enumerate(K1_SET):
        for y in K1_SET[i + 1:]:
            n, r, bs = boot_r(V, x, y, boots)
            e = {"n": n, "r": r, "r_ci95": [float(np.nanpercentile(bs, 2.5)), float(np.nanpercentile(bs, 97.5))]}
            if rel[x] is not None and rel[y] is not None and rel[x] >= DISATT_MIN_REL and rel[y] >= DISATT_MIN_REL:
                den = np.sqrt(rel[x] * rel[y])
                e.update({"r_disatt": r / den, "r_disatt_ci95": [float(np.nanpercentile(bs / den, 2.5)), float(np.nanpercentile(bs / den, 97.5))]})
            k1[f"{x}|{y}"] = e
    culm = {}
    for cname, (a, bm, sign) in {"C1": ("M4_ACCEL", "PR2_flag_keep", -1), "C2": ("M2", "PR2_flag_keep", +1)}.items():
        key = f"{bm}|{a}" if f"{bm}|{a}" in k1 else f"{a}|{bm}"
        e = k1[key]
        lo, hi = e["r_ci95"]
        culm[cname] = {"pair": key, **e, "stated_sign": sign,
                       "CONFIRMED": bool((sign < 0 and hi < 0) or (sign > 0 and lo > 0))}
        print(f"  {cname}: r={e['r']:+.3f} {e['r_ci95']} n={e['n']} -> {'CONFIRMED' if culm[cname]['CONFIRMED'] else 'not confirmed'}", flush=True)
    Z = V[PC1_SET].dropna()
    ev = np.sort(np.linalg.eigvalsh(np.corrcoef(Z.to_numpy(float).T)))[::-1]
    out["culmination"] = culm
    out["K1"] = {"reliability_DM_D1": rel, "pairs": k1,
                 "pc1": {"measures": PC1_SET, "n_players": len(Z), "share_pc1": float(ev[0] / ev.sum()), "eigenvalues": ev.tolist()}}

    # ---- report only ----
    d3 = {}
    for m in REPORT_MEASURES:
        kind = "rec" if m[:2] in ("M2", "M3") else "pass"
        ctl = "keep_spell" if kind == "rec" else "pass_complete"
        for grp in ("DM", "all"):
            d = U[kind] if grp == "all" else U[kind][U[kind]["player_id"].isin(dm)]
            for y in ("y_f3", "poss_xg"):
                d3[f"{m}|{grp}|{y}"] = t52.ptest(d, S_of[m], y, ctl)
    out["D3"] = d3

    dp = U["pass"][U["pass"]["player_id"].isin(dm)].copy()
    for m in REPORT_MEASURES + ["PR2_flag_keep"]:
        dp = dp.merge(S_of[m].rename(columns={"S_raw": m}), on=["player_id", "match_id"], how="left")
    k2 = {}
    pick = lambda r, c: {k: r[c][k] for k in ("coef_per_sd_per100", "ci95_per100", "p")}
    for y in ("y_f3", "poss_xg"):
        for m in REPORT_MEASURES:
            rows = dp.dropna(subset=[m, "PR2_flag_keep", y, f"g_{y}"])
            a, j, bo = fit_multi(rows, y, [m], f"g_{y}"), fit_multi(rows, y, [m, "PR2_flag_keep"], f"g_{y}"), \
                fit_multi(rows, y, ["PR2_flag_keep"], f"g_{y}")
            k2[f"{m}|{y}"] = {"n_rows": len(rows), "n_players": int(rows["player_id"].nunique()), "tempo_alone": pick(a, m),
                              "tempo_with_PR2": pick(j, m), "PR2_alone": pick(bo, "PR2_flag_keep"), "PR2_with_tempo": pick(j, "PR2_flag_keep")}
    out["K2"] = k2

    d5 = {}
    for m in REPORT_MEASURES + ["M4_KEEP"]:
        v = vals[m].dropna()
        df = pd.DataFrame({"sb_player_id": v.index.astype(float), "m": v.values})
        df["role"] = df["sb_player_id"].map(role)
        res = perm_test(df.dropna(subset=["role"]), {float(p) for p in pids}, np.random.default_rng(20260928))
        res["present_names"] = [names.get(int(p["sb_player_id"])) for p in res.get("present", [])]
        res["declared_direction"] = "higher" if m == "M2" else "none"
        d5[m] = res
    out["praised_by_id"] = d5

    tables = {}
    for s, m in STAB.items():
        if not out["stability"][s]["PASS"]:
            continue
        key, col, _, _, _, sign = SPECS[m]
        u = t[key][["player_id", "match_id", col]].dropna().copy()
        u[col] = sign * u[col]
        tab = dm_table(u, col, dm, names.to_dict())
        for row in tab["rows"]:
            row["praised"] = int(row["player_id"]) in pids
        tables[m] = tab
    out["dm_tables"] = tables

    sens = {"S5_equiv": d1["M2_sens"]["DM"]}
    for nm, grp, y in (("R3_equiv", "DM", "poss_xg"), ("R7_equiv", "all", "y_f3")):
        d = U["rec"] if grp == "all" else U["rec"][U["rec"]["player_id"].isin(dm)]
        sens[nm] = t52.ptest(d, S_of["M2_sens"], y, "keep_spell")
    out["M2_sensitivity_drop_excluded_spells"] = sens
    out["existing_table_reads"] = t52.READS
    out["memory_log"] = MEM_LOG
    SUMMARY_PATH.write_text(json.dumps(out, indent=2, default=str))
    print(f"Wrote {SUMMARY_PATH}")


if __name__ == "__main__":
    main()
