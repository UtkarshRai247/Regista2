"""
Task 39: does tempo show up in results? Task 35's pass-level
out-of-match test (P-test) for MOVE_ON_SPEED and HOLD_VARIATION, study
sample only. docs/specs/task-39-tempo-ptest.md.

Two inputs had to be regenerated (not changed) because they were never
saved in the form this test needs:
1. Per-pass tempo residuals WITH match_id/event_id. The stored
   tempo_redesign_{move,hold}_residuals_v2.parquet keep only
   player/competition/season. redesign_metrics.main(), patched exactly as
   redesign_metrics_v2.py patches it (Task 26 Step 2), returns move_df /
   hold_df with the ids; it is re-run with every output path redirected
   to new Task 39 files, and its residuals are asserted identical (order
   and values) to the stored v2 files.
2. Task 35's pass-level g_oof (not persisted). Regenerated with
   task35_ptest.crossfit_g on the identical inputs, then Task 35's own (a)
   v5-Decision and positive-control results are asserted to reproduce
   exactly from its saved JSON before any tempo number is computed.

S per (passer, match) is leave-one-match-out over all his other matches:
S_move = mean of move residuals, S_hold = SD (ddof=1) of hold residuals --
the preregistered per-player definitions (redesign_metrics.py) applied to
the complement -- requiring >= 100 tempo-eligible passes of that metric
elsewhere. Model: task35_ptest.fe_fit (Y ~ S + g + role FE + team-match FE,
SE clustered by passer).

Run: python src/engine_v2/task39_tempo_ptest.py
"""
import json
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from statsmodels.stats.multitest import multipletests

sys.path.append(str(Path(__file__).parent.parent / "tempo"))
import redesign_metrics_v2  # noqa: E402,F401 -- applies Task 26 Step 2's patch to redesign_metrics
import redesign_metrics as rm  # noqa: E402
import task33_step3_f_state as tfs  # noqa: E402
import task35_ptest as tp  # noqa: E402
from task32_step4 import assign_roles  # noqa: E402
from crossfit import FOLDS_PATH  # noqa: E402

warnings.filterwarnings("ignore")

DATA_DIR = Path(__file__).parent.parent.parent / "data"
V2_MOVE = DATA_DIR / "processed" / "tempo_redesign_move_residuals_v2.parquet"
V2_HOLD = DATA_DIR / "processed" / "tempo_redesign_hold_residuals_v2.parquet"
LEADERBOARD_V5C_PATH = DATA_DIR / "processed" / "leaderboard_v5c.parquet"
TASK35_PATH = DATA_DIR / "engine_v2_task35_ptest.json"
SUMMARY_PATH = DATA_DIR / "engine_v2_task39_tempo_ptest.json"
MIN_ELSEWHERE = 100


def tempo_residuals_with_ids() -> tuple:
    rm.OUT_PATH = DATA_DIR / "processed" / "tempo_task39_metrics.parquet"
    rm.MOVE_RESID_PATH = DATA_DIR / "processed" / "tempo_task39_move_residuals.parquet"
    rm.HOLD_RESID_PATH = DATA_DIR / "processed" / "tempo_task39_hold_residuals.parquet"
    rm.SUMMARY_PATH = DATA_DIR / "tempo_task39_redesign_rerun.json"
    _, move_df, hold_df, _ = rm.main()
    for new, old_path in ((move_df, V2_MOVE), (hold_df, V2_HOLD)):
        old = pd.read_parquet(old_path)
        assert len(new) == len(old)
        assert (new["player_id"].values == old["player_id"].values).all()
        assert np.allclose(new["residual"].values, old["residual"].values, rtol=0, atol=1e-12)
    return move_df[["match_id", "event_id", "player_id", "residual"]], hold_df[["match_id", "event_id", "player_id", "residual"]]


def loo(resid: pd.DataFrame, stat: str) -> pd.DataFrame:
    """Per (player, match): the metric over the player's OTHER matches (NaN if < MIN_ELSEWHERE rows)."""
    r = resid.assign(x2=resid["residual"] ** 2)
    pm = r.groupby(["player_id", "match_id"]).agg(s=("residual", "sum"), q=("x2", "sum"), n=("residual", "size"))
    tot = pm.groupby("player_id").sum()
    return pm, tot, stat


def s_for_rows(rows: pd.DataFrame, resid: pd.DataFrame, stat: str) -> pd.DataFrame:
    pm, tot, _ = loo(resid, stat)
    key = pd.MultiIndex.from_arrays([rows["player_id"], rows["match_id"]])
    own = pm.reindex(key).fillna(0.0).to_numpy()
    tt = tot.reindex(rows["player_id"]).fillna(0.0).to_numpy()
    s, q, n = (tt - own).T
    with np.errstate(invalid="ignore", divide="ignore"):
        mean = s / n
        sd = np.sqrt(np.clip((q - s ** 2 / n) / (n - 1), 0, None))
    val = mean if stat == "mean" else sd
    out = rows.copy()
    out["complement_count"] = n
    out["S_raw"] = np.where(n >= MIN_ELSEWHERE, val, np.nan)
    return out


def main():
    print("Task 39: tempo P-test ...")
    # --- Task 35's pass table, rebuilt exactly ---
    folds = pd.read_csv(FOLDS_PATH)
    ev_mids = {int(p.stem) for p in tp.EV_DIR.glob("*.parquet")}
    folds = folds[folds["match_id"].isin(ev_mids)]
    fold_of = dict(zip(folds["match_id"], folds["fold"]))
    mids = sorted(fold_of)
    y_all = pd.concat([tp.net_xg_after(m) for m in mids], ignore_index=True)
    feat = tfs.build_feature_table(mids).merge(y_all, on=["match_id", "event_id"], how="left")
    feat["pass_complete"] = feat["pass_complete"].astype(float)
    feat["g_xg"], r2_xg = tp.crossfit_g(feat, "y_net_xg", fold_of)
    feat["g_cmp"], r2_cmp = tp.crossfit_g(feat, "pass_complete", fold_of)
    v5 = pd.read_parquet(tp.CROSSFIT_V5_PATH, columns=["match_id", "event_id", "team", "player_id", "decision"])
    v5 = v5.merge(feat[["match_id", "event_id", "y_net_xg", "pass_complete", "g_xg", "g_cmp"]],
                  on=["match_id", "event_id"], how="inner")
    lb = pd.read_parquet(LEADERBOARD_V5C_PATH, columns=["player_id", "is_deep_midfield"])
    roles = assign_roles(set(lb["player_id"])).set_index("player_id")["role"]
    v5["role"] = v5["player_id"].map(roles).fillna("NONE")
    dm_ids = set(lb.loc[lb["is_deep_midfield"], "player_id"])

    t35 = json.loads(TASK35_PATH.read_text())["step2"]
    repro = {}
    for key, col, y, g in (("a_decision_v5", "decision", "y_net_xg", "g_xg"), ("control", "pass_complete", "pass_complete", "g_cmp")):
        d = tp.add_s(v5, col)
        d["role"] = d["player_id"].map(roles).fillna("NONE")
        r = tp.fe_fit(d, y, g)
        repro[key] = {"coef": r["coef_per_sd"], "se": r["se"], "task35_coef": t35[key]["coef_per_sd"], "task35_se": t35[key]["se"]}
        assert np.isclose(r["coef_per_sd"], t35[key]["coef_per_sd"], rtol=1e-9, atol=0), repro[key]
        assert np.isclose(r["se"], t35[key]["se"], rtol=1e-9, atol=0), repro[key]
    print(f"  Task 35 reproduced exactly: {repro}")
    control_all = tp.add_s(v5, "pass_complete")
    control_all["role"] = control_all["player_id"].map(roles).fillna("NONE")

    # --- tempo residuals with ids (asserted identical to the stored v2 files) ---
    move, hold = tempo_residuals_with_ids()
    ids = set(v5["event_id"])
    mapping = {name: {"n_tempo_passes": len(r), "n_in_task35_rows": int(r["event_id"].isin(ids).sum()),
                      "share_in_task35_rows": float(r["event_id"].isin(ids).mean())}
               for name, r in (("move", move), ("hold", hold))}
    mapping["task35_rows"] = len(v5)
    mapping["task35_rows_that_are_move_eligible"] = int(v5["event_id"].isin(set(move["event_id"])).sum())
    mapping["task35_rows_that_are_hold_eligible"] = int(v5["event_id"].isin(set(hold["event_id"])).sum())
    print(f"  mapping: {mapping}")

    data = {"S_move": s_for_rows(v5, move, "mean"), "S_hold": s_for_rows(v5, hold, "sd")}
    for d in data.values():
        assert (d.loc[d["S_raw"].notna(), "complement_count"] >= MIN_ELSEWHERE).all()

    def family(restrict: set = None) -> dict:
        out = {}
        for name, d in data.items():
            rows = d if restrict is None else d[d["player_id"].isin(restrict)]
            res = tp.fe_fit(rows, "y_net_xg", "g_xg")
            keep = set(rows.loc[rows["S_raw"].notna(), "event_id"])
            ctrl_rows = control_all[control_all["event_id"].isin(keep)]
            res["control_on_same_rows"] = tp.fe_fit(ctrl_rows, "pass_complete", "g_cmp")
            out[name] = res
        adj = multipletests([out[k]["p"] for k in ("S_move", "S_hold")], method="holm")[1]
        for k, a in zip(("S_move", "S_hold"), adj):
            out[k]["p_holm"] = float(a)
        for k, r in out.items():
            c = r["control_on_same_rows"]
            print(f"    {k}: n={r['n_rows']} players={r['n_players']} coef100={r['coef_per_sd_per100']:+.4f} "
                  f"CI100={[round(x, 4) for x in r['ci95_per100']]} p={r['p']:.4g} holm={r['p_holm']:.4g} "
                  f"MDE100={r['mde_80_per100']:.4f} | control coef={c['coef_per_sd']:+.4f} p={c['p']:.3g}")
        return out

    print("  Step 2 (all passers):")
    step2 = family()
    print("  Step 3 (111 deep midfielders):")
    step3 = family(dm_ids)

    summary = {"g_oof_r2": {"net_xg": r2_xg, "completion": r2_cmp}, "task35_reproduction": repro,
               "mapping": mapping, "min_elsewhere": MIN_ELSEWHERE,
               "task35_control_original": t35["control"], "step2": step2, "step3_deep_midfield": step3}
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2, default=str))
    print(f"Wrote {SUMMARY_PATH}")


if __name__ == "__main__":
    main()
