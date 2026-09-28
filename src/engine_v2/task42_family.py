"""
Task 42: the fixed claim rule. Family = every within-deep-midfielder
results test in Steps 1-3, Holm-adjusted together; a within-DM results
claim is allowed only if Holm p < 0.05 AND the positive control on the same
rows is positive with p < 0.05. Also reports each test's Holm p when Task
41's 12-test family is added. docs/specs/task-42-improvement-round-2.md.

Run: python src/engine_v2/task42_family.py   (after Steps 1-3)
"""
import json
from pathlib import Path

from statsmodels.stats.multitest import multipletests

DATA_DIR = Path(__file__).parent.parent.parent / "data"
SUMMARY_PATH = DATA_DIR / "engine_v2_task42_family.json"


def main():
    s1 = json.loads((DATA_DIR / "engine_v2_task42_step1.json").read_text())["tests"]
    s2 = json.loads((DATA_DIR / "engine_v2_task42_step2.json").read_text())["r2"]
    s3 = json.loads((DATA_DIR / "pff_task42_step3.json").read_text())["r2"]["DM_report"]
    t41 = json.loads((DATA_DIR / "engine_v2_task41_steps7_10.json").read_text())["step10"]

    fam = []
    for k, r in s1.items():
        if k.startswith("dm|"):
            fam.append({"test": f"Step 1 {k}", "coef_per100": r["coef_per_sd_per100"], "p": r["p"],
                        "control_coef_per100": r["control"]["coef_per_sd_per100"], "control_p": r["control"]["p"]})
    for k, r in s2.items():
        if k.startswith("dm|"):
            fam.append({"test": f"Step 2 R2 {k}", "coef_per100": r["coef_per_sd_per100"], "p": r["p"],
                        "control_coef_per100": r["control"]["coef_per_sd_per100"], "control_p": r["control"]["p"]})
    fam.append({"test": "Step 3 R2 dm|av_prog|y_net_xg", "coef_per100": s3["coef_per_sd_per100"], "p": s3["p"],
                "control_coef_per100": None, "control_p": None})

    holm = multipletests([f["p"] for f in fam], method="holm")[1]
    holm_ext = multipletests([f["p"] for f in fam] + [t["p_raw"] for t in t41], method="holm")[1][:len(fam)]
    for f, h, he in zip(fam, holm, holm_ext):
        f["p_holm_task42"] = float(h)
        f["p_holm_with_task41"] = float(he)
        ctrl_ok = f["control_p"] is not None and f["control_coef_per100"] > 0 and f["control_p"] < 0.05
        f["control_ok"] = bool(ctrl_ok)
        f["claim_allowed"] = bool(h < 0.05 and ctrl_ok)
        print(f"  {f['test']}: coef100={f['coef_per100']:+.4f} p={f['p']:.4g} holm={h:.4g} holm+41={he:.4g} "
              f"control_ok={ctrl_ok} claim={f['claim_allowed']}")
    SUMMARY_PATH.write_text(json.dumps({"n_family": len(fam), "n_with_task41": len(fam) + len(t41), "family": fam},
                                       indent=2, default=str))
    print(f"Wrote {SUMMARY_PATH}")


if __name__ == "__main__":
    main()
