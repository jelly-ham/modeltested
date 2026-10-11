"""Validate the question bank itself (run before committing new questions).

- every coding reference solution passes its tests
- an empty solution fails them (the tests actually test something)
- every extraction answer key scores 1.0 against itself and only uses declared fields
- public files carry the canary string
"""
from __future__ import annotations

import json

from . import sandbox, suites
from .common import BENCH, CANARY, load_questions


def main(args) -> None:
    qs = load_questions()
    problems = []

    coding = [q for q in qs if q.suite == "coding"]
    good = sandbox.run_cases({q.key: q.data["reference"] + "\n\n" + q.data["tests"] for q in coding})
    empty = sandbox.run_cases({q.key: "pass\n\n" + q.data["tests"] for q in coding})
    for q in coding:
        if not good[q.key]["passed"]:
            problems.append(f"{q.key}: reference fails: {good[q.key]['error']}")
        if empty[q.key]["passed"]:
            problems.append(f"{q.key}: tests pass without a solution")

    for q in (q for q in qs if q.suite == "extract"):
        score, detail = suites.score_extract(q.data["expected"], q.data["expected"])
        if score != 1.0:
            problems.append(f"{q.key}: answer key does not score 1.0 against itself: {detail}")
        for k in q.data["expected"]:
            if f'"{k}"' not in q.data["fields"]:
                problems.append(f"{q.key}: expected key {k!r} missing from fields spec")

    for q in (q for q in qs if q.suite == "decisions"):
        spec, exp = q.data["questions"], q.data["expected"]
        if set(spec) != set(exp):
            problems.append(f"{q.key}: questions and expected answers don't match")
            continue
        perfect = {qid: {suites._expected_key(s, exp[qid]): 1.0} for qid, s in spec.items()}
        score, _ = suites.score_decisions(spec, exp, suites.decisions_from_llm(json.dumps(perfect), spec))
        if score != 1.0:
            problems.append(f"{q.key}: answer key does not score 1.0 against itself")

    for f in (BENCH / "public").glob("*.json"):
        if json.loads(f.read_text()).get("canary") != CANARY:
            problems.append(f"{f.name}: missing canary")

    n_pub = sum(not q.private for q in qs)
    print(f"checked {len(qs)} questions ({n_pub} public, {len(qs) - n_pub} private)")
    for p in problems:
        print("PROBLEM", p)
    if problems:
        raise SystemExit(1)
    print("all good")
