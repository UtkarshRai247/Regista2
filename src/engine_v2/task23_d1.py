"""
Task 23, Step 1 (D1): take T4's three synthetic scenarios apart. NO
model, feature, or threshold changes -- this only measures, using
`test_t4_synthetic.py`'s own frames, Task 19d's value models
(value_model_for_v2.json / value_model_against_v2.json), and the
current pass-success model (pass_success_v2.py, unchanged since Task
15). Prints p_success, V_net_success, V_net_turnover, EV, and every
STATE_FEATURES value of the success state and the turnover state, for
all three scenarios.

For scenario_c only: where each of p_success/V_net_success/
V_net_turnover/EV falls as a percentile of the same quantity across a
fixed sample of the Task 19d corpus (options_ev_v2) -- 50,000 rows from
EACH of 30 matches chosen with seed 20260927 from ALL 292 match files
(the committed test (`test_t4_synthetic.py`) instead uses the first 30
files alphabetically with its own seed=42 per-file sampling -- both
EV p90 values are reported side by side, since the brief flags this as
a possible sampling artifact worth checking, not assuming away).

Also: the n_visible_players distribution in value_model_rows_v2.parquet
(Task 19d's training rows), the share of rows with <=6 visible players,
and whether scenario_c's synthetic frame (4 opponents at x=70, 1
teammate, no explicit goalkeeper) looks like anything in that
distribution.

Run: python src/engine_v2/task23_d1.py
"""
import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import xgboost as xgb

from features import compute_candidate_features, state_features_batch
from value_models import PATTERN_CODE, STATE_FEATURES
from pass_success_v2 import MODEL_PATH as PASS_SUCCESS_MODEL_PATH
from common import CANDIDATE_FEATURES, prep_X

warnings.filterwarnings("ignore")

DATA_DIR = Path(__file__).parent.parent.parent / "data"
MODEL_FOR_PATH_V2 = DATA_DIR / "processed" / "engine_v2" / "value_model_for_v2.json"
MODEL_AGAINST_PATH_V2 = DATA_DIR / "processed" / "engine_v2" / "value_model_against_v2.json"
STEP4_SUMMARY = DATA_DIR / "engine_v2_step4_pass_success.json"
EV_DIR_V2 = DATA_DIR / "processed" / "engine_v2" / "options_ev_v2"
VALUE_ROWS_V2_PATH = DATA_DIR / "processed" / "engine_v2" / "value_model_rows_v2.parquet"
OUT_PATH = DATA_DIR / "engine_v2_task23_d1.json"
SAMPLE_OUT_PATH = DATA_DIR / "processed" / "engine_v2" / "task23_d1_sample.parquet"  # reused by D3

SEED = 20260927
N_MATCHES = 30
N_PER_MATCH = 50000


def load_models():
    model_for = xgb.XGBClassifier()
    model_for.load_model(str(MODEL_FOR_PATH_V2))
    model_against = xgb.XGBClassifier()
    model_against.load_model(str(MODEL_AGAINST_PATH_V2))
    pass_success = xgb.XGBClassifier()
    pass_success.load_model(str(PASS_SUCCESS_MODEL_PATH))
    fill_values = json.loads(STEP4_SUMMARY.read_text())["fill_values"]
    return model_for, model_against, pass_success, fill_values


def compute_ev_diag(passer_raw, candidates_raw, is_teammate_dest, opponents_raw, teammates_raw,
                     model_for, model_against, p_success_override=None, pass_success_model=None, fill_values=None):
    n_visible = len(opponents_raw) + len(teammates_raw) + 1
    cand_feats = compute_candidate_features(passer_raw, candidates_raw, is_teammate_dest,
                                             direction=1, opponents_raw=opponents_raw,
                                             teammates_raw=teammates_raw, n_visible=n_visible)
    if p_success_override is not None:
        p_success = np.full(len(candidates_raw), p_success_override)
    else:
        X_cand = pd.DataFrame(cand_feats)
        X_cand, _ = prep_X(X_cand, CANDIDATE_FEATURES, fill_values)
        p_success = pass_success_model.predict_proba(X_cand)[:, 1]

    succ = state_features_batch(candidates_raw, passer_raw, 1, teammates_raw, opponents_raw, n_visible)
    succ["time_remaining_period"] = np.full(len(candidates_raw), 1000.0)
    succ["score_diff"] = np.full(len(candidates_raw), 0)
    succ["play_pattern_code"] = np.full(len(candidates_raw), PATTERN_CODE["Regular Play"])
    turn = state_features_batch(candidates_raw, passer_raw, -1, opponents_raw, teammates_raw, n_visible)
    turn["time_remaining_period"] = np.full(len(candidates_raw), 1000.0)
    turn["score_diff"] = np.full(len(candidates_raw), 0)
    turn["play_pattern_code"] = np.full(len(candidates_raw), PATTERN_CODE["From Counter"])

    X_succ = pd.DataFrame(succ)[STATE_FEATURES].astype(float)
    X_turn = pd.DataFrame(turn)[STATE_FEATURES].astype(float)
    v_net_success = model_for.predict_proba(X_succ)[:, 1] - model_against.predict_proba(X_succ)[:, 1]
    v_net_turnover = model_against.predict_proba(X_turn)[:, 1] - model_for.predict_proba(X_turn)[:, 1]
    ev = p_success * v_net_success + (1 - p_success) * v_net_turnover
    return {"ev": ev, "p_success": p_success, "v_net_success": v_net_success, "v_net_turnover": v_net_turnover,
            "succ_features": {k: v[0] for k, v in succ.items() if k in STATE_FEATURES},
            "turn_features": {k: v[0] for k, v in turn.items() if k in STATE_FEATURES}}


def scenario_a(model_for, model_against):
    passer_raw = np.array([60.0, 40.0])
    opponents_raw = np.array([[70.0, 20.0], [70.0, 35.0], [70.0, 50.0], [70.0, 65.0], [61.0, 66.0]])
    teammates_raw = np.array([[55.0, 40.0]])
    candidates_raw = np.array([[100.0, 40.0], [60.0, 65.0]])
    is_teammate_dest = np.array([0, 0])
    labels = ["unmarked_runner", "marked_sideways"]
    results = {}
    for i, label in enumerate(labels):
        r = compute_ev_diag(passer_raw, candidates_raw[i:i + 1], is_teammate_dest[i:i + 1],
                             opponents_raw, teammates_raw, model_for, model_against, p_success_override=0.75)
        results[label] = {"p_success": float(r["p_success"][0]), "V_net_success": float(r["v_net_success"][0]),
                           "V_net_turnover": float(r["v_net_turnover"][0]), "EV": float(r["ev"][0]),
                           "success_state_features": r["succ_features"], "turnover_state_features": r["turn_features"]}
    return results


def scenario_b(model_for, model_against, pass_success_model, fill_values):
    passer_raw = np.array([60.0, 40.0])
    opponents_raw = np.array([[59.0, 64.0], [61.0, 65.0], [60.0, 67.0], [70.0, 20.0]])
    teammates_raw = np.array([[55.0, 40.0]])
    candidates_raw = np.array([[60.0, 65.0], [60.0, 15.0]])
    is_teammate_dest = np.array([0, 0])
    labels = ["into_cluster", "into_open_space"]
    results = {}
    for i, label in enumerate(labels):
        r = compute_ev_diag(passer_raw, candidates_raw[i:i + 1], is_teammate_dest[i:i + 1],
                             opponents_raw, teammates_raw, model_for, model_against,
                             pass_success_model=pass_success_model, fill_values=fill_values)
        results[label] = {"p_success": float(r["p_success"][0]), "V_net_success": float(r["v_net_success"][0]),
                           "V_net_turnover": float(r["v_net_turnover"][0]), "EV": float(r["ev"][0]),
                           "success_state_features": r["succ_features"], "turnover_state_features": r["turn_features"]}
    return results


def scenario_c(model_for, model_against, pass_success_model, fill_values):
    passer_raw = np.array([60.0, 40.0])
    opponents_raw = np.array([[70.0, 20.0], [70.0, 35.0], [70.0, 50.0], [70.0, 65.0]])
    teammate_beyond = np.array([95.0, 40.0])
    teammates_raw = np.array([teammate_beyond])
    candidates_raw = np.array([teammate_beyond])
    is_teammate_dest = np.array([1])
    r = compute_ev_diag(passer_raw, candidates_raw, is_teammate_dest, opponents_raw, teammates_raw,
                         model_for, model_against, pass_success_model=pass_success_model, fill_values=fill_values)
    return {"p_success": float(r["p_success"][0]), "V_net_success": float(r["v_net_success"][0]),
            "V_net_turnover": float(r["v_net_turnover"][0]), "EV": float(r["ev"][0]),
            "success_state_features": r["succ_features"], "turnover_state_features": r["turn_features"]}


def build_seeded_sample() -> pd.DataFrame:
    """50,000 rows from EACH of 30 matches chosen with seed 20260927
    from ALL 292 match files in options_ev_v2 (not the first 30
    alphabetically)."""
    all_match_paths = sorted(EV_DIR_V2.glob("*.parquet"))
    rng = np.random.default_rng(SEED)
    chosen = rng.choice(len(all_match_paths), size=N_MATCHES, replace=False)
    chosen_paths = [all_match_paths[i] for i in sorted(chosen)]
    cols = ["match_id", "event_id", "team", "period", "candidate_x", "candidate_y",
            "distance_u", "p_success", "is_teammate_destination", "V_net_success", "V_net_turnover", "EV"]
    parts = []
    for p in chosen_paths:
        df = pd.read_parquet(p, columns=cols)
        n_take = min(N_PER_MATCH, len(df))
        parts.append(df.sample(n=n_take, random_state=SEED))
    sample = pd.concat(parts, ignore_index=True)
    return sample, [int(p.stem) for p in chosen_paths]


def build_committed_test_sample() -> pd.DataFrame:
    """Reproduces test_t4_synthetic.py's own EV-only sampling exactly
    (first 30 files alphabetically, seed=42 per-file), but pointed at
    options_ev_v2 instead of the committed test's own options_ev, since
    the brief asks for the comparison on the Task 19d corpus."""
    parts = sorted(EV_DIR_V2.glob("*.parquet"))[:30]
    sample = pd.concat([pd.read_parquet(p, columns=["EV"]).sample(
        n=min(50000, len(pd.read_parquet(p, columns=["EV"]))), random_state=42) for p in parts], ignore_index=True)
    return sample


def percentile_of(value: float, series: pd.Series) -> float:
    return float((series < value).mean() * 100)


def main():
    print("Task 23 Step 1 (D1): taking T4's scenarios apart ...")
    model_for, model_against, pass_success_model, fill_values = load_models()

    print("  scenario_a ...")
    res_a = scenario_a(model_for, model_against)
    print("  scenario_b ...")
    res_b = scenario_b(model_for, model_against, pass_success_model, fill_values)
    print("  scenario_c ...")
    res_c = scenario_c(model_for, model_against, pass_success_model, fill_values)
    for label, r in {**{f"a_{k}": v for k, v in res_a.items()}, **{f"b_{k}": v for k, v in res_b.items()}, "c": res_c}.items():
        print(f"    {label}: p_success={r['p_success']:.4f}, V_net_success={r['V_net_success']:.5f}, "
              f"V_net_turnover={r['V_net_turnover']:.5f}, EV={r['EV']:.5f}")

    print("  building seeded corpus sample (seed=20260927, 30 of 292 matches, 50k/match) ...")
    seeded_sample, seeded_match_ids = build_seeded_sample()
    seeded_sample.to_parquet(SAMPLE_OUT_PATH)
    print(f"    seeded sample: {len(seeded_sample)} rows from {len(seeded_match_ids)} matches")

    print("  building the committed test's own sample (first 30 alphabetical, seed=42/file) ...")
    committed_sample = build_committed_test_sample()
    print(f"    committed-test-style sample: {len(committed_sample)} rows")

    percentiles = {
        "p_success": percentile_of(res_c["p_success"], seeded_sample["p_success"]),
        "V_net_success": percentile_of(res_c["V_net_success"], seeded_sample["V_net_success"]),
        "V_net_turnover": percentile_of(res_c["V_net_turnover"], seeded_sample["V_net_turnover"]),
        "EV": percentile_of(res_c["EV"], seeded_sample["EV"]),
    }
    ev_p90_seeded = float(seeded_sample["EV"].quantile(0.90))
    ev_p90_committed_style = float(committed_sample["EV"].quantile(0.90))
    v_net_success_p90_seeded = float(seeded_sample["V_net_success"].quantile(0.90))
    print(f"\n  scenario_c percentiles in seeded sample (n={len(seeded_sample)}):")
    print(f"    p_success={res_c['p_success']:.4f} -> percentile {percentiles['p_success']:.2f}")
    print(f"    V_net_success={res_c['V_net_success']:.5f} -> percentile {percentiles['V_net_success']:.2f}")
    print(f"    V_net_turnover={res_c['V_net_turnover']:.5f} -> percentile {percentiles['V_net_turnover']:.2f}")
    print(f"    EV={res_c['EV']:.5f} -> percentile {percentiles['EV']:.2f} "
          f"(percentile in committed-test-style sample: {percentile_of(res_c['EV'], committed_sample['EV']):.2f})")
    print(f"    EV p90, seeded sample (30 random matches, seed={SEED}): {ev_p90_seeded:.5f}")
    print(f"    EV p90, committed-test-style sample (first 30 alphabetical, seed=42/file): {ev_p90_committed_style:.5f}")
    print(f"    scenario_c EV >= seeded p90: {res_c['EV'] >= ev_p90_seeded}")
    print(f"    scenario_c EV >= committed-test-style p90: {res_c['EV'] >= ev_p90_committed_style}")
    print(f"    V_net_success p90, seeded sample: {v_net_success_p90_seeded:.5f}")
    print(f"    scenario_c V_net_success >= seeded p90 (R1's condition): {res_c['V_net_success'] >= v_net_success_p90_seeded}")

    print("\n  n_visible_players distribution in value_model_rows_v2.parquet ...")
    vm_rows = pd.read_parquet(VALUE_ROWS_V2_PATH, columns=["n_visible_players"])
    nvp_dist = vm_rows["n_visible_players"].describe(percentiles=[0.01, 0.05, 0.10, 0.25, 0.5, 0.75, 0.9]).to_dict()
    share_le_6 = float((vm_rows["n_visible_players"] <= 6).mean())
    print(f"    describe: {nvp_dist}")
    print(f"    share of training rows with <=6 visible players: {share_le_6:.6f} ({share_le_6 * 100:.4f}%)")

    scenario_c_n_visible = 4 + 1 + 1  # 4 opponents, 1 teammate, 1 actor
    scenario_c_max_opp_x = 70.0  # scenario_c's opponents are all at x=70; passer at x=60, teammate/dest at x=95
    print(f"\n  scenario_c synthetic frame: n_visible_players={scenario_c_n_visible} "
          f"(opponents at x=70 only, no opponent beyond x=70 -- no candidate goalkeeper-depth defender; "
          f"real defending-team keepers sit near the HIGH-x end of the passer's attacking frame, "
          f"established in Task 19c/19d as the 'defensive_line_x' convention)")

    summary = {
        "scenario_a": res_a, "scenario_b": res_b, "scenario_c": res_c,
        "scenario_c_percentiles_in_seeded_sample": percentiles,
        "seeded_sample": {"n_rows": len(seeded_sample), "n_matches": len(seeded_match_ids),
                           "match_ids": seeded_match_ids, "seed": SEED},
        "committed_test_style_sample": {"n_rows": len(committed_sample)},
        "EV_p90_seeded_sample": ev_p90_seeded, "EV_p90_committed_test_style_sample": ev_p90_committed_style,
        "scenario_c_EV_ge_seeded_p90": bool(res_c["EV"] >= ev_p90_seeded),
        "scenario_c_EV_ge_committed_style_p90": bool(res_c["EV"] >= ev_p90_committed_style),
        "V_net_success_p90_seeded_sample": v_net_success_p90_seeded,
        "scenario_c_V_net_success_ge_seeded_p90_R1_condition": bool(res_c["V_net_success"] >= v_net_success_p90_seeded),
        "n_visible_players_distribution_value_model_rows_v2": nvp_dist,
        "share_training_rows_le_6_visible": share_le_6,
        "scenario_c_n_visible_players": scenario_c_n_visible,
        "scenario_c_has_goalkeeper_depth_defender": False,
    }
    OUT_PATH.write_text(json.dumps(summary, indent=2, default=str))
    print(f"\nWrote {OUT_PATH}")
    return summary


if __name__ == "__main__":
    main()
