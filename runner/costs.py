"""API cost per task, measured on the public questions.

A model's cost is the average OpenRouter charge over the public questions of a suite
group (coding + extract for the local leaderboard, decisions for the decision board),
shown as dollars per 1,000 tasks. Answers scored since 2026-10-11 carry their own cost;
for older ones, `python -m runner sample-cost` re-asks just the public questions and
stores the charge in results/costs.json. Scores are never touched.
"""
from __future__ import annotations

import json
import time
from concurrent.futures import ThreadPoolExecutor

from . import client, run
from .common import RESULTS, load_models, load_questions, load_scores, model_suites, runnable_models, today, write_json

COSTS_FILE = RESULTS / "costs.json"
GROUPS = {"tasks": ("coding", "extract"), "decisions": ("decisions",)}


def _load() -> dict:
    return json.loads(COSTS_FILE.read_text()) if COSTS_FILE.exists() else {}


def per_1k(model: dict, public_qs: list, sampled: dict | None = None) -> dict:
    """{"tasks": $ per 1,000 coding/document tasks, "decisions": $ per 1,000 decisions}; None when not fully measured."""
    sampled = (sampled if sampled is not None else _load()).get(model["slug"], {})
    items = load_scores(model["slug"])["items"]
    out = {}
    for group, suites in GROUPS.items():
        qs = [q for q in public_qs if q.suite in suites and q.suite in model_suites(model)]
        costs = []
        for q in qs:
            it = items.get(q.key, {})
            c = it.get("cost") if it.get("h") == q.hash and it.get("cost") is not None else (sampled.get(q.key) or {}).get("cost")
            if c is None:
                break
            costs.append(c)
        out[group] = round(1000 * sum(costs) / len(costs), 2) if qs and len(costs) == len(qs) else None
    return out


def _missing(model: dict, public_qs: list, sampled: dict) -> list:
    items = load_scores(model["slug"])["items"]
    have = sampled.get(model["slug"], {})
    return [q for q in public_qs if q.suite in model_suites(model)
            and not (items.get(q.key, {}).get("h") == q.hash and items.get(q.key, {}).get("cost") is not None)
            and (have.get(q.key) or {}).get("cost") is None]


def main(args) -> None:
    doc = load_models()
    models = [m for m in runnable_models(doc) if m.get("status") != "reference" and not (m.get("openrouter_id") or "").startswith("mock:")]
    public_qs = load_questions(include_private=False)
    sampled = _load()
    jobs = [(m, q) for m in models for q in _missing(m, public_qs, sampled)]
    print(f"{len(jobs)} public answers to price across {len({m['slug'] for m, _ in jobs})} models", flush=True)
    spent = 0.0

    def ask(job):
        m, q = job
        try:
            return job, run._ask(m, q)
        except Exception as e:  # noqa: BLE001
            return job, client.ChatResult(error=str(e)[:200])

    deadline = time.monotonic() + args.max_minutes * 60
    with ThreadPoolExecutor(args.concurrency) as pool:
        # Batches, so the budget and time limits are checked between them.
        for i in range(0, len(jobs), args.concurrency):
            if spent > args.budget_usd or time.monotonic() > deadline:
                print("stopped: budget or time limit reached; the rest is priced next run", flush=True)
                break
            for (m, q), r in pool.map(ask, jobs[i:i + args.concurrency]):
                if r.error:
                    print(f"[{m['slug']}] {q.key} ERROR {r.error[:120]}", flush=True)
                    continue
                spent += r.cost
                sampled.setdefault(m["slug"], {})[q.key] = {"cost": round(r.cost, 7), "ptok": (r.usage or {}).get("prompt_tokens"),
                                                             "tok": (r.usage or {}).get("completion_tokens"), "at": today()}
    write_json(COSTS_FILE, dict(sorted(sampled.items())))
    print(f"priced; spent ${spent:.4f}", flush=True)
