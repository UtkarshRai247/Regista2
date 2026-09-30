"""
Task 55: presentation only. docs/specs/task-55-figure1.md.
Step 1: redraw docs/scorecard/figure1.png (+ figure1.pdf) from the SAVED Card A values
  (data/processed/scorecard_v2_card_a.parquet; rows from data/engine_v2_task54.json's
  figure1 block) -- no recomputation; asserts every plotted value equals Task 54 A5.
Step 2: add the research lead's Card B note to docs/scorecard/index.html and
  index_public.html (one inserted element, nothing else changed).

Run: python src/engine_v2/task55_figure1.py
"""
import json
import textwrap
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

REPO = Path(__file__).parent.parent.parent
OUT = REPO / "docs" / "scorecard"
A = pd.read_parquet(REPO / "data" / "processed" / "scorecard_v2_card_a.parquet")
S = json.loads((REPO / "data" / "engine_v2_task54.json").read_text())["figure1"]
COLS = [("PR2_flag_keep", "Press resistance"), ("M4_ACCEL", "Speeds play up (style)"), ("M4_SLOW", "Recycles (style)"),
        ("M4_SWITCH", "Switches play (style)"), ("M2", "Quick and safe under pressure"), ("W", "Asks for the ball under pressure")]
SHORT = {5574: "Toni Kroos", 5203: "Sergio Busquets", 4325: "Thiago Motta", 7024: "Jorginho", 8294: "Claudio Marchisio"}
TIER_COL = {"TIER 1A": "#7a3e9d", "TIER 1B": "#1f6f5c", "TIER 2": "#2f5d9e", "TIER 3": "#9a9890"}
TITLE = ("Figure 1. Where elite deep midfielders sit: 2015/16 big five, 185 deep midfielders "
         "(percentile within deep midfielders, 90% interval)")
FOOT = "* on a list of praised midfielders fixed before any measure. Style columns describe type, not quality. Data: StatsBomb open data."
NOTE = ("The modern-era sample has few matches per deep midfielder, so most dimensions are not stable enough here to "
        "rank players. Use Card A (2015/16) for rankings; Card B is shown for completeness.")
ANCHOR = 'document.getElementById("view").innerHTML=`<h2>${esc(META.titles[c])}</h2><p class="small">Cells:'
INSERT = ('document.getElementById("view").innerHTML=`<h2>${esc(META.titles[c])}</h2>${c==="B"?`<p class="note" '
          'style="border-left:3px solid var(--acc);padding:6px 10px;margin:4px 0 10px">' + NOTE + '</p>`:""}<p class="small">Cells:')


def figure():
    rows = [int(p) for p in S["rows"]]
    praised = {int(p) for p in S["praised_present"]}
    assert set(rows) == set(SHORT)
    vals = {}
    fig, axes = plt.subplots(1, len(COLS), figsize=(10.0, 3.5), sharey=True, dpi=160)
    for ax, (d, label) in zip(axes, COLS):
        sub = A[A["dimension"] == d].set_index("player_id")
        tier = sub["tier"].iloc[0]
        for i, p in enumerate(rows):
            r = sub.loc[p]
            lo, hi, pct = float(r["ci_low_90_pct"]), float(r["ci_high_90_pct"]), float(r["percentile"])
            vals[(p, d)] = (pct, lo, hi)
            ax.plot([lo, hi], [i, i], color=TIER_COL[tier], lw=4, alpha=0.5, solid_capstyle="butt")
            ax.plot(pct, i, "o", color="black", ms=4.5, zorder=3)
            # label left of the interval when the dot is near the right edge, so it never sits on the dot
            if pct >= 85:
                ax.text(lo - 3, i, f"{pct:.0f}", ha="right", va="center", fontsize=7)
            else:
                ax.text(hi + 3, i, f"{pct:.0f}", ha="left", va="center", fontsize=7)
        ax.axvline(50, color="0.75", lw=0.8, ls="--", zorder=0)
        ax.set_xlim(-2, 102)
        ax.set_xticks([0, 50, 100])
        ax.tick_params(axis="x", labelsize=7, length=2)
        for sp in ("top", "right"):
            ax.spines[sp].set_visible(False)
        ax.set_title(textwrap.fill(label, 20), fontsize=8, pad=17)
        ax.text(0.5, 1.015, tier, transform=ax.transAxes, ha="center", va="bottom", fontsize=6.5, color="white",
                bbox=dict(boxstyle="round,pad=0.2", fc=TIER_COL[tier], ec="none"))
    axes[0].set_yticks(range(len(rows)))
    axes[0].set_yticklabels([SHORT[p] + (" *" if p in praised else "") for p in rows], fontsize=8)
    axes[0].set_ylim(len(rows) - 0.5, -0.5)
    fig.suptitle(TITLE, fontsize=8.6, x=0.01, ha="left", y=0.985)
    fig.text(0.01, 0.012, FOOT, fontsize=7, ha="left", va="bottom")
    fig.subplots_adjust(left=0.13, right=0.99, top=0.76, bottom=0.14, wspace=0.2)
    fig.savefig(OUT / "figure1.png", dpi=160)
    fig.savefig(OUT / "figure1.pdf")
    plt.close(fig)
    return vals


def check(vals: dict) -> dict:
    """Every plotted value equals the saved Task 54 A5 value (same parquet row)."""
    for (p, d), (pct, lo, hi) in vals.items():
        r = A[(A["player_id"] == p) & (A["dimension"] == d)].iloc[0]
        assert (pct, lo, hi) == (float(r["percentile"]), float(r["ci_low_90_pct"]), float(r["ci_high_90_pct"]))
    return {f"{SHORT[p]}|{d}": [round(v, 4) for v in t] for (p, d), t in vals.items()}


def note_pages() -> dict:
    out = {}
    for name in ("index.html", "index_public.html"):
        path = OUT / name
        html = path.read_text()
        assert html.count(ANCHOR) == 1 and NOTE not in html
        new = html.replace(ANCHOR, INSERT)
        path.write_text(new)
        out[name] = {"bytes_before": len(html.encode()), "bytes_after": len(new.encode())}
    return out


def main():
    vals = figure()
    checked = check(vals)
    pages = note_pages()
    sizes = {f: (OUT / f).stat().st_size for f in ("figure1.png", "figure1.pdf")}
    from PIL import Image
    w, h = Image.open(OUT / "figure1.png").size
    (REPO / "data" / "engine_v2_task55.json").write_text(json.dumps({"plotted_equals_task54_A5": True, "values": checked,
                                                                      "sizes_bytes": sizes, "png_px": [w, h], "pages": pages}, indent=2))
    print(json.dumps({"sizes": sizes, "png_px": [w, h], "pages": pages}, indent=1))
    print(f"all {len(checked)} plotted (percentile, low, high) triples equal Task 54 A5's saved values")


if __name__ == "__main__":
    main()
