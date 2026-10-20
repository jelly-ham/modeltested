"""Incrementally run the question bank against models.

Only (model, question) pairs without a current score are sent. Logging prints
question ids and scores only — never prompts or outputs of hidden questions,
because CI logs of a public repo are world-readable.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import time
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait

from . import client, sandbox, suites
HARD_GRACE_MIN = float(os.environ.get("BENCH_HARD_GRACE_MIN", 5))  # minutes after --max-minutes before in-flight requests are abandoned

from .common import (OUTPUTS_DIR, PRIVATE_OUTPUTS_DIR, Question, load_models, load_questions, load_scores,
                     model_suites, runnable_models, save_scores, today, write_json)


def _mock_answer(model: dict, q: Question) -> client.ChatResult:
    kind = model["openrouter_id"].split(":", 1)[1]
    if kind == "reference":
        if q.suite == "coding":
            text = "```python\n" + q.data["reference"] + "\n```"
        elif q.suite == "decisions":
            text = json.dumps({qid: {suites._expected_key(spec, q.data["expected"][qid]): 1.0}
                               for qid, spec in q.data["questions"].items()})
        else:
            text = json.dumps(q.data["expected"])
    elif kind == "slow":
        time.sleep(2)
        text = "too slow"
    elif kind == "explode":
        if q.suite == "coding":
            raise RuntimeError("simulated client crash")
        text = "{}"
    elif kind == "hang":
        time.sleep(3600)
        text = ""
    else:
        text = "I'm not sure."
    return client.ChatResult(text=text, provider="mock")


def model_cfg(model: dict) -> str | None:
    """Fingerprint of non-default request settings; answers given under other settings are re-run."""
    cfg = {k: model[k] for k in ("reasoning", "temperature", "max_tokens", "provider") if k in model}
    return hashlib.sha256(json.dumps(cfg, sort_keys=True).encode()).hexdigest()[:8] if cfg else None


def _ask(model: dict, q: Question) -> client.ChatResult:
    if (model.get("openrouter_id") or "").startswith("mock:"):
        return _mock_answer(model, q)
    if model.get("backend") == "clm":
        return client.clm_decide(model, q.data["state"], q.data["questions"])
    if model.get("backend") == "ollama":
        return client.ollama_chat(model, suites.build_prompt(q.suite, q.data))
    if q.suite == "decisions" and model.get("kind") == "decision":
        state = q.data["state"]
        # Some decision APIs only take text: send structured states as the same JSON text the LLMs see.
        if model.get("text_state") and not isinstance(state, str):
            state = json.dumps(state, indent=2)
        return client.decide(model, state, q.data["questions"])
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
        elif q.suite == "decisions":
            qs = q.data["questions"]
            try:
                probs = (suites.decisions_from_api(json.loads(r.text), qs) if model.get("kind") == "decision"
                         else suites.decisions_from_llm(r.text, qs))
            except ValueError:
                probs = {}
            score, detail = suites.score_decisions(qs, q.data["expected"], probs)
        else:
            parsed, strict = suites.parse_json_output(r.text)
            score, detail = suites.score_extract(q.data["expected"], parsed)
            detail["bare_json"] = strict
        items[k] = {"h": q.hash, "v": q.visibility[:4], "score": round(score, 4), "provider": r.provider,
                    "truncated": r.finish_reason == "length" or None, "brier": detail.get("brier"), "cfg": model_cfg(model),
                    "tok": (r.usage or {}).get("completion_tokens"), "ptok": (r.usage or {}).get("prompt_tokens"),
                    "cost": round(r.cost, 7) if r.cost else None,
                    "mt": model.get("max_tokens", client.MAX_TOKENS) if q.suite != "decisions" or model.get("kind") != "decision" else None,
                    "at": today()}
        items[k] = {kk: vv for kk, vv in items[k].items() if vv is not None}
        out = {"output": r.text[:20000], "score": round(score, 4), "detail": detail}
        if r.finish_reason == "length" and r.reasoning and not q.private:
            # Public questions only: where a model's reasoning was when it ran out of tokens.
            out["reasoning_tail"] = r.reasoning[-6000:]
        (private_out if q.private else public_out)[k] = out
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


def _finalize_safely(model: dict, todo: list[Question], answers: dict[str, client.ChatResult]) -> None:
    try:
        finalize_model(model, todo, answers)
    except Exception as e:
        # e.g. the sandbox failed; this model's answers are retried next run.
        print(f"[{model['slug']}] FAILED to grade: {type(e).__name__}: {str(e)[:300]}", flush=True)


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
    if getattr(args, "local", False):
        models = [m for m in doc["models"] if m.get("status") == "local"]
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
        allowed = model_suites(m)
        todo[m["slug"]] = [q for q in questions if q.suite in allowed and (args.rerun or items.get(q.key, {}).get("h") != q.hash
                           or (getattr(args, "rerun_truncated", False) and items[q.key].get("truncated"))
                           # Decision models may only be served by their maker (Clef Omni by Cloudflare), as in discover.
                           or (items[q.key].get("provider") in client.BLOCKED_PROVIDERS and m.get("kind") != "decision")
                           or items[q.key].get("cfg") != model_cfg(m)
                           or (items[q.key].get("truncated") and items[q.key].get("mt", 8192) < m.get("max_tokens", client.MAX_TOKENS)))]
    jobs = [(m, q) for m in models for q in todo[m["slug"]]]
    print(f"{len(jobs)} (model, question) pairs to run across {sum(bool(v) for v in todo.values())} models", flush=True)

    by_slug = {m["slug"]: m for m in models}
    answers: dict[str, dict[str, client.ChatResult]] = {slug: {} for slug in todo}
    pending = {slug: len(qs) for slug, qs in todo.items()}
    deadline = time.monotonic() + args.max_minutes * 60
    spent, stop = 0.0, None
    queue = iter(jobs)

    hard_deadline = deadline + HARD_GRACE_MIN * 60
    abandoned = 0
    pool = ThreadPoolExecutor(args.concurrency)
    inflight = {}
    try:
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
            if time.monotonic() > hard_deadline:
                # OpenRouter keeps slow requests alive with whitespace, so socket
                # timeouts never fire; stop waiting rather than hit the CI job timeout.
                abandoned = len(inflight)
                break
            try:
                done, _ = wait(inflight, timeout=30, return_when=FIRST_COMPLETED)
            except KeyboardInterrupt:
                # Ctrl-C on a local run: keep what's answered so far, drop what's in flight.
                stop, abandoned = "interrupted", len(inflight)
                break
            for f in done:
                m, q = inflight.pop(f)
                try:
                    res = f.result()
                except Exception as e:  # one bad request must never sink the whole run
                    res = client.ChatResult(error=f"{type(e).__name__}: {e}"[:300])
                spent += res.cost
                answers[m["slug"]][q.key] = res
                pending[m["slug"]] -= 1
                if pending[m["slug"]] == 0:
                    _finalize_safely(m, todo[m["slug"]], answers.pop(m["slug"]))
    finally:
        pool.shutdown(wait=False, cancel_futures=True)

    if stop:
        print(f"stopped submitting: {stop}", flush=True)
    for slug, got in answers.items():  # models only partly answered when we stopped
        if got:
            _finalize_safely(by_slug[slug], todo[slug], got)
    print(f"total spent: ${spent:.4f}", flush=True)
    if abandoned:
        print(f"abandoned {abandoned} requests still running after the hard deadline; they'll be retried next run",
              flush=True)
        sys.stdout.flush()
        os._exit(0)  # don't let interpreter shutdown join the stuck worker threads
