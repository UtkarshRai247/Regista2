"""
Task 27, Step 3: Study B sensitivity -- is "travels" just role
persisting? A player's role usually stays similar between club and
country, and Decision partly tracks role (xA r=0.56 within position,
Task 26 Section 7). PH-B2's mover correlation (Task 26 Step 6) used raw
stage-1 unit means, so it could reflect role persisting rather than
decision quality travelling.

SENSITIVITY: residualize the stage-1 unit means on the SAME fixed
effects Stage 2 uses (share_defensive, share_final, share_pressure) by
variance-weighted least squares (weight = 1/se^2) ACROSS ALL 2,099
units (not just movers), then recompute PH-B2's mover correlation using
the residualized means in place of raw mean_decision. The Tier 2
verdict is NOT recomputed from this -- reported as a disclosed
sensitivity only, per the brief.

Disclosed interpretation of "identical procedure": the residualization
is applied at the STAGE-1 UNIT level (one row per player x team-context,
matching where the brief says to residualize -- "the stage-1 unit
means"). PH-B2's reliability estimates (rel_club, rel_intl) are a
split-half computation over PER-PASS decision arrays (a different,
lower level than the unit means being residualized here) and are
reused UNCHANGED from Task 26's own Step 6 output -- residualizing
already-aggregated unit means does not touch the per-pass noise
structure reliability measures. Only r_obs (and hence r_true and its
CI) is recomputed, on the residualized unit means.

Run: python src/engine_v2/task27_step3_studyb_sensitivity.py
"""
import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

DATA_DIR = Path(__file__).parent.parent.parent / "data"
UNITS_PATH = DATA_DIR / "processed" / "engine_v2" / "study_b_units_v5.parquet"
TASK26_STUDYB_PATH = DATA_DIR / "engine_v2_task26_step6_study_b.json"
OUT_PATH = DATA_DIR / "engine_v2_task27_step3_studyb_sensitivity.json"

X_COLS = ["share_defensive", "share_final", "share_pressure"]
SEED = 20260920
N_BOOTSTRAP = 1000

CLUB_COMPETITIONS = {(9, 281), (11, 90), (7, 235), (7, 108), (44, 107)}
INTL_COMPETITIONS = {(43, 106), (55, 282), (55, 43)}


def wls_residualize(units: pd.DataFrame) -> pd.Series:
    """mean_decision ~ intercept + X_COLS, weighted by 1/se^2, across
    ALL units. Returns residuals (same index as units)."""
    y = units["mean_decision"].values.astype(float)
    w = 1.0 / (units["se"].values.astype(float) ** 2)
    X = np.column_stack([np.ones(len(units))] + [units[c].values.astype(float) for c in X_COLS])
    sw = np.sqrt(w)
    Xw = X * sw[:, None]
    yw = y * sw
    b, *_ = np.linalg.lstsq(Xw, yw, rcond=None)
    resid = y - X @ b
    return pd.Series(resid, index=units.index), b


def build_movers(units: pd.DataFrame):
    movers = {}
    for pid, g in units.groupby("player_id"):
        is_club = g.apply(lambda r: (r["competition_id"], r["season_id"]) in CLUB_COMPETITIONS, axis=1)
        is_intl = g.apply(lambda r: (r["competition_id"], r["season_id"]) in INTL_COMPETITIONS, axis=1)
        club, intl = g[is_club], g[is_intl]
        if len(club) and len(intl):
            movers[pid] = {"club": club, "intl": intl}
    return movers


def weighted_side_means(movers: dict, y_col: str) -> pd.DataFrame:
    rows = []
    for pid, v in movers.items():
        club_mean = float(np.average(v["club"][y_col], weights=v["club"]["n_passes"]))
        intl_mean = float(np.average(v["intl"][y_col], weights=v["intl"]["n_passes"]))
        rows.append({"player_id": pid, "club_mean": club_mean, "intl_mean": intl_mean})
    return pd.DataFrame(rows)


def main():
    print("Task 27 Step 3: Study B sensitivity -- residualized mover correlation ...")
    units = pd.read_parquet(UNITS_PATH)
    print(f"  {len(units)} stage-1 units")

    resid, b = wls_residualize(units)
    units = units.copy()
    units["resid_mean_decision"] = resid
    print(f"  WLS coefficients (intercept, {', '.join(X_COLS)}): {b.tolist()}")

    movers = build_movers(units)
    print(f"  {len(movers)} club+international movers")

    task26 = json.loads(TASK26_STUDYB_PATH.read_text())
    phb2_task26 = task26["phb2"]
    rel_club, rel_intl = phb2_task26["rel_club"], phb2_task26["rel_intl"]
    print(f"  reusing Task 26's own reliability estimates unchanged: rel_club={rel_club:.4f}, rel_intl={rel_intl:.4f}")

    pids_sorted = sorted(movers.keys())
    mover_df_resid = weighted_side_means(movers, "resid_mean_decision").set_index("player_id")
    r_obs_resid = float(mover_df_resid.loc[pids_sorted, "club_mean"].corr(mover_df_resid.loc[pids_sorted, "intl_mean"]))
    print(f"  r_obs (residualized): {r_obs_resid:.4f} (Task 26 raw r_obs was {phb2_task26['r_obs']:.4f})")

    r_true_raw = r_obs_resid / np.sqrt(rel_club * rel_intl)
    r_true = float(np.clip(r_true_raw, -1.0, 1.0))
    print(f"  r_true (residualized): {r_true:.4f} (uncapped: {r_true_raw:.4f})")

    print(f"  bootstrapping ({N_BOOTSTRAP} draws, resampling movers, residualization fixed -- "
          "recomputed once on the full design, not refit inside each draw, since the brief asks to "
          "'bootstrap on the residualised means', i.e. resample the already-residualized values) ...")
    rng = np.random.default_rng(SEED)
    pids_arr = np.array(pids_sorted)
    n_movers = len(pids_arr)
    r_true_boot = np.empty(N_BOOTSTRAP)
    n_capped = 0
    for i in range(N_BOOTSTRAP):
        drawn = rng.choice(pids_arr, size=n_movers, replace=True)
        club_means_b = mover_df_resid.loc[drawn, "club_mean"].values
        intl_means_b = mover_df_resid.loc[drawn, "intl_mean"].values
        r_obs_b = np.corrcoef(club_means_b, intl_means_b)[0, 1]
        r_true_b = r_obs_b / np.sqrt(rel_club * rel_intl)
        if abs(r_true_b) > 1:
            n_capped += 1
        r_true_boot[i] = np.clip(r_true_b, -1.0, 1.0)
    ci = (float(np.percentile(r_true_boot, 2.5)), float(np.percentile(r_true_boot, 97.5)))
    print(f"  r_true 95% CI (residualized): {ci}")

    summary = {
        "n_units": len(units), "wls_coefficients": {"intercept": float(b[0]), **{c: float(v) for c, v in zip(X_COLS, b[1:])}},
        "n_movers": len(movers),
        "task26_raw": {"r_obs": phb2_task26["r_obs"], "r_true": phb2_task26["r_true"], "r_true_ci": phb2_task26["r_true_ci"],
                        "rel_club": rel_club, "rel_intl": rel_intl},
        "sensitivity_residualized": {"r_obs": r_obs_resid, "r_true": r_true, "r_true_uncapped": r_true_raw,
                                       "r_true_ci": ci, "share_capped": n_capped / N_BOOTSTRAP,
                                       "rel_club_reused_unchanged": rel_club, "rel_intl_reused_unchanged": rel_intl},
        "note": "Tier 2 verdict is NOT recomputed from this sensitivity, per the brief -- Task 26's "
                "Tier 2 ALLOWED verdict stands as the pre-registered result.",
    }
    OUT_PATH.write_text(json.dumps(summary, indent=2, default=str))
    print(f"\nWrote {OUT_PATH}")
    return summary


if __name__ == "__main__":
    main()
