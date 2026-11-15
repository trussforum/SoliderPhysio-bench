"""Re-judge the whole leaderboard with an off-roster judge and add GPT-6.1 Sol.

    python scripts/rejudge_off_roster.py inputs   # no API calls
    python scripts/rejudge_off_roster.py judge    # paid: one judge_sweep per model
    python scripts/rejudge_off_roster.py board    # no API calls

Why: GPT-6.1 Sol joined the roster on 2026-11-15 (slot 16). The previous judge,
openai/gpt-6.1-sol-pro, is a Sol sibling from the same lab, so it may not grade
Sol. Every case is re-judged with tasks.combined_score.JUDGE_MODEL (GLM-5.3 Prime,
a lab with no model on the roster).

inputs: for every row of the current leaderboard (BASE), collect the exact 21
  source cases it was scored from (each case's `submission` file) into
  OUT/inputs/model-NN.json. Sol's cases come from SOL (a fresh run with the same
  task code, open-book Rulebook prompt included).
judge:  eval_suite.judge_sweep with the new judge into OUT/model-NN-judge/.
board:  score with the frozen tasks/combined_score.py; overall is the equal-weight
  mean of the three task means, as before. Writes OUT/final-leaderboard.json and
  prints the score shift each model saw from the judge swap.
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tasks import combined_score as cs  # noqa: E402

BASE = ROOT / '.benchmark-runs/rulebook-open-20261114/final-leaderboard.json'
SOL = ROOT / '.benchmark-runs/sol-20261115/model-16/submissions.json'
OUT = ROOT / '.benchmark-runs/rejudge-glm-20261115'
TASKS = ('keep_going', 'rulebook_vs_body', 'beat_ectemp')
MARKER = 'Reference, TB MED 507 (12 April 2022)'
CAP_PER_MODEL_USD = 4.0


def rel(p: Path) -> str:
    return str(Path(p).resolve().relative_to(ROOT))


def load(p):
    return json.loads(Path(p).read_text())


def roster():
    return {m['rank']: m for m in load(ROOT / 'eval_suite/roster.json')['models'] if m.get('openrouter_id')}


def required():
    params = load(ROOT / 'tasks/scoring_params.json')
    return sorted(f'{t}/{c}' for t, c in cs.parse_required(params['required_cases']))


def build_inputs():
    base = load(BASE)
    (OUT / 'inputs').mkdir(parents=True, exist_ok=True)
    need = required()
    rows = [(r['roster_rank'], r['model'], [(c['task'], c['case_id'], c['submission']) for c in r['cases']])
            for r in base['leaderboard']]
    sol = load(SOL) if SOL.exists() else {}
    if sol.get('status') == 'complete':
        rows.append((16, sol['model'], [(c['task'], c['case_id'], rel(SOL)) for c in sol['cases']]))
    else:
        print(f'skipping Sol: {rel(SOL)} is {sol.get("status", "missing")!r}, not complete')
    ros = roster()
    for rank, mid, refs in rows:
        if ros[rank]['openrouter_id'] != mid:
            raise SystemExit(f'rank {rank}: {mid} is not roster slot {rank}')
        cache, cases = {}, []
        for task, cid, src in refs:
            sub = cache.setdefault(src, load(ROOT / src))
            if sub['model'] != mid:
                raise SystemExit(f'{src}: model {sub["model"]!r} != {mid!r}')
            match = [c for c in sub['cases'] if c['task'] == task and c['case_id'] == cid]
            if len(match) != 1:
                raise SystemExit(f'{mid} {task}/{cid}: {len(match)} copies in {src}')
            c = dict(match[0], source_submission=src)
            if task == 'rulebook_vs_body' and MARKER not in c['materials']['prompt']:
                raise SystemExit(f'{mid} {cid}: Rulebook prompt lacks the TB MED 507 chart')
            cases.append(c)
        got = sorted(f"{c['task']}/{c['case_id']}" for c in cases)
        if got != need:
            raise SystemExit(f'{mid}: cases {got} != required {need}')
        path = OUT / 'inputs' / f'model-{rank:02d}.json'
        path.write_text(json.dumps({'model': mid, 'status': 'complete', 'roster_rank': rank,
                                    'sources': sorted(cache), 'cases': cases}, indent=1) + '\n')
        print(f'{rank:>2} {mid:<36} {len(cases)} cases from {len(cache)} source file(s)')


def judge():
    from eval_suite import judge_sweep
    total = 0.0
    for path in sorted((OUT / 'inputs').glob('model-*.json')):
        out = OUT / (path.stem + '-judge')
        res = judge_sweep.run(path, out, CAP_PER_MODEL_USD)
        total += res['spend']['accounted_usd']
        print(f"{path.stem}: {res['cases']} cases, {res['not_scorable']} not scorable, "
              f"${res['spend']['accounted_usd']:.4f}", flush=True)
    print(f'judge total ${total:.2f}')


def raw_totals(cases, params):
    g = {t: [c['grader'] for c in cases if c['task'] == t] for t in TASKS}
    kg_err = [x['core_abs_error_c'] for x in g['keep_going'] if x['core_abs_error_c'] is not None]
    rb = g['rulebook_vs_body']
    be = {}
    for v in ('3A', '3B'):
        people = [(c['case_id'].split('/')[1], c['grader']) for c in cases
                  if c['task'] == 'beat_ectemp' and c['case_id'].startswith(v + '/')]
        be[v] = [(params['ectemp_B'][v][p], x['person_mae']) for p, x in people
                 if x['valid'] and x['person_mae'] is not None]
    return {
        'keep_going': {'correct': sum(x['decision_correct'] for x in g['keep_going']), 'n': len(g['keep_going']),
                       'forecasts': len(kg_err), 'mae_c': mean(kg_err) if kg_err else None},
        'rulebook_vs_body': {
            'lookup_fields_correct': sum(sum(bool(v) for v in x['rulebook'].get('matches', {}).values()) for x in rb),
            'lookup_fields_total': sum(len(x['rulebook']['expected']) for x in rb),
            'override_correct': sum(bool(x['body'].get('decision_correct')) for x in rb),
            'override_total': len(rb),
            'work_rest_answers': [str((x['rulebook'].get('parsed') or {}).get('work_rest_min')) for x in rb]},
        'beat_ectemp': {
            'people_beating_baseline': sum(m < b for v in be.values() for b, m in v),
            'people_total': sum(1 for c in cases if c['task'] == 'beat_ectemp'),
            'variant_mae': {v: mean(m for _, m in be[v]) if be[v] else None for v in be}},
    }


def same(a, b):
    if isinstance(a, dict) and isinstance(b, dict):
        return a.keys() == b.keys() and all(same(a[k], b[k]) for k in a)
    if isinstance(a, float) or isinstance(b, float):
        return a is not None and b is not None and abs(a - b) < 1e-9
    return a == b


def judge_agreement(rows, base):
    """Same saved answers, two judges: GLM vs the retired Sol Pro marks, plus GLM vs code."""
    old_marks, cache = {}, {}
    for r in base['leaderboard']:
        for c in r['cases']:
            j = cache.setdefault(c['judged'], load(ROOT / c['judged']))
            m = next(x for x in j['cases'] if x['task'] == c['task'] and x['case_id'] == c['case_id'])
            old_marks[(r['model'], c['task'], c['case_id'])] = m.get('judge') or {}
    dims, vs_code = {}, Counter()
    for r in rows:
        jud = cache.setdefault(r['cases'][0]['judged'], load(ROOT / r['cases'][0]['judged']))
        for c in jud['cases']:
            new = c.get('judge') or {}
            if c['judge_record']['status'] != 'scored':
                continue
            g = c.get('grader') or {}
            body = g.get('body', g)
            dim = 'decision' if 'decision' in new else 'override_decision' if 'override_decision' in new else None
            if dim and 'decision_correct' in body:
                right = bool(body['decision_correct'])
                vs_code['agree' if (new[dim] >= 3) == right else 'disagree'] += 1
            old = old_marks.get((r['model'], c['task'], c['case_id']))
            for k, v in new.items():
                if old and isinstance(old.get(k), (int, float)) and isinstance(v, (int, float)):
                    d = dims.setdefault(k, {'pairs': 0, 'exact': 0, 'within_1': 0, 'sum_diff': 0.0})
                    d['pairs'] += 1
                    d['exact'] += v == old[k]
                    d['within_1'] += abs(v - old[k]) <= 1
                    d['sum_diff'] += v - old[k]
    for d in dims.values():
        d['mean_glm_minus_sol_pro'] = d.pop('sum_diff') / d['pairs']
    return {'glm_vs_sol_pro_same_answers': dims, 'decision_mark_vs_code': dict(vs_code)}


def board():
    base = load(BASE)
    params = load(ROOT / 'tasks/scoring_params.json')
    old = {r['model']: r for r in base['leaderboard']}
    ros = roster()
    rows, judgments, judge_usd = [], Counter(), 0.0
    for path in sorted((OUT / 'inputs').glob('model-*.json')):
        sub = load(path)
        jpath = OUT / (path.stem + '-judge') / 'judged.json'
        jud = load(jpath)
        mid, rank = sub['model'], sub['roster_rank']
        if jud['model'] != mid or len(jud['cases']) != len(sub['cases']):
            raise SystemExit(f'{jpath}: incomplete or mismatched')
        for c in jud['cases']:
            jr = c['judge_record']
            if jr.get('judge_model') != cs.JUDGE_MODEL:
                raise SystemExit(f'{mid} {c["case_id"]}: judge {jr.get("judge_model")!r}')
            if jr['status'] not in ('scored', 'absent_answer'):
                raise SystemExit(f'{mid} {c["case_id"]}: judge status {jr["status"]!r}')
            judgments[jr['status']] += 1
        judge_usd += jud['spend']['accounted_usd']
        scores = cs.score_runs([{'model': mid, 'cases': jud['cases']}], params)[mid]
        by_id = {(c['task'], c['case_id']): c for c in sub['cases']}
        status = {(c['task'], c['case_id']): c['judge_record']['status'] for c in jud['cases']}
        case_rows = []
        for key, rec in sorted(scores.items()):
            if rec['status'] != 'scored':
                raise SystemExit(f'{mid} {key}: not scorable: {rec}')
            case_rows.append({'task': key[0], 'case_id': key[1], 'combined': rec['combined'],
                              'components': rec['attempts'][0]['components'],
                              'flags': rec['attempts'][0].get('flags') or [],
                              'judge_status': status[key], 'finish_reason': by_id[key].get('finish_reason'),
                              'submission': by_id[key]['source_submission'], 'judged': rel(jpath)})
        means = {t: mean(c['combined'] for c in case_rows if c['task'] == t) for t in TASKS}
        task_100 = {t: means[t] * 100 for t in TASKS}
        prev = old.get(mid)
        row = {
            'rank': None, 'model': mid, 'display': ros[rank]['model'], 'roster_rank': rank,
            'task_mean_combined': means, 'task_scores_100': task_100,
            'overall_100': sum(task_100.values()) / 3, 'coverage': len(case_rows),
            'accounted_usd_inventory': (prev or {}).get('accounted_usd_inventory',
                                                         (load(SOL).get('spend') or {}).get('accounted_usd', 0.0)),
            'sources': sorted({Path(s).parent.name for s in sub['sources']}),
            'raw': raw_totals(sub['cases'], params), 'cases': case_rows,
            'provisional_research_and_overall': True,
            'judge_usd': jud['spend']['accounted_usd'],
            'sol_pro_judge_overall_100': prev['overall_100'] if prev else None,
        }
        if prev and not same(row['raw'], prev['raw']):
            raise SystemExit(f'{mid}: recomputed raw totals differ from the base board')
        rows.append(row)
    rows.sort(key=lambda r: (-r['overall_100'], r['roster_rank']))
    for i, r in enumerate(rows, 1):
        r['rank'] = i
    out = {
        'schema': 'roster-leaderboard-off-roster-judge-v1',
        'created_at': datetime.now(timezone.utc).isoformat(),
        'based_on': rel(BASE),
        'sol_run': rel(SOL.parent),
        'rulebook_prompt': base.get('rulebook_prompt'),
        'judge_model': cs.JUDGE_MODEL,
        'previous_judge_model': base.get('judge_model'),
        'judgments': dict(judgments),
        'judge_usd': judge_usd,
        'frozen_weights': cs.WEIGHTS,
        'note': ('Same saved model answers as the open-book board, plus GPT-6.1 Sol (slot 16, run '
                 '2026-11-15). Every case re-judged on 2026-11-15 by GLM-5.3 Prime, whose lab has no '
                 'model on the roster; the Sol Pro judge was retired because Sol is now rated.'),
        'judge_agreement': judge_agreement(rows, base),
        'leaderboard': rows,
    }
    path = OUT / 'final-leaderboard.json'
    path.write_text(json.dumps(out, indent=1) + '\n')
    print(f'wrote {rel(path)}  judgments {dict(judgments)}  judge ${judge_usd:.2f}')
    print(json.dumps(out['judge_agreement'], indent=1))
    for r in rows:
        was = r['sol_pro_judge_overall_100']
        shift = '   new' if was is None else f'{r["overall_100"] - was:+6.1f}'
        print(f"{r['rank']:>2} {r['display']:<26} overall {r['overall_100']:5.1f} ({shift} vs Sol Pro judge)  "
              + '  '.join(f"{t[:4]} {r['task_scores_100'][t]:5.1f}" for t in TASKS))


if __name__ == '__main__':
    steps = {'inputs': build_inputs, 'judge': judge, 'board': board}
    if len(sys.argv) != 2 or sys.argv[1] not in steps:
        raise SystemExit(__doc__)
    steps[sys.argv[1]]()
