"""Incrementally run the question bank against models.

Only (model, question) pairs without a current score are sent. Logging prints
question ids and scores only — never prompts or outputs of hidden questions,
because CI logs of a public repo are world-readable.
"""
from __future__ import annotations

import json
import os
from concurrent.futures import ThreadPoolExecutor

from . import client, sandbox, suites
from .common import (OUTPUTS_DIR, PRIVATE_OUTPUTS_DIR, Question, load_models, load_questions, load_scores,
                     runnable_models, save_scores, today, write_json)


def _mock_answer(model: dict, q: Question) -> client.ChatResult:
    kind = model["openrouter_id"].split(":", 1)[1]
    if kind == "reference":
        if q.suite == "coding":
            text = "```python\n" + q.data["reference"] + "\n```"
        else:
            text = json.dumps(q.data["expected"])
    else:
        text = "I'm not sure."
    return client.ChatResult(text=text, provider="mock")


def _ask(model: dict, q: Question) -> client.ChatResult:
    if model["openrouter_id"].startswith("mock:"):
        return _mock_answer(model, q)
    return client.chat(model, suites.build_prompt(q.suite, q.data))


def run_model(model: dict, questions: list[Question], budget: list[float], concurrency: int, rerun: bool) -> None:
    slug = model["slug"]
    scores = load_scores(slug)
    items = scores["items"]
    todo = [q for q in questions if rerun or items.get(q.key, {}).get("h") != q.hash]
    if not todo:
        print(f"[{slug}] up to date")
        return
    if budget[0] <= 0:
        print(f"[{slug}] skipped: budget exhausted")
        return
    print(f"[{slug}] {len(todo)} questions to run")

    answers: dict[str, client.ChatResult] = {}
    with ThreadPoolExecutor(concurrency) as pool:
        for i in range(0, len(todo), concurrency):
            if budget[0] <= 0:
                print(f"[{slug}] budget exhausted, stopping early")
                break
            batch = todo[i:i + concurrency]
            for q, res in zip(batch, pool.map(lambda q: _ask(model, q), batch)):
                answers[q.key] = res
                budget[0] -= res.cost

    by_key = {q.key: q for q in todo}
    errors = {k: r for k, r in answers.items() if r.error}
    ok = {k: r for k, r in answers.items() if not r.error}

    coding_cases = {k: suites.coding_case(by_key[k].data, r.text) for k, r in ok.items() if by_key[k].suite == "coding"}
    coding_results = sandbox.run_cases(coding_cases)

    public_out: dict[str, dict] = {}
    private_out: dict[str, dict] = {}
    for k, r in ok.items():
        q = by_key[k]
        if q.suite == "coding":
            res = coding_results[k]
            score, detail = (1.0 if res["passed"] else 0.0), {"error": res["error"]}
        else:
            parsed, strict = suites.parse_json_output(r.text)
            score, detail = suites.score_extract(q.data["expected"], parsed)
            detail["bare_json"] = strict
        items[k] = {"h": q.hash, "v": q.visibility[:4], "score": round(score, 4), "provider": r.provider,
                    "truncated": r.finish_reason == "length" or None, "at": today()}
        items[k] = {kk: vv for kk, vv in items[k].items() if vv is not None}
        (private_out if q.private else public_out)[k] = {"output": r.text[:20000], "score": round(score, 4), "detail": detail}
        print(f"[{slug}] {k} {score:.2f}")

    for k, r in errors.items():
        # Shown for hidden questions too: the error comes from the API, not from model output.
        print(f"[{slug}] {k} ERROR {r.error[:200]}")

    save_scores(slug, scores)
    _save_outputs(OUTPUTS_DIR / slug, public_out)
    if os.environ.get("BENCH_SAVE_PRIVATE_OUTPUTS") == "1" and not os.environ.get("CI"):
        _save_outputs(PRIVATE_OUTPUTS_DIR / slug, private_out)
    spent = sum(r.cost for r in answers.values())
    print(f"[{slug}] done: {len(ok)} scored, {len(errors)} errors, ${spent:.4f}")


def _save_outputs(d, outputs: dict) -> None:
    by_suite: dict[str, dict] = {}
    for k, v in outputs.items():
        suite, qid = k.split("/", 1)
        by_suite.setdefault(suite, {})[qid] = v
    for suite, new in by_suite.items():
        p = d / f"{suite}.json"
        cur = json.loads(p.read_text()) if p.exists() else {}
        cur.update(new)
        write_json(p, dict(sorted(cur.items())))


def main(args) -> None:
    doc = load_models()
    models = runnable_models(doc)
    if args.models:
        wanted = set(args.models.split(","))
        models = [m for m in doc["models"] if m["slug"] in wanted]
        missing = wanted - {m["slug"] for m in models}
        if missing:
            raise SystemExit(f"unknown model slugs: {sorted(missing)}")
    questions = load_questions()
    if args.suites:
        questions = [q for q in questions if q.suite in args.suites.split(",")]
    budget = [args.budget_usd]
    for m in models:
        run_model(m, questions, budget, args.concurrency, args.rerun)
    print(f"total spent: ${args.budget_usd - budget[0]:.4f}")
