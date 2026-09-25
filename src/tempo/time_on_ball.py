"""
Task 16 -- Tempo module, Step 1: time on ball.

Governing document: docs/specs/analysis-plan-tempo.md (plan section 2),
executed via docs/specs/task-16-tempo.md Step 1. Deliberately
independent of src/decision_engine/: reads only raw StatsBomb events
(data/raw/events/*.parquet). No option set, pass-success model, or
value model anywhere in this module (see plan section 0).

Run: python src/tempo/time_on_ball.py
"""
import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

DATA_DIR = Path(__file__).parent.parent.parent / "data"
EVENTS_DIR = DATA_DIR / "raw" / "events"
OUT_PATH = DATA_DIR / "processed" / "tempo_time_on_ball.parquet"
SUMMARY_PATH = DATA_DIR / "tempo_step1_time_on_ball.json"

# Mirrors src/decision_engine/options.py's own EXCLUDED_PASS_TYPES
# constant, redefined here (not imported) so this module has zero
# import-time dependency on src/decision_engine/, per plan section 0.
EXCLUDED_PASS_TYPES = {"Corner", "Free Kick", "Throw-in", "Kick Off", "Goal Kick"}

BASE_INTERVENING_TYPES = {"Carry"}                 # task-16 Step 1's own base wording
WIDENED_INTERVENING_TYPES = {"Carry", "Dribble"}   # T-1.2(b) remedy
STOPPING_EVENT_TYPES = {"Interception", "Ball Recovery", "Duel", "Block", "Clearance"}
LOW_BOUND_S, HIGH_BOUND_S = 0.0, 15.0
COVERAGE_FAIL_THRESHOLD = 0.40
COVERAGE_REMEDY_TARGET = 0.60


def parse_timestamp(ts: str) -> float:
    h, m, s = ts.split(":")
    return int(h) * 3600 + int(m) * 60 + float(s)


def is_open_play_pass(ev: pd.DataFrame) -> pd.Series:
    return ((ev["type"] == "Pass")
            & (~ev["pass_type"].isin(EXCLUDED_PASS_TYPES))
            & (ev["position"] != "Goalkeeper"))


def find_chain(ev: pd.DataFrame, i: int, intervening_types: set) -> dict:
    """ev sorted by index, reset_index(drop=True). Walks backward from
    pass row i looking for the same player's immediately preceding
    Ball Receipt* in the same possession, allowing any number of
    consecutive same-player events whose type is in `intervening_types`
    to bridge the chain (contiguous by construction: one event at a
    time, nothing skipped)."""
    row = ev.iloc[i]
    player, possession, period = row["player_id"], row["possession"], row["period"]
    j = i - 1
    had_intervening = False
    while j >= 0:
        r = ev.iloc[j]
        if r["possession"] != possession:
            break
        if r["player_id"] == player and r["type"] == "Ball Receipt*":
            if r["period"] != period:
                break
            return {"resolved": True, "receipt_idx": j, "had_intervening": had_intervening}
        if r["player_id"] == player and r["type"] in intervening_types:
            had_intervening = True
            j -= 1
            continue
        break
    if j < 0 or ev.iloc[j]["possession"] != possession:
        reason = "first event of possession"
    elif row.get("pass_body_part") == "Head":
        reason = "header"
    elif ev.iloc[j]["type"] in STOPPING_EVENT_TYPES:
        reason = "won by tackle/interception"
    else:
        reason = "other/undetermined"
    return {"resolved": False, "reason": reason}


def build_match_rows(match_id: int, intervening_types: set) -> list:
    ev = pd.read_parquet(EVENTS_DIR / f"{match_id}.parquet")
    ev = ev.sort_values("index").reset_index(drop=True)
    ev["t"] = ev["timestamp"].apply(parse_timestamp)
    open_play = is_open_play_pass(ev)

    rows = []
    for i in np.where(open_play.values)[0]:
        row = ev.iloc[i]
        chain = find_chain(ev, i, intervening_types)
        rec = {
            "match_id": match_id, "event_id": row["id"], "player_id": row["player_id"],
            "team": row["team"], "period": int(row["period"]),
            "pass_complete": bool(pd.isna(row.get("pass_outcome"))),
            "under_pressure": bool(row["under_pressure"]) if pd.notna(row["under_pressure"]) else False,
        }
        if chain["resolved"]:
            receipt_row = ev.iloc[chain["receipt_idx"]]
            rec["resolved"] = True
            rec["time_on_ball"] = float(row["t"] - receipt_row["t"])
            rec["had_intervening"] = chain["had_intervening"]
        else:
            rec["resolved"] = False
            rec["reason"] = chain["reason"]
        rows.append(rec)
    return rows


def compute_all(intervening_types: set, verbose: bool = True) -> pd.DataFrame:
    match_ids = sorted(int(p.stem) for p in EVENTS_DIR.glob("*.parquet"))
    all_rows = []
    for i, mid in enumerate(match_ids):
        all_rows.extend(build_match_rows(mid, intervening_types))
        if verbose and (i + 1) % 50 == 0:
            print(f"  {i + 1}/{len(match_ids)} matches")
    return pd.DataFrame(all_rows)


def apply_bounds(df: pd.DataFrame) -> tuple:
    resolved = df[df["resolved"]].copy()
    n_resolved = len(resolved)
    within = resolved[(resolved["time_on_ball"] >= LOW_BOUND_S) & (resolved["time_on_ball"] <= HIGH_BOUND_S)]
    return within, n_resolved - len(within), n_resolved


def sanity_check(df_bounded: pd.DataFrame) -> dict:
    # had_intervening is only set (True/False) on resolved rows in the raw
    # per-match dicts, so the assembled column can carry object dtype with
    # NaN for the rest of a full (unfiltered) frame -- `~` on an object
    # dtype does Python bitwise NOT (True->-2), not logical negation.
    # df_bounded is already resolved-only by construction, so this is a
    # defensive cast, not a behavior change.
    had_intervening = df_bounded["had_intervening"].astype(bool)
    carry = df_bounded.loc[had_intervening, "time_on_ball"]
    no_carry = df_bounded.loc[~had_intervening, "time_on_ball"]
    med_carry = float(carry.median()) if len(carry) else None
    med_no_carry = float(no_carry.median()) if len(no_carry) else None
    passed = med_carry is not None and med_no_carry is not None and med_carry > med_no_carry
    return {"median_carry_preceded": med_carry, "n_carry_preceded": int(len(carry)),
            "median_no_carry": med_no_carry, "n_no_carry": int(len(no_carry)), "passed": bool(passed)}


def coverage_report(df: pd.DataFrame) -> dict:
    n_total = len(df)
    n_resolved = int(df["resolved"].sum())
    reasons = df.loc[~df["resolved"], "reason"].value_counts().to_dict()
    return {"n_open_play_passes": n_total, "n_resolved": n_resolved,
            "share_resolved": n_resolved / n_total if n_total else None,
            "share_unresolved": 1 - n_resolved / n_total if n_total else None,
            "unresolved_reasons": reasons}


def distribution_report(df_bounded: pd.DataFrame) -> dict:
    def pct(s):
        return {str(p): float(np.percentile(s, p)) for p in (5, 25, 50, 75, 95)}
    out = {"overall": pct(df_bounded["time_on_ball"]), "n_overall": len(df_bounded)}
    comp = df_bounded.loc[df_bounded["pass_complete"], "time_on_ball"]
    incomp = df_bounded.loc[~df_bounded["pass_complete"], "time_on_ball"]
    out["complete"] = {"n": int(len(comp)), **pct(comp)} if len(comp) else None
    out["incomplete"] = {"n": int(len(incomp)), **pct(incomp)} if len(incomp) else None
    return out


def main():
    print("Step 1: building time_on_ball (base construction: same-player Carry bridges) ...")
    df = compute_all(BASE_INTERVENING_TYPES)
    cov = coverage_report(df)
    print(f"  open-play passes: {cov['n_open_play_passes']}, resolved: {cov['n_resolved']} "
          f"({cov['share_resolved']:.4f})")
    print(f"  unresolved reasons: {cov['unresolved_reasons']}")

    df_bounded, n_excl_bounds, n_resolved = apply_bounds(df)
    print(f"  excluded by 0-15s bound: {n_excl_bounds}/{n_resolved} ({n_excl_bounds / n_resolved:.4f})")

    sanity = sanity_check(df_bounded)
    print(f"  Carry sanity check: {sanity}")

    remedy_a_applied, remedy_a_note = False, None
    if not sanity["passed"]:
        remedy_a_applied = True
        print("  Sanity check FAILED -- T-1.2(a) remedy is same-player + contiguous, which the base "
              "construction already is; re-verifying (no code change possible) ...")
        sanity2 = sanity_check(df_bounded)
        if not sanity2["passed"]:
            print("  Still fails. time_on_ball is unreliable at source -- DROPPING THE WHOLE MODULE.")
            summary = {"status": "DROPPED", "reason": "Carry sanity check failed; T-1.2(a) is already "
                                                        "the base construction, so no further remedy exists",
                       "coverage": cov, "sanity_check": sanity}
            SUMMARY_PATH.write_text(json.dumps(summary, indent=2, default=str))
            return None, summary
        sanity = sanity2
        remedy_a_note = "re-verified; already same-player/contiguous by construction"

    remedy_b_applied = False
    if cov["share_unresolved"] is not None and cov["share_unresolved"] > COVERAGE_FAIL_THRESHOLD:
        remedy_b_applied = True
        print(f"  Unresolved share {cov['share_unresolved']:.4f} > 40% -- applying T-1.2(b) remedy once "
              f"(widen intervening types to Carry+Dribble) ...")
        df = compute_all(WIDENED_INTERVENING_TYPES)
        cov = coverage_report(df)
        print(f"  after remedy: resolved {cov['share_resolved']:.4f}")
        df_bounded, n_excl_bounds, n_resolved = apply_bounds(df)
        sanity = sanity_check(df_bounded)
        print(f"  Carry sanity check after remedy: {sanity}")
        if cov["share_resolved"] < COVERAGE_REMEDY_TARGET:
            print("  Coverage still below 60% after remedy -- shipping anyway; coverage is a stated bound, not a drop reason.")

    dist = distribution_report(df_bounded)
    df_bounded.to_parquet(OUT_PATH)

    summary = {
        "status": "COMPLETE", "remedy_a_applied": remedy_a_applied, "remedy_a_note": remedy_a_note,
        "remedy_b_applied": remedy_b_applied, "coverage": cov,
        "n_excluded_by_bounds": n_excl_bounds, "n_resolved_before_bounds": n_resolved,
        "sanity_check": sanity, "distribution": dist,
    }
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2, default=str))
    print(f"\nWrote {OUT_PATH} and {SUMMARY_PATH}")
    return df_bounded, summary


if __name__ == "__main__":
    main()
