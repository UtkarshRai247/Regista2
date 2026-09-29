"""
Task 51, Step 4 outputs from the scorecard parquets (after task51_scorecard.py):
  docs/scorecard/index.html  -- one self-contained page (inline CSS/JS/data, no external requests)
  docs/scorecard/figure_praised.png -- praised-list players present (Task 41's list), Tier 1-2 dimensions, 90% intervals
  docs/scorecard/figure_career.png  -- Card C career lines
Descriptive only. Run: python src/engine_v2/task51_outputs.py
"""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

REPO = Path(__file__).parent.parent.parent
PROC = REPO / "data" / "processed"
OUT_DIR = REPO / "docs" / "scorecard"
SUMMARY = json.loads((REPO / "data" / "engine_v2_task51.json").read_text())
CARD_TITLES = {"A": "Card A — 2015/16 big five (StatsBomb, 185 deep midfielders)",
               "B": "Card B — 360 era, study sample (StatsBomb, 111 deep midfielders)",
               "C": "Card C — career line, La Liga (StatsBomb reserved data, second use; descriptive)"}
TIER_TEXT = {
    "TIER 1": "Stable in deep midfielders, travels with the player between club and country, and linked to team results on untouched data.",
    "TIER 2": "Stable in deep midfielders, but no confirmed link to team results.",
    "TIER 3": "Not reliable enough within deep midfielders to rank them. Shown greyed, with the reason.",
}


def clean(v):
    if isinstance(v, (float, np.floating)):
        return None if np.isnan(v) else round(float(v), 6)
    if isinstance(v, (np.integer,)):
        return int(v)
    return v


def records(df):
    return [{k: clean(v) for k, v in r.items()} for r in df.to_dict("records")]


def page(cards: dict) -> str:
    data = {c: records(df) for c, df in cards.items()}
    meta = {"titles": CARD_TITLES, "tiers": TIER_TEXT,
            "dims": {c: list(dict.fromkeys(cards[c]["dimension"])) for c in ("A", "B")}}
    return TEMPLATE.replace("__DATA__", json.dumps(data)).replace("__META__", json.dumps(meta))


TEMPLATE = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Regista scorecard</title>
<style>
:root{--bg:#fbfaf7;--fg:#1d1d1b;--mute:#6b6a65;--line:#dedbd2;--card:#ffffff;--t1:#1f6f5c;--t2:#2f5d9e;--t3:#9a9890;--band:#cfe3dc;--acc:#b5442b}
@media (prefers-color-scheme:dark){:root{--bg:#161614;--fg:#ecebe6;--mute:#a09e96;--line:#34332f;--card:#1f1f1c;--t1:#5fbfa3;--t2:#7fa8e8;--t3:#77756e;--band:#2b4a41;--acc:#e0765c}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.45 system-ui,-apple-system,"Segoe UI",sans-serif}
main{max-width:1180px;margin:0 auto;padding:24px 16px 64px}h1{font-size:26px;margin:0 0 4px}h2{font-size:19px;margin:28px 0 8px}
.sub{color:var(--mute);margin:0 0 18px}.tabs{display:flex;gap:6px;flex-wrap:wrap;margin:14px 0}
.tabs button{border:1px solid var(--line);background:var(--card);color:var(--fg);padding:7px 12px;border-radius:6px;cursor:pointer;font:inherit}
.tabs button.on{border-color:var(--fg);font-weight:600}.legend{display:grid;gap:8px;margin:10px 0 6px}
.legend div{display:flex;gap:10px;align-items:flex-start}.badge{display:inline-block;font-size:11px;font-weight:700;letter-spacing:.04em;padding:2px 7px;border-radius:4px;color:#fff;white-space:nowrap}
.b1{background:var(--t1)}.b2{background:var(--t2)}.b3{background:var(--t3)}
input[type=search]{width:100%;max-width:360px;padding:8px 10px;border:1px solid var(--line);border-radius:6px;background:var(--card);color:var(--fg);font:inherit;margin:6px 0 10px}
.wrap{overflow-x:auto;border:1px solid var(--line);border-radius:8px;background:var(--card)}
table{border-collapse:collapse;width:100%;font-variant-numeric:tabular-nums}th,td{padding:7px 9px;border-bottom:1px solid var(--line);text-align:right;white-space:nowrap}
th{position:sticky;top:0;background:var(--card);cursor:pointer;font-size:12.5px;user-select:none}th:first-child,td:first-child{text-align:left}
tbody tr{cursor:pointer}tbody tr:hover{background:color-mix(in srgb,var(--band) 45%,transparent)}
.t3{color:var(--t3)}.lab{font-size:11px;color:var(--mute)}.up{color:var(--t1);font-weight:600}.down{color:var(--acc);font-weight:600}
#player{margin-top:18px;border:1px solid var(--line);border-radius:8px;background:var(--card);padding:16px}
.row{display:grid;grid-template-columns:minmax(150px,210px) 1fr minmax(120px,190px);gap:12px;align-items:center;padding:9px 0;border-bottom:1px solid var(--line)}
.row.grey{opacity:.55}.bar{position:relative;height:22px;background:color-mix(in srgb,var(--line) 50%,transparent);border-radius:4px}
.bar .iv{position:absolute;top:5px;height:12px;background:var(--band);border-radius:3px}.bar .pt{position:absolute;top:2px;width:3px;height:18px;background:var(--fg);border-radius:1px}
.bar .mid{position:absolute;left:50%;top:0;bottom:0;width:1px;background:var(--mute);opacity:.6}
.small{font-size:12.5px;color:var(--mute)}.credits{margin-top:14px;font-size:12.5px;color:var(--mute)}
svg text{fill:var(--fg);font-size:11px}@media (max-width:640px){.row{grid-template-columns:1fr}}
</style></head><body><main>
<h1>Regista scorecard</h1>
<p class="sub">Deep midfielders, compared only with deep midfielders in the same card. Each value is shrunk toward the group (Task 29's method) and shown as a percentile with a 90% interval. "Clearly above / below" means the interval excludes the group mean; otherwise "can't tell". Descriptive only: no new measures, no new claims.</p>
<section><h2>What the tiers mean</h2><div class="legend" id="legend"></div></section>
<div class="tabs" id="tabs"></div>
<section id="view"></section>
<section id="player" hidden></section>
</main>
<script>
const DATA=__DATA__, META=__META__;
const esc=s=>String(s??"").replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const tb=t=>`<span class="badge b${t.slice(-1)}">${t}</span>`;
const f=(x,d=0)=>x==null?"—":Number(x).toFixed(d);
document.getElementById("legend").innerHTML=Object.entries(META.tiers).map(([t,s])=>`<div>${tb(t)}<span>${s}</span></div>`).join("");
let current="A",sortKey="name",sortDir=1;
const tabs=document.getElementById("tabs");
["A","B","C"].forEach(c=>{const b=document.createElement("button");b.textContent="Card "+c;b.onclick=()=>show(c);b.id="tab"+c;tabs.appendChild(b)});
function credits(c){return `<p class="credits">Data: StatsBomb (open data).${c==="B"?" Tracking: PFF FC / Gradient Sports WC2022 (availability, AV).":""}</p>`}
function dimHeader(c,d){const r=DATA[c].find(x=>x.dimension===d);return {tier:r.tier,rel:r.reliability,src:r.reliability_source,note:r.note,floor:r.floor}}
function players(c){const m=new Map();for(const r of DATA[c]){if(!m.has(r.player_id))m.set(r.player_id,{player_id:r.player_id,name:r.name,d:{}});m.get(r.player_id).d[r.dimension]=r}return[...m.values()]}
function show(c){current=c;document.querySelectorAll(".tabs button").forEach(b=>b.classList.toggle("on",b.id==="tab"+c));document.getElementById("player").hidden=true;c==="C"?showC():showAB(c)}
function showAB(c){const dims=META.dims[c];
 const head=dims.map(d=>{const h=dimHeader(c,d);return `<th data-k="${d}" class="${h.tier==="TIER 3"?"t3":""}" title="${esc(h.tier+" · reliability "+f(h.rel,3)+" · "+h.src+(h.note?" · "+h.note:""))}">${esc(d)}<br><span class="lab">${h.tier} · rel ${f(h.rel,2)}</span></th>`}).join("");
 document.getElementById("view").innerHTML=`<h2>${esc(META.titles[c])}</h2><p class="small">Cells: percentile within the group (shrunk value). ▲ clearly above, ▼ clearly below, · can't tell, "—" not enough data. Click a column to sort, a row to open the player's card.</p>
 <input type="search" id="q" placeholder="Search players…" aria-label="Search players"><div class="wrap"><table><thead><tr><th data-k="name">Player</th>${head}</tr></thead><tbody id="tb"></tbody></table></div>${credits(c)}`;
 document.querySelectorAll("th").forEach(th=>th.onclick=()=>{const k=th.dataset.k;sortDir=sortKey===k?-sortDir:(k==="name"?1:-1);sortKey=k;fill(c)});
 document.getElementById("q").oninput=()=>fill(c);sortKey="name";sortDir=1;fill(c)}
function cell(r){if(!r||r.label==="not enough data")return `<td class="lab">—</td>`;const mk=r.label==="CLEARLY ABOVE"?`<span class="up">▲</span>`:r.label==="CLEARLY BELOW"?`<span class="down">▼</span>`:`<span class="lab">·</span>`;return `<td class="${r.tier==="TIER 3"?"t3":""}">${f(r.percentile)} ${mk}</td>`}
function fill(c){const q=(document.getElementById("q").value||"").toLowerCase();let ps=players(c).filter(p=>(p.name||"").toLowerCase().includes(q));
 ps.sort((a,b)=>{if(sortKey==="name")return sortDir*String(a.name).localeCompare(String(b.name));const x=a.d[sortKey]?.percentile,y=b.d[sortKey]?.percentile;if(x==null&&y==null)return 0;if(x==null)return 1;if(y==null)return -1;return sortDir*(x-y)});
 const dims=META.dims[c];document.getElementById("tb").innerHTML=ps.map(p=>`<tr data-p="${p.player_id}"><td>${esc(p.name)}</td>${dims.map(d=>cell(p.d[d])).join("")}</tr>`).join("");
 document.querySelectorAll("#tb tr").forEach(tr=>tr.onclick=()=>card(c,Number(tr.dataset.p)))}
function card(c,pid){const p=players(c).find(x=>x.player_id===pid);const el=document.getElementById("player");
 const rows=META.dims[c].map(d=>{const r=p.d[d];const h=dimHeader(c,d);const grey=h.tier==="TIER 3"?" grey":"";
  let bar,txt;if(!r||r.label==="not enough data"){bar=`<div class="bar"><div class="mid"></div></div>`;txt=`not enough data (n = ${r?r.n:0}; floor ${h.floor})`}
  else if(r.label==="NO INTERVAL"){bar=`<div class="bar"><div class="mid"></div><div class="pt" style="left:calc(${r.percentile}% - 1px)"></div></div>`;txt=`percentile ${f(r.percentile)} of raw SD · no interval · n = ${r.n}`}
  else{const lo=r.ci_low_90_pct??0,hi=r.ci_high_90_pct??100;bar=`<div class="bar"><div class="mid"></div><div class="iv" style="left:${lo}%;width:${Math.max(hi-lo,0.8)}%"></div><div class="pt" style="left:calc(${r.percentile}% - 1px)"></div></div>`;txt=`${r.label} · percentile ${f(r.percentile)} [${f(lo)}–${f(hi)}] · n = ${r.n}`}
  return `<div class="row${grey}"><div><b>${esc(d)}</b><br>${tb(h.tier)} <span class="small">rel ${f(h.rel,3)}</span></div>${bar}<div class="small">${esc(txt)}</div></div>
  <div class="small" style="padding:0 0 6px">${esc("Reliability source: "+h.src+(h.note?" · "+h.note:""))}</div>`}).join("");
 const av=c==="B"&&p.d.AV&&p.d.AV.label!=="not enough data";
 el.innerHTML=`<h2>${esc(p.name)}</h2><p class="small">${esc(META.titles[c])}. Bar: percentile of the shrunk value within the group (black tick), 90% interval (band), group middle (thin line).</p>${rows}<p class="credits">Data: StatsBomb (open data).${av?" Tracking: PFF FC / Gradient Sports WC2022.":""}</p>`;
 el.hidden=false;el.scrollIntoView({behavior:"smooth",block:"start"})}
function showC(){const rs=DATA.C;const byP={};rs.forEach(r=>(byP[r.name]??=[]).push(r));
 const all=rs.flatMap(r=>[r.ci_low_90,r.ci_high_90]);const lo=Math.min(...all),hi=Math.max(...all);
 let html=`<h2>${esc(META.titles.C)}</h2><p class="small">Players: deep midfielders with at least 5 La Liga seasons with at least 50 pressured receptions each. Value: raw mean PR2_flag_keep per season with a 90% interval (within-season noise by Task 29's method); not shrunk. ${tb("TIER 1")} reliability ${f(rs[0]?.reliability,3)} (${esc(rs[0]?.reliability_source)}). Number of players meeting the rule: ${Object.keys(byP).length}.</p>`;
 for(const [nm,r] of Object.entries(byP)){r.sort((a,b)=>a.season.localeCompare(b.season));const W=Math.max(640,r.length*60),H=240,pl=48,pr=12,pt=12,pb=40;
  const x=i=>pl+(i+0.5)*(W-pl-pr)/r.length,y=v=>pt+(hi-v)/(hi-lo)*(H-pt-pb);
  const ticks=[lo,(lo+hi)/2,hi].map(v=>`<text x="${pl-6}" y="${y(v)+4}" text-anchor="end">${v.toFixed(2)}</text>`).join("");
  const zero=(lo<0&&hi>0)?`<line x1="${pl}" x2="${W-pr}" y1="${y(0)}" y2="${y(0)}" stroke="currentColor" opacity=".3"/>`:"";
  const marks=r.map((s,i)=>`<line x1="${x(i)}" x2="${x(i)}" y1="${y(s.ci_low_90)}" y2="${y(s.ci_high_90)}" stroke="currentColor" stroke-width="2" opacity=".55"/><circle cx="${x(i)}" cy="${y(s.raw)}" r="4" fill="currentColor"/><text x="${x(i)}" y="${H-pb+16}" text-anchor="middle">${esc(s.season)}</text><text x="${x(i)}" y="${H-pb+30}" text-anchor="middle" opacity=".7">n ${s.n}</text>`).join("");
  const path=r.map((s,i)=>(i?"L":"M")+x(i)+" "+y(s.raw)).join(" ");
  html+=`<h2>${esc(nm)}</h2><div class="wrap" style="color:var(--fg)"><svg viewBox="0 0 ${W} ${H}" width="100%" role="img" aria-label="${esc(nm)} PR2_flag_keep per season">${ticks}${zero}<path d="${path}" fill="none" stroke="currentColor" opacity=".35"/>${marks}</svg></div>
  <div class="wrap" style="margin-top:8px"><table><thead><tr><th>Season</th><th>pressured receptions</th><th>matches</th><th>PR2_flag_keep</th><th>90% interval</th></tr></thead><tbody>${r.map(s=>`<tr><td>${esc(s.season)}</td><td>${s.n}</td><td>${s.n_matches}</td><td>${f(s.raw,4)}</td><td>[${f(s.ci_low_90,4)}, ${f(s.ci_high_90,4)}]</td></tr>`).join("")}</tbody></table></div>`}
 document.getElementById("view").innerHTML=html+credits("C")}
show("A");
</script></body></html>
"""


def fig_praised(cards: dict, summary: dict):
    panels = []
    for c in ("A", "B"):
        df = cards[c]
        ids = sorted({p for hits in summary[c]["praised"].values() for p in hits})
        dims = [d for d in dict.fromkeys(df["dimension"]) if df.loc[df["dimension"] == d, "tier"].iloc[0] in ("TIER 1", "TIER 2")]
        panels.append((c, ids, dims, df))
    ncols = max(len(p[2]) for p in panels)
    fig, axes = plt.subplots(2, ncols, figsize=(3.1 * ncols, 7.6), squeeze=False)
    for row, (c, ids, dims, df) in enumerate(panels):
        names = {p: df.loc[df["player_id"] == p, "name"].iloc[0] for p in ids}
        order = sorted(ids, key=lambda p: names[p])
        for j in range(ncols):
            ax = axes[row][j]
            if j >= len(dims):
                ax.axis("off")
                continue
            d = dims[j]
            sub = df[df["dimension"] == d].set_index("player_id")
            elig = sub[sub["label"] != "not enough data"]
            val = "shrunken" if d != "HOLD_VARIATION" else "raw"
            med = float(elig[val].median())
            ax.axvline(med, color="0.55", lw=1, ls="--")
            for i, p in enumerate(order):
                r = sub.loc[p]
                if r["label"] == "not enough data":
                    ax.text(med, i, "not enough data", va="center", ha="center", fontsize=7, color="0.5")
                    continue
                if pd.notna(r["ci_low_90"]):
                    ax.plot([r["ci_low_90"], r["ci_high_90"]], [i, i], color="#1f6f5c" if r["tier"] == "TIER 1" else "#2f5d9e", lw=2)
                ax.plot(r[val], i, "o", color="black", ms=4)
            ax.set_yticks(range(len(order)))
            ax.set_yticklabels([names[p] for p in order] if j == 0 else [], fontsize=8)
            ax.set_ylim(len(order) - 0.4, -0.6)
            tier = sub["tier"].iloc[0]
            ax.set_title(f"{d}\n{tier}, rel {sub['reliability'].iloc[0]:.2f}" + (" (raw SD, no interval)" if d == "HOLD_VARIATION" else ""),
                         fontsize=8.5)
            ax.tick_params(axis="x", labelsize=7)
        axes[row][0].set_ylabel(f"Card {c}: praised-list players present ({len(ids)})", fontsize=9)
    fig.suptitle("Praised-list deep midfielders (Task 41's fixed list), Tier 1-2 dimensions: shrunk value (dot), 90% interval (bar), "
                 "group median (dashed)\nData: StatsBomb (open data). Tracking: PFF FC / Gradient Sports WC2022 (AV).", fontsize=9)
    fig.tight_layout(rect=[0, 0, 1, 0.94])
    fig.savefig(OUT_DIR / "figure_praised.png", dpi=150)
    plt.close(fig)


def fig_career(C: pd.DataFrame):
    players_ = list(dict.fromkeys(C["name"]))
    fig, axes = plt.subplots(len(players_), 1, figsize=(10, 3.6 * max(len(players_), 1)), squeeze=False)
    for ax, nm in zip(axes[:, 0], players_):
        s = C[C["name"] == nm].sort_values("season")
        x = np.arange(len(s))
        ax.errorbar(x, s["raw"], yerr=[s["raw"] - s["ci_low_90"], s["ci_high_90"] - s["raw"]], fmt="o-", color="#1f6f5c",
                    ecolor="0.45", capsize=3, lw=1)
        ax.axhline(0, color="0.7", lw=0.8)
        ax.set_xticks(x)
        ax.set_xticklabels([f"{a}\nn={b}" for a, b in zip(s["season"], s["n"])], fontsize=7.5)
        ax.set_ylabel("PR2_flag_keep (raw mean)", fontsize=9)
        ax.set_title(f"{nm}: La Liga seasons with >= 50 pressured receptions; 90% interval (within-season noise, Task 29); TIER 1", fontsize=9)
    fig.suptitle("Card C, career line (reserved data, second use; descriptive). Data: StatsBomb (open data).", fontsize=9.5)
    fig.tight_layout(rect=[0, 0, 1, 0.95])
    fig.savefig(OUT_DIR / "figure_career.png", dpi=150)
    plt.close(fig)


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    cards = {c: pd.read_parquet(PROC / f"scorecard_card_{c.lower()}.parquet") for c in ("A", "B", "C")}
    (OUT_DIR / "index.html").write_text(page(cards))
    fig_praised(cards, SUMMARY["summary"])
    fig_career(cards["C"])
    print(f"Wrote {OUT_DIR / 'index.html'}, figure_praised.png, figure_career.png")


if __name__ == "__main__":
    main()
