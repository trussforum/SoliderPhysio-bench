"""Swap the open-book Rulebook rerun into the 2026-11-07 leaderboard.

    python scripts/merge_open_book_rulebook.py [NEW_RUN_DIR]

Keep/Pull and Beat ECTemp cases come unchanged from
.benchmark-runs/rerun-20261107/final-leaderboard.json. Rulebook cases come from
NEW_RUN_DIR (default .benchmark-runs/rulebook-open-20261114), laid out as
model-NN/submissions.json (runner output, NN = roster rank) and
model-NN-judge/judged.json (eval_suite.judge_sweep, Sol Pro judge). Scores are
recomputed with the frozen tasks/combined_score.py; overall is the equal-weight
mean of the three task means, as before. Writes NEW_RUN_DIR/final-leaderboard.json.
No API calls.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tasks import combined_score as cs  # noqa: E402

OLD = ROOT / '.benchmark-runs/rerun-20261107/final-leaderboard.json'
NEW = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else ROOT / '.benchmark-runs/rulebook-open-20261114'
TASKS = ('keep_going', 'rulebook_vs_body', 'beat_ectemp')
JUDGE = 'openai/gpt-6.1-sol-pro'
MARKER = 'Reference, TB MED 507 (12 April 2022)'


def rel(p: Path) -> str:
    return str(p.resolve().relative_to(ROOT))


def load_model(rank: int, mid: str):
    sub_path = NEW / f'model-{rank:02d}/submissions.json'
    jud_path = NEW / f'model-{rank:02d}-judge/judged.json'
    sub, jud = json.loads(sub_path.read_text()), json.loads(jud_path.read_text())
    if sub['model'] != mid or jud['model'] != mid:
        raise SystemExit(f'rank {rank}: model mismatch {sub["model"]!r} / {jud["model"]!r} != {mid!r}')
    if sub.get('status') != 'complete':
        raise SystemExit(f'rank {rank}: submission status {sub.get("status")!r}')
    cases = sorted(c['case_id'] for c in sub['cases'])
    if cases != ['RB-01', 'RB-02'] or sorted(c['case_id'] for c in jud['cases']) != cases:
        raise SystemExit(f'rank {rank}: expected RB-01 and RB-02, got {cases}')
    for c in sub['cases']:
        if MARKER not in c['materials']['prompt']:
            raise SystemExit(f'rank {rank} {c["case_id"]}: prompt sent without the TB MED 507 chart')
    for c in jud['cases']:
        jr = c['judge_record']
        if jr.get('judge_model') != JUDGE:
            raise SystemExit(f'rank {rank} {c["case_id"]}: judge {jr.get("judge_model")!r} != {JUDGE}')
        if jr['status'] not in ('scored', 'absent_answer'):
            raise SystemExit(f'rank {rank} {c["case_id"]}: judge status {jr["status"]!r}')
    return sub_path, sub, jud_path, jud


def main() -> int:
    old = json.loads(OLD.read_text())
    params = json.loads((ROOT / 'tasks/scoring_params.json').read_text())
    board = []
    for row in old['leaderboard']:
        mid, rank = row['model'], row['roster_rank']
        sub_path, sub, jud_path, jud = load_model(rank, mid)
        scores = cs.score_runs([{'model': mid, 'cases': jud['cases']}], params)[mid]
        by_id = {c['case_id']: c for c in sub['cases']}
        status = {c['case_id']: c['judge_record']['status'] for c in jud['cases']}
        rb_rows = []
        for (task, cid), rec in sorted(scores.items()):
            if rec['status'] != 'scored':
                raise SystemExit(f'rank {rank} {cid}: not scorable: {rec}')
            rb_rows.append({
                'task': task, 'case_id': cid, 'combined': rec['combined'],
                'components': rec['attempts'][0]['components'],
                'flags': rec['attempts'][0].get('flags') or [],
                'judge_status': status[cid],
                'finish_reason': by_id[cid].get('finish_reason'),
                'submission': rel(sub_path), 'judged': rel(jud_path),
            })
        kept = [c for c in row['cases'] if c['task'] != 'rulebook_vs_body']
        means = dict(row['task_mean_combined'])
        means['rulebook_vs_body'] = sum(c['combined'] for c in rb_rows) / len(rb_rows)
        task_100 = {t: means[t] * 100 for t in TASKS}
        graders = [by_id[c]['grader'] for c in ('RB-01', 'RB-02')]
        raw = dict(row['raw'])
        raw['rulebook_vs_body'] = {
            'lookup_fields_correct': sum(sum(bool(v) for v in g['rulebook'].get('matches', {}).values()) for g in graders),
            'lookup_fields_total': sum(len(g['rulebook']['expected']) for g in graders),
            'override_correct': sum(bool(g['body'].get('decision_correct')) for g in graders),
            'override_total': len(graders),
            'work_rest_answers': [str((g['rulebook'].get('parsed') or {}).get('work_rest_min')) for g in graders],
        }
        board.append({
            **row,
            'task_mean_combined': means,
            'task_scores_100': task_100,
            'overall_100': sum(task_100.values()) / 3,
            'raw': raw,
            'cases': sorted(kept + rb_rows, key=lambda c: (c['task'], c['case_id'])),
            'sources': sorted(set(row['sources']) | {sub_path.parent.name}),
            'rulebook_run_usd': (sub.get('spend') or {}).get('accounted_usd', 0.0),
            'rulebook_judge_usd': (jud.get('spend') or {}).get('accounted_usd', 0.0),
        })
    board.sort(key=lambda r: (-r['overall_100'], r['roster_rank']))
    for i, r in enumerate(board, 1):
        r['rank'] = i
    out = {
        'schema': 'roster-leaderboard-open-book-rulebook-v1',
        'created_at': datetime.now(timezone.utc).isoformat(),
        'based_on': rel(OLD),
        'rulebook_run': rel(NEW),
        'rulebook_prompt': 'open book: TB MED 507 (12 April 2022) Tables 1 and 2 plus legend included in the prompt',
        'judge_model': JUDGE,
        'frozen_weights': cs.WEIGHTS,
        'note': ('Keep/Pull and Beat ECTemp cases are the 2026-11-07/08 roster run, unchanged. '
                 'Rulebook cases were rerun on 2026-11-14 with the 2022 chart in the prompt and '
                 'judged by the same Sol Pro judge; they replace the closed-book Rulebook cases.'),
        'leaderboard': board,
    }
    path = NEW / 'final-leaderboard.json'
    path.write_text(json.dumps(out, indent=1) + '\n')
    print(f'wrote {rel(path)}')
    for r in board:
        print(f"{r['rank']:>2} {r['display']:<26} overall {r['overall_100']:5.1f}  rulebook {r['task_scores_100']['rulebook_vs_body']:5.1f}"
              f"  cells {r['raw']['rulebook_vs_body']['lookup_fields_correct']}/8  calls {r['raw']['rulebook_vs_body']['override_correct']}/2")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
