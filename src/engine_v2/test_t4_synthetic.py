"""
Task 15 -- Engine v2, Step 7: T4, three hand-built synthetic scenarios
with known right answers (docs/specs/engine-v2-rebuild.md section 6),
run through the ACTUAL trained models (pass-success, M_for, M_against)
so this is a genuine test of the built instrument, not just of the EV
formula in isolation. Plain assert-based, no framework (no pytest
anywhere in this repo).

Each scenario builds one shared hand-built freeze frame (a fixed set of
opponent/teammate raw locations for a single passer) and one or two
candidate destinations within it -- exactly how a real pass's candidate
set works (one frame, many candidates), so the two compared candidates
in (a)/(b) are genuinely evaluated against the SAME defensive picture.

(a) holds p_success EQUAL (injected at a fixed 0.75 for both candidates,
per the spec's literal "at equal p_success" -- this isolates the V_net
comparison, which is what the scenario is actually testing) and compares
real V_net_success/V_net_turnover from the real value models. (b) and
(c) use the REAL trained pass-success model's own p_success (not
injected), since neither scenario holds it fixed.

Run: python src/engine_v2/test_t4_synthetic.py
"""
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import xgboost as xgb

from features import compute_candidate_features, state_features_batch
from value_models import PATTERN_CODE, STATE_FEATURES, MODEL_FOR_PATH, MODEL_AGAINST_PATH
from pass_success_v2 import MODEL_PATH as PASS_SUCCESS_MODEL_PATH
from common import CANDIDATE_FEATURES, prep_X

warnings.filterwarnings("ignore")

DATA_DIR = Path(__file__).parent.parent.parent / "data"
EV_DIR = DATA_DIR / "processed" / "engine_v2" / "options_ev"
STEP4_SUMMARY = DATA_DIR / "engine_v2_step4_pass_success.json"


def load_models():
    model_for = xgb.XGBClassifier()
    model_for.load_model(str(MODEL_FOR_PATH))
    model_against = xgb.XGBClassifier()
    model_against.load_model(str(MODEL_AGAINST_PATH))
    pass_success = xgb.XGBClassifier()
    pass_success.load_model(str(PASS_SUCCESS_MODEL_PATH))
    import json
    fill_values = json.loads(STEP4_SUMMARY.read_text())["fill_values"]
    return model_for, model_against, pass_success, fill_values


def compute_ev(passer_raw, candidates_raw, is_teammate_dest, opponents_raw, teammates_raw,
                model_for, model_against, p_success_override=None, pass_success_model=None, fill_values=None):
    n_visible = len(opponents_raw) + len(teammates_raw) + 1  # + the actor
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
    return ev, p_success, v_net_success, v_net_turnover


def scenario_a_unmarked_runner_vs_marked_sideways(model_for, model_against):
    """An unmarked runner beyond the defensive line must have higher EV
    than a marked sideways option, at equal p_success."""
    passer_raw = np.array([60.0, 40.0])
    # a back-line 10y ahead of the passer, plus one tight marker on the sideways option
    opponents_raw = np.array([[70.0, 20.0], [70.0, 35.0], [70.0, 50.0], [70.0, 65.0], [61.0, 66.0]])
    teammates_raw = np.array([[55.0, 40.0]])
    candidates_raw = np.array([[100.0, 40.0],  # unmarked, well beyond the nx=70 line
                                [60.0, 65.0]])  # sideways, marked by the opponent at (61,66)
    is_teammate_dest = np.array([0, 0])

    ev, p_success, v_succ, v_turn = compute_ev(passer_raw, candidates_raw, is_teammate_dest,
                                                opponents_raw, teammates_raw, model_for, model_against,
                                                p_success_override=0.75)
    print(f"    unmarked runner: EV={ev[0]:.5f} (V_net_success={v_succ[0]:.5f}, V_net_turnover={v_turn[0]:.5f})")
    print(f"    marked sideways: EV={ev[1]:.5f} (V_net_success={v_succ[1]:.5f}, V_net_turnover={v_turn[1]:.5f})")
    assert ev[0] > ev[1], f"expected unmarked-runner EV ({ev[0]}) > marked-sideways EV ({ev[1]})"
    print("scenario_a_unmarked_runner_vs_marked_sideways: PASS")


def scenario_b_congested_cluster_vs_open_space(model_for, model_against, pass_success_model, fill_values):
    """A sideways pass into a 3-opponent cluster must have lower EV than
    the same pass (same distance, opposite direction) into open space."""
    passer_raw = np.array([60.0, 40.0])
    opponents_raw = np.array([[59.0, 64.0], [61.0, 65.0], [60.0, 67.0], [70.0, 20.0]])
    teammates_raw = np.array([[55.0, 40.0]])
    candidates_raw = np.array([[60.0, 65.0],   # into the 3-opponent cluster
                                [60.0, 15.0]])  # equal-distance sideways, open space
    is_teammate_dest = np.array([0, 0])

    ev, p_success, v_succ, v_turn = compute_ev(passer_raw, candidates_raw, is_teammate_dest,
                                                opponents_raw, teammates_raw, model_for, model_against,
                                                pass_success_model=pass_success_model, fill_values=fill_values)
    print(f"    into cluster:   p_success={p_success[0]:.4f}, EV={ev[0]:.5f}")
    print(f"    into open space: p_success={p_success[1]:.4f}, EV={ev[1]:.5f}")
    assert ev[1] > ev[0], f"expected open-space EV ({ev[1]}) > cluster EV ({ev[0]})"
    print("scenario_b_congested_cluster_vs_open_space: PASS")


def scenario_c_through_ball_top_decile(model_for, model_against, pass_success_model, fill_values):
    """With the defence square and a teammate beyond the line, the
    through ball must be in the top decile of EV (corpus-wide)."""
    passer_raw = np.array([60.0, 40.0])
    opponents_raw = np.array([[70.0, 20.0], [70.0, 35.0], [70.0, 50.0], [70.0, 65.0]])
    teammate_beyond = np.array([95.0, 40.0])
    teammates_raw = np.array([teammate_beyond])
    candidates_raw = np.array([teammate_beyond])
    is_teammate_dest = np.array([1])

    ev, p_success, v_succ, v_turn = compute_ev(passer_raw, candidates_raw, is_teammate_dest,
                                                opponents_raw, teammates_raw, model_for, model_against,
                                                pass_success_model=pass_success_model, fill_values=fill_values)
    through_ball_ev = float(ev[0])

    parts = sorted(EV_DIR.glob("*.parquet"))[:30]
    sample = pd.concat([pd.read_parquet(p, columns=["EV"]).sample(
        n=min(50000, len(pd.read_parquet(p, columns=["EV"]))), random_state=42) for p in parts], ignore_index=True)
    p90 = float(sample["EV"].quantile(0.90))
    print(f"    through ball: p_success={p_success[0]:.4f}, EV={through_ball_ev:.5f}, corpus p90 (n={len(sample)} sample)={p90:.5f}")
    assert through_ball_ev >= p90, f"expected through-ball EV ({through_ball_ev}) in top decile (>= {p90})"
    print("scenario_c_through_ball_top_decile: PASS")


def main():
    print("T4 synthetic scenarios ...")
    model_for, model_against, pass_success_model, fill_values = load_models()
    scenario_a_unmarked_runner_vs_marked_sideways(model_for, model_against)
    scenario_b_congested_cluster_vs_open_space(model_for, model_against, pass_success_model, fill_values)
    scenario_c_through_ball_top_decile(model_for, model_against, pass_success_model, fill_values)
    print("test_t4_synthetic.py: ALL PASS")


if __name__ == "__main__":
    main()
