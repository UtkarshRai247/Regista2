"""
Task 05 — Study A, DISCOVERY half only. Governed by
docs/specs/analysis-plan-v2.md (plan section 3, Amendment v2-1) and
docs/specs/task-05-study-a-discovery.md.

HARD RULE: the confirmation half is never loaded. Every parquet read in
this file pushes a match_id-in-discovery filter down to pyarrow, so
confirmation rows never enter a DataFrame.

No Gate D, no sensitivity checks (3.6a-d), no realized values here --
those are Task 06. This script only builds pass-level EV gaps, computes
G/P/s/L (+ G's bootstrap CI) for the 107 analyzable pairs, and applies
plan 3.4's three candidate conditions.

Run: python src/decision_engine/task05_study_a_discovery.py
"""
import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

from pitch_direction import PITCH_X, PITCH_Y, team_period_directions
from task04_situation_context import CLUB_COMPETITIONS, DATA_DIR, EVENTS_DIR, INTL_COMPETITIONS

warnings.filterwarnings("ignore")

TYPED_PATH = DATA_DIR / "processed" / "options_typed.parquet"
EV_PATH = DATA_DIR / "processed" / "options_ev.parquet"
PASSES_PATH = DATA_DIR / "processed" / "passes_situation.parquet"
SPLIT_PATH = DATA_DIR / "splits" / "match_split.csv"
OUT_TABLE_PATH = DATA_DIR / "processed" / "study_a_discovery.parquet"
CANDIDATES_CSV = Path(__file__).parent.parent.parent / "docs" / "results" / "05-study-a-candidates.csv"
SUMMARY_PATH = DATA_DIR / "task05_study_a_discovery.json"

MIN_CHOSEN_FOR_ANALYZABLE = 100
BOOTSTRAP_SEED = 20260920
N_BOOTSTRAP = 1000
STANDARD_SEASON_MATCHES = 38


def discovery_match_ids() -> list:
    split = pd.read_csv(SPLIT_PATH)
    return sorted(split.loc[split["half"] == "discovery", "match_id"].tolist())


def load_discovery_data(discovery_ids: list):
    filt = [("match_id", "in", discovery_ids)]
    typed = pd.read_parquet(TYPED_PATH, filters=filt)
    passes = pd.read_parquet(PASSES_PATH, filters=filt)
    ev = pd.read_parquet(EV_PATH, columns=["match_id", "event_id", "team", "period",
                                            "candidate_x", "candidate_y", "chosen", "ev"],
                          filters=filt)
    return typed, passes, ev


def recover_raw_positions(typed: pd.DataFrame) -> pd.DataFrame:
    """options_typed.parquet only kept normalized coordinates (Task 04).
    normalize_xy is self-inverse, so re-applying it with the same
    per-(team,period) direction recovers the original raw candidate
    position, needed to join options_ev.parquet on 'candidate position'
    as the brief specifies."""
    parts = []
    for mid, sub in typed.groupby("match_id", sort=False):
        events = pd.read_parquet(EVENTS_DIR / f"{mid}.parquet")
        directions, _, _ = team_period_directions(events)
        key = pd.MultiIndex.from_arrays([sub["team"], sub["period"]])
        direction = key.map(directions).fillna(1).astype(int).values
        sub = sub.copy()
        sub["candidate_x_raw"] = np.where(direction == 1, sub["candidate_x_norm"],
                                           PITCH_X - sub["candidate_x_norm"])
        sub["candidate_y_raw"] = np.where(direction == 1, sub["candidate_y_norm"],
                                           PITCH_Y - sub["candidate_y_norm"])
        parts.append(sub)
    return pd.concat(parts, ignore_index=True)


def join_ev(typed: pd.DataFrame, ev: pd.DataFrame):
    """Join on (match_id, event_id, candidate position), rounded to 6dp to
    absorb floating-point round-trip noise from recover_raw_positions.

    A handful of freeze frames carry two teammates at the exact same
    recorded location (confirmed: 2 of 616,038 discovery option rows,
    2026-09-20 run). Since every geometric feature -- and therefore
    p_success/ev -- is a function of position alone, verified byte-
    identical between such duplicates, a plain key merge would cross-join
    them (2x2 rows instead of 2) without changing any value. A per-key
    occurrence rank on both sides pairs same-key duplicates positionally
    instead, giving an exact 1:1 join."""
    typed = typed.copy()
    typed["cx_r"] = typed["candidate_x_raw"].round(6)
    typed["cy_r"] = typed["candidate_y_raw"].round(6)
    ev = ev.copy()
    ev["cx_r"] = ev["candidate_x"].round(6)
    ev["cy_r"] = ev["candidate_y"].round(6)

    key_cols = ["match_id", "event_id", "cx_r", "cy_r"]
    typed_group_sizes = typed.groupby(key_cols).size()
    ev_group_sizes = ev.groupby(key_cols).size()
    n_typed_collisions = int((typed_group_sizes > 1).sum())
    n_ev_collisions = int((ev_group_sizes > 1).sum())
    max_group_size_mismatch = int((typed_group_sizes.reindex(ev_group_sizes.index, fill_value=0)
                                    != ev_group_sizes.reindex(typed_group_sizes.index, fill_value=0)).sum())

    typed["_rank"] = typed.groupby(key_cols).cumcount()
    ev["_rank"] = ev.groupby(key_cols).cumcount()

    merged = typed.merge(ev[key_cols + ["_rank", "ev"]], on=key_cols + ["_rank"], how="left", indicator=True)
    n_total = len(typed)
    n_matched = int((merged["_merge"] == "both").sum())
    match_rate = n_matched / n_total if n_total else None

    report = {
        "n_typed_rows": n_total, "n_matched": n_matched, "match_rate": match_rate,
        "n_typed_key_collisions": n_typed_collisions, "n_ev_key_collisions": n_ev_collisions,
        "n_group_size_mismatches": max_group_size_mismatch,
    }
    return merged, report


def build_available_types_table(opt: pd.DataFrame, cell_info: pd.DataFrame) -> pd.DataFrame:
    """One row per (pass, option_type present in that pass), with EV*_type,
    the number of that type's candidates, and the pass's own chosen type j."""
    chosen_rows = opt[opt["chosen"]]
    dupe_chosen = chosen_rows.groupby(["match_id", "event_id"]).size()
    assert (dupe_chosen == 1).all(), "found a pass without exactly one chosen row"
    j_df = chosen_rows[["match_id", "event_id", "option_type"]].rename(columns={"option_type": "j"})

    avail = opt.groupby(["match_id", "event_id", "option_type"]).agg(
        n_options=("ev", "size"), ev_star=("ev", "max"),
    ).reset_index()
    avail = avail.merge(j_df, on=["match_id", "event_id"])
    avail = avail.merge(cell_info, on=["match_id", "event_id"])

    self_type = avail[avail["option_type"] == avail["j"]][
        ["match_id", "event_id", "ev_star", "n_options"]
    ].rename(columns={"ev_star": "ev_star_j", "n_options": "n_options_j"})
    avail = avail.merge(self_type, on=["match_id", "event_id"], how="left")
    assert avail["ev_star_j"].notna().all(), "a pass's chosen type is missing from its own available-types set"
    return avail


def analyzable_pairs(avail: pd.DataFrame) -> pd.DataFrame:
    avail = avail.copy()
    avail["k_chosen"] = avail["option_type"] == avail["j"]
    s_table = avail.groupby(["zone", "under_pressure", "game_state", "option_type"]).agg(
        n_available=("k_chosen", "size"), n_chosen=("k_chosen", "sum"),
    ).reset_index()
    s_table["s"] = s_table["n_chosen"] / s_table["n_available"]
    s_table["analyzable"] = s_table["n_chosen"] >= MIN_CHOSEN_FOR_ANALYZABLE
    return s_table


def compute_pair_stats(g_table: pd.DataFrame, pairs: pd.DataFrame, all_match_ids: list) -> pd.DataFrame:
    n_matches_total = len(all_match_ids)
    match_pos = {m: i for i, m in enumerate(all_match_ids)}
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    idx_matrix = rng.integers(0, n_matches_total, size=(N_BOOTSTRAP, n_matches_total))

    rows = []
    for _, pair in pairs.iterrows():
        z, p, gs, k = pair["zone"], pair["under_pressure"], pair["game_state"], pair["option_type"]
        sub = g_table[(g_table["zone"] == z) & (g_table["under_pressure"] == p)
                      & (g_table["game_state"] == gs) & (g_table["option_type"] == k)]

        n_passes = len(sub)
        G = float(sub["g"].mean())
        P = float((sub["g"] > 0).mean())
        n_team_matches = sub[["team", "match_id"]].drop_duplicates().shape[0]
        n_matches_contrib = sub["match_id"].nunique()
        L = G * (n_passes / n_team_matches) * STANDARD_SEASON_MATCHES

        per_match = sub.groupby("match_id")["g"].agg(["sum", "count"])
        sums = np.zeros(n_matches_total)
        counts = np.zeros(n_matches_total)
        for mid, r in per_match.iterrows():
            sums[match_pos[mid]] = r["sum"]
            counts[match_pos[mid]] = r["count"]
        boot_sums = sums[idx_matrix].sum(axis=1)
        boot_counts = counts[idx_matrix].sum(axis=1)
        with np.errstate(invalid="ignore", divide="ignore"):
            boot_G = np.where(boot_counts > 0, boot_sums / boot_counts, np.nan)
        n_nan_draws = int(np.isnan(boot_G).sum())
        ci_low, ci_high = np.nanpercentile(boot_G, [2.5, 97.5])

        rows.append({
            "zone": z, "under_pressure": bool(p), "game_state": gs, "option_type": k,
            "G": G, "ci_low": float(ci_low), "ci_high": float(ci_high),
            "P": P, "s": float(pair["s"]), "L": L,
            "n_passes": n_passes, "n_matches": int(n_matches_contrib),
            "n_bootstrap_nan_draws": n_nan_draws,
        })
    return pd.DataFrame(rows)


def descriptive_context(g_table: pd.DataFrame, candidates: pd.DataFrame) -> list:
    out = []
    for _, cand in candidates.iterrows():
        z, p, gs, k = cand["zone"], cand["under_pressure"], cand["game_state"], cand["option_type"]
        sub = g_table[(g_table["zone"] == z) & (g_table["under_pressure"] == p)
                      & (g_table["game_state"] == gs) & (g_table["option_type"] == k)]
        is_club = list(zip(sub["competition_id"], sub["season_id"]))
        n_club = sum(1 for c in is_club if c in CLUB_COMPETITIONS)
        n_intl = sum(1 for c in is_club if c in INTL_COMPETITIONS)
        out.append({
            "zone": z, "under_pressure": bool(p), "game_state": gs, "option_type": k,
            "mean_n_options_k": float(sub["n_options"].mean()),
            "mean_n_options_j": float(sub["n_options_j"].mean()),
            "n_passes": len(sub),
            "share_club_focal_team": n_club / len(sub) if len(sub) else None,
            "share_tournament": n_intl / len(sub) if len(sub) else None,
        })
    return out


def main():
    discovery_ids = discovery_match_ids()
    print(f"Discovery matches: {len(discovery_ids)}")

    print("Loading discovery-only data (confirmation never read) ...")
    typed, passes, ev = load_discovery_data(discovery_ids)
    print(f"  options_typed rows (discovery): {len(typed)}")
    print(f"  passes_situation rows (discovery): {len(passes)}")
    print(f"  options_ev rows (discovery): {len(ev)}")

    print("Recovering raw candidate positions and joining to options_ev.parquet ...")
    typed = recover_raw_positions(typed)
    opt, join_report = join_ev(typed, ev)
    print(json.dumps(join_report, indent=2))
    if join_report["n_typed_key_collisions"] or join_report["n_ev_key_collisions"]:
        print(f"  NOTE: {join_report['n_typed_key_collisions']} duplicate-position key group(s) found "
              "(two candidates in the same freeze frame at the exact same location) -- paired "
              "positionally within each group rather than cross-joined; see Section 5 of the results page.")
    if join_report["match_rate"] != 1.0 or join_report["n_group_size_mismatches"]:
        summary = {"status": "BLOCKED", "reason": "options_ev join did not reach 100% match rate",
                   "join_report": join_report}
        SUMMARY_PATH.write_text(json.dumps(summary, indent=2, default=str))
        print("STOPPING: join match rate is not 100%, or a duplicate-key group's size did not "
              "match between options_typed and options_ev. See", SUMMARY_PATH)
        return

    cell_info = passes[["match_id", "event_id", "zone", "under_pressure", "game_state",
                         "team", "competition_id", "season_id"]]
    opt = opt.drop(columns=["team"]).merge(cell_info[["match_id", "event_id", "team"]],
                                            on=["match_id", "event_id"])

    print("Building per-pass available-types table ...")
    avail = build_available_types_table(opt, cell_info)

    print("Identifying analyzable pairs (>=100 chosen in discovery) ...")
    pairs_table = analyzable_pairs(avail)
    analyzable = pairs_table[pairs_table["analyzable"]].copy()
    n_analyzable = len(analyzable)
    print(f"Analyzable pairs: {n_analyzable} (expected 107)")

    g_table = avail[avail["option_type"] != avail["j"]].copy()
    g_table["g"] = g_table["ev_star"] - g_table["ev_star_j"]

    print("Computing G/P/s/L and bootstrapping G's 95% CI (1,000 draws, seed 20260920) ...")
    stats = compute_pair_stats(g_table, analyzable, discovery_ids)
    stats = stats.sort_values(["zone", "under_pressure", "game_state", "option_type"]).reset_index(drop=True)

    OUT_TABLE_PATH.parent.mkdir(parents=True, exist_ok=True)
    stats.to_parquet(OUT_TABLE_PATH)
    print(f"Wrote {len(stats)} rows to {OUT_TABLE_PATH}")

    cond1 = (stats["G"] > 0) & (stats["ci_low"] > 0)
    cond2 = stats["P"] > 0.5
    cond3 = stats["L"] >= 0.5
    stats["is_candidate"] = cond1 & cond2 & cond3
    candidates = stats[stats["is_candidate"]].copy()
    print(f"Candidates (all 3 conditions met): {len(candidates)}")

    csv_out = candidates.copy()
    csv_out["cell"] = ("zone=" + csv_out["zone"] + "|pressure=" +
                        csv_out["under_pressure"].map({True: "yes", False: "no"}) +
                        "|state=" + csv_out["game_state"])
    csv_out["CI"] = csv_out.apply(lambda r: f"[{r['ci_low']:.5f}, {r['ci_high']:.5f}]", axis=1)
    csv_out = csv_out.rename(columns={"option_type": "type"})[
        ["cell", "type", "G", "CI", "P", "s", "L"]
    ]
    CANDIDATES_CSV.parent.mkdir(parents=True, exist_ok=True)
    csv_out.to_csv(CANDIDATES_CSV, index=False)
    print(f"Wrote {len(csv_out)} candidate rows to {CANDIDATES_CSV}")

    desc_context = descriptive_context(g_table, candidates)

    summary = {
        "status": "COMPLETE",
        "n_discovery_matches": len(discovery_ids),
        "join_report": join_report,
        "n_analyzable_pairs": n_analyzable,
        "n_candidates": len(candidates),
        "descriptive_context_for_candidates": desc_context,
    }
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2, default=str))
    print(f"Wrote summary to {SUMMARY_PATH}")


if __name__ == "__main__":
    main()
