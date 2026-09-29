"""
Task 46, Part A: does press resistance (PR2_flag_keep, Task 44 Step 2's
definition, unadjusted) travel with the player across teams?
docs/specs/task-46-movers-and-spatial-physical.md. Development task.

Also lists the RESERVED competition-seasons by id from directory names
only (no reserved file is opened).

A-i (study sample): units = player x team context (team x competition x
    season), pressured receptions with a spell outcome. Movers = Study B's
    definition (a club context and an international context, per
    task04_situation_context's CLUB/INTL sets), every used context >= 30
    pressured receptions. PH-B2 via task26_step6_study_b.ph_b2 unchanged
    (the per-unit value is passed in its `decision_new` column). Variance
    split via reml_crossed.fit_reml with Study B's parametric-bootstrap
    interval (method_ii), on units >= 30, covariates = Study B's zone shares
    (share_defensive, share_final); Study B's pressure share is dropped
    because it is constant (every unit is pressured).
A-ii: 2015/16 club score (>= 50 pressured receptions) vs study-sample
    national-team score (>= 30), same disattenuation and bootstrap recipe.

Run: python src/engine_v2/task46_part_a.py
"""
import json
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent / "decision_engine"))
from reml_crossed import fit_reml  # noqa: E402
from task04_situation_context import CLUB_COMPETITIONS, INTL_COMPETITIONS  # noqa: E402
import task26_step6_study_b as sb  # noqa: E402
from crossfit import FOLDS_PATH  # noqa: E402
from validation_common import match_competition_lookup  # noqa: E402
from task44_gate import receipt_flags, fit_baseline, T43_SPELLS, T43_PRESSURED, EV_DIR  # noqa: E402
from task44_build import RECEPTIONS_PATH as R16_PATH  # noqa: E402

warnings.filterwarnings("ignore")

DATA_DIR = Path(__file__).parent.parent.parent / "data"
OPEN = DATA_DIR / "raw_1516" / "open-data-master" / "data" / "matches"
LEADERBOARD_V5C_PATH = DATA_DIR / "processed" / "leaderboard_v5c.parquet"
STUDY_PR_PATH = DATA_DIR / "processed" / "engine_v2" / "task46_study_pr_flag.parquet"
SUMMARY_PATH = DATA_DIR / "engine_v2_task46_part_a.json"
MIN_CTX = 30
MIN_1516 = 50
X_COLS = ["share_defensive", "share_final"]
HOLDOUT = {(53, 106), (53, 315), (72, 107)}
USED_1516 = {(c, 27) for c in (2, 7, 9, 11, 12)}


def reserved_listing() -> list:
    used = set(CLUB_COMPETITIONS) | set(INTL_COMPETITIONS) | HOLDOUT | USED_1516
    out = []
    for comp_dir in sorted(OPEN.iterdir(), key=lambda p: int(p.name)):
        for f in sorted(comp_dir.iterdir()):
            key = (int(comp_dir.name), int(f.stem))
            if key not in used:
                out.append(list(key))
    return out


def disattenuated(a: dict, b: dict, seed: int) -> dict:
    """PH-B2's recipe for two per-player arrays of unit values (side a, side b)."""
    pids = sorted(set(a) & set(b))
    ma = np.array([a[p].mean() for p in pids])
    mb = np.array([b[p].mean() for p in pids])
    rel_a = sb.split_half_reliability([a[p] for p in pids], sb.N_SPLITS_PH_B2, seed)
    rel_b = sb.split_half_reliability([b[p] for p in pids], sb.N_SPLITS_PH_B2, seed + 1)
    r_obs = float(np.corrcoef(ma, mb)[0, 1])
    res = {"n_players": len(pids), "rel_a": rel_a, "rel_b": rel_b, "r_obs": r_obs}
    if rel_a < 0.10 or rel_b < 0.10:
        return {**res, "unmeasurable": True}
    res["r_true"] = float(np.clip(r_obs / np.sqrt(rel_a * rel_b), -1, 1))
    rng = np.random.default_rng(seed)
    idx = np.arange(len(pids))
    boot = np.empty(sb.N_BOOTSTRAP)
    for k in range(sb.N_BOOTSTRAP):
        d = rng.choice(idx, size=len(idx), replace=True)
        r = np.corrcoef(ma[d], mb[d])[0, 1]
        ra = sb.split_half_reliability([a[pids[i]] for i in d], sb.N_SPLITS_PH_B2_BOOT, seed + 1000 + k)
        rb = sb.split_half_reliability([b[pids[i]] for i in d], sb.N_SPLITS_PH_B2_BOOT, seed + 2000 + k)
        boot[k] = np.clip(r / np.sqrt(max(ra, 1e-8) * max(rb, 1e-8)), -1, 1)
    res["r_true_ci"] = [float(np.nanpercentile(boot, 2.5)), float(np.nanpercentile(boot, 97.5))]
    return res


def main():
    print("Task 46 Part A ...")
    reserved = reserved_listing()
    print(f"  RESERVED (not opened): {len(reserved)} competition-seasons: {reserved}")

    folds = pd.read_csv(FOLDS_PATH)
    ev_mids = {int(p.stem) for p in EV_DIR.glob("*.parquet")}
    folds = folds[folds["match_id"].isin(ev_mids)]
    fold_of = dict(zip(folds["match_id"], folds["fold"]))
    mids = sorted(fold_of)
    rec = pd.concat([receipt_flags(m) for m in mids], ignore_index=True)
    rec = rec.merge(pd.read_parquet(T43_SPELLS, columns=["match_id", "event_id", "keep_spell", "fwd_spell"]),
                    on=["match_id", "event_id"], how="left")
    pr = rec[rec["pressured_flag"] & rec["keep_spell"].notna()].reset_index(drop=True)
    fit_baseline(pr, fold_of)
    t43 = pd.read_parquet(T43_PRESSURED, columns=["player_id", "pr2_keep"]).groupby("player_id")["pr2_keep"].agg(["mean", "size"])
    t44 = pr.groupby("player_id")["pr2_flag_keep"].agg(["mean", "size"])
    j = t43[t43["size"] >= 50].join(t44[t44["size"] >= 50], lsuffix="_a", rsuffix="_b", how="inner")
    r_chk = float(j["mean_a"].corr(j["mean_b"]))
    assert abs(r_chk - 0.8395) < 5e-4, r_chk  # Task 44 Step 2's gate value, reproduced
    comp = match_competition_lookup()
    pr["competition_id"] = pr["match_id"].map(lambda m: comp[m][0])
    pr["season_id"] = pr["match_id"].map(lambda m: comp[m][1])
    pr.to_parquet(STUDY_PR_PATH)

    g = pr.assign(dfn=(pr["recv_x"] < 40).astype(float), fin=(pr["recv_x"] >= 80).astype(float)) \
          .groupby(["player_id", "team", "competition_id", "season_id"])
    units = g.agg(n_passes=("pr2_flag_keep", "size"), mean_decision=("pr2_flag_keep", "mean"),
                  sd=("pr2_flag_keep", "std"), share_defensive=("dfn", "mean"), share_final=("fin", "mean")).reset_index()
    units = units[units["n_passes"] >= MIN_CTX].copy()
    units["se"] = units["sd"] / np.sqrt(units["n_passes"])
    dm_ids = set(pd.read_parquet(LEADERBOARD_V5C_PATH).query("is_deep_midfield")["player_id"])

    movers = {}
    for pid, gg in units.groupby("player_id"):
        cs = list(zip(gg["competition_id"], gg["season_id"]))
        club = gg[[c in CLUB_COMPETITIONS for c in cs]]
        intl = gg[[c in INTL_COMPETITIONS for c in cs]]
        if len(club) and len(intl):
            movers[pid] = {"club": club, "intl": intl}
    per_pass = pr.rename(columns={"pr2_flag_keep": "decision_new"})
    ai = {"n_units": len(units), "n_players_units": int(units["player_id"].nunique()),
          "n_players_2plus_contexts": int((units.groupby("player_id").size() >= 2).sum())}
    ai["phb2_all"] = sb.ph_b2(units, per_pass, movers)
    ai["phb2_dm"] = sb.ph_b2(units, per_pass, {p: v for p, v in movers.items() if p in dm_ids})
    print(f"  A-i PH-B2 all: {ai['phb2_all']}")
    print(f"  A-i PH-B2 DM: {ai['phb2_dm']}")
    for lab, u in (("all", units), ("dm", units[units["player_id"].isin(dm_ids)])):
        fit = fit_reml(u, x_cols=X_COLS)
        ci = sb.method_ii_parametric_bootstrap(u, fit, X_COLS, sb.SEED)
        ai[f"variance_split_{lab}"] = {"n_units": len(u), "n_players": int(u["player_id"].nunique()),
                                       "fit": fit, "S_ci95_parametric": ci}
        print(f"  A-i variance split {lab}: S={fit['S']:.4f} CI={ci} n_units={len(u)}")

    r16 = pd.read_parquet(R16_PATH, columns=["player_id", "pr2_flag_keep"]).dropna()
    club16 = {p: g["pr2_flag_keep"].values for p, g in r16.groupby("player_id") if len(g) >= MIN_1516}
    intl = pr[[(c, s) in INTL_COMPETITIONS for c, s in zip(pr["competition_id"], pr["season_id"])]]
    intl_s = {p: g["pr2_flag_keep"].values for p, g in intl.groupby("player_id") if len(g) >= MIN_CTX}
    aii = disattenuated(club16, intl_s, sb.SEED)
    aii["dm"] = disattenuated({p: v for p, v in club16.items() if p in dm_ids}, intl_s, sb.SEED)
    aii["time_gap"] = "2015/16 club season vs national-team tournaments Euro 2020 (played 2021), WC 2022 and Euro 2024"
    print(f"  A-ii: {aii}")
    lb = ai["phb2_all"].get("r_true_ci")
    claim = {"travels_all": bool(lb is not None and lb[0] > 0),
             "travels_dm": bool(ai["phb2_dm"].get("r_true_ci") is not None and ai["phb2_dm"]["r_true_ci"][0] > 0)}
    SUMMARY_PATH.write_text(json.dumps({"reserved_not_opened": reserved, "gate_reproduced_r": r_chk, "n_study_pressured": len(pr),
                                        "A_i": ai, "A_ii": aii, "claim": claim}, indent=2, default=str))
    print(f"  claim {claim}; wrote {SUMMARY_PATH}")


if __name__ == "__main__":
    main()
