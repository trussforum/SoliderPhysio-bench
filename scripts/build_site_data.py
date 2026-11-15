"""Build site/lib/soldier.json and refresh public traces from the saved roster run.

    python scripts/build_site_data.py [RUN_DIR [RULEBOOK_RUN_DIR]]

Keep/Pull and Beat ECTemp come from RUN_DIR (the 2026-11-07/08 roster run).
The Rulebook task comes from RULEBOOK_RUN_DIR (the 2026-11-14 open-book rerun).
GPT-6.1 Sol's run is SOL_RUN (2026-11-15). The leaderboard the site shows is
JUDGE_RUN/final-leaderboard.json (scripts/rejudge_off_roster.py): every case
re-judged by GLM-5.3 Prime. Judge cost is that re-judge only; the retired Sol Pro
judge's spend is reported separately. No API calls.
"""
from __future__ import annotations

import collections
import glob
import json
import sqlite3
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# Every judge used so far; spend under these ids is judge cost, not model cost.
JUDGE_MODELS = {"openai/gpt-6.1-sol-pro", "z-ai/glm-5.3-prime"}
SITE = ROOT / "site"
RUN = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / ".benchmark-runs/rerun-20261107"
RB_RUN = Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / ".benchmark-runs/rulebook-open-20261114"
SOL_RUN = ROOT / ".benchmark-runs/sol-20261115"
JUDGE_RUN = ROOT / ".benchmark-runs/rejudge-glm-20261115"
LB_PATH = JUDGE_RUN / "final-leaderboard.json"
AUDIT_PATH = RUN / "control/completion-audit.json"

KEEP_LABELS = {
    "falling_power_thermal_lag": "Slowed down, core still rising",
    "steady_power_rising": "Steady work, core rising",
    "falling_power_safe": "Slowed down, actually safe",
    "steady_power_safe": "Steady work, actually safe",
}

RB_LABELS = {
    "40/20 (2003 card)": "40/20 (2003 card)",
    "other value": "Other value",
    "no answer": "No answer",
    "NL (correct, 2022)": "NL (2022 card, correct)",
}


def provider_slug(openrouter_id: str) -> str:
    return openrouter_id.split("/")[0]


def task_of_prompt(body: str) -> str:
    if "TB MED" in body:
        return "rulebook"
    if "predict" in body and "submission" in body:
        return "research"
    if "stationary bike" in body:
        return "keep_going"
    return "other"


def load_task_spend() -> tuple[dict[str, float], dict[str, collections.Counter], float, float]:
    """Keep/Pull and research spend from RUN, rulebook spend from RB_RUN, Sol's from SOL_RUN.

    Returns (model totals, per-task spend, judge spend for the shown board, retired judge spend)."""
    old, old_judge = run_task_spend(RUN)
    new, new_judge = run_task_spend(RB_RUN)
    sol, _ = run_task_spend(SOL_RUN)
    _, judge_usd = run_task_spend(JUDGE_RUN)
    per_model: dict[str, collections.Counter] = collections.defaultdict(collections.Counter)
    for model, c in old.items():
        per_model[model].update({k: v for k, v in c.items() if k != "rulebook"})
    for model, c in new.items():
        per_model[model]["rulebook"] += c.get("rulebook", 0)
    for model, c in sol.items():
        per_model[model].update(c)
    totals = {m: sum(c.values()) for m, c in per_model.items()}
    return totals, per_model, judge_usd, old_judge + new_judge


def run_task_spend(run: Path) -> tuple[dict[str, collections.Counter], float]:
    reservation_to_task: dict[str, str] = {}
    for db in glob.glob(str(run / "**/controller.sqlite"), recursive=True):
        try:
            rows = sqlite3.connect(db).execute("select payload from transcript").fetchall()
        except sqlite3.Error:
            continue
        for (payload,) in rows:
            rec = json.loads(payload)
            if rec.get("kind") != "model_request":
                continue
            res = rec.get("data", {}).get("reservation")
            if not res:
                continue
            body = json.dumps(rec["data"].get("body", ""))
            reservation_to_task[res] = task_of_prompt(body)

    per_model: dict[str, collections.Counter] = collections.defaultdict(collections.Counter)
    judge_usd = 0.0
    for db in glob.glob(str(run / "**/spend.sqlite"), recursive=True):
        try:
            rows = sqlite3.connect(db).execute(
                "select id, model, charged_nano, accounting from charges"
            ).fetchall()
        except sqlite3.Error:
            continue
        for cid, model, nano, accounting in rows:
            if accounting != "provider_reported" or not nano:
                continue
            usd = nano / 1e9
            if model in JUDGE_MODELS:
                judge_usd += usd
                continue
            task = reservation_to_task.get(cid, "other")
            per_model[model][task] += usd
    return per_model, judge_usd


def aggregate_charts(lb_doc: dict) -> tuple[dict[str, int], list[dict]]:
    """Count chart buckets from exactly the judged cases the leaderboard scores."""
    wr: collections.Counter = collections.Counter()
    kg: collections.Counter = collections.Counter()
    cache: dict[str, dict] = {}
    for row in lb_doc["leaderboard"]:
        for ref in row["cases"]:
            cid = ref["case_id"]
            if not (cid.startswith("RB") or cid.startswith("KG")):
                continue
            if ref["judged"] not in cache:
                cache[ref["judged"]] = json.loads((ROOT / ref["judged"]).read_text())
            case = next(c for c in cache[ref["judged"]]["cases"] if c["case_id"] == cid)
            grader = case.get("grader") or {}
            if cid.startswith("RB"):
                got = str(((grader.get("rulebook") or {}).get("parsed") or {}).get("work_rest_min"))
                if got == "40/20":
                    bucket = "40/20 (2003 card)"
                elif got == "NL":
                    bucket = "NL (correct, 2022)"
                elif got == "None":
                    bucket = "no answer"
                else:
                    bucket = "other value"
                wr[bucket] += 1
            if cid.startswith("KG") and "design" in grader:
                design = grader["design"]
                et = grader.get("error_type")
                if et is None and grader.get("decision_correct"):
                    outcome = "correct"
                else:
                    outcome = et or "correct"
                kg[(design, outcome)] += 1

    rulebook = {RB_LABELS[k]: wr[k] for k in RB_LABELS if wr[k]}
    keep_pull = []
    for design, label in KEEP_LABELS.items():
        keep_pull.append({
            "design": label,
            "correct": kg[(design, "correct")],
            "false_pull": kg[(design, "false_pull")],
            "missed": kg[(design, "missed_pull")],
        })
    return rulebook, keep_pull


def build_soldier() -> dict:
    lb_doc = json.loads(LB_PATH.read_text())
    audit = json.loads(AUDIT_PATH.read_text())
    roster = {r["openrouter_id"]: r for r in json.loads((ROOT / "eval_suite/roster.json").read_text())["models"] if r.get("openrouter_id")}

    totals, per_task, judge_usd, retired_judge_usd = load_task_spend()
    rulebook, keep_pull = aggregate_charts(lb_doc)

    models = []
    for row in lb_doc["leaderboard"]:
        mid = row["model"]
        raw = row["raw"]
        roster_row = roster.get(mid, {})
        costs = per_task.get(mid, collections.Counter())
        cost = round(totals.get(mid, row.get("accounted_usd_inventory") or 0.0), 2)
        models.append({
            "rank": row["rank"],
            "id": mid,
            "name": row["display"],
            "provider": provider_slug(mid),
            "effort": roster_row.get("effort", "max"),
            "overall": round(row["overall_100"], 1),
            "keep": round(row["task_scores_100"]["keep_going"], 1),
            "rulebook": round(row["task_scores_100"]["rulebook_vs_body"], 1),
            "research": round(row["task_scores_100"]["beat_ectemp"], 1),
            "cost": cost,
            "cost_tasks": {
                "keep_going": round(costs.get("keep_going", 0), 2),
                "rulebook": round(costs.get("rulebook", 0), 2),
                "research": round(costs.get("research", 0), 2),
            },
            "calls": raw["keep_going"]["correct"],
            "cells": raw["rulebook_vs_body"]["lookup_fields_correct"],
            "overrides": raw["rulebook_vs_body"]["override_correct"],
            "beat": raw["beat_ectemp"]["people_beating_baseline"],
            "mae": round(raw["keep_going"]["mae_c"] or 0, 3),
        })

    research_usd = sum(c.get("research", 0) for c in per_task.values())
    single_usd = sum(c.get("keep_going", 0) + c.get("rulebook", 0) for c in per_task.values())
    model_usd = sum(totals.values())

    return {
        "run": "2026-11-07/08; rulebook rerun open-book 2026-11-14; GPT-6.1 Sol added and all cases re-judged 2026-11-15",
        "judge": lb_doc["judge_model"],
        "previous_judge": lb_doc.get("previous_judge_model"),
        "total_usd": round(model_usd + judge_usd, 2),
        "judge_usd": round(judge_usd, 2),
        "retired_judge_usd": round(retired_judge_usd, 2),
        "judgments": lb_doc.get("judgments"),
        "rulebook": rulebook,
        "keep_pull": keep_pull,
        "models": models,
        "model_usd": round(model_usd, 2),
        "research_usd": round(research_usd, 2),
        "single_turn_usd": round(single_usd, 2),
    }


def main() -> int:
    if not LB_PATH.exists():
        sys.exit(f"missing {LB_PATH}; run: python scripts/rejudge_off_roster.py board")
    if not AUDIT_PATH.exists():
        sys.exit(f"missing {AUDIT_PATH}")

    SITE.mkdir(parents=True, exist_ok=True)
    (SITE / "lib").mkdir(parents=True, exist_ok=True)
    soldier = build_soldier()
    out = SITE / "lib/soldier.json"
    out.write_text(json.dumps(soldier, indent=1) + "\n")
    print(f"wrote {out.relative_to(ROOT)} ({len(soldier['models'])} models)")

    traces_dir = SITE / "public/traces"
    traces_dir.mkdir(parents=True, exist_ok=True)
    for stale in ("index.html", "index.txt"):
        p = traces_dir / stale
        if p.exists():
            p.unlink()

    export = ROOT / "scripts/export_web_traces.py"
    cases = traces_dir / "cases.json"
    subprocess.run([sys.executable, str(export), str(cases), str(LB_PATH)], check=True, cwd=ROOT)
    print(f"wrote {cases.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())