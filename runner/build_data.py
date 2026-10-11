"""Aggregate stored scores into the JSON the static site is built from."""
from __future__ import annotations

import json
import os
import shutil
from collections import Counter

from . import memory
from .common import (CANARY, OUTPUTS_DIR, RESULTS, SITE_DATA, SUITES, load_models, load_questions, load_scores,
                     today, write_json)

HISTORY = RESULTS / "history.json"


def _mean(xs):
    return sum(xs) / len(xs) if xs else None


def model_summary(model: dict, by_suite: dict) -> dict:
    items = load_scores(model["slug"])["items"]
    suites, providers, complete = {}, Counter(), True
    for suite, qs in by_suite.items():
        rows = [(q, items[q.key]) for q in qs if items.get(q.key, {}).get("h") == q.hash]
        providers.update(r.get("provider") for _, r in rows if r.get("provider"))
        pub = [r["score"] for q, r in rows if not q.private]
        priv = [r["score"] for q, r in rows if q.private]
        done = len(rows) == len(qs)
        complete &= done
        suites[suite] = {
            "score": round(100 * _mean([r["score"] for _, r in rows]), 1) if done else None,
            "public": round(100 * _mean(pub), 1) if pub and done else None,
            "private": round(100 * _mean(priv), 1) if priv and done else None,
            "done": len(rows), "total": len(qs),
        }
    overall = round(_mean([s["score"] for s in suites.values()]), 1) if complete else None
    keep = ("slug", "name", "org", "openrouter_id", "hf_id", "params_b", "active_params_b", "ollama", "license", "added")
    return {
        **{k: model.get(k) for k in keep},
        "overall": overall,
        "suites": suites,
        "providers": [p for p, _ in providers.most_common()],
        "memory": memory.estimate(model),
    }


def main(args) -> None:
    doc = load_models()
    statuses = {"active", "auto"} | ({"test"} if args.include_test else set())
    models = [m for m in doc["models"] if m.get("status") in statuses]
    questions = load_questions()
    if os.environ.get("CI") and not any(q.private for q in questions):
        # Publishing public-only scores would silently change every number on the site.
        raise SystemExit("hidden test set missing — refusing to build site data")
    by_suite: dict[str, list] = {}
    for q in questions:
        by_suite.setdefault(q.suite, []).append(q)

    summaries = [model_summary(m, by_suite) for m in models]
    ranked = sorted([s for s in summaries if s["overall"] is not None], key=lambda s: -s["overall"])
    for i, s in enumerate(ranked, 1):
        s["rank"] = i
    pending = [s["slug"] for s in summaries if s["overall"] is None]

    history = json.loads(HISTORY.read_text()) if HISTORY.exists() else []
    seen = {h["slug"] for h in history}
    for s in ranked:
        if s["slug"] not in seen and not s["slug"].startswith("mock-"):
            history.append({"date": today(), "slug": s["slug"], "name": s["name"], "event": "added",
                            "overall": s["overall"], "rank": s["rank"], "of": len(ranked)})
    if not args.include_test:
        write_json(HISTORY, history)

    write_json(SITE_DATA / "leaderboard.json", {
        "generated": today(),
        "suites": [{"id": k, **v, "n_public": sum(not q.private for q in by_suite.get(k, [])),
                    "n_private": sum(q.private for q in by_suite.get(k, []))} for k, v in SUITES.items()],
        "tiers": [{**t, "usable_gb": round(memory.usable_gb(t), 1)} for t in memory.TIERS],
        "memory_assumptions": {"context": memory.CONTEXT, "overhead_gb": memory.OVERHEAD_GB,
                               "quants": dict(memory.QUANTS)},
        "models": ranked,
        "pending": pending,
        "changelog": sorted(history, key=lambda h: h["date"], reverse=True)[:50],
    })

    public = [{"suite": q.suite, "id": q.id, **{k: v for k, v in q.data.items() if k != "reference"}}
              for q in questions if not q.private]
    write_json(SITE_DATA / "public-questions.json", {"canary": CANARY, "questions": public})

    out_dir = SITE_DATA / "outputs"
    shutil.rmtree(out_dir, ignore_errors=True)
    for s in ranked:
        src = OUTPUTS_DIR / s["slug"]
        if src.exists():
            merged = {p.stem: json.loads(p.read_text()) for p in sorted(src.glob("*.json"))}
            write_json(out_dir / f"{s['slug']}.json", merged)
    print(f"site data: {len(ranked)} ranked, {len(pending)} pending")
