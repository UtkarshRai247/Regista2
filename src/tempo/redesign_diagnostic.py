"""
Task 16b -- Tempo redesign, Step 1: diagnostic (T-2.2). Four checks,
run once, no interpretation beyond what is asked, per Amendment T-2.

Governing document: docs/specs/analysis-plan-tempo.md Amendment T-2,
executed via docs/specs/task-16b-tempo-redesign.md Step 1. Does not
modify any Task 16 file (time_on_ball.py, possessions.py, metrics.py,
reliability.py, relationships.py); re-derives what it needs locally.

Run: python src/tempo/redesign_diagnostic.py
"""
import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

from time_on_ball import is_open_play_pass, parse_timestamp
from possessions import build_possession_sequences, MIN_POSSESSION_PASSES, PASSES_PATH
from metrics import match_competition_lookup
from reliability import spearman_brown, summarize, N_REPEATS, RNG_SEED, THRESHOLDS, GATE_THRESHOLD

warnings.filterwarnings("ignore")

DATA_DIR = Path(__file__).parent.parent.parent / "data"
EVENTS_DIR = DATA_DIR / "raw" / "events"
SUMMARY_PATH = DATA_DIR / "tempo_step1b_diagnostic.json"


def build_new_sequences(verbose: bool = True) -> pd.DataFrame:
    """Same possession-sequence definition as possessions.py, but the
    eligible-pass population is ALL open-play passes (is_open_play_pass
    over raw events), not passes_situation.parquet's matched subset."""
    match_ids = sorted(int(p.stem) for p in EVENTS_DIR.glob("*.parquet"))
    records = []
    n_zero_duration = 0
    for i, mid in enumerate(match_ids):
        ev = pd.read_parquet(EVENTS_DIR / f"{mid}.parquet")
        ev = ev.sort_values("index").reset_index(drop=True)
        ev["t"] = ev["timestamp"].apply(parse_timestamp)
        pp = ev[is_open_play_pass(ev)].copy()
        pp = pp[pp["team"] == pp["possession_team"]]
        for poss_id, g in pp.groupby("possession"):
            if len(g) < MIN_POSSESSION_PASSES:
                continue
            g_sorted = g.sort_values("index")
            duration = float(g_sorted["t"].iloc[-1] - g_sorted["t"].iloc[0])
            pace = (len(g_sorted) / duration) if duration > 0 else None
            if duration <= 0:
                n_zero_duration += 1
            records.append({
                "match_id": mid, "possession": poss_id, "team": g_sorted["possession_team"].iloc[0],
                "n_passes": len(g_sorted), "duration_s": duration, "pace": pace,
                "passer_ids": frozenset(g_sorted["player_id"].tolist()),
                "start_min": float(g_sorted["minute"].iloc[0] + g_sorted["second"].iloc[0] / 60),
            })
        if verbose and (i + 1) % 50 == 0:
            print(f"  new sequences: {i + 1}/{len(match_ids)} matches")
    df = pd.DataFrame(records)
    if verbose:
        print(f"  {len(df)} new sequences (>= {MIN_POSSESSION_PASSES} passes), "
              f"{n_zero_duration} with zero/negative duration")
    return df


def d1_contamination(old_seq: pd.DataFrame, new_seq: pd.DataFrame) -> dict:
    merged = old_seq.merge(new_seq, on=["match_id", "possession", "team"], suffixes=("_old", "_new"), how="inner")
    diff2 = (merged["n_passes_new"] - merged["n_passes_old"]).abs() >= 2
    return {
        "n_old": int(len(old_seq)), "n_new": int(len(new_seq)),
        "median_n_passes_old": float(old_seq["n_passes"].median()),
        "median_n_passes_new": float(new_seq["n_passes"].median()),
        "median_pace_old": float(old_seq["pace"].dropna().median()),
        "median_pace_new": float(new_seq["pace"].dropna().median()),
        "n_matched_possessions": int(len(merged)),
        "share_n_passes_diff_ge_2": float(diff2.mean()),
    }


def d2_ratio_noise(new_seq: pd.DataFrame) -> dict:
    valid = new_seq[new_seq["pace"].notna()].copy()
    valid["pace_intervals"] = (valid["n_passes"] - 1) / valid["duration_s"]

    def pct(s):
        return {str(p): float(np.percentile(s, p)) for p in (5, 25, 50, 75, 95, 99)}

    return {
        "n": int(len(valid)),
        "pace_n_passes_over_duration": pct(valid["pace"]),
        "pace_intervals_over_duration": pct(valid["pace_intervals"]),
        "share_duration_under_3s": float((valid["duration_s"] < 3).mean()),
    }


def build_on_pitch_windows(mid: int, ev: pd.DataFrame) -> dict:
    """{(player_id): [(start_min, end_min), ...]} for this match, from
    Starting XI (start=0) and Substitution (off/on) events. Cumulative
    'minute' field is used throughout so period resets never enter."""
    last_min = float(ev["minute"].max() + ev.loc[ev["minute"] == ev["minute"].max(), "second"].max() / 60)
    windows = {}
    start_xi = ev[ev["type"] == "Starting XI"]
    for _, row in start_xi.iterrows():
        for p in row["tactics"]["lineup"]:
            windows.setdefault(p["player"]["id"], []).append([0.0, None])
    subs = ev[ev["type"] == "Substitution"].sort_values("index")
    for _, row in subs.iterrows():
        t = float(row["minute"] + row["second"] / 60)
        off_id = row["player_id"]
        if off_id in windows and windows[off_id] and windows[off_id][-1][1] is None:
            windows[off_id][-1][1] = t
        on_id = row["substitution_replacement_id"]
        if pd.notna(on_id):
            windows.setdefault(int(on_id), []).append([t, None])
    for pid, spans in windows.items():
        for span in spans:
            if span[1] is None:
                span[1] = last_min
    return windows


def d3_on_pitch(old_seq: pd.DataFrame, comp_lookup: dict) -> dict:
    old_seq = old_seq.copy()
    old_seq["competition_id"] = old_seq["match_id"].map(lambda m: comp_lookup.get(m, (None, None))[0])
    old_seq["season_id"] = old_seq["match_id"].map(lambda m: comp_lookup.get(m, (None, None))[1])
    valid = old_seq[old_seq["pace"].notna()]
    by_match_team = {k: list(v[["start_min", "passer_ids"]].itertuples(index=False, name=None))
                      for k, v in valid.groupby(["match_id", "team"])}
    player_match_team = {}
    for _, r in valid.iterrows():
        for pid in r["passer_ids"]:
            player_match_team.setdefault((pid, r["competition_id"], r["season_id"]), set()).add((r["match_id"], r["team"]))

    match_ids = sorted(valid["match_id"].unique())
    windows_by_match = {}
    for mid in match_ids:
        ev = pd.read_parquet(EVENTS_DIR / f"{mid}.parquet")
        windows_by_match[mid] = build_on_pitch_windows(mid, ev)

    n_without_total, n_without_offpitch = 0, 0
    for (pid, cid, sid), match_teams in player_match_team.items():
        for (mid, team) in match_teams:
            windows = windows_by_match.get(mid, {}).get(pid, [])
            for start_min, passers in by_match_team.get((mid, team), []):
                if pid in passers:
                    continue
                n_without_total += 1
                on_pitch = any(lo <= start_min <= hi for lo, hi in windows)
                if not on_pitch:
                    n_without_offpitch += 1
    return {
        "n_without_sequences": n_without_total,
        "n_without_offpitch": n_without_offpitch,
        "share_offpitch": (n_without_offpitch / n_without_total) if n_without_total else None,
    }


def d4_split_granularity(old_seq: pd.DataFrame, comp_lookup: dict) -> dict:
    old_seq = old_seq.copy()
    old_seq["competition_id"] = old_seq["match_id"].map(lambda m: comp_lookup.get(m, (None, None))[0])
    old_seq["season_id"] = old_seq["match_id"].map(lambda m: comp_lookup.get(m, (None, None))[1])
    valid = old_seq[old_seq["pace"].notna()]
    by_match_team = {k: list(v[["pace", "passer_ids"]].itertuples(index=False, name=None))
                      for k, v in valid.groupby(["match_id", "team"])}
    player_match_team = {}
    for _, r in valid.iterrows():
        for pid in r["passer_ids"]:
            player_match_team.setdefault((pid, r["competition_id"], r["season_id"]), set()).add((r["match_id"], r["team"]))

    # each player's own "with" sequences, flattened as a list of paces
    player_with_paces = {}
    for key, match_teams in player_match_team.items():
        paces = []
        for (mid, team) in match_teams:
            for pace, passers in by_match_team.get((mid, team), []):
                if key[0] in passers:
                    paces.append(pace)
        player_with_paces[key] = paces

    n_by_unit = {k: len(v) for k, v in player_with_paces.items()}
    results = {}
    for threshold in THRESHOLDS:
        units = [k for k, n in n_by_unit.items() if n >= threshold]
        # fixed "without" pool per unit does not depend on the split
        without_pool = {}
        for key in units:
            pid, cid, sid = key
            match_teams = player_match_team[key]
            vals = []
            for (mid, team) in match_teams:
                for pace, passers in by_match_team.get((mid, team), []):
                    if pid not in passers:
                        vals.append(pace)
            without_pool[key] = vals
        rng = np.random.default_rng(RNG_SEED)
        sb_vals = []
        for _ in range(N_REPEATS):
            h1_vals, h2_vals = [], []
            for key in units:
                paces = player_with_paces[key]
                if len(without_pool[key]) == 0:
                    continue
                idx = rng.permutation(len(paces))
                half = len(paces) // 2
                if half == 0:
                    continue
                p1 = float(np.mean([paces[k] for k in idx[:half]])) - float(np.mean(without_pool[key]))
                p2 = float(np.mean([paces[k] for k in idx[half:2 * half]])) - float(np.mean(without_pool[key]))
                h1_vals.append(p1)
                h2_vals.append(p2)
            if len(h1_vals) >= 3:
                r = pd.Series(h1_vals).corr(pd.Series(h2_vals))
                sb = spearman_brown(r)
                if sb is not None:
                    sb_vals.append(sb)
        results[threshold] = summarize(sb_vals, len(units))
    return results


def main():
    print("Step 1b: diagnostic (T-2.2), four checks ...")
    comp_lookup = match_competition_lookup()

    print("  building OLD sequences (passes_situation.parquet, as shipped in Task 16) ...")
    old_seq = build_possession_sequences(verbose=False)
    match_ids = sorted(old_seq["match_id"].unique())
    passes_elig = pd.read_parquet(PASSES_PATH, columns=["match_id", "event_id"])
    eligible_ids_by_match = passes_elig.groupby("match_id")["event_id"].apply(set).to_dict()
    start_min_lookup = {}
    for mid in match_ids:
        ev = pd.read_parquet(EVENTS_DIR / f"{mid}.parquet")
        ev = ev.sort_values("index").reset_index(drop=True)
        eligible_set = eligible_ids_by_match.get(mid, set())
        pp = ev[ev["id"].isin(eligible_set)]
        pp = pp[pp["team"] == pp["possession_team"]]
        for poss_id, g in pp.groupby("possession"):
            if len(g) < MIN_POSSESSION_PASSES:
                continue
            g_sorted = g.sort_values("index")
            start_min_lookup[(mid, poss_id, g_sorted["possession_team"].iloc[0])] = float(
                g_sorted["minute"].iloc[0] + g_sorted["second"].iloc[0] / 60)
    old_seq["start_min"] = old_seq.apply(
        lambda r: start_min_lookup.get((r["match_id"], r["possession"], r["team"])), axis=1)

    print("  building NEW sequences (ALL open-play passes) ...")
    new_seq = build_new_sequences()

    print("  D1 contamination ...")
    d1 = d1_contamination(old_seq, new_seq)
    print(f"    {d1}")

    print("  D2 ratio noise ...")
    d2 = d2_ratio_noise(new_seq)
    print(f"    {d2}")

    print("  D3 on-pitch ...")
    d3 = d3_on_pitch(old_seq, comp_lookup)
    print(f"    {d3}")

    print("  D4 split granularity (sequence-level pace_delta reliability) ...")
    d4 = d4_split_granularity(old_seq, comp_lookup)
    for th, r in d4.items():
        print(f"    {th}: {r}")

    summary = {"D1_contamination": d1, "D2_ratio_noise": d2, "D3_on_pitch": d3,
               "D4_split_granularity_sequence_level": d4}
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2, default=str))
    print(f"\nWrote {SUMMARY_PATH}")
    return summary


if __name__ == "__main__":
    main()
