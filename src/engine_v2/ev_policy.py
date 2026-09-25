"""
Task 15 -- Engine v2, Step 6: EV and the policy (docs/specs/
engine-v2-rebuild.md sections 4-5).

V_net(features) = M_for(features) - M_against(features), evaluated with
the SAME pair of models (M_for, M_against, from value_models.py) for
both branches -- this symmetry is the fix for Defect 1.

SUCCESS branch: state built in the PASSING team's own frame of
reference (candidate=ball, passer=prev, the frame's own teammate/
opponent roles, the passer's own score_diff, PATTERN_CODE["Regular
Play"] as the continuation pattern -- reused unchanged from v1's own
convention, not part of the audited defects). V_net_success =
M_for(succ) - M_against(succ), value directly to the passing team.

TURNOVER branch: state built in the OPPONENT's own frame of reference --
same physical ball/passer locations, but direction flipped, score_diff
negated, PATTERN_CODE["From Counter"] (reused), and -- the detail this
fix hinges on -- the freeze-frame teammate/opponent ROLE LABELS SWAPPED,
since "their teammates" are the passer's original opponents once they
have the ball. Raw model outputs there are M_for=P(opponent scores),
M_against=P(original team scores), so value to the ORIGINAL team is the
OPPOSITE pairing: V_net_turnover = M_against(turn) - M_for(turn). This
swap is not a new asymmetry -- it is what makes both branches
symmetric from the passer's team's own point of view, which a single
sign-flipped model (v1's approach) could never express.

EV = p_success * V_net_success + (1 - p_success) * V_net_turnover.

Then trains the behavior policy on the same candidate feature set as
pass_success_v2.py, label=chosen, softmax within each pass's option set
-- reports top-1/top-3 accuracy (expected far lower than v1's, since a
pass now has ~423 candidates on average instead of ~9; this is not a
failure of anything). Policy TRAINING uses negative subsampling (10
random unchosen candidates per pass, alongside every chosen row) for
tractability on 16GB unified memory against a ~106M-row corpus with a
0.24% positive rate -- a disclosed resource-driven choice, not a
methodology one; POLICY EVALUATION (top-1/top-3, softmax) always uses
each held-out pass's FULL candidate set, never the subsample.

Then T3: Spearman correlation between EV and p_success across a random
sample of candidates (5,000,000, seed 42 -- computing an exact rank
correlation over the full ~106M-row corpus is not necessary for a
stable estimate and is avoided for tractability); must be < 0.90.

Run: python src/engine_v2/ev_policy.py
"""
import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import xgboost as xgb
from scipy.stats import spearmanr
from sklearn.metrics import roc_auc_score

from geometry import team_period_directions, normalize_xy
from features import state_features_batch
from value_models import PATTERN_CODE, STATE_FEATURES, MODEL_FOR_PATH, MODEL_AGAINST_PATH
from common import CANDIDATE_FEATURES, match_disjoint_split, prep_X

warnings.filterwarnings("ignore")

DATA_DIR = Path(__file__).parent.parent.parent / "data"
EVENTS_DIR = DATA_DIR / "raw" / "events"
FRAMES_DIR = DATA_DIR / "raw" / "frames"
SCORED_DIR = DATA_DIR / "processed" / "engine_v2" / "options_scored"
EV_DIR = DATA_DIR / "processed" / "engine_v2" / "options_ev"
POLICY_MODEL_PATH = DATA_DIR / "processed" / "engine_v2" / "policy_model.json"
SUMMARY_PATH = DATA_DIR / "engine_v2_step6_ev_policy.json"

XGB_KWARGS_POLICY = dict(n_estimators=200, max_depth=4, learning_rate=0.05,
                          subsample=0.8, colsample_bytree=0.8, random_state=42, eval_metric="logloss")
NEG_SAMPLES_PER_PASS = 10
RNG_SEED = 42
T3_SAMPLE_SIZE = 5_000_000
T3_THRESHOLD = 0.90


def softmax_per_group(scores: np.ndarray, groups: np.ndarray) -> np.ndarray:
    df = pd.DataFrame({"score": scores, "group": groups})
    out = np.empty(len(df))
    for _, g in df.groupby("group"):
        s = g["score"].values
        e = np.exp(s - s.max())
        out[g.index] = e / e.sum()
    return out


def per_event_context(match_id: int, event_ids_needed: set) -> dict:
    events = pd.read_parquet(EVENTS_DIR / f"{match_id}.parquet")
    events = events.sort_values("index").reset_index(drop=True)
    events["t"] = events["minute"] * 60 + events["second"]
    period_end = events.groupby("period")["t"].transform("max")
    directions = team_period_directions(events)
    teams = events["team"].dropna().unique().tolist()
    score = {t: 0 for t in teams}
    is_goal = ((events["type"] == "Shot") & (events["shot_outcome"] == "Goal")) | (events["type"] == "Own Goal Against")

    ctx = {}
    for i in range(len(events)):
        row = events.iloc[i]
        team = row["team"]
        opp_teams = [t for t in teams if t != team]
        opponent = opp_teams[0] if opp_teams else None
        if row["id"] in event_ids_needed:
            ctx[row["id"]] = {
                "score_diff": score.get(team, 0) - score.get(opponent, 0) if opponent else 0,
                "time_remaining_period": float(period_end.iloc[i] - row["t"]),
                "direction": directions.get((team, row["period"]), 1),
            }
        if is_goal.iloc[i]:
            scorer = opponent if row["type"] == "Own Goal Against" else team
            if scorer in score:
                score[scorer] += 1
    return ctx


def build_ev_for_match(match_id: int, model_for, model_against):
    scored_path = SCORED_DIR / f"{match_id}.parquet"
    if not scored_path.exists():
        return None
    cand = pd.read_parquet(scored_path)
    frames = pd.read_parquet(FRAMES_DIR / f"{match_id}.parquet")
    frames_by_event = {eid: g for eid, g in frames.groupby("id")}
    ctx_by_event = per_event_context(match_id, set(cand["event_id"].unique()))

    succ_rows, turn_rows, order = [], [], []
    for eid, g in cand.groupby("event_id", sort=False):
        ctx = ctx_by_event.get(eid)
        frame = frames_by_event.get(eid)
        if ctx is None or frame is None:
            continue
        direction = ctx["direction"]
        opp_direction = -direction
        passer_raw = np.array([g["passer_x"].iloc[0], g["passer_y"].iloc[0]])
        cand_raw = g[["candidate_x", "candidate_y"]].values.astype(float)

        teammates = frame[(frame["teammate"] == True) & (frame["actor"] == False)]
        opponents = frame[frame["teammate"] == False]
        team_raw = np.array([list(l) for l in teammates["location"]], dtype=float) if len(teammates) else np.zeros((0, 2))
        opp_raw = np.array([list(l) for l in opponents["location"]], dtype=float) if len(opponents) else np.zeros((0, 2))

        succ = state_features_batch(cand_raw, passer_raw, direction, team_raw, opp_raw, len(frame))
        succ["time_remaining_period"] = np.full(len(g), ctx["time_remaining_period"])
        succ["score_diff"] = np.full(len(g), ctx["score_diff"])
        succ["play_pattern_code"] = np.full(len(g), PATTERN_CODE["Regular Play"])

        turn = state_features_batch(cand_raw, passer_raw, opp_direction, opp_raw, team_raw, len(frame))
        turn["time_remaining_period"] = np.full(len(g), ctx["time_remaining_period"])
        turn["score_diff"] = np.full(len(g), -ctx["score_diff"])
        turn["play_pattern_code"] = np.full(len(g), PATTERN_CODE["From Counter"])

        succ_rows.append(pd.DataFrame(succ))
        turn_rows.append(pd.DataFrame(turn))
        order.append(g.index.values)

    if not succ_rows:
        return None

    X_succ = pd.concat(succ_rows, ignore_index=True)[STATE_FEATURES].astype(float)
    X_turn = pd.concat(turn_rows, ignore_index=True)[STATE_FEATURES].astype(float)
    p_for_succ = model_for.predict_proba(X_succ)[:, 1]
    p_against_succ = model_against.predict_proba(X_succ)[:, 1]
    p_for_turn = model_for.predict_proba(X_turn)[:, 1]
    p_against_turn = model_against.predict_proba(X_turn)[:, 1]
    v_net_success = p_for_succ - p_against_succ
    v_net_turnover = p_against_turn - p_for_turn

    idx_order = np.concatenate(order)
    cand = cand.loc[idx_order].reset_index(drop=True)
    cand["V_net_success"] = v_net_success.astype("float32")
    cand["V_net_turnover"] = v_net_turnover.astype("float32")
    cand["EV"] = (cand["p_success"] * cand["V_net_success"] + (1 - cand["p_success"]) * cand["V_net_turnover"]).astype("float32")

    EV_DIR.mkdir(parents=True, exist_ok=True)
    cand.to_parquet(EV_DIR / f"{match_id}.parquet")
    return len(cand)


def sample_for_policy_training(rng: np.random.Generator) -> pd.DataFrame:
    parts = sorted(EV_DIR.glob("*.parquet"))
    frames = []
    cols = CANDIDATE_FEATURES + ["match_id", "event_id", "chosen"]
    for p in parts:
        df = pd.read_parquet(p, columns=cols)
        chosen = df[df["chosen"]]
        unchosen = df[~df["chosen"]]
        n_neg = min(NEG_SAMPLES_PER_PASS * len(chosen), len(unchosen))
        neg_sample = unchosen.sample(n=n_neg, random_state=rng.integers(0, 2**31 - 1)) if n_neg > 0 else unchosen.iloc[0:0]
        frames.append(pd.concat([chosen, neg_sample], ignore_index=True))
    return pd.concat(frames, ignore_index=True)


def evaluate_policy_full_sets(model, fill_values: dict, test_match_ids: set) -> dict:
    parts = [p for p in sorted(EV_DIR.glob("*.parquet")) if int(p.stem) in test_match_ids]
    top1_hits, top3_hits, n_passes = 0, 0, 0
    for p in parts:
        df = pd.read_parquet(p, columns=CANDIDATE_FEATURES + ["event_id", "chosen"])
        X, _ = prep_X(df, CANDIDATE_FEATURES, fill_values)
        raw_score = model.predict_proba(X)[:, 1]
        df["policy_probability"] = softmax_per_group(raw_score, df["event_id"].values)
        for eid, g in df.groupby("event_id"):
            ranked = g.sort_values("policy_probability", ascending=False).reset_index(drop=True)
            rank_of_chosen = ranked.index[ranked["chosen"]].tolist()
            if not rank_of_chosen:
                continue
            r = rank_of_chosen[0]
            n_passes += 1
            top1_hits += int(r == 0)
            top3_hits += int(r < 3)
    return {"n_passes_evaluated": n_passes,
            "top1_accuracy": top1_hits / n_passes if n_passes else None,
            "top3_accuracy": top3_hits / n_passes if n_passes else None}


def run_t3(rng: np.random.Generator) -> dict:
    parts = sorted(EV_DIR.glob("*.parquet"))
    samples = []
    remaining = T3_SAMPLE_SIZE
    for p in parts:
        df = pd.read_parquet(p, columns=["EV", "p_success"])
        n_take = min(len(df), max(1, remaining // max(1, len(parts))))
        if len(df) > 0:
            samples.append(df.sample(n=min(n_take, len(df)), random_state=rng.integers(0, 2**31 - 1)))
    sample = pd.concat(samples, ignore_index=True)
    if len(sample) > T3_SAMPLE_SIZE:
        sample = sample.sample(n=T3_SAMPLE_SIZE, random_state=42)
    rho, pval = spearmanr(sample["EV"], sample["p_success"])
    return {"n_sample": int(len(sample)), "spearman_rho": float(rho), "p_value": float(pval),
            "T3_pass": bool(rho < T3_THRESHOLD)}


def main():
    print("Step 6: EV + policy ...")
    model_for = xgb.XGBClassifier()
    model_for.load_model(str(MODEL_FOR_PATH))
    model_against = xgb.XGBClassifier()
    model_against.load_model(str(MODEL_AGAINST_PATH))

    match_ids = sorted(int(p.stem) for p in SCORED_DIR.glob("*.parquet"))
    n_ev_rows = 0
    for i, mid in enumerate(match_ids):
        n = build_ev_for_match(mid, model_for, model_against)
        if n:
            n_ev_rows += n
        if (i + 1) % 50 == 0:
            print(f"  {i + 1}/{len(match_ids)} matches, EV rows so far={n_ev_rows}")
    print(f"  total EV rows: {n_ev_rows}")

    rng = np.random.default_rng(RNG_SEED)
    print("  T3 (EV vs p_success Spearman correlation) ...")
    t3 = run_t3(rng)
    print(f"    {t3}")

    print("  training policy (negative-subsampled) ...")
    policy_train_pool = sample_for_policy_training(rng)
    train, test = match_disjoint_split(policy_train_pool, "match_id", 0.2, 42)
    X_train, fill_values = prep_X(train, CANDIDATE_FEATURES)
    y_train = train["chosen"].astype(int)
    model_policy = xgb.XGBClassifier(**XGB_KWARGS_POLICY)
    model_policy.fit(X_train, y_train)
    model_policy.save_model(str(POLICY_MODEL_PATH))
    print(f"  n_policy_train_pool={len(policy_train_pool)} (chosen={int(policy_train_pool['chosen'].sum())}, "
          f"unchosen_sampled={int((~policy_train_pool['chosen']).sum())})")

    print("  evaluating policy on held-out matches' FULL candidate sets ...")
    test_match_ids = set(test["match_id"].unique())
    policy_eval = evaluate_policy_full_sets(model_policy, fill_values, test_match_ids)
    print(f"    {policy_eval}")

    summary = {
        "n_ev_rows": n_ev_rows, "T3": t3,
        "n_policy_train_pool": int(len(policy_train_pool)),
        "n_policy_chosen": int(policy_train_pool["chosen"].sum()),
        "n_policy_unchosen_sampled": int((~policy_train_pool["chosen"]).sum()),
        "n_test_matches": len(test_match_ids),
        "policy_evaluation": policy_eval,
    }
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2, default=str))
    print(f"\nWrote {SUMMARY_PATH}")
    return summary


if __name__ == "__main__":
    main()
