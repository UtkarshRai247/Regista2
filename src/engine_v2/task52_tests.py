"""
Task 52, Step 5 (D1-D5), Amendment A tests (M4-M6) and Step 6 (K1, K2) on the
DEVELOPMENT half only (report only). docs/specs/task-52-tempo-development.md.

Inputs:
  NEW measures: task52_{1516,study}_{receptions,passes}.parquet (task52_build.py,
    development per-match raw files only).
  EXISTING comparators / controls (Clarification B): read with a pyarrow filter
    match_id in DEVELOPMENT ids, then re-filtered in pandas; replication rows are
    dropped before any computation; their existing baselines are kept:
      PR2_flag_keep  task44_receptions (2015/16), task46_study_pr_flag (study)
      W              task52_w_1516 / task52_w_study (Task 46's W, written in Step 1)
      MOVE/HOLD      tempo_task44_{move,hold}_residuals_ids (2015/16),
                     tempo_task52_study_{move,hold}_residuals_ids (study)
      v5 Decision    pass_der_crossfit_v5 (study)
      g features     value_model_rows_v5 (study; Task 42's reception g / Task 35's pass g)
  Player-level tables read for names / the study DM list: task44_roles.player_name,
  leaderboard_v5c (player_name, is_deep_midfield).
  2015/16 event-only g features: task44_build.event_features on development matches.

Player value of a measure = f(units) with its floor; per-(player, match)
sufficient statistics make D1 halves and D3 / K2 other-match S exact:
  mean: sum / n; sd: sample SD; diff: mean(group A) - mean(group B).
D1: Task 38's R1 (availability_tests.r1 recipe: 100 random halves of a player's
  matches, Pearson across players, Spearman-Brown, median, seed 20260928) with the
  measure's own formula per half; players >= 10 matches (2015/16) / >= 4 (study).
D2: task46_part_a.disattenuated (Task 46 A-ii recipe, seed = Study B's) on
  2015/16 development club units vs study-development national-team units.
D3: task35_ptest.fe_fit; S = other-match value (floor on the other matches);
  g cross-fitted on development folds; control = retention (receptions:
  keep_spell, S = other-match keep_spell >= 100) / completion (passes).
D4: within-DM Pearson r with Fisher CI.  D5: task41 perm_test with LIST_L.
K1: raw and disattenuated r (reliabilities from D1, DMs), 1,000-player bootstrap;
  PC1 variance share.  K2: task41_ptest_vetting.fit_multi on DM passes.

Run: python src/engine_v2/task52_tests.py   (after task52_build.py)
"""
import json
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
import xgboost as xgb
from scipy.stats import norm

sys.path.insert(0, str(Path(__file__).parent.parent / "decision_engine"))
import task26_step6_study_b as sb  # noqa: E402
import task35_ptest as tp  # noqa: E402
import task44_build as tb  # noqa: E402
from task27_step1_deep_midfield import name_matches  # noqa: E402
from task32_step4 import ROLE_POSITIONS  # noqa: E402
from task33_step3_f_state import XGB_REGRESSOR_KWARGS, F_STATE_FEATURES  # noqa: E402
from task41_lists_availability import perm_test, LIST_L  # noqa: E402
from task41_ptest_vetting import fit_multi  # noqa: E402
from task46_part_a import disattenuated  # noqa: E402
from task50_puzzle import safe_dummy_check  # noqa: E402
from task50_robustness import mem_gate, MEM_LOG  # noqa: E402
from task52_build import DEV, DS, N_FOLDS  # noqa: E402
from task52_split import SEED  # noqa: E402

warnings.filterwarnings("ignore")

DATA = Path(__file__).parent.parent.parent / "data"
E2 = DATA / "processed" / "engine_v2"
PROC = DATA / "processed"
SUMMARY_PATH = DATA / "engine_v2_task52_tests.json"
INTL = {(43, 106), (55, 282), (55, 43)}  # task04_situation_context.INTL_COMPETITIONS
R1_SEED, R1_SPLITS = 20260928, 100
MIN_MATCHES = {"2015/16": 10, "study": 4}
F3_X = 80.0
READS = []


def read_dev(path: Path, cols: list, ds: str) -> pd.DataFrame:
    ids = sorted(DEV[ds])
    df = pq.read_table(path, columns=cols, filters=[("match_id", "in", ids)]).to_pandas()
    df = df[df["match_id"].isin(DEV[ds])].reset_index(drop=True)
    READS.append({"table": str(path.relative_to(DATA.parent)), "filter": f"match_id in {ds} DEVELOPMENT ids ({len(ids)})",
                  "rows_kept": len(df)})
    return df


# ---------------------------------------------------------------- measures
# spec: (table key, value column, kind, group column for diff (A minus B: value 0 minus value 1 unless flip), floor, sign)
def specs(ds: str) -> dict:
    s = {
        "M2": ("pressured", "fk_res_1.5", "mean", None, 50, 1),
        "M2_1.0": ("pressured", "fk_res_1.0", "mean", None, 50, 1),
        "M2_2.0": ("pressured", "fk_res_2.0", "mean", None, 50, 1),
        "M3_speed": ("timed", "r", "mean", None, 100, -1),
        "M3_var": ("timed", "r", "sd", None, 100, 1),
        "M4_ACCEL": ("passes", "res_ACCEL", "mean", None, 100, 1),
        "M4_KEEP": ("passes", "res_KEEP", "mean", None, 100, 1),
        "M4_SLOW": ("passes", "res_SLOW", "mean", None, 100, 1),
        "M4_SWITCH": ("passes", "res_SWITCH", "mean", None, 100, 1),
        "M6": ("m6", "m6_res", "mean", None, 100, 1),
        "M6_on_ACCEL": ("m6_accel", "m6_res", "mean", None, 100, 1),
        "M6_on_SLOW": ("m6_slow", "m6_res", "mean", None, 100, 1),
        "PR2_flag_keep": ("pr2", "pr2_flag_keep", "mean", None, 50, 1),
        "W": ("w", "w", "mean", None, 100, 1),
        "MOVE_ON_SPEED": ("move", "residual", "mean", None, 200, 1),
        "HOLD_VARIATION": ("hold", "residual", "sd", None, 200, 1),
    }
    if ds == "study":
        # M1: mean r on receptions WITHOUT an opening minus WITH one (group 0 minus group 1)
        s["M1"] = ("timed_frame", "r", "diff", "opening", 30, 1)
        # M5: mean(ACCEL - p | OPPORTUNITY) minus mean(... | no OPPORTUNITY) (group 1 minus group 0)
        s["M5"] = ("passes", "res_ACCEL", "diff", "opportunity", 30, -1)
        s["Decision"] = ("decision", "decision", "mean", None, 100, 1)
    return s


def stats_table(units: pd.DataFrame, col: str, kind: str, grp) -> pd.DataFrame:
    u = units.dropna(subset=[col] + ([grp] if grp else []))[["player_id", "match_id", col] + ([grp] if grp else [])].copy()
    if kind == "diff":
        u["g"] = u[grp].astype(int)
        a = u.groupby(["player_id", "match_id", "g"])[col].agg(["sum", "count"]).unstack("g", fill_value=0)
        a.columns = [f"{s}{g}" for s, g in a.columns]
        for c in ("sum0", "sum1", "count0", "count1"):
            if c not in a:
                a[c] = 0.0
        return a.reset_index()
    u["x2"] = u[col] ** 2
    return u.groupby(["player_id", "match_id"]).agg(sum=(col, "sum"), sq=("x2", "sum"), count=(col, "size")).reset_index()


def value_from(st: pd.DataFrame, kind: str, floor: int, sign: int) -> pd.Series:
    """st: rows of summed statistics (any index). Returns value with NaN below floor."""
    with np.errstate(invalid="ignore", divide="ignore"):
        if kind == "mean":
            v = st["sum"] / st["count"]
            ok = st["count"] >= floor
        elif kind == "sd":
            v = np.sqrt(np.clip((st["sq"] - st["sum"] ** 2 / st["count"]) / (st["count"] - 1), 0, None))
            ok = st["count"] >= floor
        else:
            v = st["sum0"] / st["count0"] - st["sum1"] / st["count1"]
            ok = (st["count0"] >= floor) & (st["count1"] >= floor)
    return (sign * v).where(ok)


def player_values(st: pd.DataFrame, kind, floor, sign) -> pd.Series:
    tot = st.drop(columns=["match_id"]).groupby("player_id").sum()
    return value_from(tot, kind, floor, sign)


def other_match(st: pd.DataFrame, kind, floor, sign) -> pd.DataFrame:
    """Per (player, match): the value over the player's OTHER matches (floor applied to those)."""
    cols = [c for c in st.columns if c not in ("player_id", "match_id")]
    tot = st.groupby("player_id")[cols].transform("sum")
    oth = tot - st[cols]
    return pd.DataFrame({"player_id": st["player_id"], "match_id": st["match_id"], "S_raw": value_from(oth, kind, floor, sign).values})


def r1(st: pd.DataFrame, kind, sign, min_matches, pids=None) -> dict:
    """Task 38's R1 with the measure's own formula per half (no per-half floor; empty halves -> NaN, dropped)."""
    d = st if pids is None else st[st["player_id"].isin(pids)]
    nm = d.groupby("player_id")["match_id"].nunique()
    players = sorted(nm[nm >= min_matches].index)
    cols = [c for c in d.columns if c not in ("player_id", "match_id")]
    by = {p: g[cols].to_numpy(float) for p, g in d[d["player_id"].isin(players)].groupby("player_id")}
    rng = np.random.default_rng(R1_SEED)
    sbs = []
    for _ in range(R1_SPLITS):
        h1, h2 = [], []
        for p in players:
            a = by[p]
            idx = rng.permutation(len(a))
            k = len(a) // 2
            h1.append(a[idx[:k]].sum(0))
            h2.append(a[idx[k:]].sum(0))
        v1 = value_from(pd.DataFrame(h1, columns=cols), kind, 1, sign).values
        v2 = value_from(pd.DataFrame(h2, columns=cols), kind, 1, sign).values
        m = np.isfinite(v1) & np.isfinite(v2)
        if m.sum() < 3:
            continue
        r = np.corrcoef(v1[m], v2[m])[0, 1]
        sbs.append(2 * r / (1 + r))
    if not sbs:
        return {"n_players": len(players), "median": None}
    sbs = np.array(sbs)
    return {"n_players": len(players), "median": float(np.median(sbs)), "p5": float(np.percentile(sbs, 5)),
            "p95": float(np.percentile(sbs, 95)), "bar_0.60": bool(np.median(sbs) >= 0.60)}


def fisher(r, n):
    if n < 4 or not np.isfinite(r):
        return [None, None]
    z, se = np.arctanh(np.clip(r, -0.999999, 0.999999)), 1 / np.sqrt(n - 3)
    return [float(np.tanh(z - 1.96 * se)), float(np.tanh(z + 1.96 * se))]


# ---------------------------------------------------------------- data
def load(ds: str) -> dict:
    slug = DS[ds]["slug"]
    R = pd.read_parquet(E2 / f"task52_{slug}_receptions.parquet")
    P = pd.read_parquet(E2 / f"task52_{slug}_passes.parquet")
    assert R["match_id"].isin(DEV[ds]).all() and P["match_id"].isin(DEV[ds]).all()
    t = {"receptions": R, "passes": P, "pressured": R[R["pressured_flag"]], "timed": R[R["timed"]],
         "timed_frame": R[R["timed"] & R["opening"].notna()], "m6": P[P["m6_res"].notna()],
         "m6_accel": P[P["m6_res"].notna() & (P["category"] == "ACCEL")],
         "m6_slow": P[P["m6_res"].notna() & (P["category"] == "SLOW")]}
    if ds == "2015/16":
        t["pr2"] = read_dev(E2 / "task44_receptions.parquet", ["match_id", "event_id", "player_id", "pr2_flag_keep"], ds)
        t["w"] = read_dev(E2 / "task52_w_1516.parquet", ["match_id", "event_id", "player_id", "w"], ds)
        t["move"] = read_dev(PROC / "tempo_task44_move_residuals_ids.parquet", ["match_id", "event_id", "player_id", "residual"], ds)
        t["hold"] = read_dev(PROC / "tempo_task44_hold_residuals_ids.parquet", ["match_id", "event_id", "player_id", "residual"], ds)
    else:
        t["pr2"] = read_dev(E2 / "task46_study_pr_flag.parquet", ["match_id", "event_id", "player_id", "pr2_flag_keep"], ds)
        t["w"] = read_dev(E2 / "task52_w_study.parquet", ["match_id", "event_id", "player_id", "w"], ds)
        t["move"] = read_dev(PROC / "tempo_task52_study_move_residuals_ids.parquet", ["match_id", "event_id", "player_id", "residual"], ds)
        t["hold"] = read_dev(PROC / "tempo_task52_study_hold_residuals_ids.parquet", ["match_id", "event_id", "player_id", "residual"], ds)
        t["decision"] = read_dev(E2 / "pass_der_crossfit_v5.parquet", ["match_id", "event_id", "player_id", "decision"], ds)
    return t


def roles_and_dm(ds: str, P: pd.DataFrame) -> tuple:
    """Task 44's role rule (task44_build lines 165-172) on development eligible passes."""
    per = P.groupby("player_id").agg(n=("event_id", "size"),
                                     **{f"n_{r}": ("position", lambda s, ps=ps: int(s.isin(ps).sum())) for r, ps in ROLE_POSITIONS.items()})
    per = per[per["n"] >= tb.ROLE_MIN_PASSES]
    for r in ROLE_POSITIONS:
        per[f"share_{r}"] = per[f"n_{r}"] / per["n"]
    per["role"] = [next((r for r in ROLE_POSITIONS if row[f"share_{r}"] >= tb.SHARE), "MIXED") for _, row in per.iterrows()]
    if ds == "2015/16":
        dm = set(per.index[(per["share_DM"] >= tb.SHARE) & (per["n"] >= tb.DM_MIN_PASSES)])
        names = pd.read_parquet(E2 / "task44_roles.parquet", columns=["player_id", "player_name"]).set_index("player_id")["player_name"]
    else:
        lb = pd.read_parquet(PROC / "leaderboard_v5c.parquet", columns=["player_id", "player_name", "is_deep_midfield"])
        dm = set(lb.loc[lb["is_deep_midfield"], "player_id"]) & set(P["player_id"])
        names = lb.set_index("player_id")["player_name"]
    return per["role"], dm, names


def g_features(ds: str, t: dict) -> tuple:
    """Event-only g (2015/16: task44_build.G_FEATURES) or Task 42 / Task 35 state g (study)."""
    if ds == "2015/16":
        tb.EV16 = DS[ds]["events"]
        f = pd.concat([tb.event_features(m) for m in sorted(DEV[ds])], ignore_index=True)
        return f[["match_id", "event_id"] + tb.G_FEATURES], tb.G_FEATURES
    vm = read_dev(tb.DATA_DIR / "processed" / "engine_v2" / "value_model_rows_v5.parquet",
                  ["match_id", "event_id"] + [c for c in F_STATE_FEATURES if c not in ("under_pressure", "period", "minute")], ds)
    return vm, F_STATE_FEATURES


def crossfit_g(df: pd.DataFrame, feats: list, y: str) -> np.ndarray:
    sub = df[df[y].notna()]
    oof = pd.Series(np.nan, index=df.index)
    for k in range(N_FOLDS):
        tr, te = sub[sub["fold"] != k], sub[sub["fold"] == k]
        m = xgb.XGBRegressor(**XGB_REGRESSOR_KWARGS).fit(tr[feats].astype(float), tr[y].astype(float))
        oof.loc[te.index] = m.predict(te[feats].astype(float))
    return oof.values


def unit_frame(ds: str, t: dict, kind: str, gf: pd.DataFrame, gcols: list, role: pd.Series) -> pd.DataFrame:
    base = t["receptions"] if kind == "rec" else t["passes"]
    cols = ["match_id", "event_id", "player_id", "team", "x", "y_f3", "poss_xg", "fold", "under_pressure", "period", "minute"]
    cols += ["keep_spell"] if kind == "rec" else ["pass_complete"]
    d = base[cols].copy()
    extra = [c for c in gcols if c not in d.columns]
    d = d.merge(gf[["match_id", "event_id"] + extra], on=["match_id", "event_id"], how="left")
    d["y_f3"] = np.where(d["x"] < F3_X, d["y_f3"], np.nan)
    d["role"] = d["player_id"].map(role).fillna("NONE")
    ctl = "keep_spell" if kind == "rec" else "pass_complete"
    for y in ("y_f3", "poss_xg", ctl):
        d[f"g_{y}"] = crossfit_g(d, gcols, y)
    st = stats_table(d, ctl, "mean", None)
    d = d.merge(other_match(st, "mean", 100, 1).rename(columns={"S_raw": "S_ctl"}), on=["player_id", "match_id"], how="left")
    return d


def ptest(d: pd.DataFrame, S: pd.DataFrame, y: str, ctl: str) -> dict:
    dd = d.merge(S, on=["player_id", "match_id"], how="left")
    res = tp.fe_fit(dd, y, f"g_{y}")
    ids = set(dd.loc[dd["S_raw"].notna() & dd[y].notna() & dd[f"g_{y}"].notna(), "event_id"])
    c = dd[dd["event_id"].isin(ids)].drop(columns=["S_raw"]).rename(columns={"S_ctl": "S_raw"})
    res["control"] = tp.fe_fit(c, ctl, f"g_{ctl}")
    res["dummy_check"] = safe_dummy_check(dd, y, f"g_{y}")
    return {k: res[k] for k in ("coef_per_sd", "coef_per_sd_per100", "se", "ci95_per100", "p", "n_rows", "n_players",
                                "y_mean", "dummy_check")} | {"control": {k: res["control"][k] for k in
                                                                        ("coef_per_sd_per100", "ci95_per100", "p", "n_rows")}}


# ---------------------------------------------------------------- main
def run(ds: str) -> dict:
    mem_gate(f"{ds}: tests")
    t = load(ds)
    P, R = t["passes"], t["receptions"]
    role, dm, names = roles_and_dm(ds, P)
    sp = specs(ds)
    out = {"n_dev_matches": len(DEV[ds]), "n_dm": len(dm), "n_players_with_role": int(len(role)),
           "category_share_all": P["category"].value_counts(normalize=True).to_dict(),
           "category_share_dm": P[P["player_id"].isin(dm)]["category"].value_counts(normalize=True).to_dict()}
    ST = {m: stats_table(t[s[0]], s[1], s[2], s[3]) for m, s in sp.items()}
    vals = {m: player_values(ST[m], sp[m][2], sp[m][4], sp[m][5]) for m in sp}
    out["n_players_meeting_floor"] = {m: {"all": int(v.notna().sum()), "DM": int(v[v.index.isin(dm)].notna().sum())}
                                      for m, v in vals.items()}
    out["distribution_DM"] = {m: v[v.index.isin(dm)].describe().to_dict() for m, v in vals.items()}

    new = [m for m in sp if m.startswith("M")]
    # D1
    out["D1"] = {m: {"DM": r1(ST[m], sp[m][2], sp[m][5], MIN_MATCHES[ds], dm), "all": r1(ST[m], sp[m][2], sp[m][5], MIN_MATCHES[ds])}
                 for m in sp}
    print(f"  {ds} D1 DM: {({m: (v['DM']['median'], v['DM']['n_players']) for m, v in out['D1'].items()})}", flush=True)

    # D3 (units: receptions for M1-M3, passes for M4-M6)
    gf, gcols = g_features(ds, t)
    U = {"rec": unit_frame(ds, t, "rec", gf, gcols, role), "pass": unit_frame(ds, t, "pass", gf, gcols, role)}
    d3 = {}
    for m in [x for x in new if not x.startswith(("M2_", "M4_KEEP", "M6_on"))]:
        kind = "rec" if m[:2] in ("M1", "M2", "M3") else "pass"
        S = other_match(ST[m], sp[m][2], sp[m][4], sp[m][5])
        ctl = "keep_spell" if kind == "rec" else "pass_complete"
        for grp in ("DM", "all"):
            d = U[kind] if grp == "all" else U[kind][U[kind]["player_id"].isin(dm)]
            for y in ("y_f3", "poss_xg"):
                try:
                    d3[f"{m}|{grp}|{y}"] = ptest(d, S, y, ctl)
                except Exception as e:  # noqa: BLE001 -- recorded, not hidden
                    d3[f"{m}|{grp}|{y}"] = {"error": repr(e)}
    out["D3"] = d3
    print(f"  {ds} D3 done ({len(d3)} cells)", flush=True)

    # D4 (within DMs)
    comps = ["PR2_flag_keep", "W", "MOVE_ON_SPEED", "HOLD_VARIATION"]
    d4 = {}
    for m in new:
        for c in comps:
            j = pd.concat([vals[m], vals[c]], axis=1).loc[lambda x: x.index.isin(dm)].dropna()
            r = float(j.iloc[:, 0].corr(j.iloc[:, 1])) if len(j) >= 3 else None
            d4[f"{m}|{c}"] = {"n": len(j), "r": r, "ci95": fisher(r, len(j)) if r is not None else None}
    out["D4"] = d4

    # D5
    rng_seed = 20260928
    d5 = {}
    for m in new:
        v = vals[m].dropna()
        df = pd.DataFrame({"sb_player_id": v.index.astype(float), "m": v.values})
        df["role"] = df["sb_player_id"].map(role)
        l_ids = set()
        for nm in LIST_L:
            hits = [p for p in v.index if isinstance(names.get(p), str) and name_matches(nm, names.get(p))]
            if len(hits) == 1:
                l_ids.add(float(hits[0]))
        res = perm_test(df.dropna(subset=["role"]), l_ids, np.random.default_rng(rng_seed))
        res["present_names"] = [names.get(int(p["sb_player_id"])) for p in res.get("present", [])]
        res["declared_direction"] = "higher" if m in ("M1", "M2", "M5") else "none"
        d5[m] = res
    out["D5"] = d5
    return {"out": out, "vals": vals, "ST": ST, "specs": sp, "dm": dm, "t": t, "U": U, "role": role}


def d2(res: dict) -> dict:
    """2015/16 development club context vs study development national-team context; Task 46 A-ii recipe."""
    a16, ast = res["2015/16"], res["study"]
    out = {}
    for m in ("M2", "M3_speed", "M4_ACCEL", "M4_SLOW", "M4_SWITCH", "M6"):
        key, col, _, _, floor, sign = a16["specs"][m]
        u16 = a16["t"][key]
        ust = ast["t"][key]
        cs = pd.read_csv(Path(__file__).parent.parent.parent / "docs" / "splits" / "tempo_split.csv")
        intl_ids = set(cs.loc[(cs["dataset"] == "study") & (cs["half"] == "DEVELOPMENT")
                              & np.array([(c, s) in INTL for c, s in zip(cs["competition_id"], cs["season_id"])]), "match_id"])
        club_ids = set(cs.loc[(cs["dataset"] == "study") & (cs["half"] == "DEVELOPMENT"), "match_id"]) - intl_ids

        def arrays(u, ids=None):
            u = u.dropna(subset=[col])
            if ids is not None:
                u = u[u["match_id"].isin(ids)]
            g = u.groupby("player_id")[col]
            return {p: sign * x.to_numpy(float) for p, x in g if len(x) >= floor}
        a = arrays(u16)
        b = arrays(ust, intl_ids)
        pa = sorted(set(a) & set(b))
        r = {"floor": floor, "n_players": len(pa)}
        if len(pa) >= 4:
            r.update(disattenuated(a, b, sb.SEED))
            dmids = res["2015/16"]["dm"] | res["study"]["dm"]
            ad = {p: v for p, v in a.items() if p in dmids}
            r["dm_n_players"] = len(set(ad) & set(b))
            if r["dm_n_players"] >= 4:
                r["dm"] = disattenuated(ad, b, sb.SEED)
        ca, cb = arrays(ust, club_ids), b
        movers = sorted(set(ca) & set(cb))
        r["A_i_movers_study_dev"] = len(movers)
        if len(movers) >= 15:
            r["A_i"] = disattenuated(ca, cb, sb.SEED)
        out[m] = r
        print(f"  D2 {m}: {json.dumps(r, default=str)[:300]}", flush=True)
    return out


def k1(res: dict, ds: str) -> dict:
    a = res[ds]
    ms = ["PR2_flag_keep", "W"] + (["Decision", "M1"] if ds == "study" else []) + ["M2", "M3_speed", "M4_ACCEL", "M4_SLOW"] \
        + (["M5"] if ds == "study" else []) + ["M6"]
    V = pd.DataFrame({m: a["vals"][m] for m in ms})
    V = V[V.index.isin(a["dm"])]
    rel = {m: a["out"]["D1"][m]["DM"]["median"] for m in ms}
    rng = np.random.default_rng(SEED)
    out = {"reliability_DM_D1": rel, "pairs": {}}
    boots = [rng.integers(0, len(V), len(V)) for _ in range(1000)]
    for i, x in enumerate(ms):
        for y in ms[i + 1:]:
            j = V[[x, y]].dropna()
            n = len(j)
            if n < 4:
                out["pairs"][f"{x}|{y}"] = {"n": n}
                continue
            r = float(j[x].corr(j[y]))
            den = np.sqrt(rel[x] * rel[y]) if rel[x] and rel[y] and rel[x] > 0 and rel[y] > 0 else np.nan
            bs = []
            Vx = V[[x, y]].to_numpy(float)
            for b in boots:
                s = Vx[b]
                s = s[np.isfinite(s).all(1)]
                if len(s) >= 4:
                    bs.append(np.corrcoef(s[:, 0], s[:, 1])[0, 1])
            bs = np.array(bs)
            out["pairs"][f"{x}|{y}"] = {"n": n, "r": r, "r_ci95": [float(np.nanpercentile(bs, 2.5)), float(np.nanpercentile(bs, 97.5))],
                                        "r_disatt": float(r / den) if np.isfinite(den) else None,
                                        "r_disatt_ci95": [float(np.nanpercentile(bs / den, 2.5)), float(np.nanpercentile(bs / den, 97.5))]
                                        if np.isfinite(den) else None}
    pcs = ["PR2_flag_keep", "Decision", "M4_ACCEL", "M5"] if ds == "study" else ["PR2_flag_keep", "W", "M4_ACCEL", "M6"]
    Z = V[pcs].dropna()
    ev = np.sort(np.linalg.eigvalsh(np.corrcoef(Z.to_numpy(float).T)))[::-1]
    out["pc1"] = {"measures": pcs, "n_players": len(Z), "share_pc1": float(ev[0] / ev.sum()), "eigenvalues": ev.tolist()}
    return out


def k2(res: dict, ds: str) -> dict:
    a = res[ds]
    d = a["U"]["pass"][a["U"]["pass"]["player_id"].isin(a["dm"])].copy()
    sp = a["specs"]
    base = ["PR2_flag_keep"] + (["Decision"] if ds == "study" else [])
    tempo = ["M1", "M2", "M3_speed", "M4_ACCEL", "M4_SLOW", "M4_SWITCH", "M5", "M6"] if ds == "study" else \
        ["M2", "M3_speed", "M4_ACCEL", "M4_SLOW", "M4_SWITCH", "M6"]
    for m in base + tempo:
        S = other_match(a["ST"][m], sp[m][2], sp[m][4], sp[m][5]).rename(columns={"S_raw": m})
        d = d.merge(S, on=["player_id", "match_id"], how="left")
    out = {}
    for y in ("y_f3", "poss_xg"):
        for m in tempo:
            rows = d.dropna(subset=[m] + base + [y, f"g_{y}"])
            try:
                alone = fit_multi(rows, y, [m], f"g_{y}")
                joint = fit_multi(rows, y, [m] + base, f"g_{y}")
                bonly = fit_multi(rows, y, base, f"g_{y}")
                pick = lambda r, c: {k: r[c][k] for k in ("coef_per_sd_per100", "ci95_per100", "p")}
                out[f"{m}|{y}"] = {"n_rows": len(rows), "n_players": int(rows["player_id"].nunique()),
                                   "tempo_alone": pick(alone, m), "tempo_with_base": pick(joint, m),
                                   **{f"{b}_alone": pick(bonly, b) for b in base},
                                   **{f"{b}_with_tempo": pick(joint, b) for b in base}}
            except Exception as e:  # noqa: BLE001 -- recorded, not hidden
                out[f"{m}|{y}"] = {"n_rows": len(rows), "error": repr(e)}
    return out


def main():
    print("Task 52 tests (DEVELOPMENT half only; report only) ...")
    res = {ds: run(ds) for ds in DS}
    summary = {ds: res[ds]["out"] for ds in res}
    summary["D2"] = d2(res)
    summary["K1"] = {ds: k1(res, ds) for ds in res}
    summary["K2"] = {ds: k2(res, ds) for ds in res}
    summary["existing_table_reads"] = READS
    summary["memory_log"] = MEM_LOG
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2, default=str))
    print(f"Wrote {SUMMARY_PATH}")


if __name__ == "__main__":
    main()
