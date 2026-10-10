"""Incrementally run the question bank against models.

Only (model, question) pairs without a current score are sent. Logging prints
question ids and scores only — never prompts or outputs of hidden questions,
because CI logs of a public repo are world-readable.
"""
from __future__ import annotations

import json
import os
import time
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait

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
    elif kind == "slow":
        time.sleep(2)
        text = "too slow"
    else:
        text = "I'm not sure."
    return client.ChatResult(text=text, provider="mock")


def _ask(model: dict, q: Question) -> client.ChatResult:
    if model["openrouter_id"].startswith("mock:"):
        return _mock_answer(model, q)
    return client.chat(model, suites.build_prompt(q.suite, q.data))


def finalize_model(model: dict, todo: list[Question], answers: dict[str, client.ChatResult]) -> None:
    """Grade the answers collected for one model and persist them."""
    slug = model["slug"]
    scores = load_scores(slug)
    items = scores["items"]
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
        # Grader errors are printed for public questions only (hidden ones would leak test details).
        why = f"  ({detail.get('error')})" if q.suite == "coding" and not q.private and detail.get("error") else ""
        print(f"[{slug}] {k} {score:.2f}{why}", flush=True)

    for k, r in errors.items():
        # Shown for hidden questions too: the error comes from the API, not from model output.
        print(f"[{slug}] {k} ERROR {r.error[:200]}")

    save_scores(slug, scores)
    _save_outputs(OUTPUTS_DIR / slug, public_out)
    if os.environ.get("BENCH_SAVE_PRIVATE_OUTPUTS") == "1" and not os.environ.get("CI"):
        _save_outputs(PRIVATE_OUTPUTS_DIR / slug, private_out)
    spent = sum(r.cost for r in answers.values())
    left = len(todo) - len(ok)
    print(f"[{slug}] saved: {len(ok)} scored, {len(errors)} errors, {left} still to do, ${spent:.4f}", flush=True)


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

    # One global queue of (model, question) jobs, ordered model by model so models
    # complete one after another, while slow requests never block the others.
    todo: dict[str, list[Question]] = {}
    for m in models:
        items = load_scores(m["slug"])["items"]
        todo[m["slug"]] = [q for q in questions if args.rerun or items.get(q.key, {}).get("h") != q.hash]
    jobs = [(m, q) for m in models for q in todo[m["slug"]]]
    print(f"{len(jobs)} (model, question) pairs to run across {sum(bool(v) for v in todo.values())} models", flush=True)

    by_slug = {m["slug"]: m for m in models}
    answers: dict[str, dict[str, client.ChatResult]] = {slug: {} for slug in todo}
    pending = {slug: len(qs) for slug, qs in todo.items()}
    deadline = time.monotonic() + args.max_minutes * 60
    spent, stop = 0.0, None
    queue = iter(jobs)

    with ThreadPoolExecutor(args.concurrency) as pool:
        inflight = {}
        while True:
            while stop is None and len(inflight) < args.concurrency:
                if spent >= args.budget_usd:
                    stop = f"budget of ${args.budget_usd} reached"
                elif time.monotonic() > deadline:
                    stop = f"time limit of {args.max_minutes} min reached"
                else:
                    job = next(queue, None)
                    if job is None:
                        break
                    inflight[pool.submit(_ask, *job)] = job
            if not inflight:
                break
            done, _ = wait(inflight, return_when=FIRST_COMPLETED)
            for f in done:
                m, q = inflight.pop(f)
                res = f.result()
                spent += res.cost
                answers[m["slug"]][q.key] = res
                pending[m["slug"]] -= 1
                if pending[m["slug"]] == 0:
                    finalize_model(m, todo[m["slug"]], answers.pop(m["slug"]))

    if stop:
        print(f"stopped submitting: {stop}", flush=True)
    for slug, got in answers.items():  # models only partly answered when we stopped
        if got:
            finalize_model(by_slug[slug], todo[slug], got)
    print(f"total spent: ${spent:.4f}", flush=True)
