"""
Task 16 -- Tempo module, Step 2: per-player-season quantities.

Governing document: docs/specs/analysis-plan-tempo.md sections 2-4,
executed via docs/specs/task-16-tempo.md Step 2.

Run: python src/tempo/metrics.py
"""
import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

from possessions import build_possession_sequences
from time_on_ball import OUT_PATH as TIME_ON_BALL_PATH

warnings.filterwarnings("ignore")

DATA_DIR = Path(__file__).parent.parent.parent / "data"
OUT_PATH = DATA_DIR / "processed" / "tempo_metrics.parquet"
SUMMARY_PATH = DATA_DIR / "tempo_step2_metrics.json"

ONE_TOUCH_S = 0.4
N_BOOT = 1000
RNG_SEED = 42


def match_competition_lookup() -> dict:
    """Independent re-implementation of decompose.match_competition_lookup's
    exact shape, so this module has no import-time dependency on
    src/decision_engine/."""
    lookup = {}
    for f in (DATA_DIR / "raw" / "matches").glob("*.parquet"):
        comp_id, season_id = f.stem.split("_")
        matches = pd.read_parquet(f, columns=["match_id"])
        for mid in matches["match_id"]:
            lookup[int(mid)] = (int(comp_id), int(season_id))
    return lookup


def clustered_bootstrap_diff(a_by_match: dict, b_by_match: dict, agg=np.median,
                              n_boot: int = N_BOOT, seed: int = RNG_SEED) -> dict:
    """a_by_match/b_by_match: {match_id: np.array of values}. Point
    estimate pools all values regardless of which matches they came
    from; the bootstrap resamples the UNION of match ids (with
    replacement) to account for within-match correlation, rebuilding
    both pools from whichever matches were drawn each time."""
    matches = sorted(set(a_by_match) | set(b_by_match))
    all_a = np.concatenate(list(a_by_match.values())) if a_by_match else np.array([])
    all_b = np.concatenate(list(b_by_match.values())) if b_by_match else np.array([])
    if len(all_a) == 0 or len(all_b) == 0:
        return {"point": None, "ci_low": None, "ci_high": None, "n_matches": len(matches), "n_boot_successful": 0}
    point = float(agg(all_a) - agg(all_b))
    if len(matches) < 2:
        return {"point": point, "ci_low": None, "ci_high": None, "n_matches": len(matches), "n_boot_successful": 0}
    rng = np.random.default_rng(seed)
    boots = []
    for _ in range(n_boot):
        sample = rng.choice(matches, size=len(matches), replace=True)
        a_parts = [a_by_match[m] for m in sample if m in a_by_match]
        b_parts = [b_by_match[m] for m in sample if m in b_by_match]
        if a_parts and b_parts:
            boots.append(float(agg(np.concatenate(a_parts)) - agg(np.concatenate(b_parts))))
    ci_low, ci_high = (float(np.percentile(boots, 2.5)), float(np.percentile(boots, 97.5))) if boots else (None, None)
    return {"point": point, "ci_low": ci_low, "ci_high": ci_high,
            "n_matches": len(matches), "n_boot_successful": len(boots)}


def compute_time_on_ball_metrics(tob: pd.DataFrame, comp_lookup: dict) -> pd.DataFrame:
    tob = tob.copy()
    tob["competition_id"] = tob["match_id"].map(lambda m: comp_lookup.get(m, (None, None))[0])
    tob["season_id"] = tob["match_id"].map(lambda m: comp_lookup.get(m, (None, None))[1])

    rows = []
    for (pid, cid, sid), g in tob.groupby(["player_id", "competition_id", "season_id"]):
        n = len(g)
        median_tob = float(g["time_on_ball"].median())
        iqr = float(np.percentile(g["time_on_ball"], 75) - np.percentile(g["time_on_ball"], 25))
        one_touch = float((g["time_on_ball"] < ONE_TOUCH_S).mean())
        sd_tob = float(g["time_on_ball"].std(ddof=1)) if n > 1 else None

        a_by_match = {m: v["time_on_ball"].values for m, v in g[g["under_pressure"]].groupby("match_id")}
        b_by_match = {m: v["time_on_ball"].values for m, v in g[~g["under_pressure"]].groupby("match_id")}
        pressure = clustered_bootstrap_diff(a_by_match, b_by_match, agg=np.median)

        rows.append({
            "player_id": pid, "competition_id": cid, "season_id": sid, "n_involvements": n,
            "median_time_on_ball": median_tob, "iqr_time_on_ball": iqr, "one_touch_share": one_touch,
            "sd_time_on_ball": sd_tob,
            "pressure_delta": pressure["point"], "pressure_delta_ci_low": pressure["ci_low"],
            "pressure_delta_ci_high": pressure["ci_high"], "pressure_delta_n_matches": pressure["n_matches"],
        })
    return pd.DataFrame(rows)


def compute_pace_metrics(seq: pd.DataFrame, comp_lookup: dict) -> pd.DataFrame:
    seq = seq.copy()
    seq["competition_id"] = seq["match_id"].map(lambda m: comp_lookup.get(m, (None, None))[0])
    seq["season_id"] = seq["match_id"].map(lambda m: comp_lookup.get(m, (None, None))[1])
    seq_valid = seq[seq["pace"].notna()]

    # index: for each (match, team), the list of (pace, passer_ids) of its sequences
    by_match_team = {k: list(v[["pace", "passer_ids"]].itertuples(index=False, name=None))
                      for k, v in seq_valid.groupby(["match_id", "team"])}

    # which players passed in which (match, team, competition, season)
    player_match_team = {}
    for _, r in seq_valid.iterrows():
        for pid in r["passer_ids"]:
            player_match_team.setdefault((pid, r["competition_id"], r["season_id"]), set()).add((r["match_id"], r["team"]))

    rows = []
    for (pid, cid, sid), match_teams in player_match_team.items():
        with_by_match, without_by_match = {}, {}
        own_paces = []
        for (mid, team) in match_teams:
            seqs = by_match_team.get((mid, team), [])
            with_vals = [pace for pace, passers in seqs if pid in passers]
            without_vals = [pace for pace, passers in seqs if pid not in passers]
            if with_vals:
                with_by_match[mid] = np.array(with_vals)
                own_paces.extend(with_vals)
            if without_vals:
                without_by_match[mid] = np.array(without_vals)
        pace = clustered_bootstrap_diff(with_by_match, without_by_match, agg=np.mean)
        tempo_variation = float(np.std(own_paces, ddof=1)) if len(own_paces) > 1 else None
        rows.append({
            "player_id": pid, "competition_id": cid, "season_id": sid,
            "n_sequences_with": len(own_paces),
            "pace_delta": pace["point"], "pace_delta_ci_low": pace["ci_low"],
            "pace_delta_ci_high": pace["ci_high"], "pace_delta_n_matches": pace["n_matches"],
            "tempo_variation": tempo_variation,
        })
    return pd.DataFrame(rows)


def main():
    print("Step 2: loading time_on_ball and building possession sequences ...")
    tob = pd.read_parquet(TIME_ON_BALL_PATH)
    comp_lookup = match_competition_lookup()

    print("  computing time-on-ball metrics (median, IQR, one-touch share, pressure_delta) ...")
    tob_metrics = compute_time_on_ball_metrics(tob, comp_lookup)
    print(f"  {len(tob_metrics)} player-competition-season rows")

    print("  building possession sequences (reused Task 11 definition, reimplemented independently) ...")
    seq = build_possession_sequences()

    print("  computing pace_delta / tempo_variation ...")
    pace_metrics = compute_pace_metrics(seq, comp_lookup)
    print(f"  {len(pace_metrics)} player-competition-season rows")

    merged = tob_metrics.merge(pace_metrics, on=["player_id", "competition_id", "season_id"], how="outer")
    merged.to_parquet(OUT_PATH)

    summary = {
        "n_units_time_on_ball": len(tob_metrics), "n_units_pace": len(pace_metrics),
        "n_units_merged": len(merged),
    }
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2, default=str))
    print(f"\nWrote {OUT_PATH} and {SUMMARY_PATH}")
    return merged


if __name__ == "__main__":
    main()
