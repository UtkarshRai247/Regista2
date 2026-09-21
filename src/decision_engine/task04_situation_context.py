"""
Task 04 — Steps 1-4: situation context join, option typing, discovery/
confirmation split, feasibility counts. Governed by
docs/specs/analysis-plan-v2.md and docs/specs/task-04-situation-context.md
(frozen at commit e1ee6aca24ea8cbc3d8e875d6887388ce34eee46, D-012/013/014).

HARD RULE: this script never loads options_ev.parquet / options_policy.parquet
and never reads p_success/ev/policy_probability from anywhere. Only
options_scored.parquet (distance, chosen, pass_complete, geometry) is
read. Counts only downstream — no value quantity by cell/type/team/player.

Coordinates: passer/candidate locations are re-normalized here to the
attacking direction via pitch_direction.normalize_xy, since
options_scored.parquet stores them RAW (options.py never normalizes).

Own-goal / score-reconstruction logic mirrors decompose.py's
compute_realized_values exactly (Shot+Goal, or "Own Goal Against" credited
to the opponent), for consistency with the one other place in this
codebase that already reconstructs match score state.

Run: python src/decision_engine/task04_situation_context.py
"""
import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

from options import bearing, circular_diff
from pitch_direction import PITCH_X, PITCH_Y, normalize_xy, team_period_directions

warnings.filterwarnings("ignore")

DATA_DIR = Path(__file__).parent.parent.parent / "data"
EVENTS_DIR = DATA_DIR / "raw" / "events"
FRAMES_DIR = DATA_DIR / "raw" / "frames"
MATCHES_DIR = DATA_DIR / "raw" / "matches"
SCORED_PATH = DATA_DIR / "processed" / "options_scored.parquet"
OUT_PASSES = DATA_DIR / "processed" / "passes_situation.parquet"
OUT_OPTIONS = DATA_DIR / "processed" / "options_typed.parquet"
SPLIT_PATH = DATA_DIR / "splits" / "match_split.csv"
SUMMARY_PATH = DATA_DIR / "task04_situation_context.json"
MISMATCH_PATH = DATA_DIR / "task04_score_mismatches.json"

SPLIT_SEED = 20260920
MIN_CHOSEN_FOR_ANALYZABLE = 100
CONTEXT_MIN_PASSES = 20
YARD_IN_METERS = 0.9144

# The 8-competition-season sample (data/sample_competitions.json), split
# club vs international for the Study B mover count.
CLUB_COMPETITIONS = {(9, 281), (11, 90), (7, 235), (7, 108), (44, 107)}
INTL_COMPETITIONS = {(43, 106), (55, 282), (55, 43)}


# ---------- shared loaders ----------
def load_matches_meta() -> dict:
    meta = {}
    for f in sorted(MATCHES_DIR.glob("*.parquet")):
        comp_id, season_id = (int(x) for x in f.stem.split("_"))
        df = pd.read_parquet(f, columns=["match_id", "home_team", "away_team",
                                          "home_score", "away_score"])
        for _, r in df.iterrows():
            meta[int(r["match_id"])] = {
                "competition_id": comp_id, "season_id": season_id,
                "home_team": r["home_team"], "away_team": r["away_team"],
                "home_score": int(r["home_score"]), "away_score": int(r["away_score"]),
            }
    return meta


def position_group(pos) -> str:
    """Not specified anywhere in the plan/codebase - flagged as an
    assumption in the results page (Section 6). Used only for the
    Study B 'same position group' descriptive count in Step 4."""
    if pos is None or (isinstance(pos, float) and pd.isna(pos)):
        return None
    if pos == "Goalkeeper":
        return "GK"
    if "Back" in pos:
        return "Defender"
    if "Midfield" in pos:
        return "Midfielder"
    return "Forward"  # Wing, Forward, Striker


# ---------- unit determination (Step 2) ----------
def determine_distance_unit() -> dict:
    """Penalty-spot check: Law 1 fixes the penalty mark at 12 yards from
    the goal line. If StatsBomb units are yards, every penalty's distance
    to the nearer goal line (min(x, 120-x)) should cluster around 12."""
    dists = []
    for f in sorted(EVENTS_DIR.glob("*.parquet")):
        ev = pd.read_parquet(f, columns=["type", "shot_type", "location"])
        pens = ev[(ev["type"] == "Shot") & (ev["shot_type"] == "Penalty")]
        for loc in pens["location"]:
            if loc is None or (isinstance(loc, float) and pd.isna(loc)):
                continue
            x = loc[0]
            dists.append(min(x, PITCH_X - x))
    arr = np.array(dists, dtype=float)
    evidence = {
        "n_penalties": int(len(arr)),
        "mean_dist_to_goal_line": float(arr.mean()) if len(arr) else None,
        "median_dist_to_goal_line": float(np.median(arr)) if len(arr) else None,
        "std_dist_to_goal_line": float(arr.std()) if len(arr) else None,
    }
    median = evidence["median_dist_to_goal_line"]
    if median is not None and 11.0 <= median <= 13.0:
        evidence["unit"] = "yards"
        evidence["meters_per_unit"] = YARD_IN_METERS
        evidence["basis"] = ("Median penalty-spot distance to goal line "
                              f"({median:.2f} units) matches Law 1's 12-yard "
                              "penalty mark, so 1 StatsBomb unit = 1 yard.")
    else:
        evidence["unit"] = "inconclusive"
        evidence["meters_per_unit"] = 1.0
        evidence["basis"] = ("Median penalty-spot distance to goal line "
                              f"({median} units) does not match the expected "
                              "12-yard mark; falling back to treating units "
                              "as meters (matches this codebase's existing "
                              "undocumented _M-suffixed constants).")
    evidence["short_max_units"] = 15.0 / evidence["meters_per_unit"]
    evidence["long_min_units"] = 30.0 / evidence["meters_per_unit"]
    return evidence


# ---------- per-match processing (Steps 1 + 2 combined, one pass over files) ----------
def process_match(mid, meta, options_match, passes_match):
    ev = pd.read_parquet(EVENTS_DIR / f"{mid}.parquet")
    ev = ev.sort_values("index").reset_index(drop=True)
    ev["under_pressure"] = ev["under_pressure"].fillna(False).astype(bool)
    directions, _, _ = team_period_directions(ev)

    teams = ev["team"].dropna().unique().tolist()
    score = {t: 0 for t in teams}
    is_goal = (((ev["type"] == "Shot") & (ev["shot_outcome"] == "Goal"))
               | (ev["type"] == "Own Goal Against")) & (ev["period"] != 5)

    score_diff_before = {}
    for i in range(len(ev)):
        row = ev.iloc[i]
        opp = [t for t in teams if t != row["team"]]
        opp = opp[0] if opp else None
        score_diff_before[row["id"]] = (
            (score.get(row["team"], 0) - score.get(opp, 0)) if opp else 0
        )
        if is_goal.iloc[i]:
            scorer = row["team"]
            if row["type"] == "Own Goal Against":
                scorer = opp
            if scorer in score:
                score[scorer] += 1

    mismatch = None
    if score.get(meta["home_team"], 0) != meta["home_score"] or \
       score.get(meta["away_team"], 0) != meta["away_score"]:
        mismatch = {
            "match_id": int(mid), "reconstructed": {k: int(v) for k, v in score.items()},
            "recorded_home_team": meta["home_team"], "recorded_home_score": meta["home_score"],
            "recorded_away_team": meta["away_team"], "recorded_away_score": meta["away_score"],
        }

    ev_idx = ev.set_index("id")
    frames = pd.read_parquet(FRAMES_DIR / f"{mid}.parquet")
    frame_sizes = frames.groupby("id").size()

    third_y = PITCH_Y / 3
    pass_rows = []
    for _, p in passes_match.iterrows():
        eid = p["event_id"]
        erow = ev_idx.loc[eid]
        direction = directions.get((p["team"], p["period"]), 1)
        nx, ny = normalize_xy(p["passer_x"], p["passer_y"], direction)
        zone = "defensive" if nx < 40 else ("middle" if nx < 80 else "final")
        channel = "left" if ny < third_y else ("centre" if ny < 2 * third_y else "right")
        score_diff = score_diff_before.get(eid, 0)
        game_state = "leading" if score_diff > 0 else ("trailing" if score_diff < 0 else "level")
        n_visible = int(frame_sizes.get(eid, 0))
        pass_rows.append({
            "match_id": int(mid), "event_id": eid, "team": p["team"], "period": int(p["period"]),
            "player_id": p["player_id"],
            "competition_id": meta["competition_id"], "season_id": meta["season_id"],
            "under_pressure": bool(erow["under_pressure"]),
            "minute": int(erow["minute"]), "second": int(erow["second"]),
            "play_pattern": erow["play_pattern"],
            "passer_x_norm": nx, "passer_y_norm": ny,
            "zone": zone, "channel": channel,
            "n_visible_players": n_visible,
            "score_diff": int(score_diff), "game_state": game_state,
            "position": erow["position"],  # transient: used only for Step 4, dropped before write
        })

    option_rows = []
    for _, o in options_match.iterrows():
        direction = directions.get((o["team"], o["period"]), 1)
        px, py = normalize_xy(o["passer_x"], o["passer_y"], direction)
        cx, cy = normalize_xy(o["candidate_x"], o["candidate_y"], direction)
        diff = circular_diff(bearing((px, py), (cx, cy)), 0.0)
        direc = "forward" if diff <= 45 else ("backward" if diff > 135 else "lateral")
        option_rows.append({
            "match_id": int(mid), "event_id": o["event_id"], "team": o["team"],
            "period": int(o["period"]), "player_id": o["player_id"],
            "passer_x_norm": px, "passer_y_norm": py,
            "candidate_x_norm": cx, "candidate_y_norm": cy,
            "distance": o["distance"], "direction_type": direc,
            "chosen": bool(o["chosen"]), "pass_complete": bool(o["pass_complete"]),
            "lane_crosses_opponent": o["lane_crosses_opponent"],
            "opponents_within_5m": o["opponents_within_5m"],
            "distance_to_nearest_opponent": o["distance_to_nearest_opponent"],
            "n_opponents_visible": o["n_opponents_visible"],
        })

    return pass_rows, option_rows, mismatch


# ---------- Step 3: discovery/confirmation split ----------
def build_split(matches_meta: dict) -> pd.DataFrame:
    rng = np.random.default_rng(SPLIT_SEED)
    by_comp = {}
    for mid, m in matches_meta.items():
        by_comp.setdefault((m["competition_id"], m["season_id"]), []).append(mid)

    rows = []
    for (comp_id, season_id), mids in sorted(by_comp.items()):
        mids = sorted(mids)
        n = len(mids)
        perm = rng.permutation(n)
        half = n // 2
        discovery = {mids[j] for j in perm[:half]}
        for mid in mids:
            rows.append({"match_id": mid, "competition_id": comp_id, "season_id": season_id,
                         "half": "discovery" if mid in discovery else "confirmation"})
    return pd.DataFrame(rows)


# ---------- Step 4: feasibility counts ----------
def feasibility_counts(passes_df: pd.DataFrame, options_df: pd.DataFrame,
                        split_df: pd.DataFrame) -> dict:
    discovery_matches = set(split_df.loc[split_df["half"] == "discovery", "match_id"])
    disc_passes = passes_df[passes_df["match_id"].isin(discovery_matches)]
    disc_options = options_df[options_df["match_id"].isin(discovery_matches)]

    cells = disc_passes.groupby(["zone", "under_pressure", "game_state"]).size()
    passes_per_cell = [
        {"zone": z, "under_pressure": bool(p), "game_state": g, "n_passes": int(n)}
        for (z, p, g), n in cells.items()
    ]

    disc_opt_cell = disc_options.merge(
        disc_passes[["match_id", "event_id", "zone", "under_pressure", "game_state"]],
        on=["match_id", "event_id"], how="inner",
    )
    pair_rows = []
    n_analyzable = 0
    for (z, p, g, otype), g_df in disc_opt_cell.groupby(
            ["zone", "under_pressure", "game_state", "option_type"]):
        available = int(len(g_df))
        chosen = int(g_df["chosen"].sum())
        analyzable = chosen >= MIN_CHOSEN_FOR_ANALYZABLE
        n_analyzable += int(analyzable)
        pair_rows.append({
            "zone": z, "under_pressure": bool(p), "game_state": g, "option_type": otype,
            "available": available, "chosen": chosen, "analyzable": analyzable,
        })
    n_possible_pairs = len(passes_df["zone"].unique()) * 2 * len(passes_df["game_state"].unique()) \
        * len(options_df["option_type"].unique())

    # Study B: team contexts per player, at the 20-pass floor (full sample, eligible passes only)
    ctx_counts = passes_df.groupby(["player_id", "team", "competition_id", "season_id"]).size()
    ctx_counts = ctx_counts[ctx_counts >= CONTEXT_MIN_PASSES]
    contexts_per_player = ctx_counts.groupby(level=0).apply(lambda s: len(s))
    n_players_2plus = int((contexts_per_player >= 2).sum())

    club_intl = {}
    for (pid, team, comp_id, season_id), n in ctx_counts.items():
        is_club = (comp_id, season_id) in CLUB_COMPETITIONS
        is_intl = (comp_id, season_id) in INTL_COMPETITIONS
        club_intl.setdefault(pid, {"club": [], "intl": []})
        if is_club:
            club_intl[pid]["club"].append((team, comp_id, season_id))
        if is_intl:
            club_intl[pid]["intl"].append((team, comp_id, season_id))
    movers = {pid: v for pid, v in club_intl.items() if v["club"] and v["intl"]}
    n_movers = len(movers)

    # position group per (player, team, competition, season) context, for movers only
    pos_lookup = passes_df.groupby(["player_id", "team", "competition_id", "season_id"])["position"] \
        .agg(lambda s: s.mode().iloc[0] if not s.mode().empty else None)
    n_movers_same_group = 0
    for pid, v in movers.items():
        club_groups = {position_group(pos_lookup.get((pid, t, c, s))) for (t, c, s) in v["club"]}
        intl_groups = {position_group(pos_lookup.get((pid, t, c, s))) for (t, c, s) in v["intl"]}
        club_groups.discard(None)
        intl_groups.discard(None)
        if club_groups & intl_groups:
            n_movers_same_group += 1

    # club competition structure
    comp_structure = []
    for (comp_id, season_id), g in passes_df.groupby(["competition_id", "season_id"]):
        team_match_counts = g.groupby("team")["match_id"].nunique()
        total_matches = g["match_id"].nunique()
        top_team = team_match_counts.idxmax()
        top_team_matches = int(team_match_counts.max())
        comp_structure.append({
            "competition_id": int(comp_id), "season_id": int(season_id),
            "n_distinct_teams": int(team_match_counts.shape[0]),
            "n_matches": int(total_matches),
            "matches_per_team": {k: int(v) for k, v in team_match_counts.items()},
            "focal_team": top_team if top_team_matches == total_matches else None,
        })

    visible_dist = passes_df["n_visible_players"].describe().to_dict()
    median_visible = float(passes_df["n_visible_players"].median())

    return {
        "passes_per_cell_discovery": passes_per_cell,
        "n_cells": len(passes_per_cell),
        "pairs": pair_rows,
        "n_possible_pairs": int(n_possible_pairs),
        "n_analyzable_pairs": int(n_analyzable),
        "study_b": {
            "n_players_with_2plus_contexts_20pass_floor": n_players_2plus,
            "n_club_plus_international_movers": n_movers,
            "n_movers_same_position_group_in_both": n_movers_same_group,
        },
        "club_competition_structure": comp_structure,
        "visible_players_per_frame": {k: float(v) for k, v in visible_dist.items()},
        "visible_players_median": median_visible,
    }


def main():
    print("Loading options_scored.parquet, dropping p_success on read "
          "(never options_ev.parquet / options_policy.parquet) ...")
    scored = pd.read_parquet(SCORED_PATH).drop(columns=["p_success"])

    matches_meta = load_matches_meta()

    print("Determining distance unit from penalty-spot locations ...")
    unit_evidence = determine_distance_unit()
    print(json.dumps(unit_evidence, indent=2))

    passes_base = scored.drop_duplicates(subset=["match_id", "event_id"])[
        ["match_id", "event_id", "team", "period", "player_id", "passer_x", "passer_y"]
    ]
    n_expected = len(passes_base)
    print(f"Base matched-pass population: {n_expected} (expected 171,618)")

    scored_by_match = {mid: g for mid, g in scored.groupby("match_id")}
    passes_by_match = {mid: g for mid, g in passes_base.groupby("match_id")}
    empty_options = scored.iloc[0:0]
    empty_passes = passes_base.iloc[0:0]
    # Validate the score reconstruction against ALL 299 matches (the brief's
    # gate), not just the 292 that happen to have an eligible/matched pass in
    # options_scored.parquet (7 matches produced zero rows in Task 01 Step 1).
    match_ids = sorted(matches_meta.keys())
    n_matches_no_passes = len(match_ids) - len(scored_by_match)

    all_pass_rows, all_option_rows, mismatches = [], [], []
    for i, mid in enumerate(match_ids):
        meta = matches_meta.get(mid)
        if meta is None:
            raise RuntimeError(f"match {mid} missing from matches metadata")
        pass_rows, option_rows, mismatch = process_match(
            mid, meta, scored_by_match.get(mid, empty_options), passes_by_match.get(mid, empty_passes))
        all_pass_rows.extend(pass_rows)
        all_option_rows.extend(option_rows)
        if mismatch:
            mismatches.append(mismatch)
        if (i + 1) % 50 == 0:
            print(f"  {i + 1}/{len(match_ids)} matches processed")

    print(f"({n_matches_no_passes} of {len(match_ids)} matches contributed zero eligible/matched "
          "passes to options_scored.parquet in Task 01 -- still validated for score reconstruction here.)")
    print(f"\nScore validation: {len(mismatches)} mismatches out of {len(match_ids)} matches")
    if mismatches:
        print(json.dumps(mismatches, indent=2, default=str))
        MISMATCH_PATH.write_text(json.dumps(mismatches, indent=2, default=str))
        summary = {"status": "BLOCKED", "reason": "score validation mismatches",
                   "n_mismatches": len(mismatches), "unit_evidence": unit_evidence,
                   "n_matched_passes": n_expected}
        SUMMARY_PATH.write_text(json.dumps(summary, indent=2, default=str))
        print("STOPPING before Steps 2-4 per brief: score validation failed. "
              f"See {MISMATCH_PATH}")
        return

    passes_df = pd.DataFrame(all_pass_rows)
    options_df = pd.DataFrame(all_option_rows)

    short_max = unit_evidence["short_max_units"]
    long_min = unit_evidence["long_min_units"]
    options_df["length_type"] = np.select(
        [options_df["distance"] < short_max, options_df["distance"] < long_min],
        ["short", "medium"], default="long",
    )
    options_df["option_type"] = options_df["direction_type"] + "_" + options_df["length_type"]

    type_share = (options_df["option_type"].value_counts(normalize=True) * 100).round(2).to_dict()
    print("\nOption type shares (%):")
    print(json.dumps(type_share, indent=2))

    OUT_PASSES.parent.mkdir(parents=True, exist_ok=True)
    passes_out = passes_df.drop(columns=["position"])
    passes_out.to_parquet(OUT_PASSES)
    options_df.to_parquet(OUT_OPTIONS)
    print(f"\nWrote {len(passes_out)} rows to {OUT_PASSES}")
    print(f"Wrote {len(options_df)} rows to {OUT_OPTIONS}")

    print("\nBuilding discovery/confirmation split ...")
    split_df = build_split(matches_meta)
    SPLIT_PATH.parent.mkdir(parents=True, exist_ok=True)
    split_df.to_csv(SPLIT_PATH, index=False)
    per_comp_split = split_df.groupby(["competition_id", "season_id", "half"]).size().unstack(fill_value=0)
    print(per_comp_split.to_string())

    print("\nComputing Step 4 feasibility counts ...")
    feas = feasibility_counts(passes_df, options_df, split_df)
    print(f"Analyzable pairs: {feas['n_analyzable_pairs']} / {feas['n_possible_pairs']}")
    print(json.dumps(feas["study_b"], indent=2))

    forbidden = {"ev", "p_success", "policy_probability", "v_success",
                 "v_turnover", "policy_raw_score"}
    assert not (forbidden & set(passes_out.columns)), "value column leaked into passes_situation"
    assert not (forbidden & set(options_df.columns)), "value column leaked into options_typed"

    summary = {
        "status": "COMPLETE",
        "n_matched_passes": int(len(passes_out)),
        "n_expected_passes": 171618,
        "n_option_rows": int(len(options_df)),
        "n_matches": len(match_ids),
        "n_matches_with_zero_eligible_passes": n_matches_no_passes,
        "n_score_mismatches": 0,
        "unit_evidence": unit_evidence,
        "option_type_share_pct": type_share,
        "split_per_competition": per_comp_split.reset_index().to_dict("records"),
        "feasibility": feas,
    }
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2, default=str))
    print(f"\nWrote summary to {SUMMARY_PATH}")


if __name__ == "__main__":
    main()
