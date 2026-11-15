# SoldierPhysio results site

Next.js static site for the 2026-11-07/08 roster run (Keep/Pull, Beat ECTemp) with the 2026-11-14 open-book Rulebook rerun swapped in, GPT-6.1 Sol added and every case re-judged by GLM-5.3 Prime on 2026-11-15: leaderboard, findings, methodology, and trace explorer.

**Live:** [https://soliderphys-bench.pages.dev](https://soliderphys-bench.pages.dev)

## Local dev

```sh
cd site
npm install
npm run dev          # http://localhost:3000
```

`lib/soldier.json` and `public/traces/cases.json` come from the saved benchmark run. Regenerate from the repo root (no API calls):

```sh
python scripts/merge_open_book_rulebook.py      # open-book Rulebook board (Sol Pro judge, historical)
python scripts/rejudge_off_roster.py inputs     # gather each model's 21 scored cases, plus GPT-6.1 Sol
python scripts/rejudge_off_roster.py judge      # paid: re-judge every case with GLM-5.3 Prime
python scripts/rejudge_off_roster.py board      # .benchmark-runs/rejudge-glm-20261115/final-leaderboard.json
python scripts/build_site_data.py
python scripts/make_index_charts.py             # README figures from the same lib/soldier.json
```

Model answers come from `.benchmark-runs/rerun-20261107` (Keep/Pull, Beat ECTemp),
`.benchmark-runs/rulebook-open-20261114` (Rulebook, chart in the prompt) and
`.benchmark-runs/sol-20261115` (GPT-6.1 Sol, all 21 cases). Every judgment the site shows is in
`.benchmark-runs/rejudge-glm-20261115/model-NN-judge`.

## Deploy (Cloudflare Pages)

```sh
cd site
npm run deploy
```

Model logos under `public/model-logos/` are vendored from [Lobe Icons](https://github.com/lobehub/lobe-icons); see `public/model-logos/README.md`.