"""
Task 54, A5 and A7 outputs from the scorecard v2 parquets (after task54_scorecard.py):
  docs/scorecard/index.html         -- scorecard v2 (Task 51's page, extended for tiers
                                       1A / 1B, STYLE labels and the HOLD_VARIATION interval)
  docs/scorecard/index_public.html  -- same, with every PFF-derived value (AV) removed and a note
  docs/scorecard/figure1.png        -- Figure 1 (Card A; rows = praised-list DMs present by ID +
                                       the top three DMs by shrunk PR2_flag_keep)
Descriptive only. Run: python src/engine_v2/task54_outputs.py
"""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

import task51_outputs as t51o  # noqa: E402

REPO = Path(__file__).parent.parent.parent
PROC = REPO / "data" / "processed"
OUT_DIR = REPO / "docs" / "scorecard"
SUMMARY = json.loads((REPO / "data" / "engine_v2_task54.json").read_text())
TIER_TEXT = {
    "TIER 1A": "Confirmed on held-back data FOR DEEP MIDFIELDERS (switching; Task 53 R1).",
    "TIER 1B": "Stable within deep midfielders and confirmed on held-back data for ALL players "
               "(press resistance: Task 48 C4, C6; speeding up, recycling, quick-and-safe: Task 53 R4, R5, R7).",
    "TIER 2": "Stable, but no confirmed link to team results.",
    "TIER 3": "Not reliable enough within deep midfielders to rank them. Shown greyed, with the reason.",
}
STYLE_TEXT = ("STYLE marks the tempo-style measures (speeding up, recycling, switching): a high or low value is a "
              "type of player, not better or worse. The tier describes the evidence, not a ranking of quality.")
PUBLIC_NOTE = ("Public version: availability (AV), which is derived from PFF FC / Gradient Sports World Cup 2022 tracking "
               "data, is omitted here because PFF data is not redistributed.")
FIG_COLS = ["PR2_flag_keep", "M4_ACCEL", "M4_SLOW", "M4_SWITCH", "M2", "W"]


def adapt(template: str) -> str:
    """Task 51's template, extended: badge classes for 1A / 1B, STYLE marker, public note hook."""
    t = template
    reps = [
        (".b1{background:var(--t1)}", ".b1a{background:#7a3e9d}.b1b{background:var(--t1)}"),
        ("const tb=t=>`<span class=\"badge b${t.slice(-1)}\">${t}</span>`;",
         "const tb=t=>`<span class=\"badge b${t.replace('TIER ','').toLowerCase()}\">${t}</span>`;"),
        ("${esc(d)}<br><span class=\"lab\">${h.tier} · rel ${f(h.rel,2)}</span></th>",
         "${esc(d)}${h.style?' <span class=\"lab\">STYLE</span>':''}<br><span class=\"lab\">${h.tier} · rel ${f(h.rel,2)}</span></th>"),
        ("return {tier:r.tier,rel:r.reliability,src:r.reliability_source,note:r.note,floor:r.floor}",
         "return {tier:r.tier,rel:r.reliability,src:r.reliability_source,note:r.note,floor:r.floor,style:r.style}"),
        ("function credits(c){return `<p class=\"credits\">Data: StatsBomb (open data).${c===\"B\"?\" Tracking: PFF FC / Gradient Sports WC2022 (availability, AV).\":\"\"}</p>`}",
         "function credits(c){return `<p class=\"credits\">Data: StatsBomb (open data).${c===\"B\"&&!META.public?\" Tracking: PFF FC / Gradient Sports WC2022 (availability, AV).\":\"\"}${c===\"B\"&&META.public?\" \"+META.public:\"\"}</p>`}"),
        ("<section><h2>What the tiers mean</h2><div class=\"legend\" id=\"legend\"></div></section>",
         "<section><h2>What the tiers mean</h2><div class=\"legend\" id=\"legend\"></div><p class=\"small\" id=\"style\"></p><p class=\"small\" id=\"pub\"></p></section>"),
        ("document.getElementById(\"legend\").innerHTML=",
         "document.getElementById(\"style\").textContent=META.style;document.getElementById(\"pub\").textContent=META.public||\"\";document.getElementById(\"legend\").innerHTML="),
    ]
    for a, b in reps:
        assert t.count(a) == 1, a[:60]
        t = t.replace(a, b)
    return t


def page(cards: dict, public: bool) -> str:
    data = {c: t51o.records(df) for c, df in cards.items()}
    meta = {"titles": t51o.CARD_TITLES, "tiers": TIER_TEXT, "style": STYLE_TEXT, "public": PUBLIC_NOTE if public else None,
            "dims": {c: list(dict.fromkeys(cards[c]["dimension"])) for c in ("A", "B")}}
    return adapt(t51o.TEMPLATE).replace("__DATA__", json.dumps(data)).replace("__META__", json.dumps(meta))


def figure1(A: pd.DataFrame):
    rows = [int(p) for p in SUMMARY["figure1"]["rows"]]
    praised = {int(p) for p in SUMMARY["figure1"]["praised_present"]}
    names = {int(k): v for k, v in SUMMARY["figure1"]["names"].items()}
    fig, axes = plt.subplots(1, len(FIG_COLS), figsize=(2.55 * len(FIG_COLS), 0.62 * len(rows) + 1.9), sharey=True)
    col = {"TIER 1A": "#7a3e9d", "TIER 1B": "#1f6f5c", "TIER 2": "#2f5d9e", "TIER 3": "#9a9890"}
    for ax, d in zip(axes, FIG_COLS):
        sub = A[A["dimension"] == d].set_index("player_id")
        tier = sub["tier"].iloc[0]
        for i, p in enumerate(rows):
            r = sub.loc[p]
            if r["label"] == "not enough data":
                ax.text(50, i, "not enough data", ha="center", va="center", fontsize=7, color="0.5")
                continue
            ax.plot([r["ci_low_90_pct"], r["ci_high_90_pct"]], [i, i], color=col[tier], lw=3, alpha=0.55, solid_capstyle="butt")
            ax.plot(r["percentile"], i, "o", color="black", ms=4.5)
            ax.text(101, i, f"{r['percentile']:.0f}", va="center", fontsize=7)
        ax.axvline(50, color="0.7", lw=0.8, ls="--")
        ax.set_xlim(0, 108)
        ax.set_xticks([0, 50, 100])
        ax.tick_params(axis="x", labelsize=7)
        ax.set_title(f"{d}{' (STYLE)' if d.startswith('M4_') else ''}\n", fontsize=8.5)
        ax.text(0.5, 1.02, tier, transform=ax.transAxes, ha="center", va="bottom", fontsize=7.5, color="white",
                bbox=dict(boxstyle="round,pad=0.25", fc=col[tier], ec="none"))
    axes[0].set_yticks(range(len(rows)))
    axes[0].set_yticklabels([names[p] + (" *" if p in praised else "") for p in rows], fontsize=8.5)
    axes[0].set_ylim(len(rows) - 0.5, -0.6)
    fig.suptitle("Figure 1. 2015/16 big five (Card A, 185 deep midfielders): within-DM percentile (dot) and 90% interval (bar)\n"
                 "Rows: praised-list deep midfielders present (*, by StatsBomb id) and the top three by shrunk press resistance. "
                 "Data: StatsBomb (open data).", fontsize=8.5)
    fig.tight_layout(rect=[0, 0, 1, 0.9])
    fig.savefig(OUT_DIR / "figure1.png", dpi=170)
    plt.close(fig)


def main():
    cards = {c: pd.read_parquet(PROC / f"scorecard_v2_card_{c.lower()}.parquet") for c in ("A", "B", "C")}
    (OUT_DIR / "index.html").write_text(page(cards, public=False))
    pub = dict(cards)
    pub["B"] = cards["B"][cards["B"]["dimension"] != "AV"].reset_index(drop=True)
    html = page(pub, public=True)
    assert '"dimension": "AV"' not in html and '"AV":' not in html
    (OUT_DIR / "index_public.html").write_text(html)
    figure1(cards["A"])
    print(f"Wrote {OUT_DIR / 'index.html'}, index_public.html, figure1.png")


if __name__ == "__main__":
    main()
