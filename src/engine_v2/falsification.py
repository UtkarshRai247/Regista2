"""
Task 15 -- Engine v2, Step 7: the falsification battery
(docs/specs/engine-v2-rebuild.md section 6). Assembles T1-T5 and T7
(T6 is explicitly NOT run in this task -- task-15-engine-v2.md's Step 7
lists only T1 through T5 and T7; T6 needs per-player Decision, which the
hard rules forbid computing here) from the summaries already written by
grid.py (T1), value_models.py (T2), ev_policy.py (T3), pass_success_v2.py
(T5, T7), and runs test_t4_synthetic.py's assertions for T4. STOPS here
by design: no player metrics, no leaderboards, no studies follow this
script, whatever the verdicts are.

Run: python src/engine_v2/falsification.py
"""
import json
import subprocess
import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")

DATA_DIR = Path(__file__).parent.parent.parent / "data"
SUMMARY_PATH = DATA_DIR / "engine_v2_step7_falsification.json"


def run_t4() -> dict:
    result = subprocess.run([sys.executable, str(Path(__file__).parent / "test_t4_synthetic.py")],
                             capture_output=True, text=True)
    return {"pass": result.returncode == 0, "stdout": result.stdout, "stderr": result.stderr}


def main():
    print("Step 7: falsification battery ...")
    step2 = json.loads((DATA_DIR / "engine_v2_step2_options.json").read_text())
    step4 = json.loads((DATA_DIR / "engine_v2_step4_pass_success.json").read_text())
    step5 = json.loads((DATA_DIR / "engine_v2_step5_value_models.json").read_text())
    step6 = json.loads((DATA_DIR / "engine_v2_step6_ev_policy.json").read_text())

    t1 = {"pass_condition": "median displacement between scored chosen destination and pass_end_location <= 2 yards",
          "median_displacement_u": step2["T1_median_displacement_u"], "verdict": step2["T1_pass_condition_le_2u"]}

    t2 = {"pass_condition": "M_for's prediction differs materially (>=10% of its own predicted-probability IQR) "
                              "between the 10th and 90th percentile of numerical_advantage_ahead, ball location fixed",
          **step5["T2"], "verdict": step5["T2"]["T2_pass"]}

    t3 = {"pass_condition": "Spearman(EV, p_success) < 0.90 across all options",
          "spearman_rho": step6["T3"]["spearman_rho"], "n_sample": step6["T3"]["n_sample"],
          "verdict": step6["T3"]["T3_pass"]}

    t4_run = run_t4()
    t4 = {"pass_condition": "three hand-built synthetic scenarios (unmarked runner > marked sideways at equal "
                              "p_success; open space > congested cluster; through ball in top EV decile) all hold",
          "verdict": t4_run["pass"], "output": t4_run["stdout"]}

    t5 = {"pass_condition": "pass-success calibration off by no more than 5pp in every pass-length bucket",
          "by_bucket": step4["T5_calibration_by_length_bucket"], "verdict": step4["T5_pass_condition_le_5pp_all_buckets"]}

    t7 = {"pass_condition": "reported, not a pass/fail gate: share of chosen destinations outside the convex hull "
                              "of training destinations, per length bucket",
          "by_bucket": step4["T7_offpolicy_support_by_length_bucket"], "verdict": None}

    t6 = {"pass_condition": "split-half reliability of Decision, 100 splits, >=200 passes, >= 0.60",
          "verdict": None, "note": "NOT RUN -- task-15-engine-v2.md Step 7 explicitly lists only T1-T5 and T7; "
                                     "T6 requires per-player Decision, which this task's hard rules forbid computing."}

    battery = {"T1": t1, "T2": t2, "T3": t3, "T4": t4, "T5": t5, "T6": t6, "T7": t7}
    for name, t in battery.items():
        v = t["verdict"]
        v_str = "PASS" if v is True else ("FAIL" if v is False else "N/A (reported only)" if name == "T7" else "NOT RUN")
        print(f"  {name}: {v_str} -- {t['pass_condition']}")

    gate_tests = ["T1", "T2", "T3", "T4", "T5"]
    all_gate_pass = all(battery[t]["verdict"] for t in gate_tests)
    print(f"\n  Overall (T1-T5 pass/fail gates, T6 not run, T7 reported only): {'ALL PASS' if all_gate_pass else 'AT LEAST ONE FAILURE'}")

    SUMMARY_PATH.write_text(json.dumps(battery, indent=2, default=str))
    print(f"\nWrote {SUMMARY_PATH}")
    return battery


if __name__ == "__main__":
    main()
