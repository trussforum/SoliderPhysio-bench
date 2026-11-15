"""Write representative transcripts (prompt, raw answer, code grade, judge marks) to transcripts/.

Picks real saved cases from the published board (BOARD: every case re-judged by GLM-5.3
Prime on 2026-11-15): at least one failure per task plus successes. The 2003-card example
comes from the closed-book 2026-11-07 run (OLD_BOARD, Sol Pro judge), the only run where
the chart was not in the prompt. No API calls.

    python scripts/extract_transcripts.py [BOARD_JSON] [OUT_DIR]
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BOARD = Path(sys.argv[1] if len(sys.argv) > 1 else ROOT / ".benchmark-runs/rejudge-glm-20261115/final-leaderboard.json")
OLD_BOARD = ROOT / ".benchmark-runs/rerun-20261107/final-leaderboard.json"
OUT = Path(sys.argv[2] if len(sys.argv) > 2 else ROOT / "transcripts")
OUT.mkdir(exist_ok=True)
lb = json.loads(Path(BOARD).read_text())["leaderboard"]
old_lb = json.loads(OLD_BOARD.read_text())["leaderboard"]
fix = lambda p: ROOT / p  # board paths are repo-relative


def load(r, c):
    sub = next(x for x in json.loads(fix(c["submission"]).read_text())["cases"] if x["case_id"] == c["case_id"])
    jud = next(x for x in json.loads(fix(c["judged"]).read_text())["cases"] if x["case_id"] == c["case_id"])
    return sub, jud


def find(pred, prefer=(), board=None):
    order = sorted(board or lb, key=lambda r: (r["display"] not in prefer, -r["overall_100"]))
    for r in order:
        for c in r["cases"]:
            if c.get("judge_status") != "scored":
                continue
            sub, jud = load(r, c)
            if pred(c, sub):
                return r, c, sub, jud
    raise LookupError


rb = lambda s: (s.get("grader") or {}).get("rulebook") or {}
PICKS = [
    ("rulebook-2003-card", "Rulebook, closed-book run (no chart in prompt, Sol Pro judge): recites the superseded 2003 card (40/20)",
     lambda c, s: c["task"] == "rulebook_vs_body" and rb(s).get("parsed", {}).get("work_rest_min") == "40/20",
     ("Sonnet 5.5", "Opus 5"), old_lb),
    ("rulebook-correct-NL", "Rulebook (chart in prompt): reads the 2022 card cell correctly (NL)",
     lambda c, s: c["task"] == "rulebook_vs_body" and rb(s).get("parsed", {}).get("work_rest_min") == "NL", ()),
    ("keep-pull-false-pull", "Keep/Pull: needless pull of a soldier who stayed below 38.5 C",
     lambda c, s: c["task"] == "keep_going" and (s.get("grader") or {}).get("error_type") == "false_pull",
     ("Sonnet 5.5",)),
    ("keep-pull-missed-pull", "Keep/Pull: missed pull, soldier crossed 38.5 C (dangerous direction)",
     lambda c, s: c["task"] == "keep_going" and (s.get("grader") or {}).get("error_type") == "missed_pull",
     ("GPT-6 Astra",)),
    ("keep-pull-thermal-lag-caught", "Keep/Pull: thermal lag caught (near miss turned success)",
     lambda c, s: c["task"] == "keep_going" and (s.get("grader") or {}).get("design") == "falling_power_thermal_lag"
     and (s.get("grader") or {}).get("decision_correct"), ("Hy4",)),
    ("beat-ectemp-worse-than-baseline", "Beat ECTemp: predictor no better than the baseline (predictor score 0)",
     lambda c, s: c["task"] == "beat_ectemp" and c["components"].get("predictor") == 0.0, ("GPT-6 Astra",)),
    ("beat-ectemp-beats-baseline", "Beat ECTemp: predictor clearly beats the baseline",
     lambda c, s: c["task"] == "beat_ectemp" and c["components"].get("predictor", 0) > 0.6, ("Muse Wonder 1.0",)),
]
index = ["# Representative transcripts", "",
         "Real saved cases from the published board, one file each: prompt, raw model answer, "
         "deterministic grade and judge marks (GLM-5.3 Prime, except the closed-book 2003-card example). "
         "Each file names its source under `results/`. Regenerate with `python scripts/extract_transcripts.py`.", "",
         "| File | What it shows | Model | Case |", "|---|---|---|---|"]
def render(title, r, c, sub, jud):
    prompt = (sub.get("materials") or {}).get("prompt")
    body = [f"# {title}", "", f"- **Model:** {r['display']} (`{r['model']}`)",
            f"- **Case:** `{c['task']}/{c['case_id']}` · finish reason `{sub.get('finish_reason')}`",
            f"- **Combined score:** {c['combined']:.3f} · components {json.dumps(c['components'])}",
            f"- **Source:** `{Path(c['submission']).as_posix().replace('.benchmark-runs', 'results')}`", ""]
    if prompt:
        body += ["## Prompt (exactly as sent)", "", "```text", prompt.strip(), "```", ""]
    else:
        body += ["## Prompt", "", "Agentic research session; task spec in `tasks/beat_ectemp/README.md`.", ""]
    body += ["## Model answer (raw)", "", "```text", (sub.get("answer") or "(empty)").strip()[:12000], "```", "",
             "## Deterministic grade", "", "```json", json.dumps(sub.get("grader"), indent=2)[:6000], "```", "",
             "## LLM judge marks", "", "```json", json.dumps(jud.get("judge"), indent=2), "```", ""]
    return "\n".join(body)


for slug, title, pred, prefer, *board in PICKS:
    r, c, sub, jud = find(pred, prefer, *board)
    (OUT / f"{slug}.md").write_text(render(title, r, c, sub, jud))
    index.append(f"| [{slug}.md]({slug}.md) | {title} | {r['display']} | `{c['case_id']}` |")
    print("wrote", slug, r["display"], c["case_id"])

# One transcript per roster model: its worst scored single-turn case (a failure, or the weakest answer).
BYM = OUT / "by-model"
BYM.mkdir(exist_ok=True)
index += ["", "## One transcript per model", "",
          "Each model's lowest-scoring answered single-turn case (Keep/Pull or Rulebook), so every "
          "reported model has a failure on file. Beat ECTemp failures are above.", "",
          "| Model | Case | Combined | Transcript |", "|---|---|---:|---|"]
for r in sorted(lb, key=lambda r: r["rank"] if "rank" in r else -r["overall_100"]):
    cands = [c for c in r["cases"] if c.get("judge_status") == "scored" and c["task"] in ("keep_going", "rulebook_vs_body")]
    if not cands:
        print("NO scored single-turn case:", r["display"])
        continue
    c = min(cands, key=lambda c: c["combined"])
    sub, jud = load(r, c)
    slug = "".join(ch if ch.isalnum() else "-" for ch in r["display"].lower()).strip("-")
    title = f"{r['display']}: weakest single-turn answer ({c['task']}/{c['case_id']})"
    (BYM / f"{slug}.md").write_text(render(title, r, c, sub, jud))
    index.append(f"| {r['display']} | `{c['case_id']}` | {c['combined']:.3f} | [by-model/{slug}.md](by-model/{slug}.md) |")
    print("wrote by-model", slug, c["case_id"])
(OUT / "README.md").write_text("\n".join(index) + "\n")
