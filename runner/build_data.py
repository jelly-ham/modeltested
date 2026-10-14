"""Aggregate stored scores into the JSON the static site is built from."""
from __future__ import annotations

import json
import os
import shutil
from collections import Counter

from . import client, costs, memory
from .common import (CANARY, OUTPUTS_DIR, RANKED_SUITES, RESULTS, SITE_DATA, SUITES, load_models, load_questions,
                     load_scores, model_suites, today, write_json)

HISTORY = RESULTS / "history.json"


def _mean(xs):
    return sum(xs) / len(xs) if xs else None


_SAMPLED_COSTS: dict | None = None


def model_summary(model: dict, by_suite: dict) -> dict:
    global _SAMPLED_COSTS
    if _SAMPLED_COSTS is None:
        _SAMPLED_COSTS = costs._load()
    items = load_scores(model["slug"])["items"]
    suites, providers, complete = {}, Counter(), True
    for suite, qs in by_suite.items():
        if suite not in model_suites(model):
            continue
        rows = [(q, items[q.key]) for q in qs if items.get(q.key, {}).get("h") == q.hash]
        providers.update(r.get("provider") for _, r in rows if r.get("provider"))
        pub = [r["score"] for q, r in rows if not q.private]
        priv = [r["score"] for q, r in rows if q.private]
        done = len(rows) == len(qs)
        if suite in RANKED_SUITES:
            complete &= done
        suites[suite] = {
            "score": round(100 * _mean([r["score"] for _, r in rows]), 1) if done else None,
            "public": round(100 * _mean(pub), 1) if pub and done else None,
            "private": round(100 * _mean(priv), 1) if priv and done else None,
            "done": len(rows), "total": len(qs),
        }
        if suite == "decisions" and done:
            briers = [r["brier"] for _, r in rows if r.get("brier") is not None]
            # 100 = perfectly calibrated and certain; Brier per question ranges 0..2.
            suites[suite]["calibration"] = round(100 * (1 - _mean(briers) / 2), 1) if briers else None
            hard_scores = [r["score"] for q, r in rows if q.data.get("difficulty") == "hard"]
            suites[suite]["hard"] = round(100 * _mean(hard_scores), 1) if hard_scores else None
    ranked = [s["score"] for k, s in suites.items() if k in RANKED_SUITES]
    overall = round(_mean(ranked), 1) if complete and ranked else None
    # Hard tasks: reported separately so the top of the table stays distinguishable.
    # Only the ranked suites: decisions has its own hard score (suites["decisions"]["hard"]).
    hard_rows = [r["score"] for k, qs in by_suite.items() if k in RANKED_SUITES for q in qs if q.data.get("difficulty") == "hard"
                 for r in [items.get(q.key)] if r and r.get("h") == q.hash]
    n_hard = sum(q.data.get("difficulty") == "hard" for k, qs in by_suite.items() if k in RANKED_SUITES for q in qs)
    hard = round(100 * _mean(hard_rows), 1) if n_hard and len(hard_rows) == n_hard else None
    # Answers cut off at the token limit (usually a thinking model that never stopped thinking).
    ranked_rows = [items[q.key] for k, qs in by_suite.items() if k in RANKED_SUITES for q in qs
                   if items.get(q.key, {}).get("h") == q.hash]
    truncated = {"n": sum(1 for r in ranked_rows if r.get("truncated")), "of": len(ranked_rows)}
    # When every cut-off answer stopped well short of what we asked for, the provider imposed a lower
    # output limit (LFM2.5-24B-A2B's only provider stops at 8,192). That's not the model overthinking.
    cut = [r.get("tok") or 0 for r in ranked_rows if r.get("truncated")]
    if cut and all(cut) and max(cut) < 0.9 * min(r.get("mt") or client.MAX_TOKENS for r in ranked_rows if r.get("truncated")):
        truncated["provider_cap"] = max(cut)
    keep = ("slug", "name", "org", "openrouter_id", "hf_id", "params_b", "active_params_b", "ollama", "license", "added", "kind", "status",
            "base", "quant")
    return {
        **{k: model.get(k) for k in keep},
        "overall": overall,
        "hard": hard,
        "suites": suites,
        "providers": [p for p, _ in providers.most_common()],
        "memory": memory.estimate(model),
        "truncated": truncated,
        # API cost per 1,000 tasks at OpenRouter prices; local (Mac) runs have none.
        "cost": None if model.get("status") == "local" else costs.per_1k(
            model, [q for qs in by_suite.values() for q in qs if not q.private], _SAMPLED_COSTS,
            [q for qs in by_suite.values() for q in qs]),
    }


def decision_board(doc: dict, by_suite: dict, summaries: list[dict]) -> list[dict]:
    """Everyone who finished the decisions suite: dedicated decision models, local LLMs and reference models."""
    rows = []
    dec_models = [m for m in doc["models"] if m.get("kind") == "decision" and m.get("status") in ("active", "auto", "unavailable", "local")]
    for s in summaries + [model_summary(m, by_suite) for m in dec_models]:
        d = s.get("suites", {}).get("decisions") or {}
        if d.get("score") is None:
            continue
        kind = "decision" if s.get("kind") == "decision" else "reference" if s.get("status") == "reference" else "local"
        rows.append({"slug": s["slug"], "name": s["name"], "org": s.get("org"), "kind": kind, "params_b": s.get("params_b"),
                     "open_weights": bool(s.get("hf_id")), "license": s.get("license"),
                     "accuracy": d["score"], "calibration": d.get("calibration"), "hard": d.get("hard"), "openrouter_id": s.get("openrouter_id"),
                     "hf_id": s.get("hf_id"), "public": d.get("public"), "private": d.get("private"),
                     "tested_on": "mac" if s.get("status") == "local" else "openrouter", "added": s.get("added"),
                     "cost_per_1k": (s.get("cost") or {}).get("decisions")})
    rows.sort(key=lambda r: (-r["accuracy"], -(r["calibration"] or 0)))
    for i, r in enumerate(rows, 1):
        r["rank"] = i
    return rows


def main(args) -> None:
    doc = load_models()
    # "unavailable" models keep their place on the leaderboard if they were fully tested.
    # "local" = a quantized download run with Ollama on the Mac test machine.
    statuses = {"active", "auto", "unavailable", "local"} | ({"test"} if args.include_test else set())
    models = [m for m in doc["models"] if m.get("status") in statuses and m.get("kind") != "decision"]
    questions = load_questions()
    if os.environ.get("CI") and not any(q.private for q in questions):
        # Publishing public-only scores would silently change every number on the site.
        raise SystemExit("hidden test set missing — refusing to build site data")
    by_suite: dict[str, list] = {}
    for q in questions:
        by_suite.setdefault(q.suite, []).append(q)

    summaries = [model_summary(m, by_suite) for m in models]

    # While new questions are being rolled out, a model is incomplete until it has answered them.
    # Keep showing its last complete result (marked as updating) instead of dropping it.
    # Source: results/last-complete.json (committed), seeded from the site data the first time.
    last_path = RESULTS / "last-complete.json"
    if last_path.exists():
        last = json.loads(last_path.read_text())
    else:
        site = SITE_DATA / "leaderboard.json"
        # Entries flagged "updating" still carry that model's last complete result.
        last = {m["slug"]: {k: v for k, v in m.items() if k not in ("updating", "memory", "rank")}
                for m in json.loads(site.read_text()).get("models", [])} if site.exists() else {}
    for i, s in enumerate(summaries):
        if s["overall"] is not None:
            last[s["slug"]] = {k: v for k, v in s.items() if k not in ("memory", "rank")}
        elif s["slug"] in last and not args.include_test:
            summaries[i] = {**last[s["slug"]], "memory": s["memory"], "updating": True}
    if not args.include_test:
        write_json(last_path, dict(sorted(last.items())))

    # A local run of a model we also tested at full precision is a Q4-vs-full comparison, shown on
    # that model's page. A local run of a model we couldn't test otherwise fills the gap on the leaderboard.
    by_slug = {s["slug"]: s for s in summaries}
    quantized = []
    for s in [s for s in summaries if s.get("status") == "local"]:
        base = by_slug.get(s.get("base") or "")
        if not base or base["overall"] is None:
            continue
        summaries.remove(s)
        # Only compare like with like: an "updating" base result predates the current questions.
        if s["overall"] is not None and not base.get("updating"):
            quantized.append({"slug": s["slug"], "name": s["name"], "base": base["slug"], "quant": s.get("quant"),
                              "overall": s["overall"], "hard": s["hard"], "suites": s["suites"],
                              "base_overall": base["overall"], "base_hard": base.get("hard"),
                              "base_suites": base["suites"], "delta": round(s["overall"] - base["overall"], 1)})

    references = [model_summary(m, by_suite) for m in doc["models"] if m.get("status") == "reference"]
    ranked = sorted([s for s in summaries if s["overall"] is not None], key=lambda s: -s["overall"])
    for i, s in enumerate(ranked, 1):
        s["rank"] = i
    unavailable = {m["slug"] for m in models if m.get("status") in ("unavailable", "local")}
    pending = [s["slug"] for s in summaries if s["overall"] is None and s["slug"] not in unavailable]

    history = json.loads(HISTORY.read_text()) if HISTORY.exists() else []
    seen = {h["slug"] for h in history}
    for s in ranked:
        if s["slug"] not in seen and not s["slug"].startswith("mock-"):
            history.append({"date": today(), "slug": s["slug"], "name": s["name"], "event": "added",
                            "overall": s["overall"], "rank": s["rank"], "of": len(ranked)})
    if not args.include_test:
        write_json(HISTORY, history)

    decision_rows = decision_board(doc, by_suite, summaries)
    write_json(SITE_DATA / "leaderboard.json", {
        "generated": today(),
        "suites": [{"id": k, **v, "n_public": sum(not q.private for q in by_suite.get(k, [])),
                    "n_private": sum(q.private for q in by_suite.get(k, []))} for k, v in SUITES.items()],
        "tiers": [{**t, "usable_gb": round(memory.usable_gb(t), 1)} for t in memory.TIERS],
        "memory_assumptions": {"context": memory.CONTEXT, "overhead_gb": memory.OVERHEAD_GB,
                               "quants": dict(memory.QUANTS)},
        "models": ranked,
        "pending": pending,
        # Mac (Ollama) models waiting for their first complete run; shown as "Testing next".
        "local_queue": [s["name"].replace(" (Q4, Mac)", "") for s in summaries
                        if s.get("status") == "local" and s["overall"] is None and not s.get("updating")],
        "references": [r for r in references if r["overall"] is not None],
        "quantized": quantized,
        # Reference (cloud) models get a write-up of their own, never a place on a board.
        "decisions": decision_rows,
        "decisions_unsupported": [{"name": m["name"], "openrouter_id": m["openrouter_id"], "open_weights": bool(m.get("hf_id")),
                                   "reason": m.get("unsupported_reason")} for m in doc["models"]
                                  if m.get("kind") == "decision" and m.get("status") == "unsupported"],
        "n_hard": sum(q.data.get("difficulty") == "hard" and q.suite in RANKED_SUITES for q in questions),
        "n_hard_decisions": sum(q.data.get("difficulty") == "hard" and q.suite == "decisions" for q in questions),
        "changelog": sorted(history, key=lambda h: h["date"], reverse=True)[:50],
    })

    public = [{"suite": q.suite, "id": q.id, **{k: v for k, v in q.data.items() if k != "reference"}}
              for q in questions if not q.private]
    write_json(SITE_DATA / "public-questions.json", {"canary": CANARY, "questions": public})

    out_dir = SITE_DATA / "outputs"
    shutil.rmtree(out_dir, ignore_errors=True)
    # Decision models have their own pages (/decision-models/<slug>/) with their public answers.
    for s in ranked + [r for r in decision_rows if r["kind"] == "decision"]:
        src = OUTPUTS_DIR / s["slug"]
        if src.exists():
            merged = {p.stem: json.loads(p.read_text()) for p in sorted(src.glob("*.json"))}
            write_json(out_dir / f"{s['slug']}.json", merged)
    print(f"site data: {len(ranked)} ranked, {len(pending)} pending")
