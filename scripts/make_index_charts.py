"""Index-style graphics (Truss brand: paper, slate ink, amber, EB Garamond) for the current board.

    python scripts/build_site_data.py          # first: writes site/lib/soldier.json
    python scripts/make_index_charts.py [SOLDIER_JSON] [OUT_DIR]

Reads the same site/lib/soldier.json the results site shows (re-judged board, per-task
cost from spend ledgers), so README figures and site always agree. Writes index_vs_cost.png,
cost_by_task.png, keep_pull.png, task_scores.html (+ .png if Chrome is found). No API calls.
"""
import collections
import html
import json
import shutil
import subprocess
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

SOLDIER = Path(sys.argv[1] if len(sys.argv) > 1 else "site/lib/soldier.json")
OUT = Path(sys.argv[2] if len(sys.argv) > 2 else "docs/figures")
OUT.mkdir(parents=True, exist_ok=True)

# Truss brand (truss.signalor.app): paper, slate ink, amber accent, EB Garamond
BG, INK, MUTED, GRID, HEAD, RULE = "#FAFAF8", "#0F172A", "#57534E", "#E7E5E4", "#914400", "#E7E5E4"
PROVIDER = {  # (name, colour) - muted editorial set anchored on ink + amber
    "anthropic": ("Anthropic", "#B45309"), "openai": ("OpenAI", "#0F172A"),
    "google": ("Google", "#5F7A3A"), "meta": ("Meta", "#3B5B8C"),
    "moonshotai": ("Moonshot AI", "#7C5A8C"), "x-ai": ("xAI", "#A8A29E"),
    "tencent": ("Tencent", "#0E7490"), "deepseek": ("DeepSeek", "#64748B"),
}
TASKS = [("keep_going", "Keep / Pull", "#0F172A"), ("rulebook", "Rulebook", "#B45309"),
         ("research", "Beat ECTemp", "#D6D3D1")]
for f in (Path(__file__).resolve().parent.parent / "docs" / "fonts").glob("EBGaramond*.ttf"):
    font_manager.fontManager.addfont(str(f))
mono = "EB Garamond"  # labels use the brand serif
plt.rcParams.update({
    "figure.facecolor": BG, "axes.facecolor": BG, "savefig.facecolor": BG, "text.color": INK,
    "axes.labelcolor": MUTED, "xtick.color": MUTED, "ytick.color": INK, "axes.edgecolor": INK,
    "axes.linewidth": 0.8, "font.size": 14, "axes.spines.top": False, "axes.spines.right": False,
    "font.family": ["EB Garamond", "Georgia", "DejaVu Serif"],
})

S = json.loads(SOLDIER.read_text())
prov = lambda mid: PROVIDER[mid.split("/")[0]]
lb = [{"model": m["id"], "display": m["name"], "overall_100": m["overall"],
       "task_scores_100": {"keep_going": m["keep"], "rulebook_vs_body": m["rulebook"], "beat_ectemp": m["research"]},
       "raw": {"keep_going": {"correct": m["calls"]}, "rulebook_vs_body": {"lookup_fields_correct": m["cells"]}}}
      for m in S["models"]]
cost = {m["id"]: collections.Counter(m["cost_tasks"]) for m in S["models"]}
total = {m["id"]: m["cost"] for m in S["models"]}
N = len(lb)


def header(fig, text, sub=None):
    fig.text(0.02, 0.965, " ".join(text), family=mono, fontsize=15, color=HEAD, va="top")
    if sub:
        fig.text(0.98, 0.965, sub, family=mono, fontsize=12, color=MUTED, va="top", ha="right")


def save(fig, fn):
    fig.savefig(OUT / fn, dpi=200, bbox_inches="tight", pad_inches=0.35)
    plt.close(fig)
    print("wrote", OUT / fn)


# 1. Index vs cost, provider-coloured
fig, ax = plt.subplots(figsize=(13, 7.2))
fig.subplots_adjust(top=0.88, bottom=0.2)
header(fig, "SOLDIERPHYSIO INDEX", f"{N} MODELS · 21 CASES · JUDGE {S['judge'].upper()}")
by_p = collections.defaultdict(list)
for r in lb:
    by_p[r["model"].split("/")[0]].append((total[r["model"]], r["overall_100"], r["display"]))
OFFS = {"Muse Wonder 1.0": (8, -16), "Gemini 3.8 Flash": (0, -20), "Kimi K3.1 Pro": (0, 11),
        "Grok 4.6": (8, 6), "Opus 5": (8, -15), "Fable 5": (-8, 10), "Opus 5.5": (8, -15),
        "GPT-6.1 Terra": (0, 11), "Hy4": (0, 11), "Gemini 4 Argon": (8, -15), "Fable 5.1": (-8, 10),
        "GPT-6 Astra": (0, 11), "Sonnet 5.5": (-10, 0), "DeepSeek-V4.1-Flash-1017": (8, -15),
        "GPT-6.1 Sol": (8, -15)}
for p, pts in by_p.items():
    name, col = PROVIDER[p]
    pts.sort()
    for x, y, lab in pts:
        ax.scatter(x, y, s=95, color=col, edgecolor=BG, lw=1.6, zorder=3)
        dx, dy = OFFS.get(lab, (8, 8))
        ha = "right" if dx < 0 else "center" if dx == 0 else "left"
        ax.annotate(lab.replace("DeepSeek-V4.1-Flash-1017", "DeepSeek V4.1 Flash"), (x, y),
                    xytext=(dx, dy), textcoords="offset points", ha=ha, va="center",
                    family=mono, fontsize=13, color=col if p != "x-ai" else "#78716C")
ax.set_xscale("log")
ax.set_xlim(0.2, 45)
lo, hi = min(r["overall_100"] for r in lb), max(r["overall_100"] for r in lb)
ax.set_ylim(5 * int(lo // 5) - 5, 5 * int(hi // 5) + 10)
ax.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"${v:g}"))
ax.grid(True, color=GRID, lw=0.9)
ax.set_axisbelow(True)
ax.set_xlabel("Provider-reported cost to answer all 21 cases (USD, log scale)", labelpad=10)
ax.set_ylabel("SoldierPhysio index (/100)")
handles = [plt.Line2D([], [], marker="s", ls="", ms=11, color=c, label=n) for n, c in PROVIDER.values()]
fig.legend(handles=handles, loc="lower center", ncol=8, frameon=False, fontsize=14,
           bbox_to_anchor=(0.5, 0.03), handletextpad=0.3, columnspacing=1.4)
save(fig, "index_vs_cost.png")

# 2. Cost by task, all models, stacked
rows = sorted(lb, key=lambda r: total[r["model"]])
fig, ax = plt.subplots(figsize=(12, 7.6))
fig.subplots_adjust(top=0.9, bottom=0.16)
header(fig, "COST BY TASK", f"TOTAL \\${S['total_usd']:.2f} INCL. JUDGE \\${S['judge_usd']:.2f}")
for y, r in enumerate(rows):
    left = 0
    for key, _, col in TASKS:
        v = cost[r["model"]][key]
        ax.barh(y, v, left=left, color=col, height=0.62, edgecolor=BG, lw=1.2)
        left += v
    ax.text(left + 0.35, y, f"${left:,.2f}", va="center", family=mono, fontsize=13, color=INK)
ax.set_yticks(range(len(rows)), [r["display"].replace("DeepSeek-V4.1-Flash-1017", "DeepSeek V4.1 Flash")
                                 for r in rows])
ax.tick_params(axis="y", length=0)
ax.xaxis.grid(True, color=GRID, lw=0.9)
ax.set_axisbelow(True)
ax.set_xlim(0, 35)
ax.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"${v:g}"))
ax.set_xlabel("Cost (USD)")
fig.legend(handles=[plt.Line2D([], [], marker="s", ls="", ms=11, color=c, label=n) for _, n, c in TASKS],
           loc="lower center", ncol=3, frameon=False, fontsize=14, bbox_to_anchor=(0.5, 0.02))
save(fig, "cost_by_task.png")

# 3. Keep/Pull by case design (deterministic grades on the board's cases)
kp = S["keep_pull"]
fig, ax = plt.subplots(figsize=(11, 5.6))
fig.subplots_adjust(top=0.86)
n_ans = 12 * N  # every Keep/Pull answer, including unparsed ones outside the four buckets
n_ok = sum(m["calls"] for m in S["models"])
header(fig, "KEEP OR PULL", f"{n_ok}/{n_ans} RIGHT ({100 * n_ok / n_ans:.0f}%) · {N} MODELS")
x = range(len(kp))
c_, fp, mp = [d["correct"] for d in kp], [d["false_pull"] for d in kp], [d["missed"] for d in kp]
ax.bar(x, c_, color=INK, width=0.6, label="correct call", edgecolor=BG, lw=2)
ax.bar(x, fp, bottom=c_, color="#D6D3D1", width=0.6, label="needless pull", edgecolor=BG, lw=2)
ax.bar(x, mp, bottom=[a + b for a, b in zip(c_, fp)], color=HEAD, width=0.6, label="missed pull (dangerous)",
       edgecolor=BG, lw=2)
for i in x:
    for base, v, fg in ((0, c_[i], BG), (c_[i], fp[i], INK), (c_[i] + fp[i], mp[i], BG)):
        if v >= 4:
            ax.text(i, base + v / 2, str(v), ha="center", va="center", color=fg, fontsize=16)
ax.set_xticks(list(x), [d["design"].replace(", ", ",\n") for d in kp])
ax.tick_params(axis="x", length=0)
ax.set_ylabel("model answers")
ax.set_ylim(0, max(a + b + c for a, b, c in zip(c_, fp, mp)) * 1.18)
ax.yaxis.grid(True, color=GRID, lw=0.9)
ax.set_axisbelow(True)
ax.legend(frameon=False, loc="upper center", ncol=3, fontsize=14, bbox_to_anchor=(0.5, 1.02))
save(fig, "keep_pull.png")

# 4. Task scores table (HTML -> PNG)
cols = [("INDEX", lambda r: r["overall_100"] / 100, "{:.3f}"),
        ("KEEP/PULL", lambda r: r["task_scores_100"]["keep_going"] / 100, "{:.2f}"),
        ("RULEBOOK", lambda r: r["task_scores_100"]["rulebook_vs_body"] / 100, "{:.2f}"),
        ("RESEARCH", lambda r: r["task_scores_100"]["beat_ectemp"] / 100, "{:.2f}"),
        ("CALLS RIGHT", lambda r: r["raw"]["keep_going"]["correct"], "{}/12"),
        ("CARD CELLS", lambda r: r["raw"]["rulebook_vs_body"]["lookup_fields_correct"], "{}/8"),
        ("COST", lambda r: total[r["model"]], "${:.2f}")]
best = {c: max(f(r) for r in lb) for c, f, _ in cols if c != "COST"}
best["COST"] = min(total[r["model"]] for r in lb)
trs = []
for r in sorted(lb, key=lambda r: -r["overall_100"]):
    name, col = prov(r["model"])
    cells = "".join(
        f'<td class="{"b" if abs(f(r) - best[c]) < 1e-9 else ""}{" idx" if c == "INDEX" else ""}">{fmt.format(f(r))}</td>'
        for c, f, fmt in cols)
    disp = r["display"].replace("DeepSeek-V4.1-Flash-1017", "DeepSeek V4.1 Flash")
    trs.append(f'<tr><td class="sw"><i style="background:{col}"></i></td><td class="m">{html.escape(disp)}'
               f'<span>{name} · {html.escape(r["model"])}</span></td>{cells}</tr>')
head = "".join(f'<th{" class=idx" if c == "INDEX" else ""}>{c}</th>' for c, _, _ in cols)
best_row = (
            '<td class="idx">1.000</td><td>1.00</td><td>1.00</td><td>1.00</td><td>12/12</td><td>8/8</td><td></td></tr>')
page = f"""<!doctype html><meta charset=utf-8>
<link href="https://fonts.googleapis.com/css2?family=EB+Garamond:ital,wght@0,400;0,500;1,400&display=swap" rel="stylesheet">
<style>
body{{background:{BG};color:{INK};font:18px/1.5 'EB Garamond',Georgia,serif;margin:0;padding:40px 44px;width:1180px;-webkit-font-smoothing:antialiased}}
.k{{font-size:18px;color:{INK};letter-spacing:.12em;text-transform:uppercase;margin-bottom:18px}}
table{{border-collapse:collapse;width:100%;font-variant-numeric:tabular-nums lining-nums}}
th{{font-size:13px;letter-spacing:.1em;color:{HEAD};text-align:right;padding:10px 14px;border-bottom:1px solid {INK};font-weight:400}}
td{{font-size:18px;text-align:right;padding:10px 14px;border-bottom:1px solid {RULE}}}
td.m{{font-size:19px;text-align:left;color:{INK}}}
td.m span{{display:block;font-size:13px;font-style:italic;color:{MUTED};margin-top:1px}}
td.sw{{width:14px;padding-right:0;color:#A8A29E}} td.sw i{{display:inline-block;width:10px;height:10px;border-radius:50%}}
.idx{{border-right:1px solid {RULE}}} td.b{{font-weight:500;color:{HEAD}}}
tr.ref td{{color:{MUTED};font-style:italic}}
.n{{font-size:15px;font-style:italic;color:{MUTED};margin-top:16px}}
</style><div class=k>Task scores</div><table><tr><th></th><th style="text-align:left"></th>{head}</tr>{best_row}{''.join(trs)}</table>
<div class=n>Index = mean of the three task scores (0–1). Amber = best in column. Cost = provider-reported USD for all 21 cases.
Judge: {html.escape(S['judge'])} (no model from its lab is rated).</div>"""
(OUT / "task_scores.html").write_text(page)
chrome = shutil.which("google-chrome") or "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
if Path(chrome).exists():
    prof = Path("/tmp/spb-chrome-profile")
    subprocess.run([chrome, "--headless=new", f"--user-data-dir={prof}", "--hide-scrollbars",
                    "--force-device-scale-factor=2", "--window-size=1260,1420", "--virtual-time-budget=8000",
                    f"--screenshot={(OUT / 'task_scores.png').resolve()}", (OUT / "task_scores.html").resolve().as_uri()],
                   capture_output=True, timeout=60)
    shutil.rmtree(prof, ignore_errors=True)
    print("wrote", OUT / "task_scores.png")
